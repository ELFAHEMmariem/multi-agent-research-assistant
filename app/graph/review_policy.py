
"""
Deterministic policy for LLM research reviews.

Groq evaluates research quality.

Python decides whether to:
- accept the research,
- request another research pass,
- reject insufficient research.

This module does not call an LLM or Redis.
"""

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.review import ResearchReview

class ReviewAction(str, Enum):
    ACCEPT = "accept"
    RETRY = "retry"
    REJECT = "reject"

class ReviewDecision(BaseModel):
    """
    Final decision derived from an LLM review.
    """

    action: ReviewAction

    reason: str = Field(
        min_length=1
    )

    feedback: str = ""

    approved: bool = False

    retry_allowed: bool = False

def decide_review_action(
    review: ResearchReview,
    revisions_used: int,
    max_revisions: int = 1,
) -> ReviewDecision:
    """
    Convert an LLM quality review into a
    deterministic decision.

    The retry limit is never delegated
    to the LLM.

    Global time and token budgets must also
    be checked by the Supervisor.
    """

    if revisions_used < 0:
        raise ValueError(
            "revisions_used cannot be negative"
        )

    if max_revisions < 0:
        raise ValueError(
            "max_revisions cannot be negative"
        )

    # The answer is sufficiently supported.
    if review.approved:
        return ReviewDecision(
            action=ReviewAction.ACCEPT,
            reason=review.reason,
            feedback=review.feedback,
            approved=True,
            retry_allowed=False,
        )

    # The findings are insufficient.
    # Only retry if the Reviewer recommends it
    # AND the allowed revision count permits it.
    retry_allowed = (
        review.retry_recommended
        and revisions_used < max_revisions
    )

    if retry_allowed:
        return ReviewDecision(
            action=ReviewAction.RETRY,
            reason=review.reason,
            feedback=review.feedback,
            approved=False,
            retry_allowed=True,
        )

    # The findings remain insufficient but
    # no additional pass is justified/allowed.
    return ReviewDecision(
        action=ReviewAction.REJECT,
        reason=review.reason,
        feedback=review.feedback,
        approved=False,
        retry_allowed=False,
    )