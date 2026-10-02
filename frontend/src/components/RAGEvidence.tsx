import React, { useState } from 'react';
import { RetrievedPaper } from '../types';
import { AgenticRAGStatus } from './AgenticRAGStatus';
import { Search, BookMarked, ExternalLink, X, FileText, ArrowRightLeft, Download, Layers } from 'lucide-react';

interface RAGEvidenceProps {
  papers: RetrievedPaper[];
  searchQuery?: string;
  claimUnderInvestigation?: string;
  claimSource?: string;
  evidenceSummary?: string;
  recommendation?: string;
  retrievalHistory?: Array<{
    iteration: number;
    query: string;
    reason: string;
    results_found: number;
    status: string;
  }>;
}

export const RAGEvidence: React.FC<RAGEvidenceProps> = ({
  papers,
  searchQuery,
  claimUnderInvestigation,
  claimSource,
  evidenceSummary,
  recommendation,
  retrievalHistory = [],
}) => {
  const [selectedPaper, setSelectedPaper] = useState<RetrievedPaper | null>(null);

  const displayQuery =
    searchQuery ||
    (retrievalHistory.length > 0 && retrievalHistory[0].query) ||
    (papers.length > 0 ? papers[0].title : 'Scientific literature search');

  const displayClaim =
    claimUnderInvestigation ||
    'Evaluation of novelty and differentiation claims against recent arXiv literature.';

  return (
    <div className="space-y-6 text-left">
      <div>
        <h2 className="text-xl font-bold tracking-tight text-slate-900 font-serif">
          arXiv Literature Grounding
        </h2>
        <p className="text-xs text-slate-500 mt-1">
          Automated literature retrieval via arXiv to assess novelty, prior art, and attribution.
        </p>
      </div>

      {/* Claim being investigated */}
      <div className="p-4 bg-white border border-slate-200 rounded-xl shadow-2xs">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block mb-1">
          Claim Under Verification
        </span>
        <blockquote className="text-sm font-serif italic text-slate-900 border-l-2 border-slate-900 pl-3.5 py-0.5">
          "{displayClaim}"
        </blockquote>
        {claimSource && (
          <div className="mt-2 text-xs text-slate-500">
            Source: <span className="font-mono text-slate-700">{claimSource}</span>
          </div>
        )}
      </div>

      {/* Agentic RAG Status */}
      <AgenticRAGStatus />

      {/* Search Query Banner */}
      <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center space-x-2 text-xs text-slate-600 min-w-0">
          <Search className="w-4 h-4 text-slate-400 shrink-0" />
          <span className="font-semibold text-slate-700 shrink-0">arXiv Search Query:</span>
          <code className="bg-white px-2 py-0.5 border border-slate-200 rounded text-slate-800 font-mono text-[11px] truncate max-w-md">
            {displayQuery}
          </code>
        </div>
        <span className="text-xs font-mono text-slate-500 shrink-0">
          {papers.length} {papers.length === 1 ? 'publication' : 'publications'} retrieved
        </span>
      </div>

      {/* Multi-round Query History if present */}
      {retrievalHistory.length > 1 && (
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-2xs space-y-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 block">
            Agentic Retrieval Iterations
          </span>
          <div className="space-y-1.5 text-xs">
            {retrievalHistory.map((item, idx) => (
              <div
                key={idx}
                className="flex flex-col sm:flex-row sm:items-center justify-between gap-1 p-2 rounded bg-slate-50 border border-slate-100"
              >
                <div className="flex items-center space-x-2">
                  <span className="font-mono font-semibold text-slate-500">
                    #{item.iteration}
                  </span>
                  <span className="font-medium text-slate-800 truncate max-w-sm">
                    "{item.query}"
                  </span>
                </div>
                <div className="flex items-center space-x-3 text-slate-500 font-mono text-[11px]">
                  <span>{item.results_found} results</span>
                  <span className="px-1.5 py-0.5 rounded bg-white border border-slate-200 text-slate-700">
                    {item.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Retrieved Papers List */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Grounding Publications ({papers.length})
        </h3>

        {papers.length === 0 ? (
          <div className="p-8 bg-white border border-dashed border-slate-200 rounded-xl text-center">
            <BookMarked className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-700">No external literature retrieved yet.</p>
            <p className="text-xs text-slate-500 mt-1">
              Run an agentic RAG review to query arXiv for related work and prior art comparison.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {papers.map((paper) => (
              <div
                key={paper.id}
                className="p-5 bg-white border border-slate-200 rounded-xl hover:border-slate-300 transition-all shadow-2xs"
              >
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-2 mb-2">
                  <div className="min-w-0">
                    <h4 className="text-base font-semibold text-slate-900 font-serif">
                      {paper.title}
                    </h4>
                    <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500 mt-0.5">
                      <span className="font-medium text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
                        {paper.type || 'arXiv Preprint'}
                      </span>
                      {paper.year && (
                        <>
                          <span>·</span>
                          <span className="font-mono">{paper.year}</span>
                        </>
                      )}
                      {paper.authors && (
                        <>
                          <span>·</span>
                          <span className="italic truncate max-w-sm">{paper.authors}</span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {paper.sourceUrl && (
                      <a
                        href={paper.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                        <span>arXiv</span>
                      </a>
                    )}
                    {paper.pdfUrl && (
                      <a
                        href={paper.pdfUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-md transition-colors"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>PDF</span>
                      </a>
                    )}
                    <button
                      onClick={() => setSelectedPaper(paper)}
                      className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-800 bg-slate-100 hover:bg-slate-200 border border-slate-200 rounded-md transition-colors cursor-pointer"
                    >
                      <ArrowRightLeft className="w-3.5 h-3.5 text-slate-500" />
                      <span>Compare</span>
                    </button>
                  </div>
                </div>

                <p className="text-xs text-slate-600 leading-relaxed mb-3 line-clamp-3">
                  {paper.snippet}
                </p>

                <div className="p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 flex items-center justify-between">
                  <div>
                    <span className="font-semibold text-slate-800">Relevance to claim: </span>
                    <span>{paper.relevance}</span>
                  </div>
                  {paper.sourceUrl && (
                    <span className="font-mono text-[10px] text-slate-400 truncate max-w-xs">
                      {paper.sourceUrl}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Evidence Summary Card */}
      <div className="p-5 bg-slate-50/80 border border-slate-200 rounded-xl">
        <div className="flex items-center space-x-2 text-slate-900 font-semibold text-sm mb-1.5">
          <BookMarked className="w-4 h-4 text-slate-700" />
          <span>Literature Grounding Assessment</span>
        </div>
        <p className="text-sm text-slate-700 leading-relaxed">
          {evidenceSummary ||
            (papers.length > 0
              ? `Retrieved ${papers.length} publications from arXiv related to the manuscript's claims. The authors should explicitly cite relevant prior work and demarcate their specific novel contributions.`
              : 'Literature grounding completed without overlapping prior art alerts.')}
        </p>
        {recommendation && (
          <p className="text-xs text-slate-600 mt-2 font-medium">
            <span className="text-slate-900 font-semibold">Recommendation: </span>
            {recommendation}
          </p>
        )}
      </div>

      {/* Evidence Comparison Modal */}
      {selectedPaper && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-2xs">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-2xl w-full p-6 text-left relative animate-in fade-in zoom-in-95 duration-150 max-h-[85vh] overflow-y-auto">
            <button
              onClick={() => setSelectedPaper(null)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1 rounded-md cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center space-x-2 mb-4">
              <ArrowRightLeft className="w-5 h-5 text-slate-700" />
              <h3 className="text-base font-bold text-slate-900">
                Manuscript vs. arXiv Literature Comparison
              </h3>
            </div>

            <div className="mb-4 pb-3 border-b border-slate-200">
              <h4 className="text-sm font-semibold text-slate-900 font-serif">
                {selectedPaper.title} {selectedPaper.year ? `(${selectedPaper.year})` : ''}
              </h4>
              <p className="text-xs text-slate-500">{selectedPaper.authors}</p>
            </div>

            <div className="space-y-4 text-xs">
              <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5">
                <span className="font-semibold text-slate-700 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-slate-500" />
                  Manuscript Novelty Claim
                </span>
                <p className="font-mono text-slate-800 leading-relaxed bg-white p-2.5 rounded border border-slate-200">
                  {selectedPaper.paperExcerpt || displayClaim}
                </p>
              </div>

              <div className="p-3.5 bg-blue-50/50 border border-blue-200 rounded-lg space-y-1.5">
                <span className="font-semibold text-blue-900 flex items-center gap-1.5">
                  <BookMarked className="w-3.5 h-3.5 text-blue-700" />
                  Retrieved arXiv Abstract / Excerpt
                </span>
                <p className="font-mono text-slate-800 leading-relaxed bg-white p-2.5 rounded border border-blue-200">
                  {selectedPaper.matchedExcerpt || selectedPaper.snippet}
                </p>
              </div>

              <div className="p-3 bg-amber-50/60 border border-amber-200 rounded-lg text-amber-900">
                <span className="font-semibold">Reviewer Recommendation: </span>
                <span>
                  {selectedPaper.relevance
                    ? `Claim match analysis: ${selectedPaper.relevance}. Explicitly state differences in problem formulation, algorithmic architecture, and experimental baseline.`
                    : 'Compare methodological details directly to clarify novelty.'}
                </span>
              </div>
            </div>

            <div className="mt-5 flex justify-between items-center">
              {selectedPaper.sourceUrl ? (
                <a
                  href={selectedPaper.sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center space-x-1.5 text-xs text-blue-700 hover:underline"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Open Paper on arXiv</span>
                </a>
              ) : <div />}

              <button
                onClick={() => setSelectedPaper(null)}
                className="px-4 py-1.5 text-xs font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
