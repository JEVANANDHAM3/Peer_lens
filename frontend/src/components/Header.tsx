import React from 'react';
import { FileText, RotateCcw, GitCompare, FileCheck2, Lock, PanelLeftClose, PanelLeft } from 'lucide-react';

interface HeaderProps {
  currentScreen: 'upload' | 'analyzing' | 'review';
  fileName?: string;
  onNewReview: () => void;
  onOpenRevision?: () => void;
  onOpenReport?: () => void;
  isReportEnabled?: boolean;
  answeredCount?: number;
  totalIssuesCount?: number;
  onToggleSidebar?: () => void;
  isSidebarOpen?: boolean;
}

export const Header: React.FC<HeaderProps> = ({
  currentScreen,
  fileName = 'research_paper.pdf',
  onNewReview,
  onOpenRevision,
  onOpenReport,
  isReportEnabled = true,
  answeredCount = 0,
  totalIssuesCount = 0,
  onToggleSidebar,
  isSidebarOpen = true,
}) => {
  return (
    <header className="border-b border-slate-200 bg-white/95 sticky top-0 z-20 backdrop-blur-xs">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
        {/* Brand & Sidebar Toggle */}
        <div className="flex items-center space-x-3">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer"
              title={isSidebarOpen ? 'Hide Manuscripts Sidebar' : 'Show Manuscripts Sidebar'}
              aria-label="Toggle Sidebar"
            >
              {isSidebarOpen ? (
                <PanelLeftClose className="w-5 h-5" />
              ) : (
                <PanelLeft className="w-5 h-5 text-indigo-600" />
              )}
            </button>
          )}

          <div
            onClick={onNewReview}
            className="cursor-pointer flex items-baseline space-x-2.5 focus:outline-none"
            role="button"
            tabIndex={0}
          >
            <span className="text-xl font-bold tracking-tight text-slate-900 font-serif">
              PEERLENS
            </span>
            <span className="hidden sm:inline-block text-xs font-medium text-slate-500 uppercase tracking-widest pl-2 border-l border-slate-300">
              AI Research Paper Reviewer
            </span>
          </div>
        </div>

        {/* Action Controls on Review screen */}
        {currentScreen === 'review' && (
          <div className="flex items-center space-x-2 sm:space-x-3">
            <div className="hidden md:flex items-center space-x-1.5 px-2.5 py-1 bg-slate-50 border border-slate-200 rounded-md text-xs font-mono text-slate-700">
              <FileText className="w-3.5 h-3.5 text-slate-500" />
              <span className="truncate max-w-[140px]">{fileName}</span>
            </div>

            {onOpenRevision && (
              <button
                onClick={onOpenRevision}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50 hover:text-slate-900 transition-colors shadow-2xs cursor-pointer"
                title="Compare with Revised Paper"
              >
                <GitCompare className="w-3.5 h-3.5 text-slate-500" />
                <span className="hidden sm:inline">Upload Revised Paper</span>
                <span className="sm:hidden">Revision</span>
              </button>
            )}

            {onOpenReport && (
              <button
                onClick={() => {
                  if (isReportEnabled) {
                    onOpenReport();
                  }
                }}
                disabled={!isReportEnabled}
                className={`inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors shadow-2xs ${
                  isReportEnabled
                    ? 'text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-300 cursor-pointer'
                    : 'text-slate-400 bg-slate-50 border border-slate-200 cursor-not-allowed opacity-60'
                }`}
                title={
                  isReportEnabled
                    ? 'View Final Review Report'
                    : `Answer all issues to unlock final report (${answeredCount}/${totalIssuesCount} answered)`
                }
              >
                {isReportEnabled ? (
                  <FileCheck2 className="w-3.5 h-3.5 text-slate-700" />
                ) : (
                  <Lock className="w-3.5 h-3.5 text-slate-400" />
                )}
                <span className="hidden sm:inline">Final Report</span>
                <span className="sm:hidden">Report</span>
                {!isReportEnabled && totalIssuesCount > 0 && (
                  <span className="hidden lg:inline text-[10px] font-mono px-1 py-0.2 rounded bg-slate-200/70 text-slate-600">
                    {answeredCount}/{totalIssuesCount}
                  </span>
                )}
              </button>
            )}

            <button
              onClick={onNewReview}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-md transition-colors cursor-pointer"
              title="Start a new review"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>New Review</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
