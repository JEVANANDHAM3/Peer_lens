import React from 'react';
import { Loader2, Cpu, Database, Sparkles } from 'lucide-react';
import { ReviewMode, ReviewStatus } from '../types';

interface AnalysisProgressProps {
  mode: ReviewMode;
  onComplete: () => void;
  isRevision?: boolean;
  fileName?: string;
  status?: ReviewStatus;
}

const stageMap: Record<ReviewStatus, { title: string; description: string }> = {
  idle: {
    title: 'Starting review...',
    description: 'Initializing the review session.',
  },
  running: {
    title: 'Preparing paper context...',
    description: 'Loading the manuscript and setting up the review agents.',
  },
  reviewing: {
    title: 'Running specialist review...',
    description: 'Rigor, clarity, and novelty reviewers are evaluating the paper.',
  },
  waiting_for_human: {
    title: 'Awaiting author feedback...',
    description: 'The reviewers flagged issues and are waiting for your decisions.',
  },
  re_reviewing: {
    title: 'Rechecking flagged issues...',
    description: 'The reviewers are revisiting the key concerns before finalizing.',
  },
  completed: {
    title: 'Finalizing review...',
    description: 'Summarizing the findings into the final report.',
  },
  failed: {
    title: 'Review error...',
    description: 'The pipeline hit an issue and needs attention.',
  },
};

const MODE_DETAILS: Record<ReviewMode, { title: string; badge: string; icon: React.ComponentType<{ className?: string }>; detail: string; workflowText: string }> = {
  no_rag: {
    title: 'No-RAG Baseline',
    badge: 'Pure LLM',
    icon: Cpu,
    detail: 'Unassisted LLM evaluation without external literature retrieval (hallucination baseline).',
    workflowText: 'Workflow: Rigor → Clarity → Novelty (Unassisted LLM) → Synthesis',
  },
  basic_rag: {
    title: 'Basic RAG',
    badge: 'Single-Pass Vector',
    icon: Database,
    detail: 'Single-pass dense vector similarity retrieval over paper sections.',
    workflowText: 'Workflow: Rigor → Clarity → Novelty (Single-Pass Retrieval) → Synthesis',
  },
  agentic_rag: {
    title: 'Agentic RAG',
    badge: 'Dynamic arXiv Search',
    icon: Sparkles,
    detail: 'Multi-hop claim extraction, dynamic scientific query formulation, and live arXiv verification.',
    workflowText: 'Workflow: Rigor → Clarity → Novelty (Agentic arXiv Search) → Synthesis',
  },
};

export const AnalysisProgress: React.FC<AnalysisProgressProps> = ({
  mode,
  isRevision = false,
  fileName,
  status = 'running',
}) => {
  const activeStage = stageMap[status] ?? stageMap.running;
  const currentModeInfo = MODE_DETAILS[mode] || MODE_DETAILS.agentic_rag;
  const ModeIcon = currentModeInfo.icon;

  const stages = [
    'Initialising',
    'Context prep',
    'Rigor review',
    'Clarity review',
    'Novelty review',
    'Finalizing',
  ];

  const stageIndex = status === 'waiting_for_human' ? 5 : status === 're_reviewing' ? 4 : status === 'completed' ? 5 : status === 'reviewing' ? 2 : status === 'failed' ? 0 : 1;

  return (
    <div className="w-full max-w-lg mx-auto py-12 px-4 sm:px-6">
      <div className="bg-white border border-slate-200 rounded-xl p-8 shadow-xs">
        <div className="text-center mb-5">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-100 mb-4 text-slate-800">
            <Loader2 className="w-6 h-6 animate-spin text-slate-700" />
          </div>
          <h2 className="text-lg font-semibold text-slate-900 tracking-tight font-serif">
            {isRevision ? 'Analyzing revised paper...' : activeStage.title}
          </h2>
          <p className="text-xs text-slate-600 mt-2">
            {isRevision
              ? `Reviewing ${fileName || 'the revised manuscript'} against the current evaluation.`
              : activeStage.description}
          </p>
        </div>

        {/* Mode Architecture Callout */}
        <div className="mb-5 p-3 rounded-lg bg-slate-50 border border-slate-200 text-left">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <ModeIcon className="w-4 h-4 text-indigo-600" />
              <span className="text-xs font-bold text-slate-900 font-serif">
                Pipeline: {currentModeInfo.title}
              </span>
            </div>
            <span className="text-[10px] font-mono uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 font-semibold">
              {currentModeInfo.badge}
            </span>
          </div>
          <p className="text-[11px] text-slate-600 leading-relaxed">
            {currentModeInfo.detail}
          </p>
        </div>

        <div className="space-y-3">
          <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-slate-900 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${((stageIndex + 1) / stages.length) * 100}%` }}
            />
          </div>

          <div className="flex items-center justify-between text-[10px] uppercase tracking-[0.2em] text-slate-500">
            {stages.map((step, index) => (
              <span
                key={step}
                className={index <= stageIndex ? 'text-slate-900 font-semibold' : 'text-slate-400'}
              >
                {step}
              </span>
            ))}
          </div>

          <p className="text-center text-[11px] text-slate-500 mt-2 font-mono">
            {currentModeInfo.workflowText}
          </p>
        </div>
      </div>
    </div>
  );
};
