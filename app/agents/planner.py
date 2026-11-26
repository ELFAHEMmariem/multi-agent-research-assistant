
from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import get_llm
from app.persistence.token_tracker import GroqTokenTracker
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


def run_planner(
    question: str,
    run_id: str | None = None,
) -> ResearchPlan:
    """
    Generate a structured research plan.

    When run_id is provided, track Groq token
    consumption in Redis for the current run.
    """

    llm = get_llm()

    structured_llm = llm.with_structured_output(
        ResearchPlan,
        method="function_calling",
    )

    messages = [
        SystemMessage(content=PLANNER_PROMPT),
        HumanMessage(content=question),
    ]

    if run_id:
        tracker = GroqTokenTracker(
            run_id=run_id,
            agent="planner",
        )

        response = structured_llm.invoke(
            messages,
            config={
                "callbacks": [tracker],
            },
        )
    else:
        response = structured_llm.invoke(
            messages
        )

    return response
