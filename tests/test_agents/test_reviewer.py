"""
Unit tests for the Groq research quality reviewer.

These tests use a fake LLM.
No real Groq API calls are performed.
"""

from datetime import datetime, timezone

import pytest

from app.agents.reviewer import (
    build_review_payload,
    review_research,
)

from app.schemas.finding import Finding
from app.schemas.review import ResearchReview


class FakeStructuredModel:
    """
    Fake LangChain model used for unit tests.
    """

    def __init__(self, response):
        self.response = response
        self.prompt = None
        self.config = None
        self.schema = None
        self.method = None

    def with_structured_output(
        self,
        schema,
        method=None,
    ):
        self.schema = schema
        self.method = method
        return self

    def invoke(self, prompt, config=None):
        self.prompt = prompt
        self.config = config
        return self.response


def make_finding():
    return Finding(
        id="finding-001",
        sub_question_id="Q1",
        claim=(
            "Zero Trust implementation requires "
            "strong identity verification."
        ),
        source_url="https://example.com/zero-trust",
        snippet=(
            "Continuous verification and identity "
            "controls are important."
        ),
        retrieved_at=datetime.now(timezone.utc),
    )


def test_review_schema_approval():
    review = ResearchReview(
        question_answered=True,
        sources_sufficient=True,
        retry_recommended=False,
        reason="The evidence addresses the question.",
        feedback="No further research required.",
    )

    assert review.approved is True


def test_review_schema_rejection():
    review = ResearchReview(
        question_answered=False,
        sources_sufficient=False,
        retry_recommended=True,
        reason="Evidence is incomplete.",
        feedback="Find more implementation examples.",
    )

    assert review.approved is False


def test_build_review_payload():
    payload = build_review_payload(
        question="What is Zero Trust?",
        findings=[make_finding()],
    )

    assert payload["question"] == "What is Zero Trust?"
    assert payload["findings_count"] == 1
    assert len(payload["findings"]) == 1
    assert payload["truncated"] is False


def test_reviewer_accepts_good_research():
    fake_model = FakeStructuredModel(
        ResearchReview(
            question_answered=True,
            sources_sufficient=True,
            retry_recommended=False,
            reason="Good evidence.",
            feedback="Proceed to writing.",
        )
    )

    result = review_research(
        question="What are Zero Trust challenges?",
        findings=[make_finding()],
        model=fake_model,
    )

    assert result.approved is True
    assert result.retry_recommended is False
    assert fake_model.schema is ResearchReview
    assert fake_model.method == "function_calling"
    assert "Zero Trust" in fake_model.prompt


def test_reviewer_requests_retry():
    fake_model = FakeStructuredModel(
        ResearchReview(
            question_answered=False,
            sources_sufficient=False,
            retry_recommended=True,
            reason="Missing practical evidence.",
            feedback="Find concrete deployment challenges.",
        )
    )

    result = review_research(
        question="What are deployment challenges?",
        findings=[make_finding()],
        model=fake_model,
    )

    assert result.approved is False
    assert result.retry_recommended is True
    assert "deployment" in result.feedback


def test_reviewer_rejects_empty_question():
    fake_model = FakeStructuredModel(
        ResearchReview(
            question_answered=True,
            sources_sufficient=True,
            retry_recommended=False,
            reason="Valid.",
            feedback="Proceed.",
        )
    )

    with pytest.raises(ValueError):
        review_research(
            question="",
            findings=[],
            model=fake_model,
        )


def test_reviewer_model_error_propagates():
    class FailingModel(FakeStructuredModel):
        def invoke(self, prompt, config=None):
            raise RuntimeError(
                "Simulated Groq failure"
            )

    fake_model = FailingModel(response=None)

    with pytest.raises(
        RuntimeError,
        match="Simulated Groq failure",
    ):
        review_research(
            question="What is Zero Trust?",
            findings=[make_finding()],
            model=fake_model,
        )
