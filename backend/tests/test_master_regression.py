from __future__ import annotations

from backend.graph.routing import route_after_meta


def test_regression_no_retrieval_in_no_rag_mode_is_preserved():
    state = {
        "review_mode": "no_rag",
        "meta_review": {"re_review_requests": [], "conflicts": []},
    }
    assert route_after_meta(state) == "finalize_review"


def test_regression_duplicate_issues_are_not_readded_unbounded():
    state = {
        "meta_review": {"re_review_requests": [{"issue_id": "DUP-1", "recommended_reviewer": "rigor"}], "conflicts": []},
        "re_review_count": 0,
    }
    assert route_after_meta(state) == "rerun_rigor"


def test_regression_human_feedback_not_lost_after_re_review():
    state = {
        "needs_human_feedback": True,
        "human_feedback": [{"issue_id": "CLARITY-1", "decision": "disputed", "reason": "Need second pass."}],
        "meta_review": {"re_review_requests": [{"issue_id": "CLARITY-1", "recommended_reviewer": "clarity"}]},
        "current_reviewer": "clarity",
    }
    assert route_after_meta(state) == "human_feedback"
