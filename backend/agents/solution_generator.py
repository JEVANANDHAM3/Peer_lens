"""Solution Generator Agent for PeerLens.

Generates actionable 3-step remediation plans for review issues ON DEMAND.
This module is only invoked when the user explicitly clicks 'Give Report',
ensuring that solutions are never generated during the review pipeline.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from backend.agents.clarity_agent import get_default_llm
except Exception:
    get_default_llm = None  # type: ignore[assignment]


def generate_solutions(
    issues: List[Dict[str, Any]],
    paper_context: str = "",
    paper_title: str = "Research Paper",
) -> List[Dict[str, Any]]:
    """Generate actionable solutions for each issue.
    
    Tries LLM-based generation first; falls back to heuristic templates.
    
    Args:
        issues: List of review issues (each with id, issue, section, severity, etc.)
        paper_context: Full or partial manuscript text for context
        paper_title: Title of the manuscript
        
    Returns:
        List of issues enriched with 'suggestedAction' and 'actionPlan' fields.
    """
    if not issues:
        return []

    # Try LLM-based solution generation
    llm_result = _generate_with_llm(issues, paper_context, paper_title)
    if llm_result:
        return llm_result

    # Fallback to heuristic generation
    return _generate_heuristically(issues)


def _generate_with_llm(
    issues: List[Dict[str, Any]],
    paper_context: str,
    paper_title: str,
) -> Optional[List[Dict[str, Any]]]:
    """Use LLM to generate tailored solutions for each issue."""
    if not get_default_llm:
        return None

    try:
        llm = get_default_llm(temperature=0.2)
    except Exception as exc:
        logger.debug(f"LLM initialization failed for solution generation: {exc}")
        return None

    enriched_issues: List[Dict[str, Any]] = []

    for issue in issues:
        issue_copy = dict(issue)
        issue_title = issue.get("issue") or issue.get("title") or "Review finding"
        section = issue.get("section") or "General"
        severity = issue.get("severity") or "Medium"
        explanation = issue.get("explanation") or ""
        evidence = issue.get("evidence") or []
        if isinstance(evidence, list):
            evidence_text = " • ".join(
                str(e.get("text", "") if isinstance(e, dict) else e) for e in evidence
            )
        else:
            evidence_text = str(evidence)

        prompt = f"""You are an expert scientific manuscript advisor.
Generate a precise, actionable remediation plan for a flagged issue in the paper '{paper_title}'.

ISSUE DETAILS:
- Title: {issue_title}
- Section: {section}
- Severity: {severity}
- Explanation: {explanation}
- Evidence: {evidence_text}

PAPER CONTEXT (excerpt):
\"\"\"{paper_context[:2000]}\"\"\"

Generate a JSON response with:
{{
  "suggestedAction": "A clear, 1-2 sentence recommended action",
  "actionPlan": [
    "Step 1: Specific, actionable first step",
    "Step 2: Specific, actionable second step",
    "Step 3: Specific, actionable third step"
  ]
}}
"""
        try:
            response = llm.invoke(prompt)
            text = getattr(response, "content", str(response)).strip()
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                data = json.loads(match.group(0))
                issue_copy["suggestedAction"] = data.get("suggestedAction") or issue_copy.get("recommendation") or "Address this finding."
                issue_copy["actionPlan"] = data.get("actionPlan") or []
                issue_copy["recommendation"] = issue_copy["suggestedAction"]
                issue_copy["solution_pending"] = False
                enriched_issues.append(issue_copy)
                continue
        except Exception as exc:
            logger.debug(f"LLM solution generation failed for issue {issue.get('id')}: {exc}")

        # If LLM fails for this specific issue, use heuristic
        enriched_issues.append(_heuristic_solution(issue_copy))

    return enriched_issues


def _generate_heuristically(issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate template-based solutions when LLM is unavailable."""
    return [_heuristic_solution(dict(issue)) for issue in issues]


