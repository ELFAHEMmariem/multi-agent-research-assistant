
"""
Pydantic schemas for the Supervisor LLM review.

The Reviewer evaluates research quality.
The Python Supervisor remains responsible
for routing, retries and budget enforcement.
"""

from pydantic import BaseModel, Field


class ResearchReview(BaseModel):
    """
    Structured quality review of one sub-question.

    This model is returned by the Groq Reviewer.
    """

    question_answered: bool = Field(
        description=(
            "True if the findings directly answer "
            "the current sub-question."
        )
    )

    sources_sufficient: bool = Field(
        description=(
            "True if the available evidence is "
            "sufficient to support the answer."
        )
    )

    retry_recommended: bool = Field(
        description=(
            "True if another research pass would "
            "meaningfully improve the answer."
        )
    )

    reason: str = Field(
        min_length=1,
        description=(
            "Short explanation of the quality "
            "assessment based on the findings."
        ),
    )

    feedback: str = Field(
        min_length=1,
        description=(
            "Concrete guidance for improving the "
            "research if another pass is needed. "
            "Otherwise explain what is sufficient."
        ),
    )

    @property
    def approved(self) -> bool:
        """
        The findings are ready for the Writer
        only when both quality checks pass.
        """
        return (
            self.question_answered
            and self.sources_sufficient
        )
