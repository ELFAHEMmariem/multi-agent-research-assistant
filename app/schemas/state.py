
from typing import Literal, NotRequired, TypedDict


Action = Literal["research", "write", "stop"]


class ResearchState(TypedDict):
    # Initial information
    run_id: str
    question: str
    started_at: float

    # Research plan
    plan: NotRequired[dict]
    question_index: NotRequired[int]

    # Research results
    findings: NotRequired[list[dict]]
    last_result_status: NotRequired[str]

    # Execution counters
    attempts: NotRequired[dict[str, int]]
    revisions: NotRequired[dict[str, int]]
    total_tokens: NotRequired[int]

    # Supervisor decisions
    next_action: NotRequired[Action]
    status: NotRequired[str]
    stop_reason: NotRequired[str]

    # Final result
    report: NotRequired[dict]
