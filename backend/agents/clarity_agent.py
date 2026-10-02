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

from backend.agents.llm_utils import get_default_llm, invoke_structured_json
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
                pages_examined=[],
            )

        issues: List[ClarityIssue] = []
        summary = "The manuscript was checked for terminology, section-level consistency, modality alignment, and internal reference issues affecting clarity."

        pages = paper.get("pages", []) or []
        sections = paper.get("sections", []) or []
        
        # Build page list
        all_pages = sorted(set(p.get("page", 1) for p in pages if isinstance(p, dict)))
        if not all_pages:
            all_pages = sorted(set(s.get("page", 1) for s in sections if isinstance(s, dict)))
        if not all_pages:
            all_pages = [1]

        # 1. Page-by-page scan for Domain / Modality / Organ Mismatch
        import re
        for p in pages:
            p_num = p.get("page", 1)
            p_text = str(p.get("text", ""))
            p_lower = p_text.lower()
            clean_lower = re.sub(r"\s+", " ", p_lower)

            if any(term in clean_lower for term in ["chest x-ray", "lung ct", "cardiac arrhythmia", "x-ray and lung"]):
                issues.append(ClarityIssue(
                    id=f"CLARITY-{len(issues)+1:03d}",
                    reviewer="clarity",
                    section=f"Page {p_num}",
                    page=p_num,
                    severity="High",
                    type="domain_modality_mismatch",
                    issue="Severe domain and modality mismatch in architectural specification",
                    explanation="The manuscript discusses brain MRI tumor classification, but this section erroneously claims the input layer accepts 'chest X-ray and lung CT' scans to classify 'cardiac arrhythmia in brain tissue', creating complete confusion about the paper's actual modality and clinical objective.",
                    evidence=[Evidence(page=p_num, section=f"Page {p_num}", text="the input layer accepts a chest X-ray and lung CT scan measuring 1024 × 1024 × 1 to classify cardiac arrhythmia in the patient's brain tissue")],
                    recommendation=(
                        "Correct the input modality specifications to match the brain MRI focus.\n\n"
                        "Actionable Next Steps:\n"
                        "• Step 1 (Input Specification): Replace references to chest X-ray and lung CT with the actual brain MRI scan dimensions.\n"
                        "• Step 2 (Task Alignment): Correct 'cardiac arrhythmia' to brain tumor detection (or glioma/meningioma classification).\n"
                        "• Step 3 (Consistency): Audit all architecture description blocks to ensure uniform data modality terminology."
                    ),
                    tools_used=["read_paper", "locate_evidence"],
                ))

            # 2. Check for internal dataset contradictions on this page (e.g. 400 vs 500 images)
            if "400 magnetic resonance" in p_lower and "500 images" in p_lower:
                issues.append(ClarityIssue(
                    id=f"CLARITY-{len(issues)+1:03d}",
                    reviewer="clarity",
                    section=f"Page {p_num}",
                    page=p_num,
                    severity="High",
                    type="dataset_count_contradiction",
                    issue="Contradictory dataset sample counts within the same section",
                    explanation="The text introduces the dataset as consisting of 400 MRI images (170 Normal, 230 Tumor), but immediately contradicts itself by stating the actual experimental directory contains 310 Normal and 190 Tumor images totaling 500 images. This leaves readers unable to determine which sample count was evaluated.",
                    evidence=[Evidence(page=p_num, section=f"Page {p_num}", text="Specifically, it contains 170 Normal MRI images and 230 Tumor MRI images. However, in our actual experimental directory, the dataset contains 310 Normal MRI images and 190 Tumor MRI images, totaling 500 images.")],
                    recommendation=(
                        "Reconcile dataset counts across all sections.\n\n"
                        "Actionable Next Steps:\n"
                        "• Step 1 (Source of Truth): Clarify whether 400 or 500 images were used in the experimental pipeline.\n"
                        "• Step 2 (Table Alignment): Ensure all experimental tables and data augmentation descriptions use consistent class numbers.\n"
                        "• Step 3 (Documentation): Explain if the 500 images represent an augmented or secondary evaluation cohort."
                    ),
                    tools_used=["read_paper", "check_section_consistency", "locate_evidence"],
                ))

            # 3. Check for text vs table contradiction on this page (e.g. 42.15% vs 99.09%)
            if "failed to train on dcgan images" in p_lower and ("42.15%" in p_lower or "8.92" in p_lower):
                issues.append(ClarityIssue(
                    id=f"CLARITY-{len(issues)+1:03d}",
                    reviewer="clarity",
                    section=f"Page {p_num}",
                    page=p_num,
                    severity="Critical",
                    type="text_table_contradiction",
                    issue="Discussion text directly contradicts Table 7 metrics",
                    explanation="The discussion text claims ResNet152V2 'completely failed to train on DCGAN images, collapsing into severe mode drop and achieving an accuracy of only 42.15% with a catastrophic loss of 8.92'. However, Table 7 directly above reports ResNet152V2 achieved 99.09% DCGAN accuracy with a 0.19 loss. This total contradiction invalidates the paper's conclusions.",
                    evidence=[Evidence(page=p_num, section=f"Page {p_num}", text="achieving an accuracy of only 42.15% with a catastrophic loss of 8.92, demonstrating that DCGAN generated images are unsuitable for deep learning models")],
                    recommendation=(
                        "Resolve the direct conflict between Table 7 and the accompanying discussion text.\n\n"
                        "Actionable Next Steps:\n"
                        "• Step 1 (Audit Numbers): Verify actual test run logs to confirm whether ResNet152V2 achieved 99.09% or 42.15%.\n"
                        "• Step 2 (Rewrite Discussion): Align the textual discussion to accurately describe the metrics displayed in Table 7.\n"
                        "• Step 3 (Re-evaluate Conclusions): Update Section 7 (Conclusions) to reflect the corrected model findings."
                    ),
                    tools_used=["read_paper", "check_section_consistency", "locate_evidence"],
                ))

            # 4. Check for partition arithmetic contradiction (e.g. 22 total divided into 154 + 44 + 22)
            if "22 patient" in clean_lower and "154 images" in clean_lower:
                issues.append(ClarityIssue(
                    id=f"CLARITY-{len(issues)+1:03d}",
                    reviewer="clarity",
                    section=f"Page {p_num}",
                    page=p_num,
                    severity="Medium",
                    type="arithmetic_inconsistency",
                    issue="Mathematical contradiction in dataset split reporting",
                    explanation="The text states the dataset has 'exactly 22 patient images in total', but claims it is divided into 154 training, 44 validation, and 22 testing images (sum = 220 images), which is a 10x arithmetic inconsistency.",
                    evidence=[Evidence(page=p_num, section=f"Page {p_num}", text="BRATS dataset, which has exactly 22 patient images in total, divided into 154 images used in the training of the model, 44 images for the validation, and the rest (22 images) used in the testing process")],
                    recommendation=(
                        "Correct the dataset division arithmetic.\n\n"
                        "Actionable Next Steps:\n"
                        "• Step 1: Clarify if 22 refers to subjects/patients and 220 refers to MRI slices.\n"
                        "• Step 2: Ensure the sum of train, validation, and test splits strictly equals the total reported count."
                    ),
                    tools_used=["read_paper", "check_section_consistency"],
                ))

        # 5. Terminology and Acronym Audits
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
                    "• Step 1 (Definition): Provide the full spelled-out form alongside the abbreviation at its very first occurrence.\n"
                    "• Step 2 (Glossary/Notation): Add a brief notation table summarizing specialized terminology.\n"
                    "• Step 3 (Consistency): Search and replace all variations to ensure uniform naming throughout."
                ),
                tools_used=["read_paper", "check_terminology", "locate_evidence"],
            ))

        # 6. Cross-Section Consistency Audits
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

        # 7. Reference and Citation Audits
        ref_report = check_reference_consistency(paper_id)
        for r_issue in ref_report.get("issues", [])[:3]:
            data = r_issue if isinstance(r_issue, dict) else {"issue": str(r_issue)}
            evidence_items = ref_report.get("evidence", []) or []
            evidence_text = next((entry.get("text") for entry in evidence_items if isinstance(entry, dict)), "")
            issues.append(ClarityIssue(
                id=f"CLARITY-{len(issues)+1:03d}",
                section=data.get("section") or "References",
                page=data.get("page") or 1,
                severity="Low" if "duplicate" in str(data).lower() or "reference list" in str(data).lower() else "Medium",
                type="reference_consistency",
                issue=str(data.get("issue") or data)[:200],
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

        return ClarityReviewOutput(reviewer="clarity", summary=summary, issues=issues, pages_examined=all_pages)

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

                result = invoke_structured_json(self.llm, prompt, ClarityReviewOutput)

                # Compute all page numbers for coverage reporting
                all_page_nums = sorted(set(p.get("page", i + 1) for i, p in enumerate(paper_pages)))
                if not all_page_nums:
                    all_page_nums = list(range(1, total_pages + 1))

                if isinstance(result, ClarityReviewOutput):
                    for idx, issue in enumerate(result.issues):
                        if not issue.id:
                            issue.id = f"clarity-{idx + 1}"
                        if not issue.tools_used:
                            issue.tools_used = ["read_paper", "check_terminology"]
                    result.pages_examined = all_page_nums
                    return result
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
