import React, { useState, useMemo } from 'react';
import {
  FileText,
  Plus,
  RefreshCw,
  Search,
  ChevronLeft,
  ChevronRight,
  Database,
  Trash2,
  Clock,
  CheckCircle2,
  AlertCircle,
  Loader2,
  FileCheck2,
  Sparkles,
  Layers,
  ArrowUpRight,
} from 'lucide-react';
import { PaperSummary } from '../types';

interface SidebarProps {
  papers: PaperSummary[];
  activePaperId: string | null;
  isLoading: boolean;
  isOpen: boolean;
  onToggleOpen: () => void;
  onSelectPaper: (paper: PaperSummary) => void;
  onNewPaper: () => void;
  onDeletePaper: (paperId: string, e: React.MouseEvent) => void;
  onRefresh: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  papers,
  activePaperId,
  isLoading,
  isOpen,
  onToggleOpen,
  onSelectPaper,
  onNewPaper,
  onDeletePaper,
  onRefresh,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<'all' | 'ongoing' | 'completed'>('all');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Filter papers
  const filteredPapers = useMemo(() => {
    return papers.filter((p) => {
      const matchesSearch =
        p.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.filename.toLowerCase().includes(searchQuery.toLowerCase());

      if (!matchesSearch) return false;

      const isOngoing = ['running', 'reviewing', 'waiting_for_human', 're_reviewing'].includes(
        p.status
      );

      if (activeFilter === 'ongoing') {
        return isOngoing;
      }
      if (activeFilter === 'completed') {
        return p.status === 'completed';
      }
      return true;
    });
  }, [papers, searchQuery, activeFilter]);

  const ongoingCount = useMemo(
    () =>
      papers.filter((p) =>
        ['running', 'reviewing', 'waiting_for_human', 're_reviewing'].includes(p.status)
      ).length,
    [papers]
  );

  const completedCount = useMemo(
    () => papers.filter((p) => p.status === 'completed').length,
    [papers]
  );

  const formatDate = (dateStr: string) => {
    if (!dateStr) return 'Recently';
    try {
      const d = new Date(dateStr);
      if (isNaN(d.getTime())) return 'Recently';
      const now = new Date();
      const diffMs = now.getTime() - d.getTime();
      const diffMins = Math.floor(diffMs / 60000);
      if (diffMins < 1) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      const diffHours = Math.floor(diffMins / 60);
      if (diffHours < 24) return `${diffHours}h ago`;
      const diffDays = Math.floor(diffHours / 24);
      if (diffDays < 7) return `${diffDays}d ago`;
      return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    } catch {
      return 'Recently';
    }
  };

