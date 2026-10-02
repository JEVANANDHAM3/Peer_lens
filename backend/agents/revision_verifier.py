"""Revision verifier for checking whether errors were changed in the revised manuscript."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from backend.agents.clarity_agent import get_default_llm
except ImportError:
    get_default_llm = None  # type: ignore[assignment]


def _extract_section_text(
    sections: List[Dict[str, Any]],
    target_section: str,
    full_text: str,
    target_page: Optional[int] = None,
) -> str:
    """Find text of a specific section in revised sections, by page or section name, or fallback to full text."""
    target_clean = re.sub(r"[^a-z0-9]", "", (target_section or "").lower())
    
    # 1. Match by section name
    if target_clean:
        for sec in sections:
            sec_name = re.sub(r"[^a-z0-9]", "", str(sec.get("name", "")).lower())
            if sec_name and (sec_name in target_clean or target_clean in sec_name):
                content = sec.get("content") or sec.get("text") or ""
                if content:
                    return str(content)

    # 2. Match by page number if provided
    if target_page is not None:
        for sec in sections:
            p_start = sec.get("page")
            p_end = sec.get("page_end", p_start)
            if p_start is not None and (p_start == target_page or (p_start <= target_page <= p_end)):
                content = sec.get("content") or sec.get("text") or ""
                if content:
                    return str(content)

    # 3. Fallback: if section name appears in full text, extract nearby text
    if target_section and target_section.lower() in full_text.lower():
        idx = full_text.lower().find(target_section.lower())
        start = max(0, idx - 100)
        end = min(len(full_text), idx + 2000)
        return full_text[start:end]

    return full_text[:2500] if full_text else ""


def _verify_issue_with_llm(
    llm: Any,
    issue: Dict[str, Any],
    revised_section_text: str,
) -> Optional[Dict[str, Any]]:
    """Use Gemini/LLM to verify whether an error has been changed or fixed in the revised text."""
    if not llm:
        return None

    title = issue.get("title") or issue.get("issue") or "Flagged Issue"
    section = issue.get("section") or "General"
    evidence = issue.get("evidence")
    if isinstance(evidence, list):
        evidence = " • ".join(str(e.get("text", "") or e) for e in evidence)
    evidence_str = str(evidence or issue.get("explanation") or "No excerpt provided")
    recommendation = issue.get("suggestedAction") or issue.get("recommendation") or "Address the concern"

    prompt = f"""You are an expert scientific manuscript reviewer.
Verify whether an author has changed and resolved a previously identified issue in their revised manuscript.

PREVIOUS IDENTIFIED ERROR:
- Title: {title}
- Section: {section}
- Original Flawed Evidence / Claim: {evidence_str}
- Reviewer Recommendation: {recommendation}

REVISED MANUSCRIPT SECTION TEXT:
\"\"\"
{revised_section_text[:2000]}
\"\"\"

