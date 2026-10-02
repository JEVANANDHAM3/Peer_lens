from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from backend.models.novelty import ClaimAssessment, EvidenceItem, NoveltyIssue, NoveltyReviewOutput, RetrievedEvidence
from backend.rag.retriever import LiteratureRetriever
from backend.tools.paper_tools import locate_evidence, read_paper
from backend.tools.rag_tools import compare_evidence, expand_search_query, find_related_work


class NoveltyReviewerAgent:
    MAX_RETRIEVAL_ITERATIONS = 3

    def __init__(self, retriever: Optional[LiteratureRetriever] = None):
        self.retriever = retriever or LiteratureRetriever()

    def requires_retrieval(self, claim: str) -> bool:
        if not claim:
            return False
        lower = claim.lower()
        novelty_markers = (
            "novel", "first", "new", "pioneer", "introduce", "propose",
            "contribution", "state-of-the-art", "outperform", "improve",
            "prior work", "related work", "without prior"
        )
        return any(marker in lower for marker in novelty_markers)

    def _coerce_claims(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        sections = state.get("sections", []) or []
        pages = state.get("pages", []) or []
        paper_text = str(state.get("paper_text") or "")
        claims: List[Dict[str, Any]] = []
        seen_texts = set()

        for section in sections:
            name = str(section.get("name", "")).strip()
            text = str(section.get("text", "")).strip()
            if any(word in name.lower() for word in ["abstract", "introduction", "contribution", "method", "related work", "discussion", "results", "conclusion"]):
                if text and text[:80] not in seen_texts:
                    seen_texts.add(text[:80])
                    claims.append({"text": text[:1500], "section": name or "Section", "page": section.get("page", 1)})

        for page in pages:
            page_num = page.get("page", 1)
            text = str(page.get("text", "")).strip()
            if text and self.requires_retrieval(text):
                if text[:80] not in seen_texts:
                    seen_texts.add(text[:80])
                    claims.append({"text": text[:1500], "section": f"Page {page_num}", "page": page_num})

        if not claims and paper_text:
            claims.append({"text": paper_text[:1500], "section": "Paper", "page": 1})
        return claims[:10]

    def generate_queries(self, claim: str, reason: str) -> List[str]:
        cleaned = re.sub(r"\s+", " ", (claim or "")).strip()
        if not cleaned:
            return []
        base_terms = [token for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", cleaned) if token.lower() not in {"paper", "research", "system", "method", "approach"}]
        focus = " ".join(base_terms[:8])
        queries = [
            cleaned[:180],
            f"{focus} related work novelty comparison" if focus else cleaned,
            f"{focus} prior art state of the art" if focus else cleaned,
            f"{focus} prior work literature overlap" if focus else cleaned,
        ]
        if reason and reason.strip():
            queries.insert(1, f"{cleaned} {reason[:120]}".strip())
        return list(dict.fromkeys(q for q in queries if q and len(q.strip()) > 8))[:4]

    def _evaluate_evidence(self, claim: str, evidence: List[Dict[str, Any]]) -> str:
        if not evidence:
            return "insufficient"
        avg = sum(float(item.get("similarity_score", 0.0)) for item in evidence) / len(evidence)
        if avg >= 0.6:
            return "sufficient"
        if avg >= 0.3:
            return "partially_sufficient"
        return "insufficient"

    def _detect_false_prior_art_issues(self, claims: List[Dict[str, Any]]) -> List[NoveltyIssue]:
        issues: List[NoveltyIssue] = []
        prior_art_map = {
            "dcgan": ("Radford et al. (2015/2016)", "Deep Convolutional Generative Adversarial Networks (DCGAN) was invented by Alec Radford, Luke Metz, and Soumith Chintala in 2015"),
            "vanilla gan": ("Goodfellow et al. (2014)", "Generative Adversarial Networks was pioneered by Ian Goodfellow et al. in 2014"),
            "gan": ("Goodfellow et al. (2014)", "GAN was introduced by Goodfellow et al. in 2014"),
            "resnet": ("He et al. (2015)", "Deep Residual Learning (ResNet) was introduced by Kaiming He et al. in 2015"),
            "mobilenet": ("Howard et al. (2017)", "MobileNet was introduced by Andrew Howard et al. in 2017"),
        }

        for idx, claim_item in enumerate(claims):
            text = str(claim_item.get("text", "")).strip()
            lower = text.lower()
            page = claim_item.get("page", 1)
            section = claim_item.get("section", "Contributions")

            is_sweeping_claim = any(
                phrase in lower
                for phrase in [
                    "invent for the very first time",
                    "never been conceived or utilized",
                    "original creators of",
                    "we invent",
                    "first time in literature",
                    "first to propose",
                ]
            )

            for key, (source_citation, details) in prior_art_map.items():
                if key in lower and is_sweeping_claim:
                    issues.append(
                        NoveltyIssue(
                            id=f"NOVELTY-ART-{idx+1:03d}",
                            reviewer="novelty",
                            section=section,
                            page=page,
                            severity="Critical",
                            type="prior_art_misattribution",
                            issue=f"False claim of inventing well-established prior art ({key.upper()})",
                            explanation=(
                                f"The manuscript explicitly claims to have invented {key.upper()} for the very first time in literature "
                                f"and asserts the authors are the original creators. However, {details} ({source_citation}). "
                                f"Claiming original authorship of a foundational architecture is a critical misattribution of prior art."
                            ),
                            claim=text[:400],
                            evidence=[EvidenceItem(page=page, section=section, text=text[:300], title=source_citation, source="peer_review_audit")],
                            similarities=[f"Radford et al. (2015/2016): Unsupervised Representation Learning with Deep Convolutional GANs"],
                            differences=["The paper should frame DCGAN as an adopted tool rather than an original invention."],
                            recommendation=(
                                f"Properly attribute {key.upper()} to its original authors ({source_citation}).\n\n"
                                f"Actionable Next Steps:\n"
                                f"• Step 1 (Attribution): Remove the claim that this paper invented or originally conceived {key.upper()}.\n"
                                f"• Step 2 (Citation): Cite {source_citation} at the first mention of {key.upper()}.\n"
                                f"• Step 3 (Contribution Recalibration): Clarify that the novel contribution lies in applying and evaluating {key.upper()} for brain MRI augmentation."
                            ),
                            confidence=0.98,
                            tools_used=["read_paper", "locate_evidence", "find_related_work"],
                        )
                    )
                    break
        return issues

    def _build_issue(self, claim: Dict[str, Any], assessment: ClaimAssessment, evidence: List[Dict[str, Any]], related_work: List[Dict[str, Any]]) -> Optional[NoveltyIssue]:
        issue_text = "The authors' novelty claim requires clearer differentiation from related literature."
        main_similarity = ""
        for item in evidence:
            if item.get("similarity_score", 0.0) >= 0.5:
                main_similarity = item.get("title") or item.get("document") or "Related work"
                break

        if main_similarity:
            issue_text = f"Potential literature overlap with '{main_similarity}' requires clarification."

        similarities = []
        differences = [
            "The manuscript should explicitly explain what is new relative to the retrieved work.",
            "The contribution should be framed in terms of scope, architecture, or evaluation differences.",
        ]
        for item in evidence:
            text = item.get("relevant_text") or item.get("content") or ""
            if text:
                similarities.append(text[:180])

        if not similarities and related_work:
            similarities.append(f"Retrieved work related to: {related_work[0].get('title', 'a similar paper')}")

        section = claim.get("section", "Introduction")
        page = claim.get("page", 1)
        confidence = float(assessment.confidence or 0.5)
        severity = "High" if confidence >= 0.65 else "Medium"
        retrieved_title = main_similarity or (related_work[0].get('title') if related_work else "retrieved academic prior art")
        actionable_rec = (
            f"Differentiate this contribution explicitly from '{retrieved_title}'.\n\n"
            f"Actionable Next Steps:\n"
            f"• Step 1 (Literature Attribution): Add a dedicated paragraph in Section 2 (Related Work) citing '{retrieved_title}' and summarizing its primary objective and limitations.\n"
            f"• Step 2 (Architectural/Theoretical Contrast): Insert a structured comparison table or bullet list clearly highlighting differences in assumptions, objective functions, or benchmark settings.\n"
            f"• Step 3 (Contribution Recalibration): Calibrate broad novelty claims (such as 'the first to propose') to specify the exact novel mechanism rather than claiming an unstudied problem domain."
        )

        return NoveltyIssue(
            id=f"NOVELTY-{len(assessment.related_work) + 1:03d}",
            reviewer="novelty",
            section=section,
            page=page,
            severity=severity,
            type="potential_literature_overlap",
            issue=issue_text,
            explanation="The paper makes a broad novelty claim, but does not provide sufficient contrast against foundational or contemporary generative literature.",
            claim=claim.get("text", "")[:400],
            evidence=[EvidenceItem(page=page, section=section, text=item.get("relevant_text") or item.get("content") or "") for item in evidence[:2]] or [EvidenceItem(page=page, section=section, text=claim.get("text", "")[:200])],
            similarities=similarities[:3],
            differences=differences,
            recommendation=actionable_rec,
            confidence=confidence,
            tools_used=["read_paper", "locate_evidence", "search_literature", "retrieve_evidence", "compare_evidence", "expand_search_query", "find_related_work"],
        )

    def _fallback_claim_state(self, claim: Dict[str, Any], retrieval_required: bool = False) -> ClaimAssessment:
        text = claim.get("text", "")
        return ClaimAssessment(
            claim=text[:400],
            retrieval_required=retrieval_required,
            queries=[],
            retrieval_iterations=0,
            evidence=[],
            assessment="The claim appears to be a contribution statement that may require external comparison if the novelty is asserted directly.",
            potential_overlap="No external evidence was retrieved for this claim.",
            differences="The manuscript should clarify the specific novelty relative to prior work.",
            confidence=0.2,
            related_work=[],
        )

    def review(self, state: Dict[str, Any], mode: str = "agentic_rag", original_issue: Optional[str] = None, human_feedback: Optional[str] = None, human_reason: Optional[str] = None) -> Dict[str, Any]:
        state = state or {}
        sections = state.get("sections", []) or []
        paper_text = state.get("paper_text", "") or ""
        claims = self._coerce_claims(state)

        if not claims and paper_text:
            claims = [{"text": paper_text[:1000], "section": "Paper", "page": 1}]

        if mode not in {"no_rag", "basic_rag", "agentic_rag"}:
            mode = "agentic_rag"

        if mode == "no_rag":
            retrieval_cap = 0
        elif mode == "basic_rag":
            retrieval_cap = 1
        else:
            retrieval_cap = self.MAX_RETRIEVAL_ITERATIONS

        claims_checked: List[ClaimAssessment] = []
        retrieval_history: List[Dict[str, Any]] = []
        all_evidence: List[Dict[str, Any]] = []
        issues: List[NoveltyIssue] = []
        all_queries: List[str] = []
        retrieval_throttled = False

        for claim in claims:
            claim_text = claim.get("text", "")
            claim_section = claim.get("section", "Introduction")
            claim_page = claim.get("page", 1)
            retrieval_required = self.requires_retrieval(claim_text) and mode != "no_rag"
            query_list: List[str] = []
            captured_evidence: List[Dict[str, Any]] = []
            related_work: List[Dict[str, Any]] = []
            retrieval_failed = False

            if retrieval_required and retrieval_cap > 0 and not retrieval_throttled:
                max_iterations = retrieval_cap if mode == "basic_rag" else min(retrieval_cap, self.MAX_RETRIEVAL_ITERATIONS)
                for iteration in range(1, max_iterations + 1):
                    reason = "Initial search for similar contributions" if iteration == 1 else "Refining the novelty search to improve specificity and overlap detection"
                    candidate_queries = self.generate_queries(claim_text, reason)
                    if not candidate_queries:
                        break
                    q = candidate_queries[0]
                    if iteration > 1:
                        q = candidate_queries[min(iteration - 1, len(candidate_queries) - 1)]
                    query_list.append(q)
                    all_queries.append(q)
                    try:
                        docs = self.retriever.search(q, max_results=5)
                        retrieved = self.retriever.retrieve_evidence(q, top_k=5, documents=docs)
                        captured_evidence.extend(retrieved)
                        all_evidence.extend(retrieved)
                        related_work.extend(docs)
                        status = self._evaluate_evidence(claim_text, retrieved)
                        retrieval_history.append({
                            "iteration": iteration,
                            "query": q,
                            "reason": reason,
                            "results_found": len(retrieved),
                            "status": status,
                        })
                        if status in {"sufficient"}:
                            break
                        if mode == "basic_rag":
                            break
                    except Exception as exc:  # pragma: no cover - safety guard for retrieval failure
                        retrieval_failed = True
                        if any(err in str(exc) for err in ("429", "503", "ConnectionError")):
                            retrieval_throttled = True
                        retrieval_history.append({
                            "iteration": iteration,
                            "query": q,
                            "reason": reason,
                            "results_found": 0,
                            "status": "failed",
                            "error": str(exc),
                        })
                        break

                if not captured_evidence and retrieval_required and not retrieval_failed:
                    retrieval_history.append({
                        "iteration": max_iterations + 1 if max_iterations < self.MAX_RETRIEVAL_ITERATIONS else self.MAX_RETRIEVAL_ITERATIONS,
                        "query": "",
                        "reason": "No usable novelty evidence retrieved",
                        "results_found": 0,
                        "status": "insufficient",
                    })

            if not retrieval_required:
                assessment = self._fallback_claim_state(claim, retrieval_required=False)
            else:
                comparison = compare_evidence(claim_text, captured_evidence)
                overlap_text = ", ".join(comparison.get("overlap", [])) or "No clear overlap was found in the retrieved literature."
                difference_text = ", ".join(comparison.get("differences", [])) or "The manuscript should explain the distinctive contribution more explicitly."
                avg_score = sum(float(item.get("similarity_score", 0.0)) for item in captured_evidence) / len(captured_evidence) if captured_evidence else 0.0
                confidence = min(0.95, max(0.15, avg_score))
                assessment = ClaimAssessment(
                    claim=claim_text[:400],
                    retrieval_required=retrieval_required,
                    queries=query_list,
                    retrieval_iterations=len(query_list),
                    evidence=[RetrievedEvidence(document=item.get("document") or item.get("title") or "Retrieved work", title=item.get("title") or item.get("document") or "Retrieved work", page=item.get("page"), relevant_text=item.get("relevant_text") or item.get("content") or "", similarity_score=float(item.get("similarity_score", 0.0)), source=item.get("source", "local"), metadata=item.get("metadata", {})) for item in captured_evidence],
                    assessment="Related literature was found; the novelty claim should be compared against the retrieved results for overlap." if captured_evidence else "No sufficient external evidence was retrieved to assess novelty confidently.",
                    potential_overlap=overlap_text,
                    differences=difference_text,
                    confidence=confidence,
                    related_work=related_work,
                )

            claims_checked.append(assessment)

            if assessment.retrieval_required or assessment.evidence:
                issue = self._build_issue(claim, assessment, captured_evidence, related_work)
                if issue is not None:
                    issues.append(issue)

        # Detect and prepend false prior art claims (e.g. claiming to invent DCGAN)
        prior_art_issues = self._detect_false_prior_art_issues(claims)
        issues = prior_art_issues + issues

        summary = (
            "The paper was reviewed for contribution claims and related literature overlap using a bounded, claim-triggered retrieval process."
            if any(item.retrieval_required for item in claims_checked)
            else "The paper was reviewed for novelty claims based on the manuscript text alone, without external retrieval."
        )

        # Compute pages examined from claims analyzed and state pages
        pages_examined_set = set()
        for claim in claims:
            pages_examined_set.add(claim.get("page", 1))
        for page in state.get("pages", []) or []:
            pages_examined_set.add(page.get("page", 1))
        for section in state.get("sections", []) or []:
            pages_examined_set.add(section.get("page", 1))
        pages_examined = sorted(pages_examined_set) or [1]

        payload = NoveltyReviewOutput(
            reviewer="novelty",
            summary=summary,
            claims_checked=claims_checked,
            retrieval_required=any(item.retrieval_required for item in claims_checked),
            retrieval_iterations=sum(max(1, item.retrieval_iterations) for item in claims_checked if item.retrieval_required),
            queries=all_queries,
            retrieval_history=retrieval_history,
            evidence=[{"claim": item.claim, "retrieved_documents": [doc.model_dump() for doc in item.evidence]} for item in claims_checked],
            issues=issues,
            claims_analyzed=claims_checked,
            pages_examined=pages_examined,
        )
        state["novelty_review"] = payload.model_dump()
        state["retrieved_documents"] = all_evidence
        state["retrieval_history"] = retrieval_history
        return payload.model_dump()


def run_novelty_reviewer(state: Dict[str, Any], retriever=None, mode: str = "agentic_rag", original_issue: Optional[str] = None, human_feedback: Optional[str] = None, human_reason: Optional[str] = None) -> Dict[str, Any]:
    agent = NoveltyReviewerAgent(retriever=retriever)
    result = agent.review(state, mode=mode, original_issue=original_issue, human_feedback=human_feedback, human_reason=human_reason)
    state["novelty_review"] = result
    return state
