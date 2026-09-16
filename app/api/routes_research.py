import asyncio
from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.schemas.state import GraphState
from app.persistence.checkpoint import save_state, load_state
from app.graph.build_graph import run_graph
from app.validation.citation_check import validate_citations, UnverifiedCitationError

router = APIRouter()


class ResearchRequest(BaseModel):
    question: str


class ResearchStartResponse(BaseModel):
    run_id: str


class ResearchStatusResponse(BaseModel):
    run_id: str
    status: str
    report: dict | None = None
    error: str | None = None


@router.post("/research", response_model=ResearchStartResponse)
async def start_research(req: ResearchRequest):
    run_id = str(uuid4())
    initial_state = GraphState(run_id=run_id, original_question=req.question)
    await save_state(initial_state)

    asyncio.create_task(_execute(run_id, initial_state))
    return ResearchStartResponse(run_id=run_id)


async def _execute(run_id: str, state: GraphState):
    final_state = await run_graph(state)

    if final_state.report and final_state.findings:
        try:
            validate_citations(final_state.report, final_state.findings)
        except UnverifiedCitationError as e:
            final_state.status = "failed"
            final_state.error = str(e)

    await save_state(final_state)


@router.get("/research/{run_id}", response_model=ResearchStatusResponse)
async def get_status(run_id: str):
    state = await load_state(run_id)
    if state is None:
        raise HTTPException(status_code=404, detail="run not found")
    return ResearchStatusResponse(
        run_id=run_id,
        status=state.status,
        report=state.report.model_dump() if state.report else None,
        error=state.error,
    )
