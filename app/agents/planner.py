"""
Planner: research question -> structured Plan.

No "you are a world-class researcher" framing. The contract is the
Plan schema; the prompt only needs to explain the schema and the task.
"""
import json
from groq import Groq
from app.config import settings
from app.schemas.plan import Plan

client = Groq(api_key=settings.groq_api_key)

SYSTEM_PROMPT = """You break a research question into independent, answerable
sub-questions. Each sub-question must be:
- Narrow enough to answer with 3-5 web searches
- Independent of the others (no sub-question should depend on another's answer)
- Ranked by priority (1 = essential, 3 = nice-to-have)

Return ONLY a JSON object matching this schema, no prose, no markdown fences:
{
  "original_question": string,
  "sub_questions": [
    {"id": string, "question": string, "priority": 1|2|3}
  ]
}
Produce at most 5 sub-questions."""


async def plan(question: str) -> Plan:
    response = client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=1000,
        temperature=0.3,
        response_format={"type": "json_object"},  # Groq JSON mode — skips fence-stripping
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
    )
    raw = response.choices[0].message.content.strip()
    data = json.loads(raw)
    return Plan.model_validate(data)