  const getStatusBadge = (status: string, totalIssues?: number, criticalCount?: number) => {
    switch (status) {
      case 'running':
      case 'reviewing':
      case 're_reviewing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 animate-pulse">
            <Loader2 className="w-2.5 h-2.5 animate-spin" />
            Analyzing
          </span>
        );
      case 'waiting_for_human':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">
            <Clock className="w-2.5 h-2.5" />
            Feedback
          </span>
        );
      case 'completed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle2 className="w-2.5 h-2.5 text-emerald-600" />
            {totalIssues !== undefined && totalIssues > 0
              ? `${totalIssues} issue${totalIssues === 1 ? '' : 's'}`
              : 'Complete'}
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertCircle className="w-2.5 h-2.5 text-rose-600" />
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <FileText className="w-2.5 h-2.5" />
            Uploaded
          </span>
        );
    }
  };

  if (!isOpen) {
    return (
      <aside className="hidden md:flex flex-col items-center py-4 px-2 w-16 bg-slate-900 border-r border-slate-800 text-white shrink-0 transition-all select-none">
        {/* Toggle open button */}
        <button
          onClick={onToggleOpen}
          className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors cursor-pointer mb-4"
          title="Open Tracked Papers Sidebar"
          aria-label="Open Sidebar"
        >
          <ChevronRight className="w-5 h-5" />
        </button>

        {/* New paper button */}
        <button
          onClick={onNewPaper}
          className="w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center shadow-sm transition-all mb-4 cursor-pointer"
          title="Analyze New Paper"
        >
          <Plus className="w-5 h-5" />
        </button>

        {/* Ongoing indicator icon */}
        {ongoingCount > 0 && (
          <div
            onClick={onToggleOpen}
            className="w-10 h-10 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-400 flex items-center justify-center mb-3 cursor-pointer animate-pulse relative"
            title={`${ongoingCount} ongoing review${ongoingCount === 1 ? '' : 's'} in progress`}
          >
            <Loader2 className="w-5 h-5 animate-spin" />
            <span className="absolute -top-1 -right-1 w-4 h-4 bg-amber-500 text-slate-950 text-[9px] font-bold rounded-full flex items-center justify-center">
              {ongoingCount}
            </span>
          </div>
        )}

        {/* Database indicator */}
        <div className="mt-auto flex flex-col items-center gap-2">
          <button
            onClick={onRefresh}
            className={`p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors cursor-pointer ${
              isLoading ? 'animate-spin text-indigo-400' : ''
            }`}
            title="Sync with SQLite Database"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <div
            className="w-2.5 h-2.5 rounded-full bg-emerald-500"
            title="SQLite Database Connected"
          />
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-80 sm:w-84 h-screen max-h-screen bg-slate-900 border-r border-slate-800 text-slate-200 flex flex-col shrink-0 transition-all select-none shadow-xl z-30">
      {/* 1. Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center space-x-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              Manuscripts
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                {papers.length}
              </span>
            </h2>
            <p className="text-[11px] text-slate-400">Database & Ongoing Reviews</p>
          </div>
        </div>

        <div className="flex items-center space-x-1">
          <button
            onClick={onRefresh}
            className={`p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors cursor-pointer ${
              isLoading ? 'animate-spin text-indigo-400' : ''
            }`}
            title="Sync with Database"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={onToggleOpen}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-md transition-colors cursor-pointer"
            title="Collapse Sidebar"
            aria-label="Collapse Sidebar"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 2. Primary Action Button */}
      <div className="p-3 border-b border-slate-800/80">
        <button
          onClick={onNewPaper}
          className="w-full py-2.5 px-3 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white rounded-xl text-xs font-semibold flex items-center justify-center space-x-2 transition-all shadow-sm cursor-pointer group"
        >
          <Plus className="w-4 h-4 transition-transform group-hover:rotate-90" />
          <span>Upload New Manuscript</span>
        </button>
      </div>

      {/* 3. Search & Filters */}
      <div className="p-3 space-y-2 border-b border-slate-800/80">
        <div className="relative">
          <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search papers or files..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 bg-slate-950/60 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
          />
        </div>

        {/* Tab Pills */}
        <div className="grid grid-cols-3 gap-1 bg-slate-950/80 p-1 rounded-lg border border-slate-800 text-[11px] font-medium">
          <button
            onClick={() => setActiveFilter('all')}
            className={`py-1 text-center rounded transition-all cursor-pointer ${
              activeFilter === 'all'
                ? 'bg-slate-800 text-white font-semibold shadow-xs'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Stored ({papers.length})
          </button>
          <button
            onClick={() => setActiveFilter('ongoing')}
            className={`py-1 text-center rounded transition-all flex items-center justify-center gap-1 cursor-pointer ${
              activeFilter === 'ongoing'
                ? 'bg-slate-800 text-amber-300 font-semibold shadow-xs'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            {ongoingCount > 0 && (
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
            )}
            <span>Ongoing ({ongoingCount})</span>
          </button>
          <button
            onClick={() => setActiveFilter('completed')}
            className={`py-1 text-center rounded transition-all cursor-pointer ${
              activeFilter === 'completed'
                ? 'bg-slate-800 text-emerald-300 font-semibold shadow-xs'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Processed ({completedCount})
          </button>
        </div>
      </div>

      {/* 4. Papers List (Scrollable) */}
      <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1.5 custom-scrollbar">
        {filteredPapers.length === 0 ? (
          <div className="py-12 px-4 text-center space-y-2">
            <div className="mx-auto w-10 h-10 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-400">
              <FileText className="w-5 h-5" />
            </div>
            <p className="text-xs font-medium text-slate-300">
              {searchQuery ? 'No matching manuscripts' : 'No stored manuscripts'}
            </p>
            <p className="text-[11px] text-slate-500 max-w-[200px] mx-auto leading-relaxed">
              {searchQuery
                ? 'Try a different search keyword.'
                : 'Stored papers and processed review results will appear here automatically.'}
            </p>
          </div>
        ) : (
          filteredPapers.map((paper) => {
            const isSelected = activePaperId === paper.paper_id;
            const isOngoing = ['running', 'reviewing', 'waiting_for_human', 're_reviewing'].includes(
              paper.status
            );

            return (
              <div
                key={paper.paper_id}
                onClick={() => onSelectPaper(paper)}
                className={`group relative p-3 rounded-xl border transition-all cursor-pointer text-left ${
                  isSelected
                    ? 'bg-indigo-950/40 border-indigo-500/60 shadow-md ring-1 ring-indigo-500/20'
                    : isOngoing
                    ? 'bg-amber-950/20 border-amber-500/30 hover:bg-slate-800/70 hover:border-slate-700'
                    : 'bg-slate-950/40 border-slate-800/90 hover:bg-slate-800/60 hover:border-slate-700'
                }`}
              >
                {/* Top Row: Title & Status Badge */}
                <div className="flex items-start justify-between gap-2 mb-1.5">
                  <h3
                    className={`text-xs font-semibold line-clamp-1 leading-snug ${
                      isSelected ? 'text-indigo-200' : 'text-slate-100 group-hover:text-white'
                    }`}
                    title={paper.title}
                  >
                    {paper.title || paper.filename}
                  </h3>
                  <div className="shrink-0">
                    {getStatusBadge(
                      paper.status,
                      paper.total_issues,
                      paper.critical_issues_count
                    )}
                  </div>
                </div>

                {/* Subtitle / Filename */}
                <div className="flex items-center space-x-1.5 text-[11px] text-slate-400 mb-2">
                  <FileText className="w-3 h-3 text-slate-500 shrink-0" />
                  <span className="truncate" title={paper.filename}>
                    {paper.filename}
                  </span>
                  {paper.file_size && (
                    <span className="text-[10px] text-slate-500 font-mono shrink-0">
                      • {paper.file_size}
                    </span>
                  )}
                </div>

                {/* Ongoing status message or issues metrics */}
                {isOngoing ? (
                  <div className="bg-amber-950/40 border border-amber-900/50 rounded-lg p-2 text-[10px] text-amber-200/90 flex items-center justify-between mb-1">
                    <span className="truncate flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                      {paper.status_message || 'Analyzing manuscript...'}
                    </span>
                    <span className="text-[9px] font-mono uppercase bg-amber-900/60 px-1 py-0.5 rounded text-amber-300">
                      Live
                    </span>
                  </div>
                ) : paper.status === 'completed' && paper.total_issues !== undefined ? (
                  <div className="flex flex-wrap items-center gap-1.5 text-[10px] text-slate-400 font-mono">
                    <span className={paper.total_issues === 0 ? "text-emerald-400 font-semibold" : "text-slate-300 font-semibold"}>
                      {paper.total_issues === 0 ? "0 issues (All fixed)" : `${paper.total_issues} open`}
                    </span>
                    {paper.resolved_issues_count ? (
                      <span className="text-emerald-400 font-semibold">
                        • {paper.resolved_issues_count} resolved
                      </span>
                    ) : null}
                    {paper.critical_issues_count ? (
                      <span className="text-rose-400 font-semibold">
                        • {paper.critical_issues_count} crit
                      </span>
                    ) : null}
                    {paper.high_issues_count ? (
                      <span className="text-amber-400 font-semibold">
                        • {paper.high_issues_count} high
                      </span>
                    ) : null}
                    {paper.version_count && paper.version_count > 1 ? (
                      <span className="ml-auto px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 text-[9px]">
                        v{paper.version_count}.0
                      </span>
                    ) : null}
                  </div>
                ) : null}

                {/* Bottom Row: Date & Actions */}
                <div className="mt-2 pt-1.5 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-500">
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3 h-3 text-slate-600" />
                    <span>{formatDate(paper.created_at || paper.updated_at)}</span>
                  </div>

                  <div className="flex items-center space-x-1">
                    {isSelected && (
                      <span className="text-[10px] text-indigo-400 font-medium flex items-center gap-0.5 mr-1">
                        Active <ArrowUpRight className="w-3 h-3" />
                      </span>
                    )}

                    {/* Delete button */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        if (confirm(`Remove "${paper.title || paper.filename}" from database?`)) {
                          onDeletePaper(paper.paper_id, e);
                        }
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-rose-400 hover:bg-slate-800/80 rounded transition-all cursor-pointer"
                      title="Delete manuscript and reviews from database"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* 5. Footer */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/70 flex items-center justify-between text-[11px] text-slate-400">
        <div className="flex items-center space-x-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-xs shadow-emerald-500/50" />
          <span className="font-mono text-[10px] text-slate-300">SQLite Database</span>
        </div>
        <span className="text-[10px] text-slate-500 font-mono">
          {papers.length} paper{papers.length === 1 ? '' : 's'} saved
        </span>
      </div>
    </aside>
  );
};
