"""
Supervisor routing decisions. Pure functions over GraphState -> next node name.
The reviewer sends work back exactly once per sub-question — unlimited
revision loops are how a run quietly costs twelve dollars.
"""
from app.schemas.state import GraphState
from app.schemas.finding import ResearchResult

MAX_REVISIONS = 1


def review_research(state: GraphState, result: ResearchResult) -> str:
    """Returns: 'accept' | 'revise' | 'skip'"""
    sq_id = result.sub_question_id
    revisions_so_far = state.revision_count.get(sq_id, 0)

    if result.status in ("rate_limited", "paywalled", "timed_out"):
        if revisions_so_far >= MAX_REVISIONS:
            return "skip"  # give up on this sub-question, don't stall the run
        return "revise"

    if result.status == "no_results" or len(result.findings) == 0:
        if revisions_so_far >= MAX_REVISIONS:
            return "skip"
        return "revise"

    if len(result.findings) < 2 and revisions_so_far < MAX_REVISIONS:
        return "revise"

    return "accept"


def next_sub_question_or_write(state: GraphState) -> str:
    """Returns: 'research_next' | 'write'"""
    if not state.plan:
        return "write"
    remaining = [sq for sq in state.plan.sub_questions if sq.id not in state.completed_sq_ids]
    return "research_next" if remaining else "write"
