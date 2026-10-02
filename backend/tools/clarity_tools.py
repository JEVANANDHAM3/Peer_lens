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


def _section_entries(paper: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries = paper.get("sections") or []
    sections = [section for section in entries if isinstance(section, dict)]
    pages = paper.get("pages") or []
    seen = {str(s.get("text") or "")[:100] for s in sections}
    for p in pages:
        txt = str(p.get("text") or "").strip()
        if txt and txt[:100] not in seen:
            sections.append({
                "name": f"Page {p.get('page', 1)}",
                "page": p.get("page", 1),
                "text": txt,
            })
    return sections


def _check_terminology_impl(paper_id: str, term: Optional[str] = None) -> Dict[str, Any]:
    """Audit manuscript terminology for undefined terms, abbreviations, and inconsistent names."""
    paper = get_paper(paper_id)
    if not paper:
        return {"paper_id": paper_id, "term": term, "observations": [], "evidence": [], "error": "Paper not found."}

    sections = _section_entries(paper)
    observations: List[str] = []
    evidence: List[Dict[str, Any]] = []

    definition_positions: Dict[str, int] = {}
    first_mention: Dict[str, int] = {}
    for idx, section in enumerate(sections):
        text = _normalize_text(section.get("text"))
        for expanded, acronym in re.findall(r"\b([A-Z][A-Za-z0-9&/\- ]+?)\s*\(([A-Z]{2,})\)", text):
            key = acronym.upper()
            if key not in definition_positions:
                definition_positions[key] = idx
        for acronym in re.findall(r"\b[A-Z]{2,}\b", text):
            key = acronym.upper()
            if key in {"AI", "ML", "NLP", "CV", "DL", "GPU", "CPU", "API", "RAM", "SQL", "URL"}:
                continue
            first_mention.setdefault(key, idx)

    for section in sections:
        text = _normalize_text(section.get("text"))
        section_name = _normalize_text(section.get("name"))
        if not text:
            continue

        if term:
            if term.lower() not in text.lower():
                continue
            if re.search(rf"\b{re.escape(term)}\b", text, flags=re.IGNORECASE):
                observations.append(f"The term '{term}' appears in the manuscript without a clear definition in the surrounding text.")
                evidence.append({"page": section.get("page"), "section": section_name or "Unknown Section", "text": text[:1200]})
        else:
            for acronym in sorted({a for a in re.findall(r"\b[A-Z]{2,}\b", text) if a.upper() not in {"AI", "ML", "NLP", "CV", "DL", "GPU", "CPU", "API", "RAM", "SQL", "URL"}}):
                key = acronym.upper()
                if key in definition_positions and first_mention.get(key, 10**9) <= definition_positions.get(key, 10**9):
                    observations.append(f"The abbreviation '{acronym}' is used without a nearby definition.")
                    evidence.append({"page": section.get("page"), "section": section_name or "Unknown Section", "text": text[:1200]})
                    break

    if not observations:
        for section in sections:
            text = _normalize_text(section.get("text"))
            section_name = _normalize_text(section.get("name"))
            if any(token in text.lower() for token in ["system", "method", "module", "component", "model", "dataset", "network"]):
                if re.search(r"\b(?:system|model|method)\b[\s\S]{0,200}\b(?:contains|consists of|has)\b\s+\d+\s+\b(?:modules|components|parts|stages)\b", text, flags=re.IGNORECASE):
                    observations.append("The manuscript appears to use a repeated concept name across sections without a clear canonical term.")
                    evidence.append({"page": section.get("page"), "section": section_name or "Unknown Section", "text": text[:1200]})
                    break

    if term:
        return {"paper_id": paper_id, "term": term, "observations": observations or [f"No specific terminology issue was detected for '{term}'."], "evidence": evidence}
    return {"paper_id": paper_id, "term": term, "observations": observations or ["No obvious terminology issue was detected in the available manuscript text."], "evidence": evidence}


check_terminology_tool = tool("check_terminology")(_check_terminology_impl)

def check_terminology(paper_id: str, term: Optional[str] = None) -> Dict[str, Any]:
    return _check_terminology_impl(paper_id, term)


def _check_section_consistency_impl(
    paper_id: str,
    section_a: Optional[str] = None,
    section_b: Optional[str] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare descriptions across sections for meaningful inconsistencies in terminology or structure."""
    paper = get_paper(paper_id)
    if not paper:
        return {"paper_id": paper_id, "section_a": section_a, "section_b": section_b, "query": query, "inconsistencies": [], "evidence": [], "error": "Paper not found."}

    sections = _section_entries(paper)
    valid_sections = {str(section.get("name", "")).strip(): section for section in sections if section.get("name")}
    if section_a:
        section_a_entry = valid_sections.get(section_a) or next((s for s in sections if section_a.lower() in _normalize_text(s.get("name")).lower()), None)
    else:
        section_a_entry = next((s for s in sections if "introduction" in _normalize_text(s.get("name")).lower()), None)
    if section_b:
        section_b_entry = valid_sections.get(section_b) or next((s for s in sections if section_b.lower() in _normalize_text(s.get("name")).lower()), None)
    else:
        section_b_entry = next((s for s in sections if "methodology" in _normalize_text(s.get("name")).lower()), None)

    if section_a_entry is None:
        section_a_entry = sections[0] if sections else {"name": section_a or "Unknown Section", "text": "", "page": 1}
    if section_b_entry is None:
        section_b_entry = sections[-1] if sections else {"name": section_b or "Unknown Section", "text": "", "page": 1}

    inconsistencies: List[str] = []
    evidence: List[Dict[str, Any]] = []

    for entry_a, entry_b in [(section_a_entry, section_b_entry)]:
        text_a = _normalize_text(entry_a.get("text"))
        text_b = _normalize_text(entry_b.get("text"))
        if query:
            if query.lower() not in text_a.lower() and query.lower() not in text_b.lower():
                continue

        number_words = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }

        def module_counts(text: str) -> tuple[int | None, str | None]:
            match_digits = re.search(r"(?:contains?|consists of|has)\s+(\d+)\s+(?:modules|components|parts|stages)", text, flags=re.IGNORECASE)
            if match_digits:
                return int(match_digits.group(1)), str(match_digits.group(1))

            match_words = re.search(r"(?:contains?|consists of|has)\s+([a-z]+)\s+(?:modules|components|parts|stages)", text, flags=re.IGNORECASE)
            if match_words:
                value = match_words.group(1).lower()
                if value in number_words:
                    return number_words[value], value
            return None, None

        count_a, label_a = module_counts(text_a)
        count_b, label_b = module_counts(text_b)
        if count_a is not None and count_b is not None and count_a != count_b:
            count_a_word = label_a or str(count_a)
            count_b_word = label_b or str(count_b)
            msg = (
                f"The description of the system structure differs across sections: '{entry_a.get('name', 'Section A')}' says {count_a_word} modules, while "
                f"'{entry_b.get('name', 'Section B')}' says {count_b_word} modules."
            )
            inconsistencies.append(msg)
            evidence.append({"page": entry_a.get("page"), "section": entry_a.get("name", "Unknown Section"), "text": text_a[:1000]})
            evidence.append({"page": entry_b.get("page"), "section": entry_b.get("name", "Unknown Section"), "text": text_b[:1000]})

    if not inconsistencies:
        return {"paper_id": paper_id, "section_a": section_a, "section_b": section_b, "query": query, "inconsistencies": ["No material section-to-section inconsistency was detected in the available text."], "evidence": evidence}

    return {"paper_id": paper_id, "section_a": section_a, "section_b": section_b, "query": query, "inconsistencies": inconsistencies, "evidence": evidence}


check_section_consistency_tool = tool("check_section_consistency")(_check_section_consistency_impl)

def check_section_consistency(
    paper_id: str,
    section_a: Optional[str] = None,
    section_b: Optional[str] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    return _check_section_consistency_impl(paper_id, section_a, section_b, query)
