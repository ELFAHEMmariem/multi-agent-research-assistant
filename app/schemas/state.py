from typing import Literal
from pydantic import BaseModel, Field
from app.schemas.plan import Plan
from app.schemas.finding import Finding
from app.schemas.report import Report

RunStatus = Literal["planning", "researching", "writing", "done", "failed"]


class TraceEvent(BaseModel):
    node: str
    input_summary: str
    output_summary: str
    tools_called: list[str] = Field(default_factory=list)
    tokens: int = 0
    latency_ms: int = 0
    timestamp: str


class GraphState(BaseModel):
    run_id: str
    original_question: str
    status: RunStatus = "planning"

    plan: Plan | None = None
    completed_sq_ids: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    revision_count: dict[str, int] = Field(default_factory=dict)

    # Budget counters — checked against app.config.settings in graph/budgets.py
    token_spend: int = 0
    search_count: int = 0
    started_at: str | None = None

    report: Report | None = None
    error: str | None = None
