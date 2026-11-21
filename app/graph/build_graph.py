
"""
LangGraph workflow builder.

Architecture:

START
  |
  v
Planner
  |
  v
Researcher <---------+
  |                  |
  v                  |
Supervisor ----------+
  |
  +--> Writer --> END
  |
  +--> END

The Supervisor can optionally use Groq
to review the quality of research findings.
"""

from functools import partial

from langgraph.graph import (
    START,
    END,
    StateGraph,
)

from app.agents.reviewer import review_research

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


def route_after_supervisor(
    state: ResearchState,
) -> str:
    """
    Select the next graph node based
    on the Supervisor's decision.
    """

    action = state.get(
        "next_action",
        "stop",
    )

    if action == "research":
        return "research"

    if action == "write":
        return "write"

    return "stop"


from app.graph.budgeted_supervisor import budgeted_supervisor_node

def build_graph(
    planner_fn: PlannerFn,
    researcher_fn: ResearcherFn,
    writer_fn: WriterFn,
    limits: BudgetLimits | None = None,
    checkpointer=None,
    use_cache: bool = False,
    use_llm_review: bool = False,
):
    """
    Build the research workflow.

    Args:
        planner_fn:
            Planner implementation.

        researcher_fn:
            Researcher implementation.

        writer_fn:
            Writer implementation.

        limits:
            Graph budget limits.

        checkpointer:
            Optional LangGraph checkpointer.

        use_cache:
            Compatibility parameter retained
            for existing callers. This flag
            does not itself enable caching;
            caching must be handled by the
            supplied Researcher or persistence layer.

        use_llm_review:
            Enable Groq research quality review.

    Returns:
        Compiled LangGraph workflow.
    """

    if limits is None:
        limits = BudgetLimits()

    # The optional Reviewer is injected
    # into the Supervisor.
    reviewer_fn = (
        review_research
        if use_llm_review
        else None
    )

    builder = StateGraph(
        ResearchState
    )

    # ======================================
    # 1. REGISTER PLANNER
    # ======================================

    builder.add_node(
        "planner",
        make_planner_node(
            planner_fn
        ),
    )

    # ======================================
    # 2. REGISTER RESEARCHER
    # ======================================

    # Important:
    # make_researcher_node accepts only
    # researcher_fn in the current project.
    builder.add_node(
        "researcher",
        make_researcher_node(
            researcher_fn
        ),
    )

    # ======================================
    # 3. REGISTER SUPERVISOR
    # ======================================

    builder.add_node(
        "supervisor",
        partial(budgeted_supervisor_node,
            limits=limits,
            reviewer_fn=reviewer_fn,
        ),
    )

    # ======================================
    # 4. REGISTER WRITER
    # ======================================

    builder.add_node(
        "writer",
        make_writer_node(
            writer_fn
        ),
    )

    # ======================================
    # 5. GRAPH EDGES
    # ======================================

    builder.add_edge(
        START,
        "planner",
    )

    builder.add_edge(
        "planner",
        "researcher",
    )

    builder.add_edge(
        "researcher",
        "supervisor",
    )

    # ======================================
    # 6. CONDITIONAL ROUTING
    # ======================================

    builder.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "research": "researcher",
            "write": "writer",
            "stop": END,
        },
    )

    # ======================================
    # 7. WRITER TO END
    # ======================================

    builder.add_edge(
        "writer",
        END,
    )

    # ======================================
    # 8. COMPILE WORKFLOW
    # ======================================

    return builder.compile(
        checkpointer=checkpointer,
    )
