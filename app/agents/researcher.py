
from datetime import datetime, timezone

from app.schemas.finding import Finding, ResearchResult
from app.schemas.plan import SubQuestion

from app.tools.search import (
    web_search,
    classify_tool_error,
)
from app.tools.dedup import deduplicate_results
from app.tools.extract import (
    extract_pages,
    get_useful_content,
)


def run_researcher(
    sub_question: SubQuestion,
) -> ResearchResult:

    # 1. Search for relevant pages
    try:
        search_results = web_search(
            sub_question.question
        )
    except Exception as exc:
        return ResearchResult(
            sub_question_id=sub_question.id,
            status=classify_tool_error(exc),
            error_message=str(exc),
        )

    if not search_results:
        return ResearchResult(
            sub_question_id=sub_question.id,
            status="no_results",
        )

    # 2. Remove duplicate sources
    unique_results = deduplicate_results(
        search_results,
        max_per_domain=2,
        max_total=3,
    )

    if not unique_results:
        return ResearchResult(
            sub_question_id=sub_question.id,
            status="no_results",
        )

    # 3. Extract page contents
    urls = [
        item["url"]
        for item in unique_results
    ]

    try:
        extraction = extract_pages(urls)
    except Exception as exc:
        return ResearchResult(
            sub_question_id=sub_question.id,
            status=classify_tool_error(exc),
            error_message=str(exc),
        )

    # 4. Build structured findings
    findings = []

    for index, page in enumerate(
        extraction["results"],
        start=1,
    ):
        content = get_useful_content(page)

        if not content:
            continue

        finding = Finding(
            id=f"{sub_question.id}-F{index:03d}",
            sub_question_id=sub_question.id,
            claim=content[:500],
            source_url=page["url"],
            snippet=content,
            retrieved_at=datetime.now(timezone.utc),
        )

        findings.append(finding)

    # 5. Determine status
    if findings:
        status = "success"
    else:
        status = "extraction_failed"

    return ResearchResult(
        sub_question_id=sub_question.id,
        status=status,
        findings=findings,
    )
