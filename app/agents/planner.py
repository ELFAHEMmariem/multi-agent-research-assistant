
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm
from app.schemas.plan import ResearchPlan


PLANNER_PROMPT = """
You are a research planning component.

Your task is to decompose a research question into
1 to 3 specific, independent and searchable sub-questions.

Rules:
- Each question must address a different aspect.
- Avoid duplicate questions.
- Preserve the intent of the original question.
- Assign identifiers Q1, Q2 and Q3.
- Do not answer the research question.
"""


def run_planner(question: str) -> ResearchPlan:
    llm = get_llm()

    structured_llm = llm.with_structured_output(
        ResearchPlan,
        method="function_calling"
    )

    response = structured_llm.invoke([
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=question),
    ])

    return response
