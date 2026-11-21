
from app.persistence.redis_client import (
    get_redis_client,
)

from app.schemas.finding import ResearchResult


CACHE_TTL_SECONDS = 86400


def operation_key(
    run_id: str,
    question_id: str,
    attempt: int,
) -> str:

    return (
        f"research:operation:{run_id}:"
        f"{question_id}:attempt{attempt}"
    )


def get_cached_result(
    run_id: str,
    question_id: str,
    attempt: int,
) -> ResearchResult | None:

    client = get_redis_client()

    try:
        key = operation_key(
            run_id,
            question_id,
            attempt,
        )

        cached_data = client.get(key)

        if cached_data is None:
            return None

        return ResearchResult.model_validate_json(
            cached_data
        )

    finally:
        client.close()


def save_completed_result(
    run_id: str,
    question_id: str,
    attempt: int,
    result: ResearchResult,
) -> bool:

    if result.status != "success":
        return False

    client = get_redis_client()

    try:
        key = operation_key(
            run_id,
            question_id,
            attempt,
        )

        payload = result.model_dump_json()

        saved = client.set(
            key,
            payload,
            nx=True,
            ex=CACHE_TTL_SECONDS,
        )

        return bool(saved)

    finally:
        client.close()
