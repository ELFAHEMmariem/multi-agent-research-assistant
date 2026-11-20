
from app.graph.budgets import (
    BudgetLimits,
    can_retry,
    time_budget_exceeded,
    token_budget_exceeded,
)
from app.schemas.state import ResearchState


def supervisor_node(
    state: ResearchState,
    limits: BudgetLimits,
) -> dict:

    # 1. Verify global budgets
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

    # 2. Identify current question
    questions = state["plan"]["sub_questions"]
    index = state["question_index"]

    question = questions[index]
    question_id = question["id"]

    # 3. Check whether research succeeded
    success = state["last_result_status"] == "success"

    if not success and can_retry(
        state, question_id, limits
    ):
        revisions = dict(state["revisions"])

        revisions[question_id] = (
            revisions.get(question_id, 0) + 1
        )

        return {
            "revisions": revisions,
            "next_action": "research",
            "status": "retrying",
        }

    # 4. Move to the next question
    next_index = index + 1

    if next_index < len(questions):
        return {
            "question_index": next_index,
            "next_action": "research",
            "status": "researching",
        }

    # 5. All questions have been processed
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
