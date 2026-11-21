
from typing import Literal

from pydantic import BaseModel, Field


RunStatus = Literal[
    "queued",
    "running",
    "completed",
    "stopped",
    "failed",
    "interrupted",
]


class ResearchRequest(BaseModel):
    question: str = Field(
        min_length=10,
        max_length=2000,
    )


class ResearchCreated(BaseModel):
    run_id: str
    status: RunStatus


class ResearchStatusResponse(BaseModel):
    run_id: str
    status: RunStatus
    question: str
    error: str | None = None


class ResearchReportResponse(BaseModel):
    run_id: str
    status: RunStatus
    report: dict


class CitationItem(BaseModel):
    claim_number: int
    claim_text: str
    finding_id: str
    source_url: str | None = None
    snippet: str | None = None
    reference_valid: bool
    support_verified: bool = False
    reason: str


class CitationResponse(BaseModel):
    run_id: str
    total_references: int
    valid_references: int
    invalid_references: int
    citations: list[CitationItem]
