"""
Budget enforcement lives here, as code the graph checks on every edge —
NOT as an instruction inside a prompt. A prompt asking the model to be
efficient is not a budget.
"""
from datetime import datetime, timezone
from app.config import settings
from app.schemas.state import GraphState


class BudgetExceeded(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def check_sub_question_budget(state: GraphState) -> None:
    if state.plan and len(state.plan.sub_questions) > settings.max_sub_questions:
        raise BudgetExceeded(f"sub_questions > {settings.max_sub_questions}")


def check_search_budget(state: GraphState) -> None:
    if state.search_count >= settings.max_searches_per_sq * settings.max_sub_questions:
        raise BudgetExceeded("total search budget exhausted")


def check_token_budget(state: GraphState) -> None:
    if state.token_spend >= settings.max_total_tokens:
        raise BudgetExceeded(f"token_spend >= {settings.max_total_tokens}")


def check_wall_clock(state: GraphState) -> None:
    if not state.started_at:
        return
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(state.started_at)).total_seconds()
    if elapsed > settings.wall_clock_seconds:
        raise BudgetExceeded(f"wall clock > {settings.wall_clock_seconds}s")


def check_all_budgets(state: GraphState) -> None:
    check_sub_question_budget(state)
    check_search_budget(state)
    check_token_budget(state)
    check_wall_clock(state)
