"""
Tests for GET /research/{run_id}/trace.

These tests mock the data layer and do not require
Groq, Tavily, or a real Redis connection.
"""

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError

from app.api import main as main_module
from app.schemas.trace import (
    TokenUsage,
    TraceEvent,
    TraceResponse,
    TraceSummary,
)


client = TestClient(main_module.app)


def fake_run():
    return {
        "status": "completed",
        "question": "What is Zero Trust?",
        "error": "",
    }


def fake_trace_response(run_id, with_step=True):
    steps = []

    if with_step:
        now = datetime.now(timezone.utc)

        steps.append(
            TraceEvent(
                run_id=run_id,
                agent="planner",
                status="success",
                input_data={
                    "question": "What is Zero Trust?"
                },
                output_data={
                    "sub_questions_count": 3
                },
                tools_called=[],
                tokens=TokenUsage(
                    input_tokens=100,
                    output_tokens=50,
                    total_tokens=150,
                ),
                started_at=now,
                completed_at=now,
                latency_ms=15.5,
            )
        )

    total_steps = len(steps)

    return TraceResponse(
        run_id=run_id,
        summary=TraceSummary(
            run_id=run_id,
            total_steps=total_steps,
            successful_steps=total_steps,
            failed_steps=0,
            total_input_tokens=100 if with_step else 0,
            total_output_tokens=50 if with_step else 0,
            total_tokens=150 if with_step else 0,
        ),
        steps=steps,
    )


def test_trace_endpoint_success(monkeypatch):
    run_id = "trace-test-001"

    monkeypatch.setattr(
        main_module,
        "get_run",
        lambda _: fake_run(),
    )

    monkeypatch.setattr(
        main_module,
        "get_research_trace",
        lambda _: fake_trace_response(run_id),
    )

    response = client.get(
        f"/research/{run_id}/trace"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["run_id"] == run_id
    assert data["summary"]["total_steps"] == 1
    assert data["summary"]["total_tokens"] == 150
    assert data["steps"][0]["agent"] == "planner"


def test_trace_unknown_run(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "get_run",
        lambda _: None,
    )

    response = client.get(
        "/research/unknown-run/trace"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Research run not found"
    )


def test_trace_without_steps(monkeypatch):
    run_id = "trace-empty-001"

    monkeypatch.setattr(
        main_module,
        "get_run",
        lambda _: fake_run(),
    )

    monkeypatch.setattr(
        main_module,
        "get_research_trace",
        lambda _: fake_trace_response(
            run_id,
            with_step=False,
        ),
    )

    response = client.get(
        f"/research/{run_id}/trace"
    )

    assert response.status_code == 200
    assert response.json()["steps"] == []
    assert response.json()["summary"]["total_steps"] == 0


def test_trace_redis_unavailable(monkeypatch):
    def raise_redis_error(_run_id):
        raise RedisConnectionError(
            "Redis connection failed"
        )

    monkeypatch.setattr(
        main_module,
        "get_run",
        raise_redis_error,
    )

    response = client.get(
        "/research/trace-error-001/trace"
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Trace storage unavailable"
    )


def test_trace_service_redis_unavailable(monkeypatch):
    monkeypatch.setattr(
        main_module,
        "get_run",
        lambda _: fake_run(),
    )

    def raise_redis_error(_run_id):
        raise RedisConnectionError(
            "Unable to read trace list"
        )

    monkeypatch.setattr(
        main_module,
        "get_research_trace",
        raise_redis_error,
    )

    response = client.get(
        "/research/trace-error-002/trace"
    )

    assert response.status_code == 503


def test_trace_endpoint_is_registered():
    registered_paths = [
        route.path
        for route in main_module.app.routes
    ]

    assert "/research/{run_id}/trace" in registered_paths
