import React from 'react';
import { Severity } from '../types';

interface SeverityBadgeProps {
  severity: Severity;
  className?: string;
}

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({ severity, className = '' }) => {
  const styles: Record<Severity, string> = {
    Critical: 'bg-rose-50 text-rose-700 border-rose-200',
    High: 'bg-amber-50 text-amber-700 border-amber-200',
    Medium: 'bg-slate-100 text-slate-700 border-slate-300',
    Low: 'bg-slate-50 text-slate-600 border-slate-200',
  };

  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase tracking-wider border whitespace-nowrap ${styles[severity]} ${className}`}
    >
      {severity}
    </span>
  );
};
