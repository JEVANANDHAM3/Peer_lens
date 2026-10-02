from __future__ import annotations

from backend.agents.novelty_agent import NoveltyReviewerAgent


class FakeRetriever:
    def __init__(self, docs=None):
        self.docs = docs or [
            {
                "title": "Multi-agent review systems",
                "content": "A multi-agent system for paper review using iterative evidence gathering.",
                "source": "fake://a",
                "similarity_score": 0.82,
            },
            {
                "title": "Scientific novelty detection",
                "content": "The study compares novelty claims against prior literature and related work.",
                "source": "fake://b",
                "similarity_score": 0.55,
            },
        ]

    def search(self, query: str, max_results: int = 5):
        return self.docs[:max_results]

    def retrieve_evidence(self, query: str, top_k: int = 5, documents=None):
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


class FailingRetriever(FakeRetriever):
    def search(self, query: str, max_results: int = 5):
        raise RuntimeError("retrieval unavailable")

    def retrieve_evidence(self, query: str, top_k: int = 5, documents=None):
        raise RuntimeError("retrieval unavailable")


def test_no_rag_mode_skips_retrieval_and_keeps_structure():
    agent = NoveltyReviewerAgent(retriever=FakeRetriever())
    state = {
        "paper_text": "We propose the first multi-agent framework for automated paper review.",
        "sections": [{"name": "Introduction", "page": 2, "text": "We propose the first multi-agent framework for automated paper review."}],
    }
    result = agent.review(state, mode="no_rag")
    assert result["retrieval_required"] is False
    assert result["retrieval_iterations"] == 0
    assert result["reviewer"] == "novelty"


def test_basic_rag_mode_uses_single_retrieval_loop():
    agent = NoveltyReviewerAgent(retriever=FakeRetriever())
    state = {
        "paper_text": "We propose the first multi-agent framework for automated paper review.",
        "sections": [{"name": "Introduction", "page": 2, "text": "We propose the first multi-agent framework for automated paper review."}],
    }
    result = agent.review(state, mode="basic_rag")
    assert result["retrieval_required"] is True
    assert result["retrieval_iterations"] >= 1
    assert result["retrieval_history"]


def test_agentic_rag_happy_path_stops_after_sufficient_evidence():
    agent = NoveltyReviewerAgent(retriever=FakeRetriever())
    state = {
        "paper_text": "We propose the first multi-agent framework for automated paper review.",
        "sections": [{"name": "Introduction", "page": 2, "text": "We propose the first multi-agent framework for automated paper review."}],
    }
    result = agent.review(state, mode="agentic_rag")
    assert result["retrieval_required"] is True
    assert result["retrieval_iterations"] <= 3
    assert result["issues"] or result["claims_checked"]


def test_agentic_rag_respects_max_iteration_limit_on_insufficient_results():
    class WeakRetriever(FakeRetriever):
        def search(self, query: str, max_results: int = 5):
            return [{
                "title": "Different unrelated benchmark work",
                "content": "This paper studies image segmentation rather than review systems.",
                "source": "fake://weak",
                "similarity_score": 0.05,
            }]

    agent = NoveltyReviewerAgent(retriever=WeakRetriever())
    state = {
        "paper_text": "We propose the first multi-agent framework for automated paper review.",
        "sections": [{"name": "Introduction", "page": 2, "text": "We propose the first multi-agent framework for automated paper review."}],
    }
    result = agent.review(state, mode="agentic_rag")
    assert result["retrieval_iterations"] <= 3
    assert result["retrieval_history"]


def test_retrieval_failure_is_recorded_without_crashing():
    agent = NoveltyReviewerAgent(retriever=FailingRetriever())
    state = {
        "paper_text": "We propose the first multi-agent framework for automated paper review.",
        "sections": [{"name": "Introduction", "page": 2, "text": "We propose the first multi-agent framework for automated paper review."}],
    }
    result = agent.review(state, mode="agentic_rag")
    assert result["retrieval_required"] is True
    assert result["retrieval_history"][-1]["status"] == "failed"
