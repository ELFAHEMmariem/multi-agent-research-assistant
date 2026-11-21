
from app.persistence.token_tracker import (
    get_token_usage,
)


class TokenBudgetExceeded(Exception):
    """The research token budget is exhausted."""


DEFAULT_MAX_TOKENS = 12000
DEFAULT_RESERVED_TOKENS = 1500


def check_token_budget(
    run_id: str,
    max_total_tokens: int = DEFAULT_MAX_TOKENS,
    reserved_tokens: int = DEFAULT_RESERVED_TOKENS,
) -> int:

    if max_total_tokens <= 0:
        raise ValueError(
            "max_total_tokens must be positive"
        )

    if reserved_tokens < 0:
        raise ValueError(
            "reserved_tokens cannot be negative"
        )

    usage = get_token_usage(run_id)

    consumed = usage["total_tokens"]

    remaining = max_total_tokens - consumed

    if remaining < reserved_tokens:

        raise TokenBudgetExceeded(
            f"Token budget exceeded for {run_id}. "
            f"Consumed: {consumed}. "
            f"Remaining: {remaining}. "
            f"Required reserve: {reserved_tokens}."
        )

    return remaining
