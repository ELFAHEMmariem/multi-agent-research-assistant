from app.graph.supervisor import review_research, next_sub_question_or_write
from app.schemas.state import GraphState
from app.schemas.plan import Plan, SubQuestion
from app.schemas.finding import ResearchResult, Finding


def _finding(sq_id="sq1"):
    return Finding(claim="x", source_url="https://a.com", snippet="s",
                    retrieved_at="2026-01-01T00:00:00Z", sub_question_id=sq_id)


def test_revises_once_then_skips_on_repeated_failure():
    state = GraphState(run_id="r1", original_question="q")
    result = ResearchResult(sub_question_id="sq1", findings=[], status="no_results")

    first = review_research(state, result)
    assert first == "revise"

    state.revision_count["sq1"] = 1
    second = review_research(state, result)
    assert second == "skip"  # never a third attempt — no unlimited loops


def test_accepts_with_enough_findings():
    state = GraphState(run_id="r1", original_question="q")
    result = ResearchResult(sub_question_id="sq1", findings=[_finding(), _finding()], status="complete")
    assert review_research(state, result) == "accept"


def test_routes_to_write_when_all_sub_questions_done():
    plan = Plan(original_question="q", sub_questions=[SubQuestion(id="sq1", question="a", priority=1)])
    state = GraphState(run_id="r1", original_question="q", plan=plan, completed_sq_ids=["sq1"])
    assert next_sub_question_or_write(state) == "write"


def test_routes_to_research_when_sub_questions_remain():
    plan = Plan(original_question="q", sub_questions=[
        SubQuestion(id="sq1", question="a", priority=1),
        SubQuestion(id="sq2", question="b", priority=2),
    ])
    state = GraphState(run_id="r1", original_question="q", plan=plan, completed_sq_ids=["sq1"])
    assert next_sub_question_or_write(state) == "research_next"
