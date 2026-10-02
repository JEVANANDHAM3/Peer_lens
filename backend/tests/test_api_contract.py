from __future__ import annotations

import time

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_review_upload_and_status_flow(monkeypatch):
    def fake_run_review_graph_sync(review_id: str, paper_id: str, review_mode: str = "agentic_rag", use_checkpointing: bool = False):
        return {
            "review_id": review_id,
            "paper_id": paper_id,
            "review_mode": review_mode,
            "status": "completed",
            "final_report": {"summary": "Completed review", "recommended_actions": ["Clarify methods"]},
            "meta_review": {"summary": "Good overall assessment", "issues": []},
            "rigor_review": {"reviewer": "rigor", "summary": "Methodological details are adequate.", "issues": []},
            "clarity_review": {"reviewer": "clarity", "summary": "Clear writing.", "issues": []},
            "novelty_review": {"reviewer": "novelty", "summary": "Novelty is acceptable.", "issues": []},
            "retrieval_history": [{"query": "novelty", "status": "ok"}],
            "retrieved_documents": [{"title": "Related work", "source": "local"}],
            "issues": [{"id": "issue-1", "issue": "Minor clarity issue", "severity": "Low", "reviewer": "clarity"}],
            "conflicts": [],
            "human_feedback": [],
        }

    monkeypatch.setattr("backend.main.run_review_graph_sync", fake_run_review_graph_sync)

    upload_response = client.post(
        "/api/review/upload",
        files={"file": ("sample.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", "application/pdf")},
    )
    assert upload_response.status_code == 200
    uploaded = upload_response.json()
    assert uploaded["status"] == "uploaded"
    assert uploaded["paper_id"]

    review_response = client.post(
        "/api/review",
        json={"paper_id": uploaded["paper_id"], "review_mode": "agentic_rag"},
    )
    assert review_response.status_code == 200
    review = review_response.json()
    assert review["review_id"]
    assert review["paper_id"] == uploaded["paper_id"]
    assert review["status"] == "running"

    status_response = client.get(f"/api/review/{review['review_id']}/status")
    assert status_response.status_code == 200
    assert status_response.json()["status"] in {"running", "completed"}

    for _ in range(50):
        status_response = client.get(f"/api/review/{review['review_id']}/status")
        if status_response.json()["status"] == "completed":
            break
        time.sleep(0.05)

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"

    result_response = client.get(f"/api/review/{review['review_id']}")
    assert result_response.status_code == 200
    assert result_response.json()["paper_id"] == uploaded["paper_id"]

    feedback_response = client.post(
        f"/api/review/{review['review_id']}/feedback",
        json={"issue_id": "issue-1", "decision": "approve", "reason": "Looks sound."},
    )
    assert feedback_response.status_code == 200
    assert feedback_response.json()["message"] == "Feedback recorded."


def test_review_starts_as_running_and_completes_in_background(monkeypatch):
    def fake_run_review_graph_sync(review_id: str, paper_id: str, review_mode: str = "agentic_rag", use_checkpointing: bool = False):
        time.sleep(0.1)
        return {
            "review_id": review_id,
            "paper_id": paper_id,
            "review_mode": review_mode,
            "status": "completed",
            "final_report": {"summary": "Completed review", "recommended_actions": ["Clarify methods"]},
            "meta_review": {"summary": "Good overall assessment", "issues": []},
            "rigor_review": {"reviewer": "rigor", "summary": "Methodological details are adequate.", "issues": []},
            "clarity_review": {"reviewer": "clarity", "summary": "Clear writing.", "issues": []},
            "novelty_review": {"reviewer": "novelty", "summary": "Novelty is acceptable.", "issues": []},
            "retrieval_history": [{"query": "novelty", "status": "ok"}],
            "retrieved_documents": [{"title": "Related work", "source": "local"}],
            "issues": [{"id": "issue-1", "issue": "Minor clarity issue", "severity": "Low", "reviewer": "clarity"}],
            "conflicts": [],
            "human_feedback": [],
        }

    monkeypatch.setattr("backend.main.run_review_graph_sync", fake_run_review_graph_sync)

    upload_response = client.post(
        "/api/review/upload",
        files={"file": ("sample.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", "application/pdf")},
    )
    uploaded = upload_response.json()

    review_response = client.post(
        "/api/review",
        json={"paper_id": uploaded["paper_id"], "review_mode": "agentic_rag"},
    )
    review_data = review_response.json()
    assert review_data["status"] == "running"

    for _ in range(50):
        status_response = client.get(f"/api/review/{review_data['review_id']}/status")
        if status_response.json()["status"] == "completed":
            break
        time.sleep(0.05)

    assert client.get(f"/api/review/{review_data['review_id']}/status").json()["status"] == "completed"


def test_upload_and_review_all_in_one(monkeypatch):
    def fake_run_review_graph_sync(review_id: str, paper_id: str, review_mode: str = "agentic_rag", use_checkpointing: bool = False):
        return {
            "review_id": review_id,
            "paper_id": paper_id,
            "review_mode": review_mode,
            "status": "completed",
            "final_report": {
                "summary": "Completed review",
                "critical_issues": [{"id": "crit-1", "issue": "Missing baseline comparison", "severity": "Critical"}],
                "high_issues": [],
                "medium_issues": [],
                "low_issues": [{"id": "low-1", "issue": "Minor clarity issue", "severity": "Low"}],
                "recommended_actions": ["Add baseline model comparison."],
            },
            "meta_review": {
                "summary": "Solid paper with few gaps",
                "issues": [
                    {"id": "crit-1", "issue": "Missing baseline comparison", "severity": "Critical", "reviewer": "rigor"},
                    {"id": "low-1", "issue": "Minor clarity issue", "severity": "Low", "reviewer": "clarity"},
                ],
            },
            "rigor_review": {"reviewer": "rigor", "summary": "Methodological details need baseline.", "issues": [{"id": "crit-1", "issue": "Missing baseline comparison", "severity": "Critical"}]},
            "clarity_review": {"reviewer": "clarity", "summary": "Clear writing.", "issues": [{"id": "low-1", "issue": "Minor clarity issue", "severity": "Low"}]},
            "novelty_review": {"reviewer": "novelty", "summary": "Novelty is acceptable.", "issues": []},
            "retrieval_history": [{"query": "novelty", "status": "ok"}],
            "retrieved_documents": [{"title": "Related work", "source": "local"}],
            "issues": [
                {"id": "crit-1", "issue": "Missing baseline comparison", "severity": "Critical", "reviewer": "rigor"},
                {"id": "low-1", "issue": "Minor clarity issue", "severity": "Low", "reviewer": "clarity"},
            ],
            "conflicts": [],
            "human_feedback": [],
        }

    monkeypatch.setattr("backend.main.run_review_graph_sync", fake_run_review_graph_sync)

    response = client.post(
        "/api/review/upload-and-review",
        files={"file": ("paper.pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF", "application/pdf")},
        data={"review_mode": "agentic_rag"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["review_id"].startswith("review_")
    assert data["mistakes_summary"]["total_mistakes"] == 2
    assert data["mistakes_summary"]["critical_count"] == 1
    assert data["mistakes_summary"]["low_count"] == 1
    assert len(data["all_mistakes"]) == 2
    assert data["all_mistakes"][0]["issue"] == "Missing baseline comparison"
    assert "final_report" in data
    assert "rigor_review" in data
    assert "clarity_review" in data
    assert "novelty_review" in data

