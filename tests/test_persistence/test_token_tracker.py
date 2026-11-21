
import uuid
from types import SimpleNamespace

from app.persistence.token_tracker import (
    GroqTokenTracker,
    get_token_usage,
)


def create_fake_response(
    input_tokens=100,
    output_tokens=50,
):
    message = SimpleNamespace(
        usage_metadata={
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": (
                input_tokens + output_tokens
            ),
        }
    )

    generation = SimpleNamespace(
        message=message
    )

    return SimpleNamespace(
        generations=[[generation]],
        llm_output={},
    )


def test_token_tracking():

    run_id = str(uuid.uuid4())
    tracker = GroqTokenTracker(run_id)

    tracker.on_llm_end(
        create_fake_response(100, 50)
    )

    usage = get_token_usage(run_id)

    assert usage["input_tokens"] == 100
    assert usage["output_tokens"] == 50
    assert usage["total_tokens"] == 150


def test_token_accumulation():

    run_id = str(uuid.uuid4())
    tracker = GroqTokenTracker(run_id)

    tracker.on_llm_end(
        create_fake_response(100, 50)
    )

    tracker.on_llm_end(
        create_fake_response(200, 100)
    )

    usage = get_token_usage(run_id)

    assert usage["input_tokens"] == 300
    assert usage["output_tokens"] == 150
    assert usage["total_tokens"] == 450


def test_separate_runs():

    run_id_1 = str(uuid.uuid4())
    run_id_2 = str(uuid.uuid4())

    tracker = GroqTokenTracker(run_id_1)

    tracker.on_llm_end(
        create_fake_response(100, 50)
    )

    usage_1 = get_token_usage(run_id_1)
    usage_2 = get_token_usage(run_id_2)

    assert usage_1["total_tokens"] == 150
    assert usage_2["total_tokens"] == 0
