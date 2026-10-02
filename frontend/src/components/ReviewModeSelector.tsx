import React from 'react';
import { ReviewMode } from '../types';
import { Cpu, Database, Sparkles, Check, HelpCircle } from 'lucide-react';

interface ReviewModeSelectorProps {
  selectedMode: ReviewMode;
  onSelectMode: (mode: ReviewMode) => void;
  disabled?: boolean;
  compact?: boolean;
}

interface ModeOption {
  id: ReviewMode;
  title: string;
  badge: string;
  badgeColor: string;
  icon: React.ComponentType<{ className?: string }>;
  description: string;
  meta: string;
  recommended?: boolean;
}

const MODES: ModeOption[] = [
  {
    id: 'no_rag',
    title: 'No-RAG Baseline',
    badge: 'Pure LLM',
    badgeColor: 'bg-slate-100 text-slate-700 border-slate-300',
    icon: Cpu,
    description: 'Evaluates manuscript using unassisted LLM reasoning without external retrieval. Serves as baseline for hallucination evaluation.',
    meta: 'Fastest · 0 external queries',
  },
  {
    id: 'basic_rag',
    title: 'Basic RAG',
    badge: 'Single-Pass Vector',
    badgeColor: 'bg-blue-50 text-blue-700 border-blue-200',
    icon: Database,
    description: 'Executes standard vector similarity search over the paper text. Static single-pass retrieval without dynamic query planning.',
    meta: 'Standard retrieval · 1 search pass',
  },
  {
    id: 'agentic_rag',
    title: 'Agentic RAG',
    badge: 'Recommended',
    badgeColor: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    icon: Sparkles,
    description: 'Autonomous novelty claim extraction, dynamic scientific query formulation, live arXiv academic search, and evidence reranking.',
    meta: 'Deepest verification · Live arXiv integration',
    recommended: true,
  },
];

export const ReviewModeSelector: React.FC<ReviewModeSelectorProps> = ({
  selectedMode,
  onSelectMode,
  disabled = false,
  compact = false,
}) => {
  if (compact) {
    return (
      <div className="inline-flex items-center p-1 bg-slate-100/90 border border-slate-200 rounded-lg text-xs font-medium">
        {MODES.map((mode) => {
          const isSelected = selectedMode === mode.id;
          const Icon = mode.icon;
          return (
            <button
              key={mode.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelectMode(mode.id)}
              className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md transition-all cursor-pointer ${
                isSelected
                  ? 'bg-white text-slate-900 shadow-2xs font-semibold'
                  : 'text-slate-600 hover:text-slate-900 disabled:opacity-50'
              }`}
              title={mode.description}
            >
              <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-indigo-600' : 'text-slate-400'}`} />
              <span>{mode.title}</span>
              {mode.recommended && (
                <span className="text-[9px] uppercase px-1 py-0.2 bg-indigo-100 text-indigo-800 rounded font-mono font-bold">
                  Rec
                </span>
              )}
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="space-y-3 text-left w-full">
      <div className="flex items-center justify-between">
        <label className="text-xs font-bold uppercase tracking-wider text-slate-700 font-mono flex items-center gap-1.5">
          <span>Select Evaluation Pipeline Architecture</span>
        </label>
        <span className="text-[11px] text-slate-500 font-mono">
          Controlled experimental baselines
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {MODES.map((mode) => {
          const isSelected = selectedMode === mode.id;
          const Icon = mode.icon;

          return (
            <div
              key={mode.id}
              onClick={() => !disabled && onSelectMode(mode.id)}
              className={`relative rounded-xl border p-4 transition-all cursor-pointer flex flex-col justify-between ${
                disabled ? 'opacity-60 cursor-not-allowed' : ''
              } ${
                isSelected
                  ? 'bg-slate-900 text-white border-slate-900 shadow-md ring-2 ring-indigo-500/30'
                  : 'bg-white hover:bg-slate-50 border-slate-200 text-slate-900 hover:border-slate-300 shadow-2xs'
              }`}
            >
              <div>
                {/* Header Row: Icon, Title & Badge */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div
                    className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 border ${
                      isSelected
                        ? 'bg-slate-800 border-slate-700 text-indigo-400'
                        : 'bg-slate-100 border-slate-200 text-slate-700'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                  </div>

                  <span
                    className={`text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full border font-semibold ${
                      isSelected
                        ? 'bg-slate-800 border-slate-700 text-indigo-300'
                        : mode.badgeColor
                    }`}
                  >
                    {mode.badge}
                  </span>
                </div>

                <div className="flex items-center gap-1.5 mb-1.5">
                  <h4 className="text-sm font-bold font-serif">{mode.title}</h4>
                  {isSelected && <Check className="w-3.5 h-3.5 text-indigo-400 shrink-0" />}
                </div>

                <p
                  className={`text-xs leading-relaxed ${
                    isSelected ? 'text-slate-300' : 'text-slate-600'
                  }`}
                >
                  {mode.description}
                </p>
              </div>

              {/* Footer Meta */}
              <div
                className={`mt-3 pt-2.5 border-t text-[10.5px] font-mono flex items-center justify-between ${
                  isSelected
                    ? 'border-slate-800 text-slate-400'
                    : 'border-slate-100 text-slate-500'
                }`}
              >
                <span>{mode.meta}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
