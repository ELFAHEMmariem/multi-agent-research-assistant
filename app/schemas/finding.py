
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


ResearchStatus = Literal[
    "success",
    "no_results",
    "rate_limited",
    "timeout",
    "extraction_failed",
    "error",
]


class Finding(BaseModel):
    id: str
    sub_question_id: str
    claim: str = Field(min_length=1)
    source_url: HttpUrl
    snippet: str
    retrieved_at: datetime


class ResearchResult(BaseModel):
    sub_question_id: str
    status: ResearchStatus

    findings: list[Finding] = Field(
        default_factory=list
    )

    error_message: str | None = None
