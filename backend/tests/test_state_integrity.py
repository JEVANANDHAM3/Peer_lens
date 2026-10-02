from __future__ import annotations

from backend.graph.nodes import initialize_review, prepare_review_context


def test_initialize_review_sets_expected_state_fields():
    state = {
        "paper_id": "paper-1",
        "review_mode": "agentic_rag",
    }
    result = initialize_review(state)
    assert result["review_id"]
    assert result["paper_id"] == "paper-1"
    assert result["status"] == "running"
    assert result["re_review_count"] == 0
    assert result["retrieval_count"] == 0
    assert result["human_feedback"] == []


def test_prepare_review_context_preserves_paper_sections_and_pages(minimal_valid_paper):
    state = {
        "paper_id": "minimal-valid-paper",
        "pages": [],
        "sections": [],
        "paper_text": "",
    }
    result = prepare_review_context(state)
    assert result["sections"]
    assert result["pages"]
    assert result["paper_text"]
    assert result["status"] == "reviewing"


def test_state_keeps_specialist_outputs_separate():
    state = {
        "rigor_review": {"reviewer": "rigor", "issues": [{"id": "RIGOR-1"}]},
        "clarity_review": {"reviewer": "clarity", "issues": [{"id": "CLARITY-1"}]},
        "novelty_review": {"reviewer": "novelty", "issues": [{"id": "NOVELTY-1"}]},
        "human_feedback": [{"issue_id": "RIGOR-1", "decision": "disputed", "reason": "Needed clarifying."}],
    }
    assert state["rigor_review"]["issues"][0]["id"] == "RIGOR-1"
    assert state["clarity_review"]["issues"][0]["id"] == "CLARITY-1"
    assert state["novelty_review"]["issues"][0]["id"] == "NOVELTY-1"
    assert state["human_feedback"][0]["decision"] == "disputed"
