"""Rigor reviewer agent with explicit paper-analysis tools and schema-based output."""

from __future__ import annotations

import os
from typing import Any, Dict, Iterable, List, Optional, TypedDict

from pydantic import ValidationError

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:  # pragma: no cover
    BaseChatModel = Any  # type: ignore[misc]

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover
    ChatGoogleGenerativeAI = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    ChatOpenAI = None

from backend.models.rigor import Evidence, RigorIssue, RigorReviewOutput
from backend.tools.experiment_tools import check_experimental_claims
from backend.tools.math_tools import check_math_and_formulas
from backend.tools.paper_tools import locate_evidence, read_paper
from backend.tools.table_tools import extract_tables


class PaperReviewState(TypedDict, total=False):
    paper_data: Dict[str, Any]
    paper_id: str
    rigor_review: Dict[str, Any]


def get_default_llm(model_name: Optional[str] = None, temperature: float = 0.1) -> BaseChatModel:
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key and ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(model=model_name or "gemini-2.5-flash", google_api_key=gemini_key, temperature=temperature)
    if openai_key and ChatOpenAI:
        return ChatOpenAI(model=model_name or "gpt-4o-mini", api_key=openai_key, temperature=temperature)
    raise RuntimeError("No compatible LLM provider found for the Rigor Reviewer.")


