import React from 'react';
import { Issue } from '../types';
import { SeverityBadge } from './SeverityBadge';
import { ReviewerBadge } from './ReviewerBadge';
import { Check, MessageSquare, HelpCircle, ExternalLink, Undo2, CheckCircle2, AlertTriangle, Sparkles } from 'lucide-react';

interface IssueCardProps {
  issue: Issue;
  onOpenDetail: (issue: Issue) => void;
  onAccept: (issueId: string) => void;
  onDispute: (issue: Issue) => void;
  onExplainMore: (issue: Issue) => void;
  onViewEvidence?: (issue: Issue) => void;
  onUndoStatus?: (issueId: string) => void;
}

export const IssueCard: React.FC<IssueCardProps> = ({
  issue,
  onOpenDetail,
  onAccept,
  onDispute,
  onExplainMore,
  onViewEvidence,
  onUndoStatus,
}) => {
  const isAccepted = issue.status === 'accepted';
  const isDisputed = issue.status === 'disputed';
  const isDismissed = issue.status === 'dismissed' || issue.reconsiderationOutcome === 'dismissed';
  const isReframed = issue.reconsiderationOutcome === 'reframed';
  const isResolved = issue.resolvedInRevision;

  return (
    <div
      className={`border rounded-xl p-5 transition-all bg-white relative ${
        isResolved
          ? 'border-emerald-200 bg-emerald-50/20 shadow-2xs'
          : !isResolved && issue.resolutionNote
          ? 'border-amber-200 bg-amber-50/15 shadow-2xs'
          : isAccepted
          ? 'border-emerald-200 bg-emerald-50/10'
          : isDisputed
          ? 'border-amber-200 bg-amber-50/10'
          : 'border-slate-200 hover:border-slate-300 shadow-2xs'
      }`}
    >
      {/* Top Meta Header: Severity, Reviewer, Location & Version */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center space-x-2">
          <SeverityBadge severity={issue.severity} />
          <ReviewerBadge reviewer={issue.reviewer} />
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-mono text-slate-600 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded">
            Tracked in {issue.introducedInVersion || 'v1.0'}
          </span>
          <div className="text-xs font-mono text-slate-500 bg-slate-50 border border-slate-200 px-2 py-0.5 rounded">
            Page {issue.page} · {issue.section}
          </div>
        </div>
      </div>

      {/* Title & Status indicator */}
      <div className="mb-2">
        <div className="flex items-start justify-between gap-2">
          <h4
            onClick={() => onOpenDetail(issue)}
            className={`text-base font-semibold transition-colors cursor-pointer ${
              isResolved ? 'text-slate-800 hover:text-slate-900' : 'text-slate-900 hover:text-slate-700'
            }`}
          >
            {issue.title}
          </h4>

          <div className="flex items-center space-x-1.5 shrink-0">
            {isDismissed ? (
              <span className="inline-flex items-center text-xs font-semibold text-emerald-800 bg-emerald-100 border border-emerald-300 px-2.5 py-0.5 rounded-full whitespace-nowrap">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                Dismissed (Author Argument)
              </span>
            ) : isReframed ? (
              <span className="inline-flex items-center text-xs font-semibold text-purple-800 bg-purple-100 border border-purple-300 px-2.5 py-0.5 rounded-full whitespace-nowrap">
                <Sparkles className="w-3.5 h-3.5 mr-1 text-purple-600" />
                Reframed
              </span>
            ) : isResolved ? (
              <span className="inline-flex items-center text-xs font-semibold text-emerald-800 bg-emerald-100 border border-emerald-300 px-2.5 py-0.5 rounded-full whitespace-nowrap">
                <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                Resolved in {issue.resolvedInVersion || 'v2.0'}
              </span>
            ) : !isResolved && issue.resolutionNote ? (
              <span className="inline-flex items-center text-xs font-medium text-amber-800 bg-amber-100/80 border border-amber-300 px-2.5 py-0.5 rounded-full whitespace-nowrap">
                <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-600" />
                Persists in Revision
              </span>
            ) : isAccepted ? (
              <span className="inline-flex items-center text-xs font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded whitespace-nowrap">
                <Check className="w-3 h-3 mr-1" />
                Accepted
              </span>
            ) : isDisputed ? (
              <span className="inline-flex items-center text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded whitespace-nowrap">
                <MessageSquare className="w-3 h-3 mr-1" />
                Disputed
              </span>
            ) : null}
          </div>
        </div>

        {/* Reframed perspective banner */}
        {isReframed && issue.reconsiderationNote && (
          <div className="mt-2 p-2.5 bg-purple-50/80 border border-purple-200 rounded-lg text-xs text-purple-950 flex items-start gap-2">
            <Sparkles className="w-4 h-4 text-purple-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-purple-900">Perspective Reframed: </span>
              <span>{issue.reconsiderationNote}</span>
            </div>
          </div>
        )}

        {/* Dismissed note banner */}
        {isDismissed && issue.reconsiderationNote && (
          <div className="mt-2 p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-950 flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-emerald-900">Retracted & Dismissed: </span>
              <span>{issue.reconsiderationNote}</span>
            </div>
          </div>
        )}

        {/* Resolution note banner if resolved */}
        {isResolved && issue.resolutionNote && (
          <div className="mt-2 p-2.5 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-900 flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Revision Verification ({issue.resolvedInVersion || 'v2.0'}): </span>
              <span>{issue.resolutionNote}</span>
              {issue.revisedEvidence && (
                <div className="mt-1 pt-1 border-t border-emerald-200 font-mono text-[11px] text-emerald-800">
                  <span className="font-semibold">Revised text excerpt: </span>"{issue.revisedEvidence}"
                </div>
              )}
            </div>
          </div>
        )}

        {/* Persisting note banner if checked in revision and still unresolved */}
        {!isResolved && issue.resolutionNote && (
          <div className="mt-2 p-2.5 bg-amber-50/70 border border-amber-200 rounded-lg text-xs text-amber-900 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold">Revision Verification Check: </span>
              <span>{issue.resolutionNote}</span>
              {issue.revisedEvidence && (
                <div className="mt-1 pt-1 border-t border-amber-200 font-mono text-[11px] text-amber-800">
                  <span className="font-semibold">Found in revised text: </span>"{issue.revisedEvidence}"
                </div>
              )}
            </div>
          </div>
        )}

        {/* Explanation with explicit "Potential Issue" phrasing */}
        <p className="text-sm text-slate-700 mt-1.5 leading-relaxed">
          {issue.explanation}
        </p>
      </div>

      {/* Disputed reason if present */}
      {isDisputed && issue.disputeReason && (
        <div className="mt-2.5 p-2.5 bg-amber-50/60 border border-amber-200 rounded-lg text-xs text-amber-900">
          <span className="font-semibold">Author response: </span>
          <span className="italic">"{issue.disputeReason}"</span>
        </div>
      )}

      {/* Evidence & Suggested Action Blocks */}
      <div className="mt-3.5 space-y-2.5 text-xs">
        <div className="p-3 bg-slate-50/80 rounded-lg border border-slate-200/80">
          <span className="font-semibold text-slate-800 uppercase tracking-wider block mb-1 text-[11px]">
            Evidence from Paper
          </span>
          <p className="text-slate-600 font-mono text-[11.5px] leading-relaxed">
            {typeof issue.evidence === 'string'
              ? issue.evidence
              : Array.isArray(issue.evidence)
              ? issue.evidence.map((e: any) => e?.text || e?.section || JSON.stringify(e)).join(' • ')
              : String(issue.evidence || 'No direct evidence captured.')}
          </p>
        </div>

        <div className="p-3 bg-slate-50/80 rounded-lg border border-slate-200/80 space-y-2">
          <span className="font-semibold text-slate-800 uppercase tracking-wider block text-[11px]">
            Suggested Action & Remediation
          </span>
          {(() => {
            const hasExplicitAction = Boolean(
              issue.suggestedAction || (issue as any).recommendation || (issue.actionPlan && issue.actionPlan.length > 0)
            );
            if (issue.solution_pending || !hasExplicitAction) {
              return (
                <div className="flex items-center gap-2 py-1 text-slate-500 italic text-xs">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-500 shrink-0 not-italic" />
                  <span>No solutions generated yet — click &ldquo;Give Report&rdquo; to generate actionable remediation plans.</span>
                </div>
              );
            }

            const actionText =
              issue.suggestedAction ||
              (issue as any).recommendation ||
              '';
            const hasSteps = typeof actionText === 'string' && actionText.includes('Actionable Next Steps:');
            if (!hasSteps) {
              return <p className="text-slate-700 leading-relaxed font-sans">{actionText}</p>;
            }
            const [mainRec, stepsBlock] = actionText.split(/Actionable Next Steps:/i);
            const steps = (stepsBlock || '')
              .split(/\n•\s*|\n-\s*|•\s*/)
              .map((s) => s.trim())
              .filter((s) => s.length > 0);

            return (
              <div className="space-y-2">
                <p className="text-slate-800 leading-relaxed font-sans font-medium">{mainRec.trim()}</p>
                {steps.length > 0 && (
                  <div className="space-y-1.5 pt-1 border-t border-slate-200/60">
                    <span className="text-[10.5px] font-bold uppercase tracking-wider text-slate-600 font-mono block">
                      Detailed Next Steps:
                    </span>
                    {steps.map((st, sidx) => (
                      <div
                        key={sidx}
                        className="flex items-start gap-2 p-2 rounded-md bg-white border border-slate-200 text-[11.5px] text-slate-800"
                      >
                        <span className="px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-900 font-bold font-mono text-[10px] shrink-0">
                          Step {sidx + 1}
                        </span>
                        <span className="leading-relaxed">
                          {st.replace(/^Step\s*\d+\s*(\([^)]+\))?:?\s*/i, '')}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })()}
        </div>
      </div>

      {/* Action Footer */}
      <div className="mt-4 pt-3.5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
          {/* View Evidence button for Novelty issues */}
          {issue.hasLiteratureEvidence && onViewEvidence && (
            <button
              onClick={() => onViewEvidence(issue)}
              className="inline-flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-blue-700 bg-blue-50/80 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>View Evidence</span>
            </button>
          )}

          <button
            onClick={() => onAccept(issue.id)}
            className={`inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              isAccepted
                ? 'bg-emerald-600 text-white shadow-2xs'
                : 'text-slate-700 bg-white hover:bg-slate-50 border border-slate-300'
            }`}
          >
            <Check className="w-3.5 h-3.5" />
            <span>{isAccepted ? 'Accepted' : 'Accept'}</span>
          </button>

          <button
            onClick={() => onDispute(issue)}
            className={`inline-flex items-center space-x-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
              isDisputed
                ? 'bg-amber-600 text-white shadow-2xs'
                : 'text-slate-700 bg-white hover:bg-slate-50 border border-slate-300'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>{isDisputed ? 'Edit Dispute' : 'Dispute'}</span>
          </button>

          <button
            onClick={() => onExplainMore(issue)}
            className="inline-flex items-center space-x-1 px-2.5 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors"
          >
            <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
            <span>Explain More</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {(isAccepted || isDisputed) && onUndoStatus && (
            <button
              onClick={() => onUndoStatus(issue.id)}
              className="text-xs text-slate-600 hover:text-slate-700 inline-flex items-center gap-1 font-mono transition-colors"
              title="Reset status to Open"
            >
              <Undo2 className="w-3 h-3" />
              <span className="hidden sm:inline">Reset</span>
            </button>
          )}

          <button
            onClick={() => onOpenDetail(issue)}
            className="text-xs font-medium text-slate-500 hover:text-slate-900 underline underline-offset-2 ml-auto"
          >
            Inspect
          </button>
        </div>
      </div>
    </div>
  );
};
