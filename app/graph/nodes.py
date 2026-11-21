
"""
LangGraph nodes for the Multi-Agent Research Assistant.

This module contains:
- Planner node
- Researcher node
- Writer node
- Step-level tracing
- Feedback-based research revision

Each traced execution records:
- Agent name and step ID
- Input and output summaries
- Execution status and latency
- Available token usage
"""

import logging
import time

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.graph.research_revision import (
    build_revised_question,
)

from app.schemas.finding import (
    Finding,
    ResearchResult,
)
from app.schemas.plan import (
    ResearchPlan,
    SubQuestion,
)
from app.schemas.report import ResearchReport
from app.schemas.state import ResearchState
from app.schemas.trace import (
    TraceEvent,
    TokenUsage,
)

from app.persistence.trace_store import record_trace
from app.persistence.token_tracker import (
    get_token_usage,
)


logger = logging.getLogger(__name__)


PlannerFn = Callable[[str], ResearchPlan]

ResearcherFn = Callable[
    [SubQuestion],
    ResearchResult,
]

WriterFn = Callable[
    [str, list[Finding]],
    ResearchReport,
]


def _get_tokens_safely(
    run_id: str,
) -> dict | None:
    """
    Read cumulative token usage for a run.

    Tracing failures must not prevent
    the workflow from continuing.
    """

    if not run_id:
        return None

    try:
        return get_token_usage(run_id)

    except Exception:
        logger.warning(
            "Unable to read tokens for run %s",
            run_id,
            exc_info=True,
        )
        return None


def _calculate_step_tokens(
    before: dict | None,
    after: dict | None,
) -> TokenUsage:
    """
    Calculate token usage during one node.

    This uses cumulative-counter differences
    and assumes sequential node execution.
    """

    if before is None or after is None:
        return TokenUsage()

    input_tokens = max(
        0,
        after["input_tokens"]
        - before["input_tokens"],
    )

    output_tokens = max(
        0,
        after["output_tokens"]
        - before["output_tokens"],
    )

    total_tokens = max(
        0,
        after["total_tokens"]
        - before["total_tokens"],
    )

    total_tokens = max(
        total_tokens,
        input_tokens + output_tokens,
    )

    return TokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
    )


def _save_trace_safely(
    trace: TraceEvent,
) -> None:
    """
    Store traces independently from graph state.
    """

    try:
        record_trace(trace)

    except Exception:
        logger.warning(
            "Unable to save trace for run %s",
            trace.run_id,
            exc_info=True,
        )


def _execute_with_tracing(
    state: ResearchState,
    agent: str,
    input_data: dict[str, Any],
    execute: Callable[[], dict],
    summarize_output: Callable[[dict], dict],
) -> dict:
    """
    Execute one LangGraph node and store its trace.

    Return the original node result unchanged.
    """

    run_id = str(
        state.get("run_id") or ""
    )

    # Existing tests can use states without
    # a run_id and do not require Redis.
    if not run_id:
        return execute()

    step_id = str(uuid4())

    started_at = datetime.now(
        timezone.utc
    )

    start_clock = time.perf_counter()

    tokens_before = _get_tokens_safely(
        run_id
    )

    result = None
    error = None
    status = "success"

    try:
        result = execute()
        return result

    except Exception as exc:
        status = "failed"
        error = type(exc).__name__
        raise

    finally:
        completed_at = datetime.now(
            timezone.utc
        )

        latency_ms = round(
            (
                time.perf_counter()
                - start_clock
            ) * 1000,
            2,
        )

        tokens_after = _get_tokens_safely(
            run_id
        )

        tokens = _calculate_step_tokens(
            tokens_before,
            tokens_after,
        )

        output_data = {}

        if result is not None:
            try:
                output_data = summarize_output(
                    result
                )

            except Exception:
                logger.warning(
                    "Unable to summarize output for %s",
                    agent,
                    exc_info=True,
                )

        trace = TraceEvent(
            run_id=run_id,
            step_id=step_id,
            agent=agent,
            status=status,
            input_data=input_data,
            output_data=output_data,
            tools_called=[],
            tokens=tokens,
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=latency_ms,
            error=error,
        )

        _save_trace_safely(trace)


