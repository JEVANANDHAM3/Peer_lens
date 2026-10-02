from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

try:
    from langchain_core.tools import tool
except ImportError:  # pragma: no cover
    def tool(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

from backend.tools.paper_tools import get_paper


def _normalize_text(value: Any) -> str:
    return "" if value is None else str(value)


def _normalize_ref_title(value: Any) -> str:
    text = _normalize_text(value).lower()
    text = re.sub(r"\s+", " ", text)
    text = text.replace("&", "and")
    return text.strip()


def check_reference_consistency(paper_id: str) -> Dict[str, Any]:
    """Audit internal reference and citation consistency without judging the research itself."""
    paper = get_paper(paper_id)
    if not paper:
        return {"paper_id": paper_id, "issues": [], "observations": [], "evidence": [], "error": "Paper not found."}

    sections = paper.get("sections") or []
    references = paper.get("references") or []
    figures = paper.get("figures") or []
    tables = paper.get("tables") or []

    issues: List[str] = []
    observations: List[str] = []
    evidence: List[Dict[str, Any]] = []

    def normalize_title(entry: Any) -> str:
        if not isinstance(entry, dict):
            return ""
        return _normalize_ref_title(entry.get("title") or entry.get("name") or entry.get("citation"))

    ref_titles = [normalize_title(entry) for entry in references if isinstance(entry, dict)]

    cited_numbers: set[str] = set()
    for section in sections:
        text = _normalize_text(section.get("text"))
        for number in re.findall(r"\[(\d+)\]", text):
            cited_numbers.add(number)
        for match in re.finditer(r"(?:Figure|Fig\.)\s+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE):
            figure_number = match.group(1)
            if not any(str(fig.get("figure_number") or fig.get("number") or "").strip() == figure_number for fig in figures if isinstance(fig, dict)):
                issues.append(f"Figure {figure_number} is referenced in a section but no matching figure entry was found.")
                evidence.append({"page": section.get("page"), "section": section.get("name", "Unknown Section"), "text": text[:1200]})
        for match in re.finditer(r"(?:Table)\s+(\d+(?:\.\d+)?)", text, flags=re.IGNORECASE):
            table_number = match.group(1)
            if not any(str(tab.get("table_number") or tab.get("number") or "").strip() == table_number for tab in tables if isinstance(tab, dict)):
                issues.append(f"Table {table_number} is referenced in a section but no matching table entry was found.")
                evidence.append({"page": section.get("page"), "section": section.get("name", "Unknown Section"), "text": text[:1200]})

    ref_numbers = {str(index + 1) for index in range(len(references))}
    missing_ref_numbers = sorted(cited_numbers - ref_numbers)
    if missing_ref_numbers:
        issues.append(f"Citations [{', '.join(sorted(missing_ref_numbers))}] are mentioned in the text but no matching references are present in the bibliography.")

    duplicate_titles = []
    seen = set()
    for title in ref_titles:
        if title and title in seen:
            duplicate_titles.append(title)
        else:
            seen.add(title)
    if duplicate_titles:
        issues.append("Duplicate bibliography entries were detected for the same reference title or citation.")
        observations.append(f"Duplicate reference entries: {', '.join(sorted(set(duplicate_titles))[:5])}")

    for entry in references:
        if not isinstance(entry, dict):
            continue
        title = normalize_title(entry)
        if not title:
            continue
        if all(title not in _normalize_text(section.get("text")).lower() for section in sections):
            observations.append(f"Reference '{entry.get('title') or entry.get('name') or entry.get('citation')}' appears in the bibliography but is not cited in the manuscript text.")

    if not issues and not observations:
        return {"paper_id": paper_id, "issues": ["No obvious reference consistency issues were detected in the available manuscript data."], "observations": ["No obvious reference consistency issues were detected in the available manuscript data."], "evidence": []}

    return {"paper_id": paper_id, "issues": issues or observations, "observations": observations or issues, "evidence": evidence}


reference_consistency_tool = tool("check_reference_consistency")(check_reference_consistency)
