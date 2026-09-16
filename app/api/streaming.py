"""
SSE progress stream so the client isn't a four-minute spinner.
Polls the checkpoint; swap for Redis pub/sub if you need push instead
of poll at higher run volume.
"""
import asyncio
import json
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse
from app.persistence.checkpoint import load_state

router = APIRouter()


@router.get("/research/{run_id}/stream")
async def stream_progress(run_id: str):
    async def event_generator():
        last_status = None
        while True:
            state = await load_state(run_id)
            if state is None:
                yield {"event": "error", "data": "run not found"}
                return
            if state.status != last_status:
                yield {"event": "status", "data": json.dumps({
                    "status": state.status,
                    "completed_sub_questions": len(state.completed_sq_ids),
                    "total_sub_questions": len(state.plan.sub_questions) if state.plan else None,
                })}
                last_status = state.status
            if state.status in ("done", "failed"):
                return
            await asyncio.sleep(1.5)

    return EventSourceResponse(event_generator())
