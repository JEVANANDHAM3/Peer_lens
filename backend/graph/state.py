from __future__ import annotations

from typing import Any, Dict, List, Literal, TypedDict


class ReviewState(TypedDict, total=False):
    review_id: str
    paper_id: str
    pdf_path: str
    paper_text: str
    pages: List[Dict[str, Any]]
    sections: List[Dict[str, Any]]
    review_mode: Literal["no_rag", "basic_rag", "agentic_rag"]

    rigor_review: Dict[str, Any] | None
    clarity_review: Dict[str, Any] | None
    novelty_review: Dict[str, Any] | None
    meta_review: Dict[str, Any] | None

    retrieved_documents: List[Dict[str, Any]]
    retrieval_history: List[Dict[str, Any]]

    issues: List[Dict[str, Any]]
    conflicts: List[Dict[str, Any]]
    human_feedback: List[Dict[str, Any]]

    current_issue_id: str | None
    current_reviewer: str | None

    re_review_count: int
    retrieval_count: int
    needs_human_feedback: bool
    status: str

    final_report: Dict[str, Any] | None

    # Page Coverage Registry: {page_num: {"rigor": "pending"|"reviewed", ...}}
    page_registry: Dict[int, Dict[str, str]]
    # List of (page, agent) tuples where coverage is missing
    coverage_gaps: List[Dict[str, Any]]
    # Whether solutions have been generated (deferred until Give Report)
    solutions_generated: bool
