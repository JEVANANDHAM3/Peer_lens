from __future__ import annotations

from typing import Any, Dict, List


def _route_for_reviewer(state: Dict[str, Any], reviewer: str | None) -> str:
    if reviewer not in {"rigor", "clarity", "novelty"}:
        return "finalize_review"
    if state.get("re_review_count", 0) >= 2:
        return "finalize_review"
    return f"rerun_{reviewer}"


def route_after_meta(state: Dict[str, Any]) -> str:
    if state.get("needs_human_feedback"):
        return "human_feedback"

    if state.get("re_review_count", 0) >= 2:
        return "finalize_review"

    meta_review = state.get("meta_review") or {}
    re_review_requests: List[Dict[str, Any]] = meta_review.get("re_review_requests", []) or []
    if re_review_requests:
        for request in re_review_requests:
            reviewer = request.get("recommended_reviewer") or request.get("reviewer")
            if reviewer in {"rigor", "clarity", "novelty"}:
                return _route_for_reviewer(state, reviewer)

    for conflict in meta_review.get("conflicts", []) or []:
        target = conflict.get("target_agent") or conflict.get("recommended_reviewer")
        if target in {"rigor", "clarity", "novelty"}:
            return _route_for_reviewer(state, target)

    return "finalize_review"


def route_after_human_feedback(state: Dict[str, Any]) -> str:
    feedback = state.get("human_feedback") or []
    if not feedback:
        return "finalize_review"

    last = feedback[-1]
    decision = str(last.get("decision", "")).lower()
    if decision == "approved":
        return "run_meta_review_node"
    if decision == "disputed":
        issue_id = last.get("issue_id")
        meta_review = state.get("meta_review") or {}
        for request in meta_review.get("re_review_requests", []) or []:
            if request.get("issue_id") == issue_id:
                reviewer = request.get("recommended_reviewer") or request.get("reviewer")
                if reviewer in {"rigor", "clarity", "novelty"}:
                    return _route_for_reviewer(state, reviewer)
        return _route_for_reviewer(state, state.get("current_reviewer") or "rigor")
    return "finalize_review"
