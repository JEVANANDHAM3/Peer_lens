from __future__ import annotations

import uuid
from typing import Any, Callable, Dict, List

from backend.agents.clarity_agent import run_clarity_reviewer
from backend.agents.meta_agent import MetaReviewerAgent
from backend.agents.novelty_agent import run_novelty_reviewer
from backend.agents.rigor_agent import run_rigor_review
from backend.graph.state import ReviewState
from backend.tools.paper_tools import get_paper


def _safe_model_dump(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {"value": value}


def initialize_review(state: Dict[str, Any]) -> Dict[str, Any]:
    review_id = state.get("review_id") or f"review-{uuid.uuid4().hex[:8]}"
    paper_id = state.get("paper_id")
    if not paper_id:
        raise ValueError("A paper_id is required before a review can begin.")

    state["review_id"] = review_id
    state["paper_id"] = paper_id
    state["status"] = "running"
    state["review_mode"] = state.get("review_mode") or "agentic_rag"
    state["re_review_count"] = int(state.get("re_review_count", 0))
    state["retrieval_count"] = int(state.get("retrieval_count", 0))
    state["human_feedback"] = list(state.get("human_feedback") or [])
    state["retrieval_history"] = list(state.get("retrieval_history") or [])
    state["issues"] = list(state.get("issues") or [])
    state["conflicts"] = list(state.get("conflicts") or [])
    state["needs_human_feedback"] = bool(state.get("needs_human_feedback", False))
    state["current_issue_id"] = state.get("current_issue_id")
    state["current_reviewer"] = state.get("current_reviewer")
    return state


def prepare_review_context(state: Dict[str, Any]) -> Dict[str, Any]:
    paper_id = state.get("paper_id")
    state["pages"] = list(state.get("pages") or [])
    state["sections"] = list(state.get("sections") or [])
    state["paper_text"] = state.get("paper_text") or ""

    if paper_id:
        paper = get_paper(paper_id)
        if paper is not None:
            state["pages"] = list(paper.get("pages", []) or [])
            state["sections"] = list(paper.get("sections", []) or [])
            page_text = "\n\n".join(str(page.get("text", "")) for page in state["pages"])
            state["paper_text"] = page_text

    if not state.get("sections") and not state.get("pages") and not state.get("paper_text"):
        state["status"] = "failed"

    state["status"] = "reviewing"
    return state


def run_rigor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    paper_id = state.get("paper_id")
    try:
        result = run_rigor_review(paper_id)
        state["rigor_review"] = _safe_model_dump(result)
    except Exception as exc:  # pragma: no cover - safety guard for downstream workflow
        state["rigor_review"] = {"reviewer": "rigor", "summary": f"Rigor review failed: {exc}", "issues": [], "status": "failed"}
    return state


def run_clarity_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        state_for_clarity = dict(state)
        state_for_clarity["paper_id"] = state.get("paper_id")
        result = run_clarity_reviewer(state_for_clarity)
        if isinstance(result, dict):
            state["clarity_review"] = result.get("clarity_review", result)
        else:
            state["clarity_review"] = _safe_model_dump(result)
    except Exception as exc:  # pragma: no cover - safety guard for downstream workflow
        state["clarity_review"] = {"reviewer": "clarity", "summary": f"Clarity review failed: {exc}", "issues": [], "status": "failed"}
    return state


def run_novelty_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = run_novelty_reviewer(dict(state), mode=state.get("review_mode", "agentic_rag"))
        novelty_review = result.get("novelty_review", result)
        state["novelty_review"] = novelty_review
        state["retrieved_documents"] = result.get("retrieved_documents", [])
        state["retrieval_history"] = result.get("retrieval_history", [])
    except Exception as exc:  # pragma: no cover - safety guard for downstream workflow
        state["novelty_review"] = {"reviewer": "novelty", "summary": f"Novelty review failed: {exc}", "issues": [], "retrieval_history": [], "retrieval_status": "failed"}
        state["retrieved_documents"] = []
        state["retrieval_history"] = []
    return state


def run_meta_review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    meta_agent = MetaReviewerAgent()
    result = meta_agent.review(state)
    meta_dict = _safe_model_dump(result)
    state["meta_review"] = meta_dict
    state["issues"] = list(meta_dict.get("issues", []) or [])
    state["conflicts"] = list(meta_dict.get("conflicts", []) or [])
    state["needs_human_feedback"] = any(
        request.get("needs_human_feedback")
        for request in meta_dict.get("re_review_requests", []) or []
    )
    prior_status = state.get("status")
    if prior_status in {"completed", "unresolved_after_re_review", "waiting_for_human", "re_reviewing"}:
        state["status"] = prior_status
    else:
        state["status"] = "reviewing"
    return state


def _count_re_review(state: Dict[str, Any]) -> int:
    return max(0, int(state.get("re_review_count", 0)))


def rerun_specialist_node(reviewer_name: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def _node(state: Dict[str, Any]) -> Dict[str, Any]:
        state["current_reviewer"] = reviewer_name
        state["re_review_count"] = _count_re_review(state) + 1
        state["status"] = "re_reviewing"

        if reviewer_name == "rigor":
            state.update(run_rigor_node(state))
        elif reviewer_name == "clarity":
            state.update(run_clarity_node(state))
        elif reviewer_name == "novelty":
            state.update(run_novelty_node(state))
        else:
            state["status"] = "failed"
        return state

    return _node


def process_human_feedback(state: Dict[str, Any]) -> Dict[str, Any]:
    feedback = list(state.get("human_feedback") or [])
    if not feedback:
        state["status"] = "waiting_for_human"
        return state

    last = feedback[-1]
    decision = str(last.get("decision") or "").lower()
    state["status"] = "re_reviewing" if decision == "disputed" else "reviewing"
    if decision == "approved":
        state["needs_human_feedback"] = False
    elif decision == "disputed":
        state["needs_human_feedback"] = True
    return state


def finalize_review(state: Dict[str, Any]) -> Dict[str, Any]:
    meta_review = state.get("meta_review") or {}
    rigor_review = state.get("rigor_review") or {}
    clarity_review = state.get("clarity_review") or {}
    novelty_review = state.get("novelty_review") or {}
    human_feedback = state.get("human_feedback") or []

    final_report = {
        "summary": meta_review.get("summary") or meta_review.get("overall_assessment") or "The manuscript review is complete.",
        "critical_issues": list(meta_review.get("critical_issues", []) or []),
        "high_issues": list(meta_review.get("high_priority_issues", []) or []),
        "medium_issues": list(meta_review.get("medium_priority_issues", []) or []),
        "low_issues": list(meta_review.get("low_priority_issues", []) or []),
        "reviewer_agreement": list(meta_review.get("reviewer_agreement", []) or []),
        "conflicts": list(meta_review.get("conflicts", []) or []),
        "resolved_conflicts": list(meta_review.get("resolved_conflicts", []) or []),
        "human_feedback": list(human_feedback),
        "human_confirmed_issues": [item for item in human_feedback if str(item.get("decision", "")).lower() == "approved"],
        "human_disputed_issues": [item for item in human_feedback if str(item.get("decision", "")).lower() == "disputed"],
        "resolved_issues": [],
        "unresolved_issues": [],
        "novelty_findings": list(novelty_review.get("issues", []) or []),
        "retrieval_summary": novelty_review.get("retrieval_history") or state.get("retrieval_history") or [],
        "recommended_actions": list(meta_review.get("recommended_actions", []) or []),
        "rigor_review": rigor_review,
        "clarity_review": clarity_review,
        "novelty_review": novelty_review,
    }

    existing_status = state.get("status") or "completed"
    if existing_status in {"completed", "unresolved_after_re_review"}:
        final_status = existing_status
    else:
        final_status = "completed"

    state["final_report"] = final_report
    state["status"] = final_status
    return state
