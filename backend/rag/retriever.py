"""Production arXiv Literature Retriever for PeerLens.

Searches arXiv for real scientific publications, computes similarity scores against
author claims, and caches results in SQLite to prevent rate limits.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import arxiv
except ImportError:  # pragma: no cover
    arxiv = None

from backend.database import get_cached_arxiv_results, set_cached_arxiv_results
from .vector_store import LocalVectorStore

logger = logging.getLogger(__name__)


def _compute_query_hash(query: str, max_results: int) -> str:
    cleaned = re.sub(r"\s+", " ", query.strip().lower())
    return hashlib.sha256(f"{cleaned}::{max_results}".encode("utf-8")).hexdigest()[:16]


def _clean_arxiv_query(query: str) -> str:
    """Sanitize query string for arXiv API."""
    if not query:
        return ""
    # Strip common boilerplate phrases and non-alphanumeric punctuation
    cleaned = re.sub(r"[^\w\s-]", " ", query)
    words = [
        w.strip()
        for w in cleaned.split()
        if len(w) > 2 and w.lower() not in {
            "the", "and", "for", "with", "this", "that", "from", "paper", "propose",
            "presents", "study", "introduces", "novel", "approach", "method"
        }
    ]
    if not words:
        words = [w.strip() for w in cleaned.split() if w.strip()]
    return " ".join(words[:12])


def _calculate_similarity(query: str, text: str) -> float:
    """Calculate token overlap similarity score between query and paper text."""
    q_tokens = set(re.findall(r"[a-z0-9]+", (query or "").lower()))
    t_tokens = set(re.findall(r"[a-z0-9]+", (text or "").lower()))
    if not q_tokens or not t_tokens:
        return 0.1
    intersection = q_tokens & t_tokens
    # Jaccard + query coverage blend
    jaccard = len(intersection) / max(1, len(q_tokens | t_tokens))
    coverage = len(intersection) / max(1, len(q_tokens))
    score = round(0.4 * jaccard + 0.6 * coverage, 3)
    return min(0.98, max(0.15, score))


class LiteratureRetriever:
    """Production retriever connecting to the official arXiv repository."""

    def __init__(self, documents: Optional[List[Dict[str, Any]]] = None):
        self.custom_store = LocalVectorStore(documents) if documents is not None else None

    def search_arxiv(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search arXiv for papers matching the given query with caching."""
        sanitized = _clean_arxiv_query(query)
        if not sanitized:
            return []

        q_hash = _compute_query_hash(sanitized, max_results)

        # 1. Check SQLite cache
        try:
            cached = get_cached_arxiv_results(q_hash)
            if cached is not None:
                return cached
        except Exception as exc:
            logger.warning("Failed to read arXiv cache from SQLite: %s", exc)

        # 2. Query arXiv
        results: List[Dict[str, Any]] = []
        if arxiv is not None:
            try:
                client = arxiv.Client(page_size=max_results, delay_seconds=0.2, num_retries=0)
                search = arxiv.Search(
                    query=sanitized,
                    max_results=max_results,
                    sort_by=arxiv.SortCriterion.Relevance,
                )
                for item in client.results(search):
                    full_text = f"{item.title}\n\nAbstract: {item.summary}"
                    sim_score = _calculate_similarity(query, full_text)
                    author_names = [a.name for a in item.authors]
                    pub_year = item.published.year if item.published else None

                    results.append({
                        "title": item.title,
                        "abstract": item.summary,
                        "content": full_text,
                        "source": item.entry_id,
                        "entry_id": item.entry_id,
                        "pdf_url": item.pdf_url,
                        "authors": ", ".join(author_names[:4]) + (" et al." if len(author_names) > 4 else ""),
                        "year": pub_year,
                        "similarity_score": sim_score,
                    })
            except Exception as exc:
                logger.warning("arXiv query failed (%s): %s", sanitized, exc)

        # 3. Store in SQLite cache
        if results:
            try:
                set_cached_arxiv_results(q_hash, sanitized, results)
            except Exception as exc:
                logger.warning("Failed to cache arXiv results in SQLite: %s", exc)

        return results

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Search either custom documents (if provided) or real arXiv."""
        if self.custom_store is not None:
            return self.custom_store.search(query, k=max_results)
        return self.search_arxiv(query, max_results=max_results)

    def retrieve_evidence(
        self,
        query: str,
        top_k: int = 5,
        documents: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """Format retrieved publications into structured evidence items."""
        docs = documents or self.search(query, max_results=top_k)
        evidence_items = []
        for d in docs:
            score = d.get("similarity_score")
            if score is None:
                content = d.get("content") or d.get("abstract") or ""
                score = _calculate_similarity(query, f"{d.get('title', '')} {content}")

            evidence_items.append({
                "document": d.get("title") or d.get("source") or "arXiv Paper",
                "title": d.get("title") or d.get("source") or "arXiv Paper",
                "page": d.get("page"),
                "relevant_text": d.get("content") or d.get("abstract") or "",
                "similarity_score": float(score),
                "source": d.get("source", "arxiv"),
                "authors": d.get("authors", ""),
                "year": d.get("year"),
                "pdf_url": d.get("pdf_url"),
                "metadata": {
                    k: v
                    for k, v in d.items()
                    if k not in {"content", "abstract", "title", "source", "similarity_score"}
                },
            })
        return evidence_items
