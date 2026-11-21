
"""
Unit tests for research citation validation.

These tests do not require:
- Groq API
- Tavily API
- Redis
"""

from app.graph.citation_validator import (
    validate_citations,
)


# ==================================================
# TEST 1: VALID FINDING ID
# ==================================================

def test_valid_finding_reference():

    report = {
        "claims": [
            {
                "text": (
                    "AI agents may expose "
                    "sensitive credentials."
                ),
                "finding_ids": ["Q1-F001"],
            }
        ]
    }

    findings = [
        {
            "id": "Q1-F001",
            "sub_question_id": "Q1",
            "claim": (
                "AI agents can access credentials."
            ),
            "source_url": (
                "https://example.org/ai-security"
            ),
            "snippet": (
                "Agents with excessive permissions "
                "may access sensitive credentials."
            ),
        }
    ]

    result = validate_citations(
        report=report,
        findings=findings,
    )

    assert result["total_references"] == 1
    assert result["valid_references"] == 1
    assert result["invalid_references"] == 0

    citation = result["citations"][0]

    assert citation["finding_id"] == "Q1-F001"
    assert citation["reference_valid"] is True

    assert citation["source_url"] == (
        "https://example.org/ai-security"
    )

    # ID validation is not semantic verification.
    assert citation["support_verified"] is False


# ==================================================
# TEST 2: INVALID FINDING ID
# ==================================================

def test_invalid_finding_reference():

    report = {
        "claims": [
            {
                "text": "Unsupported research claim.",
                "finding_ids": ["Q9-F999"],
            }
        ]
    }

    findings = [
        {
            "id": "Q1-F001",
            "source_url": (
                "https://example.org/source"
            ),
            "snippet": "Existing finding",
        }
    ]

    result = validate_citations(
        report=report,
        findings=findings,
    )

    assert result["total_references"] == 1
    assert result["valid_references"] == 0
    assert result["invalid_references"] == 1

    citation = result["citations"][0]

    assert citation["finding_id"] == "Q9-F999"
    assert citation["reference_valid"] is False
    assert citation["source_url"] is None


# ==================================================
# TEST 3: MULTIPLE FINDINGS FOR ONE CLAIM
# ==================================================

def test_multiple_findings_for_one_claim():

    report = {
        "claims": [
            {
                "text": (
                    "AI agents introduce "
                    "multiple cybersecurity risks."
                ),
                "finding_ids": [
                    "Q1-F001",
                    "Q2-F001",
                    "Q3-F001",
                ],
            }
        ]
    }

    findings = [
        {
            "id": "Q1-F001",
            "source_url": (
                "https://example.org/source1"
            ),
            "snippet": "Security finding one",
        },
        {
            "id": "Q2-F001",
            "source_url": (
                "https://example.org/source2"
            ),
            "snippet": "Security finding two",
        },
        {
            "id": "Q3-F001",
            "source_url": (
                "https://example.org/source3"
            ),
            "snippet": "Security finding three",
        },
    ]

    result = validate_citations(
        report=report,
        findings=findings,
    )

    assert result["total_references"] == 3
    assert result["valid_references"] == 3
    assert result["invalid_references"] == 0

    assert len(result["citations"]) == 3

    found_ids = {
        citation["finding_id"]
        for citation in result["citations"]
    }

    assert found_ids == {
        "Q1-F001",
        "Q2-F001",
        "Q3-F001",
    }


# ==================================================
# TEST 4: CLAIM WITHOUT FINDING IDS
# ==================================================

def test_claim_without_findings():

    report = {
        "claims": [
            {
                "text": (
                    "This claim has no references."
                ),
                "finding_ids": [],
            }
        ]
    }

    result = validate_citations(
        report=report,
        findings=[],
    )

    assert result["total_references"] == 0
    assert result["valid_references"] == 0
    assert result["invalid_references"] == 0

    assert result["citations"] == []


# ==================================================
# TEST 5: MIXED VALID AND INVALID REFERENCES
# ==================================================

def test_mixed_references():

    report = {
        "claims": [
            {
                "text": (
                    "AI agents require "
                    "security controls."
                ),
                "finding_ids": [
                    "Q1-F001",
                    "Q9-F999",
                ],
            }
        ]
    }

    findings = [
        {
            "id": "Q1-F001",
            "source_url": (
                "https://example.org/source"
            ),
            "snippet": "Security controls",
        }
    ]

    result = validate_citations(
        report=report,
        findings=findings,
    )

    assert result["total_references"] == 2
    assert result["valid_references"] == 1
    assert result["invalid_references"] == 1

    assert (
        result["citations"][0]["reference_valid"]
        is True
    )

    assert (
        result["citations"][1]["reference_valid"]
        is False
    )


# ==================================================
# TEST 6: EMPTY REPORT
# ==================================================

def test_empty_report():

    report = {
        "title": "Empty Research Report",
        "claims": [],
    }

    result = validate_citations(
        report=report,
        findings=[],
    )

    assert result["total_references"] == 0
    assert result["valid_references"] == 0
    assert result["invalid_references"] == 0
    assert result["citations"] == []
