import React from 'react';
import { ReviewerType } from '../types';
import { Microscope, Sparkles, BookOpen } from 'lucide-react';

interface ReviewerBadgeProps {
  reviewer: ReviewerType;
  className?: string;
  showIcon?: boolean;
}

export const ReviewerBadge: React.FC<ReviewerBadgeProps> = ({
  reviewer,
  className = '',
  showIcon = true,
}) => {
  const config: Record<
    ReviewerType,
    { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
  > = {
    'Rigor Reviewer': {
      label: 'Rigor Reviewer',
      bg: 'bg-indigo-50/70',
      text: 'text-indigo-800',
      border: 'border-indigo-200',
      icon: <Microscope className="w-3.5 h-3.5 mr-1 text-indigo-700" />,
    },
    'Clarity Reviewer': {
      label: 'Clarity Reviewer',
      bg: 'bg-emerald-50/70',
      text: 'text-emerald-800',
      border: 'border-emerald-200',
      icon: <BookOpen className="w-3.5 h-3.5 mr-1 text-emerald-700" />,
    },
    'Novelty Reviewer': {
      label: 'Novelty Reviewer',
      bg: 'bg-blue-50/70',
      text: 'text-blue-800',
      border: 'border-blue-200',
      icon: <Sparkles className="w-3.5 h-3.5 mr-1 text-blue-700" />,
    },
  };

  const normalized = (reviewer || '').toLowerCase();
  const normalizedKey: ReviewerType = normalized.includes('clarity')
    ? 'Clarity Reviewer'
    : normalized.includes('novelty')
    ? 'Novelty Reviewer'
    : 'Rigor Reviewer';

  const current = config[normalizedKey] || config['Rigor Reviewer'];

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border whitespace-nowrap ${current.bg} ${current.text} ${current.border} ${className}`}
    >
      {showIcon && current.icon}
      {current.label}
    </span>
  );
};
