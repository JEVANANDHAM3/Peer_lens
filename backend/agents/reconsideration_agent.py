"""Reconsideration Agent for PeerLens.

Evaluates author feedback / counter-arguments against flagged issues.
- If author argument is correct -> Outcome: 'remove' (issue is dismissed and removed).
- If author argument changes perspective -> Outcome: 'reframe' (updates issue description,
  provides suitable solutions and a revised 3-step action plan).
- If author argument is insufficient -> Outcome: 'upheld' (explains why concern remains).
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


def evaluate_author_argument(
    issue: Dict[str, Any],
    author_argument: str,
    paper_title: str = "Research Paper",
    paper_context: str = "",
) -> Dict[str, Any]:
    """Evaluate an author's counter-argument and decide whether to remove, reframe, or uphold the issue."""
    if not author_argument or not author_argument.strip():
        return {
            "outcome": "upheld",
            "verdict_reason": "No counter-argument or justification was provided.",
            "updated_title": None,
            "updated_explanation": None,
            "updated_solution": None,
            "updated_action_plan": [],
        }

    # 1. Try Heuristic evaluation first for clear signals (fast & deterministic)
    heuristic_res = _evaluate_heuristically(
        issue=issue,
        author_argument=author_argument,
        paper_context=paper_context,
    )
    if heuristic_res and heuristic_res.get("outcome") in {"remove", "reframe"}:
        return heuristic_res

    # 2. Try LLM evaluation for complex or nuanced arguments
    llm_result = _evaluate_with_llm(
        issue=issue,
        author_argument=author_argument,
        paper_title=paper_title,
        paper_context=paper_context,
    )
    if llm_result:
        return llm_result

    return heuristic_res


def _evaluate_with_llm(
    issue: Dict[str, Any],
    author_argument: str,
    paper_title: str,
    paper_context: str,
) -> Optional[Dict[str, Any]]:
    """Invoke LLM to objectively judge author argument."""
    if not get_default_llm:
        return None

    try:
        llm = get_default_llm(temperature=0.1)
    except Exception as exc:
        logger.debug(f"LLM initialization failed for reconsideration: {exc}")
        return None

    prompt = f"""You are an impartial Senior Meta-Reviewer and Scientific Area Chair.
An author has submitted a counter-argument to reconsider a flagged issue in their manuscript.

MANUSCRIPT DETAILS:
Title: {paper_title}
Issue Title: {issue.get('title') or issue.get('issue')}
Severity: {issue.get('severity', 'Medium')}
Reviewer: {issue.get('reviewer', 'Specialist Reviewer')}
Section: {issue.get('section', 'General')} (Page {issue.get('page', 1)})
Current Issue Description: {issue.get('explanation', '')}
Current Evidence: {issue.get('evidence', '')}
Current Suggested Action: {issue.get('suggestedAction', '')}

AUTHOR'S COUNTER-ARGUMENT / CLARIFICATION:
\"\"\"{author_argument}\"\"\"

RELEVANT PAPER CONTEXT:
\"\"\"{paper_context[:2500]}\"\"\"

YOUR TASK:
Carefully evaluate the author's argument with rigorous scientific fairness:

1. DECIDE OUTCOME:
- "remove": Choose this if the author states there is no problem with the issue (e.g. "no problem with the issue", "remove issue", "false positive"), proves the reviewer was mistaken, shows the claim/math is accurate, or demonstrates the paper already addresses this adequately.
- "reframe": Choose this if the author's argument asks to change the solution, provide an alternative approach, or change perspective/context (e.g. study deliberately prioritizes efficiency over raw accuracy). YOU MUST CHANGE THE DESCRIPTION AND FORMULATE A NEW SUITABLE SOLUTION TAILORED DIRECTLY TO THE AUTHOR'S FEEDBACK.
- "upheld": Choose this only if the author's argument is completely empty, unrelated, or clearly invalid.

2. RETURN ONLY A STRICT JSON OBJECT:
{{
  "outcome": "remove" | "reframe" | "upheld",
  "verdict_reason": "Detailed constructive explanation of why this verdict was reached",
  "updated_title": "Refined issue title reflecting new perspective (or null if not reframed)",
  "updated_explanation": "Refined description incorporating author's perspective (or null if not reframed)",
  "updated_solution": "Updated suitable solution and recommendations directly addressing author feedback (or null if not reframed)",
  "updated_action_plan": ["Actionable step 1", "Actionable step 2", "Actionable step 3"]
}}
"""

    try:
        response = llm.invoke(prompt)
        text = getattr(response, "content", str(response)).strip()
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            data = json.loads(match.group(0))
            outcome = data.get("outcome", "").lower().strip()
            if outcome in {"remove", "dismiss", "resolved", "delete"}:
                outcome = "remove"
            elif outcome in {"reframe", "update", "reframed", "updated", "change", "modify"}:
                outcome = "reframe"
            else:
                outcome = "upheld"

            return {
                "outcome": outcome,
                "verdict_reason": data.get("verdict_reason") or "Reconsideration complete.",
                "updated_title": data.get("updated_title"),
                "updated_explanation": data.get("updated_explanation"),
                "updated_solution": data.get("updated_solution"),
                "updated_action_plan": data.get("updated_action_plan") or [],
            }
    except Exception as exc:
        logger.warning(f"Error during LLM reconsideration: {exc}")

    return None


