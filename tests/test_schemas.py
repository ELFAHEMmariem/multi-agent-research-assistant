
import pytest
from pydantic import ValidationError

from app.schemas.plan import ResearchPlan


def test_valid_plan():
    plan = ResearchPlan(
        original_question="AI security",
        sub_questions=[
            {
                "id": "Q1",
                "question": "What are the main AI security risks?"
            }
        ]
    )

    assert len(plan.sub_questions) == 1
    assert plan.sub_questions[0].id == "Q1"


def test_plan_with_too_many_questions():
    with pytest.raises(ValidationError):
        ResearchPlan(
            original_question="AI security",
            sub_questions=[
                {
                    "id": f"Q{i}",
                    "question": f"What is AI security risk number {i}?"
                }
                for i in range(4)
            ]
        )
