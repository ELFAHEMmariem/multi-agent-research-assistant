"""
Tests for synchronized Groq token budgets.

No live Redis or Groq connection required.
"""

import pytest

from app.graph.token_budget_sync import (
    TokenBudgetUnavailable,
    read_token_budget,
    synchronized_state_update,
)


def make_state(total_tokens=0):
    return {
        "run_id": "test-budget-001",
        "question": "Explain Zero Trust architecture.",
        "started_at": 0.0,
        "total_tokens": total_tokens,
    }


def test_redis_usage_is_used_when_higher():
    state = make_state(7000)

    snapshot = read_token_budget(
        state=state,
        max_total_tokens=15000,
        usage_reader=lambda run_id: {
            "total_tokens": 12400
        },
    )

    assert snapshot.consumed_tokens == 12400
    assert snapshot.remaining_tokens == 2600
    assert snapshot.exhausted is False


def test_state_usage_is_used_when_higher():
    state = make_state(9000)

    snapshot = read_token_budget(
        state=state,
        max_total_tokens=15000,
        usage_reader=lambda run_id: {
            "total_tokens": 5000
        },
    )

    assert snapshot.consumed_tokens == 9000
    assert snapshot.remaining_tokens == 6000


def test_budget_is_exhausted_at_limit():
    state = make_state(15000)

    snapshot = read_token_budget(
        state=state,
        max_total_tokens=15000,
        usage_reader=lambda run_id: {
            "total_tokens": 15000
        },
    )

    assert snapshot.exhausted is True
    assert snapshot.remaining_tokens == 0


def test_unavailable_redis_is_reported():
    def broken_reader(run_id):
        raise ConnectionError("Redis unavailable")

    with pytest.raises(TokenBudgetUnavailable):
        read_token_budget(
            state=make_state(100),
            max_total_tokens=15000,
            usage_reader=broken_reader,
        )


def test_state_update_preserves_token_count():
    snapshot = read_token_budget(
        state=make_state(2000),
        max_total_tokens=15000,
        usage_reader=lambda run_id: {
            "total_tokens": 5000
        },
    )

    update = synchronized_state_update(snapshot)

    assert update == {
        "total_tokens": 5000
    }
