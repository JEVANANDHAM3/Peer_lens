import React from 'react';
import { Microscope, BookOpen, Sparkles, AlertCircle } from 'lucide-react';
import { ReviewerType } from '../types';

interface ReviewSummaryProps {
  rigorCount: number;
  clarityCount: number;
  noveltyCount: number;
  overallStatus?: string;
  onSelectReviewerFilter?: (reviewer: ReviewerType) => void;
}

export const ReviewSummary: React.FC<ReviewSummaryProps> = ({
  rigorCount,
  clarityCount,
  noveltyCount,
  overallStatus = 'Needs Revision',
  onSelectReviewerFilter,
}) => {
  const cards = [
    {
      title: 'Rigor',
      count: rigorCount,
      label: `${rigorCount} Issues`,
      icon: Microscope,
      reviewer: 'Rigor Reviewer' as ReviewerType,
      color: 'text-indigo-900',
      bgColor: 'bg-indigo-50/50',
      borderColor: 'border-indigo-100',
    },
    {
      title: 'Clarity',
      count: clarityCount,
      label: `${clarityCount} Issues`,
      icon: BookOpen,
      reviewer: 'Clarity Reviewer' as ReviewerType,
      color: 'text-emerald-900',
      bgColor: 'bg-emerald-50/50',
      borderColor: 'border-emerald-100',
    },
    {
      title: 'Novelty',
      count: noveltyCount,
      label: `${noveltyCount} Issues`,
      icon: Sparkles,
      reviewer: 'Novelty Reviewer' as ReviewerType,
      color: 'text-blue-900',
      bgColor: 'bg-blue-50/50',
      borderColor: 'border-blue-100',
    },
    {
      title: 'Overall',
      count: null,
      label: overallStatus,
      icon: AlertCircle,
      reviewer: null,
      color: 'text-amber-900',
      bgColor: 'bg-amber-50/40',
      borderColor: 'border-amber-200/70',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 my-6">
      {cards.map((card, idx) => {
        const Icon = card.icon;
        const isClickable = !!card.reviewer && !!onSelectReviewerFilter;

        return (
          <div
            key={idx}
            onClick={() => card.reviewer && onSelectReviewerFilter?.(card.reviewer)}
            className={`p-4 rounded-xl border transition-all text-left ${
              card.borderColor
            } bg-white shadow-2xs ${
              isClickable ? 'cursor-pointer hover:border-slate-400 hover:shadow-xs' : ''
            }`}
          >
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                {card.title}
              </span>
              <Icon className="w-4 h-4 text-slate-400" />
            </div>

            <div className="mt-1">
              <span
                className={`text-lg sm:text-xl font-bold tracking-tight ${
                  card.count !== null ? 'text-slate-900' : 'text-amber-700'
                }`}
              >
                {card.label}
              </span>
            </div>

            {card.reviewer && (
              <p className="text-[11px] text-slate-600 mt-1 flex items-center gap-1">
                <span>View {card.title.toLowerCase()} breakdown</span>
                <span className="text-slate-400">→</span>
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
};
