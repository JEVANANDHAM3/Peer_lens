from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from backend.tools.paper_tools import get_paper


def _normalize_table(table: Dict[str, Any]) -> Dict[str, Any]:
    table_number = table.get("table_number") or table.get("name") or "Table"
    caption = table.get("caption") or table.get("title") or ""
    headers = table.get("headers") or []
    rows = table.get("rows") or []
    return {
        "table_number": str(table_number),
        "caption": str(caption),
        "headers": [str(item) for item in headers],
        "rows": rows,
    }


def extract_tables(paper_id: str, page: Optional[int] = None) -> Dict[str, Any]:
    """Extract structured tables from a paper or return the best available parsed content."""
    paper = get_paper(paper_id)
    if not paper:
        return {"paper_id": paper_id, "page": page, "tables": [], "error": "Paper not found."}

    raw_tables = paper.get("tables") or []
    parsed_tables: List[Dict[str, Any]] = []
    for table in raw_tables:
        if page is not None and table.get("page") not in (None, page):
            continue
        parsed_tables.append(_normalize_table(table))

    if not parsed_tables:
        for section in paper.get("sections", []):
            if page is not None and section.get("page") != page:
                continue
            text = str(section.get("text") or "")
            if "table" in text.lower() or "baseline" in text.lower():
                matches = re.findall(r"Table\s*\d+[\s\S]*?(?:\n\n|$)", text, flags=re.IGNORECASE)
                if matches:
                    for idx, block in enumerate(matches[:5], start=1):
                        parsed_tables.append({
                            "table_number": f"Table {idx}",
                            "caption": "Extracted table block",
                            "headers": [],
                            "rows": [],
                            "raw_text": block,
                        })

    if not parsed_tables and page is not None:
        for entry in paper.get("pages", []):
            if entry.get("page") == page:
                raw_text = str(entry.get("text") or "")
                if "table" in raw_text.lower():
                    parsed_tables.append({
                        "table_number": f"Table {page}",
                        "caption": "Extracted page table content",
                        "headers": [],
                        "rows": [],
                        "raw_text": raw_text[:2000],
                    })

    return {
        "paper_id": paper_id,
        "page": page,
        "tables": parsed_tables,
        "observations": [
            f"Extracted {len(parsed_tables)} table(s) for {paper_id}." if parsed_tables else "No tables were extracted automatically."
        ],
    }
