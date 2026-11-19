
import json

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm
from app.schemas.finding import Finding
from app.schemas.report import ResearchReport


WRITER_PROMPT = """
You are a research report writing component.

Create a structured report using only the findings provided.

Rules:
- Never invent sources or finding IDs.
- Every factual claim must reference existing finding IDs.
- Use only information supported by the findings.
- Clearly mention limitations in the available evidence.
- Produce a title, introduction, claims and conclusion.
"""


def run_writer(
    question: str,
    findings: list[Finding]
) -> ResearchReport:

    llm = get_llm()

    structured_llm = llm.with_structured_output(
        ResearchReport,
        method="function_calling",
    )

    findings_data = [
        finding.model_dump(mode="json")
        for finding in findings
    ]

    prompt = (
        f"Research question:\n{question}\n\n"
        f"Available findings:\n"
        f"{json.dumps(findings_data, indent=2)}"
    )

    return structured_llm.invoke([
        SystemMessage(content=WRITER_PROMPT),
        HumanMessage(content=prompt),
    ])
