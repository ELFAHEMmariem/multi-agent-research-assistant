
"""
Hybrid Supervisor for the Multi-Agent Research Assistant.

Responsibilities:
- Enforce time and token budgets
- Review researcher findings with an optional LLM
- Authorize at most one research revision
- Route to Researcher, Writer, or Stop
- Record execution traces in Redis

The Reviewer is injected so unit tests can run
without making real Groq API calls.
"""

import logging
import time

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from app.graph.budgets import (
    BudgetLimits,
    can_retry,
    time_budget_exceeded,
    token_budget_exceeded,
)

from app.persistence.trace_store import record_trace
from app.schemas.finding import Finding
from app.schemas.review import ResearchReview
from app.schemas.state import ResearchState
from app.schemas.trace import TraceEvent, TokenUsage


logger = logging.getLogger(__name__)


ReviewerFn = Callable[
    [str, list[Finding], str | None],
    ResearchReview,
]


def _current_question(state: ResearchState) -> dict:
    """Return the current sub-question."""

    questions = state["plan"]["sub_questions"]
    index = state["question_index"]

    return questions[index]


def _question_text(question: dict) -> str:
    """
    Extract the text of a sub-question.

    Supports common field names without
    changing the existing plan schema.
    """

    for field in ("question", "text", "title"):
        value = question.get(field)

        if isinstance(value, str) and value.strip():
            return value.strip()

    raise ValueError(
        "Current sub-question has no usable text"
    )


def _question_findings(
    state: ResearchState,
    question_id: str,
) -> list[Finding]:
    """Retrieve findings for one sub-question."""

    result = []

    for item in state.get("findings", []):
        finding = Finding.model_validate(item)

        if finding.sub_question_id == question_id:
            result.append(finding)

    return result


def _supervisor_decision(
    state: ResearchState,
    limits: BudgetLimits,
    review: ResearchReview | None = None,
    review_failed: bool = False,
) -> dict:
    """
    Apply deterministic routing rules.

    A technical Reviewer failure must not
    be treated as a recommendation to retry
    an otherwise successful research pass.
    """

    # 1. Global budget checks
    if time_budget_exceeded(state, limits):
        return {
            "next_action": "stop",
            "status": "stopped",
            "stop_reason": "Time budget exceeded",
        }

    if token_budget_exceeded(state, limits):
        return {
            "next_action": "stop",
            "status": "stopped",
            "stop_reason": "Token budget exceeded",
        }

    # 2. Current research question
    questions = state["plan"]["sub_questions"]
    index = state["question_index"]

    question = questions[index]
    question_id = question["id"]

    research_success = (
        state["last_result_status"] == "success"
    )

    # 3. Decide whether another pass is justified
    should_retry = not research_success

    if review is not None:
        should_retry = (
            not review.approved
            and review.retry_recommended
        )

    # A technical review error does not justify
    # repeating a successful research pass.
    if review_failed and research_success:
        should_retry = False

    # 4. Enforce retry limits
    if should_retry and can_retry(
        state,
        question_id,
        limits,
    ):
        revisions = dict(
            state.get("revisions") or {}
        )

        revisions[question_id] = (
            revisions.get(question_id, 0) + 1
        )

        result = {
            "revisions": revisions,
            "next_action": "research",
            "status": "retrying",
        }

        # Preserve feedback when a quality-based
        # revision has been authorized.
        if review is not None and review.feedback:
            feedback_by_question = dict(
                state.get("review_feedback") or {}
            )

            feedback_by_question[question_id] = (
                review.feedback
            )

            result["review_feedback"] = (
                feedback_by_question
            )

        return result

    # 5. Move to next sub-question
    next_index = index + 1

    if next_index < len(questions):
        return {
            "question_index": next_index,
            "next_action": "research",
            "status": "researching",
        }

    # 6. Write report if findings exist
    if state["findings"]:
        return {
            "next_action": "write",
            "status": "writing",
        }

    return {
        "next_action": "stop",
        "status": "no_results",
        "stop_reason": "No usable findings",
    }