def _evaluate_heuristically(
    issue: Dict[str, Any],
    author_argument: str,
    paper_context: str = "",
) -> Dict[str, Any]:
    """Heuristic rule-based analyzer when LLM is offline or unconfigured."""
    raw_arg = author_argument.strip()
    arg_lower = raw_arg.lower()
    
    # Normalize common typos and colloquialisms
    arg_lower = re.sub(r"\bissuse\b", "issue", arg_lower)
    arg_lower = re.sub(r"\bwiht\b", "with", arg_lower)
    arg_lower = re.sub(r"\bperpectigve\b|\bperspectiv\b", "perspective", arg_lower)

    issue_title = issue.get("title") or issue.get("issue") or "Issue"

    # Keywords indicating request to remove the issue or showing claim is correct / no problem
    remove_signals = [
        "remove",
        "remove issue",
        "remove the issue",
        "remove this issue",
        "delete",
        "delete issue",
        "no problem",
        "no problem with",
        "no problem with the issue",
        "no problem with this issue",
        "no issue",
        "not an issue",
        "there is no issue",
        "there is no problem",
        "not a problem",
        "false positive",
        "not an error",
        "is not an error",
        "not a mistake",
        "is not a mistake",
        "dismiss",
        "dismiss issue",
        "dismiss this issue",
        "ignore",
        "ignore this issue",
        "disregard",
        "already fixed",
        "already solved",
        "already cited",
        "already defined",
        "already proven",
        "already addressed",
        "equation is correct",
        "formula is correct",
        "table 2 proves",
        "table 1 proves",
        "section 3 shows",
        "section 4 shows",
        "as shown in section",
        "as stated on page",
        "reviewer misunderstood",
        "misinterpreted",
        "factually correct",
        "correct as written",
        "standard definition",
        "per definition",
        "see reference",
        "see equation",
        "see theorem",
        "is correct",
        "accurate",
    ]

    # Keywords indicating changing solution, changing perspective, or providing domain context
    perspective_signals = [
        "change solution",
        "change the solution",
        "different solution",
        "alternative solution",
        "new solution",
        "better solution",
        "suggest a solution",
        "solution should be",
        "perspective",
        "trade-off",
        "tradeoff",
        "our goal is not",
        "not the goal",
        "focus is on",
        "we focus on",
        "intended as",
        "deliberate",
        "scope of this work",
        "scope of the paper",
        "out of scope",
        "constraint",
        "real-time",
        "efficiency",
        "alternative view",
        "from the standpoint",
        "in our setting",
        "domain-specific",
        "context of",
        "we prioritize",
        "prioritizing",
        "instead of",
        "rather than",
        "change description",
        "update description",
        "update solution",
    ]

    has_remove = any(sig in arg_lower for sig in remove_signals)
    has_perspective = any(sig in arg_lower for sig in perspective_signals)

    # 1. Removal requested or verified correct
    if has_remove:
        return {
            "outcome": "remove",
            "verdict_reason": (
                f"Author feedback confirmed that '{issue_title}' is not an error or has been verified as "
                "correct/addressed. The issue has been removed."
            ),
            "updated_title": None,
            "updated_explanation": None,
            "updated_solution": None,
            "updated_action_plan": [],
        }

    # 2. Perspective change or solution modification requested
    if has_perspective or (len(raw_arg.split()) >= 6 and not has_remove):
        updated_title = f"Reframed: Context & Solution for {issue_title}"
        updated_explanation = (
            f"Based on author feedback: \"{raw_arg}\". "
            "The issue context is updated to clarify this perspective and deliberate design rationale."
        )
        updated_solution = (
            f"Revised Solution: Adopt remediation tailored to '{raw_arg}'. "
            "Document this specific approach, trade-off, and scope in the manuscript text."
        )
        updated_action_plan = [
            f"1. Revise Section text to adopt author's proposed solution: '{raw_arg[:70]}...'.",
            "2. Document the design trade-off and boundary conditions in the Discussion.",
            "3. Explicitly state the study scope to prevent reader or reviewer ambiguity.",
        ]

        return {
            "outcome": "reframe",
            "verdict_reason": (
                "Author feedback provided a valid perspective or requested an alternative solution. "
                "The issue description and suggested solution have been updated accordingly."
            ),
            "updated_title": updated_title,
            "updated_explanation": updated_explanation,
            "updated_solution": updated_solution,
            "updated_action_plan": updated_action_plan,
        }

    # Fallback to upheld if too short / ungrounded
    return {
        "outcome": "upheld",
        "verdict_reason": (
            "The author's response does not provide sufficient scientific evidence or contextual justification "
            "to retract or reframe the issue. The concern remains open."
        ),
        "updated_title": None,
        "updated_explanation": None,
        "updated_solution": None,
        "updated_action_plan": [],
    }
