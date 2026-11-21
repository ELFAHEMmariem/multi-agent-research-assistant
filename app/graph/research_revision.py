"""
Research revision helpers.

Transform Reviewer feedback into a targeted
research question while preserving the
original SubQuestion identifier.
"""

from app.schemas.plan import SubQuestion


QUESTION_FIELDS = (
    "question",
    "text",
    "title",
)


def build_revised_question(
    original: SubQuestion,
    feedback: str,
) -> SubQuestion:
    """
    Create a revised research question.

    The original sub-question ID is preserved
    to keep findings, retries and checkpoints
    associated with the same research task.
    """

    if not isinstance(original, SubQuestion):
        raise TypeError(
            "original must be a SubQuestion"
        )

    if not isinstance(feedback, str):
        raise TypeError(
            "feedback must be a string"
        )

    feedback = " ".join(
        feedback.split()
    )

    if not feedback:
        raise ValueError(
            "Revision feedback cannot be empty"
        )

    feedback = feedback[:500]

    question_field = None

    for field in QUESTION_FIELDS:
        if field in type(original).model_fields:
            value = getattr(
                original,
                field,
                None,
            )

            if (
                isinstance(value, str)
                and value.strip()
            ):
                question_field = field
                break

    if question_field is None:
        raise ValueError(
            "SubQuestion has no supported text field"
        )

    original_text = getattr(
        original,
        question_field,
    ).strip()

    revised_text = (
        f"{original_text}\n\n"
        "Additional research focus based on "
        "quality review:\n"
        f"{feedback}\n\n"
        "Find new, relevant supporting evidence "
        "for the missing aspects."
    )

    revised = original.model_copy(
        update={
            question_field: revised_text,
        }
    )

    return SubQuestion.model_validate(
        revised.model_dump()
    )
