from pydantic import BaseModel, Field


class SubQuestion(BaseModel):
    id: str
    question: str
    priority: int = Field(ge=1, le=3)


class Plan(BaseModel):
    original_question: str
    sub_questions: list[SubQuestion]
