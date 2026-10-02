"""Tests for issue reconsideration agent and endpoint."""

import pytest
from starlette.testclient import TestClient

from backend.main import app, _put_review, _empty_review_record
from backend.agents.reconsideration_agent import evaluate_author_argument


def test_reconsider_heuristic_remove():
    """Verify that an author providing factual/math proof removes the issue."""
    issue = {
        "id": "iss-1",
        "title": "Equation 4 Lipschitz continuity condition missing",
        "explanation": "The proof does not show Lipschitz continuity holds on Page 3.",
        "evidence": "||f(x) - f(y)|| <= L ||x - y|| is not stated.",
        "severity": "High",
        "reviewer": "Rigor Reviewer",
        "section": "Methodology",
        "page": 3,
        "suggestedAction": "Add proof of Lipschitz continuity.",
    }
    arg = "The Lipschitz continuity condition is already proven in Section 3, Theorem 2 on page 4."
    res = evaluate_author_argument(issue, arg)
    assert res["outcome"] == "remove"
    assert "retracted" in res["verdict_reason"].lower() or "removed" in res["verdict_reason"].lower()


def test_reconsider_heuristic_reframe():
    """Verify that an author explaining a trade-off/perspective reframes the issue and provides updated solutions."""
    issue = {
        "id": "iss-2",
        "title": "Latency higher than baseline Model X",
        "explanation": "The model has 12ms latency which is 2ms higher than baseline.",
        "evidence": "Table 1 shows 12ms vs 10ms.",
        "severity": "Medium",
        "reviewer": "Clarity Reviewer",
        "section": "Evaluation",
        "page": 5,
        "suggestedAction": "Optimize model pruning.",
    }
    arg = "Our perspective and focus is on edge device efficiency under battery constraints rather than raw peak speed, as this deliberate trade-off saves 40% memory."
    res = evaluate_author_argument(issue, arg)
    assert res["outcome"] == "reframe"
    assert res["updated_title"] is not None
    assert "Reframed" in res["updated_title"]
    assert res["updated_explanation"] is not None
    assert res["updated_solution"] is not None
    assert len(res["updated_action_plan"]) == 3


def test_reconsider_endpoint():
    """Test the full HTTP endpoint for reconsidering an issue."""
    client = TestClient(app)

    review_id = "test_rev_reconsider"
    record = _empty_review_record(review_id, "paper_mock", "agentic_rag")
    record["status"] = "completed"
    record["issues"] = [
        {
            "id": "iss-reconsider-1",
            "title": "Sample size is small",
            "explanation": "Only tested on 10 subjects.",
            "evidence": "n=10",
            "severity": "High",
            "reviewer": "Rigor Reviewer",
            "status": "open",
        }
    ]
    _put_review(review_id, record)

    # 1. Reframe test
    resp = client.post(
        f"/api/review/{review_id}/issue/iss-reconsider-1/reconsider",
        json={"author_argument": "From our perspective this is deliberate as a pilot exploratory feasibility study with n=10 in our setting."}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["outcome"] == "reframe"
    assert data["updated_issue"]["reconsidered"] is True
    assert "Reframed" in data["updated_issue"]["title"]
    assert len(data["updated_issue"]["actionPlan"]) == 3

    # 2. Remove test
    resp_remove = client.post(
        f"/api/review/{review_id}/issue/iss-reconsider-1/reconsider",
        json={"author_argument": "This is already addressed in section 4 where the full clinical cohort of n=500 is evaluated as shown in section 4."}
    )
    assert resp_remove.status_code == 200
    data_remove = resp_remove.json()
    assert data_remove["outcome"] == "remove"
    assert data_remove["updated_issue"]["status"] == "dismissed"


def test_reconsider_human_feedback_phrasing():
    """Verify author phrases like 'remove issue' or 'no problem' and 'change solution'."""
    issue = {
        "id": "iss-3",
        "title": "Minor typo in algorithm line 4",
        "explanation": "Variable x is used instead of y.",
        "evidence": "line 4: x = 1",
        "severity": "Low",
        "reviewer": "Clarity Reviewer",
        "suggestedAction": "Rename x to y.",
    }

    # Removal phrasing
    res_remove = evaluate_author_argument(issue, "remove issuse or no problem wiht the issuse")
    assert res_remove["outcome"] == "remove"

    # Change solution phrasing
    res_change = evaluate_author_argument(
        issue,
        "Change the solution to keep x and document it as a global scalar in Section 2."
    )
    assert res_change["outcome"] == "reframe"
    assert res_change["updated_solution"] is not None
    assert "Revised Solution" in res_change["updated_solution"] or "global scalar" in res_change["updated_solution"].lower()

