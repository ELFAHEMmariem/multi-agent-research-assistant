
from collections.abc import Callable

from app.schemas.finding import Finding, ResearchResult
from app.schemas.plan import ResearchPlan, SubQuestion
from app.schemas.report import ResearchReport
from app.schemas.state import ResearchState


PlannerFn = Callable[[str], ResearchPlan]
ResearcherFn = Callable[[SubQuestion], ResearchResult]
WriterFn = Callable[[str, list[Finding]], ResearchReport]


def make_planner_node(planner_fn: PlannerFn):

    def planner_node(state: ResearchState) -> dict:
        plan = planner_fn(state["question"])

        return {
            "plan": plan.model_dump(mode="json"),
            "question_index": 0,
            "findings": [],
            "attempts": {},
            "revisions": {},
            "total_tokens": 0,
            "status": "researching",
        }

    return planner_node


def make_researcher_node(researcher_fn: ResearcherFn):

    def researcher_node(state: ResearchState) -> dict:
        questions = state["plan"]["sub_questions"]
        index = state["question_index"]

        question = SubQuestion.model_validate(
            questions[index]
        )

        attempts = dict(state["attempts"])
        attempts[question.id] = attempts.get(question.id, 0) + 1

        result = researcher_fn(question)

        existing_findings = list(state["findings"])
        known_ids = {
            finding["id"] for finding in existing_findings
        }

        for finding in result.findings:
            if finding.id not in known_ids:
                existing_findings.append(
                    finding.model_dump(mode="json")
                )
                known_ids.add(finding.id)

        return {
            "findings": existing_findings,
            "attempts": attempts,
            "last_result_status": result.status,
        }

    return researcher_node


def make_writer_node(writer_fn: WriterFn):

    def writer_node(state: ResearchState) -> dict:
        findings = [
            Finding.model_validate(item)
            for item in state["findings"]
        ]

        report = writer_fn(
            state["question"],
            findings,
        )

        return {
            "report": report.model_dump(mode="json"),
            "status": "completed",
        }

    return writer_node
