
from pydantic import BaseModel, Field


class ReportClaim(BaseModel):
    text: str
    finding_ids: list[str] = Field(min_length=1)


class ResearchReport(BaseModel):
    title: str
    introduction: str
    claims: list[ReportClaim]
    conclusion: str
