"""SQLite database persistence layer for PeerLens.

Provides durable storage for manuscripts, reviews, statuses, revision versions,
and arXiv literature cache.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

_DB_ENV_VAR = "PEERLENS_DB_PATH"
_DEFAULT_DB_FILE = Path(__file__).resolve().parent / "peerlens.db"


def get_db_path() -> str:
    """Return the absolute path to the SQLite database file."""
    return os.getenv(_DB_ENV_VAR, str(_DEFAULT_DB_FILE))


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Provide a transactional database connection with row factory enabled."""
    db_path = get_db_path()
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Initialize all SQLite tables and indices required by PeerLens."""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Papers table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS papers (
                paper_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                title TEXT,
                abstract TEXT,
                sections TEXT,
                pages TEXT,
                full_text TEXT,
                authors TEXT,
                file_size TEXT,
                page_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # 2. Reviews table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                paper_id TEXT NOT NULL,
                review_mode TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                final_report TEXT,
                meta_review TEXT,
                rigor_review TEXT,
                clarity_review TEXT,
                novelty_review TEXT,
                retrieval_history TEXT,
                retrieved_documents TEXT,
                issues TEXT,
                conflicts TEXT,
                human_feedback TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (paper_id) REFERENCES papers (paper_id)
            )
            """
        )

        # 3. Review Statuses table (for fast lightweight polling)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS review_statuses (
                review_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                message TEXT,
                paper_id TEXT,
                review_mode TEXT,
                updated_at TEXT NOT NULL
            )
            """
        )

        # 4. arXiv literature cache (to prevent duplicate queries and rate limits)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS arxiv_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                results TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # 5. Paper revision versions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                version_tag TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_size TEXT,
                total_issues INTEGER DEFAULT 0,
                resolved_issues INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )

        # Indices for efficient querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_paper_id ON reviews(paper_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_versions_paper_id ON paper_versions(paper_id)")

        # Migration: ensure revision_comparison column exists in reviews table
        try:
            cursor.execute("ALTER TABLE reviews ADD COLUMN revision_comparison TEXT")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Paper Operations
# ---------------------------------------------------------------------------


def save_paper(paper: Dict[str, Any]) -> Dict[str, Any]:
    """Persist or update a paper in SQLite."""
    paper_id = paper.get("paper_id") or paper.get("id")
    if not paper_id:
        raise ValueError("paper_id is required")

    now = datetime.now(timezone.utc).isoformat()
    sections = paper.get("sections", [])
    pages = paper.get("pages", [])

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO papers (
                paper_id, filename, title, abstract, sections, pages, full_text,
                authors, file_size, page_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(paper_id) DO UPDATE SET
                filename = excluded.filename,
                title = excluded.title,
                abstract = excluded.abstract,
                sections = excluded.sections,
                pages = excluded.pages,
                full_text = excluded.full_text,
                authors = excluded.authors,
                file_size = excluded.file_size,
                page_count = excluded.page_count,
                updated_at = excluded.updated_at
            """,
            (
                paper_id,
                paper.get("filename") or f"{paper_id}.pdf",
                paper.get("title") or "Untitled Paper",
                paper.get("abstract") or "",
                json.dumps(sections) if not isinstance(sections, str) else sections,
                json.dumps(pages) if not isinstance(pages, str) else pages,
                paper.get("full_text") or "",
                paper.get("authors") or "Unknown Authors",
                paper.get("file_size") or "1.0 MB",
                len(pages) if pages else int(paper.get("page_count", 1)),
                paper.get("created_at") or now,
                now,
            ),
        )

    return paper


