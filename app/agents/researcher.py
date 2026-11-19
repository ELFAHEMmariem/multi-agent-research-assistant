
from datetime import datetime, timezone

from app.schemas.finding import Finding, ResearchResult
from app.schemas.plan import SubQuestion
from app.tools.search import web_search


def run_researcher(
    sub_question: SubQuestion
) -> ResearchResult:

    results = web_search(sub_question.question)

    findings = []

    for index, result in enumerate(results, start=1):
        url = result.get("url")
        snippet = result.get("content", "")

        if not url or not snippet:
            continue

        finding = Finding(
            id=f"{sub_question.id}-F{index:03d}",
            sub_question_id=sub_question.id,
            claim=snippet,
            source_url=url,
            snippet=snippet,
            retrieved_at=datetime.now(timezone.utc),
        )

        findings.append(finding)

    status = "success" if findings else "no_results"

    return ResearchResult(
        sub_question_id=sub_question.id,
        status=status,
        findings=findings,
    )
