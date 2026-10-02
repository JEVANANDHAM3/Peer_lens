import React from 'react';
import { ReviewRound } from '../types';
import { Clock, CheckCircle2, AlertTriangle, ArrowRight, UploadCloud, FileText } from 'lucide-react';

interface ReviewHistoryProps {
  rounds: ReviewRound[];
  onUploadRevised?: () => void;
}

export const ReviewHistory: React.FC<ReviewHistoryProps> = ({ rounds, onUploadRevised }) => {
  return (
    <div className="space-y-6 text-left">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold tracking-tight text-slate-900 font-serif">
            Review History
          </h2>
          <p className="text-xs text-slate-500 mt-1">
            Tracking longitudinal progress and issue resolution across revision rounds. All document versions are preserved.
          </p>
        </div>

        {onUploadRevised && (
          <button
            onClick={onUploadRevised}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-900 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors shadow-2xs self-start cursor-pointer"
          >
            <UploadCloud className="w-3.5 h-3.5 text-slate-600" />
            <span>Upload Revised Paper</span>
          </button>
        )}
      </div>

      {/* Timeline or Empty State */}
      {rounds.length === 0 ? (
        <div className="bg-slate-50 border border-dashed border-slate-300 rounded-xl p-8 text-center">
          <Clock className="w-8 h-8 text-slate-400 mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-slate-800">No review rounds recorded yet</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Review rounds track changes and resolved issues between your initial submission and subsequent revisions.
          </p>
          {onUploadRevised && (
            <button
              onClick={onUploadRevised}
              className="mt-4 inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-white bg-slate-900 rounded-lg hover:bg-slate-800 transition-colors shadow-2xs cursor-pointer"
            >
              <UploadCloud className="w-3.5 h-3.5" />
              <span>Upload Revision Draft</span>
            </button>
          )}
        </div>
      ) : (
        <div className="relative pl-6 sm:pl-8 space-y-8 before:absolute before:left-2.5 sm:before:left-3.5 before:top-3 before:bottom-3 before:w-px before:bg-slate-200">
          {rounds.map((round, idx) => {
            const isLatest = idx === rounds.length - 1;
            const versionTag = round.versionTag || `v${round.round}.0`;
            const fileName = round.fileName || (round.round === 1 ? 'research_paper.pdf' : `research_paper_v${round.round}.pdf`);

            return (
              <div key={`${round.round}-${idx}`} className="relative group">
              {/* Timeline marker */}
              <div
                className={`absolute -left-6 sm:-left-8 top-1.5 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                  isLatest
                    ? 'border-slate-900 bg-slate-900 text-white'
                    : 'border-slate-300 bg-white text-slate-500'
                }`}
              >
                <Clock className="w-3 h-3" />
              </div>

              {/* Card Container */}
              <div
                className={`p-5 rounded-xl border transition-all ${
                  isLatest
                    ? 'border-slate-300 bg-white shadow-xs'
                    : 'border-slate-200 bg-slate-50/50'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-semibold text-slate-900 font-serif">
                      Review Round {round.round}
                    </h3>
                    <span className="text-[11px] font-mono font-medium text-slate-700 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded flex items-center gap-1">
                      <FileText className="w-3 h-3 text-slate-500" />
                      <span>{versionTag} ({fileName})</span>
                    </span>
                    {isLatest && (
                      <span className="text-[10px] font-mono uppercase tracking-wider font-semibold text-slate-700 bg-slate-100 border border-slate-200 px-1.5 py-0.5 rounded">
                        Latest
                      </span>
                    )}
                  </div>
                  <span className="text-xs font-mono text-slate-500">{round.date}</span>
                </div>

                {/* Issues Identified / Remaining Badges */}
                <div className="flex flex-wrap items-center gap-2 my-2.5">
                  <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-800 border border-slate-200">
                    {round.round === 1
                      ? `${round.issuesIdentified} issues identified`
                      : `${round.issuesRemaining} issues remaining`}
                  </span>

                  {round.resolvedIssues.length > 0 && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
                      <CheckCircle2 className="w-3 h-3 mr-1" />
                      {round.resolvedIssues.length} resolved
                    </span>
                  )}
                </div>

                <p className="text-xs text-slate-600 leading-relaxed mt-2">{round.summary}</p>

                {/* Resolved items checklist */}
                {round.resolvedIssues.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-slate-200/80">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-800 block mb-1.5">
                      Resolved in this round:
                    </span>
                    <ul className="space-y-1">
                      {round.resolvedIssues.map((item, i) => (
                        <li key={i} className="text-xs text-slate-700 flex items-center gap-2">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Remaining items */}
                {round.activeIssues.length > 0 && isLatest && (
                  <div className="mt-3 pt-3 border-t border-slate-200/80">
                    <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-800 block mb-1.5">
                      Remaining focus areas:
                    </span>
                    <ul className="space-y-1">
                      {round.activeIssues.slice(0, 3).map((item, i) => (
                        <li key={i} className="text-xs text-slate-700 flex items-center gap-2">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
      )}
    </div>
  );
};
