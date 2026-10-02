from __future__ import annotations

import os
from pathlib import Path
from backend.database import (
    get_db,
    init_db,
    save_paper,
    get_paper_by_id,
    save_review,
    get_review_by_id,
    save_status,
    get_status_by_id,
    set_cached_arxiv_results,
    get_cached_arxiv_results,
    delete_all_papers,
    delete_all_reviews,
    delete_all_statuses,
)
from backend.rag.retriever import LiteratureRetriever, _clean_arxiv_query, _calculate_similarity


def test_sqlite_db_init_and_crud(tmp_path):
    test_db = str(tmp_path / "test_peerlens.db")
    os.environ["PEERLENS_DB_PATH"] = test_db
    init_db()

    # 1. Test paper persistence
    paper = {
        "paper_id": "paper_sqlite_1",
        "title": "Quantum Neural Algorithms",
        "filename": "quantum.pdf",
        "abstract": "We explore quantum neural networks.",
        "sections": [{"name": "Introduction", "page": 1, "text": "Intro text"}],
        "pages": [{"page": 1, "text": "Intro text"}],
        "full_text": "Intro text",
        "authors": "Dr. Alice & Dr. Bob",
        "file_size": "2.5 MB",
        "page_count": 1,
    }
    saved_paper = save_paper(paper)
    assert saved_paper["paper_id"] == "paper_sqlite_1"

    loaded_paper = get_paper_by_id("paper_sqlite_1")
    assert loaded_paper is not None
    assert loaded_paper["title"] == "Quantum Neural Algorithms"
    assert loaded_paper["authors"] == "Dr. Alice & Dr. Bob"
    assert len(loaded_paper["sections"]) == 1

    # 2. Test review persistence
    review = {
        "review_id": "review_sqlite_1",
        "paper_id": "paper_sqlite_1",
        "review_mode": "agentic_rag",
        "status": "completed",
        "message": "Review completed successfully.",
        "issues": [
            {
                "id": "RIGOR-001",
                "issue": "Missing baseline comparison",
                "severity": "High",
                "section": "Experiments",
                "page": 1,
            }
        ],
        "final_report": {"overall_assessment": "Needs Revision"},
    }
    saved_review = save_review(review)
    assert saved_review["review_id"] == "review_sqlite_1"

    loaded_review = get_review_by_id("review_sqlite_1")
    assert loaded_review is not None
    assert loaded_review["status"] == "completed"
    assert len(loaded_review["issues"]) == 1
    assert loaded_review["issues"][0]["id"] == "RIGOR-001"

    # 3. Test status persistence
    save_status("review_sqlite_1", "completed", "Done reviewing", paper_id="paper_sqlite_1")
    loaded_status = get_status_by_id("review_sqlite_1")
    assert loaded_status is not None
    assert loaded_status["status"] == "completed"

    # 4. Test arXiv cache persistence
    cached_items = [{"title": "Real arXiv Paper", "entry_id": "arxiv://1234.5678"}]
    set_cached_arxiv_results("test_hash", "quantum neural networks", cached_items)
    retrieved_cache = get_cached_arxiv_results("test_hash")
    assert retrieved_cache is not None
    assert retrieved_cache[0]["title"] == "Real arXiv Paper"

    # 5. Clean up
    delete_all_papers()
    delete_all_reviews()
    delete_all_statuses()
    assert get_paper_by_id("paper_sqlite_1") is None
    assert get_review_by_id("review_sqlite_1") is None


def test_arxiv_query_sanitization():
    raw = "The authors propose an adaptive transformer routing method for attention!"
    cleaned = _clean_arxiv_query(raw)
    assert "adaptive" in cleaned
    assert "transformer" in cleaned
    assert "routing" in cleaned
    assert "!" not in cleaned


def test_literature_retriever_arxiv_integration():
    retriever = LiteratureRetriever()
    # Query arXiv for a known well-established topic
    results = retriever.search("deep reinforcement learning policy gradient", max_results=2)
    assert isinstance(results, list)
    # Even if offline/rate-limited, it returns a list without raising unhandled exceptions
    if results:
        assert "title" in results[0]
        assert "similarity_score" in results[0]
        evidence = retriever.retrieve_evidence("deep reinforcement learning", top_k=2, documents=results)
        assert len(evidence) == len(results)
        assert "similarity_score" in evidence[0]
