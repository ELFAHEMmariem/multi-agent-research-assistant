
import time

from app.graph.budgets import BudgetLimits
from app.graph.supervisor import supervisor_node


def test_supervisor_moves_to_next_question():
    state = {
        "run_id": "test-001",
        "question": "AI security",
        "started_at": time.time(),
        "plan": {
            "sub_questions": [
                {"id": "Q1", "question": "First question?"},
                {"id": "Q2", "question": "Second question?"},
            ]
        },
        "question_index": 0,
        "findings": [{"id": "Q1-F001"}],
        "attempts": {"Q1": 1},
        "revisions": {},
        "total_tokens": 0,
        "last_result_status": "success",
    }

    decision = supervisor_node(
        state,
        BudgetLimits(),
    )

    assert decision["next_action"] == "research"
    assert decision["question_index"] == 1
