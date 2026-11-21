
"""
Service layer for retrieving research execution traces.

This module connects the Redis Trace Store
to the FastAPI response schema.
"""

from app.persistence.trace_store import (
    get_run_traces,
    get_trace_summary,
)

from app.schemas.trace import TraceResponse


def get_research_trace(run_id: str) -> TraceResponse:
    """
    Retrieve the complete execution trace
    for a research run.

    Args:
        run_id: Unique identifier of the research run.

    Returns:
        TraceResponse containing:
        - Run identifier
        - Trace summary
        - Ordered agent execution traces

    Raises:
        ValueError: If run_id is empty.
        RedisError: If Redis cannot be accessed.
    """

    if not run_id or not run_id.strip():
        raise ValueError(
            "run_id cannot be empty"
        )

    steps = get_run_traces(run_id)

    summary = get_trace_summary(run_id)

    return TraceResponse(
        run_id=run_id,
        summary=summary,
        steps=steps,
    )
