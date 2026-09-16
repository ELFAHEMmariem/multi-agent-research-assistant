"""
Append-only step log per run — separate from checkpoint.py (mutable
current state) because trace is history, not state: different access
pattern (Redis list, not string), never overwritten.
"""
import json
from app.persistence.redis_client import get_redis
from app.schemas.state import TraceEvent

TTL_SECONDS = 86400
KEY_PREFIX = "trace:"


async def append_trace(run_id: str, event: TraceEvent) -> None:
    r = get_redis()
    key = f"{KEY_PREFIX}{run_id}"
    await r.rpush(key, event.model_dump_json())
    await r.expire(key, TTL_SECONDS)


async def get_trace(run_id: str) -> list[dict]:
    r = get_redis()
    raw_events = await r.lrange(f"{KEY_PREFIX}{run_id}", 0, -1)
    return [json.loads(e) for e in raw_events]
