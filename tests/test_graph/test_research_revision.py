"""
Tests for Researcher question revision.

Verify that Groq feedback changes the research
question without changing its identifier.

No Groq or Tavily calls are performed.
"""

import pytest

from app.graph.research_revision import (
    build_revised_question,
)
from app.schemas.plan import SubQuestion


def make_question():
    """
    Build a valid test SubQuestion based on
    the actual project's Pydantic schema.
    """

    fields = SubQuestion.model_fields

    question_field = next(
        (
            field
            for field in ("question", "text", "title")
            if field in fields
        ),
        None,
    )

    if question_field is None:
        pytest.fail(
            "Unsupported SubQuestion text field"
        )

    data = {
        "id": "Q1",
        question_field: (
            "What are Zero Trust challenges?"
        ),
    }

    # Include additional required fields
    # using their declared defaults where possible.
    for name, field in fields.items():
        if name in data:
            continue

        if field.is_required():
            annotation = field.annotation

            if annotation is str:
                data[name] = "Test value"
            elif annotation is int:
                data[name] = 1
            elif annotation is bool:
                data[name] = False

    question = SubQuestion.model_validate(data)

    return question, question_field


def test_revision_uses_feedback():
    question, field = make_question()

    revised = build_revised_question(
        original=question,
        feedback=(
            "Investigate MFA deployment challenges."
        ),
    )

    revised_text = getattr(revised, field)

    assert "MFA deployment" in revised_text
    assert "Zero Trust" in revised_text


def test_revision_preserves_question_id():
    question, _ = make_question()

    revised = build_revised_question(
        original=question,
        feedback="Research identity lifecycle risks.",
    )

    assert revised.id == question.id


def test_revision_does_not_change_original():
    question, field = make_question()

    original_text = getattr(question, field)

    build_revised_question(
        original=question,
        feedback="Investigate IAM challenges.",
    )

    assert getattr(question, field) == original_text


def test_empty_feedback_is_rejected():
    question, _ = make_question()

    with pytest.raises(ValueError):
        build_revised_question(
            original=question,
            feedback="   ",
        )


def test_feedback_must_be_string():
    question, _ = make_question()

    with pytest.raises(TypeError):
        build_revised_question(
            original=question,
            feedback=None,
        )
