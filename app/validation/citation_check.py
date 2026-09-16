"""
Every claim in the report carries a citation, and each citation is
validated against a real Finding before the report is returned.
A citation that doesn't map to a stored finding is a hallucination
and must block the response, not ship silently.
"""
from app.schemas.report import Report
from app.schemas.finding import Finding


class UnverifiedCitationError(Exception):
    def __init__(self, bad_urls: list[str]):
        self.bad_urls = bad_urls
        super().__init__(f"citations reference unknown sources: {bad_urls}")


def validate_citations(report: Report, findings: list[Finding]) -> None:
    known_urls = {f.source_url for f in findings}
    bad = [c.source_url for c in report.citations if c.source_url not in known_urls]
    if bad:
        raise UnverifiedCitationError(bad)
