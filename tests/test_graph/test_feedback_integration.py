"""
Tests for Groq feedback integration in the
LangGraph Researcher node.

No network connection or Redis required.
"""

from app.graph.nodes import make_researcher_node
from app.schemas.finding import ResearchResult


def make_state():
    return {
        "question": (
            "What are Zero Trust challenges?"
        ),
        "started_at": 0.0,
        "plan": {
            "original_question": (
                "What are Zero Trust challenges?"
            ),
            "sub_questions": [
                {
                    "id": "Q1",
                    "question": (
                        "What are Zero Trust "
                        "implementation challenges?"
                    ),
                }
            ],
        },
        "question_index": 0,
        "findings": [],
        "attempts": {},
        "revisions": {},
        "review_feedback": {},
        "total_tokens": 0,
        "last_result_status": "",
    }


def fake_result(question):
    return ResearchResult(
        sub_question_id=question.id,
        status="no_results",
        findings=[],
    )


def test_initial_search_uses_original_question():
    calls = []

    def researcher(question):
        calls.append(question.question)
        return fake_result(question)

    node = make_researcher_node(
        researcher
    )

    state = make_state()

    result = node(state)

    assert len(calls) == 1

    assert calls[0] == (
        "What are Zero Trust "
        "implementation challenges?"
    )

    assert result["attempts"]["Q1"] == 1


def test_revision_uses_groq_feedback():
    calls = []

    def researcher(question):
        calls.append(question)
        return fake_result(question)

    node = make_researcher_node(
        researcher
    )

    state = make_state()

    state["attempts"] = {
        "Q1": 1
    }

    state["revisions"] = {
        "Q1": 1
    }

    state["review_feedback"] = {
        "Q1": (
            "Investigate IAM and MFA "
            "deployment challenges."
        )
    }

    result = node(state)

    assert len(calls) == 1

    revised = calls[0]

    assert revised.id == "Q1"

    assert "IAM and MFA" in revised.question

    assert "Zero Trust" in revised.question

    assert result["attempts"]["Q1"] == 2


def test_feedback_for_other_question_is_ignored():
    calls = []

    def researcher(question):
        calls.append(question.question)
        return fake_result(question)

    node = make_researcher_node(
        researcher
    )

    state = make_state()

    state["review_feedback"] = {
        "Q2": "Research unrelated evidence."
    }

    node(state)

    assert len(calls) == 1

    assert "unrelated" not in calls[0]


def test_two_passes_use_different_questions():
    calls = []

    def researcher(question):
        calls.append(question.question)
        return fake_result(question)

    node = make_researcher_node(
        researcher
    )

    state = make_state()

    # First research pass
    first_result = node(state)

    state.update(first_result)

    # Simulate an authorized Supervisor retry
    state["revisions"] = {
        "Q1": 1
    }

    state["review_feedback"] = {
        "Q1": (
            "Find additional sources about "
            "Zero Trust identity governance."
        )
    }

    # Second research pass
    second_result = node(state)

    assert len(calls) == 2

    assert calls[0] != calls[1]

    assert "identity governance" in calls[1]

    assert first_result["attempts"]["Q1"] == 1

    assert second_result["attempts"]["Q1"] == 2
