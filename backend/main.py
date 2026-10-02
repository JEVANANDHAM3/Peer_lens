"""FastAPI backend for the PeerLens AI-powered peer-review system.

Exposes endpoints consumed by the React frontend and direct API clients:

  1. GET  /api/health                     – Liveness probe
  2. POST /api/review/upload              – Upload a manuscript (PDF, TXT, MD)
  3. POST /api/review/start               – Kick off the LangGraph review pipeline (async)
  4. GET  /api/review/{id}/status         – Poll lightweight review progress
  5. GET  /api/review/{id}/result         – Fetch the full review payload
  6. POST /api/review/{id}/feedback       – Submit author accept / dispute on an issue
  7. POST /api/review/upload-and-review   – All-in-one: upload file, run workflow, return full result
"""

from __future__ import annotations
import asyncio
import os
import uuid
from typing import Any, Dict, Iterable, List, Optional

from dotenv import load_dotenv

# Automatically load environment variables from backend/.env or root
_backend_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_backend_dir, ".env"))
load_dotenv(os.path.join(os.path.dirname(_backend_dir), ".env"))
load_dotenv()

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.database import (
    delete_all_papers,
    delete_all_reviews,
    delete_all_statuses,
    delete_paper,
    get_all_papers_summary,
    get_paper_by_id,
    get_paper_versions,
    get_review_by_id,
    get_reviews_by_paper_id,
    init_db,
    save_paper,
    save_paper_version,
    save_review,
)
from backend.graph.workflow import run_review_graph, run_review_graph_sync

_ORIGINAL_RUN_REVIEW_GRAPH_SYNC = run_review_graph_sync
from backend.review_status import clear_statuses, get_status_snapshot, record_status
from backend.tools.paper_tools import clear_papers, get_paper, register_paper
from backend.agents.revision_verifier import verify_revision_errors
from backend.agents.reconsideration_agent import evaluate_author_argument
from backend.agents.solution_generator import generate_solutions

# Ensure SQLite schema is prepared
init_db()

# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="PeerLens Review Service",
    description=(
        "Backend API powering the PeerLens AI peer-review system. "
        "Orchestrates Rigor, Clarity, and Novelty specialist reviewers "
        "through a LangGraph workflow, and exposes endpoints for paper "
        "upload, review lifecycle management, and author feedback."
    ),
    version="2.0.0",
)

# ---------------------------------------------------------------------------
# CORS – allow the Vite dev server and common local origins
# ---------------------------------------------------------------------------

_allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|\d+\.\d+\.\d+\.\d+)(:\d+)?$",
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ReviewStartRequest(BaseModel):
    """Body sent by the frontend to start a new review."""

    paper_id: str = Field(
        ..., description="ID returned by the /api/review/upload endpoint."
    )
    review_mode: str = Field(
        default="agentic_rag",
        description="One of 'no_rag', 'basic_rag', or 'agentic_rag'.",
    )


class FeedbackRequest(BaseModel):
    """Body sent by the frontend when the author accepts or disputes an issue."""

    issue_id: str = Field(..., description="ID of the issue being responded to.")
    decision: str = Field(
        ...,
        description="Author's decision: 'approve' or 'dispute'.",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Free-text justification (required for disputes).",
    )


class ReconsiderIssueRequest(BaseModel):
    """Body sent by the frontend to reconsider a flagged issue based on author argument."""

    author_argument: str = Field(..., description="Author's counter-argument, perspective, or clarification")


class PaperVersionRequest(BaseModel):
    """Body sent to record a new manuscript revision version."""

    version: int = Field(..., description="Version number, e.g. 2")
    version_tag: str = Field(..., description="Version tag, e.g. 'v2.0'")
    filename: str = Field(..., description="Filename of revision")
    file_size: str = Field(default="1.0 MB", description="File size string")
    total_issues: int = Field(default=0, description="Total issues tracked")
    resolved_issues: int = Field(default=0, description="Resolved issues count")


# ---------------------------------------------------------------------------
# In-memory review store (keyed by review_id)
# ---------------------------------------------------------------------------

_REVIEW_STORE: Dict[str, Dict[str, Any]] = {}


