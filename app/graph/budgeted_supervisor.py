"""
Redis-synchronized token budget for the Supervisor.

The wrapper checks cumulative Groq token usage
before and after the existing Supervisor node.

Existing review, retry and tracing logic remains
inside supervisor_node.
"""

import logging
from collections.abc import Callable

from app.graph.budgets import BudgetLimits
from app.graph.supervisor import supervisor_node
from app.graph.token_budget_sync import (
    TokenBudgetUnavailable,
    read_token_budget,
)
from app.schemas.state import ResearchState


logger = logging.getLogger(__name__)


def _stop(
    reason: str,
    tokens: int,
) -> dict:
    """Return a budget-related stop decision."""

    return {
        "next_action": "stop",
        "status": "stopped",
        "stop_reason": reason,
        "total_tokens": tokens,
    }


def budgeted_supervisor_node(
    state: ResearchState,
    limits: BudgetLimits,
    reviewer_fn: Callable | None = None,
) -> dict:
    """
    Run the existing Supervisor with token checks.

    Steps:
    1. Synchronize cumulative token usage.
    2. Refuse new work if the budget is exhausted.
    3. Execute the existing Supervisor.
    4. Synchronize tokens again.
    5. Prevent further work if the budget is exceeded.
    """

    state_tokens = max(
        0,
        int(state.get("total_tokens") or 0),
    )

    try:
        before = read_token_budget(
            state=state,
            max_total_tokens=limits.max_total_tokens,
        )

    except TokenBudgetUnavailable:
        logger.exception(
            "Token budget unavailable before review"
        )

        return _stop(
            "Token budget unavailable",
            state_tokens,
        )

    if before.exhausted:
        return _stop(
            "Token budget exceeded",
            before.consumed_tokens,
        )

    synchronized_state = {
        **state,
        "total_tokens": before.consumed_tokens,
    }

    decision = supervisor_node(
        state=synchronized_state,
        limits=limits,
        reviewer_fn=reviewer_fn,
    )

    try:
        after = read_token_budget(
            state=synchronized_state,
            max_total_tokens=limits.max_total_tokens,
        )

    except TokenBudgetUnavailable:
        logger.exception(
            "Token budget unavailable after review"
        )

        return {
            **decision,
            **_stop(
                "Token budget unavailable after review",
                before.consumed_tokens,
            ),
        }

    result = {
        **decision,
        "total_tokens": after.consumed_tokens,
    }

    if after.exhausted:
        result.update(
            {
                "next_action": "stop",
                "status": "stopped",
                "stop_reason": (
                    "Token budget exceeded after review"
                ),
            }
        )

    return result
