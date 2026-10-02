from __future__ import annotations

from backend.graph.routing import route_after_human_feedback


def test_human_approval_keeps_issue_confirmed():
    state = {
        "human_feedback": [{"issue_id": "RIGOR-1", "decision": "approved", "reason": "Confirmed by reviewer."}],
        "meta_review": {"re_review_requests": [{"issue_id": "RIGOR-1", "recommended_reviewer": "rigor"}]},
    }
    assert route_after_human_feedback(state) == "run_meta_review_node"


def test_human_dispute_routes_back_to_reviewer():
    state = {
        "human_feedback": [{"issue_id": "RIGOR-1", "decision": "disputed", "reason": "Evidence was misunderstood."}],
        "meta_review": {"re_review_requests": [{"issue_id": "RIGOR-1", "recommended_reviewer": "rigor"}]},
        "current_reviewer": "rigor",
    }
    assert route_after_human_feedback(state) == "rerun_rigor"


def test_invalid_human_decision_falls_back_to_finalize():
    state = {"human_feedback": [{"issue_id": "RIGOR-1", "decision": "maybe", "reason": "Unclear."}], "meta_review": {"re_review_requests": []}}
    assert route_after_human_feedback(state) == "finalize_review"
