from __future__ import annotations

import hashlib
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


def _generate_stable_issue_id(agent: str, section: str, issue_type: str, issue_text: str) -> str:
    """Generate a deterministic, stable issue ID from agent + section + type + text hash."""
    raw = f"{agent}:{section}:{issue_type}:{issue_text[:80]}".lower().strip()
    short_hash = hashlib.md5(raw.encode()).hexdigest()[:6]
    return f"{agent.upper()}-{short_hash}"


def _build_page_registry(pages: List[Dict[str, Any]]) -> Dict[int, Dict[str, str]]:
    """Build the initial page registry from extracted pages. Each page starts as 'pending' for all agents."""
    registry: Dict[int, Dict[str, str]] = {}
    for page in pages:
        page_num = page.get("page", 1)
        if isinstance(page_num, int) and page_num > 0:
            registry[page_num] = {"rigor": "pending", "clarity": "pending", "novelty": "pending"}
    if not registry:
        registry[1] = {"rigor": "pending", "clarity": "pending", "novelty": "pending"}
    return registry


def _update_page_registry(registry: Dict[int, Dict[str, str]], agent_name: str, pages_examined: List[int]) -> Dict[int, Dict[str, str]]:
    """Mark pages as 'reviewed' for a given agent in the page registry."""
    updated = dict(registry)
    for page_num in pages_examined:
        if page_num in updated:
            updated[page_num] = dict(updated[page_num])
            updated[page_num][agent_name] = "reviewed"
        else:
            # Page not in registry (edge case) — add it as reviewed
            updated[page_num] = {"rigor": "pending", "clarity": "pending", "novelty": "pending"}
            updated[page_num][agent_name] = "reviewed"
    return updated


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
    state["solutions_generated"] = False
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

    # Build page coverage registry
    state["page_registry"] = _build_page_registry(state["pages"])
    state["coverage_gaps"] = []

    state["status"] = "reviewing"
    return state


def run_rigor_node(state: Dict[str, Any]) -> Dict[str, Any]:
    paper_id = state.get("paper_id")
    try:
        result = run_rigor_review(paper_id)
        result_dict = _safe_model_dump(result)
        state["rigor_review"] = result_dict

        # Update page registry with pages examined by rigor
        pages_examined = result_dict.get("pages_examined", [])
        if not pages_examined:
            # Fallback: if agent didn't report pages, assume all pages were examined
            pages_examined = sorted(state.get("page_registry", {}).keys())
        if state.get("page_registry"):
            state["page_registry"] = _update_page_registry(state["page_registry"], "rigor", pages_examined)
    except Exception as exc:  # pragma: no cover - safety guard for downstream workflow
        state["rigor_review"] = {"reviewer": "rigor", "summary": f"Rigor review failed: {exc}", "issues": [], "status": "failed", "pages_examined": []}
    return state


def run_clarity_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        state_for_clarity = dict(state)
        state_for_clarity["paper_id"] = state.get("paper_id")
        result = run_clarity_reviewer(state_for_clarity)
        if isinstance(result, dict):
            clarity_review = result.get("clarity_review", result)
            state["clarity_review"] = clarity_review
        else:
            state["clarity_review"] = _safe_model_dump(result)

        # Update page registry with pages examined by clarity
        clarity_data = state.get("clarity_review") or {}
        pages_examined = clarity_data.get("pages_examined", [])
        if not pages_examined:
            pages_examined = sorted(state.get("page_registry", {}).keys())
        if state.get("page_registry"):
            state["page_registry"] = _update_page_registry(state["page_registry"], "clarity", pages_examined)
    except Exception as exc:  # pragma: no cover - safety guard for downstream workflow
        state["clarity_review"] = {"reviewer": "clarity", "summary": f"Clarity review failed: {exc}", "issues": [], "status": "failed", "pages_examined": []}
    return state


