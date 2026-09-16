import pytest
from app.schemas.report import Report, Citation
from app.schemas.finding import Finding
from app.validation.citation_check import validate_citations, UnverifiedCitationError


def test_rejects_citation_not_in_findings():
    findings = [Finding(claim="x", source_url="https://real.com", snippet="s",
                         retrieved_at="2026-01-01T00:00:00Z", sub_question_id="sq1")]
    report = Report(title="t", body="b", citations=[Citation(claim="c", source_url="https://fake.com")])
    with pytest.raises(UnverifiedCitationError):
        validate_citations(report, findings)


def test_accepts_citation_present_in_findings():
    findings = [Finding(claim="x", source_url="https://real.com", snippet="s",
                         retrieved_at="2026-01-01T00:00:00Z", sub_question_id="sq1")]
    report = Report(title="t", body="b", citations=[Citation(claim="c", source_url="https://real.com")])
    validate_citations(report, findings)  # should not raise
