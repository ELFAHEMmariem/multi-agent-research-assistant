"""
GraphState persistence — the difference between a demo and a service.
Written after every node. load_state is what makes a crashed/redeployed
process resume instead of replaying from scratch.
"""
from app.persistence.redis_client import get_redis
from app.schemas.state import GraphState

TTL_SECONDS = 86400  # 24h
KEY_PREFIX = "run:"


async def save_state(state: GraphState) -> None:
    r = get_redis()
    await r.set(f"{KEY_PREFIX}{state.run_id}", state.model_dump_json(), ex=TTL_SECONDS)


async def load_state(run_id: str) -> GraphState | None:
    r = get_redis()
    raw = await r.get(f"{KEY_PREFIX}{run_id}")
    if raw is None:
        return None
    return GraphState.model_validate_json(raw)
