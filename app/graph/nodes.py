"""
LangGraph node functions. Each node: mutate state, checkpoint to Redis,
append a trace event. This is where persistence and tracing are wired
in — agents themselves stay pure (input -> typed output).
"""
import time
from datetime import datetime, timezone
from app.schemas.state import GraphState, TraceEvent
from app.agents.planner import plan as run_planner
from app.agents.researcher import research_sub_question
from app.agents.writer import write_report
from app.graph.supervisor import review_research, next_sub_question_or_write
from app.graph.budgets import check_all_budgets, BudgetExceeded
from app.persistence.checkpoint import save_state
from app.persistence.trace_store import append_trace
from app.config import settings


async def _trace(state: GraphState, node: str, input_summary: str, output_summary: str,
                  tools_called: list[str], started: float, tokens: int = 0):
    event = TraceEvent(
        node=node,
        input_summary=input_summary,
        output_summary=output_summary,
        tools_called=tools_called,
        tokens=tokens,
        latency_ms=int((time.monotonic() - started) * 1000),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    await append_trace(state.run_id, event)


async def planner_node(state: GraphState) -> GraphState:
    started = time.monotonic()
    state.started_at = state.started_at or datetime.now(timezone.utc).isoformat()

    result_plan = await run_planner(state.original_question)
    state.plan = result_plan
    state.status = "researching"

    await _trace(state, "planner", state.original_question,
                 f"{len(result_plan.sub_questions)} sub-questions", ["claude"], started)
    check_all_budgets(state)
    await save_state(state)
    return state


async def researcher_node(state: GraphState) -> GraphState:
    started = time.monotonic()
    remaining = [sq for sq in state.plan.sub_questions if sq.id not in state.completed_sq_ids]
    sq = remaining[0]

    # Idempotency: if this sub-question was already fully processed in a
    # previous (crashed) run, the checkpoint load in save_state/load_state
    # would already have it in completed_sq_ids and we'd never reach here.
    search_budget_remaining = settings.max_searches_per_sq - state.revision_count.get(sq.id, 0)
    result = await research_sub_question(sq, search_budget_remaining)
    state.search_count += 1

    decision = review_research(state, result)

    if decision == "revise":
        state.revision_count[sq.id] = state.revision_count.get(sq.id, 0) + 1
    else:  # accept or skip
        state.findings.extend(result.findings)
        state.completed_sq_ids.append(sq.id)

    await _trace(state, "researcher", sq.question,
                 f"status={result.status} findings={len(result.findings)} decision={decision}",
                 ["tavily", "fetch_and_extract"], started)
    check_all_budgets(state)
    await save_state(state)
    return state


async def writer_node(state: GraphState) -> GraphState:
    started = time.monotonic()
    state.status = "writing"

    report = await write_report(state.plan, state.findings)
    state.report = report
    state.status = "done"

    await _trace(state, "writer", f"{len(state.findings)} findings",
                 f"report: {report.title}", ["claude"], started)
    await save_state(state)
    return state


def route_after_planner(state: GraphState) -> str:
    return "researcher"


def route_after_researcher(state: GraphState) -> str:
    return next_sub_question_or_write(state)