def _record_supervisor_trace(
    run_id: str,
    step_id: str,
    status: str,
    input_data: dict,
    output_data: dict,
    started_at: datetime,
    latency_ms: float,
    error: str | None,
) -> None:
    """Persist Supervisor tracing information."""

    try:
        trace = TraceEvent(
            run_id=run_id,
            step_id=step_id,
            agent="supervisor",
            status=status,
            input_data=input_data,
            output_data=output_data,
            tools_called=[],
            tokens=TokenUsage(),
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            latency_ms=latency_ms,
            error=error,
        )

        record_trace(trace)

    except Exception:
        logger.warning(
            "Could not store Supervisor trace: %s",
            run_id,
            exc_info=True,
        )


def supervisor_node(
    state: ResearchState,
    limits: BudgetLimits,
    reviewer_fn: ReviewerFn | None = None,
) -> dict:
    """
    Run the hybrid Supervisor.

    When reviewer_fn is provided, the
    Supervisor evaluates research quality.

    Without reviewer_fn, original deterministic
    routing remains available for compatibility.
    """

    run_id = str(state.get("run_id") or "")

    step_id = str(uuid4())
    started_at = datetime.now(timezone.utc)
    start_clock = time.perf_counter()

    review = None
    review_failed = False
    review_error = None
    result = None

    trace_status = "success"
    error = None

    input_data = {
        "question_index": state.get(
            "question_index",
            0,
        ),
        "last_result_status": state.get(
            "last_result_status"
        ),
        "findings_count": len(
            state.get("findings") or []
        ),
        "total_tokens": state.get(
            "total_tokens",
            0,
        ),
        "reviewer_enabled": (
            reviewer_fn is not None
        ),
    }

    try:
        # Never call Groq when a global
        # budget is already exhausted.
        budgets_available = (
            not time_budget_exceeded(state, limits)
            and not token_budget_exceeded(state, limits)
        )

        research_success = (
            state.get("last_result_status")
            == "success"
        )

        if (
            reviewer_fn is not None
            and budgets_available
            and research_success
        ):
            question = _current_question(state)
            question_id = question["id"]

            question_text = _question_text(
                question
            )

            findings = _question_findings(
                state,
                question_id,
            )

            if findings:
                try:
                    review = reviewer_fn(
                        question_text,
                        findings,
                        run_id=run_id or None,
                    )

                    review = (
                        ResearchReview.model_validate(
                            review
                        )
                    )

                except Exception as exc:
                    review_failed = True
                    review_error = type(exc).__name__

                    logger.warning(
                        "LLM review failed for run %s",
                        run_id,
                        exc_info=True,
                    )

            else:
                review_failed = True
                review_error = "NoFindings"

        result = _supervisor_decision(
            state=state,
            limits=limits,
            review=review,
            review_failed=review_failed,
        )

        return result

    except Exception as exc:
        trace_status = "failed"
        error = type(exc).__name__
        raise

    finally:
        latency_ms = round(
            (
                time.perf_counter()
                - start_clock
            ) * 1000,
            2,
        )

        output_data = {}

        if result is not None:
            output_data = {
                "next_action": result.get(
                    "next_action"
                ),
                "status": result.get(
                    "status"
                ),
                "stop_reason": result.get(
                    "stop_reason"
                ),
                "question_index": result.get(
                    "question_index"
                ),
                "revisions": result.get(
                    "revisions",
                    {},
                ),
            }

        if review is not None:
            output_data["quality_review"] = (
                review.model_dump()
            )

        if review_error is not None:
            output_data["review_error"] = (
                review_error
            )

        if run_id:
            _record_supervisor_trace(
                run_id=run_id,
                step_id=step_id,
                status=trace_status,
                input_data=input_data,
                output_data=output_data,
                started_at=started_at,
                latency_ms=latency_ms,
                error=error,
            )
