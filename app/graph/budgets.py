
import time
from dataclasses import dataclass

from app.schemas.state import ResearchState


@dataclass(frozen=True)
class BudgetLimits:
    max_subquestions: int = 3
    max_searches_per_question: int = 2
    max_revisions: int = 1
    max_total_tokens: int = 15000
    max_run_seconds: int = 240


def time_budget_exceeded(
    state: ResearchState,
    limits: BudgetLimits,
) -> bool:
    elapsed = time.time() - state["started_at"]
    return elapsed >= limits.max_run_seconds


def token_budget_exceeded(
    state: ResearchState,
    limits: BudgetLimits,
) -> bool:
    return (
        state.get("total_tokens", 0)
        >= limits.max_total_tokens
    )


def can_retry(
    state: ResearchState,
    question_id: str,
    limits: BudgetLimits,
) -> bool:
    attempts = state["attempts"].get(question_id, 0)
    revisions = state["revisions"].get(question_id, 0)

    return (
        attempts < limits.max_searches_per_question
        and revisions < limits.max_revisions
    )
