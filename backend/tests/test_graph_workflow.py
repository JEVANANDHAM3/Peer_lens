from __future__ import annotations

from types import SimpleNamespace

import backend.graph.nodes as graph_nodes
from backend.graph.workflow import build_review_graph


def _as_review(payload: dict):
    return SimpleNamespace(model_dump=lambda: payload)


def test_basic_graph_executes_specialists_then_meta(monkeypatch):
    def fake_rigor(state):
        state["rigor_review"] = {"reviewer": "rigor", "summary": "ok", "issues": [{"id": "RIGOR-001", "severity": "High", "issue": "Missing comparison"}]}
        return state

    def fake_clarity(state):
        state["clarity_review"] = {"reviewer": "clarity", "summary": "ok", "issues": []}
        return state

    def fake_novelty(state):
        state["novelty_review"] = {"reviewer": "novelty", "summary": "ok", "issues": []}
        return state

    def fake_meta(state):
        assert state.get("rigor_review")
        assert state.get("clarity_review")
        assert state.get("novelty_review")
        state["meta_review"] = {"reviewer": "meta", "summary": "ok", "issues": [], "re_review_requests": [], "conflicts": []}
        state["status"] = "completed"
        return state

    monkeypatch.setattr(graph_nodes, "run_rigor_node", fake_rigor)
    monkeypatch.setattr(graph_nodes, "run_clarity_node", fake_clarity)
    monkeypatch.setattr(graph_nodes, "run_novelty_node", fake_novelty)
    monkeypatch.setattr(graph_nodes, "run_meta_review_node", fake_meta)

    graph = build_review_graph()
    result = graph.invoke({
        "paper_id": "paper-1",
        "review_mode": "agentic_rag",
        "sections": [{"name": "Abstract", "page": 1, "text": "We propose a method."}],
        "pages": [{"page": 1, "text": "We propose a method."}],
    })

    assert result["rigor_review"]["issues"]
    assert result["clarity_review"]["issues"] == []
    assert result["novelty_review"]["issues"] == []
    assert result["status"] == "completed"


def test_graph_routes_selective_rerun_for_conflict(monkeypatch):
    graph = build_review_graph()

    def fake_rigor(state):
        state["rigor_review"] = {"reviewer": "rigor", "summary": "rechecked", "issues": [{"id": "RIGOR-001", "severity": "High", "issue": "Baseline comparison is now evidenced."}]}
        return state

    def fake_clarity(state):
        state["clarity_review"] = {"reviewer": "clarity", "summary": "ok", "issues": []}
        return state

    def fake_novelty(state):
        state["novelty_review"] = {"reviewer": "novelty", "summary": "ok", "issues": []}
        return state

    def fake_meta(state):
        if state.get("re_review_count", 0) == 0:
            state["meta_review"] = {"reviewer": "meta", "summary": "needs rerun", "issues": [], "re_review_requests": [{"issue_id": "RIGOR-001", "recommended_reviewer": "rigor"}], "conflicts": []}
            state["needs_human_feedback"] = False
            return state
        state["meta_review"] = {"reviewer": "meta", "summary": "resolved", "issues": [], "re_review_requests": [], "conflicts": []}
        state["status"] = "completed"
        return state

    monkeypatch.setattr(graph_nodes, "run_rigor_node", fake_rigor)
    monkeypatch.setattr(graph_nodes, "run_clarity_node", fake_clarity)
    monkeypatch.setattr(graph_nodes, "run_novelty_node", fake_novelty)
    monkeypatch.setattr(graph_nodes, "run_meta_review_node", fake_meta)

    result = graph.invoke({
        "paper_id": "paper-1",
        "review_mode": "basic_rag",
        "sections": [{"name": "Abstract", "page": 1, "text": "We propose a method."}],
        "pages": [{"page": 1, "text": "We propose a method."}],
    })

    assert result["status"] == "completed"
    assert result["rigor_review"]["issues"][0]["issue"] == "Baseline comparison is now evidenced."


