"""Final coordinator for the existing PeerLens reviewer outputs."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

from backend.models.meta import Conflict, MetaIssue, MetaReviewOutput


class MetaReviewerAgent:
    def __init__(self, llm: Any = None):
        self.llm = llm

    def normalize_severity(self, value: Any) -> str:
        if not isinstance(value, str):
            value = "Medium"
        mapping = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
        return mapping.get(value.lower(), value.title() if value else "Medium")

    def _coerce_text(self, value: Any) -> str:
        return "" if value is None else str(value)

    def _normalize_issue(self, review_item: Dict[str, Any], agent: str) -> Dict[str, Any]:
        evidence = review_item.get("evidence") or []
        if isinstance(evidence, dict):
            evidence = [evidence]
        if not isinstance(evidence, list):
            evidence = []

        issue_id = str(review_item.get("id") or f"{agent.upper()}-{len(review_item.get('issue', '')) % 7 + 1}")
        original_severity = self.normalize_severity(review_item.get("severity") or review_item.get("final_severity") or "Medium")
        final_severity = original_severity
        issue_text = self._coerce_text(review_item.get("issue") or review_item.get("title") or "")
        issue_type = str(review_item.get("type") or "general").strip() or "general"
        reviewer_name = f"{agent.title()} Reviewer"

        return {
            "id": issue_id,
            "reviewer": reviewer_name,
            "source_agents": [agent],
            "section": review_item.get("section") or "General",
            "page": review_item.get("page") or 1,
            "severity": final_severity,
            "original_severity": original_severity,
            "final_severity": final_severity,
            "type": issue_type,
            "issue": issue_text,
            "explanation": self._coerce_text(review_item.get("explanation") or review_item.get("description") or issue_text),
            "evidence": evidence,
            "recommendation": self._coerce_text(review_item.get("recommendation") or "Clarify the issue with local evidence and a precise corrective action."),
            "source_reviewers": [agent],
            "evidence_status": self._classify_evidence(evidence),
            "human_status": None,
            "final_status": "confirmed",
            "needs_re_review": False,
            "recommended_reviewer": None,
        }

    def _classify_evidence(self, evidence: List[Any]) -> str:
        if not evidence:
            return "insufficient"
        if len(evidence) >= 1 and any((item.get("text") if isinstance(item, dict) else str(item)) for item in evidence):
            return "sufficient"
        return "insufficient"

    def _merge_issue(self, issue_a: Dict[str, Any], issue_b: Dict[str, Any]) -> Dict[str, Any]:
        evidence_a = issue_a.get("evidence", []) or []
        evidence_b = issue_b.get("evidence", []) or []

        def _canonicalize(item: Any) -> Dict[str, Any]:
            if isinstance(item, dict):
                return item
            if isinstance(item, str):
                return {"text": item}
            return {"text": str(item)}

        evidence = []
        seen = set()
        for item in evidence_a + evidence_b:
            canonical = _canonicalize(item)
            key = str(canonical.get("text") or canonical.get("section") or canonical.get("page") or str(canonical))
            if key not in seen:
                evidence.append(canonical)
                seen.add(key)

        source_agents = sorted(set(issue_a.get("source_agents", []) + issue_b.get("source_agents", [])))
        primary_agent = source_agents[0] if source_agents else "rigor"
        reviewer_name = f"{primary_agent.title()} Reviewer" if len(source_agents) == 1 else "Meta Reviewer"

        merged_issue = {
            "id": issue_a["id"],
            "reviewer": reviewer_name,
            "source_agents": source_agents,
            "section": issue_a.get("section") or issue_b.get("section") or "General",
            "page": issue_a.get("page") or issue_b.get("page") or 1,
            "severity": self._max_severity(issue_a.get("severity", "Medium"), issue_b.get("severity", "Medium")),
            "original_severity": self._max_severity(issue_a.get("original_severity", "Medium"), issue_b.get("original_severity", "Medium")),
            "final_severity": self._max_severity(issue_a.get("final_severity", "Medium"), issue_b.get("final_severity", "Medium")),
            "type": issue_a.get("type") or issue_b.get("type") or "general",
            "issue": issue_a.get("issue") or issue_b.get("issue") or "Related reviewer concerns were combined.",
            "explanation": issue_a.get("explanation") or issue_b.get("explanation") or "The issue was reported by multiple reviewers and is treated as a single underlying concern.",
            "evidence": evidence,
            "recommendation": issue_a.get("recommendation") or issue_b.get("recommendation") or "Clarify and verify the underlying issue with the relevant specialist reviewer.",
            "source_reviewers": sorted(set(issue_a.get("source_reviewers", []) + issue_b.get("source_reviewers", []))),
            "evidence_status": "sufficient" if evidence else "insufficient",
            "human_status": None,
            "final_status": "confirmed",
            "needs_re_review": False,
            "recommended_reviewer": None,
        }
        return merged_issue

    def _max_severity(self, severity_a: str, severity_b: str) -> str:
        order = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
        a = order.get(str(severity_a).title(), 2)
        b = order.get(str(severity_b).title(), 2)
        if a >= b:
            return str(severity_a).title() if str(severity_a).title() in order else "Medium"
        return str(severity_b).title() if str(severity_b).title() in order else "Medium"

    def _similar_issue(self, issue_a: Dict[str, Any], issue_b: Dict[str, Any]) -> bool:
        page_a = issue_a.get("page")
        page_b = issue_b.get("page")
        # Never merge issues located on different pages!
        if page_a is not None and page_b is not None and page_a != page_b:
            return False

        text_a = self._coerce_text(issue_a.get("issue")).lower().strip()
        text_b = self._coerce_text(issue_b.get("issue")).lower().strip()
        if not text_a or not text_b:
            return False
        if text_a == text_b:
            return True

        words_a = set(re.findall(r"[a-z0-9]+", text_a))
        words_b = set(re.findall(r"[a-z0-9]+", text_b))
        if not words_a or not words_b:
            return False
        jaccard = len(words_a & words_b) / max(1, len(words_a | words_b))
        return jaccard >= 0.75

    def _detect_duplicates(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        for issue in issues:
            matched = False
            for existing in merged:
                if self._similar_issue(existing, issue):
                    merged[merged.index(existing)] = self._merge_issue(existing, issue)
                    matched = True
                    break
            if not matched:
                merged.append(issue)
        return merged

    def _recommended_reviewer(self, issue: Dict[str, Any]) -> str:
        text = (issue.get("issue") or "").lower() + " " + (issue.get("type") or "").lower() + " " + (issue.get("section") or "").lower()
        if any(word in text for word in ["baseline", "experiment", "method", "statistical", "training", "result", "validation", "data"]):
            return "rigor"
        if any(word in text for word in ["term", "clarity", "figure", "table", "section", "ambiguous", "definition", "organization", "methodology", "explanation"]):
            return "clarity"
        if any(word in text for word in ["novel", "literature", "overlap", "related work", "prior work", "contribution", "similar"]):
            return "novelty"
        return issue.get("source_agents", ["rigor"])[0] if issue.get("source_agents") else "none"

    def _detect_conflicts(self, issues: List[Dict[str, Any]]) -> List[Conflict]:
        conflicts: List[Conflict] = []
        for i in range(len(issues)):
            for j in range(i + 1, len(issues)):
                a = issues[i]
                b = issues[j]
                if set(a.get("source_agents", [])) == set(b.get("source_agents", [])):
                    continue
                a_text = self._coerce_text(a.get("issue")).lower()
                b_text = self._coerce_text(b.get("issue")).lower()
                if not a_text or not b_text:
                    continue
                if ("missing" in a_text and "present" in b_text) or ("unclear" in a_text and "clear" in b_text) or ("lack" in a_text and "provided" in b_text):
                    target_agent = self._recommended_reviewer(a if a.get("source_agents") else b)
                    agents = list(dict.fromkeys(a.get("source_agents", []) + b.get("source_agents", [])))
                    conflicts.append(
                        Conflict(
                            id=f"CONFLICT-{len(conflicts)+1:03d}",
                            issue_ids=[a.get("id"), b.get("id")],
                            agents=agents,
                            agents_involved=agents,
                            description=f"{a.get('issue')} vs {b.get('issue')}",
                            reason="The reviewers' statements disagree on whether a claim or evidence is present or sufficiently explained.",
                            recommended_reviewer=target_agent,
                            target_agent=target_agent,
                            requires_re_review=True,
                            status="unresolved",
                        )
                    )
        return conflicts

    def _determine_re_review(self, issue: Dict[str, Any], conflict: Optional[Conflict] = None, human_feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        evidence_status = issue.get("evidence_status", "insufficient")
        source_agents = issue.get("source_agents") or []
        duplicate_across_reviewers = len(source_agents) > 1
        needs_re_review = bool(
            evidence_status == "insufficient"
            or conflict is not None
            or duplicate_across_reviewers
            or (human_feedback and human_feedback.get("decision") == "disputed")
            or (issue.get("severity", "Medium").lower() in {"high", "critical"} and evidence_status != "sufficient")
        )
        recommended_reviewer = issue.get("recommended_reviewer") or self._recommended_reviewer(issue)
        return {
            "issue_id": issue.get("id"),
            "needs_re_review": needs_re_review,
            "recommended_reviewer": recommended_reviewer,
            "reason": "The issue lacks sufficient evidence, is in conflict with another reviewer, or was disputed by human feedback." if needs_re_review else "The finding is sufficiently supported and does not require a re-review.",
        }

    def _apply_human_feedback(self, issues: List[Dict[str, Any]], human_feedback: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        if not human_feedback:
            return issues
        for event in human_feedback:
            issue_id = event.get("issue_id")
            if not issue_id:
                continue
            for issue in issues:
                if issue.get("id") == issue_id:
                    decision = (event.get("decision") or "").lower()
                    if decision == "approved":
                        issue["human_status"] = "confirmed"
                        issue["final_status"] = "confirmed"
                        issue["needs_re_review"] = False
                    elif decision == "disputed":
                        issue["human_status"] = "disputed"
                        issue["final_status"] = "disputed"
                        issue["needs_re_review"] = True
                        issue["recommended_reviewer"] = self._recommended_reviewer(issue)
                    issue["human_reason"] = event.get("reason") or event.get("explanation") or ""
        return issues

    def _reviewer_agreement(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for issue in issues:
            topic = issue.get("type") or issue.get("section") or "general"
            grouped[topic].append(issue)
        agreement: List[Dict[str, Any]] = []
        for topic, items in grouped.items():
            agents = sorted({agent for item in items for agent in item.get("source_agents", [])})
            if len(agents) > 1:
                agreement.append({
                    "topic": topic,
                    "agents": agents,
                    "description": f"Multiple reviewers related this issue to '{topic}'.",
                })
        return agreement

    def review(self, state: Optional[Dict[str, Any]] = None, rigor_review: Optional[Dict[str, Any]] = None, clarity_review: Optional[Dict[str, Any]] = None, novelty_review: Optional[Dict[str, Any]] = None, human_feedback: Optional[List[Dict[str, Any]]] = None, review_history: Optional[List[Dict[str, Any]]] = None) -> MetaReviewOutput:
        if state is not None:
            reviews = {name: state.get(f"{name}_review", {}) or {} for name in ("rigor", "clarity", "novelty")}
            human = state.get("human_feedback") or []
            history = state.get("review_history") or []
        else:
            reviews = {"rigor": rigor_review or {}, "clarity": clarity_review or {}, "novelty": novelty_review or {}}
            human = human_feedback or []
            history = review_history or []

        raw_issues: List[Dict[str, Any]] = []
        for agent_name, review in reviews.items():
            for item in review.get("issues", []) or []:
                raw_issues.append(self._normalize_issue(item, agent_name))

        merged_issues = self._detect_duplicates(raw_issues)
        merged_issues = self._apply_human_feedback(merged_issues, human)
        conflicts = self._detect_conflicts(merged_issues)
        re_review_requests: List[Dict[str, Any]] = []
        for issue in merged_issues:
            matched = None
            for conflict in conflicts:
                if issue["id"] in conflict.issue_ids:
                    matched = conflict
                    break
            re_review_requests.append(self._determine_re_review(issue, matched, next((f for f in human if f.get("issue_id") == issue["id"]), None)))

        for issue in merged_issues:
            if issue.get("needs_re_review") is None:
                issue["needs_re_review"] = False
            issue["recommended_reviewer"] = issue.get("recommended_reviewer") or self._recommended_reviewer(issue)
            if issue.get("evidence_status") == "insufficient":
                issue["needs_re_review"] = True
            if issue.get("human_status") == "disputed":
                issue["needs_re_review"] = True

        buckets = defaultdict(list)
        for issue in merged_issues:
            severity_key = (issue.get("final_severity") or issue.get("severity") or "Medium").title()
            buckets[severity_key].append(issue)

        actions = [issue.get("recommendation", "") for issue in merged_issues if issue.get("recommendation")]
        summary = f"The Meta-Reviewer consolidated {len(merged_issues)} issue(s) across rigor, clarity, and novelty reviews and identified {len(conflicts)} meaningful conflict(s)."

        review_output = MetaReviewOutput(
            reviewer="meta",
            summary=summary,
            overall_assessment="The specialist reviews were combined and normalized to identify duplicate findings, reviewer conflicts, and reassessment priorities.",
            issues=merged_issues,
            critical_issues=buckets.get("Critical", []),
            high_priority_issues=buckets.get("High", []),
            medium_priority_issues=buckets.get("Medium", []),
            low_priority_issues=buckets.get("Low", []),
            reviewer_agreement=self._reviewer_agreement(merged_issues),
            conflicts=conflicts,
            resolved_conflicts=[],
            re_review_requests=re_review_requests,
            human_feedback=human,
            recommended_actions=actions,
            final_summary=f"The final review consolidates {len(merged_issues)} issue(s), with {len(conflicts)} conflict(s) and {sum(1 for r in re_review_requests if r.get('needs_re_review'))} re-review request(s).",
            retrieval_summary="No external retrieval was performed by the Meta-Reviewer; it reasoned only over specialist review outputs.",
            review_history=history,
        )
        review_output.issues = [MetaIssue.model_validate(issue) for issue in merged_issues]
        return review_output


async def review_meta_review(rigor_review: Optional[Dict[str, Any]] = None, clarity_review: Optional[Dict[str, Any]] = None, novelty_review: Optional[Dict[str, Any]] = None, human_feedback: Optional[List[Dict[str, Any]]] = None, review_history: Optional[List[Dict[str, Any]]] = None) -> MetaReviewOutput:
    return MetaReviewerAgent().review(rigor_review=rigor_review, clarity_review=clarity_review, novelty_review=novelty_review, human_feedback=human_feedback, review_history=review_history)


def check_conflicts(state: Dict[str, Any]) -> Dict[str, Any]:
    agent = MetaReviewerAgent()
    out = agent.review(state)
    state["conflicts"] = [conflict.model_dump() for conflict in out.conflicts]
    return state


def run_meta_reviewer(state: Dict[str, Any]) -> Dict[str, Any]:
    out = MetaReviewerAgent().review(state)
    state["meta_review"] = out.model_dump()
    state["conflicts"] = [c.model_dump() for c in out.conflicts]
    state["re_review_requests"] = out.re_review_requests
    state["reflection_loops"] = state.get("reflection_loops", 0) + (1 if out.conflicts else 0)
    return state


async def run_meta_review(rigor_review: Optional[Dict[str, Any]] = None, clarity_review: Optional[Dict[str, Any]] = None, novelty_review: Optional[Dict[str, Any]] = None, human_feedback: Optional[List[Dict[str, Any]]] = None, review_history: Optional[List[Dict[str, Any]]] = None) -> MetaReviewOutput:
    return await review_meta_review(rigor_review, clarity_review, novelty_review, human_feedback, review_history)
