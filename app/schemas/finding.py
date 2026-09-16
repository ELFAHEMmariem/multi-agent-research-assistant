from typing import Literal
from pydantic import BaseModel

ResearchStatus = Literal["complete", "no_results", "rate_limited", "paywalled", "timed_out"]


class Finding(BaseModel):
    claim: str
    source_url: str
    snippet: str
    retrieved_at: str  # ISO 8601
    sub_question_id: str


class ResearchResult(BaseModel):
    sub_question_id: str
    findings: list[Finding]
    status: ResearchStatus