def _put_review(review_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    """Store review in memory cache and persist to SQLite database."""
    _REVIEW_STORE[review_id] = record
    try:
        save_review(record)
        if record.get("status") == "completed" and record.get("paper_id"):
            pid = record["paper_id"]
            all_issues = list(record.get("issues") or [])
            if not all_issues:
                for rev_key in ("rigor_review", "clarity_review", "novelty_review"):
                    rev = record.get(rev_key) or {}
                    for it in rev.get("issues", []) or []:
                        all_issues.append(it)
            v_list = get_paper_versions(pid)
            if not v_list:
                paper_obj = get_paper_by_id(pid) or {}
                save_paper_version(
                    paper_id=pid,
                    version=1,
                    version_tag="v1.0",
                    filename=paper_obj.get("filename", "manuscript.pdf"),
                    file_size=paper_obj.get("file_size", "1.0 MB"),
                    total_issues=len(all_issues),
                    resolved_issues=0,
                )
            elif len(v_list) == 1 and (v_list[0].get("total_issues", 0) == 0):
                v1 = v_list[0]
                save_paper_version(
                    paper_id=pid,
                    version=1,
                    version_tag=v1.get("version_tag", "v1.0"),
                    filename=v1.get("filename", "manuscript.pdf"),
                    file_size=v1.get("file_size", "1.0 MB"),
                    total_issues=len(all_issues),
                    resolved_issues=0,
                )
    except Exception:
        pass
    return record


def _get_review(review_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve review from memory cache or load from SQLite database."""
    if not review_id:
        return None
    if review_id in _REVIEW_STORE:
        return _REVIEW_STORE[review_id]
    try:
        db_review = get_review_by_id(review_id)
        if db_review:
            _REVIEW_STORE[review_id] = db_review
            return db_review
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _new_review_id() -> str:
    """Generate a short, human-friendly review identifier."""
    return f"review_{uuid.uuid4().hex[:8]}"


def _empty_review_record(
    review_id: str, paper_id: str, review_mode: str
) -> Dict[str, Any]:
    """Return a blank review record with every field initialised."""
    return {
        "review_id": review_id,
        "paper_id": paper_id,
        "review_mode": review_mode,
        "status": "running",
        "message": "Review started.",
        "final_report": None,
        "meta_review": None,
        "rigor_review": None,
        "clarity_review": None,
        "novelty_review": None,
        "retrieval_history": [],
        "retrieved_documents": [],
        "issues": [],
        "conflicts": [],
        "human_feedback": [],
        "needs_human_feedback": False,
    }


def _coerce_result(
    raw: Dict[str, Any], review_id: str, paper_id: str, review_mode: str
) -> Dict[str, Any]:
    """Normalise the raw LangGraph output into the canonical review shape."""
    payload = dict(raw or {})
    payload.setdefault("review_id", review_id)
    payload.setdefault("paper_id", paper_id)
    payload.setdefault("review_mode", review_mode)
    payload.setdefault("status", "completed")
    for list_key in (
        "issues",
        "conflicts",
        "retrieval_history",
        "retrieved_documents",
        "human_feedback",
    ):
        payload.setdefault(list_key, payload.get(list_key) or [])
    for nullable_key in (
        "final_report",
        "meta_review",
        "rigor_review",
        "clarity_review",
        "novelty_review",
        "page_registry",
    ):
        payload.setdefault(nullable_key, payload.get(nullable_key))
    if not payload["issues"]:
        seen_ids = set()
        aggregated_issues = []
        for rev_key in ("rigor_review", "clarity_review", "novelty_review"):
            rev = payload.get(rev_key)
            if isinstance(rev, dict):
                for issue in rev.get("issues", []) or []:
                    iid = issue.get("id") or issue.get("issue")
                    if iid and iid not in seen_ids:
                        seen_ids.add(iid)
                        aggregated_issues.append(issue)
        payload["issues"] = aggregated_issues
    payload.setdefault("needs_human_feedback", False)
    return payload


def _paper_text_from_sections(sections: Iterable[Dict[str, Any]]) -> str:
    """Concatenate section text into a single document string."""
    fragments: List[str] = []
    for section in sections:
        if isinstance(section, dict):
            text = section.get("text")
            if text:
                fragments.append(str(text))
    return "\n\n".join(fragments)


def extract_document_structure(
    filename: str, content: bytes
) -> tuple[str, list[Dict[str, Any]], list[Dict[str, Any]], str]:
    """Extract real abstract, sections, pages, and full text from PDF, TXT, or MD."""
    pages: List[Dict[str, Any]] = []
    sections: List[Dict[str, Any]] = []
    filename_lower = filename.lower()

    if filename_lower.endswith(".pdf"):
        try:
            import io
            import pypdf

            reader = pypdf.PdfReader(io.BytesIO(content))
            for idx, page in enumerate(reader.pages):
                txt = (page.extract_text() or "").strip()
                pages.append({"page": idx + 1, "text": txt or f"[Page {idx + 1}: Formatted visual/tabular content]"})
        except Exception as exc:
            print(f"[PDF Extraction Error]: {exc}")

        if not pages:
            fallback_text = "Uploaded PDF for review."
            pages = [{"page": 1, "text": fallback_text}]
            sections = [{"name": "Abstract", "page": 1, "text": fallback_text}]
            return "Uploaded PDF for review.", sections, pages, fallback_text

        full_text = "\n\n".join(p["text"] for p in pages)
        import re

        section_headers = [
            "abstract", "introduction", "related work", "background",
            "methodology", "method", "proposed method", "model architecture",
            "system design", "experimental setup", "experiments", "evaluation",
            "results", "discussion", "limitations", "conclusion", "references",
        ]

        current_section_name = "Abstract"
        current_page = pages[0]["page"]
        current_lines: List[str] = []

        for p in pages:
            lines = p["text"].split("\n")
            for line in lines:
                clean_line = line.strip()
                lower_line = clean_line.lower()
                is_header = False
                matched_header = None
                for header in section_headers:
                    pattern = rf"^(?:\d+[\.\s]+)?{header}(?:\s*[:\-\.]|\s*$)"
                    if re.match(pattern, lower_line):
                        is_header = True
                        matched_header = clean_line
                        break

                if is_header and current_lines:
                    sections.append(
                        {
                            "name": current_section_name,
                            "page": current_page,
                            "page_end": p["page"],
                            "text": "\n".join(current_lines).strip(),
                        }
                    )
                    current_section_name = matched_header
                    current_page = p["page"]
                    current_lines = []
                else:
                    current_lines.append(line)

        if current_lines:
            sections.append(
                {
                    "name": current_section_name,
                    "page": current_page,
                    "page_end": pages[-1]["page"] if pages else current_page,
                    "text": "\n".join(current_lines).strip(),
                }
            )

        if not sections:
            sections = [
                {"name": f"Page {p['page']}", "page": p["page"], "page_end": p["page"], "text": p["text"]}
                for p in pages
            ]

        abstract = ""
        for sec in sections:
            if "abstract" in sec["name"].lower():
                abstract = sec["text"][:1500]
                break
        if not abstract:
            abstract = full_text[:600]

        return abstract, sections, pages, full_text
    else:
        text = content.decode("utf-8", errors="replace").strip()
        lines = text.split("\n")
        current_section = "Introduction"
        current_lines = []

        for line in lines:
            if line.strip().startswith(("# ", "## ", "### ")):
                if current_lines:
                    sections.append(
                        {
                            "name": current_section,
                            "page": 1,
                            "text": "\n".join(current_lines).strip(),
                        }
                    )
                    current_lines = []
                current_section = line.strip().lstrip("#").strip()
            else:
                current_lines.append(line)

        if current_lines:
            sections.append(
                {
                    "name": current_section,
                    "page": 1,
                    "text": "\n".join(current_lines).strip(),
                }
            )

        if not sections:
            sections = [{"name": "Body", "page": 1, "text": text}]
        pages = [{"page": 1, "text": text}]
        abstract = text[:500]
        return abstract, sections, pages, text


# ---------------------------------------------------------------------------
# Background task: run the LangGraph review pipeline asynchronously
# ---------------------------------------------------------------------------


async def _run_review_pipeline(
    review_id: str, paper_id: str, review_mode: str
) -> None:
    """Execute the full multi-agent review in the background.

    Updates ``_REVIEW_STORE`` and the global status tracker as the
    pipeline progresses so the frontend can poll ``/status``.
    """
    record_status(
        review_id,
        "reviewing",
        "Running the review pipeline across the specialist agents.",
        paper_id=paper_id,
        review_mode=review_mode,
    )

    try:
        runner_sync = globals().get("run_review_graph_sync")
        if callable(runner_sync) and runner_sync is not _ORIGINAL_RUN_REVIEW_GRAPH_SYNC:
            res = runner_sync(review_id, paper_id, review_mode=review_mode)
            result = await res if asyncio.iscoroutine(res) else res
        else:
            result = await run_review_graph(review_id, paper_id, review_mode=review_mode)
        stored = _coerce_result(result, review_id, paper_id, review_mode)

        if stored.get("status") in {"waiting_for_human", "re_reviewing"}:
            stored.setdefault(
                "message", "The review requires author follow-up."
            )
        else:
            stored["status"] = "completed"
            stored["message"] = "Review completed successfully."

        record_status(
            review_id,
            stored["status"],
            stored["message"],
            paper_id=paper_id,
            review_mode=review_mode,
        )
        _put_review(review_id, stored)

    except Exception as exc:  # pragma: no cover – safety net
        failed = _empty_review_record(review_id, paper_id, review_mode)
        failed["status"] = "failed"
        failed["message"] = str(exc)
        _put_review(review_id, failed)
        record_status(
            review_id, "failed", str(exc), paper_id=paper_id, review_mode=review_mode
        )


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT 1 – Health Check
# ═══════════════════════════════════════════════════════════════════════════


@app.get(
    "/api/health",
    summary="Health check",
    description="Returns a simple JSON object indicating the API is running. "
    "Used by deployment probes and the frontend connection check.",
    tags=["System"],
)
def health_check() -> Dict[str, str]:
    """Liveness probe – always returns ``{"status": "ok"}``."""
    return {"status": "ok"}


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT 2 – Upload Paper
# ═══════════════════════════════════════════════════════════════════════════


@app.post(
    "/api/review/upload",
    summary="Upload a PDF manuscript",
    description=(
        "Accepts a single PDF file via multipart form-data, validates the "
        "file header, registers the paper in the in-memory store, and returns "
        "a ``paper_id`` that must be passed to ``/api/review/start``."
    ),
    tags=["Papers"],
)
async def upload_paper(file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload and register a research paper for subsequent review.

    Validations performed:
    - File must have a ``.pdf`` extension.
    - File must begin with the ``%PDF`` magic bytes.
    - File must not be empty.

    Returns:
        JSON with ``paper_id``, ``filename``, ``title``, and ``status``.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="A PDF file is required.")
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    if not content or len(content) < 4:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400, detail="The uploaded file is not a valid PDF."
        )

    paper_id = f"paper_{uuid.uuid4().hex[:8]}"
    title = file.filename.rsplit(".pdf", 1)[0]
    abstract, sections, pages, full_text = extract_document_structure(file.filename, content)

    file_size_mb = f"{len(content)/(1024*1024):.1f} MB"
    paper = {
        "paper_id": paper_id,
        "title": title,
        "filename": file.filename,
        "abstract": abstract,
        "sections": sections,
        "pages": pages,
        "references": [],
        "figures": [],
        "tables": [],
        "file_size": file_size_mb,
        "full_text": full_text,
    }
    register_paper(paper_id, paper)
    try:
        save_paper_version(
            paper_id=paper_id,
            version=1,
            version_tag="v1.0",
            filename=file.filename,
            file_size=file_size_mb,
            total_issues=0,
            resolved_issues=0,
        )
    except Exception:
        pass

    return {
        "paper_id": paper_id,
        "filename": file.filename,
        "title": title,
        "status": "uploaded",
        "abstract": abstract,
        "sections": [s.get("name") for s in sections if isinstance(s, dict) and s.get("name")],
        "pages": len(pages),
        "file_size": file_size_mb,
    }


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS – Paper Management & Sidebar Tracking
# ═══════════════════════════════════════════════════════════════════════════


@app.get(
    "/api/papers",
    summary="List all tracked manuscripts and review statuses",
    description="Returns all manuscripts stored in SQLite with their latest review status and issue metrics for the sidebar tracker.",
    tags=["Papers"],
)
def list_papers() -> List[Dict[str, Any]]:
    """Retrieve all manuscripts and ongoing review statuses."""
    return get_all_papers_summary()


@app.get(
    "/api/papers/{paper_id}",
    summary="Get manuscript details and versions",
    description="Returns full manuscript details, saved revision versions, and associated review history.",
    tags=["Papers"],
)
def get_paper_details(paper_id: str) -> Dict[str, Any]:
    """Retrieve manuscript metadata, versions, and past review records."""
    paper = get_paper(paper_id)
    if not paper:
        paper = get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    versions = get_paper_versions(paper_id)
    reviews = get_reviews_by_paper_id(paper_id)
    return {
        "paper": paper,
        "versions": versions,
        "reviews": reviews,
    }


@app.delete(
    "/api/papers/{paper_id}",
    summary="Delete manuscript",
    description="Deletes a manuscript, associated reviews, statuses, and version records from SQLite.",
    tags=["Papers"],
)
def remove_paper(paper_id: str) -> Dict[str, str]:
    """Delete a manuscript and its associated records."""
    delete_paper(paper_id)
    return {"status": "ok", "message": f"Paper {paper_id} and associated reviews deleted."}


@app.post(
    "/api/papers/{paper_id}/version",
    summary="Record manuscript revision version",
    description="Persists a new manuscript revision version to SQLite.",
    tags=["Papers"],
)
def record_paper_version(paper_id: str, request: PaperVersionRequest) -> Dict[str, Any]:
    """Save revision version data to SQLite."""
    version_data = save_paper_version(
        paper_id=paper_id,
        version=request.version,
        version_tag=request.version_tag,
        filename=request.filename,
        file_size=request.file_size,
        total_issues=request.total_issues,
        resolved_issues=request.resolved_issues,
    )
    return {"status": "ok", "version": version_data}


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT 3 – Start Review
# ═══════════════════════════════════════════════════════════════════════════


@app.post(
    "/api/review/start",
    summary="Start a new review",
    description=(
        "Initiates the full LangGraph multi-agent review pipeline for an "
        "already-uploaded paper. The review runs asynchronously in the "
        "background; poll ``/api/review/{review_id}/status`` to track "
        "progress and fetch results from ``/api/review/{review_id}/result`` "
        "once the status reaches ``completed``."
    ),
    tags=["Reviews"],
)
async def start_review(request: ReviewStartRequest) -> Dict[str, Any]:
    """Kick off the review pipeline and return immediately with a review_id.

    The frontend uses the returned ``review_id`` to poll status and
    eventually retrieve the full review result.

    Raises:
        404 – if the ``paper_id`` does not correspond to an uploaded paper.
    """
    paper = get_paper(request.paper_id)
    if paper is None:
        raise HTTPException(
            status_code=404,
            detail="Paper not found. Upload the PDF before starting review.",
        )

    review_id = _new_review_id()
    review_mode = request.review_mode or "agentic_rag"

    # Pre-populate the store so /status returns immediately.
    sections = list(paper.get("sections", []) or [])
    pages = list(paper.get("pages", []) or [])
    record = _empty_review_record(review_id, request.paper_id, review_mode)
    record.update(
        {
            "sections": sections,
            "pages": pages,
            "paper_text": _paper_text_from_sections(sections),
        }
    )
    _put_review(review_id, record)
    record_status(
        review_id,
        "running",
        "Review started.",
        paper_id=request.paper_id,
        review_mode=review_mode,
    )

    # Launch the pipeline without blocking the response.
    asyncio.create_task(
        _run_review_pipeline(review_id, request.paper_id, review_mode)
    )

    return {
        "review_id": review_id,
        "paper_id": request.paper_id,
        "status": "running",
        "review_mode": review_mode,
        "message": "Review started successfully.",
    }


@app.post(
    "/api/review",
    summary="Start a new review (alias for /api/review/start)",
    include_in_schema=False,
)
async def start_review_alias(request: ReviewStartRequest) -> Dict[str, Any]:
    """Compatibility alias for /api/review/start."""
    return await start_review(request)


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT 4 – Poll Review Status (lightweight)
# ═══════════════════════════════════════════════════════════════════════════


@app.get(
    "/api/review/{review_id}/status",
    summary="Poll review status",
    description=(
        "Returns a lightweight status object for the review. The frontend "
        "polls this every 2 seconds while the review is ``running`` or "
        "``reviewing``. No heavy review data is included — use "
        "``/api/review/{review_id}/result`` for the full payload."
    ),
    tags=["Reviews"],
)
def get_review_status(review_id: str) -> Dict[str, Any]:
    """Return the current progress of a review.

    Fields returned:
    - ``review_id`` / ``paper_id``
    - ``status`` – one of running, reviewing, waiting_for_human,
      re_reviewing, completed, failed
    - ``review_mode``
    - ``needs_human_feedback`` – true when the pipeline paused for author input
    - ``message`` – human-readable progress note

    Raises:
        404 – if the review_id is unknown.
    """
    stored = _get_review(review_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Review not found.")

    snapshot = get_status_snapshot(review_id)
    status_value = snapshot.get("status") or stored.get("status", "completed")

    return {
        "review_id": review_id,
        "paper_id": stored.get("paper_id") or snapshot.get("paper_id"),
        "status": status_value,
        "review_mode": stored.get("review_mode")
        or snapshot.get("review_mode", "agentic_rag"),
        "needs_human_feedback": bool(
            stored.get("needs_human_feedback")
            or snapshot.get("needs_human_feedback")
        ),
        "message": snapshot.get("message") or stored.get("message"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT 5 – Full Review Result
# ═══════════════════════════════════════════════════════════════════════════


@app.get(
    "/api/review/{review_id}/result",
    summary="Get full review result",
    description=(
        "Returns the complete review payload including individual specialist "
        "reviews (rigor, clarity, novelty), the meta-review, the final "
        "report, all issues, conflicts, RAG retrieval evidence, and any "
        "author feedback submitted so far."
    ),
    tags=["Reviews"],
)
def get_review_result(review_id: str) -> Dict[str, Any]:
    """Fetch the full result of a completed (or in-progress) review.

    This is the heavyweight endpoint the frontend calls once the status
    reaches ``completed``, ``failed``, or ``waiting_for_human``.

    Raises:
        404 – if the review_id is unknown.
    """
    stored = _get_review(review_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Review not found.")

    return {
        "review_id": review_id,
        "paper_id": stored.get("paper_id"),
        "status": stored.get("status", "completed"),
        "review_mode": stored.get("review_mode", "agentic_rag"),
        "final_report": stored.get("final_report"),
        "meta_review": stored.get("meta_review"),
        "rigor_review": stored.get("rigor_review"),
        "clarity_review": stored.get("clarity_review"),
        "novelty_review": stored.get("novelty_review"),
        "retrieval_history": stored.get("retrieval_history", []),
        "retrieved_documents": stored.get("retrieved_documents", []),
        "issues": stored.get("issues", []),
        "conflicts": stored.get("conflicts", []),
        "human_feedback": stored.get("human_feedback", []),
        "solutions_generated": stored.get("solutions_generated", False),
        "page_coverage": stored.get("page_registry") or (stored.get("final_report") or {}).get("page_coverage") or {},
        "message": stored.get("message"),
    }


@app.post(
    "/api/review/{review_id}/generate-report",
    summary="Generate actionable solutions and full report on-demand",
    description=(
        "Invoked when the user explicitly clicks 'Give Report'. Generates "
        "actionable 3-step remediation plans for each identified issue, "
        "enriches the stored review record, and returns the updated issues "
        "and finalized report."
    ),
    tags=["Reviews"],
)
async def generate_report_endpoint(review_id: str) -> Dict[str, Any]:
    """Generate solutions and action plans for review issues on demand."""
    stored = _get_review(review_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Review not found.")

    issues_list = list(stored.get("issues") or [])
    if not issues_list:
        for rev_key in ("rigor_review", "clarity_review", "novelty_review"):
            rev = stored.get(rev_key) or {}
            for it in rev.get("issues", []) or []:
                issues_list.append(it)

    paper_id = stored.get("paper_id")
    paper = get_paper(paper_id) or get_paper_by_id(paper_id) or {}
    paper_title = paper.get("title") or "Research Manuscript"
    paper_context = paper.get("full_text") or _paper_text_from_sections(paper.get("sections") or [])

    # Generate actionable 3-step solutions
    enriched_issues = generate_solutions(
        issues=issues_list,
        paper_context=paper_context,
        paper_title=paper_title,
    )

    for iss in enriched_issues:
        iss["solution_pending"] = False

    stored["issues"] = enriched_issues
    stored["solutions_generated"] = True
    if stored.get("final_report"):
        stored["final_report"]["solutions_generated"] = True
        stored["final_report"]["recommended_actions"] = [
            iss.get("suggestedAction") for iss in enriched_issues if iss.get("suggestedAction")
        ]

    _put_review(review_id, stored)

    return {
        "status": "ok",
        "review_id": review_id,
        "solutions_generated": True,
        "issues": enriched_issues,
        "all_mistakes": enriched_issues,
        "final_report": stored.get("final_report"),
        "page_coverage": stored.get("page_registry") or (stored.get("final_report") or {}).get("page_coverage") or {},
        "message": "Action plans and report generated successfully.",
    }


@app.get(
    "/api/review/{review_id}",
    summary="Get full review result (alias for /api/review/{review_id}/result)",
    include_in_schema=False,
)
def get_review_result_alias(review_id: str) -> Dict[str, Any]:
    """Compatibility alias for /api/review/{review_id}/result."""
    return get_review_result(review_id)


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT 6 – Submit Author Feedback
# ═══════════════════════════════════════════════════════════════════════════


@app.post(
    "/api/review/{review_id}/feedback",
    summary="Submit author feedback on an issue",
    description=(
        "Allows the author to accept (``approve``) or dispute an issue "
        "flagged by one of the specialist reviewers. The feedback is "
        "appended to the review record and, if the review was paused "
        "for human input (``waiting_for_human``), triggers a background "
        "re-review cycle through the LangGraph pipeline."
    ),
    tags=["Reviews"],
)
async def submit_feedback(
    review_id: str, payload: FeedbackRequest
) -> Dict[str, Any]:
    """Record an author's accept / dispute decision on a specific issue.

    Behaviour:
    - The feedback entry is persisted immediately.
    - If the review's current status is ``waiting_for_human``, a background
      re-review is triggered automatically so the meta-reviewer can
      incorporate the decision.
    - The response includes the updated feedback list and the current
      review status.

    Raises:
        404 – if the review_id is unknown or the paper reference is missing.
    """
    stored = _get_review(review_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Review not found.")

    # Append feedback entry.
    feedback_list: List[Dict[str, Any]] = list(
        stored.get("human_feedback") or []
    )
    feedback_list.append(
        {
            "issue_id": payload.issue_id,
            "decision": payload.decision.lower(),
            "reason": payload.reason or "",
        }
    )
    stored["human_feedback"] = feedback_list
    _put_review(review_id, stored)

    # If the pipeline was waiting for human input, trigger a re-review.
    paper_id = stored.get("paper_id")
    if not paper_id:
        raise HTTPException(
            status_code=404, detail="Paper reference missing for review."
        )

    current_status = stored.get("status", "")
    if current_status in {"waiting_for_human", "re_reviewing"}:
        review_mode = stored.get("review_mode", "agentic_rag")
        stored["status"] = "re_reviewing"
        stored["message"] = "Re-reviewing after author feedback."
        _put_review(review_id, stored)
        record_status(
            review_id,
            "re_reviewing",
            "Re-reviewing after author feedback.",
            paper_id=paper_id,
            review_mode=review_mode,
        )
        asyncio.create_task(
            _run_review_pipeline(review_id, paper_id, review_mode)
        )

    return {
        "status": "ok",
        "message": "Feedback recorded.",
        "human_feedback": feedback_list,
        "review_status": stored.get("status", "reviewing"),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT 6.5 – Reconsider Flagged Issue with Author Argument
# ═══════════════════════════════════════════════════════════════════════════


@app.post(
    "/api/review/{review_id}/issue/{issue_id}/reconsider",
    summary="Reconsider a flagged issue based on author counter-argument",
    description=(
        "Evaluates the author's argument against the flagged issue: "
        "if correct -> removes/retracts the issue; "
        "if changes perspective -> reframes description and provides tailored solutions; "
        "otherwise upholds the issue."
    ),
    tags=["Reviews"],
)
async def reconsider_issue_endpoint(
    review_id: str,
    issue_id: str,
    payload: ReconsiderIssueRequest,
) -> Dict[str, Any]:
    """Reconsider a flagged issue using the Reconsideration Agent."""
    stored = _get_review(review_id)
    if not stored:
        raise HTTPException(status_code=404, detail="Review not found.")

    issues_list = list(stored.get("issues") or [])
    if not issues_list:
        for rev_key in ("rigor_review", "clarity_review", "novelty_review"):
            rev = stored.get(rev_key) or {}
            for it in rev.get("issues", []) or []:
                issues_list.append(it)

    target_issue = None
    target_idx = -1
    for idx, iss in enumerate(issues_list):
        if iss.get("id") == issue_id or iss.get("issue") == issue_id:
            target_issue = iss
            target_idx = idx
            break

    if not target_issue:
        raise HTTPException(status_code=404, detail=f"Issue '{issue_id}' not found in review.")

    paper_id = stored.get("paper_id")
    paper = get_paper(paper_id) or get_paper_by_id(paper_id) or {}
    paper_title = paper.get("title") or "Research Manuscript"
    paper_context = paper.get("full_text") or _paper_text_from_sections(paper.get("sections") or [])

    eval_result = evaluate_author_argument(
        issue=target_issue,
        author_argument=payload.author_argument,
        paper_title=paper_title,
        paper_context=paper_context,
    )

    outcome = eval_result["outcome"]
    verdict_reason = eval_result["verdict_reason"]

    if outcome == "remove":
        target_issue["status"] = "dismissed"
        target_issue["dismissed"] = True
        target_issue["resolvedInRevision"] = True
        target_issue["resolutionNote"] = verdict_reason
        target_issue["reconsidered"] = True
        target_issue["reconsiderationOutcome"] = "dismissed"
        target_issue["reconsiderationNote"] = verdict_reason
        target_issue["title"] = target_issue.get("title") or target_issue.get("issue") or "Flagged issue"
        target_issue["issue"] = target_issue["title"]
        target_issue["suggestedAction"] = target_issue.get("suggestedAction") or target_issue.get("recommendation") or "Clarify with supporting evidence."
        target_issue["recommendation"] = target_issue["suggestedAction"]

        # Pop from active issues list so it is removed from active review
        issues_list.pop(target_idx)
        stored["issues"] = issues_list
        removed_issues = list(stored.get("removed_issues") or [])
        removed_issues.append(target_issue)
        stored["removed_issues"] = removed_issues
    elif outcome == "reframe":
        target_issue["status"] = "open"
        target_issue["title"] = eval_result.get("updated_title") or target_issue.get("title")
        target_issue["explanation"] = eval_result.get("updated_explanation") or target_issue.get("explanation")
        target_issue["suggestedAction"] = eval_result.get("updated_solution") or target_issue.get("suggestedAction")
        if eval_result.get("updated_action_plan"):
            target_issue["actionPlan"] = eval_result["updated_action_plan"]
        target_issue["reconsidered"] = True
        target_issue["reconsiderationOutcome"] = "reframed"
        target_issue["reconsiderationNote"] = verdict_reason
        target_issue["disputeReason"] = payload.author_argument

        target_issue["title"] = target_issue.get("title") or target_issue.get("issue") or "Flagged issue"
        target_issue["issue"] = target_issue["title"]
        target_issue["suggestedAction"] = target_issue.get("suggestedAction") or target_issue.get("recommendation") or "Clarify with supporting evidence."
        target_issue["recommendation"] = target_issue["suggestedAction"]
        issues_list[target_idx] = target_issue
        stored["issues"] = issues_list
    else:
        target_issue["status"] = "disputed"
        target_issue["reconsidered"] = True
        target_issue["reconsiderationOutcome"] = "upheld"
        target_issue["reconsiderationNote"] = verdict_reason
        target_issue["disputeReason"] = payload.author_argument

        target_issue["title"] = target_issue.get("title") or target_issue.get("issue") or "Flagged issue"
        target_issue["issue"] = target_issue["title"]
        target_issue["suggestedAction"] = target_issue.get("suggestedAction") or target_issue.get("recommendation") or "Clarify with supporting evidence."
        target_issue["recommendation"] = target_issue["suggestedAction"]
        issues_list[target_idx] = target_issue
        stored["issues"] = issues_list

    # Append to human_feedback history
    feedback_list = list(stored.get("human_feedback") or [])
    feedback_list.append({
        "issue_id": issue_id,
        "decision": "reconsidered",
        "reason": payload.author_argument,
        "outcome": outcome,
        "verdict_reason": verdict_reason,
    })
    stored["human_feedback"] = feedback_list

    # Persist updated review to SQLite & memory cache
    _put_review(review_id, stored)

    return {
        "status": "ok",
        "outcome": outcome,
        "verdict_reason": verdict_reason,
        "updated_issue": target_issue,
        "issues": issues_list,
        "message": f"Issue reconsideration complete: {outcome}.",
    }


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT 7 – Upload and Run Review Workflow (All-in-One)
# ═══════════════════════════════════════════════════════════════════════════


@app.post(
    "/api/review/upload-and-review",
    summary="Upload manuscript and run full review workflow",
    description=(
        "All-in-one endpoint: uploads a manuscript file (PDF, TXT, MD), executes "
        "the complete LangGraph multi-agent review pipeline, and returns the comprehensive "
        "results including all identified mistakes/issues, severity breakdown, and review report."
    ),
    tags=["Reviews"],
)
async def upload_and_review(
    file: UploadFile = File(..., description="The manuscript file (PDF, TXT, or MD)."),
    review_mode: str = Form(
        default="agentic_rag",
        description="Review mode: 'no_rag', 'basic_rag', or 'agentic_rag'.",
    ),
) -> Dict[str, Any]:
    """Upload a paper, execute the review workflow to completion, and return all mistakes.

    Parameters:
    - file: Multipart file upload (PDF, TXT, or Markdown)
    - review_mode: 'agentic_rag' (default), 'basic_rag', or 'no_rag'

    Returns:
    - JSON object containing:
      - review_id & paper_id
      - status ("completed")
      - mistakes_summary (total_mistakes, critical_count, high_count, etc.)
      - all_mistakes / issues (list of all identified mistakes with severity, reviewer, recommendation)
      - critical_issues, high_issues, medium_issues, low_issues
      - final_report (overall assessment and recommended actions)
      - specialist reviews (rigor_review, clarity_review, novelty_review, meta_review)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file is required.")

    filename_lower = file.filename.lower()
    valid_exts = (".pdf", ".txt", ".md")
    if not any(filename_lower.endswith(ext) for ext in valid_exts):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload a PDF, TXT, or Markdown file.",
        )

    content = await file.read()
    if not content or len(content) < 4:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if filename_lower.endswith(".pdf") and not content.startswith(b"%PDF"):
        raise HTTPException(
            status_code=400, detail="The uploaded file is not a valid PDF."
        )

    paper_id = f"paper_{uuid.uuid4().hex[:8]}"
    review_id = _new_review_id()
    title = file.filename.rsplit(".", 1)[0]

    abstract, sections, pages, paper_text = extract_document_structure(file.filename, content)

    paper = {
        "paper_id": paper_id,
        "title": title,
        "filename": file.filename,
        "abstract": abstract,
        "sections": sections,
        "pages": pages,
        "references": [],
        "figures": [],
        "tables": [],
    }
    register_paper(paper_id, paper)

    record = _empty_review_record(review_id, paper_id, review_mode)
    record.update(
        {
            "sections": sections,
            "pages": pages,
            "paper_text": paper_text,
        }
    )
    _put_review(review_id, record)
    record_status(
        review_id,
        "reviewing",
        "Running review pipeline across specialist agents.",
        paper_id=paper_id,
        review_mode=review_mode,
    )

    try:
        runner_sync = globals().get("run_review_graph_sync")
        if callable(runner_sync) and runner_sync is not _ORIGINAL_RUN_REVIEW_GRAPH_SYNC:
            res = runner_sync(review_id, paper_id, review_mode=review_mode)
            result = await res if asyncio.iscoroutine(res) else res
        else:
            result = await run_review_graph(review_id, paper_id, review_mode=review_mode)

        stored = _coerce_result(result, review_id, paper_id, review_mode)
        stored["status"] = "completed"
        stored["message"] = "Review completed successfully."
        _put_review(review_id, stored)
        record_status(
            review_id,
            "completed",
            "Review completed successfully.",
            paper_id=paper_id,
            review_mode=review_mode,
        )
    except Exception as exc:
        failed = _empty_review_record(review_id, paper_id, review_mode)
        failed["status"] = "failed"
        failed["message"] = str(exc)
        _put_review(review_id, failed)
        record_status(
            review_id, "failed", str(exc), paper_id=paper_id, review_mode=review_mode
        )
        raise HTTPException(
            status_code=500, detail=f"Review workflow failed: {exc}"
        )

    final_report = stored.get("final_report") or {}
    meta_review = stored.get("meta_review") or {}
    rigor_review = stored.get("rigor_review") or {}
    clarity_review = stored.get("clarity_review") or {}
    novelty_review = stored.get("novelty_review") or {}

    all_issues = list(stored.get("issues") or [])
    if not all_issues:
        seen_ids = set()
        for rev in (rigor_review, clarity_review, novelty_review):
            for issue in rev.get("issues", []) or []:
                iid = issue.get("id") or issue.get("issue")
                if iid and iid not in seen_ids:
                    seen_ids.add(iid)
                    all_issues.append(issue)

    critical_issues = list(final_report.get("critical_issues", []) or [])
    high_issues = list(final_report.get("high_issues", []) or [])
    medium_issues = list(final_report.get("medium_issues", []) or [])
    low_issues = list(final_report.get("low_issues", []) or [])

    try:
        save_paper_version(
            paper_id=paper_id,
            version=1,
            version_tag="v1.0",
            filename=file.filename,
            file_size=f"{len(content)/(1024*1024):.1f} MB",
            total_issues=len(all_issues),
            resolved_issues=0,
        )
    except Exception:
        pass

    return {
        "status": stored.get("status", "completed"),
        "review_id": review_id,
        "paper_id": paper_id,
        "title": title,
        "filename": file.filename,
        "review_mode": review_mode,
        "mistakes_summary": {
            "total_mistakes": len(all_issues),
            "critical_count": len(critical_issues),
            "high_count": len(high_issues),
            "medium_count": len(medium_issues),
            "low_count": len(low_issues),
        },
        "all_mistakes": all_issues,
        "issues": all_issues,
        "critical_issues": critical_issues,
        "high_issues": high_issues,
        "medium_issues": medium_issues,
        "low_issues": low_issues,
        "conflicts": stored.get("conflicts", []),
        "final_report": final_report,
        "rigor_review": rigor_review,
        "clarity_review": clarity_review,
        "novelty_review": novelty_review,
        "meta_review": meta_review,
        "retrieval_history": stored.get("retrieval_history", []),
        "retrieved_documents": stored.get("retrieved_documents", []),
        "page_coverage": stored.get("page_registry") or (stored.get("final_report") or {}).get("page_coverage") or {},
        "message": stored.get("message", "Review completed successfully."),
    }


# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINT 8 – Re-Review Revised Manuscript & Error Change Verification
# ═══════════════════════════════════════════════════════════════════════════


@app.post(
    "/api/review/{paper_id}/re-review",
    summary="Re-review revised paper and verify whether errors were changed/fixed",
    description=(
        "Accepts a revised manuscript file for an existing paper, extracts updated sections, "
        "and evaluates whether previously identified errors have been changed/resolved. "
        "Performs error diff verification, identifies any new issues, increments version tag, "
        "and stores revision records in SQLite."
    ),
    tags=["Reviews"],
)
async def rereview_revised_paper(
    paper_id: str,
    file: UploadFile = File(..., description="Revised manuscript file (PDF, TXT, or MD)"),
    review_mode: str = Form(default="agentic_rag", description="Review mode"),
) -> Dict[str, Any]:
    """Re-review a revised paper draft and verify if previous errors have been changed/resolved."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="A revised file is required.")

    paper = get_paper(paper_id) or get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Original paper not found in database.")

    filename_lower = file.filename.lower()
    valid_exts = (".pdf", ".txt", ".md")
    if not any(filename_lower.endswith(ext) for ext in valid_exts):
        raise HTTPException(status_code=400, detail="Unsupported file format.")

    content = await file.read()
    if not content or len(content) < 4:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if filename_lower.endswith(".pdf") and not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="The uploaded file is not a valid PDF.")

    # 1. Extract revised document structure
    revised_abstract, revised_sections, revised_pages, revised_paper_text = extract_document_structure(file.filename, content)

    # 2. Get previous issues from latest review
    reviews = get_reviews_by_paper_id(paper_id)
    previous_issues: List[Dict[str, Any]] = []
    if reviews:
        latest_rev_id = reviews[0].get("review_id")
        latest_full_rev = _get_review(latest_rev_id)
        if latest_full_rev:
            previous_issues = list(latest_full_rev.get("issues") or [])
            if not previous_issues:
                for rev_key in ("rigor_review", "clarity_review", "novelty_review"):
                    rev = latest_full_rev.get(rev_key) or {}
                    for it in rev.get("issues", []) or []:
                        previous_issues.append(it)

    previous_paper_text = paper.get("full_text") or _paper_text_from_sections(paper.get("sections") or [])

    # 3. Verify whether previous errors have been changed / fixed in the revised text
    verification = verify_revision_errors(
        previous_issues=previous_issues,
        original_paper_text=previous_paper_text,
        revised_paper_text=revised_paper_text,
        revised_sections=revised_sections,
        original_sections=paper.get("sections") or [],
    )

    # 4. Update paper in memory & SQLite with the new version details
    file_size_mb = f"{len(content)/(1024*1024):.1f} MB"
    paper["filename"] = file.filename
    paper["abstract"] = revised_abstract or paper.get("abstract", "")
    paper["sections"] = revised_sections
    paper["pages"] = revised_pages
    paper["full_text"] = revised_paper_text
    paper["file_size"] = file_size_mb
    register_paper(paper_id, paper)

    # 5. Determine version tag (e.g. v2.0)
    existing_versions = get_paper_versions(paper_id)
    if not any(v.get("version") == 1 for v in existing_versions):
        save_paper_version(
            paper_id=paper_id,
            version=1,
            version_tag="v1.0",
            filename=paper.get("filename", file.filename),
            file_size=paper.get("file_size", file_size_mb),
            total_issues=len(previous_issues),
            resolved_issues=0,
        )
        existing_versions = get_paper_versions(paper_id)

    max_ver = max((v.get("version", 1) for v in existing_versions), default=1)
    new_version_num = max(2, max_ver + 1)
    new_version_tag = f"v{new_version_num}.0"

    # 6. Execute review graph on revised manuscript to verify and capture new issues
    new_review_id = _new_review_id()
    record = _empty_review_record(new_review_id, paper_id, review_mode)
    record.update({
        "sections": revised_sections,
        "pages": revised_pages,
        "paper_text": revised_paper_text,
    })
    _put_review(new_review_id, record)
    record_status(new_review_id, "reviewing", f"Re-reviewing revision {new_version_tag} across specialist agents...", paper_id=paper_id, review_mode=review_mode)

    try:
        runner_sync = globals().get("run_review_graph_sync")
        if callable(runner_sync) and runner_sync is not _ORIGINAL_RUN_REVIEW_GRAPH_SYNC:
            res = runner_sync(new_review_id, paper_id, review_mode=review_mode)
            result = await res if asyncio.iscoroutine(res) else res
        else:
            result = await run_review_graph(new_review_id, paper_id, review_mode=review_mode)
        fresh_review = _coerce_result(result, new_review_id, paper_id, review_mode)
    except Exception as exc:
        fresh_review = record

    # 7. Merge verification results with fresh review
    verified_map = {item["id"]: item for item in verification.get("verified_issues", [])}
    merged_issues: List[Dict[str, Any]] = []
    seen_ids = set()

    for old_iss in previous_issues:
        iid = old_iss.get("id")
        v = verified_map.get(iid)
        iss_copy = dict(old_iss)
        if v and v.get("resolved"):
            iss_copy["resolvedInRevision"] = True
            iss_copy["resolvedInVersion"] = new_version_tag
            iss_copy["resolutionNote"] = v.get("change_summary")
            iss_copy["revisedEvidence"] = v.get("revised_evidence")
            iss_copy["status"] = "accepted"
        else:
            iss_copy["resolvedInRevision"] = False
            iss_copy["resolutionNote"] = v.get("change_summary") if v else "Error still present in revised text."
            iss_copy["revisedEvidence"] = v.get("revised_evidence") if v else ""
            iss_copy["status"] = "open"
        seen_ids.add(iid)
        merged_issues.append(iss_copy)

    # Check for newly introduced issues in the fresh review
    fresh_issues = list(fresh_review.get("issues") or [])
    newly_added_count = 0
    for n_iss in fresh_issues:
        nid = n_iss.get("id") or n_iss.get("issue")
        if nid and nid not in seen_ids:
            seen_ids.add(nid)
            n_copy = dict(n_iss)
            n_copy["introducedInVersion"] = new_version_tag
            n_copy["status"] = "open"
            merged_issues.append(n_copy)
            newly_added_count += 1

    verification["new_errors_introduced"] = newly_added_count

    # 8. Persist new version to SQLite paper_versions
    save_paper_version(
        paper_id=paper_id,
        version=new_version_num,
        version_tag=new_version_tag,
        filename=file.filename,
        file_size=file_size_mb,
        total_issues=len(merged_issues),
        resolved_issues=verification.get("errors_resolved", 0),
    )

    # 9. Store the completed re-review record
    fresh_review["status"] = "completed"
    fresh_review["message"] = f"Re-review of {new_version_tag} completed: {verification['verdict']}"
    fresh_review["issues"] = merged_issues
    fresh_review["revision_comparison"] = verification
    _put_review(new_review_id, fresh_review)
    record_status(new_review_id, "completed", fresh_review["message"], paper_id=paper_id, review_mode=review_mode)

    return {
        "status": "completed",
        "paper_id": paper_id,
        "review_id": new_review_id,
        "version": new_version_num,
        "version_tag": new_version_tag,
        "filename": file.filename,
        "file_size": file_size_mb,
        "revision_comparison": verification,
        "all_mistakes": merged_issues,
        "issues": merged_issues,
        "mistakes_summary": {
            "total_mistakes": len(merged_issues),
            "errors_resolved": verification.get("errors_resolved", 0),
            "errors_persisting": verification.get("errors_persisting", 0),
            "new_errors_introduced": newly_added_count,
        },
        "final_report": fresh_review.get("final_report") or {},
        "rigor_review": fresh_review.get("rigor_review") or {},
        "clarity_review": fresh_review.get("clarity_review") or {},
        "novelty_review": fresh_review.get("novelty_review") or {},
        "meta_review": fresh_review.get("meta_review") or {},
        "message": fresh_review["message"],
    }


# ═══════════════════════════════════════════════════════════════════════════
# Utility – Reset (development only)
# ═══════════════════════════════════════════════════════════════════════════


@app.post(
    "/api/reset",
    summary="Reset all data (development)",
    description=(
        "Clears the SQLite review database, status tracker, and paper "
        "registry, as well as in-memory caches."
    ),
    tags=["System"],
)
def reset_all() -> Dict[str, str]:
    """Wipe every store — useful during development."""
    _REVIEW_STORE.clear()
    clear_statuses()
    clear_papers()
    try:
        delete_all_reviews()
        delete_all_papers()
        delete_all_statuses()
    except Exception:
        pass
    return {"status": "ok", "message": "All database and in-memory data cleared."}

# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(app, host="0.0.0.0", port=8000)
