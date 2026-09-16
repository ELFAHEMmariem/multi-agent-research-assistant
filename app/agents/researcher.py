"""
Researcher: one sub-question -> ResearchResult (findings with provenance).

Every claim is grounded in a fetched page, never a raw search snippet.
Failure paths return a status the supervisor can route on instead of
raising and killing the run.
"""
from datetime import datetime, timezone
from groq import Groq
from app.config import settings
from app.schemas.plan import SubQuestion
from app.schemas.finding import Finding, ResearchResult
from app.tools.search import tavily_search, RateLimitError
from app.tools.extract import fetch_and_extract, PaywallError, FetchTimeoutError
from app.tools.dedup import dedupe_by_domain

client = Groq(api_key=settings.groq_api_key)

CLAIM_EXTRACTION_PROMPT = """Given this sub-question and page content, extract
ONE concise, specific claim (max 2 sentences) that directly answers or informs
the sub-question. Return ONLY the claim text, no preamble, no JSON."""


async def research_sub_question(sq: SubQuestion, search_budget_remaining: int) -> ResearchResult:
    if search_budget_remaining <= 0:
        return ResearchResult(sub_question_id=sq.id, findings=[], status="timed_out")

    try:
        results = await tavily_search(sq.question, max_results=5)
    except RateLimitError:
        return ResearchResult(sub_question_id=sq.id, findings=[], status="rate_limited")

    if not results:
        return ResearchResult(sub_question_id=sq.id, findings=[], status="no_results")

    capped_results = dedupe_by_domain(results, cap=settings.max_results_per_domain)

    findings: list[Finding] = []
    for r in capped_results:
        try:
            page_text = await fetch_and_extract(r["url"])
        except (PaywallError, FetchTimeoutError):
            continue
        if not page_text:
            continue

        # Fast/free small model for the cheap per-page extraction call —
        # keep the bigger model budget for planning and writing.
        claim_response = client.chat.completions.create(
            model=settings.groq_model_fast,
            max_tokens=200,
            temperature=0.2,
            messages=[
                {"role": "system", "content": CLAIM_EXTRACTION_PROMPT},
                {"role": "user", "content": f"Sub-question: {sq.question}\n\nPage content:\n{page_text[:4000]}"},
            ],
        )
        claim = claim_response.choices[0].message.content.strip()

        findings.append(Finding(
            claim=claim,
            source_url=r["url"],
            snippet=page_text[:300],
            retrieved_at=datetime.now(timezone.utc).isoformat(),
            sub_question_id=sq.id,
        ))

    status = "complete" if findings else "no_results"
    return ResearchResult(sub_question_id=sq.id, findings=findings, status=status)