TASK:
Determine if the author has corrected the error in the revised text.
Output STRICT JSON format:
{{
  "status": "resolved" or "persisting" or "partially_addressed",
  "resolved": true or false,
  "change_summary": "1-2 sentence description explaining what was changed and why the error is resolved or still persists",
  "revised_evidence": "A short excerpt from the revised text demonstrating the change or current state"
}}
"""
    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)
        text = text.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in text:
            text = text.split("```", 1)[1].split("```", 1)[0].strip()

        data = json.loads(text)
        return {
            "status": data.get("status", "persisting"),
            "resolved": bool(data.get("resolved", data.get("status") == "resolved")),
            "change_summary": str(data.get("change_summary") or "Revised text examined."),
            "revised_evidence": str(data.get("revised_evidence") or revised_section_text[:250]),
        }
    except Exception as exc:
        logger.warning(f"LLM verification failed for issue {issue.get('id')}: {exc}")
        return None


def _verify_issue_heuristically(
    issue: Dict[str, Any],
    original_paper_text: str,
    revised_paper_text: str,
    original_section_text: str,
    revised_section_text: str,
) -> Dict[str, Any]:
    """Heuristic rule-based check to verify if the error text was modified or resolved."""
    evidence = issue.get("evidence")
    if isinstance(evidence, list):
        evidence = " ".join(str(e.get("text", "") or e) for e in evidence)
    evidence_str = str(evidence or "").strip()

    title = str(issue.get("title") or issue.get("issue") or "")
    section = str(issue.get("section") or "General")

    orig_clean = re.sub(r"\s+", " ", original_paper_text).strip().lower()
    rev_clean = re.sub(r"\s+", " ", revised_paper_text).strip().lower()

    # Case 1: Paper was re-uploaded completely unchanged
    if orig_clean and rev_clean and orig_clean == rev_clean:
        return {
            "status": "persisting",
            "resolved": False,
            "change_summary": f"Manuscript text is identical to previous draft. Section '{section}' was not edited.",
            "revised_evidence": revised_section_text[:250] if revised_section_text else "No text changes detected.",
        }

    # Case 2: Specific evidence phrase still appears verbatim in the revised text
    if len(evidence_str) > 15 and evidence_str.lower() in rev_clean:
        return {
            "status": "persisting",
            "resolved": False,
            "change_summary": f"The problematic text in section '{section}' was found verbatim in the revised manuscript without modification.",
            "revised_evidence": evidence_str[:250],
        }

    # Case 3: The section text itself is identical between drafts
    orig_sec_clean = re.sub(r"\s+", " ", original_section_text).strip().lower()
    rev_sec_clean = re.sub(r"\s+", " ", revised_section_text).strip().lower()

    if orig_sec_clean and rev_sec_clean and orig_sec_clean == rev_sec_clean:
        return {
            "status": "persisting",
            "resolved": False,
            "change_summary": f"Section '{section}' remains unchanged from the previous draft; this issue was not addressed.",
            "revised_evidence": revised_section_text[:250] if revised_section_text else "Section unchanged.",
        }

    # Case 4: Evidence phrase was present previously and is now removed or modified
    if len(evidence_str) > 15 and evidence_str.lower() in orig_clean and evidence_str.lower() not in rev_clean:
        return {
            "status": "resolved",
            "resolved": True,
            "change_summary": f"The flagged text in section '{section}' was removed/rewritten in the revised draft.",
            "revised_evidence": revised_section_text[:250] if revised_section_text else "Section content revised.",
        }

    # Case 5: The section was edited
    if orig_sec_clean != rev_sec_clean:
        return {
            "status": "resolved",
            "resolved": True,
            "change_summary": f"Section '{section}' was revised to address '{title}'.",
            "revised_evidence": revised_section_text[:250] if revised_section_text else "Updated manuscript text.",
        }

    return {
        "status": "persisting",
        "resolved": False,
        "change_summary": f"No substantive changes addressing '{title}' found in section '{section}'.",
        "revised_evidence": revised_section_text[:250] if revised_section_text else "Unchanged.",
    }


def verify_revision_errors(
    previous_issues: List[Dict[str, Any]],
    original_paper_text: str,
    revised_paper_text: str,
    revised_sections: List[Dict[str, Any]],
    original_sections: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Comprehensive evaluation of whether previously flagged errors have been changed in the revision.

    Returns:
        Dict with verification metrics, per-issue verification results, and revision verdict.
    """
    llm = None
    if get_default_llm:
        try:
            llm = get_default_llm(temperature=0.0)
        except Exception:
            llm = None

    verified_issues: List[Dict[str, Any]] = []
    resolved_count = 0
    persisting_count = 0
    partial_count = 0

    for iss in previous_issues:
        section = iss.get("section") or "General"
        target_page = iss.get("page")
        orig_sec_text = _extract_section_text(original_sections or [], section, original_paper_text, target_page=target_page)
        revised_sec_text = _extract_section_text(revised_sections, section, revised_paper_text, target_page=target_page)

        # Attempt LLM verification first for deep semantic precision if section changed
        verdict = None
        if llm and orig_sec_text != revised_sec_text:
            verdict = _verify_issue_with_llm(llm, iss, revised_sec_text)

        if not verdict:
            verdict = _verify_issue_heuristically(
                issue=iss,
                original_paper_text=original_paper_text,
                revised_paper_text=revised_paper_text,
                original_section_text=orig_sec_text,
                revised_section_text=revised_sec_text,
            )

        status = verdict.get("status", "persisting")
        is_resolved = bool(verdict.get("resolved", status == "resolved"))

        if is_resolved:
            resolved_count += 1
        elif status == "partially_addressed":
            partial_count += 1
        else:
            persisting_count += 1

        verified_issues.append({
            "id": iss.get("id"),
            "title": iss.get("title") or iss.get("issue") or "Issue",
            "reviewer": iss.get("reviewer") or "Specialist Reviewer",
            "section": section,
            "severity": iss.get("severity") or "Medium",
            "original_explanation": iss.get("explanation") or "",
            "original_evidence": str(iss.get("evidence") or ""),
            "status": status,
            "resolved": is_resolved,
            "change_summary": verdict.get("change_summary", ""),
            "revised_evidence": verdict.get("revised_evidence", ""),
        })

    total = len(previous_issues)
    if total > 0 and resolved_count == total:
        verdict_str = "All Previous Errors Successfully Changed & Fixed"
    elif resolved_count > 0:
        verdict_str = f"{resolved_count} of {total} Errors Addressed; {persisting_count} Errors Still Persist"
    elif total > 0:
        verdict_str = "Errors Persist Unchanged; Further Revision Required"
    else:
        verdict_str = "No Previous Errors to Verify"

    return {
        "total_previous_issues": total,
        "errors_resolved": resolved_count,
        "errors_persisting": persisting_count,
        "errors_partially_addressed": partial_count,
        "verdict": verdict_str,
        "verified_issues": verified_issues,
    }
