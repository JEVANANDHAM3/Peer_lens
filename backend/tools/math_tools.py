from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from backend.tools.paper_tools import get_paper


def _collect_relevant_text(paper: Dict[str, Any], section: Optional[str] = None) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    seen = set()
    for item in paper.get("sections", []) or []:
        if section and item.get("name", "").lower() != section.lower():
            continue
        txt = str(item.get("text") or "").strip()
        if txt and txt not in seen:
            seen.add(txt)
            items.append({
                "section": item.get("name", "Section"),
                "page": item.get("page", 1),
                "text": txt,
            })
    for p in paper.get("pages", []) or []:
        txt = str(p.get("text") or "").strip()
        if txt and not any(txt in it["text"] or it["text"] in txt for it in items):
            items.append({
                "section": f"Page {p.get('page', 1)}",
                "page": p.get("page", 1),
                "text": txt,
            })
    return items


def check_math_and_formulas(
    paper_id: str,
    section: Optional[str] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """Inspect equations, notation definitions, loss formulations, and theoretical claims for mathematical rigor."""
    paper = get_paper(paper_id)
    if not paper:
        return {"paper_id": paper_id, "section": section, "query": query, "observations": [], "potential_issues": [], "findings": [], "error": "Paper not found."}

    section_items = _collect_relevant_text(paper, section)
    combined = "\n".join(item["text"] for item in section_items)
    if query:
        query_l = query.lower()
        section_items = [item for item in section_items if query_l in item["text"].lower()]
        combined = "\n".join(item["text"] for item in section_items)

    observations: List[Dict[str, Any]] = []
    potential_issues: List[Dict[str, Any]] = []
    findings: List[Dict[str, Any]] = []

    # 1. Detect Explicit Equations
    expressions = re.findall(r"(?:[A-Za-z0-9_]+\s*=\s*.*?(?:;|\n|$))|(?:\\[.*?\\]|\$\$.*?\$\$|\$.*?\$)", combined)
    for expr in expressions[:10]:
        observations.append({
            "type": "equation_observed",
            "text": expr.strip(),
            "evidence": expr.strip()[:500],
        })

    # 2. Check for Undefined Notation / Dense Symbol Bundles
    variable_pattern = re.compile(r"\b([A-Z][A-Za-z0-9_]*|[a-z][A-Za-z0-9_]*)\b")
    for item in section_items:
        text = item["text"]
        sec_name = item["section"]
        page_num = item["page"]
        
        # Check if loss function or optimization objective is claimed without formula
        has_loss_mention = any(w in text.lower() for w in ["loss function", "objective function", "cost function", "optimization goal", "we minimize", "we maximize"])
        has_loss_math = bool(re.search(r"(?:\\mathcal\{L\}|\bL\b|\bJ\b|\bLoss\b)\s*\(.*?\)\s*=", text) or re.search(r"\bmin(?:imize)?\b|\bmax(?:imize)?\b", text))
        
        if has_loss_mention and not has_loss_math and any(w in sec_name.lower() for w in ["method", "model", "approach", "algorithm"]):
            findings.append({
                "type": "undefined_objective_function",
                "severity": "High",
                "title": f"Optimization objective in '{sec_name}' lacks explicit mathematical formulation",
                "section": sec_name,
                "page": page_num,
                "evidence": text[:500],
                "explanation": (
                    "The manuscript discusses minimizing or optimizing an objective or loss function, but does not provide an explicit "
                    "mathematical definition specifying input arguments, weighting hyperparameters, or regularizer terms."
                ),
                "next_steps": [
                    "Step 1 (Formulation): Formulate the complete objective function in a numbered display equation (e.g., L_total = L_task + λ L_reg).",
                    "Step 2 (Notation): Explicitly define the domain and dimensionality of every parameter and variable in the equation.",
                    "Step 3 (Manuscript): Describe how gradients are computed or how the objective is optimized numerically."
                ],
            })

        # Check for unproven convergence or optimality assertions
        has_theoretic_assertion = any(w in text.lower() for w in ["guarantees convergence", "provably optimal", "linear convergence", "convergence theorem", "unbiased estimator", "without loss of generality"])
        has_proof = any(w in text.lower() for w in ["proof:", "proof of theorem", "appendix", "we prove", "qed", "lemma", "theorem"])
        
        if has_theoretic_assertion and not has_proof:
            findings.append({
                "type": "unsubstantiated_theoretical_claim",
                "severity": "Critical",
                "title": f"Theoretical convergence or optimality assertion in '{sec_name}' lacks proof or derivation",
                "section": sec_name,
                "page": page_num,
                "evidence": text[:500],
                "explanation": (
                    "The manuscript claims theoretical properties (such as guaranteed convergence or optimality) without providing "
                    "a mathematical proof, formal lemma, or reference to a detailed derivation in an appendix."
                ),
                "next_steps": [
                    "Step 1 (Formalization): State the theoretical claim formally as a Lemma, Proposition, or Theorem with explicit initial conditions and assumptions.",
                    "Step 2 (Derivation): Provide a step-by-step mathematical proof either in the main methodology section or in Appendix A.",
                    "Step 3 (Calibration): If theoretical guarantees hold only under bounded conditions, soften the text to state 'empirically observes convergence' rather than claiming universal guarantees."
                ],
            })

        # Check for undefined notation in equations
        for expr in expressions[:5]:
            tokens = variable_pattern.findall(expr)
            if len(tokens) >= 5 and "loss" not in expr.lower() and "objective" not in expr.lower():
                potential_issues.append({
                    "type": "notation_check",
                    "text": "The equation contains several symbols whose definitions should be verified in the surrounding text.",
                    "evidence": expr.strip(),
                })

    return {
        "paper_id": paper_id,
        "section": section,
        "query": query,
        "observations": observations,
        "potential_issues": potential_issues,
        "findings": findings,
    }