def get_paper_by_id(paper_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a paper by paper_id from SQLite."""
    if not paper_id:
        return None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers WHERE paper_id = ?", (paper_id,))
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        for json_field in ("sections", "pages"):
            val = data.get(json_field)
            if val and isinstance(val, str):
                try:
                    data[json_field] = json.loads(val)
                except Exception:
                    data[json_field] = []

        data["id"] = data["paper_id"]
        return data


def delete_all_papers() -> None:
    """Clear all stored papers in SQLite."""
    with get_db() as conn:
        conn.cursor().execute("DELETE FROM papers")


def delete_paper(paper_id: str) -> None:
    """Delete a paper and its associated reviews, statuses, and versions."""
    if not paper_id:
        return
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM papers WHERE paper_id = ?", (paper_id,))
        cursor.execute("DELETE FROM reviews WHERE paper_id = ?", (paper_id,))
        cursor.execute("DELETE FROM review_statuses WHERE paper_id = ?", (paper_id,))
        cursor.execute("DELETE FROM paper_versions WHERE paper_id = ?", (paper_id,))


def save_paper_version(
    paper_id: str,
    version: int,
    version_tag: str,
    filename: str,
    file_size: str = "1.0 MB",
    total_issues: int = 0,
    resolved_issues: int = 0,
) -> Dict[str, Any]:
    """Persist or update a revision version record for a paper."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM paper_versions WHERE paper_id = ? AND version = ?",
            (paper_id, version),
        )
        existing = cursor.fetchone()
        if existing:
            cursor.execute(
                """
                UPDATE paper_versions SET
                    version_tag = ?, filename = ?, file_size = ?,
                    total_issues = ?, resolved_issues = ?, created_at = ?
                WHERE id = ?
                """,
                (
                    version_tag,
                    filename,
                    file_size,
                    total_issues,
                    resolved_issues,
                    now,
                    existing["id"],
                ),
            )
        else:
            cursor.execute(
                """
                INSERT INTO paper_versions (
                    paper_id, version, version_tag, filename, file_size,
                    total_issues, resolved_issues, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_id,
                    version,
                    version_tag,
                    filename,
                    file_size,
                    total_issues,
                    resolved_issues,
                    now,
                ),
            )
    return {
        "paper_id": paper_id,
        "version": version,
        "version_tag": version_tag,
        "filename": filename,
        "file_size": file_size,
        "total_issues": total_issues,
        "resolved_issues": resolved_issues,
        "created_at": now,
    }


def get_paper_versions(paper_id: str) -> List[Dict[str, Any]]:
    """Retrieve all saved versions for a paper, ordered by version ASC."""
    if not paper_id:
        return []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM paper_versions WHERE paper_id = ? ORDER BY version ASC",
            (paper_id,),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_reviews_by_paper_id(paper_id: str) -> List[Dict[str, Any]]:
    """Retrieve all reviews associated with a specific paper_id."""
    if not paper_id:
        return []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT review_id, paper_id, review_mode, status, message, created_at, updated_at FROM reviews WHERE paper_id = ? ORDER BY created_at DESC",
            (paper_id,),
        )
        return [dict(r) for r in cursor.fetchall()]


def get_all_papers_summary() -> List[Dict[str, Any]]:
    """Retrieve summary cards of all papers stored in SQLite with their current review statuses."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM papers ORDER BY created_at DESC")
        papers = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM reviews ORDER BY created_at DESC")
        reviews = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT * FROM review_statuses ORDER BY updated_at DESC")
        statuses = [dict(row) for row in cursor.fetchall()]

        cursor.execute("SELECT paper_id, count(*) as vcount FROM paper_versions GROUP BY paper_id")
        version_counts = {row["paper_id"]: row["vcount"] for row in cursor.fetchall()}

        cursor.execute("SELECT * FROM paper_versions ORDER BY version DESC")
        all_versions = [dict(row) for row in cursor.fetchall()]
        latest_version_by_paper = {}
        for ver in all_versions:
            v_pid = ver.get("paper_id")
            if v_pid and v_pid not in latest_version_by_paper:
                latest_version_by_paper[v_pid] = ver

    # Group reviews and statuses by paper_id
    reviews_by_paper: Dict[str, Dict[str, Any]] = {}
    for rev in reviews:
        pid = rev.get("paper_id")
        if pid and pid not in reviews_by_paper:
            reviews_by_paper[pid] = rev

    statuses_by_paper: Dict[str, Dict[str, Any]] = {}
    for st in statuses:
        pid = st.get("paper_id")
        if pid and pid not in statuses_by_paper:
            statuses_by_paper[pid] = st

    results: List[Dict[str, Any]] = []
    seen_pids = set()

    for p in papers:
        pid = p["paper_id"]
        seen_pids.add(pid)
        latest_rev = reviews_by_paper.get(pid)
        latest_status = statuses_by_paper.get(pid)
        latest_ver = latest_version_by_paper.get(pid)

        # Parse issues to calculate active vs resolved counts according to last revision
        issues_raw = latest_rev.get("issues") if latest_rev else None
        issues_list = []
        if issues_raw:
            try:
                issues_list = json.loads(issues_raw) if isinstance(issues_raw, str) else issues_raw
            except Exception:
                issues_list = []

        active_issues = [
            iss for iss in issues_list
            if not iss.get("resolvedInRevision") and iss.get("status") != "accepted"
        ]
        resolved_count = sum(
            1 for iss in issues_list
            if iss.get("resolvedInRevision") or iss.get("status") == "accepted"
        )
        active_count = len(active_issues)
        total_tracked = len(issues_list)

        # If paper_versions has specific revision totals, use them as fallback/corroboration
        if latest_ver:
            ver_total = latest_ver.get("total_issues", total_tracked)
            ver_resolved = latest_ver.get("resolved_issues", resolved_count)
            ver_active = max(0, ver_total - ver_resolved)
            effective_active = active_count if issues_list else ver_active
            effective_resolved = resolved_count if issues_list else ver_resolved
            version_num = max(1, version_counts.get(pid, 1), latest_ver.get("version", 1))
        else:
            effective_active = active_count
            effective_resolved = resolved_count
            version_num = max(1, version_counts.get(pid, 1))

        critical_count = sum(1 for iss in active_issues if str(iss.get("severity", "")).lower() == "critical")
        high_count = sum(1 for iss in active_issues if str(iss.get("severity", "")).lower() == "high")
        medium_count = sum(1 for iss in active_issues if str(iss.get("severity", "")).lower() == "medium")
        low_count = sum(1 for iss in active_issues if str(iss.get("severity", "")).lower() == "low")

        # Determine current review status: if ongoing in review_statuses, it stays ongoing!
        status_val = "uploaded"
        status_msg = "Uploaded and ready for analysis"
        review_mode = "agentic_rag"
        latest_review_id = None

        if latest_status and latest_status.get("status") in ("running", "reviewing", "re_reviewing", "waiting_for_human"):
            status_val = latest_status.get("status")
            status_msg = latest_status.get("message") or "Review in progress..."
            latest_review_id = latest_status.get("review_id")
            review_mode = latest_status.get("review_mode") or review_mode
        elif latest_rev:
            latest_review_id = latest_rev.get("review_id")
            review_mode = latest_rev.get("review_mode") or review_mode
            status_val = latest_rev.get("status") or "completed"
            status_msg = latest_rev.get("message") or "Review completed"
        elif latest_status:
            status_val = latest_status.get("status") or "uploaded"
            status_msg = latest_status.get("message") or "Uploaded and ready for analysis"
            latest_review_id = latest_status.get("review_id")
            review_mode = latest_status.get("review_mode") or review_mode

        results.append({
            "paper_id": pid,
            "filename": p.get("filename", "manuscript.pdf"),
            "title": p.get("title") or p.get("filename") or "Untitled Paper",
            "abstract": p.get("abstract", ""),
            "authors": p.get("authors", "Manuscript Author(s)"),
            "file_size": p.get("file_size", "1.0 MB"),
            "page_count": p.get("page_count", 1),
            "created_at": p.get("created_at", ""),
            "updated_at": p.get("updated_at", ""),
            "latest_review_id": latest_review_id,
            "status": status_val,
            "status_message": status_msg,
            "review_mode": review_mode,
            "total_issues": effective_active,
            "active_issues_count": effective_active,
            "resolved_issues_count": effective_resolved,
            "all_issues_count": total_tracked if issues_list else (latest_ver.get("total_issues", 0) if latest_ver else 0),
            "critical_issues_count": critical_count,
            "high_issues_count": high_count,
            "medium_issues_count": medium_count,
            "low_issues_count": low_count,
            "version_count": version_num,
        })

    # Sort results by created_at DESC
    results.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return results


