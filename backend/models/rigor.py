from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class Evidence(BaseModel):
    page: int | None = Field(default=None, description="Page number associated with the evidence")
    section: str | None = Field(default=None, description="Section name where the evidence appears")
    text: str = Field(..., description="Extracted text or direct quote supporting the issue")


class RigorIssue(BaseModel):
    id: str = Field(..., description="Unique issue identifier, e.g. 'rigor-issue-1'")
    reviewer: str = Field(default="rigor", description="Reviewer name")
    section: str | None = Field(default=None, description="Section of the paper where the issue occurred")
    page: int | None = Field(default=None, description="Page number where the issue or claim is located")
    severity: Literal["Critical", "High", "Medium", "Low"] = Field(..., description="Severity level")
    type: str = Field(..., description="Type of concern")
    issue: str = Field(..., description="Concise statement of the potential issue")
    explanation: str = Field(..., description="Detailed explanation distinguishing observable fact from inferred concern")
    evidence: list[Evidence] = Field(default_factory=list, description="Direct quotes or excerpts supporting the issue")
    recommendation: str = Field(..., description="Concrete actionable recommendation for the authors")
    tools_used: list[str] = Field(default_factory=list, description="Tools used to investigate the issue")

    @field_validator("severity", mode="before")
    @classmethod
    def normalize_severity(cls, value):
        if isinstance(value, str):
            mapping = {
                "critical": "Critical",
                "high": "High",
                "medium": "Medium",
                "low": "Low",
            }
            return mapping.get(value.lower(), "Medium")
        return "Medium"


class RigorReviewOutput(BaseModel):
    reviewer: str = Field(default="rigor", description="Reviewer name, always 'rigor'")
    summary: str = Field(..., description="Executive summary of the methodological and experimental rigor of the manuscript")
    issues: list[RigorIssue] = Field(default_factory=list, description="List of identified rigor issues")

    @field_validator("reviewer", mode="before")
    @classmethod
    def normalize_reviewer(cls, value):
        return "rigor"


RigorReview = RigorReviewOutput
