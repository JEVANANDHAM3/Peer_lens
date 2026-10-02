import React, { useState } from 'react';
import { Issue, Severity, ReviewerType } from '../types';
import { IssueCard } from './IssueCard';
import { Filter, Search, X, CheckCircle2, Lock, FileCheck2, UploadCloud, Layers } from 'lucide-react';

interface IssuesTabProps {
  issues: Issue[];
  selectedReviewerFilter?: ReviewerType | 'All';
  onClearReviewerFilter?: () => void;
  onOpenDetail: (issue: Issue) => void;
  onAccept: (issueId: string) => void;
  onDispute: (issue: Issue) => void;
  onExplainMore: (issue: Issue) => void;
  onViewEvidence: (issue: Issue) => void;
  onUndoStatus?: (issueId: string) => void;
  onAcceptAllRemaining?: () => void;
  onOpenReport?: () => void;
  isReportEnabled?: boolean;
  onOpenRevisionModal?: () => void;
  currentVersion?: number;
}

export const IssuesTab: React.FC<IssuesTabProps> = ({
  issues,
  selectedReviewerFilter = 'All',
  onClearReviewerFilter,
  onOpenDetail,
  onAccept,
  onDispute,
  onExplainMore,
  onViewEvidence,
  onUndoStatus,
  onAcceptAllRemaining,
  onOpenReport,
  isReportEnabled = false,
  onOpenRevisionModal,
  currentVersion = 1,
}) => {
  const [versionFilter, setVersionFilter] = useState<'all' | 'active' | 'resolved'>('all');
  const [severityFilter, setSeverityFilter] = useState<'All' | Severity>('All');
  const [statusFilter, setStatusFilter] = useState<'All' | 'open' | 'accepted' | 'disputed'>('All');
  const [searchQuery, setSearchQuery] = useState('');

  const severityOptions: ('All' | Severity)[] = ['All', 'Critical', 'High', 'Medium', 'Low'];

  const resolvedCount = issues.filter(
    (i) => Boolean(i.resolvedInRevision) || i.status === 'dismissed' || i.reconsiderationOutcome === 'dismissed'
  ).length;
  const activeCount = Math.max(0, issues.length - resolvedCount);

  const answeredCount = issues.filter(
    (i) => i.status === 'accepted' || i.status === 'disputed' || i.status === 'dismissed' || Boolean(i.resolvedInRevision)
  ).length;
  const totalIssuesCount = issues.length;
  const unansweredCount = totalIssuesCount - answeredCount;

  // Filter issues
  const filteredIssues = issues.filter((issue) => {
    const isDone = Boolean(issue.resolvedInRevision) || issue.status === 'dismissed' || issue.reconsiderationOutcome === 'dismissed';
    // Version status
    if (versionFilter === 'active' && isDone) return false;
    if (versionFilter === 'resolved' && !isDone) return false;

    // Severity
    if (severityFilter !== 'All' && issue.severity !== severityFilter) return false;
    // Reviewer
    if (selectedReviewerFilter !== 'All' && issue.reviewer !== selectedReviewerFilter) return false;
    // Status
    if (statusFilter !== 'All' && issue.status !== statusFilter) return false;
    // Search query
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchTitle = issue.title.toLowerCase().includes(q);
      const matchExpl = issue.explanation.toLowerCase().includes(q);
      const matchSec = issue.section.toLowerCase().includes(q);
      if (!matchTitle && !matchExpl && !matchSec) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6 text-left">
      {/* Header & Filter Controls */}
      <div>
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2">
          <div>
            <h2 className="text-xl font-bold tracking-tight text-slate-900 font-serif">
              Potential Issues
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Items flagged for author consideration across methodology, clarity, and novelty.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {onOpenRevisionModal && (
              <button
                onClick={onOpenRevisionModal}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-medium transition-colors shadow-2xs cursor-pointer"
                title="Upload an updated manuscript file to check whether errors have been changed and resolved"
              >
                <UploadCloud className="w-3.5 h-3.5 text-slate-300" />
                <span>Re-Review Revised Paper</span>
              </button>
            )}

            {/* Version Lifecycle Tabs */}
            <div className="flex items-center p-1 bg-slate-100 rounded-lg border border-slate-200 self-start sm:self-auto text-xs">
              <button
                onClick={() => setVersionFilter('all')}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  versionFilter === 'all'
                    ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                All Issues ({issues.length})
              </button>
              <button
                onClick={() => setVersionFilter('active')}
                className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                  versionFilter === 'active'
                    ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Active ({activeCount})
              </button>
              {resolvedCount > 0 && (
                <button
                  onClick={() => setVersionFilter('resolved')}
                  className={`px-2.5 py-1 rounded-md font-medium transition-all flex items-center gap-1 ${
                    versionFilter === 'resolved'
                      ? 'bg-emerald-50 text-emerald-800 shadow-2xs font-semibold border border-emerald-200'
                      : 'text-emerald-700 hover:text-emerald-900'
                  }`}
                >
                  <span>Resolved ({resolvedCount})</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Revision Verification Banner */}
        {issues.some((i) => i.resolutionNote || i.resolvedInRevision) && (
          <div className="mt-3 p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-start sm:items-center space-x-2.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5 sm:mt-0" />
              <div>
                <span className="font-semibold text-emerald-950 font-serif">
                  Manuscript Revision Check (v{currentVersion || 2}.0):
                </span>{' '}
                <span className="text-emerald-900">
                  {resolvedCount} of {issues.length} flagged errors verified as changed & resolved.{' '}
                  {activeCount > 0
                    ? `${activeCount} error(s) still persist in the text.`
                    : 'All identified issues have been successfully addressed!'}
                </span>
              </div>
            </div>
            {onOpenRevisionModal && (
              <button
                onClick={onOpenRevisionModal}
                className="inline-flex items-center space-x-1.5 px-2.5 py-1 bg-white hover:bg-emerald-50 text-emerald-900 border border-emerald-300 rounded-md text-xs font-medium transition-colors shrink-0 shadow-2xs cursor-pointer"
              >
                <UploadCloud className="w-3 h-3 text-emerald-700" />
                <span>Upload Next Draft</span>
              </button>
            )}
          </div>
        )}

        {/* Author Response / Report Readiness Banner */}
        <div
          className={`mt-3 p-3.5 rounded-xl border flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs ${
            isReportEnabled
              ? 'bg-emerald-50/70 border-emerald-200 text-emerald-900'
              : 'bg-amber-50/70 border-amber-200 text-amber-900'
          }`}
        >
          <div className="flex items-start sm:items-center space-x-2.5">
            {isReportEnabled ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5 sm:mt-0" />
            ) : (
              <Lock className="w-4 h-4 text-amber-600 shrink-0 mt-0.5 sm:mt-0" />
            )}
            <div>
              <div className="font-semibold flex items-center gap-1.5">
                <span>
                  {isReportEnabled
                    ? 'All Issues Answered — Final Report Unlocked!'
                    : `Author Decision Progress: ${answeredCount}/${totalIssuesCount} Issues Answered`}
                </span>
                {!isReportEnabled && (
                  <span className="font-mono text-[11px] font-normal bg-amber-100 text-amber-800 px-1.5 py-0.2 rounded border border-amber-300">
                    {unansweredCount} remaining
                  </span>
                )}
              </div>
              <p className="text-[11px] opacity-80 mt-0.5">
                {isReportEnabled
                  ? 'All issues have received author decisions (Accepted, Disputed, or Revision Fix). You can now generate the official review report.'
                  : 'Every issue must receive an author answer (Accept or Dispute) before the Final Evaluation Report is enabled.'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0 self-start sm:self-auto">
            {!isReportEnabled && onAcceptAllRemaining && (
              <button
                type="button"
                onClick={onAcceptAllRemaining}
                className="px-2.5 py-1.5 text-xs font-medium bg-white hover:bg-amber-100/60 text-amber-900 border border-amber-300 rounded-md transition-colors shadow-2xs cursor-pointer"
                title="Accept all remaining open issues to quickly unlock the final report"
              >
                Accept All Remaining ({unansweredCount})
              </button>
            )}

            {isReportEnabled && onOpenReport && (
              <button
                type="button"
                onClick={onOpenReport}
                className="px-3 py-1.5 text-xs font-semibold bg-emerald-700 hover:bg-emerald-800 text-white rounded-md transition-colors shadow-2xs cursor-pointer flex items-center gap-1.5"
              >
                <FileCheck2 className="w-3.5 h-3.5" />
                <span>Generate PDF Report</span>
              </button>
            )}
          </div>
        </div>

        {/* Filter bar */}
        <div className="pt-3 pb-2 flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-slate-200">
          {/* Severity Filters */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-semibold text-slate-500 mr-1 flex items-center gap-1">
              <Filter className="w-3.5 h-3.5" />
              Severity:
            </span>
            {severityOptions.map((sev) => {
              const count =
                sev === 'All'
                  ? issues.length
                  : issues.filter((i) => i.severity === sev).length;

              const isSelected = severityFilter === sev;

              return (
                <button
                  key={sev}
                  onClick={() => setSeverityFilter(sev)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                    isSelected
                      ? 'bg-slate-900 text-white shadow-2xs'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
                >
                  {sev}
                  <span className="ml-1.5 text-[10px] opacity-75 font-mono">({count})</span>
                </button>
              );
            })}
          </div>

          {/* Search box */}
          <div className="relative w-full md:w-56">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search issues..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-900 placeholder:text-slate-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-slate-900"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* Secondary Active Filter Pills */}
        {(selectedReviewerFilter !== 'All' || statusFilter !== 'All') && (
          <div className="flex flex-wrap items-center gap-2 pt-2.5">
            <span className="text-[11px] text-slate-500 font-medium">Active filters:</span>
            {selectedReviewerFilter !== 'All' && (
              <span className="inline-flex items-center text-xs bg-slate-100 border border-slate-300 px-2 py-0.5 rounded text-slate-800">
                <span>{selectedReviewerFilter}</span>
                {onClearReviewerFilter && (
                  <button
                    onClick={onClearReviewerFilter}
                    className="ml-1 text-slate-400 hover:text-slate-700"
                  >
                    <X className="w-3 h-3" />
                  </button>
                )}
              </span>
            )}
            {statusFilter !== 'All' && (
              <span className="inline-flex items-center text-xs bg-slate-100 border border-slate-300 px-2 py-0.5 rounded text-slate-800">
                <span>Status: {statusFilter}</span>
                <button
                  onClick={() => setStatusFilter('All')}
                  className="ml-1 text-slate-400 hover:text-slate-700"
                >
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
          </div>
        )}
      </div>

      {/* Issues List */}
      <div className="space-y-4">
        {filteredIssues.length > 0 ? (
          filteredIssues.map((issue) => (
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
          ))
        ) : (
          <div className="p-8 text-center bg-slate-50 border border-slate-200 rounded-xl space-y-2">
            <p className="text-sm font-semibold text-slate-700">No matching issues found</p>
            <p className="text-xs text-slate-500">
              Try adjusting your severity, reviewer filter, or search query.
            </p>
            <button
              onClick={() => {
                setSeverityFilter('All');
                setStatusFilter('All');
                setSearchQuery('');
                onClearReviewerFilter?.();
              }}
              className="mt-2 px-3 py-1.5 text-xs text-slate-800 bg-white border border-slate-300 rounded-md hover:bg-slate-50"
            >
              Reset Filters
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
