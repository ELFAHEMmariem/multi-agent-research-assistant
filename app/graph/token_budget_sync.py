"""
Synchronize Groq token usage with LangGraph state.

Redis contains cumulative token usage recorded by
GroqTokenTracker.

The effective consumption is the maximum of:
- the token count stored in ResearchState
- the cumulative token count stored in Redis

This prevents stale state values from underestimating
token consumption.

No Redis writes are performed.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.persistence.token_tracker import get_token_usage
from app.schemas.state import ResearchState


class TokenBudgetUnavailable(RuntimeError):
    """Token counters could not be read reliably."""


@dataclass(frozen=True)
class TokenBudgetSnapshot:
    consumed_tokens: int
    remaining_tokens: int
    max_total_tokens: int
    exhausted: bool


def _nonnegative_int(value: Any) -> int:
    """Convert a token counter to a nonnegative integer."""

    try:
        return max(0, int(value))
    except (TypeError, ValueError, OverflowError):
        return 0


def read_token_budget(
    state: ResearchState,
    max_total_tokens: int,
    usage_reader: Callable[[str], dict] | None = None,
) -> TokenBudgetSnapshot:
    """
    Read the effective token budget.

    Raises:
        ValueError: Invalid configured budget.
        TokenBudgetUnavailable: Redis cannot be read.
    """

    if max_total_tokens <= 0:
        raise ValueError(
            "max_total_tokens must be positive"
        )

    state_tokens = _nonnegative_int(
        state.get("total_tokens", 0)
    )

    run_id = state.get("run_id") or ""
    redis_tokens = 0

    if run_id:
        reader = usage_reader or get_token_usage

        try:
            usage = reader(run_id)

            if not isinstance(usage, dict):
                raise TypeError(
                    "Token usage must be a dictionary"
                )

            redis_tokens = _nonnegative_int(
                usage.get("total_tokens", 0)
            )

        except Exception as exc:
            raise TokenBudgetUnavailable(
                f"Cannot read token usage for run {run_id}"
            ) from exc

    consumed = max(
        state_tokens,
        redis_tokens,
    )

    remaining = max(
        0,
        max_total_tokens - consumed,
    )

    return TokenBudgetSnapshot(
        consumed_tokens=consumed,
        remaining_tokens=remaining,
        max_total_tokens=max_total_tokens,
        exhausted=consumed >= max_total_tokens,
    )


def synchronized_state_update(
    snapshot: TokenBudgetSnapshot,
) -> dict[str, int]:
    """
    Return an update compatible with ResearchState.

    LangGraph can persist this value in a checkpoint.
    """

    return {
        "total_tokens": snapshot.consumed_tokens
    }
