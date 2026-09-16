"""
Simulates the 'killed process resumes' requirement: save state mid-run,
reload it as if from a fresh process, assert completed work isn't repeated.
"""
import pytest
from app.schemas.state import GraphState
from app.schemas.plan import Plan, SubQuestion
from app.schemas.finding import Finding


@pytest.mark.asyncio
async def test_reload_preserves_completed_sub_questions(monkeypatch):
    import fakeredis.aioredis
    from app.persistence import redis_client, checkpoint

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_client, "get_redis", lambda: fake)

    plan = Plan(original_question="q", sub_questions=[
        SubQuestion(id="sq1", question="a", priority=1),
        SubQuestion(id="sq2", question="b", priority=2),
    ])
    finding = Finding(claim="x", source_url="https://a.com", snippet="s",
                       retrieved_at="2026-01-01T00:00:00Z", sub_question_id="sq1")
    state = GraphState(run_id="killed-run", original_question="q", plan=plan,
                        completed_sq_ids=["sq1"], findings=[finding])

    await checkpoint.save_state(state)  # simulates checkpoint before crash

    # "process restarts" — fresh load, no in-memory state carried over
    reloaded = await checkpoint.load_state("killed-run")

    assert reloaded is not None
    assert reloaded.completed_sq_ids == ["sq1"]
    remaining = [sq for sq in reloaded.plan.sub_questions if sq.id not in reloaded.completed_sq_ids]
    assert [sq.id for sq in remaining] == ["sq2"]  # only sq2 left — sq1 not replayed
