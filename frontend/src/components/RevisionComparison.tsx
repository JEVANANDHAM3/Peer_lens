import React, { useState, useRef } from 'react';
import {
  X,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  UploadCloud,
  FileText,
  Trash2,
  Layers,
  Check,
} from 'lucide-react';
import { PaperVersion, Issue, ReviewMode } from '../types';
import { ReviewModeSelector } from './ReviewModeSelector';

interface RevisionComparisonProps {
  isOpen: boolean;
  onClose: () => void;
  versions: PaperVersion[];
  currentVersion: number;
  issues?: Issue[];
  selectedMode?: ReviewMode;
  onSelectMode?: (mode: ReviewMode) => void;
  onSelectVersion?: (ver: number) => void;
  onStartRevisionAnalysis?: (revisedFile: File) => void;
}

export const RevisionComparison: React.FC<RevisionComparisonProps> = ({
  isOpen,
  onClose,
  versions,
  currentVersion,
  issues = [],
  selectedMode = 'agentic_rag',
  onSelectMode,
  onSelectVersion,
  onStartRevisionAnalysis,
}) => {
  const [selectedFile, setSelectedFile] = useState<{
    name: string;
    size: string;
    date: string;
  } | null>(null);
  const [selectedFileObj, setSelectedFileObj] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const nextVersionNumber = versions.length + 1;

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const processFile = (file: File) => {
    const sizeInMb = (file.size / (1024 * 1024)).toFixed(1);
    setSelectedFileObj(file);
    setSelectedFile({
      name: file.name,
      size: `${sizeInMb} MB`,
      date: 'Just now',
    });
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setSelectedFileObj(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleStartAnalysis = () => {
    if (!selectedFileObj) return;
    onStartRevisionAnalysis?.(selectedFileObj);
    setSelectedFile(null);
    setSelectedFileObj(null);
    onClose();
  };

  const resolvedIssues = issues
    .filter((iss) => iss.status === 'accepted' || iss.resolvedInRevision)
    .map((iss) => ({
      title: iss.title,
      detail: iss.suggestedAction || iss.explanation || 'Issue addressed in revision.',
    }));

  const stillPresentIssues = issues
    .filter((iss) => iss.status !== 'accepted' && !iss.resolvedInRevision)
    .map((iss) => ({
      title: iss.title,
      detail: iss.explanation || iss.suggestedAction || 'Awaiting author response or revised evidence.',
    }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-2xs">
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-3xl w-full p-6 text-left relative animate-in fade-in zoom-in-95 duration-150 max-h-[92vh] overflow-y-auto">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1 rounded-md"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="flex items-center space-x-2.5 mb-1">
          <div className="w-8 h-8 rounded-lg bg-slate-100 flex items-center justify-center text-slate-800">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-900 font-serif">
              Manuscript Version Control & Revisions
            </h3>
          </div>
        </div>
        <p className="text-xs text-slate-500 mb-6 pl-10.5">
          All manuscript drafts are versioned and preserved. Issues are continuously tracked across rounds without overwriting prior submissions.
        </p>

        {/* SECTION 1: ALL VERSIONED DOCUMENTS */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2.5">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 font-mono flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-slate-500" />
              <span>Tracked Manuscript Versions ({versions.length})</span>
            </h4>
            <span className="text-[11px] text-slate-500 font-mono">
              All documents archived & appended
            </span>
          </div>

          <div className="space-y-2.5">
            {versions.map((ver) => {
              const isSelected = ver.version === currentVersion;
              return (
                <div
                  key={ver.version}
                  className={`p-3.5 rounded-xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                    isSelected
                      ? 'bg-slate-50/90 border-slate-400 ring-1 ring-slate-400'
                      : 'bg-white border-slate-200 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <div
                      className={`w-9 h-9 rounded-lg flex items-center justify-center font-mono font-bold text-xs ${
                        isSelected
                          ? 'bg-slate-900 text-white'
                          : 'bg-slate-100 text-slate-700 border border-slate-200'
                      }`}
                    >
                      {ver.versionTag}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-slate-900 font-serif">
                          {ver.title}
                        </span>
                        {ver.version === versions.length && (
                          <span className="text-[9px] uppercase px-1.5 py-0.2 bg-emerald-100 text-emerald-800 border border-emerald-300 rounded font-semibold">
                            Latest Version
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-500 font-mono">
                        <span className="font-semibold text-slate-700">{ver.fileName}</span>
                        <span>·</span>
                        <span>{ver.fileSize}</span>
                        <span>·</span>
                        <span>{ver.uploadedAt}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className="text-right font-mono text-xs">
                      {ver.resolvedIssues > 0 ? (
                        <div className="text-emerald-700 font-semibold flex items-center gap-1">
                          <Check className="w-3.5 h-3.5" />
                          <span>{ver.resolvedIssues} Resolved · {ver.activeIssues} Active</span>
                        </div>
                      ) : (
                        <span className="text-slate-600 font-medium">
                          {ver.totalIssues} Issues Tracked
                        </span>
                      )}
                    </div>

                    {onSelectVersion && (
                      <button
                        type="button"
                        onClick={() => onSelectVersion(ver.version)}
                        className={`px-2.5 py-1 text-xs rounded-md transition-colors cursor-pointer ${
                          isSelected
                            ? 'bg-slate-900 text-white font-medium'
                            : 'bg-slate-100 text-slate-700 hover:bg-slate-200 border border-slate-300'
                        }`}
                      >
                        {isSelected ? 'Viewing' : 'Switch To'}
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* SECTION 2: DELTA COMPARISON (IF REVISION EXISTS) */}
        {versions.length > 1 && (
          <div className="mb-6 p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-700 font-mono">
                Revision Delta (v1.0 → v{versions.length}.0)
              </span>
              <span className="text-[11px] font-semibold text-emerald-800 bg-emerald-100 border border-emerald-200 px-2 py-0.5 rounded-full">
                5 Issues Resolved in Revisions
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 text-xs">
              {/* Resolved */}
              <div className="p-3.5 bg-emerald-50/60 border border-emerald-200 rounded-lg space-y-2">
                <div className="flex items-center space-x-1.5 text-emerald-900 font-semibold uppercase tracking-wider text-[10.5px]">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Resolved Issues ({resolvedIssues.length})</span>
                </div>
                <ul className="space-y-1.5">
                  {resolvedIssues.map((item, idx) => (
                    <li key={idx} className="bg-white p-2 rounded border border-emerald-100 shadow-2xs">
                      <div className="font-semibold text-slate-900 flex items-center gap-1 text-[11px]">
                        <span className="text-emerald-600 font-bold">✓</span>
                        {item.title}
                      </div>
                      <p className="text-[10px] text-slate-600 mt-0.5">{item.detail}</p>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Still Active */}
              <div className="p-3.5 bg-amber-50/50 border border-amber-200 rounded-lg space-y-2">
                <div className="flex items-center space-x-1.5 text-amber-900 font-semibold uppercase tracking-wider text-[10.5px]">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  <span>Active Issues Remaining ({stillPresentIssues.length})</span>
                </div>
                <ul className="space-y-1.5">
                  {stillPresentIssues.length === 0 ? (
                    <li className="p-2 text-xs text-slate-500 italic bg-white rounded border border-slate-200">
                      All identified issues have been resolved.
                    </li>
                  ) : (
                    stillPresentIssues.map((item, idx) => (
                      <li key={idx} className="bg-white p-2 rounded border border-amber-100 shadow-2xs">
                        <div className="font-semibold text-slate-900 flex items-center gap-1 text-[11px]">
                          <span className="text-amber-600 font-bold">⚠</span>
                          {item.title}
                        </div>
                        <p className="text-[10px] text-slate-600 mt-0.5">{item.detail}</p>
                      </li>
                    ))
                  )}
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* SECTION 3: APPEND NEXT REVISION UPLOAD */}
        <div className="p-5 bg-slate-50/90 rounded-xl border border-dashed border-slate-300">
          <div className="mb-3">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 font-mono flex items-center gap-1.5">
              <UploadCloud className="w-4 h-4 text-slate-700" />
              <span>Append Next Revision Manuscript (v{nextVersionNumber}.0)</span>
            </h4>
            <p className="text-xs text-slate-600 mt-0.5">
              Upload an updated PDF draft. It will append as version <strong>v{nextVersionNumber}.0</strong> to your document repository without modifying previous versions.
            </p>
          </div>

          {onSelectMode && (
            <div className="mb-4">
              <ReviewModeSelector
                selectedMode={selectedMode}
                onSelectMode={onSelectMode}
              />
            </div>
          )}

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md"
            onChange={handleFileInput}
            className="hidden"
          />

          {!selectedFile ? (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className={`border border-dashed rounded-lg p-5 text-center transition-all bg-white ${
                isDragging ? 'border-slate-900 bg-slate-100' : 'border-slate-300 hover:border-slate-400'
              }`}
            >
              <UploadCloud className="w-6 h-6 text-slate-400 mx-auto mb-1.5" />
              <p className="text-xs font-semibold text-slate-800">
                Drag & drop revised manuscript here, or browse
              </p>
              <p className="text-[11px] text-slate-500 mt-0.5 mb-3">
                PDF, TXT, or Markdown documents (up to 25MB)
              </p>
              <div className="flex items-center justify-center gap-2">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium rounded-lg transition-colors cursor-pointer shadow-2xs"
                >
                  Browse Revised Manuscript
                </button>
              </div>
            </div>
          ) : (
            <div className="p-3.5 bg-white border border-slate-200 rounded-lg shadow-2xs">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="flex items-center space-x-2.5">
                  <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center text-slate-700">
                    <FileText className="w-4 h-4" />
                  </div>
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-bold text-slate-900 font-mono">
                        {selectedFile.name}
                      </span>
                      <span className="text-[10px] font-semibold text-emerald-800 bg-emerald-100 px-1.5 py-0.2 rounded font-mono">
                        Staged for v{nextVersionNumber}.0
                      </span>
                    </div>
                    <span className="text-[10.5px] text-slate-500 font-mono block">
                      {selectedFile.size} · Will append as Version v{nextVersionNumber}.0
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={handleRemoveFile}
                    className="px-2.5 py-1.5 text-xs text-rose-600 bg-white border border-rose-200 hover:bg-rose-50 rounded-lg transition-colors inline-flex items-center gap-1 cursor-pointer"
                  >
                    <Trash2 className="w-3 h-3 text-rose-500" />
                    <span>Remove</span>
                  </button>

                  <button
                    type="button"
                    onClick={handleStartAnalysis}
                    className="px-3.5 py-1.5 text-xs font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors inline-flex items-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <span>Re-Review Revised Manuscript (v{nextVersionNumber}.0)</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-slate-200 flex items-center justify-between">
          <span className="text-xs text-slate-500 font-mono">
            {versions.length} manuscript {versions.length === 1 ? 'version' : 'versions'} tracked in repository
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium text-slate-800 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 border border-slate-300 rounded-lg transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
