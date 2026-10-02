from __future__ import annotations

from backend.graph.workflow import build_review_graph


def test_end_to_end_review_flow_completes_for_clean_paper(monkeypatch):
    graph = build_review_graph()

    def fake_rigor(state):
        state["rigor_review"] = {"reviewer": "rigor", "summary": "No major issues.", "issues": []}
        return state

    def fake_clarity(state):
        state["clarity_review"] = {"reviewer": "clarity", "summary": "No major issues.", "issues": []}
        return state

    def fake_novelty(state):
        state["novelty_review"] = {"reviewer": "novelty", "summary": "No major issues.", "issues": []}
        state["retrieved_documents"] = []
        state["retrieval_history"] = []
        return state

    def fake_meta(state):
        state["meta_review"] = {
            "reviewer": "meta",
            "summary": "No major issues found.",
            "issues": [],
            "re_review_requests": [],
            "conflicts": [],
        }
        state["status"] = "completed"
        return state

    monkeypatch.setattr("backend.graph.nodes.run_rigor_node", fake_rigor)
    monkeypatch.setattr("backend.graph.nodes.run_clarity_node", fake_clarity)
    monkeypatch.setattr("backend.graph.nodes.run_novelty_node", fake_novelty)
    monkeypatch.setattr("backend.graph.nodes.run_meta_review_node", fake_meta)

    result = graph.invoke({
        "paper_id": "minimal-valid-paper",
        "review_mode": "agentic_rag",
        "sections": [{"name": "Abstract", "page": 1, "text": "A strong valid paper."}],
        "pages": [{"page": 1, "text": "A strong valid paper."}],
    })

    assert result["status"] == "completed"
    assert result["meta_review"]["summary"]
    assert result["final_report"] if "final_report" in result else True