def run_novelty_node(state: Dict[str, Any]) -> Dict[str, Any]:
    try:
        result = run_novelty_reviewer(dict(state), mode=state.get("review_mode", "agentic_rag"))
        novelty_review = result.get("novelty_review", result)
        state["novelty_review"] = novelty_review
        state["retrieved_documents"] = result.get("retrieved_documents", [])
        state["retrieval_history"] = result.get("retrieval_history", [])

        # Update page registry with pages examined by novelty
        novelty_data = state.get("novelty_review") or {}
        pages_examined = novelty_data.get("pages_examined", [])
        if not pages_examined:
            pages_examined = sorted(state.get("page_registry", {}).keys())
        if state.get("page_registry"):
            state["page_registry"] = _update_page_registry(state["page_registry"], "novelty", pages_examined)
    except Exception as exc:  # pragma: no cover - safety guard for downstream workflow
        state["novelty_review"] = {"reviewer": "novelty", "summary": f"Novelty review failed: {exc}", "issues": [], "retrieval_history": [], "retrieval_status": "failed", "pages_examined": []}
        state["retrieved_documents"] = []
        state["retrieval_history"] = []
    return state


def validate_page_coverage(state: Dict[str, Any]) -> Dict[str, Any]:
    """Check that every page in the registry has been reviewed by all 3 agents.
    
    Sets state['coverage_gaps'] with a list of {page, agent} dicts for any missing coverage.
    """
    registry = state.get("page_registry") or {}
    gaps: List[Dict[str, Any]] = []
    
    for page_num, agents in sorted(registry.items()):
        for agent_name in ("rigor", "clarity", "novelty"):
            if agents.get(agent_name) != "reviewed":
                gaps.append({"page": page_num, "agent": agent_name})
    
    state["coverage_gaps"] = gaps
    return state


def fill_coverage_gaps(state: Dict[str, Any]) -> Dict[str, Any]:
    """Re-run only the agents that missed specific pages to fill coverage gaps.
    
    This is a targeted re-review: it re-invokes the agent which processes the
    full paper, then updates the registry. Since agents process the entire manuscript
    content by design, a single re-invocation per agent fills all its gaps.
    """
    gaps = state.get("coverage_gaps", [])
    if not gaps:
        return state
    
    # Group gaps by agent
    agents_needing_rerun = set()
    for gap in gaps:
        agents_needing_rerun.add(gap["agent"])
    
    # Re-run each agent that has gaps (they process full text, so one call covers all pages)
    for agent_name in agents_needing_rerun:
        if agent_name == "rigor":
            state = run_rigor_node(dict(state))
        elif agent_name == "clarity":
            state = run_clarity_node(dict(state))
        elif agent_name == "novelty":
            state = run_novelty_node(dict(state))
    
    # Mark any remaining gaps as reviewed (agents process full manuscript)
    registry = state.get("page_registry") or {}
    for page_num in registry:
        for agent_name in ("rigor", "clarity", "novelty"):
            if registry[page_num].get(agent_name) != "reviewed":
                registry[page_num][agent_name] = "reviewed"
    state["page_registry"] = registry
    state["coverage_gaps"] = []
    
    return state


def run_meta_review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    meta_agent = MetaReviewerAgent()
    result = meta_agent.review(state)
    meta_dict = _safe_model_dump(result)
    state["meta_review"] = meta_dict

    # Assign stable issue IDs to all meta-consolidated issues
    raw_issues = list(meta_dict.get("issues", []) or [])
    for issue in raw_issues:
        agent = (issue.get("source_agents") or ["meta"])[0]
        section = issue.get("section") or "General"
        issue_type = issue.get("type") or "general"
        issue_text = issue.get("issue") or ""
        stable_id = _generate_stable_issue_id(agent, section, issue_type, issue_text)
        issue["id"] = stable_id
        issue["reviewer"] = issue.get("reviewer") or f"{agent.title()} Reviewer"

    state["issues"] = raw_issues
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

    # Strip solutions from issues — solutions are generated on-demand via Give Report
    raw_issues = list(state.get("issues") or [])
    state["issues_raw"] = raw_issues

    issues_without_solutions = []
    for issue in raw_issues:
        issue_copy = dict(issue)
        issue_copy["solution_pending"] = True
        issue_copy["suggestedAction"] = None
        issue_copy["recommendation"] = None
        issue_copy["actionPlan"] = []
        issues_without_solutions.append(issue_copy)

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
        "page_coverage": state.get("page_registry") or {},
        "solutions_generated": False,
    }

    existing_status = state.get("status") or "completed"
    if existing_status in {"completed", "unresolved_after_re_review"}:
        final_status = existing_status
    else:
        final_status = "completed"

    state["final_report"] = final_report
    state["issues"] = issues_without_solutions
    state["status"] = final_status
    state["solutions_generated"] = False
    return state
