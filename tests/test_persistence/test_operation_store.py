
import uuid

from app.persistence.operation_store import (
    get_cached_result,
    save_completed_result,
)

from app.schemas.finding import ResearchResult


def create_result(status="success"):

    return ResearchResult(
        sub_question_id="Q1",
        status=status,
        findings=[],
    )


def test_save_and_retrieve():

    run_id = str(uuid.uuid4())

    result = create_result()

    save_completed_result(
        run_id,
        "Q1",
        1,
        result,
    )

    cached = get_cached_result(
        run_id,
        "Q1",
        1,
    )

    assert cached is not None
    assert cached.status == "success"


def test_different_attempt():

    run_id = str(uuid.uuid4())

    save_completed_result(
        run_id,
        "Q1",
        1,
        create_result(),
    )

    cached = get_cached_result(
        run_id,
        "Q1",
        2,
    )

    assert cached is None


def test_cache_not_overwritten():

    run_id = str(uuid.uuid4())

    original = create_result()

    save_completed_result(
        run_id,
        "Q1",
        1,
        original,
    )

    save_completed_result(
        run_id,
        "Q1",
        1,
        original,
    )

    cached = get_cached_result(
        run_id,
        "Q1",
        1,
    )

    assert cached.status == "success"
