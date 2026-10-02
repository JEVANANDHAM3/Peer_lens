from __future__ import annotations

from typing import Any

import pytest
from pydantic import BaseModel

from backend.agents.rigor_agent import RigorReviewerAgent, run_rigor_review
from backend.schemas.rigor import RigorReview
from backend.tools.experiment_tools import check_experimental_claims
from backend.tools.math_tools import check_math_and_formulas
from backend.tools.paper_tools import clear_papers, read_paper, locate_evidence, register_paper
from backend.tools.table_tools import extract_tables


class FakeLLM:
    def __init__(self, response: Any = None):
        self.response = response

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    def with_structured_output(self, schema):
        self.schema = schema
        return self

    def invoke(self, messages):
        if self.response is not None:
            return self.response
        return {
            "reviewer": "rigor",
            "summary": "The paper includes some technical concerns but no fatal issues were identified.",
            "issues": [
                {
                    "id": "rigor-issue-1",
                    "section": "Experiments",
                    "page": 8,
                    "severity": "High",
                    "type": "experimental_claim",
                    "issue": "The reported improvement may require stronger statistical evidence.",
                    "explanation": "The paper reports a small gain without a significance test.",
                    "evidence": [{"page": 8, "section": "Experiments", "text": "Accuracy improved by 0.4% over baseline."}],
                    "recommendation": "Add confidence intervals or paired significance tests.",
                    "tools_used": ["read_paper", "locate_evidence"],
                }
            ],
        }


@pytest.fixture(autouse=True)
def setup_papers():
    clear_papers()
    register_paper(
        "paper-1",
        {
            "title": "Benchmarking Graph Models",
            "sections": [
                {"name": "Abstract", "page": 1, "text": "Our method improves accuracy by 0.4% over baseline."},
                {"name": "Methodology", "page": 2, "text": "We train with learning rate 0.001 and use the Adam optimizer."},
                {"name": "Experiments", "page": 8, "text": "Accuracy improved by 0.4% over baseline; no significance test was reported."},
            ],
            "pages": [
                {"page": 1, "text": "Our method improves accuracy by 0.4% over baseline."},
                {"page": 2, "text": "We train with learning rate 0.001 and use the Adam optimizer."},
                {"page": 8, "text": "Accuracy improved by 0.4% over baseline; no significance test was reported."},
            ],
            "tables": [
                {
                    "page": 8,
                    "table_number": "Table 2",
                    "caption": "Performance Comparison",
                    "headers": ["Method", "Accuracy"],
                    "rows": [{"Method": "Baseline", "Accuracy": "91.2"}, {"Method": "Ours", "Accuracy": "91.6"}],
                }
            ],
        },
    )
    yield
    clear_papers()


def test_read_paper_returns_page_and_text():
    result = read_paper("paper-1", section="Methodology")
    assert result["page"] == 2
    assert "learning rate" in result["text"].lower()
    assert result["section"] == "Methodology"


def test_locate_evidence_finds_query():
    result = locate_evidence("paper-1", "no significance test was reported")
    assert result["matches"]
    assert result["matches"][0]["page"] == 8
    assert "significance" in result["matches"][0]["text"].lower()


def test_extract_tables_returns_structured_table():
    tables = extract_tables("paper-1", page=8)
    assert tables["tables"]
    assert tables["tables"][0]["table_number"] == "Table 2"
    assert tables["tables"][0]["headers"] == ["Method", "Accuracy"]


def test_check_math_and_formulas_returns_observations():
    result = check_math_and_formulas("paper-1", section="Methodology", query="learning rate")
    assert "observations" in result
    assert isinstance(result["observations"], list)


def test_check_experimental_claims_collects_metrics_and_claims():
    result = check_experimental_claims("paper-1", claim="accuracy improved")
    assert result["observations"]
    assert "accuracy" in " ".join(result["metrics"]).lower()


def test_rigor_agent_initializes_with_custom_llm():
    agent = RigorReviewerAgent(llm=FakeLLM())
    assert agent.llm is not None


def test_rigor_agent_tool_selection_includes_expected_tools():
    agent = RigorReviewerAgent(llm=FakeLLM())
    tool_names = agent.get_tool_names()
    assert {"read_paper", "locate_evidence", "extract_tables", "check_math_and_formulas", "check_experimental_claims"}.issubset(set(tool_names))


def test_rigor_agent_structured_output_and_evidence_inclusion():
    response = FakeLLM().invoke(None)
    agent = RigorReviewerAgent(llm=FakeLLM(response=response))
    result = agent.review("paper-1")
    assert isinstance(result, RigorReview)
    assert result.issues
    assert result.issues[0].evidence[0].page == 8
    assert result.issues[0].tools_used


def test_invalid_paper_handling():
    state = run_rigor_review({"paper_id": "missing-paper"})
    assert state["rigor_review"]["summary"]
    assert state["rigor_review"]["issues"] == []
