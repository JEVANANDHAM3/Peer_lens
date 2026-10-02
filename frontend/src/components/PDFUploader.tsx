import React, { useRef, useState } from 'react';
import { UploadCloud, FileText, X, CheckCircle2 } from 'lucide-react';
import { PaperInfo } from '../types';

interface PDFUploaderProps {
  paperInfo: PaperInfo | null;
  onPaperSelected: (info: PaperInfo) => void;
  onFileSelected?: (file: File) => void;
  onPaperRemoved: () => void;
  defaultPaper: PaperInfo;
}

export const PDFUploader: React.FC<PDFUploaderProps> = ({
  paperInfo,
  onPaperSelected,
  onFileSelected,
  onPaperRemoved,
  defaultPaper,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      await handleFile(file);
    }
  };

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      await handleFile(e.target.files[0]);
    }
  };

  const handleFile = async (file: File) => {
    const validExtensions = ['.pdf', '.txt', '.md'];
    if (!validExtensions.some((ext) => file.name.toLowerCase().endsWith(ext))) {
      return;
    }

    const sizeInMb = (file.size / (1024 * 1024)).toFixed(1);
    const cleanTitle = file.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ');
    onPaperSelected({
      title: cleanTitle,
      fileName: file.name,
      fileSize: `${sizeInMb} MB`,
      pages: 1,
      authors: 'Manuscript Author(s)',
      abstract: 'Analyzing extracted manuscript text...',
      sections: [],
    });

    if (onFileSelected) {
      onFileSelected(file);
    }
  };

  return (
    <div className="w-full">
      {!paperInfo ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 sm:p-10 text-center transition-all bg-white ${
            isDragging
              ? 'border-slate-800 bg-slate-50 scale-[0.99]'
              : 'border-slate-200 hover:border-slate-400'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.md"
            onChange={handleFileInput}
            className="hidden"
          />

          <div className="mx-auto w-12 h-12 rounded-full bg-slate-50 border border-slate-200 flex items-center justify-center mb-4">
            <UploadCloud className="w-6 h-6 text-slate-600" />
          </div>

          <h3 className="text-base font-semibold text-slate-900 mb-1">Upload Research Paper</h3>
          <p className="text-sm text-slate-600 mb-4">Drag and drop your PDF, TXT, or Markdown here</p>

          <div className="flex items-center justify-center space-x-2 my-2 text-xs text-slate-400 uppercase tracking-wider">
            <span>or</span>
          </div>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-2 mt-4">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="px-4 py-2 text-xs font-semibold text-slate-900 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 hover:border-slate-400 transition-colors shadow-2xs"
            >
              Browse Manuscript
            </button>

          </div>

          <p className="text-xs text-slate-600 mt-4">PDF, TXT, or Markdown (up to 25 MB)</p>
        </div>
      ) : (
        <div className="bg-slate-50/70 border border-slate-200 rounded-xl p-4 sm:p-5 flex items-center justify-between">
          <div className="flex items-center space-x-3.5 min-w-0">
            <div className="w-10 h-10 rounded-lg bg-white border border-slate-200 flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5 text-slate-700" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center space-x-2">
                <p className="text-sm font-semibold text-slate-900 truncate">
                  {paperInfo.fileName}
                </p>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
              </div>
              <p className="text-xs text-slate-500 font-mono">{paperInfo.fileSize}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={onPaperRemoved}
            className="p-1.5 text-slate-400 hover:text-slate-700 hover:bg-white rounded-md border border-transparent hover:border-slate-200 transition-all text-xs flex items-center gap-1"
            title="Remove file"
          >
            <X className="w-4 h-4" />
            <span className="hidden sm:inline text-xs font-medium">Remove</span>
          </button>
        </div>
      )}
    </div>
  );
};
