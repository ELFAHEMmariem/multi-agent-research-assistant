
from types import SimpleNamespace

from app.agents.writer import (
    prepare_findings_for_writer,
)


def test_balanced_findings():

    findings = []

    for question_id in ["Q1", "Q2", "Q3"]:

        for i in range(3):

            findings.append(
                SimpleNamespace(
                    id=f"{question_id}-F{i}",
                    sub_question_id=question_id,
                    claim="Example security finding",
                    source_url="https://example.org",
                    snippet="Example evidence text",
                )
            )

    compact = prepare_findings_for_writer(
        findings
    )

    assert len(compact) == 6

    question_ids = {
        finding["sub_question_id"]
        for finding in compact
    }

    assert question_ids == {
        "Q1",
        "Q2",
        "Q3",
    }

    for question_id in question_ids:

        count = sum(
            1
            for finding in compact
            if finding["sub_question_id"]
            == question_id
        )

        assert count == 2
