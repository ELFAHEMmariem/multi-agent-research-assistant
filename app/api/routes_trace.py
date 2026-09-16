from fastapi import APIRouter, HTTPException
from app.persistence.trace_store import get_trace
from app.persistence.checkpoint import load_state

router = APIRouter()


@router.get("/research/{run_id}/trace")
async def trace(run_id: str):
    state = await load_state(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="run not found")
    events = await get_trace(run_id)
    return {"run_id": run_id, "steps": events}
