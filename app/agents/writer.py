"""
Writer: findings -> cited Report.

Every claim in the body must be traceable to a Finding; validation
against the real finding records happens in validation/citation_check.py
AFTER this agent returns, so the writer is never trusted blindly.
"""
import json
from groq import Groq
from app.config import settings
from app.schemas.plan import Plan
from app.schemas.finding import Finding
from app.schemas.report import Report

client = Groq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You write a research report from a set of findings, each
tagged with a source URL. Every factual sentence must be immediately followed
by a citation marker like [1], [2] referencing the finding it came from.
Do not state anything not supported by a finding.

Return ONLY JSON matching this schema, no prose outside it:
{
  "title": string,
  "body": string,   // markdown, with [n] citation markers inline
  "citations": [{"claim": string, "source_url": string}]
}"""


async def write_report(plan: Plan, findings: list[Finding]) -> Report:
    findings_payload = [
        {"n": i + 1, "claim": f.claim, "source_url": f.source_url, "sub_question_id": f.sub_question_id}
        for i, f in enumerate(findings)
    ]
    user_content = json.dumps({
        "original_question": plan.original_question,
        "findings": findings_payload,
    })

    response = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=3000,
        temperature=0.3,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    raw = response.choices[0].message.content.strip()
    data = json.loads(raw)
    return Report.model_validate(data)
