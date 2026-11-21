"""
Tests for the Redis-synchronized Supervisor.

No real Groq or Redis requests.
"""

import importlib

from app.graph.budgets import BudgetLimits
from app.graph.token_budget_sync import (
    TokenBudgetSnapshot,
    TokenBudgetUnavailable,
)


module = importlib.import_module(
    "app.graph.budgeted_supervisor"
)


def make_state(tokens=0):
    return {
        "run_id": "test-budgeted-supervisor",
        "question": "Explain Zero Trust.",
        "started_at": 0.0,
        "total_tokens": tokens,
    }


def snapshot(consumed):
    maximum = 15000

    return TokenBudgetSnapshot(
        consumed_tokens=consumed,
        remaining_tokens=max(
            0,
            maximum - consumed,
        ),
        max_total_tokens=maximum,
        exhausted=consumed >= maximum,
    )


def limits():
    return BudgetLimits(
        max_total_tokens=15000
    )


def test_normal_execution(monkeypatch):
    calls = []

    monkeypatch.setattr(
        module,
        "read_token_budget",
        lambda **kwargs: snapshot(1000),
    )

    def fake_supervisor(
        state,
        limits,
        reviewer_fn,
    ):
        calls.append(state)

        return {
            "next_action": "research",
            "status": "researching",
        }

    monkeypatch.setattr(
        module,
        "supervisor_node",
        fake_supervisor,
    )

    result = module.budgeted_supervisor_node(
        make_state(),
        limits(),
    )

    assert result["next_action"] == "research"
    assert result["total_tokens"] == 1000
    assert len(calls) == 1


def test_exhausted_budget_blocks_groq(monkeypatch):
    calls = []

    monkeypatch.setattr(
        module,
        "read_token_budget",
        lambda **kwargs: snapshot(15000),
    )

    monkeypatch.setattr(
        module,
        "supervisor_node",
        lambda **kwargs: calls.append(kwargs),
    )

    result = module.budgeted_supervisor_node(
        make_state(),
        limits(),
    )

    assert result["next_action"] == "stop"
    assert result["status"] == "stopped"
    assert calls == []


def test_exhaustion_after_review(monkeypatch):
    readings = iter([
        snapshot(14500),
        snapshot(15300),
    ])

    monkeypatch.setattr(
        module,
        "read_token_budget",
        lambda **kwargs: next(readings),
    )

    monkeypatch.setattr(
        module,
        "supervisor_node",
        lambda **kwargs: {
            "next_action": "research",
            "status": "retrying",
        },
    )

    result = module.budgeted_supervisor_node(
        make_state(),
        limits(),
    )

    assert result["next_action"] == "stop"
    assert result["total_tokens"] == 15300


def test_unavailable_redis_stops(monkeypatch):
    def failing_reader(**kwargs):
        raise TokenBudgetUnavailable(
            "Redis unavailable"
        )

    monkeypatch.setattr(
        module,
        "read_token_budget",
        failing_reader,
    )

    result = module.budgeted_supervisor_node(
        make_state(500),
        limits(),
    )

    assert result["next_action"] == "stop"
    assert result["total_tokens"] == 500


def test_existing_decision_preserved(monkeypatch):
    monkeypatch.setattr(
        module,
        "read_token_budget",
        lambda **kwargs: snapshot(3000),
    )

    monkeypatch.setattr(
        module,
        "supervisor_node",
        lambda **kwargs: {
            "next_action": "stop",
            "status": "stopped",
            "stop_reason": "Time budget exceeded",
        },
    )

    result = module.budgeted_supervisor_node(
        make_state(),
        limits(),
    )

    assert result["next_action"] == "stop"
    assert result["stop_reason"] == (
        "Time budget exceeded"
    )
    assert result["total_tokens"] == 3000
