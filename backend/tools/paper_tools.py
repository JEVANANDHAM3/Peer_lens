"""Paper-level evidence tools for the rigor reviewer.

These tools are intentionally narrow: they read the uploaded manuscript and
locate supporting evidence without performing literature search or workflow
routing.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from langchain_core.tools import BaseTool, tool
except ImportError:  # pragma: no cover
    BaseTool = Any  # type: ignore[misc]
    def tool(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

try:
    from backend.database import delete_all_papers, get_paper_by_id, save_paper
except Exception:  # pragma: no cover
    save_paper = None
    get_paper_by_id = None
    delete_all_papers = None

_PAPER_STORE: Dict[str, Dict[str, Any]] = {}


def register_paper(paper_id: str, paper: Dict[str, Any]) -> Dict[str, Any]:
    """Register a paper in the in-memory cache and SQLite database."""
    if not paper_id:
        raise ValueError("paper_id must be a non-empty string")
    _PAPER_STORE[paper_id] = paper
    if save_paper is not None:
        try:
            save_paper(dict(paper, paper_id=paper_id))
        except Exception:
            pass
    return paper


def get_paper(paper_id: str) -> Optional[Dict[str, Any]]:
    if not paper_id:
        return None
    if paper_id in _PAPER_STORE:
        return _PAPER_STORE[paper_id]
    if get_paper_by_id is not None:
        try:
            db_paper = get_paper_by_id(paper_id)
            if db_paper:
                _PAPER_STORE[paper_id] = db_paper
                return db_paper
        except Exception:
            pass
    return None


def clear_papers() -> None:
    _PAPER_STORE.clear()
    if delete_all_papers is not None:
        try:
            delete_all_papers()
        except Exception:
            pass



def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value)


def read_paper(paper_id: str, section: Optional[str] = None, page: Optional[int] = None) -> Dict[str, Any]:
    """Return the requested section or page and preserve the manuscript metadata."""
    paper = get_paper(paper_id)
    if not paper:
        return {"paper_id": paper_id, "section": section, "page": page, "text": "", "error": "Paper not found."}

    sections: List[Dict[str, Any]] = paper.get("sections", []) or []
    pages: List[Dict[str, Any]] = paper.get("pages", []) or []

    if page is not None:
        page_match = next((entry for entry in pages if entry.get("page") == page), None)
        if page_match:
            section_name = next((entry.get("name", f"Page {page}") for entry in sections if entry.get("page") == page), f"Page {page}")
            text = _normalize_text(page_match.get("text"))
            return {"paper_id": paper_id, "page": page, "section": section_name, "text": text, "extracted_text": text}

    if section:
        norm = section.strip().lower()
        match = next((entry for entry in sections if norm in _normalize_text(entry.get("name")).lower() or _normalize_text(entry.get("name")).lower() in norm), None)
        if match:
            text = _normalize_text(match.get("text"))
            return {"paper_id": paper_id, "page": match.get("page", page or 1), "section": match.get("name", section), "text": text, "extracted_text": text}

        text_match = next((entry for entry in sections if norm in _normalize_text(entry.get("text")).lower()), None)
        if text_match:
            text = _normalize_text(text_match.get("text"))
            return {"paper_id": paper_id, "page": text_match.get("page", page or 1), "section": text_match.get("name", section or "Unknown Section"), "text": text, "extracted_text": text}

    if pages:
        first_page = pages[0]
        return {"paper_id": paper_id, "page": first_page.get("page", 1), "section": section or "Unknown Section", "text": _normalize_text(first_page.get("text")), "extracted_text": _normalize_text(first_page.get("text"))}

    return {"paper_id": paper_id, "section": section, "page": page, "text": "", "extracted_text": "", "error": "No extracted text available."}


def locate_evidence(paper_id: str, query: str) -> Dict[str, Any]:
    """Locate evidence in the paper related to a query or suspected issue."""
    if not query or not query.strip():
        return {"paper_id": paper_id, "query": query, "matches": []}

    paper = get_paper(paper_id)
    if not paper:
        return {"paper_id": paper_id, "query": query, "matches": [], "error": "Paper not found."}

    query_words = [token.lower() for token in query.split() if len(token) > 2]
    matches: List[Dict[str, Any]] = []

    for section in paper.get("sections", []) or []:
        section_text = _normalize_text(section.get("text"))
        section_name = _normalize_text(section.get("name"))
        if not section_text:
            continue
        score = sum(1 for term in query_words if term in section_text.lower())
        if score > 0:
            excerpt = section_text[:2000]
            matches.append({"page": section.get("page"), "section": section_name or "Unknown Section", "text": excerpt})

    for page_entry in paper.get("pages", []) or []:
        page_text = _normalize_text(page_entry.get("text"))
        if not page_text:
            continue
        score = sum(1 for term in query_words if term in page_text.lower())
        if score > 0 and not any(match.get("page") == page_entry.get("page") for match in matches):
            section_name = next((section.get("name", "Unknown Section") for section in paper.get("sections", []) if section.get("page") == page_entry.get("page")), "Unknown Section")
            matches.append({"page": page_entry.get("page"), "section": section_name, "text": page_text[:2000]})

    return {"paper_id": paper_id, "query": query, "matches": matches}


def create_paper_tools(paper_data: Optional[Dict[str, Any]] = None) -> List[BaseTool]:
    """Build the LangChain tool objects bound to a paper if available."""

    @tool("read_paper")
    def read_tool(section: str = "", page: Optional[int] = None) -> Dict[str, Any]:
        paper_id = (paper_data or {}).get("paper_id") or (paper_data or {}).get("id")
        if not paper_id:
            return {"paper_id": None, "section": section, "page": page, "text": "", "error": "No paper_id available for this tool call."}
        return read_paper(paper_id, section=section or None, page=page)

    @tool("locate_evidence")
    def locate_tool(query: str) -> Dict[str, Any]:
        paper_id = (paper_data or {}).get("paper_id") or (paper_data or {}).get("id")
        if not paper_id:
            return {"paper_id": None, "query": query, "matches": [], "error": "No paper_id available for this tool call."}
        return locate_evidence(paper_id, query)

    return [read_tool, locate_tool]
