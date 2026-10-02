from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from backend.rag.retriever import LiteratureRetriever


class QueryInput(BaseModel):
    query: str = Field(...)


class CompareInput(BaseModel):
    claim: str
    retrieved_documents: List[Dict[str, Any]] = Field(default_factory=list)


class SearchResultInput(BaseModel):
    title: str
    abstract: Optional[str] = None


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def search_literature(query: str, max_results: int = 5, retriever: Optional[LiteratureRetriever] = None) -> List[Dict[str, Any]]:
    r = retriever or LiteratureRetriever()
    return r.search(query, max_results=max_results)


def retrieve_evidence(query: str, top_k: int = 5, retriever: Optional[LiteratureRetriever] = None) -> Dict[str, Any]:
    r = retriever or LiteratureRetriever()
    docs = r.search(query, max_results=top_k)
    return {"documents": r.retrieve_evidence(query, top_k=top_k, documents=docs)}


def compare_evidence(claim: str, retrieved_documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not retrieved_documents:
        return {
            "similarity": "unknown",
            "overlap": [],
            "differences": ["No retrieved documents were available for comparison."],
            "potential_overlap": "No clear overlap could be established from the retrieved evidence.",
            "confidence": 0.0,
        }

    overlap: List[str] = []
    differences: List[str] = []
    claim_terms = _token_set(claim)
    claim_key_terms = [term for term in sorted(claim_terms) if len(term) > 3]

    for doc in retrieved_documents:
        doc_text = " ".join(filter(None, [doc.get("title"), doc.get("abstract"), doc.get("content"), doc.get("relevant_text")]))
        doc_terms = _token_set(doc_text)
        shared = sorted(claim_key_terms[:5])
        if shared and any(term in doc_terms for term in shared):
            overlap.append(f"The retrieved work shares terms related to: {', '.join(shared[:3])}.")
        title = doc.get("title") or doc.get("document") or "Retrieved work"
        if any(keyword in doc_text.lower() for keyword in ["llm", "agent", "review", "peer", "paper"]):
            differences.append(f"{title} covers related review or agentic workflow concepts but may differ in scope or contribution.")

    similarity = "high" if len(overlap) > 0 else "low"
    return {
        "similarity": similarity,
        "overlap": overlap or ["No strong lexical overlap was detected in the retrieved literature."],
        "differences": differences or ["The paper's claimed contribution must be compared to the retrieved work on scope, mechanism, and evaluation details."],
        "potential_overlap": "Potential literature overlap should be assessed against the paper's explicit claim and the retrieved work's method or scope." if overlap else "No clear overlap was established from the current evidence.",
        "confidence": min(0.95, max(0.2, round(len(overlap) * 0.3 + 0.2, 2))),
    }


def expand_search_query(original_query: str, reason: str) -> Dict[str, Any]:
    base = (original_query or "").strip()
    if not base:
        return {"original_query": original_query, "reason": reason, "refined_queries": []}
    cleaned = re.sub(r"\s+", " ", base)
    refined = [
        cleaned,
        f"{cleaned} related work",
        f"{cleaned} novelty contribution comparison",
        f"{cleaned} literature review multi agent",
    ]
    return {"original_query": original_query, "reason": reason, "refined_queries": list(dict.fromkeys(refined))[:5]}


def find_related_work(title: str, abstract: Optional[str] = None) -> Dict[str, Any]:
    if not title and not abstract:
        return {"title": title, "abstract": abstract, "related_work": []}
    query = title or abstract or ""
    docs = search_literature(query, max_results=5)
    return {"title": title, "abstract": abstract, "related_work": docs}


def create_rag_tools(paper_text: Any, sections, retriever: Optional[LiteratureRetriever] = None):
    r = retriever or LiteratureRetriever()

    @tool("read_paper")
    def read_paper(query: str = "") -> Dict[str, Any]:
        """Read relevant uploaded paper content."""
        return {"text": str(paper_text), "sections": sections, "query": query}

    @tool("search_literature")
    def search_literature_tool(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        return search_literature(query, max_results=max_results, retriever=r)

    @tool("retrieve_evidence")
    def retrieve_evidence_tool(query: str, top_k: int = 5) -> Dict[str, Any]:
        return retrieve_evidence(query, top_k=top_k, retriever=r)

    @tool("compare_evidence")
    def compare_evidence_tool(claim: str, retrieved_documents: List[Dict[str, Any]] = []) -> Dict[str, Any]:
        return compare_evidence(claim, retrieved_documents)

    @tool("expand_search_query")
    def expand_search_query_tool(original_query: str, reason: str) -> Dict[str, Any]:
        return expand_search_query(original_query, reason)

    @tool("find_related_work")
    def find_related_work_tool(title: str, abstract: Optional[str] = None) -> Dict[str, Any]:
        return find_related_work(title, abstract)

    return [
        read_paper,
        search_literature_tool,
        retrieve_evidence_tool,
        compare_evidence_tool,
        expand_search_query_tool,
        find_related_work_tool,
    ]
