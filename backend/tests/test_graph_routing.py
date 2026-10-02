from __future__ import annotations

from backend.graph.routing import route_after_human_feedback, route_after_meta


def test_route_after_meta_returns_rerun_for_rigor_request():
    state = {
        "re_review_count": 0,
        "meta_review": {
            "re_review_requests": [{"issue_id": "RIGOR-1", "recommended_reviewer": "rigor"}],
            "conflicts": [],
        },
    }
    assert route_after_meta(state) == "rerun_rigor"


def test_route_after_meta_returns_human_feedback_when_required():
    state = {"needs_human_feedback": True, "meta_review": {"re_review_requests": []}}
    assert route_after_meta(state) == "human_feedback"


def test_route_after_meta_finalizes_when_no_request_exists():
    state = {"meta_review": {"re_review_requests": [], "conflicts": []}, "re_review_count": 0}
    assert route_after_meta(state) == "finalize_review"


def test_route_after_human_feedback_approves_then_meta_recheck():
    state = {
        "human_feedback": [{"issue_id": "RIGOR-1", "decision": "approved", "reason": "Looks correct."}],
        "meta_review": {"re_review_requests": [{"issue_id": "RIGOR-1", "recommended_reviewer": "rigor"}]},
    }
    assert route_after_human_feedback(state) == "run_meta_review_node"


def test_route_after_human_feedback_dispute_uses_reviewer_route():
    state = {
        "human_feedback": [{"issue_id": "RIGOR-1", "decision": "disputed", "reason": "Claim is actually supported."}],
        "meta_review": {"re_review_requests": [{"issue_id": "RIGOR-1", "recommended_reviewer": "rigor"}]},
        "current_reviewer": "rigor",
    }
    assert route_after_human_feedback(state) == "rerun_rigor"
