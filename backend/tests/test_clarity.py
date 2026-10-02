from __future__ import annotations

from typing import Any

import pytest

from backend.agents.clarity_agent import ClarityReviewerAgent, run_clarity_reviewer
from backend.models.clarity import ClarityReviewOutput
from backend.tools.clarity_tools import check_section_consistency, check_terminology
from backend.tools.paper_tools import clear_papers, register_paper
from backend.tools.reference_tools import check_reference_consistency


class FakeLLM:
    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        return {
            "reviewer": "clarity",
            "summary": "The manuscript has several clarity concerns that affect reader comprehension.",
            "issues": [
                {
                    "id": "CLARITY-001",
                    "section": "Methodology",
                    "page": 3,
                    "severity": "medium",
                    "type": "undefined_term",
                    "issue": "The acronym TAM is used before it is defined.",
                    "explanation": "The manuscript introduces the acronym before providing the full term or definition.",
                    "evidence": [{"page": 3, "section": "Methodology", "text": "The model uses TAM without definition."}],
                    "recommendation": "Define the acronym the first time it appears.",
                    "tools_used": ["read_paper", "check_terminology", "locate_evidence"],
                }
            ],
        }


@pytest.fixture(autouse=True)
def setup_clarity_papers():
    clear_papers()
    register_paper(
        "clarity-paper",
        {
            "paper_id": "clarity-paper",
            "title": "Adaptive Fusion Network",
            "sections": [
                {"name": "Abstract", "page": 1, "text": "We present the Adaptive Fusion Network (AFN). The AFN improves performance."},
                {"name": "Introduction", "page": 2, "text": "The system contains three modules. We show the AFN architecture. The model uses TAM without definition. Figure 3 shows the architecture."},
                {"name": "Methodology", "page": 3, "text": "The system contains four modules. Our method includes a temporal attention module (TAM). The TAM aligns the features across views."},
                {"name": "Results", "page": 5, "text": "As shown in Figure 3 and Table 2, the method achieves strong performance. Table 3 reports ablation studies."},
                {"name": "References", "page": 10, "text": "[1] Smith et al. (2023). [2] Smith et al. (2023). [3] Brown et al. (2024)."},
            ],
            "pages": [
                {"page": 1, "text": "We present the Adaptive Fusion Network (AFN). The AFN improves performance."},
                {"page": 2, "text": "The system contains three modules. We show the AFN architecture. The model uses TAM without definition. Figure 3 shows the architecture."},
                {"page": 3, "text": "The system contains four modules. Our method includes a temporal attention module (TAM). The TAM aligns the features across views."},
                {"page": 5, "text": "As shown in Figure 3 and Table 2, the method achieves strong performance. Table 3 reports ablation studies."},
            ],
            "references": [
                {"title": "Smith et al. (2023)", "year": 2023},
                {"title": "Smith et al. (2023)", "year": 2023},
                {"title": "Brown et al. (2024)", "year": 2024},
                {"title": "Chen et al. (2025)", "year": 2025},
            ],
            "figures": [{"figure_number": 2, "caption": "Architecture overview"}],
            "tables": [{"table_number": 2, "caption": "Performance metrics"}],
        },
    )
    yield
    clear_papers()


def test_check_terminology_detects_undefined_abbreviation_and_term_usage():
    result = check_terminology("clarity-paper")
    assert "observations" in result
    observations = result["observations"]
    assert any("TAM" in str(item) for item in observations)


def test_check_section_consistency_detects_module_count_difference():
    result = check_section_consistency("clarity-paper", "Introduction", "Methodology")
    assert result["inconsistencies"]
    assert any("three modules" in str(item).lower() or "four modules" in str(item).lower() for item in result["inconsistencies"])


def test_reference_consistency_detects_missing_reference_and_duplicate_entries():
    result = check_reference_consistency("clarity-paper")
    assert result["observations"]
    assert "duplicate" in " ".join(str(item).lower() for item in result["observations"]) or "missing" in " ".join(str(item).lower() for item in result["observations"])


def test_clarity_agent_tool_selection_uses_relevant_tools_for_specific_issue():
    agent = ClarityReviewerAgent(llm=FakeLLM())
    tool_names = agent.select_tools_for_issue("clarity-paper")
    assert "read_paper" in tool_names
    assert "check_terminology" in tool_names or "check_section_consistency" in tool_names or "check_reference_consistency" in tool_names


def test_clarity_agent_structured_output_and_evidence_inclusion():
    response = FakeLLM().invoke(None)
    result = ClarityReviewerAgent(llm=FakeLLM()).review("clarity-paper")
    assert isinstance(result, ClarityReviewOutput)
    assert result.issues
    assert result.issues[0].evidence[0].page == 3
    assert result.issues[0].tools_used


def test_run_clarity_reviewer_preserves_compatibility():
    state = run_clarity_reviewer({"paper_id": "clarity-paper"})
    assert state["clarity_review"]["reviewer"] == "clarity"
    assert "summary" in state["clarity_review"]


def test_reference_and_figure_checks_detect_wrong_figure_reference():
    result = check_reference_consistency("clarity-paper")
    assert result["issues"]
    issue_text = " ".join(str(issue) for issue in result["issues"]).lower()
    assert "figure" in issue_text or "table" in issue_text or "reference" in issue_text
