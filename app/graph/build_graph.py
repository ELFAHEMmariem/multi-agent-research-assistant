"""
Wires nodes into a LangGraph StateGraph. Nodes are agents, edges are
supervisor routing decisions, GraphState is the single source of truth.
"""
from langgraph.graph import StateGraph, END
from app.schemas.state import GraphState
from app.graph.nodes import (
    planner_node,
    researcher_node,
    writer_node,
    route_after_planner,
    route_after_researcher,
)
from app.graph.budgets import BudgetExceeded


def build_graph():
    graph = StateGraph(GraphState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges("planner", route_after_planner, {
        "researcher": "researcher",
    })

    graph.add_conditional_edges("researcher", route_after_researcher, {
        "research_next": "researcher",
        "write": "writer",
    })

    graph.add_edge("writer", END)

    return graph.compile()


async def run_graph(state: GraphState) -> GraphState:
    compiled = build_graph()
    try:
        final_state_dict = await compiled.ainvoke(state)
        return GraphState.model_validate(final_state_dict)
    except BudgetExceeded as e:
        state.status = "failed"
        state.error = f"budget_exceeded: {e.reason}"
        return state
    except Exception as e:
        state.status = "failed"
        state.error = str(e)
        return state
