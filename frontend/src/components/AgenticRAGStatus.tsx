import React from 'react';
import { Check, Sparkles } from 'lucide-react';

export const AgenticRAGStatus: React.FC = () => {
  const steps = [
    'Claim identified',
    'Retrieval required',
    'Literature searched',
    'Evidence analyzed',
    'Evidence sufficient',
  ];

  return (
    <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 mb-6">
      <div className="flex items-center justify-between mb-3.5 pb-2 border-b border-slate-200/80">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-4 h-4 text-blue-700" />
          <span className="text-xs font-bold uppercase tracking-wider text-slate-900 font-mono">
            Agentic RAG Verification Pipeline
          </span>
        </div>
        <span className="text-[11px] font-mono font-medium text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded">
          Complete
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
        {steps.map((step, idx) => (
          <div
            key={idx}
            className="flex items-center space-x-2 text-xs font-medium text-slate-800 bg-white p-2.5 rounded-lg border border-slate-200 shadow-2xs"
          >
            <div className="w-4 h-4 rounded-full bg-slate-900 text-white flex items-center justify-center shrink-0">
              <Check className="w-2.5 h-2.5 stroke-[2.5]" />
            </div>
            <span className="truncate">{step}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
