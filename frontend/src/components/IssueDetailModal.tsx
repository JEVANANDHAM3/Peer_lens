import React, { useState, useEffect } from 'react';
import { Issue } from '../types';
import { SeverityBadge } from './SeverityBadge';
import { ReviewerBadge } from './ReviewerBadge';
import {
  X,
  Check,
  MessageSquare,
  HelpCircle,
  CheckCircle,
  ExternalLink,
  AlertTriangle,
  Sparkles,
  Loader2,
} from 'lucide-react';

interface IssueDetailModalProps {
  issue: Issue | null;
  isOpen: boolean;
  onClose: () => void;
  onAccept: (issueId: string) => void;
  onDisputeFeedback: (issueId: string, feedback: string) => void;
  onViewEvidence?: (issue: Issue) => void;
  onReconsiderIssue?: (
    issueId: string,
    authorArgument: string,
  ) => Promise<{ outcome: string; verdict_reason: string; updated_issue: Issue }>;
}

export const IssueDetailModal: React.FC<IssueDetailModalProps> = ({
  issue,
  isOpen,
  onClose,
  onAccept,
  onDisputeFeedback,
  onViewEvidence,
  onReconsiderIssue,
}) => {
  const [currentIssue, setCurrentIssue] = useState<Issue | null>(issue);
  const [showDisputeInput, setShowDisputeInput] = useState(false);
  const [feedbackText, setFeedbackText] = useState('');
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [showDeepExplain, setShowDeepExplain] = useState(false);
  const [isReconsidering, setIsReconsidering] = useState(false);
  const [reconsiderOutcome, setReconsiderOutcome] = useState<string | null>(
    issue?.reconsiderationOutcome || null,
  );
  const [reconsiderNote, setReconsiderNote] = useState<string | null>(
    issue?.reconsiderationNote || null,
  );

  useEffect(() => {
    if (issue) {
      setCurrentIssue(issue);
      setFeedbackText(issue.disputeReason || '');
      setShowDisputeInput(false);
      setFeedbackSubmitted(false);
      setShowDeepExplain(false);
      setReconsiderOutcome(issue.reconsiderationOutcome || null);
      setReconsiderNote(issue.reconsiderationNote || null);
    }
  }, [issue]);

  if (!isOpen || !issue || !currentIssue) return null;

  const handleDisputeSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedbackText.trim()) return;
    onDisputeFeedback(currentIssue.id, feedbackText);
    setFeedbackSubmitted(true);
    setTimeout(() => {
      setFeedbackSubmitted(false);
      setShowDisputeInput(false);
    }, 1500);
  };

  const handleExecuteReconsideration = async (argText: string) => {
    if (!onReconsiderIssue || !currentIssue) return;
    const trimmed = argText.trim();
    if (!trimmed) return;

    try {
      setIsReconsidering(true);
      const res = await onReconsiderIssue(currentIssue.id, trimmed);
      if (res && res.outcome) {
        const normOutcome = res.outcome === 'remove' ? 'dismissed' : res.outcome;
        setReconsiderOutcome(normOutcome);
        setReconsiderNote(res.verdict_reason);
        if (res.updated_issue) {
          setCurrentIssue((prev) => {
            if (!prev) return null;
            const up = res.updated_issue as any;
            return {
              ...prev,
              status: res.outcome === 'remove' ? 'dismissed' : res.outcome === 'reframe' ? 'open' : 'disputed',
              dismissed: res.outcome === 'remove',
              reconsidered: true,
              reconsiderationOutcome: normOutcome,
              reconsiderationNote: res.verdict_reason,
              title: String(up.title || up.issue || prev.title),
              explanation: String(up.explanation || prev.explanation),
              suggestedAction: String(up.suggestedAction || up.recommendation || prev.suggestedAction),
              actionPlan: Array.isArray(up.actionPlan) ? up.actionPlan : prev.actionPlan,
              disputeReason: trimmed,
            };
          });
        }
        if (res.outcome === 'remove') {
          setTimeout(() => {
            onClose();
          }, 2400);
        }
      }
    } catch (err) {
      console.error('Reconsideration error:', err);
    } finally {
      setIsReconsidering(false);
    }
  };

  const handleDisputeAndReconsider = (e: React.MouseEvent) => {
    e.preventDefault();
    if (!feedbackText.trim()) return;
    onDisputeFeedback(currentIssue.id, feedbackText);
    void handleExecuteReconsideration(feedbackText);
    setShowDisputeInput(false);
  };

  const isAccepted = currentIssue.status === 'accepted';
  const isDisputed = currentIssue.status === 'disputed';
  const isDismissed = currentIssue.status === 'dismissed';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-2xs">
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto text-left relative animate-in fade-in zoom-in-95 duration-150">
        {/* Sticky Header */}
        <div className="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest block">
              Potential Issue
            </span>
            <div className="flex items-center gap-2 flex-wrap mt-0.5">
              <h3 className="text-lg font-bold text-slate-900">{currentIssue.title}</h3>
              {currentIssue.reconsiderationOutcome === 'reframed' && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-purple-100 text-purple-900 border border-purple-200">
                  <Sparkles className="w-3 h-3 text-purple-600" />
                  <span>Reframed by Author Argument</span>
                </span>
              )}
              {currentIssue.status === 'dismissed' && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10.5px] font-semibold bg-emerald-100 text-emerald-900 border border-emerald-200">
                  <CheckCircle className="w-3 h-3 text-emerald-600" />
                  <span>Dismissed (Argument Verified)</span>
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 p-1.5 rounded-md hover:bg-slate-100 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5">
          {/* Metadata Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 bg-slate-50 border border-slate-200 rounded-lg text-xs">
            <div>
              <span className="text-slate-500 block mb-0.5">Reviewer</span>
              <ReviewerBadge reviewer={currentIssue.reviewer} showIcon={false} />
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">Severity</span>
              <SeverityBadge severity={currentIssue.severity} />
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">Page</span>
              <span className="font-mono font-medium text-slate-900">{currentIssue.page}</span>
            </div>
            <div>
              <span className="text-slate-500 block mb-0.5">Section</span>
              <span className="font-medium text-slate-900 truncate block">{currentIssue.section}</span>
            </div>
          </div>

          {/* Explanation */}
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center justify-between">
              <span>Explanation</span>
              {currentIssue.reconsiderationOutcome === 'reframed' && (
                <span className="text-[11px] font-mono text-purple-700 font-medium">
                  Updated from Author Perspective
                </span>
              )}
            </h4>
            <p className="text-sm text-slate-800 leading-relaxed bg-slate-50/50 p-3.5 rounded-lg border border-slate-100">
              {currentIssue.explanation}
            </p>
          </div>

          {/* Evidence from Paper */}
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5">
              Evidence from Paper
            </h4>
            <div className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 font-mono text-xs text-slate-700 leading-relaxed">
              {typeof currentIssue.evidence === 'string'
                ? currentIssue.evidence
                : Array.isArray(currentIssue.evidence)
                ? currentIssue.evidence.map((e: any) => e?.text || e?.section || JSON.stringify(e)).join(' • ')
                : String(currentIssue.evidence || 'No direct evidence captured.')}
            </div>
          </div>

          {/* Suggested Action & Detailed Next Steps */}
          <div>
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-1.5 flex items-center justify-between">
              <span>Suggested Action & Next Steps</span>
              {currentIssue.reconsiderationOutcome === 'reframed' && (
                <span className="text-[11px] font-mono text-purple-700 font-medium">
                  Tailored to Reframed Perspective
                </span>
              )}
            </h4>
            <div className="p-4 bg-emerald-50/50 rounded-lg border border-emerald-200 text-xs text-emerald-950 leading-relaxed space-y-3">
              {(() => {
                const actionPlan = currentIssue.actionPlan;
                if (actionPlan && actionPlan.length > 0) {
                  return (
                    <div className="space-y-3">
                      <p className="font-medium text-slate-900 leading-relaxed">
                        {currentIssue.suggestedAction || (currentIssue as any).recommendation || 'Clarify the issue with supporting evidence.'}
                      </p>
                      <div className="space-y-2 pt-2 border-t border-emerald-200/80">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-900 font-mono block">
                          Step-by-Step Action Plan:
                        </span>
                        {actionPlan.map((st, sidx) => (
                          <div
                            key={sidx}
                            className="flex items-start gap-2.5 p-2.5 rounded-lg bg-white border border-emerald-200 shadow-2xs text-xs text-slate-800"
                          >
                            <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-900 font-bold font-mono text-[10.5px] shrink-0">
                              Step {sidx + 1}
                            </span>
                            <span className="leading-relaxed">
                              {st.replace(/^Step\s*\d+\s*(\([^)]+\))?:?\s*/i, '')}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                }

                const actionText =
                  currentIssue.suggestedAction ||
                  (currentIssue as any).recommendation ||
                  'Clarify the issue with supporting evidence.';
                const hasSteps = typeof actionText === 'string' && actionText.includes('Actionable Next Steps:');
                if (!hasSteps) {
                  return <p className="leading-relaxed whitespace-pre-line">{actionText}</p>;
                }
                const [mainRec, stepsBlock] = actionText.split(/Actionable Next Steps:/i);
                const steps = (stepsBlock || '')
                  .split(/\n•\s*|\n-\s*|•\s*/)
                  .map((s) => s.trim())
                  .filter((s) => s.length > 0);

                return (
                  <div className="space-y-3">
                    <p className="font-medium text-slate-900 leading-relaxed">{mainRec.trim()}</p>
                    {steps.length > 0 && (
                      <div className="space-y-2 pt-2 border-t border-emerald-200/80">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-900 font-mono block">
                          Step-by-Step Action Plan:
                        </span>
                        {steps.map((st, sidx) => (
                          <div
                            key={sidx}
                            className="flex items-start gap-2.5 p-2.5 rounded-lg bg-white border border-emerald-200 shadow-2xs text-xs text-slate-800"
                          >
                            <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-900 font-bold font-mono text-[10.5px] shrink-0">
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

          {/* Revision Verification Card */}
          {issue.resolutionNote && (
            <div
              className={`p-4 rounded-lg border text-xs space-y-2 ${
                issue.resolvedInRevision
                  ? 'bg-emerald-50/80 border-emerald-200 text-emerald-950'
                  : 'bg-amber-50/80 border-amber-200 text-amber-950'
              }`}
            >
              <div className="flex items-center space-x-2">
                {issue.resolvedInRevision ? (
                  <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0" />
                ) : (
                  <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
                )}
                <span className="font-semibold uppercase tracking-wider text-[11px]">
                  {issue.resolvedInRevision
                    ? `Verified Resolved in ${issue.resolvedInVersion || 'Revision'}`
                    : 'Revision Verification Check (Unresolved)'}
                </span>
              </div>
              <p className="leading-relaxed">{issue.resolutionNote}</p>
              {issue.revisedEvidence && (
                <div className="pt-2 border-t border-slate-200/60 font-mono text-[11px]">
                  <span className="font-semibold">Excerpt from revised manuscript: </span>
                  <span>"{issue.revisedEvidence}"</span>
                </div>
              )}
            </div>
          )}

          {/* Explain More Contextual Deep Dive */}
          {showDeepExplain && issue.deepExplanation && (
            <div className="p-4 bg-indigo-50/50 rounded-lg border border-indigo-100 text-xs text-indigo-950 space-y-1.5 animate-in fade-in duration-150">
              <span className="font-semibold flex items-center gap-1.5 text-indigo-900">
                <HelpCircle className="w-3.5 h-3.5 text-indigo-600" />
                Reviewer Rationale & Context
              </span>
              <p className="leading-relaxed">{issue.deepExplanation}</p>
            </div>
          )}

          {/* Dispute Input Section */}
          {showDisputeInput && (
            <div className="pt-2 border-t border-slate-200">
              {feedbackSubmitted ? (
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-lg text-center space-y-1">
                  <CheckCircle className="w-5 h-5 text-emerald-600 mx-auto" />
                  <p className="text-xs font-semibold text-emerald-900">Feedback submitted</p>
                  <p className="text-[11px] text-emerald-700">
                    Your response will be recorded in the final review report.
                  </p>
                </div>
              ) : (
                <form onSubmit={handleDisputeSubmit} className="space-y-3">
                  <label htmlFor="modal-dispute-reason" className="block text-xs font-semibold text-slate-900">
                    Why do you disagree?
                  </label>
                  <textarea
                    id="modal-dispute-reason"
                    rows={3}
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                    placeholder="Provide justification or reference relevant subsections..."
                    className="w-full text-xs text-slate-900 border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900"
                    required
                  />
                  <div className="flex items-center justify-end space-x-2">
                    <button
                      type="button"
                      onClick={() => setShowDisputeInput(false)}
                      className="px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-300 rounded-md"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={!feedbackText.trim()}
                      className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 rounded-md shadow-2xs cursor-pointer"
                    >
                      Save Feedback
                    </button>
                    <button
                      type="button"
                      onClick={handleDisputeAndReconsider}
                      disabled={!feedbackText.trim() || isReconsidering}
                      className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 rounded-md shadow-2xs cursor-pointer"
                      title="Reconsider the issue with AI: deletes if verified correct or no problem, or updates description and changes perspective"
                    >
                      {isReconsidering ? (
                        <>
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          <span>Evaluating Feedback...</span>
                        </>
                      ) : (
                        <>
                          <Sparkles className="w-3.5 h-3.5" />
                          <span>Submit & Reconsider with AI</span>
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* Current Dispute Feedback & Reconsideration Card */}
          {(currentIssue.disputeReason || feedbackSubmitted || isDisputed) && !showDisputeInput && (
            <div className="p-4 rounded-xl border border-indigo-200 bg-gradient-to-r from-indigo-50/70 to-purple-50/70 space-y-3 text-xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5 text-indigo-950 font-semibold font-serif text-sm">
                    <Sparkles className="w-4 h-4 text-indigo-600" />
                    <span>AI Reconsideration of Issue</span>
                  </div>
                  {currentIssue.disputeReason && (
                    <p className="text-slate-700 italic">
                      <span className="font-semibold not-italic text-slate-900">Your Feedback: </span>
                      "{currentIssue.disputeReason}"
                    </p>
                  )}
                  <p className="text-[11px] text-slate-500">
                    The AI evaluates your feedback to determine whether to delete the issue or change the perspective and solution.
                  </p>
                </div>

                {onReconsiderIssue && (
                  <button
                    type="button"
                    onClick={() => handleExecuteReconsideration(currentIssue.disputeReason || feedbackText)}
                    disabled={isReconsidering || (!currentIssue.disputeReason && !feedbackText.trim())}
                    className="inline-flex items-center space-x-1.5 px-3.5 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-700 text-white disabled:bg-indigo-300 transition-colors shadow-2xs shrink-0 cursor-pointer self-start sm:self-auto"
                  >
                    {isReconsidering ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Evaluating Feedback...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles className="w-3.5 h-3.5" />
                        <span>{reconsiderNote ? 'Re-evaluate Again' : 'Reconsider Issue with AI'}</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Reconsideration Decision Result */}
              {reconsiderNote && (
                <div
                  className={`p-3.5 rounded-lg border text-xs animate-in fade-in duration-200 ${
                    reconsiderOutcome === 'dismissed'
                      ? 'bg-emerald-50 border-emerald-300 text-emerald-950'
                      : reconsiderOutcome === 'reframed'
                      ? 'bg-purple-50 border-purple-300 text-purple-950'
                      : 'bg-amber-50 border-amber-300 text-amber-950'
                  }`}
                >
                  <div className="flex items-start gap-2.5">
                    {reconsiderOutcome === 'dismissed' ? (
                      <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                    ) : reconsiderOutcome === 'reframed' ? (
                      <Sparkles className="w-4 h-4 text-purple-600 shrink-0 mt-0.5" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    )}
                    <div className="space-y-1">
                      <span className="font-bold uppercase tracking-wider text-[11px] block">
                        {reconsiderOutcome === 'dismissed'
                          ? 'Verdict: Author Argument Accepted — Issue Retracted & Dismissed'
                          : reconsiderOutcome === 'reframed'
                          ? 'Verdict: Perspective Reframed — Description & Solutions Updated'
                          : 'Verdict: Issue Upheld'}
                      </span>
                      <p className="leading-relaxed">{reconsiderNote}</p>
                      {reconsiderOutcome === 'dismissed' && (
                        <p className="text-[11px] font-semibold text-emerald-800 mt-1">
                          ✓ This issue has been retracted/dismissed and is removed from active errors.
                        </p>
                      )}
                      {reconsiderOutcome === 'reframed' && (
                        <p className="text-[11px] font-semibold text-purple-800 mt-1">
                          ✓ The explanation and actionable next steps above have been tailored to your perspective.
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="sticky bottom-0 bg-slate-50 border-t border-slate-200 px-6 py-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <button
              onClick={() => onAccept(currentIssue.id)}
              disabled={isDismissed}
              className={`inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-medium rounded-lg transition-colors ${
                isDismissed
                  ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                  : isAccepted
                  ? 'bg-emerald-600 text-white'
                  : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-300'
              }`}
            >
              <Check className="w-3.5 h-3.5" />
              <span>{isDismissed ? 'Dismissed' : isAccepted ? 'Accepted' : 'Accept'}</span>
            </button>

            <button
              onClick={() => setShowDisputeInput((prev) => !prev)}
              disabled={isDismissed}
              className={`inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-medium rounded-lg transition-colors ${
                isDismissed
                  ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                  : isDisputed
                  ? 'bg-amber-600 text-white'
                  : 'bg-white hover:bg-slate-100 text-slate-700 border border-slate-300'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>{isDisputed ? 'Edit Dispute' : 'Dispute'}</span>
            </button>

            <button
              onClick={() => setShowDeepExplain((prev) => !prev)}
              className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-medium text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-300 rounded-lg transition-colors"
            >
              <HelpCircle className="w-3.5 h-3.5 text-slate-500" />
              <span>{showDeepExplain ? 'Hide Explanation' : 'Explain More'}</span>
            </button>

            {currentIssue.hasLiteratureEvidence && onViewEvidence && (
              <button
                onClick={() => {
                  onClose();
                  onViewEvidence(currentIssue);
                }}
                className="inline-flex items-center space-x-1.5 px-3.5 py-2 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>View Evidence</span>
              </button>
            )}
          </div>

          <button
            onClick={onClose}
            className="text-xs font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
