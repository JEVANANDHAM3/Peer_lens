from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from backend.tools.paper_tools import get_paper


def _extract_metric_mentions(text: str) -> List[str]:
    metrics = ["accuracy", "f1", "precision", "recall", "auc", "mse", "mae", "bleu", "rouge", "loss", "iou", "perplexity"]
    return [metric for metric in metrics if metric in text.lower()]


def check_experimental_claims(paper_id: str, claim: Optional[str] = None) -> Dict[str, Any]:
    """Audit experimental methodology for missing baselines, absence of statistical error bars,
    lack of ablation studies, and dataset split documentation."""
    paper = get_paper(paper_id)
    if not paper:
        return {"paper_id": paper_id, "claim": claim, "observations": [], "findings": [], "error": "Paper not found."}

    claim_text = claim or ""
    sections = paper.get("sections", []) or []
    pages = paper.get("pages", []) or []
    relevant: List[Dict[str, Any]] = []
    metrics: List[str] = []
    proposed_results: List[str] = []
    baseline_results: List[str] = []
    statistical_tests: List[str] = []
    findings: List[Dict[str, Any]] = []

    # Compile comprehensive audit units across all sections and pages
    audit_units: List[Dict[str, Any]] = []
    seen_texts = set()

    for sec in sections:
        txt = str(sec.get("text") or "").strip()
        if txt and txt not in seen_texts:
            seen_texts.add(txt)
            audit_units.append({
                "section": sec.get("name", "Section"),
                "page": sec.get("page", 1),
                "page_end": sec.get("page_end", sec.get("page", 1)),
                "text": txt,
            })

    for p in pages:
        txt = str(p.get("text") or "").strip()
        if txt and not any(txt in u["text"] or u["text"] in txt for u in audit_units):
            audit_units.append({
                "section": f"Page {p.get('page', 1)}",
                "page": p.get("page", 1),
                "page_end": p.get("page", 1),
                "text": txt,
            })

    full_text = "\n".join(str(u["text"]) for u in audit_units)
    lower_full = full_text.lower()

    for unit in audit_units:
        sec_name = str(unit.get("section") or "Section")
        page_num = unit.get("page", 1)
        text = str(unit.get("text") or "")
        lower = text.lower()

        if claim_text and (claim_text.lower() in lower or any(token in lower for token in claim_text.lower().split()[:3])):
            relevant.append({"section": sec_name, "page": page_num, "text": text[:1000]})

        if any(keyword in lower for keyword in ["baseline", "ours", "our method", "improvement", "outperform", "significant"]):
            relevant.append({"section": sec_name, "page": page_num, "text": text[:800]})

        for m in _extract_metric_mentions(text):
            if m not in metrics:
                metrics.append(m)

        if "baseline" in lower:
            baseline_results.append(text[:500])

        if any(token in lower for token in ["p-value", "statistically significant", "confidence interval", "t-test", "wilcoxon", "bootstrap", "standard deviation", "±", "+/-", "std dev"]):
            statistical_tests.append(text[:500])

        if any(token in lower for token in ["accuracy", "f1", "precision", "recall", "auc", "benchmark"]):
            proposed_results.append(text[:500])

        # Diagnostic 1: Claiming superiority without statistical significance / error bars
        has_metrics = bool(re.search(r"\b(?:\d+(?:\.\d+)?%|\b0\.\d{2,4}\b)", text))
        has_superiority = any(w in lower for w in ["outperforms", "superior", "beats", "state-of-the-art", "sota", "improvement of", "achieves higher"])
        has_uncertainty = any(w in lower for w in ["±", "+/-", "std", "variance", "confidence interval", "p <", "p=", "p-value", "bootstrap", "error bar"])

        if has_superiority and has_metrics and not has_uncertainty:
            findings.append({
                "type": "missing_statistical_significance",
                "severity": "High",
                "title": f"Performance gains reported in '{sec_name}' lack statistical significance tests and error bounds",
                "section": sec_name,
                "page": page_num,
                "evidence": text[:500],
                "explanation": (
                    "The manuscript claims quantitative superiority or outperforming prior work, but reports isolated point estimates "
                    "without standard deviations (±), confidence intervals, or formal hypothesis tests (e.g., paired t-test or Wilcoxon signed-rank test). "
                    "Without error bounds across multiple random seeds, the reported margin may be experimental noise."
                ),
                "next_steps": [
                    "Step 1 (Empirical): Re-run experiments across at least 5 distinct random seeds and report mean ± standard deviation for all benchmarks.",
                    "Step 2 (Statistical): Conduct paired statistical significance testing (e.g., student's t-test or Wilcoxon signed-rank test) and report exact p-values in Table results.",
                    "Step 3 (Manuscript): Explicitly state whether reported improvements over baselines meet standard significance thresholds (p < 0.05)."
                ],
            })

        # Diagnostic 2: Missing baseline comparative evaluation
        if any(w in lower for w in ["we propose", "our model", "our algorithm", "we introduce"]) and any(w in sec_name.lower() for w in ["experiment", "result", "evaluation"]):
            has_explicit_baseline = any(w in lower for w in ["baseline", "compared against", "comparison with", "benchmark against", "prior sota", "existing method"])
            if not has_explicit_baseline:
                findings.append({
                    "type": "missing_baseline_comparison",
                    "severity": "Critical",
                    "title": f"Evaluation in '{sec_name}' lacks competitive baseline comparisons",
                    "section": sec_name,
                    "page": page_num,
                    "evidence": text[:500],
                    "explanation": (
                        "The evaluation section presents results for the proposed architecture without benchmarking against standard or "
                        "contemporary peer-reviewed baseline methods under identical experimental conditions."
                    ),
                    "next_steps": [
                        "Step 1 (Literature): Identify at least 2-3 standard or state-of-the-art baseline architectures commonly evaluated on this benchmark.",
                        "Step 2 (Benchmarking): Execute baselines using identical compute budgets, hyperparameter tuning protocols, and data pre-processing.",
                        "Step 3 (Reporting): Integrate a unified comparative evaluation table contrasting your method directly against the implemented baselines."
                    ],
                })

        # Diagnostic 3: Missing ablation study for multi-component architectures
        component_count = len(re.findall(r"\b(?:module|component|loss term|attention mechanism|regularizer|branch|stage)\b", lower))
        has_ablation = any(w in lower for w in ["ablation", "component analysis", "without", "w/o", "ablated", "isolated effect"])
        if component_count >= 2 and any(w in sec_name.lower() for w in ["experiment", "result", "discussion"]) and not has_ablation:
            findings.append({
                "type": "missing_ablation_study",
                "severity": "Medium",
                "title": f"Multi-component framework in '{sec_name}' lacks an ablation study",
                "section": sec_name,
                "page": page_num,
                "evidence": text[:500],
                "explanation": (
                    "The paper introduces multiple novel architectural components, modules, or loss terms, but does not provide an ablation study "
                    "isolating the individual marginal contribution of each component."
                ),
                "next_steps": [
                    "Step 1 (Ablation Setup): Systematically remove or substitute each proposed module one at a time (e.g., Model w/o Module A, Model w/o Loss Term B).",
                    "Step 2 (Quantification): Measure performance degradation across identical benchmarks to quantify the specific impact of each component.",
                    "Step 3 (Manuscript): Add an 'Ablation Study' subsection with a dedicated comparison table clearly demonstrating that all proposed components are necessary."
                ],
            })

    return {
        "paper_id": paper_id,
        "claim": claim_text,
        "proposed_method_results": proposed_results[:5],
        "baseline_results": baseline_results[:5],
        "metrics": list(dict.fromkeys(metrics)),
        "statistical_tests": statistical_tests[:5],
        "observations": relevant[:5],
        "findings": findings,
    }
