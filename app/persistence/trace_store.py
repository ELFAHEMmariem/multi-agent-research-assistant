
"""
Redis storage for step-level agent traces.

Each research run owns a Redis list containing
its trace events in insertion order.
"""

from __future__ import annotations

import json
from typing import Any

from redis import Redis

from app.persistence.redis_client import get_redis_client
from app.schemas.trace import (
    TraceEvent,
    TraceSummary,
)


TRACE_PREFIX = "research:trace:"
TRACE_TTL_SECONDS = 7 * 24 * 60 * 60


def trace_key(run_id: str) -> str:
    """
    Return the Redis key used to store
    the traces of a research run.
    """

    if not run_id or not run_id.strip():
        raise ValueError("run_id cannot be empty")

    return f"{TRACE_PREFIX}{run_id}"


def _get_client(
    redis_client: Redis | None = None,
) -> Redis:
    """
    Use an injected Redis client when provided.

    Otherwise use the project's existing
    Redis connection helper.
    """

    if redis_client is not None:
        return redis_client

    return get_redis_client()


def record_trace(
    trace: TraceEvent,
    redis_client: Redis | None = None,
) -> None:
    """
    Save one trace event into Redis.

    Events are appended to a Redis list so
    their insertion order is preserved.

    Refresh the expiration time whenever
    a new event is recorded.
    """

    client = _get_client(redis_client)

    key = trace_key(trace.run_id)

    payload = trace.model_dump_json()

    with client.pipeline(transaction=True) as pipe:
        pipe.rpush(key, payload)
        pipe.expire(key, TRACE_TTL_SECONDS)
        pipe.execute()


def get_run_traces(
    run_id: str,
    redis_client: Redis | None = None,
) -> list[TraceEvent]:
    """
    Retrieve all trace events belonging
    to a research run.

    Return an empty list when the run
    has no stored traces.
    """

    client = _get_client(redis_client)

    key = trace_key(run_id)

    raw_events = client.lrange(key, 0, -1)

    traces: list[TraceEvent] = []

    for raw_event in raw_events:
        if isinstance(raw_event, bytes):
            raw_event = raw_event.decode("utf-8")

        event = TraceEvent.model_validate_json(
            raw_event
        )

        traces.append(event)

    return traces


def get_trace_summary(
    run_id: str,
    redis_client: Redis | None = None,
) -> TraceSummary:
    """
    Calculate aggregate statistics from
    all trace events of one research run.
    """

    traces = get_run_traces(
        run_id=run_id,
        redis_client=redis_client,
    )

    successful_steps = sum(
        trace.status == "success"
        for trace in traces
    )

    failed_steps = sum(
        trace.status == "failed"
        for trace in traces
    )

    total_input_tokens = sum(
        trace.tokens.input_tokens
        for trace in traces
    )

    total_output_tokens = sum(
        trace.tokens.output_tokens
        for trace in traces
    )

    total_tokens = sum(
        trace.tokens.total_tokens
        for trace in traces
    )

    return TraceSummary(
        run_id=run_id,
        total_steps=len(traces),
        successful_steps=successful_steps,
        failed_steps=failed_steps,
        total_input_tokens=total_input_tokens,
        total_output_tokens=total_output_tokens,
        total_tokens=total_tokens,
    )


def get_trace_data(
    run_id: str,
    redis_client: Redis | None = None,
) -> dict[str, Any]:
    """
    Return a serializable representation
    containing the summary and all steps.
    """

    traces = get_run_traces(
        run_id=run_id,
        redis_client=redis_client,
    )

    summary = TraceSummary(
        run_id=run_id,
        total_steps=len(traces),
        successful_steps=sum(
            trace.status == "success"
            for trace in traces
        ),
        failed_steps=sum(
            trace.status == "failed"
            for trace in traces
        ),
        total_input_tokens=sum(
            trace.tokens.input_tokens
            for trace in traces
        ),
        total_output_tokens=sum(
            trace.tokens.output_tokens
            for trace in traces
        ),
        total_tokens=sum(
            trace.tokens.total_tokens
            for trace in traces
        ),
    )

    return {
        "run_id": run_id,
        "summary": summary.model_dump(
            mode="json"
        ),
        "steps": [
            trace.model_dump(mode="json")
            for trace in traces
        ],
    }
