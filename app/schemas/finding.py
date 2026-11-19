
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class Finding(BaseModel):
    id: str
    sub_question_id: str

    claim: str = Field(min_length=1)
    source_url: HttpUrl
    snippet: str
    retrieved_at: datetime


class ResearchResult(BaseModel):
    sub_question_id: str

    status: Literal[
        "success",
        "no_results",
        "rate_limited",
        "timeout",
        "error"
    ]

    findings: list[Finding] = Field(
        default_factory=list
    )
