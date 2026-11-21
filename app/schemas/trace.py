
"""
Pydantic schemas for step-level agent tracing.

Each TraceEvent represents one execution
of a node in the LangGraph workflow.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


TraceStatus = Literal[
    "running",
    "success",
    "failed",
    "interrupted",
]


class TokenUsage(BaseModel):
    """Token consumption for one agent step."""

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_total(self):
        expected = (
            self.input_tokens + self.output_tokens
        )

        if self.total_tokens < expected:
            raise ValueError(
                "total_tokens cannot be smaller "
                "than input_tokens + output_tokens"
            )

        return self


class TraceEvent(BaseModel):
    """
    Information recorded during one
    LangGraph agent execution.
    """

    run_id: str = Field(min_length=1)

    step_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    agent: str = Field(min_length=1)

    status: TraceStatus

    input_data: dict[str, Any] = Field(
        default_factory=dict
    )

    output_data: dict[str, Any] = Field(
        default_factory=dict
    )

    tools_called: list[str] = Field(
        default_factory=list
    )

    tokens: TokenUsage = Field(
        default_factory=TokenUsage
    )

    started_at: datetime = Field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    completed_at: datetime | None = None

    latency_ms: float | None = Field(
        default=None,
        ge=0,
    )

    error: str | None = None

    @model_validator(mode="after")
    def validate_timestamps(self):
        if (
            self.completed_at is not None
            and self.completed_at < self.started_at
        ):
            raise ValueError(
                "completed_at cannot be earlier "
                "than started_at"
            )

        return self


class TraceSummary(BaseModel):
    """Aggregated statistics for a research run."""

    run_id: str

    total_steps: int = Field(default=0, ge=0)

    successful_steps: int = Field(default=0, ge=0)

    failed_steps: int = Field(default=0, ge=0)

    total_input_tokens: int = Field(
        default=0,
        ge=0,
    )

    total_output_tokens: int = Field(
        default=0,
        ge=0,
    )

    total_tokens: int = Field(
        default=0,
        ge=0,
    )


class TraceResponse(BaseModel):
    """Response returned by the FastAPI trace endpoint."""

    run_id: str

    summary: TraceSummary

    steps: list[TraceEvent] = Field(
        default_factory=list
    )