def _heuristic_solution(issue: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a heuristic solution for a single issue based on its type and severity."""
    issue_type = (issue.get("type") or "general").lower()
    severity = (issue.get("severity") or "Medium").lower()
    section = issue.get("section") or "General"
    issue_title = issue.get("issue") or issue.get("title") or "Review finding"

    # Type-specific action plans
    if "experiment" in issue_type or "baseline" in issue_type or "statistical" in issue_type:
        suggested = f"Strengthen experimental validation in section '{section}' with additional baselines and statistical tests."
        plan = [
            f"Step 1 (Baselines): Add at least two additional comparative baselines relevant to '{section}'.",
            "Step 2 (Statistical Tests): Include confidence intervals, p-values, or error bars for all reported metrics.",
            "Step 3 (Reproducibility): Document exact hyperparameters, hardware, and random seeds used.",
        ]
    elif "math" in issue_type or "formula" in issue_type or "proof" in issue_type:
        suggested = f"Formalize mathematical claims in '{section}' with complete derivations or proofs."
        plan = [
            f"Step 1 (Derivation): Provide a step-by-step derivation for the key formula in '{section}'.",
            "Step 2 (Notation): Define all mathematical symbols in a notation table or glossary.",
            "Step 3 (Verification): Cross-check the derivation against established results or provide a proof sketch.",
        ]
    elif "term" in issue_type or "acronym" in issue_type or "definition" in issue_type:
        suggested = f"Define all technical terms and acronyms upon first use in '{section}'."
        plan = [
            "Step 1 (Definition): Spell out the full form alongside each abbreviation at its first occurrence.",
            "Step 2 (Glossary): Add a notation/terminology table summarizing all specialized terms.",
            "Step 3 (Consistency): Search-and-replace to ensure uniform naming throughout the manuscript.",
        ]
    elif "reference" in issue_type or "citation" in issue_type:
        suggested = f"Reconcile internal citations and bibliography references in '{section}'."
        plan = [
            "Step 1 (Numbering): Verify that all Figure/Table numbers increment sequentially.",
            "Step 2 (Bibliography): Confirm every cited bracket [N] maps to a valid References entry.",
            "Step 3 (Callouts): Ensure every figure and table is explicitly discussed in the body text.",
        ]
    elif "novelty" in issue_type or "overlap" in issue_type or "literature" in issue_type:
        suggested = f"Differentiate the contribution from related work cited in '{section}'."
        plan = [
            "Step 1 (Literature): Add a dedicated comparison paragraph in Section 2 (Related Work).",
            "Step 2 (Contrast Table): Create a structured comparison highlighting architectural/methodological differences.",
            "Step 3 (Claim Calibration): Narrow broad novelty claims to specify the exact novel mechanism.",
        ]
    elif "consistency" in issue_type or "contradiction" in issue_type:
        suggested = f"Resolve cross-section inconsistencies related to '{section}'."
        plan = [
            f"Step 1 (Audit): Trace the concept across Abstract, Methodology, and Results in '{section}'.",
            "Step 2 (Unification): Ensure identical counts, names, and design claims across all sections.",
            "Step 3 (Cross-Reference): Use precise section pointers (e.g., 'as detailed in Section 3.2').",
        ]
    elif "reproducibility" in issue_type or "hyperparameter" in issue_type:
        suggested = "Provide a complete reproducibility section with all training details."
        plan = [
            "Step 1 (Hyperparameters): Document learning rates, batch sizes, optimizer, and schedule.",
            "Step 2 (Hardware): Report training hardware (GPU model, VRAM) and average runtime.",
            "Step 3 (Open Science): Provide a GitHub repository link or promise code release upon publication.",
        ]
    else:
        suggested = f"Address the identified concern in '{section}' with supporting evidence."
        plan = [
            f"Step 1: Review and revise the relevant passage in '{section}' to address the concern.",
            "Step 2: Add supporting evidence, citations, or clarifications as needed.",
            "Step 3: Verify the change is consistent with the rest of the manuscript.",
        ]

    # Severity-based priority note
    if severity in ("critical", "high"):
        suggested = f"[Priority] {suggested}"

    issue["suggestedAction"] = suggested
    issue["actionPlan"] = plan
    issue["recommendation"] = suggested
    issue["solution_pending"] = False
    return issue