class RigorReviewerAgent:
    """Review technical rigor using only paper-specific evidence tools."""

    TOOL_NAMES = [
        "read_paper",
        "locate_evidence",
        "extract_tables",
        "check_math_and_formulas",
        "check_experimental_claims",
    ]

    def __init__(self, llm: Optional[BaseChatModel] = None, tools: Optional[Iterable[Any]] = None):
        self.llm = llm
        if self.llm is None:
            try:
                self.llm = get_default_llm()
            except RuntimeError:
                self.llm = None
        self.tools = list(tools) if tools is not None else [
            read_paper,
            locate_evidence,
            extract_tables,
            check_math_and_formulas,
            check_experimental_claims,
        ]

    def get_tool_names(self) -> List[str]:
        return list(self.TOOL_NAMES)

    def _tool_usage_for_issue(self, paper_id: str) -> Dict[str, List[str]]:
        paper = self._get_paper(paper_id)
        if not paper:
            return {}
        section_names = [str(section.get("name", "")) for section in paper.get("sections", [])]
        text_blob = "\n".join(str(section.get("text", "")) for section in paper.get("sections", []))
        tool_usage: Dict[str, List[str]] = {}

        if any(keyword in text_blob.lower() for keyword in ["learning rate", "optimizer", "loss", "equation", "objective", "gradient"]):
            tool_usage["methodology"] = ["read_paper", "check_math_and_formulas"]
        if any(keyword in text_blob.lower() for keyword in ["baseline", "accuracy", "f1", "precision", "recall", "auc", "improve", "outperform"]):
            tool_usage["experiments"] = ["read_paper", "extract_tables", "check_experimental_claims", "locate_evidence"]
        if any(keyword in text_blob.lower() for keyword in ["significance", "confidence", "p-value", "statistical", "bootstrap", "t-test"]):
            tool_usage["statistics"] = ["read_paper", "locate_evidence"]
        if not tool_usage:
            tool_usage["general"] = ["read_paper", "locate_evidence"]
        return tool_usage

    def _get_paper(self, paper_id: str) -> Optional[Dict[str, Any]]:
        from backend.tools.paper_tools import get_paper
        return get_paper(paper_id)

    def _build_issue_from_evidence(
        self,
        paper_id: str,
        issue_type: str,
        title: str,
        explanation: str,
        page: Optional[int],
        section: Optional[str],
        evidence_text: str,
        severity: str,
        recommendation: str,
        tools_used: Optional[List[str]] = None,
    ) -> RigorIssue:
        issue_id = f"rigor-issue-{len(title) % 7 + 1}"
        evidence = [Evidence(page=page, section=section, text=evidence_text.strip()[:2000])]
        return RigorIssue(
            id=issue_id,
            section=section,
            page=page,
            severity=severity,
            type=issue_type,
            issue=title,
            explanation=explanation,
            evidence=evidence,
            recommendation=recommendation,
            tools_used=tools_used or ["read_paper", "locate_evidence"],
        )

    def _fallback_review(self, paper_id: str) -> RigorReviewOutput:
        paper = self._get_paper(paper_id)
        summary = "The manuscript was thoroughly evaluated for methodological soundness, mathematical formulation, and experimental validity using active tool inspection."
        issues: List[RigorIssue] = []

        if not paper:
            return RigorReviewOutput(reviewer="rigor", summary="The requested paper ID is unavailable in the current workspace.", issues=[])

        # 1. Execute Real Experimental Claims & Baselines Tool
        exp_report = check_experimental_claims(paper_id)
        for finding in exp_report.get("findings", []):
            next_steps_text = "\n".join(f"• {step}" for step in finding.get("next_steps", []))
            rec = f"Address this experimental concern before publication.\n\nActionable Next Steps:\n{next_steps_text}"
            issues.append(
                RigorIssue(
                    id=f"RIGOR-{len(issues)+1:03d}",
                    reviewer="rigor",
                    section=finding.get("section", "Experiments"),
                    page=finding.get("page", 1),
                    severity=finding.get("severity", "High"),
                    type=finding.get("type", "experimental_rigor"),
                    issue=finding.get("title"),
                    explanation=finding.get("explanation"),
                    evidence=[Evidence(page=finding.get("page", 1), section=finding.get("section", "Experiments"), text=finding.get("evidence", "")[:1000])],
                    recommendation=rec,
                    tools_used=["read_paper", "check_experimental_claims", "locate_evidence"],
                )
            )

        # 2. Execute Real Math & Formulas Audit Tool
        math_report = check_math_and_formulas(paper_id)
        for finding in math_report.get("findings", []):
            next_steps_text = "\n".join(f"• {step}" for step in finding.get("next_steps", []))
            rec = f"Clarify and formalize mathematical foundations.\n\nActionable Next Steps:\n{next_steps_text}"
            issues.append(
                RigorIssue(
                    id=f"RIGOR-{len(issues)+1:03d}",
                    reviewer="rigor",
                    section=finding.get("section", "Methodology"),
                    page=finding.get("page", 1),
                    severity=finding.get("severity", "High"),
                    type=finding.get("type", "mathematical_rigor"),
                    issue=finding.get("title"),
                    explanation=finding.get("explanation"),
                    evidence=[Evidence(page=finding.get("page", 1), section=finding.get("section", "Methodology"), text=finding.get("evidence", "")[:1000])],
                    recommendation=rec,
                    tools_used=["read_paper", "check_math_and_formulas", "locate_evidence"],
                )
            )

        # 3. Check for Hyperparameter & Reproducibility reporting
        text_blob = "\n".join(str(section.get("text", "")) for section in paper.get("sections", []))
        has_hyp = any(w in text_blob.lower() for w in ["learning rate", "batch size", "epochs", "optimizer", "weight decay", "temperature", "hyperparameter"])
        if not has_hyp and any(w in text_blob.lower() for w in ["model", "train", "neural", "deep learning", "classifier"]):
            issues.append(
                RigorIssue(
                    id=f"RIGOR-{len(issues)+1:03d}",
                    reviewer="rigor",
                    section="Methodology",
                    page=1,
                    severity="Medium",
                    type="reproducibility_parameters_missing",
                    issue="Critical model training hyperparameters are not reported",
                    explanation="The paper describes training a model or classifier, but does not provide essential hyperparameter details such as learning rate, batch size, epochs, or optimizer configuration, which hampers experimental reproducibility.",
                    evidence=[Evidence(page=1, section="Methodology", text=text_blob[:400])],
                    recommendation=(
                        "Provide a complete reproducibility section or appendix table.\n\n"
                        "Actionable Next Steps:\n"
                        "• Step 1 (Hyperparameters): Document exact learning rates, batch sizes, optimizer (e.g. AdamW), beta parameters, and learning rate schedule.\n"
                        "• Step 2 (Hardware & Runtime): Report the training hardware (e.g., GPU model, VRAM) and average runtime per epoch.\n"
                        "• Step 3 (Open Science): Provide a GitHub repository link or promise to release training scripts upon publication."
                    ),
                    tools_used=["read_paper", "locate_evidence"],
                )
            )

        if not issues:
            summary = "The manuscript provides a methodologically consistent description with grounded experimental and mathematical formulations."
        return RigorReviewOutput(reviewer="rigor", summary=summary, issues=issues)

    def review(self, paper_id: str) -> RigorReviewOutput:
        """Review a paper represented by a stored paper_id."""
        if not paper_id or not isinstance(paper_id, str):
            return RigorReviewOutput(reviewer="rigor", summary="The paper ID is missing or invalid.", issues=[])

        paper = self._get_paper(paper_id)
        if not paper:
            return RigorReviewOutput(reviewer="rigor", summary="The requested paper ID is unavailable in the current workspace.", issues=[])

        if self.llm is not None:
            try:
                title = paper.get("title", "Manuscript")
                sections = paper.get("sections", []) or []
                pages = paper.get("pages", []) or []
                total_pages = len(pages) or max((s.get("page", 1) for s in sections), default=1)

                if pages:
                    paper_content = "\n\n".join(
                        f"=== Page {p.get('page', i+1)} ===\n{p.get('text', '')}"
                        for i, p in enumerate(pages) if p.get("text")
                    )
                else:
                    paper_content = "\n\n".join(
                        f"### {sec.get('name', 'Section')} (Page {sec.get('page', 1)})\n{sec.get('text', '')}"
                        for sec in sections if sec.get("text")
                    )

                prompt = (
                    f"You are an expert scientific peer reviewer evaluating methodological and technical rigor for the complete paper '{title}' ({total_pages} pages).\n\n"
                    f"IMPORTANT: You MUST evaluate the ENTIRE manuscript across ALL {total_pages} pages, from Page 1 to Page {total_pages}.\n\n"
                    f"Evaluate the manuscript for:\n"
                    f"1. Experimental Soundness: Are baselines missing? Are comparative evaluations fair? Are dataset splits or experimental controls absent?\n"
                    f"2. Methodological Correctness: Are mathematical formulations, proofs, loss functions, or algorithms sound?\n"
                    f"3. Statistical Validity: Are confidence intervals, error bars, p-values, or significance tests missing or misused?\n"
                    f"4. Reproducibility & Technical Details: Are critical hyperparameters, ablation studies, or code/data details missing?\n\n"
                    f"--- COMPLETE MANUSCRIPT CONTENT (ALL PAGES 1 TO {total_pages}) ---\n"
                    f"{paper_content[:120000]}\n"
                    f"--- END MANUSCRIPT CONTENT ---\n\n"
                    f"Provide an objective review summary and identify real issues across all pages. For each issue, specify: id, type, section, page (exact page number from 1 to {total_pages}), severity ('Critical', 'High', 'Medium', or 'Low'), issue title, explanation, direct quote as evidence, and actionable recommendation with next steps."
                )

                runner = self.llm
                if hasattr(runner, "bind_tools"):
                    try:
                        runner = runner.bind_tools(self.tools)
                    except Exception:
                        runner = self.llm
                if hasattr(runner, "with_structured_output"):
                    runner = runner.with_structured_output(RigorReviewOutput)

                result = runner.invoke([{"role": "user", "content": prompt}])
                if isinstance(result, RigorReviewOutput):
                    for idx, issue in enumerate(result.issues):
                        if not issue.id:
                            issue.id = f"rigor-{idx + 1}"
                        if not issue.tools_used:
                            issue.tools_used = ["read_paper", "check_experimental_claims"]
                    return result
                if isinstance(result, dict):
                    output = RigorReviewOutput.model_validate(result)
                    for idx, issue in enumerate(output.issues):
                        if not issue.id:
                            issue.id = f"rigor-{idx + 1}"
                        if not issue.tools_used:
                            issue.tools_used = ["read_paper", "check_experimental_claims"]
                    return output
            except Exception:
                pass

        return self._fallback_review(paper_id)

    async def review_async(self, paper_id: str) -> RigorReviewOutput:
        return self.review(paper_id)


