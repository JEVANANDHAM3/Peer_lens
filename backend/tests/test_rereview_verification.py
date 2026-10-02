import io
import pytest
from starlette.testclient import TestClient

from backend.main import app
from backend.tools.paper_tools import clear_papers, register_paper
from backend.database import save_paper, get_paper_versions, get_reviews_by_paper_id


@pytest.fixture
def client():
    return TestClient(app)


def test_rereview_detects_error_changes(client):
    """Test that the re-review pipeline correctly verifies whether errors were changed."""
    paper_id = "paper_rereview_test_01"
    original_text = (
        "# Abstract\n\nWe present a new algorithm.\n\n"
        "# Methodology\n\nOur model assumes linear convergence with zero variance without theoretical justification.\n\n"
        "# Results\n\nWe achieve 99% accuracy on standard benchmarks."
    )

    paper_record = {
        "paper_id": paper_id,
        "filename": "draft_v1.md",
        "title": "A Novel Convergence Proof",
        "abstract": "We present a new algorithm.",
        "sections": [
            {"name": "Abstract", "page": 1, "text": "We present a new algorithm."},
            {
                "name": "Methodology",
                "page": 1,
                "text": "Our model assumes linear convergence with zero variance without theoretical justification.",
            },
            {"name": "Results", "page": 1, "text": "We achieve 99% accuracy on standard benchmarks."},
        ],
        "pages": [{"page": 1, "text": original_text}],
        "full_text": original_text,
        "authors": "Alice Researcher",
        "file_size": "0.1 MB",
        "page_count": 1,
    }
    register_paper(paper_id, paper_record)
    save_paper(paper_record)

    # Initial review run for the paper
    initial_res = client.post(
        "/api/review",
        json={"paper_id": paper_id, "review_mode": "no_rag"},
    )
    assert initial_res.status_code == 200
    rev_id = initial_res.json()["review_id"]

    # Now author submits a revised manuscript draft where the flawed claim in Methodology was changed
    revised_text = (
        "# Abstract\n\nWe present a new algorithm.\n\n"
        "# Methodology\n\nWe establish bounded empirical variance under stochastic perturbation, providing a complete convergence theorem in Appendix A.\n\n"
        "# Results\n\nWe achieve 99% accuracy on standard benchmarks."
    )

    revised_file = io.BytesIO(revised_text.encode("utf-8"))

    # Send re-review request
    rereview_res = client.post(
        f"/api/review/{paper_id}/re-review",
        files={"file": ("draft_v2.md", revised_file, "text/markdown")},
        data={"review_mode": "no_rag"},
    )

    assert rereview_res.status_code == 200
    data = rereview_res.json()

    assert data["status"] == "completed"
    assert data["version"] >= 1
    assert "revision_comparison" in data

    comp = data["revision_comparison"]
    assert "errors_resolved" in comp
    assert "verdict" in comp

    # Verify versions are persisted in SQLite
    versions = get_paper_versions(paper_id)
    assert len(versions) >= 1

    # Verify reviews associated with this paper
    reviews = get_reviews_by_paper_id(paper_id)
    assert len(reviews) >= 2  # initial + re-review