def test_graph_human_dispute_routes_to_reviewer(monkeypatch):
    graph = build_review_graph()

    def fake_rigor(state):
        state["rigor_review"] = {"reviewer": "rigor", "summary": "human dispute addressed", "issues": [{"id": "RIGOR-001", "severity": "High", "issue": "Table 3 contains the baseline comparison."}]}
        return state

    def fake_meta(state):
        if state.get("human_feedback"):
            state["meta_review"] = {"reviewer": "meta", "summary": "resolved after human dispute", "issues": [], "re_review_requests": [], "conflicts": []}
            state["status"] = "completed"
            return state
        state["meta_review"] = {"reviewer": "meta", "summary": "needs human input", "issues": [], "re_review_requests": [{"issue_id": "RIGOR-001", "recommended_reviewer": "rigor"}], "conflicts": []}
        state["needs_human_feedback"] = True
        return state

    monkeypatch.setattr(graph_nodes, "run_rigor_node", fake_rigor)
    monkeypatch.setattr(graph_nodes, "run_clarity_node", lambda state: state)
    monkeypatch.setattr(graph_nodes, "run_novelty_node", lambda state: state)
    monkeypatch.setattr(graph_nodes, "run_meta_review_node", fake_meta)

    result = graph.invoke({
        "paper_id": "paper-2",
        "review_mode": "no_rag",
        "sections": [{"name": "Abstract", "page": 1, "text": "We propose a method."}],
        "pages": [{"page": 1, "text": "We propose a method."}],
        "human_feedback": [{"issue_id": "RIGOR-001", "decision": "disputed", "reason": "The baseline is in Table 3."}],
    })

    assert result["status"] == "completed"


def test_graph_stops_after_two_rereviews(monkeypatch):
    graph = build_review_graph()

    def fake_rigor(state):
        state["rigor_review"] = {"reviewer": "rigor", "summary": "still failing", "issues": [{"id": "RIGOR-001", "severity": "High", "issue": "Persistent issue"}]}
        return state

    def fake_meta(state):
        state["meta_review"] = {"reviewer": "meta", "summary": "repeat", "issues": [], "re_review_requests": [{"issue_id": "RIGOR-001", "recommended_reviewer": "rigor"}], "conflicts": []}
        if state.get("re_review_count", 0) >= 2:
            state["status"] = "completed"
        return state

    monkeypatch.setattr(graph_nodes, "run_rigor_node", fake_rigor)
    monkeypatch.setattr(graph_nodes, "run_clarity_node", lambda state: state)
    monkeypatch.setattr(graph_nodes, "run_novelty_node", lambda state: state)
    monkeypatch.setattr(graph_nodes, "run_meta_review_node", fake_meta)

    result = graph.invoke({
        "paper_id": "paper-3",
        "review_mode": "agentic_rag",
        "sections": [{"name": "Abstract", "page": 1, "text": "We propose a method."}],
        "pages": [{"page": 1, "text": "We propose a method."}],
    })

    assert result["status"] in {"completed", "unresolved_after_re_review"}


def test_page_coverage_registry_and_validation():
    from backend.graph.nodes import prepare_review_context, validate_page_coverage, fill_coverage_gaps

    state = {
        "paper_id": "test_coverage",
        "review_mode": "agentic_rag",
        "pages": [{"page": 1, "text": "Page 1"}, {"page": 2, "text": "Page 2"}, {"page": 3, "text": "Page 3"}],
        "sections": [{"name": "Abstract", "page": 1, "text": "Page 1"}],
    }
    state = prepare_review_context(state)
    registry = state["page_registry"]
    assert len(registry) == 3
    assert registry[1]["rigor"] == "pending"

    # Simulate incomplete coverage
    registry[1]["rigor"] = "reviewed"
    registry[1]["clarity"] = "reviewed"
    state = validate_page_coverage(state)
    assert len(state["coverage_gaps"]) > 0

    # Fill coverage gaps
    state = fill_coverage_gaps(state)
    assert state["coverage_gaps"] == []
    for p in (1, 2, 3):
        for ag in ("rigor", "clarity", "novelty"):
            assert state["page_registry"][p][ag] == "reviewed"
