import pytest
from app.graph.budgets import check_token_budget, check_sub_question_budget, BudgetExceeded
from app.schemas.state import GraphState
from app.schemas.plan import Plan, SubQuestion


def test_token_budget_raises_when_exceeded():
    state = GraphState(run_id="r1", original_question="q", token_spend=999_999)
    with pytest.raises(BudgetExceeded):
        check_token_budget(state)


def test_sub_question_budget_raises_when_plan_too_large():
    sqs = [SubQuestion(id=f"sq{i}", question=f"q{i}", priority=1) for i in range(10)]
    state = GraphState(run_id="r1", original_question="q", plan=Plan(original_question="q", sub_questions=sqs))
    with pytest.raises(BudgetExceeded):
        check_sub_question_budget(state)