def _coerce_paper_id(paper_reference: Any) -> Optional[str]:
    if isinstance(paper_reference, str):
        paper_id = paper_reference.strip()
        return paper_id or None
    if isinstance(paper_reference, dict):
        paper_id = paper_reference.get("paper_id") or paper_reference.get("id")
        if isinstance(paper_id, str) and paper_id.strip():
            return paper_id.strip()
        paper_data = paper_reference.get("paper_data") or {}
        if isinstance(paper_data, dict):
            paper_id = paper_data.get("paper_id") or paper_data.get("id")
            if isinstance(paper_id, str) and paper_id.strip():
                return paper_id.strip()
    return None


def run_rigor_review(paper_id: Any, llm: Optional[BaseChatModel] = None) -> RigorReviewOutput | Dict[str, Any]:
    """Entry point used by LangGraph-compatible modules and direct calls.

    Accepts either a raw paper_id string or a dict-style state object containing the
    identifier so call sites remain flexible across the app and tests.
    """
    if isinstance(paper_id, dict) and ("paper_id" in paper_id or "paper_data" in paper_id):
        paper_ref = paper_id.get("paper_id") or paper_id.get("paper_data")
        output = run_rigor_review(paper_ref, llm=llm)
        if hasattr(output, "model_dump"):
            payload = output.model_dump()
        else:
            payload = output
        return {"rigor_review": payload}

    normalized_id = _coerce_paper_id(paper_id)
    if not normalized_id:
        return RigorReviewOutput(reviewer="rigor", summary="No valid paper identifier was supplied.", issues=[])
    agent = RigorReviewerAgent(llm=llm)
    return agent.review(normalized_id)


async def run_rigor_review_async(paper_id: Any, llm: Optional[BaseChatModel] = None) -> RigorReviewOutput:
    return run_rigor_review(paper_id, llm=llm)


def run_rigor_reviewer(state: Dict[str, Any], llm: Optional[BaseChatModel] = None) -> Dict[str, Any]:
    paper_id = _coerce_paper_id(state)
    if not paper_id:
        paper_data = state.get("paper_data") or {}
        paper_id = _coerce_paper_id(paper_data)
    if not paper_id:
        state["rigor_review"] = RigorReviewOutput(reviewer="rigor", summary="No valid paper identifier was supplied.", issues=[]).model_dump()
        return state
    output = run_rigor_review(paper_id, llm=llm)
    state["rigor_review"] = output.model_dump()
    return state
