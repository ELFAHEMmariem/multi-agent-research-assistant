
from datetime import datetime, timezone

from app.agents.writer import run_writer
from app.schemas.finding import Finding


def main():
    findings = [
        Finding(
            id="F001",
            sub_question_id="Q1",
            claim="AI systems can be exposed to prompt injection.",
            source_url="https://example.org/source1",
            snippet="Test data: prompt injection affects AI systems.",
            retrieved_at=datetime.now(timezone.utc),
        ),
        Finding(
            id="F002",
            sub_question_id="Q1",
            claim="Sensitive information may be disclosed by insecure AI systems.",
            source_url="https://example.org/source2",
            snippet="Test data: insecure AI systems may disclose sensitive data.",
            retrieved_at=datetime.now(timezone.utc),
        ),
    ]

    report = run_writer(
        question="What are the security risks of AI?",
        findings=findings,
    )

    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
