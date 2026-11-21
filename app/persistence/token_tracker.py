
"""
Track Groq token consumption in Redis.

Supports:
- Global token usage per research run
- Token usage per agent
- Token usage per individual step
"""

from langchain_core.callbacks import BaseCallbackHandler

from app.persistence.redis_client import get_redis_client


TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60


def token_key(run_id: str) -> str:
    """Redis key for global run token usage."""
    return f"research:tokens:{run_id}"


def agent_token_key(
    run_id: str,
    agent: str,
) -> str:
    """Redis key for an agent's token usage."""
    return f"research:tokens:{run_id}:agent:{agent}"


def step_token_key(
    run_id: str,
    step_id: str,
) -> str:
    """Redis key for an individual step."""
    return f"research:tokens:{run_id}:step:{step_id}"


def _read_token_usage(key: str) -> dict:
    """
    Read input, output and total tokens
    from a Redis hash.
    """

    client = get_redis_client()

    try:
        values = client.hgetall(key)

        return {
            "input_tokens": int(
                values.get(
                    "input_tokens",
                    values.get(b"input_tokens", 0),
                )
            ),
            "output_tokens": int(
                values.get(
                    "output_tokens",
                    values.get(b"output_tokens", 0),
                )
            ),
            "total_tokens": int(
                values.get(
                    "total_tokens",
                    values.get(b"total_tokens", 0),
                )
            ),
        }

    finally:
        client.close()


def get_token_usage(run_id: str) -> dict:
    """
    Return cumulative token usage for
    the complete research run.
    """

    return _read_token_usage(
        token_key(run_id)
    )


def get_agent_token_usage(
    run_id: str,
    agent: str,
) -> dict:
    """
    Return cumulative token usage
    for one agent within a research run.
    """

    return _read_token_usage(
        agent_token_key(run_id, agent)
    )


def get_step_token_usage(
    run_id: str,
    step_id: str,
) -> dict:
    """
    Return token usage for one step.
    """

    return _read_token_usage(
        step_token_key(run_id, step_id)
    )


class GroqTokenTracker(BaseCallbackHandler):
    """
    Collect Groq token usage using
    LangChain callback events.

    run_id is required.

    agent and step_id are optional to
    preserve backward compatibility.
    """

    def __init__(
        self,
        run_id: str,
        agent: str | None = None,
        step_id: str | None = None,
    ):
        super().__init__()

        if not run_id or not run_id.strip():
            raise ValueError(
                "run_id cannot be empty"
            )

        self.run_id = run_id
        self.agent = agent
        self.step_id = step_id

    @staticmethod
    def _extract_usage(response) -> dict:
        """
        Extract token information from
        a LangChain LLMResult.

        Prefer message.usage_metadata.
        Fall back to llm_output.token_usage.
        """

        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        found_usage = False

        generations = getattr(
            response,
            "generations",
            [],
        ) or []

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

                if not usage:
                    continue

                found_usage = True

                current_input = int(
                    usage.get("input_tokens", 0)
                )

                current_output = int(
                    usage.get("output_tokens", 0)
                )

                current_total = int(
                    usage.get("total_tokens", 0)
                )

                if current_total <= 0:
                    current_total = (
                        current_input + current_output
                    )

                input_tokens += current_input
                output_tokens += current_output
                total_tokens += current_total

        if not found_usage:
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

        if total_tokens <= 0:
            total_tokens = (
                input_tokens + output_tokens
            )

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    def on_llm_end(self, response, **kwargs):
        """
        Called automatically when an LLM
        invocation finishes successfully.

        Update the global counter and,
        when provided, the agent and
        step counters.
        """

        usage = self._extract_usage(response)

        if usage["total_tokens"] <= 0:
            return

        keys = [
            token_key(self.run_id)
        ]

        if self.agent:
            keys.append(
                agent_token_key(
                    self.run_id,
                    self.agent,
                )
            )

        if self.step_id:
            keys.append(
                step_token_key(
                    self.run_id,
                    self.step_id,
                )
            )

        client = get_redis_client()

        try:
            with client.pipeline(
                transaction=True
            ) as pipe:

                for key in keys:
                    pipe.hincrby(
                        key,
                        "input_tokens",
                        usage["input_tokens"],
                    )

                    pipe.hincrby(
                        key,
                        "output_tokens",
                        usage["output_tokens"],
                    )

                    pipe.hincrby(
                        key,
                        "total_tokens",
                        usage["total_tokens"],
                    )

                    pipe.expire(
                        key,
                        TOKEN_TTL_SECONDS,
                    )

                pipe.execute()

        finally:
            client.close()
