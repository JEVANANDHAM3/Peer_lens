from backend.agents.meta_agent import MetaReviewerAgent, run_meta_reviewer


def test_meta_agent_merges_duplicate_findings_and_detects_conflict():
    state = {
        "rigor_review": {
            "issues": [
                {
                    "id": "rigor-1",
                    "section": "Experiments",
                    "page": 8,
                    "severity": "High",
                    "type": "experimental_claim",
                    "issue": "The paper lacks statistical significance testing.",
                    "explanation": "The improvement is not validated with significance tests.",
                    "evidence": [{"text": "Accuracy improved by 0.4%."}],
                    "recommendation": "Add a significance test.",
                }
            ]
        },
        "clarity_review": {
            "issues": [
                {
                    "id": "clarity-1",
                    "section": "Experiments",
                    "page": 8,
                    "severity": "Medium",
                    "type": "experimental_claim",
                    "issue": "The paper lacks statistical significance testing.",
                    "explanation": "The narrative needs clearer validation details.",
                    "evidence": [{"text": "The results are reported without intervals."}],
                    "recommendation": "Clarify the statistical validity of the gain.",
                }
            ]
        },
        "novelty_review": {
            "issues": [
                {
                    "id": "novelty-1",
                    "section": "Related Work",
                    "page": 3,
                    "severity": "Low",
                    "type": "novelty_gap",
                    "issue": "The paper does not clearly separate its novelty from prior work.",
                    "explanation": "Prior-art positioning is ambiguous.",
                    "evidence": [{"text": "Related work is only briefly mentioned."}],
                    "recommendation": "Add a sharper novelty comparison.",
                }
            ]
        },
    }

    out = MetaReviewerAgent().review(state)
    assert len(out.issues) >= 2
    assert any(issue.id == "rigor-1" for issue in out.issues)
    assert any(conflict.conflict_detected for conflict in out.conflicts) or any(item["needs_re_review"] for item in out.re_review_requests)


def test_run_meta_reviewer_populates_state_for_graph_router():
    state = {
        "rigor_review": {"issues": []},
        "clarity_review": {"issues": []},
        "novelty_review": {"issues": []},
    }

    updated = run_meta_reviewer(state)
    assert "meta_review" in updated
    assert isinstance(updated["meta_review"], dict)
    assert "conflicts" in updated
    assert "re_review_requests" in updated
