from pydantic import BaseModel


class Citation(BaseModel):
    claim: str
    source_url: str


class Report(BaseModel):
    title: str
    body: str
    citations: list[Citation]
