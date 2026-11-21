
from fastapi.testclient import TestClient

from app.api.main import app
from app.api.service import record_graph_updates


client = TestClient(app)


def test_node_completed_event(monkeypatch):
    """
    Verify that a LangGraph node completion
    generates an SSE event.
    """

    recorded_events = []

    def fake_add_event(
        run_id,
        event_type,
        message,
        node=None,
    ):
        recorded_events.append({
            "run_id": run_id,
            "type": event_type,
            "message": message,
            "node": node,
        })

    monkeypatch.setattr(
        "app.api.service.add_event",
        fake_add_event,
    )

    record_graph_updates(
        "test-run",
        {
            "planner": {
                "plan": {
                    "sub_questions": []
                }
            }
        },
    )

    assert len(recorded_events) == 1
    assert recorded_events[0]["type"] == (
        "node_completed"
    )
    assert recorded_events[0]["node"] == "planner"


def test_multiple_node_events(monkeypatch):
    """
    Verify that several node updates
    produce separate events.
    """

    recorded_events = []

    def fake_add_event(
        run_id,
        event_type,
        message,
        node=None,
    ):
        recorded_events.append({
            "type": event_type,
            "node": node,
        })

    monkeypatch.setattr(
        "app.api.service.add_event",
        fake_add_event,
    )

    record_graph_updates(
        "test-run",
        {
            "researcher": {
                "findings": []
            },
            "supervisor": {
                "status": "running"
            },
        },
    )

    assert len(recorded_events) == 2

    assert recorded_events[0]["node"] == (
        "researcher"
    )

    assert recorded_events[1]["node"] == (
        "supervisor"
    )


def test_completed_run_sse(monkeypatch):
    """
    Verify that the API sends events
    in the SSE response format.
    """

    monkeypatch.setattr(
        "app.api.main.get_run",
        lambda run_id: {
            "run_id": run_id,
            "question": "AI cybersecurity risks",
            "status": "completed",
        },
    )

    events = [
        {
            "type": "queued",
            "message": "Research accepted",
        },
        {
            "type": "node_completed",
            "message": "Node planner completed",
            "node": "planner",
        },
        {
            "type": "completed",
            "message": "Report generated",
        },
    ]

    def fake_get_events(
        run_id,
        start_index=0,
    ):
        return events[start_index:]

    monkeypatch.setattr(
        "app.api.main.get_events",
        fake_get_events,
    )

    response = client.get(
        "/events/test-run"
    )

    assert response.status_code == 200

    assert response.headers[
        "content-type"
    ].startswith("text/event-stream")

    assert "queued" in response.text
    assert "node_completed" in response.text
    assert "completed" in response.text


def test_unknown_run_sse(monkeypatch):
    """
    Verify that an unknown run
    returns HTTP 404.
    """

    monkeypatch.setattr(
        "app.api.main.get_run",
        lambda run_id: None,
    )

    response = client.get(
        "/events/unknown-run"
    )

    assert response.status_code == 404