def make_planner_node(
    planner_fn: PlannerFn,
):
    """
    Create the Planner node.

    The Planner converts a user question
    into a structured research plan.
    """

    def planner_node(
        state: ResearchState,
    ) -> dict:

        def execute() -> dict:
            plan = planner_fn(
                state["question"]
            )

            return {
                "plan": plan.model_dump(
                    mode="json"
                ),
                "question_index": 0,
                "findings": [],
                "attempts": {},
                "revisions": {},
                "review_feedback": {},
                "total_tokens": 0,
                "status": "researching",
            }

        def summarize_output(
            result: dict,
        ) -> dict:
            questions = result[
                "plan"
            ]["sub_questions"]

            return {
                "sub_questions_count": len(
                    questions
                ),
                "sub_question_ids": [
                    item["id"]
                    for item in questions
                ],
                "status": result["status"],
            }

        return _execute_with_tracing(
            state=state,
            agent="planner",
            input_data={
                "question": state["question"][:500],
            },
            execute=execute,
            summarize_output=summarize_output,
        )

    return planner_node


def make_researcher_node(
    researcher_fn: ResearcherFn,
):
    """
    Create the Researcher node.

    For the initial pass:
        Use the original SubQuestion.

    For an authorized retry with feedback:
        Build a revised SubQuestion that targets
        missing evidence identified by Groq.

    The original question ID is preserved.
    """

    def researcher_node(
        state: ResearchState,
    ) -> dict:

        questions = state["plan"][
            "sub_questions"
        ]

        index = state["question_index"]

        original_question = (
            SubQuestion.model_validate(
                questions[index]
            )
        )

        question_id = original_question.id

        revisions = state.get(
            "revisions"
        ) or {}

        revisions_used = revisions.get(
            question_id,
            0,
        )

        feedback_by_question = state.get(
            "review_feedback"
        ) or {}

        feedback = feedback_by_question.get(
            question_id,
            "",
        )

        # A revised search requires BOTH:
        # - an authorized revision
        # - non-empty Groq feedback.
        is_revision = (
            revisions_used > 0
            and isinstance(feedback, str)
            and bool(feedback.strip())
        )

        research_question = original_question

        if is_revision:
            research_question = (
                build_revised_question(
                    original=original_question,
                    feedback=feedback,
                )
            )

        def execute() -> dict:
            attempts = dict(
                state.get("attempts") or {}
            )

            attempts[question_id] = (
                attempts.get(question_id, 0)
                + 1
            )

            # This is the key integration:
            # run_researcher receives the
            # revised question when retrying.
            result = researcher_fn(
                research_question
            )

            existing_findings = list(
                state.get("findings") or []
            )

            known_ids = {
                finding["id"]
                for finding in existing_findings
            }

            for finding in result.findings:
                if finding.id not in known_ids:
                    existing_findings.append(
                        finding.model_dump(
                            mode="json"
                        )
                    )

                    known_ids.add(
                        finding.id
                    )

            return {
                "findings": existing_findings,
                "attempts": attempts,
                "last_result_status": (
                    result.status
                ),
            }

        def summarize_output(
            result: dict,
        ) -> dict:
            return {
                "sub_question_id": question_id,
                "result_status": result[
                    "last_result_status"
                ],
                "total_findings": len(
                    result["findings"]
                ),
                "finding_ids": [
                    item["id"]
                    for item in result[
                        "findings"
                    ]
                ],
                "attempt": result[
                    "attempts"
                ][question_id],
                "is_revision": is_revision,
                "feedback_used": (
                    bool(feedback.strip())
                    if is_revision
                    else False
                ),
            }

        return _execute_with_tracing(
            state=state,
            agent="researcher",
            input_data={
                "sub_question_id": question_id,
                "question": (
                    research_question.question[:500]
                ),
                "existing_findings_count": len(
                    state.get("findings") or []
                ),
                "is_revision": is_revision,
                "revisions_used": revisions_used,
                "feedback": (
                    feedback[:500]
                    if is_revision
                    else ""
                ),
            },
            execute=execute,
            summarize_output=summarize_output,
        )

    return researcher_node


def make_writer_node(
    writer_fn: WriterFn,
):
    """
    Create the Writer node.

    The Writer creates a final report
    from the collected findings.
    """

    def writer_node(
        state: ResearchState,
    ) -> dict:

        def execute() -> dict:
            findings = [
                Finding.model_validate(
                    item
                )
                for item in state[
                    "findings"
                ]
            ]

            report = writer_fn(
                state["question"],
                findings,
            )

            return {
                "report": report.model_dump(
                    mode="json"
                ),
                "status": "completed",
            }

        def summarize_output(
            result: dict,
        ) -> dict:
            return {
                "status": result["status"],
                "report_generated": bool(
                    result.get("report")
                ),
                "findings_used_count": len(
                    state["findings"]
                ),
                "finding_ids": [
                    item["id"]
                    for item in state[
                        "findings"
                    ]
                ],
            }

        return _execute_with_tracing(
            state=state,
            agent="writer",
            input_data={
                "question": state["question"][:500],
                "findings_count": len(
                    state["findings"]
                ),
            },
            execute=execute,
            summarize_output=summarize_output,
        )

    return writer_node
