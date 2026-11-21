
"""
FastAPI application for Multi-Agent Research Assistant.

Endpoints:
- GET  /health
- POST /research
- GET  /research/{run_id}
- GET  /report/{run_id}
- GET  /research/{run_id}/citations
- GET  /research/{run_id}/trace
- GET  /events/{run_id}
"""

import asyncio
import json
import logging
import uuid

from fastapi import (
    BackgroundTasks,
    FastAPI,
    HTTPException,
)
from fastapi.responses import StreamingResponse
from redis.exceptions import RedisError

from app.api.models import (
    CitationResponse,
    ResearchCreated,
    ResearchReportResponse,
    ResearchRequest,
    ResearchStatusResponse,
)

from app.api.service import (
    add_event,
    execute_research,
    get_events,
    get_research_citations,
    get_run,
    save_run,
)

from app.api.trace_service import get_research_trace
from app.persistence.redis_client import check_redis_connection
from app.schemas.trace import TraceResponse


logger = logging.getLogger(__name__)


app = FastAPI(
    title="Multi-Agent Research Assistant API",
    description=(
        "Research API powered by Groq, Tavily, "
        "LangGraph and Redis"
    ),
    version="0.4.0",
)


TERMINAL_STATUSES = {
    "completed",
    "failed",
    "stopped",
    "interrupted",
}


# ==================================================
# 1. HEALTH CHECK
# ==================================================

@app.get("/health")
def health():

    try:
        redis_ok = check_redis_connection()
    except Exception:
        redis_ok = False

    if not redis_ok:
        raise HTTPException(
            status_code=503,
            detail="Redis unavailable",
        )

    return {
        "status": "healthy",
        "redis": "connected",
    }


# ==================================================
# 2. START RESEARCH
# ==================================================

@app.post(
    "/research",
    response_model=ResearchCreated,
    status_code=202,
)
def create_research(
    request: ResearchRequest,
    background_tasks: BackgroundTasks,
):

    run_id = str(uuid.uuid4())

    try:
        save_run(
            run_id=run_id,
            question=request.question,
            status="queued",
        )

        add_event(
            run_id,
            "queued",
            "Research request accepted",
        )

    except Exception:
        logger.exception(
            "Failed to create research run"
        )
        raise HTTPException(
            status_code=503,
            detail="Research storage unavailable",
        )

    background_tasks.add_task(
        execute_research,
        run_id,
        request.question,
    )

    return ResearchCreated(
        run_id=run_id,
        status="queued",
    )


# ==================================================
# 3. GET RESEARCH STATUS
# ==================================================

@app.get(
    "/research/{run_id}",
    response_model=ResearchStatusResponse,
)
def research_status(run_id: str):

    run = get_run(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Research run not found",
        )

    return ResearchStatusResponse(
        run_id=run_id,
        status=run["status"],
        question=run["question"],
        error=run.get("error") or None,
    )


# ==================================================
# 4. GET FINAL REPORT
# ==================================================

@app.get(
    "/report/{run_id}",
    response_model=ResearchReportResponse,
)
def get_report(run_id: str):

    run = get_run(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Research run not found",
        )

    if run["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail="Research report not available yet",
        )

    report = run.get("report")

    if not isinstance(report, dict):
        raise HTTPException(
            status_code=409,
            detail="Completed run has no report",
        )

    return ResearchReportResponse(
        run_id=run_id,
        status="completed",
        report=report,
    )


# ==================================================
# 5. GET RESEARCH CITATIONS
# ==================================================

@app.get(
    "/research/{run_id}/citations",
    response_model=CitationResponse,
)
def research_citations(run_id: str):

    run = get_run(run_id)

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Research run not found",
        )

    if run["status"] != "completed":
        raise HTTPException(
            status_code=409,
            detail="Research is not completed",
        )

    try:
        result = get_research_citations(run_id)

    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="Research run not found",
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    return CitationResponse(**result)


# ==================================================
# 6. GET RESEARCH TRACE
# ==================================================

@app.get(
    "/research/{run_id}/trace",
    response_model=TraceResponse,
)
def research_trace(run_id: str):
    """
    Return step-level traces for a research run.

    A running research can have partial traces.
    An existing run without traces returns
    an empty steps list.
    """

    try:
        run = get_run(run_id)

        if run is None:
            raise HTTPException(
                status_code=404,
                detail="Research run not found",
            )

        return get_research_trace(run_id)

    except HTTPException:
        raise

    except RedisError:
        logger.exception(
            "Redis unavailable while retrieving trace"
        )
        raise HTTPException(
            status_code=503,
            detail="Trace storage unavailable",
        )

    except Exception:
        logger.exception(
            "Unexpected trace retrieval error"
        )
        raise HTTPException(
            status_code=500,
            detail="Unable to retrieve research trace",
        )


# ==================================================
# 7. STREAM RESEARCH EVENTS (SSE)
# ==================================================

@app.get("/events/{run_id}")
async def stream_events(run_id: str):

    run = await asyncio.to_thread(
        get_run,
        run_id,
    )

    if run is None:
        raise HTTPException(
            status_code=404,
            detail="Research run not found",
        )

    async def event_generator():

        next_index = 0

        while True:

            events = await asyncio.to_thread(
                get_events,
                run_id,
                next_index,
            )

            for event in events:

                data = json.dumps(
                    event,
                    ensure_ascii=False,
                )

                yield f"data: {data}\n\n"
                next_index += 1

            current = await asyncio.to_thread(
                get_run,
                run_id,
            )

            if current is None:
                break

            if current["status"] in TERMINAL_STATUSES:

                remaining = await asyncio.to_thread(
                    get_events,
                    run_id,
                    next_index,
                )

                for event in remaining:

                    data = json.dumps(
                        event,
                        ensure_ascii=False,
                    )

                    yield f"data: {data}\n\n"
                    next_index += 1

                break

            yield ": ping\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
