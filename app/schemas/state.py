
"""
Shared LangGraph state for the research workflow.

The state is the single source of truth for:
- Research plan
- Research results
- Execution counters
- LLM review feedback
- Supervisor routing decisions
- Final report

LangGraph checkpoints persist this state.
"""

from typing import Literal, NotRequired, TypedDict


Action = Literal["research", "write", "stop"]


class ResearchState(TypedDict):
    # ======================================
    # Initial information
    # ======================================

    run_id: str
    question: str
    started_at: float

    # ======================================
    # Research plan
    # ======================================

    plan: NotRequired[dict]
    question_index: NotRequired[int]

    # ======================================
    # Research results
    # ======================================

    findings: NotRequired[list[dict]]
    last_result_status: NotRequired[str]

    # ======================================
    # Execution counters
    # ======================================

    attempts: NotRequired[dict[str, int]]
    revisions: NotRequired[dict[str, int]]
    total_tokens: NotRequired[int]

    # ======================================
    # LLM quality review
    # ======================================

    # Feedback produced by Groq for each
    # sub-question, indexed by question ID.
    #
    # Example:
    # {
    #     "Q1": "Find more evidence about MFA."
    # }
    review_feedback: NotRequired[dict[str, str]]

    # ======================================
    # Supervisor decisions
    # ======================================

    next_action: NotRequired[Action]
    status: NotRequired[str]
    stop_reason: NotRequired[str]

    # ======================================
    # Final result
    # ======================================

    report: NotRequired[dict]
