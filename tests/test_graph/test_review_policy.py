
"""
Tests for deterministic LLM review decisions.

No Groq calls.
No Redis connection.
"""

import pytest

from app.graph.review_policy import (
    ReviewAction,
    decide_review_action,
)

from app.schemas.review import ResearchReview

def make_review(
    answered: bool,
    sufficient: bool,
    retry: bool,
) -> ResearchReview:
    return ResearchReview(
        question_answered=answered,
        sources_sufficient=sufficient,
        retry_recommended=retry,
        reason="Quality evaluation completed.",
        feedback="Improve missing evidence if needed.",
    )

def test_accept_complete_research():
    review = make_review(
        answered=True,
        sufficient=True,
        retry=False,
    )

    decision = decide_review_action(
        review,
        revisions_used=0,
    )

    assert decision.action == ReviewAction.ACCEPT
    assert decision.approved is True
    assert decision.retry_allowed is False

def test_retry_incomplete_research():
    review = make_review(
        answered=False,
        sufficient=False,
        retry=True,
    )

    decision = decide_review_action(
        review,
        revisions_used=0,
    )

    assert decision.action == ReviewAction.RETRY
    assert decision.retry_allowed is True

def test_reject_after_one_revision():
    review = make_review(
        answered=False,
        sufficient=False,
        retry=True,
    )

    decision = decide_review_action(
        review,
        revisions_used=1,
        max_revisions=1,
    )

    assert decision.action == ReviewAction.REJECT
    assert decision.approved is False
    assert decision.retry_allowed is False

def test_reject_when_retry_not_recommended():
    review = make_review(
        answered=False,
        sufficient=False,
        retry=False,
    )

    decision = decide_review_action(
        review,
        revisions_used=0,
    )

    assert decision.action == ReviewAction.REJECT

def test_accept_even_if_retry_recommended():
    review = make_review(
        answered=True,
        sufficient=True,
        retry=True,
    )

    decision = decide_review_action(
        review,
        revisions_used=0,
    )

    assert decision.action == ReviewAction.ACCEPT

def test_reject_when_revisions_disabled():
    review = make_review(
        answered=False,
        sufficient=False,
        retry=True,
    )

    decision = decide_review_action(
        review,
        revisions_used=0,
        max_revisions=0,
    )

    assert decision.action == ReviewAction.REJECT

def test_negative_revision_count_rejected():
    review = make_review(
        answered=False,
        sufficient=False,
        retry=True,
    )

    with pytest.raises(ValueError):
        decide_review_action(
            review,
            revisions_used=-1,
        )

def test_feedback_preserved():
    review = make_review(
        answered=False,
        sufficient=False,
        retry=True,
    )

    decision = decide_review_action(
        review,
        revisions_used=0,
    )

    assert decision.feedback == review.feedback