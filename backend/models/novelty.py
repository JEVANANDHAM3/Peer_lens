from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field, field_validator

Severity = Literal["Critical", "High", "Medium", "Low", "critical", "high", "medium", "low"]


class EvidenceItem(BaseModel):
    page: int | None = None
    section: str | None = None
    text: str = ""
    title: str | None = None
    source: str = "local"


class RetrievedEvidence(BaseModel):
    document: str
    title: str | None = None
    page: int | None = None
    relevant_text: str
    similarity_score: float = 0.0
    source: str = "local"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ClaimAssessment(BaseModel):
    claim: str
    retrieval_required: bool
    queries: List[str] = Field(default_factory=list)
    retrieval_iterations: int = 0
    evidence: List[RetrievedEvidence] = Field(default_factory=list)
    assessment: str
    potential_overlap: str
    differences: str
    confidence: float = Field(ge=0, le=1)
    related_work: List[Dict[str, Any]] = Field(default_factory=list)


class NoveltyIssue(BaseModel):
    id: str
    reviewer: str = Field(default="novelty", description="Reviewer name")
    section: str | None = None
    page: int | None = None
    severity: Severity = "Medium"
    type: str = "potential_literature_overlap"
    issue: str
    explanation: str
    claim: str = ""
    evidence: List[EvidenceItem] = Field(default_factory=list)
    similarities: List[str] = Field(default_factory=list)
    differences: List[str] = Field(default_factory=list)
    recommendation: str
    confidence: float = Field(default=0.0, ge=0, le=1)
    tools_used: List[str] = Field(default_factory=list)

    @field_validator("reviewer", mode="before")
    @classmethod
    def normalize_reviewer(cls, value):
        return "novelty"

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
            return mapping.get(value.lower(), value.title() if value else "Medium")
        return "Medium"


class NoveltyReviewOutput(BaseModel):
    reviewer: str = Field(default="novelty", description="Reviewer name")
    summary: str
    claims_checked: List[ClaimAssessment] = Field(default_factory=list)
    retrieval_required: bool = False
    retrieval_iterations: int = 0
    queries: List[str] = Field(default_factory=list)
    retrieval_history: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    issues: List[NoveltyIssue] = Field(default_factory=list)
    claims_analyzed: List[ClaimAssessment] = Field(default_factory=list)
    pages_examined: List[int] = Field(default_factory=list, description="Page numbers that were analyzed by this reviewer")

    @field_validator("reviewer", mode="before")
    @classmethod
    def normalize_reviewer(cls, value):
        return "novelty"

    model_config = {"populate_by_name": True}

