
from langchain_core.callbacks import BaseCallbackHandler

from app.persistence.redis_client import get_redis_client


def token_key(run_id: str) -> str:
    return f"research:tokens:{run_id}"


def get_token_usage(run_id: str) -> dict:
    client = get_redis_client()

    try:
        values = client.hgetall(token_key(run_id))

        return {
            "input_tokens": int(
                values.get("input_tokens", 0)
            ),
            "output_tokens": int(
                values.get("output_tokens", 0)
            ),
            "total_tokens": int(
                values.get("total_tokens", 0)
            ),
        }
    finally:
        client.close()


class GroqTokenTracker(BaseCallbackHandler):
    """Collect Groq token usage in Redis."""

    def __init__(self, run_id: str):
        self.run_id = run_id

    def on_llm_end(self, response, **kwargs):
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        generations = getattr(
            response,
            "generations",
            [],
        )

        for group in generations:
            for generation in group:
                message = getattr(
                    generation,
                    "message",
                    None,
                )

                if message is None:
                    continue

                usage = getattr(
                    message,
                    "usage_metadata",
                    None,
                ) or {}

                if usage:
                    input_tokens += int(
                        usage.get("input_tokens", 0)
                    )
                    output_tokens += int(
                        usage.get("output_tokens", 0)
                    )
                    total_tokens += int(
                        usage.get("total_tokens", 0)
                    )

        if total_tokens == 0:
            llm_output = getattr(
                response,
                "llm_output",
                None,
            ) or {}

            usage = llm_output.get(
                "token_usage",
                {},
            ) or {}

            input_tokens = int(
                usage.get("prompt_tokens", 0)
            )
            output_tokens = int(
                usage.get("completion_tokens", 0)
            )
            total_tokens = int(
                usage.get("total_tokens", 0)
            )

        if total_tokens == 0:
            total_tokens = (
                input_tokens + output_tokens
            )

        if total_tokens <= 0:
            return

        client = get_redis_client()

        try:
            key = token_key(self.run_id)

            with client.pipeline() as pipe:
                pipe.hincrby(
                    key,
                    "input_tokens",
                    input_tokens,
                )
                pipe.hincrby(
                    key,
                    "output_tokens",
                    output_tokens,
                )
                pipe.hincrby(
                    key,
                    "total_tokens",
                    total_tokens,
                )
                pipe.expire(key, 86400 * 7)
                pipe.execute()

        finally:
            client.close()
