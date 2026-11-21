
import time

from app.graph.build_graph import build_graph
from app.schemas.finding import Finding, ResearchResult
from app.schemas.plan import ResearchPlan
from app.schemas.report import ResearchReport


def fake_planner(question):
    return ResearchPlan(
        original_question=question,
        sub_questions=[
            {
                "id": "Q1",
                "question": "What are the main cybersecurity risks?"
            },
            {
                "id": "Q2",
                "question": "How can these security risks be reduced?"
            },
        ],
    )


def fake_researcher(sub_question):
    return ResearchResult(
        sub_question_id=sub_question.id,
        status="success",
        findings=[
            Finding(
                id=f"{sub_question.id}-F001",
                sub_question_id=sub_question.id,
                claim="Example finding for testing.",
                source_url="https://example.org/test",
                snippet="This is simulated research data.",
                retrieved_at="2026-11-20T10:00:00Z",
            )
        ],
    )


def fake_writer(question, findings):
    return ResearchReport(
        title="Test Research Report",
        introduction="Test introduction.",
        claims=[
            {
                "text": "Example finding for testing.",
                "finding_ids": [findings[0].id],
            }
        ],
        conclusion="Test conclusion.",
    )


def test_complete_workflow():
    graph = build_graph(
        planner_fn=fake_planner,
        researcher_fn=fake_researcher,
        writer_fn=fake_writer,
    )

    result = graph.invoke({
        "run_id": "test-001",
        "question": "What are AI cybersecurity risks?",
        "started_at": time.time(),
    })

    assert result["status"] == "completed"
    assert len(result["findings"]) == 2
    assert result["attempts"]["Q1"] == 1
    assert result["attempts"]["Q2"] == 1
    assert result["report"]["title"] == "Test Research Report"

def test_supervisor_retries_failed_research():
    calls = {}

    def researcher_with_failure(sub_question):
        question_id = sub_question.id

        calls[question_id] = calls.get(question_id, 0) + 1

        if question_id == "Q1" and calls[question_id] == 1:
            return ResearchResult(
                sub_question_id=question_id,
                status="no_results",
                findings=[],
            )

        return fake_researcher(sub_question)

    graph = build_graph(
        planner_fn=fake_planner,
        researcher_fn=researcher_with_failure,
        writer_fn=fake_writer,
    )

    result = graph.invoke({
        "run_id": "test-retry-001",
        "question": "What are AI cybersecurity risks?",
        "started_at": time.time(),
    })

    assert result["status"] == "completed"
    assert calls["Q1"] == 2
    assert result["revisions"]["Q1"] == 1

def test_workflow_stops_when_time_budget_exceeded():
    graph = build_graph(
        planner_fn=fake_planner,
        researcher_fn=fake_researcher,
        writer_fn=fake_writer,
    )

    result = graph.invoke({
        "run_id": "test-timeout-001",
        "question": "What are AI cybersecurity risks?",
        "started_at": time.time() - 10000,
    })

    assert result["status"] == "stopped"
    assert result["next_action"] == "stop"
    assert result["stop_reason"] == "Time budget exceeded"
    assert "report" not in result
