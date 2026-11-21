
from typing import Any


def to_dict(value: Any) -> dict:
    """Convert a Pydantic model or dict to a dictionary."""

    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    return {}


def validate_citations(
    report: dict,
    findings: list,
) -> dict:
    """
    Match report claims to original research findings.

    This verifies that finding IDs exist.
    It does not verify semantic support.
    """

    report_data = to_dict(report)

    # Build an index for fast lookup.
    finding_index = {}

    for finding in findings:
        item = to_dict(finding)

        finding_id = item.get("id")

        if finding_id:
            finding_index[finding_id] = item

    citations = []
    valid_count = 0
    invalid_count = 0

    # Inspect claims in the final report.
    for claim_number, raw_claim in enumerate(
        report_data.get("claims", []),
        start=1,
    ):
        claim = to_dict(raw_claim)

        claim_text = claim.get("text", "")

        finding_ids = claim.get(
            "finding_ids",
            [],
        )

        for finding_id in finding_ids:
            finding = finding_index.get(finding_id)

            if finding is None:
                invalid_count += 1

                citations.append({
                    "claim_number": claim_number,
                    "claim_text": claim_text,
                    "finding_id": finding_id,
                    "source_url": None,
                    "snippet": None,
                    "reference_valid": False,
                    "support_verified": False,
                    "reason": "Finding ID not found",
                })

                continue

            valid_count += 1

            citations.append({
                "claim_number": claim_number,
                "claim_text": claim_text,
                "finding_id": finding_id,
                "source_url": str(
                    finding.get("source_url", "")
                ),
                "snippet": str(
                    finding.get("snippet", "")
                )[:1000],
                "reference_valid": True,
                "support_verified": False,
                "reason": (
                    "Finding exists; semantic "
                    "support not yet verified"
                ),
            })

    return {
        "total_references": (
            valid_count + invalid_count
        ),
        "valid_references": valid_count,
        "invalid_references": invalid_count,
        "citations": citations,
    }
