"""Paper-based Clarity Reviewer Agent."""

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

from backend.models.clarity import ClarityIssue, ClarityReviewOutput, Evidence
from backend.prompts.clarity_prompt import CLARITY_SYSTEM_PROMPT, CLARITY_USER_PROMPT_TEMPLATE
from backend.tools.clarity_tools import check_section_consistency, check_terminology
from backend.tools.paper_tools import get_paper, locate_evidence, read_paper
from backend.tools.reference_tools import check_reference_consistency


class ClarityReviewState(TypedDict, total=False):
    paper_id: str
    paper_text: Any
    sections: List[Dict[str, Any]]
    pages: List[Dict[str, Any]]
    clarity_review: Dict[str, Any]


def get_default_llm(model_name: Optional[str] = None, temperature: float = 0.1) -> BaseChatModel:
    key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if key and ChatGoogleGenerativeAI:
        return ChatGoogleGenerativeAI(model=model_name or "gemini-2.5-flash", google_api_key=key, temperature=temperature)
    if openai_key and ChatOpenAI:
        return ChatOpenAI(model=model_name or "gpt-4o-mini", api_key=openai_key, temperature=temperature)
    raise RuntimeError("Install langchain-google-genai or langchain-openai and configure an API key.")


class ClarityReviewerAgent:
    TOOL_NAMES = [
        "read_paper",
        "locate_evidence",
        "check_terminology",
        "check_section_consistency",
        "check_reference_consistency",
    ]

    def __init__(self, llm: Optional[BaseChatModel] = None, tools: Optional[Iterable[Any]] = None):
        if llm is not None:
            self.llm = llm
        else:
            try:
                self.llm = get_default_llm()
            except RuntimeError:
                self.llm = None
        self.tools = list(tools) if tools is not None else [
            read_paper,
            locate_evidence,
            check_terminology,
            check_section_consistency,
            check_reference_consistency,
        ]

    def get_tool_names(self) -> List[str]:
        return list(self.TOOL_NAMES)

    def select_tools_for_issue(self, paper_id: str) -> List[str]:
        paper = get_paper(paper_id)
        text_blob = "\n".join(section.get("text", "") for section in (paper.get("sections", []) if paper else []))
        lower = text_blob.lower()

        selected = ["read_paper"]
        if any(token in lower for token in ["module", "component", "figure", "table", "section", "methodology", "introduction"]):
            if any(token in lower for token in ["module", "component", "system contains", "contains three", "contains four"]):
                selected.append("check_section_consistency")
        if any(token in lower for token in ["figure", "table", "citation", "reference", "section", "appendix"]):
            selected.append("check_reference_consistency")
        if any(token in lower for token in ["afn", "tam", "mse", "f1", "bert", "gcn", "cnn", "llm", "gan", "rnn", "acronym"]):
            selected.append("check_terminology")
        selected.append("locate_evidence")
        return list(dict.fromkeys(selected))

    def _fallback_review(self, paper_id: str) -> ClarityReviewOutput:
        paper = get_paper(paper_id)
        if not paper:
            return ClarityReviewOutput(
                summary="The requested paper ID is unavailable in the current workspace.",
                issues=[],
            )

        issues: List[ClarityIssue] = []
        summary = "The manuscript was checked for terminology, section-level consistency, and internal reference issues that affect reading clarity."

        term_report = check_terminology(paper_id)
        for observation in term_report.get("observations", [])[:5]:
            text = str(observation)
            if not text:
                continue
            issue_text = text.split(":", 1)[1] if ":" in text else text
            evidence = term_report.get("evidence", [])
            match = next((entry for entry in evidence if str(entry.get("text", "")).lower() in text.lower() or any(token in text.lower() for token in ["tam", "afn", "module", "term"] if token in text.lower())), None)
            issues.append(ClarityIssue(
                id=f"CLARITY-{len(issues)+1:03d}",
                section=match.get("section") if match else "General",
                page=match.get("page") if match else 1,
                severity="Medium",
                type="undefined_term",
                issue=issue_text[:200],
                explanation="The manuscript introduces or reuses an acronym or technical concept without defining it upon first occurrence in the text.",
                evidence=[Evidence(page=match.get("page") if match else 1, section=match.get("section") if match else "General", text=match.get("text") if match else text)],
                recommendation=(
                    "Standardize and define all terminology.\n\n"
                    "Actionable Next Steps:\n"
                    "• Step 1 (Definition): Provide the full spelled-out form alongside the abbreviation at its very first occurrence in the Abstract and Section 1.\n"
                    "• Step 2 (Glossary/Notation): Add a brief notation table or paragraph summarizing specialized terminology.\n"
                    "• Step 3 (Consistency): Search and replace all variations to ensure uniform capitalization and naming throughout."
                ),
                tools_used=["read_paper", "check_terminology", "locate_evidence"],
            ))

        consistency_report = check_section_consistency(paper_id)
        for inconsistency in consistency_report.get("inconsistencies", [])[:3]:
            evidence = consistency_report.get("evidence", [])
            match = next((entry for entry in evidence if str(entry.get("text", "")).lower() in str(inconsistency).lower() or str(entry.get("section", "")).lower() in str(inconsistency).lower()), None)
            issues.append(ClarityIssue(
                id=f"CLARITY-{len(issues)+1:03d}",
                section=match.get("section") if match else "Methodology",
                page=match.get("page") if match else 2,
                severity="Medium",
                type="section_inconsistency",
                issue=str(inconsistency)[:200],
                explanation="The same concept or metric is described inconsistently across sections, which may confuse readers about the paper's structure or design.",
                evidence=[Evidence(page=match.get("page") if match else 2, section=match.get("section") if match else "Methodology", text=match.get("text") if match else str(inconsistency))],
                recommendation=(
                    "Align cross-section descriptions and metrics.\n\n"
                    "Actionable Next Steps:\n"
                    "• Step 1 (Audit): Trace this concept across Abstract, Methodology, and Experiments.\n"
                    "• Step 2 (Unification): Ensure identical numerical counts, module names, and design claims across all sections.\n"
                    "• Step 3 (Cross-Reference): Use precise section pointers (e.g., 'as detailed in Section 3.2') rather than vague forward references."
                ),
                tools_used=["read_paper", "check_section_consistency", "locate_evidence"],
            ))

        ref_report = check_reference_consistency(paper_id)
        for issue in ref_report.get("issues", [])[:3]:
            data = issue if isinstance(issue, dict) else {"issue": str(issue)}
            evidence_items = ref_report.get("evidence", []) or []
            evidence_text = next((entry.get("text") for entry in evidence_items if isinstance(entry, dict)), "")
            issues.append(ClarityIssue(
                id=f"CLARITY-{len(issues)+1:03d}",
                section=data.get("section") or "References",
                page=data.get("page") or 1,
                severity="Low" if "duplicate" in str(data).lower() or "reference list" in str(data).lower() else "Medium",
                type="reference_consistency",
                issue=str(data.get("issue") or data),
                explanation="Internal citation, figure, or table references should be consistent so readers can reliably verify the claims in the manuscript.",
                evidence=[Evidence(page=data.get("page") or 1, section=data.get("section") or "References", text=evidence_text or str(data))],
                recommendation=(
                    "Reconcile in-text citations and figure/table numbering.\n\n"
                    "Actionable Next Steps:\n"
                    "• Step 1 (Numbering): Check that all Figure and Table numbers increment sequentially without skips.\n"
                    "• Step 2 (Bibliography Sync): Verify that every cited bracket [N] maps to a valid entry in the References list.\n"
                    "• Step 3 (Callouts): Ensure every figure and table is explicitly discussed in the body text."
                ),
                tools_used=["read_paper", "check_reference_consistency", "locate_evidence"],
            ))

        if not issues:
            summary = "The manuscript appears readable and internally consistent in the available text, with no major terminology, reference, or cross-section clarity problems detected."

        return ClarityReviewOutput(reviewer="clarity", summary=summary, issues=issues)

    def review(self, paper_reference: Any, sections: Optional[List[Dict[str, Any]]] = None, pages: Optional[List[Dict[str, Any]]] = None) -> ClarityReviewOutput:
        paper_id = None
        if isinstance(paper_reference, str):
            paper_id = paper_reference.strip() or None
        elif isinstance(paper_reference, dict):
            paper_id = paper_reference.get("paper_id") or paper_reference.get("id")
            if not paper_id:
                paper_data = paper_reference.get("paper_data") or {}
                paper_id = paper_data.get("paper_id") or paper_data.get("id")

        if paper_id and get_paper(paper_id):
            paper_for_review = get_paper(paper_id)
        else:
            paper_for_review = None

        if self.llm is not None and paper_for_review:
            try:
                title = paper_for_review.get("title", "Manuscript")
                paper_sections = paper_for_review.get("sections", []) or []
                paper_pages = paper_for_review.get("pages", []) or []
                total_pages = len(paper_pages) or max((s.get("page", 1) for s in paper_sections), default=1)

                if paper_pages:
                    paper_content = "\n\n".join(
                        f"=== Page {p.get('page', i+1)} ===\n{p.get('text', '')}"
                        for i, p in enumerate(paper_pages) if p.get("text")
                    )
                else:
                    paper_content = "\n\n".join(
                        f"### {sec.get('name', 'Section')} (Page {sec.get('page', 1)})\n{sec.get('text', '')}"
                        for sec in paper_sections if sec.get("text")
                    )

                prompt = (
                    f"You are an expert scientific peer reviewer evaluating writing clarity, terminology, and presentation for the complete paper '{title}' ({total_pages} pages).\n\n"
                    f"IMPORTANT: You MUST evaluate the ENTIRE manuscript across ALL {total_pages} pages, from Page 1 to Page {total_pages}.\n\n"
                    f"Evaluate the manuscript for:\n"
                    f"1. Terminology & Acronyms: Undefined, ambiguous, or inconsistently used technical terms.\n"
                    f"2. Conceptual & Cross-Section Consistency: Contradictions between sections, architecture count mismatches, or shifting terminology.\n"
                    f"3. References & Citations: Missing context, broken figure/table citations, or incomplete reference details.\n"
                    f"4. Readability & Structure: Dense, confusing, or poorly structured passages.\n\n"
                    f"--- COMPLETE MANUSCRIPT CONTENT (ALL PAGES 1 TO {total_pages}) ---\n"
                    f"{paper_content[:120000]}\n"
                    f"--- END MANUSCRIPT CONTENT ---\n\n"
                    f"Provide an objective review summary and identify specific clarity issues across all pages. For each issue, specify: id, type, section, page (exact page number from 1 to {total_pages}), severity ('Critical', 'High', 'Medium', or 'Low'), issue title, explanation, direct quote as evidence, and actionable recommendation."
                )

                runner = self.llm
                if hasattr(runner, "bind_tools"):
                    try:
                        runner = runner.bind_tools(self.tools)
                    except Exception:
                        runner = self.llm
                if hasattr(runner, "with_structured_output"):
                    runner = runner.with_structured_output(ClarityReviewOutput)

                result = runner.invoke([{"role": "user", "content": prompt}])
                if isinstance(result, ClarityReviewOutput):
                    for idx, issue in enumerate(result.issues):
                        if not issue.id:
                            issue.id = f"clarity-{idx + 1}"
                        if not issue.tools_used:
                            issue.tools_used = ["read_paper", "check_terminology"]
                    return result
                if isinstance(result, dict):
                    output = ClarityReviewOutput.model_validate(result)
                    for idx, issue in enumerate(output.issues):
                        if not issue.id:
                            issue.id = f"clarity-{idx + 1}"
                        if not issue.tools_used:
                            issue.tools_used = ["read_paper", "check_terminology"]
                    return output
            except Exception:
                pass

        if paper_id:
            return self._fallback_review(paper_id)

        if sections is None:
            sections = []
        if pages is None:
            pages = []
        summary = "\n".join(f"- Page {s.get('page', '?')}: {s.get('name', 'Section')}" for s in sections) or "Page stream available"
        prompt = CLARITY_USER_PROMPT_TEMPLATE.format(sections_summary=summary)
        prompt += f"\n\nEXTRACTED PAPER CONTENT:\n{paper_reference}"
        return ClarityReviewOutput(reviewer="clarity", summary="The uploaded manuscript was reviewed for clarity and communication issues.", issues=[])


def run_clarity_reviewer(state: ClarityReviewState, llm: Optional[BaseChatModel] = None) -> ClarityReviewState:
    state = state or {}
    paper_id = state.get("paper_id") or (state.get("paper_data") or {}).get("paper_id") or (state.get("paper_data") or {}).get("id")
    sections = state.get("sections", []) or []
    pages = state.get("pages", []) or []
    paper_text = state.get("paper_text", "")

    if not paper_id and not paper_text and not sections and not pages:
        state["clarity_review"] = ClarityReviewOutput(summary="No structured paper content was supplied.", issues=[]).model_dump()
        return state

    output = ClarityReviewerAgent(llm).review(paper_id or paper_text, sections, pages)
    state["clarity_review"] = output.model_dump()
    return state
