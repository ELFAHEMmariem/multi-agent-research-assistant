from langgraph.graph import StateGraph, START, END

from app.graph.budgets import BudgetLimits
from app.graph.nodes import (
    PlannerFn,
    ResearcherFn,
    WriterFn,
    make_planner_node,
    make_researcher_node,
    make_writer_node,
)
from app.graph.supervisor import supervisor_node
from app.schemas.state import ResearchState


def route_after_supervisor(state: ResearchState) -> str:
    return state["next_action"]


def build_graph(
    planner_fn: PlannerFn,
    researcher_fn: ResearcherFn,
    writer_fn: WriterFn,
    limits: BudgetLimits | None = None,
    checkpointer=None,
):
    if limits is None:
        limits = BudgetLimits()

    builder = StateGraph(ResearchState)

    # Register nodes
    builder.add_node(
        "planner",
        make_planner_node(planner_fn)
    )

    builder.add_node(
        "researcher",
        make_researcher_node(researcher_fn)
    )

    builder.add_node(
        "supervisor",
        lambda state: supervisor_node(state, limits)
    )

    builder.add_node(
        "writer",
        make_writer_node(writer_fn)
    )

    # Define entry point
    builder.add_edge(START, "planner")

    # Initial workflow
    builder.add_edge("planner", "researcher")

    # Researcher always reports to Supervisor
    builder.add_edge("researcher", "supervisor")

    # Supervisor chooses next action
    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "research": "researcher",
            "write": "writer",
            "stop": END,
        }
    )

    # Final node
    builder.add_edge("writer", END)

    return builder.compile(
        checkpointer=checkpointer
    )