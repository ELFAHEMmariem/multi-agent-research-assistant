
from pydantic import BaseModel, Field


class SubQuestion(BaseModel):
    id: str = Field(
        description="Unique identifier, for example Q1"
    )

    question: str = Field(
        min_length=10,
        description="Specific and searchable question"
    )


class ResearchPlan(BaseModel):
    original_question: str

    sub_questions: list[SubQuestion] = Field(
        min_length=1,
        max_length=3
    )
