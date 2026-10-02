from __future__ import annotations

from typing import Any, Dict, List

import pytest

from backend.agents.novelty_agent import NoveltyReviewerAgent, run_novelty_reviewer
from backend.models.novelty import NoveltyReviewOutput
from backend.rag.retriever import LiteratureRetriever
from backend.tools.rag_tools import compare_evidence, expand_search_query, find_related_work, retrieve_evidence, search_literature


class FakeRetriever:
    def __init__(self, docs=None):
        self.docs = docs or [
            {
                "title": "Multi-agent LLM review system",
                "content": "A multi-agent LLM system evaluates research papers for review and critique.",
                "source": "fake://paper-a",
                "similarity_score": 0.82,
            },
            {
                "title": "LLM reviewer agents for scientific writing",
                "content": "The framework uses multiple reviewer agents for peer review tasks.",
                "source": "fake://paper-b",
                "similarity_score": 0.61,
            },
        ]

    def search(self, query: str, max_results: int = 5):
        return self.docs[:max_results]

    def retrieve_evidence(self, query: str, top_k: int = 5, documents: list | None = None):
        items = documents or self.docs[:top_k]
        return [
            {
                "document": item["title"],
                "title": item["title"],
                "relevant_text": item.get("content", ""),
                "similarity_score": item.get("similarity_score", 0.4),
                "source": item.get("source", "fake"),
                "metadata": {},
            }
            for item in items
        ]


@pytest.fixture
def fake_retriever():
    return FakeRetriever()


def test_novelty_agent_initializes():
    agent = NoveltyReviewerAgent(retriever=FakeRetriever())
    assert agent.retriever is not None


def test_search_literature_returns_results():
    results = search_literature("multi-agent paper review", max_results=5, retriever=FakeRetriever())
    assert results
    assert "title" in results[0]


def test_retrieve_evidence_returns_documents():
    result = retrieve_evidence("multi-agent paper review", top_k=2, retriever=FakeRetriever())
    assert "documents" in result
    assert result["documents"][0]["document"]


def test_compare_evidence_detects_similarity():
    comparison = compare_evidence("We propose the first multi-agent framework for automated research paper review.", [
        {"title": "Multi-agent LLM review system", "content": "A multi-agent LLM system evaluates research papers for review."},
    ])
    assert comparison["similarity"] in {"high", "low"}
    assert comparison["overlap"]


def test_expand_search_query_refines_query():
    result = expand_search_query("multi-agent paper review", "need better novelty search")
    assert result["refined_queries"]
    assert any("novelty" in q.lower() for q in result["refined_queries"])


def test_find_related_work_returns_hits():
    result = find_related_work("Multi-agent review system", "A multi-agent LLM system evaluates research papers")
    assert result["related_work"]


def test_retrieval_decision_for_claim_requires_retrieval():
    agent = NoveltyReviewerAgent(retriever=FakeRetriever())
    claim = "We propose the first multi-agent framework for automated paper review."
    assert agent.requires_retrieval(claim) is True


def test_query_refinement_uses_iterative_stages():
    agent = NoveltyReviewerAgent(retriever=FakeRetriever())
    queries = agent.generate_queries("first multi-agent paper review system", "Initial retry for a broader novelty search")
    assert len(queries) >= 2
    assert queries[0]


def test_agentic_rag_limits_iterations_to_three():
    agent = NoveltyReviewerAgent(retriever=FakeRetriever())
    state = {
        "paper_text": "We propose the first multi-agent framework for automated academic paper review.",
        "sections": [{"name": "Introduction", "page": 2, "text": "We propose the first multi-agent framework for automated academic paper review."}],
    }
    result = agent.review(state, mode="agentic_rag")
    assert result["retrieval_iterations"] <= 3
    assert "retrieval_history" in result


def test_no_rag_mode_skips_retrieval():
    agent = NoveltyReviewerAgent(retriever=FakeRetriever())
    state = {
        "paper_text": "We propose the first multi-agent framework for automated academic paper review.",
        "sections": [{"name": "Introduction", "page": 2, "text": "We propose the first multi-agent framework for automated academic paper review."}],
    }
    result = agent.review(state, mode="no_rag")
    assert result["retrieval_required"] is False


def test_basic_rag_mode_runs_single_retrieval_cycle():
    agent = NoveltyReviewerAgent(retriever=FakeRetriever())
    state = {
        "paper_text": "We propose the first multi-agent framework for automated academic paper review.",
        "sections": [{"name": "Introduction", "page": 2, "text": "We propose the first multi-agent framework for automated academic paper review."}],
    }
    result = agent.review(state, mode="basic_rag")
    assert result["retrieval_required"] is True
    assert result["retrieval_iterations"] >= 1


def test_retrieval_failure_does_not_crash():
    class FailingRetriever:
        def search(self, query: str, max_results: int = 5):
            raise RuntimeError("retrieval unavailable")

        def retrieve_evidence(self, query: str, top_k: int = 5, documents: list | None = None):
            raise RuntimeError("retrieval unavailable")

    agent = NoveltyReviewerAgent(retriever=FailingRetriever())
    state = {"paper_text": "We propose the first multi-agent framework for automated paper review.", "sections": [{"name": "Introduction", "page": 2, "text": "We propose the first multi-agent framework for automated paper review."}]}
    result = agent.review(state, mode="agentic_rag")
    assert result["retrieval_required"] is True
    assert result["retrieval_history"][-1]["status"] == "failed"


def test_structured_output_remains_compatible():
    agent = NoveltyReviewerAgent(retriever=FakeRetriever())
    result = agent.review({
        "paper_text": "We propose the first multi-agent framework for automated academic paper review.",
        "sections": [{"name": "Introduction", "page": 2, "text": "We propose the first multi-agent framework for automated academic paper review."}],
    }, mode="agentic_rag")
    assert isinstance(result, dict)
    assert result["reviewer"] == "novelty"
    assert result["issues"] or result["claims_checked"]
