"""
Tests for the LangGraph Reviewer wiring.

These tests check graph construction and routing.
No Groq API call is performed.
"""

import importlib

from app.graph.build_graph import (
    route_after_supervisor,
)


graph_module = importlib.import_module(
    "app.graph.build_graph"
)


def fake_planner(question):
    raise AssertionError(
        "Planner should not execute during graph compilation"
    )


def fake_researcher(question):
    raise AssertionError(
        "Researcher should not execute during graph compilation"
    )


def fake_writer(question, findings):
    raise AssertionError(
        "Writer should not execute during graph compilation"
    )


def test_route_to_researcher():
    state = {"next_action": "research"}

    assert route_after_supervisor(state) == "research"


def test_route_to_writer():
    state = {"next_action": "write"}

    assert route_after_supervisor(state) == "write"


def test_route_to_stop():
    state = {"next_action": "stop"}

    assert route_after_supervisor(state) == "stop"


def test_unknown_action_stops():
    state = {"next_action": "unknown"}

    assert route_after_supervisor(state) == "stop"


def test_graph_builds_with_llm_review(monkeypatch):
    def fake_reviewer(
        question,
        findings,
        run_id=None,
    ):
        raise AssertionError(
            "Reviewer should not run during compilation"
        )

    monkeypatch.setattr(
        graph_module,
        "review_research",
        fake_reviewer,
    )

    graph = graph_module.build_graph(
        planner_fn=fake_planner,
        researcher_fn=fake_researcher,
        writer_fn=fake_writer,
        use_llm_review=True,
    )

    assert "planner" in graph.nodes
    assert "researcher" in graph.nodes
    assert "supervisor" in graph.nodes
    assert "writer" in graph.nodes


def test_graph_builds_without_llm_review():
    graph = graph_module.build_graph(
        planner_fn=fake_planner,
        researcher_fn=fake_researcher,
        writer_fn=fake_writer,
        use_llm_review=False,
    )

    assert "supervisor" in graph.nodes
