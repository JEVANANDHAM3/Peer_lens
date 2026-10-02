from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

Severity = Literal["Critical", "High", "Medium", "Low", "critical", "high", "medium", "low"]


class MetaIssue(BaseModel):
    id: str
    reviewer: str | None = None
    source_agents: List[str] = Field(default_factory=list)
    section: str | None = None
    page: int | None = None
    severity: str = "Medium"
    original_severity: str | None = None
    final_severity: str | None = None
    type: str = "general"
    issue: str
    explanation: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    recommendation: str
    evidence_status: str = "insufficient"
    human_status: str | None = None
    final_status: str = "confirmed"
    needs_re_review: bool = False
    recommended_reviewer: str | None = None
    source_reviewers: List[str] = Field(default_factory=list)


class Conflict(BaseModel):
    id: str
    issue_ids: List[str] = Field(default_factory=list)
    agents: List[str] = Field(default_factory=list)
    agents_involved: List[str] = Field(default_factory=list)
    description: str
    reason: str
    recommended_reviewer: str = "none"
    target_agent: str | None = None
    requires_re_review: bool = False
    status: str = "unresolved"
    conflict_detected: bool = True


class MetaReviewOutput(BaseModel):
    reviewer: str = "meta"
    summary: str = ""
    overall_assessment: str = ""
    issues: List[MetaIssue] = Field(default_factory=list)
    critical_issues: List[MetaIssue] = Field(default_factory=list)
    high_priority_issues: List[MetaIssue] = Field(default_factory=list)
    medium_priority_issues: List[MetaIssue] = Field(default_factory=list)
    low_priority_issues: List[MetaIssue] = Field(default_factory=list)
    reviewer_agreement: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: List[Conflict] = Field(default_factory=list)
    resolved_conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    re_review_requests: List[Dict[str, Any]] = Field(default_factory=list)
    human_feedback: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
    final_summary: str = ""
    retrieval_summary: str | None = None
    claims: List[Dict[str, Any]] = Field(default_factory=list)
    retrieval_history: List[Dict[str, Any]] = Field(default_factory=list)
    review_history: List[Dict[str, Any]] = Field(default_factory=list)

