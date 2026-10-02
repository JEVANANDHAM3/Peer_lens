from typing import List, Literal

from pydantic import BaseModel, Field, field_validator

SeverityLevel = Literal["Critical", "High", "Medium", "Low"]


class Evidence(BaseModel):
    page: int | None = Field(default=None, description="Page number associated with the evidence")
    section: str | None = Field(default=None, description="Section name where the evidence appears")
    text: str = Field(..., description="Direct excerpt supporting the clarity issue")


class ClarityIssue(BaseModel):
    id: str = Field(..., description="Unique identifier, e.g. CLARITY-001")
    reviewer: Literal["clarity"] = "clarity"
    section: str | None = Field(default=None, description="Section of the paper associated with the issue")
    page: int | None = Field(default=None, ge=1)
    severity: SeverityLevel
    type: str = Field(..., description="Clarity issue type, such as undefined_term or ambiguous_statement")
    issue: str
    explanation: str
    evidence: List[Evidence] = Field(default_factory=list)
    recommendation: str
    tools_used: List[str] = Field(default_factory=list)

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
            return mapping.get(value.lower(), value)
        return value


class ClarityReviewOutput(BaseModel):
    reviewer: Literal["clarity"] = "clarity"
    summary: str
    issues: List[ClarityIssue] = Field(default_factory=list)