# ---------------------------------------------------------------------------
# Review Operations
# ---------------------------------------------------------------------------


def save_review(review_data: Dict[str, Any]) -> Dict[str, Any]:
    """Persist or update a review payload in SQLite."""
    review_id = review_data.get("review_id")
    paper_id = review_data.get("paper_id") or ""
    review_mode = review_data.get("review_mode") or "agentic_rag"
    status = review_data.get("status") or "completed"
    message = review_data.get("message") or ""

    if not review_id:
        raise ValueError("review_id is required")

    now = datetime.now(timezone.utc).isoformat()

    def _ser(key: str) -> Optional[str]:
        val = review_data.get(key)
        if val is None:
            return None
        return json.dumps(val) if not isinstance(val, str) else val

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reviews (
                review_id, paper_id, review_mode, status, message,
                final_report, meta_review, rigor_review, clarity_review, novelty_review,
                retrieval_history, retrieved_documents, issues, conflicts, human_feedback,
                revision_comparison, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(review_id) DO UPDATE SET
                paper_id = excluded.paper_id,
                review_mode = excluded.review_mode,
                status = excluded.status,
                message = excluded.message,
                final_report = excluded.final_report,
                meta_review = excluded.meta_review,
                rigor_review = excluded.rigor_review,
                clarity_review = excluded.clarity_review,
                novelty_review = excluded.novelty_review,
                retrieval_history = excluded.retrieval_history,
                retrieved_documents = excluded.retrieved_documents,
                issues = excluded.issues,
                conflicts = excluded.conflicts,
                human_feedback = excluded.human_feedback,
                revision_comparison = excluded.revision_comparison,
                updated_at = excluded.updated_at
            """,
            (
                review_id,
                paper_id,
                review_mode,
                status,
                message,
                _ser("final_report"),
                _ser("meta_review"),
                _ser("rigor_review"),
                _ser("clarity_review"),
                _ser("novelty_review"),
                _ser("retrieval_history"),
                _ser("retrieved_documents"),
                _ser("issues"),
                _ser("conflicts"),
                _ser("human_feedback"),
                _ser("revision_comparison"),
                review_data.get("created_at") or now,
                now,
            ),
        )

    # Also update review_statuses table
    save_status(
        review_id=review_id,
        status=status,
        message=message,
        paper_id=paper_id,
        review_mode=review_mode,
    )

    return review_data


def get_review_by_id(review_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve full review payload by review_id from SQLite."""
    if not review_id:
        return None

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reviews WHERE review_id = ?", (review_id,))
        row = cursor.fetchone()
        if not row:
            return None

        data = dict(row)
        json_fields = (
            "final_report",
            "meta_review",
            "rigor_review",
            "clarity_review",
            "novelty_review",
            "retrieval_history",
            "retrieved_documents",
            "issues",
            "conflicts",
            "human_feedback",
            "revision_comparison",
        )
        for field in json_fields:
            raw = data.get(field)
            if raw and isinstance(raw, str):
                try:
                    data[field] = json.loads(raw)
                except Exception:
                    data[field] = [] if "s" in field or "history" in field else None
            elif raw is None and (field.endswith("s") or "history" in field or "feedback" in field):
                data[field] = []

        return data


def delete_all_reviews() -> None:
    """Clear all stored reviews in SQLite."""
    with get_db() as conn:
        conn.cursor().execute("DELETE FROM reviews")


# ---------------------------------------------------------------------------
# Status Operations
# ---------------------------------------------------------------------------


def save_status(
    review_id: str,
    status: str,
    message: str = "",
    paper_id: Optional[str] = None,
    review_mode: Optional[str] = None,
) -> None:
    """Persist the current review status in SQLite."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.cursor().execute(
            """
            INSERT INTO review_statuses (
                review_id, status, message, paper_id, review_mode, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(review_id) DO UPDATE SET
                status = excluded.status,
                message = excluded.message,
                paper_id = COALESCE(excluded.paper_id, review_statuses.paper_id),
                review_mode = COALESCE(excluded.review_mode, review_statuses.review_mode),
                updated_at = excluded.updated_at
            """,
            (review_id, status, message, paper_id, review_mode, now),
        )


def get_status_by_id(review_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve review status snapshot by review_id from SQLite."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM review_statuses WHERE review_id = ?", (review_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)


def delete_all_statuses() -> None:
    """Clear all stored review statuses in SQLite."""
    with get_db() as conn:
        conn.cursor().execute("DELETE FROM review_statuses")


# ---------------------------------------------------------------------------
# arXiv Cache Operations
# ---------------------------------------------------------------------------


def get_cached_arxiv_results(query_hash: str) -> Optional[List[Dict[str, Any]]]:
    """Retrieve cached arXiv search results if available."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT results FROM arxiv_cache WHERE query_hash = ?", (query_hash,))
        row = cursor.fetchone()
        if row and row["results"]:
            try:
                return json.loads(row["results"])
            except Exception:
                return None
    return None


def set_cached_arxiv_results(query_hash: str, query: str, results: List[Dict[str, Any]]) -> None:
    """Cache arXiv query results in SQLite."""
    now = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        conn.cursor().execute(
            """
            INSERT INTO arxiv_cache (query_hash, query, results, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(query_hash) DO UPDATE SET
                results = excluded.results,
                created_at = excluded.created_at
            """,
            (query_hash, query, json.dumps(results), now),
        )


# Initialize schema on module import
init_db()
