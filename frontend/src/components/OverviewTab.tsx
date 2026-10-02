import React from 'react';
import { PaperInfo, Issue } from '../types';
import { IssueCard } from './IssueCard';
import { FileText, ArrowRight, Lock, CheckCircle2 } from 'lucide-react';

interface OverviewTabProps {
  paperInfo: PaperInfo;
  priorityIssues: Issue[];
  onOpenDetail: (issue: Issue) => void;
  onAccept: (issueId: string) => void;
  onDispute: (issue: Issue) => void;
  onExplainMore: (issue: Issue) => void;
  onViewEvidence: (issue: Issue) => void;
  onViewAllIssues: () => void;
  onUndoStatus?: (issueId: string) => void;
  isReportEnabled?: boolean;
  answeredCount?: number;
  totalIssuesCount?: number;
  onOpenReport?: () => void;
  onAcceptAllRemaining?: () => void;
  aiReviewSummary?: string;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  paperInfo,
  priorityIssues,
  onOpenDetail,
  onAccept,
  onDispute,
  onExplainMore,
  onViewEvidence,
  onViewAllIssues,
  onUndoStatus,
  isReportEnabled = false,
  answeredCount = 0,
  totalIssuesCount = 0,
  onOpenReport,
  onAcceptAllRemaining,
  aiReviewSummary,
}) => {
  const pendingCount = Math.max(0, totalIssuesCount - answeredCount);

  return (
    <div className="space-y-8 text-left">
      {/* Paper Information Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-2xs">
        <div className="flex items-center space-x-2 text-slate-500 mb-3">
          <FileText className="w-4 h-4 text-slate-400" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500">
            Paper Information
          </span>
        </div>

        <div className="space-y-3">
          <div>
            <span className="text-xs text-slate-500 block">Title</span>
            <h3 className="text-lg font-bold text-slate-900 font-serif mt-0.5">
              "{paperInfo.title}"
            </h3>
            <p className="text-xs text-slate-500 mt-1">{paperInfo.authors}</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-3 border-t border-slate-100 text-xs">
            <div>
              <span className="text-slate-500 block mb-0.5 font-medium">Pages</span>
              <span className="font-mono text-slate-900 font-semibold">{paperInfo.pages}</span>
            </div>

            <div>
              <span className="text-slate-500 block mb-0.5 font-medium">Sections</span>
              <p className="text-slate-700 font-sans leading-relaxed">
                {paperInfo.sections.length > 0
                  ? paperInfo.sections.join(' · ')
                  : 'Full Document Text'}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* AI Review Summary */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
          AI Review Summary
        </h3>
        <p className="text-sm text-slate-800 leading-relaxed font-sans">
          {aiReviewSummary ||
            'The paper has been evaluated across Rigor, Clarity, and Novelty dimensions. Inspect the priority issues below to address potential methodological gaps, terminology ambiguities, or prior art attributions.'}
        </p>
      </div>

      {/* Author Response & Final Report Readiness */}
      <div
        className={`border rounded-xl p-5 transition-all ${
          isReportEnabled
            ? 'bg-emerald-50/60 border-emerald-200'
            : 'bg-slate-50 border-slate-200'
        }`}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-start sm:items-center space-x-3">
            <div
              className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                isReportEnabled
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-slate-200 text-slate-700'
              }`}
            >
              {isReportEnabled ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              ) : (
                <Lock className="w-4 h-4 text-slate-600" />
              )}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-sm font-bold text-slate-900 font-serif">
                  {isReportEnabled
                    ? 'All Issues Answered — Final Report Ready'
                    : `Author Decisions: ${answeredCount}/${totalIssuesCount} Issues Answered`}
                </h4>
                <span
                  className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-semibold ${
                    isReportEnabled
                      ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                      : 'bg-amber-100 text-amber-800 border border-amber-300'
                  }`}
                >
                  {isReportEnabled ? 'Report Enabled' : `${pendingCount} Pending Decision`}
                </span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                {isReportEnabled
                  ? 'All potential issues have received an author answer. You can now generate, print, or download the official review report.'
                  : 'Before the final report can be generated, each potential issue must receive an author answer (Accept or Dispute).'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-start sm:self-auto">
            {!isReportEnabled ? (
              <>
                <button
                  type="button"
                  onClick={onViewAllIssues}
                  className="px-3 py-1.5 text-xs font-medium text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-100 border border-slate-300 rounded-lg transition-colors cursor-pointer"
                >
                  Answer Issues
                </button>
                {onAcceptAllRemaining && pendingCount > 0 && (
                  <button
                    type="button"
                    onClick={onAcceptAllRemaining}
                    className="px-3 py-1.5 text-xs font-semibold text-slate-800 bg-slate-200/80 hover:bg-slate-300 border border-slate-300 rounded-lg transition-colors cursor-pointer"
                    title="Accept all remaining open issues to quickly unlock report"
                  >
                    Accept Remaining ({pendingCount})
                  </button>
                )}
              </>
            ) : (
              onOpenReport && (
                <button
                  type="button"
                  onClick={onOpenReport}
                  className="px-3.5 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-colors shadow-2xs cursor-pointer flex items-center gap-1.5"
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Generate PDF Report</span>
                </button>
              )
            )}
          </div>
        </div>

        {/* Progress bar */}
        {!isReportEnabled && totalIssuesCount > 0 && (
          <div className="mt-3.5">
            <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
              <div
                className="bg-slate-900 h-full transition-all duration-300 rounded-full"
                style={{
                  width: `${Math.round((answeredCount / (totalIssuesCount || 1)) * 100)}%`,
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Priority Issues */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-base font-bold text-slate-900 font-serif">
              Priority Issues
            </h3>
            <p className="text-xs text-slate-500">
              High-impact findings requiring attention before peer review submission.
            </p>
          </div>

          <button
            onClick={onViewAllIssues}
            className="text-xs font-medium text-slate-700 hover:text-slate-900 flex items-center space-x-1 group"
          >
            <span>View All Issues</span>
            <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5" />
          </button>
        </div>

        <div className="space-y-3.5">
          {priorityIssues.map((issue) => (
            <IssueCard
              key={issue.id}
              issue={issue}
              onOpenDetail={onOpenDetail}
              onAccept={onAccept}
              onDispute={onDispute}
              onExplainMore={onExplainMore}
              onViewEvidence={onViewEvidence}
              onUndoStatus={onUndoStatus}
            />
          ))}
        </div>
      </div>
    </div>
  );
};
