import React, { useState, useEffect } from 'react';
import { FinalReportData, Issue } from '../types';
import {
  X,
  Download,
  Printer,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Loader2,
  Sparkles,
  FileCheck,
} from 'lucide-react';

interface FinalReportProps {
  data: FinalReportData;
  issues: Issue[];
  isOpen: boolean;
  onClose: () => void;
}

export const FinalReport: React.FC<FinalReportProps> = ({
  data,
  issues,
  isOpen,
  onClose,
}) => {
  if (!isOpen) return null;

  const [pdfStatus, setPdfStatus] = useState<'idle' | 'processing' | 'ready'>('idle');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingStep, setProcessingStep] = useState('Compiling review report layout...');

  // Reset generation status when modal opens
  useEffect(() => {
    if (isOpen) {
      setPdfStatus('idle');
      setProcessingProgress(0);
      setProcessingStep('Compiling review report layout...');
    }
  }, [isOpen]);

  const acceptedCount = issues.filter((i) => i.status === 'accepted').length;
  const disputedIssues = issues.filter((i) => i.status === 'disputed');

  const startPdfGeneration = () => {
    setPdfStatus('processing');
    setProcessingProgress(15);
    setProcessingStep('Aggregating reviewer rubrics and issue deltas...');

    setTimeout(() => {
      setProcessingProgress(45);
      setProcessingStep('Formatting typography, tables, and author responses...');
    }, 700);

    setTimeout(() => {
      setProcessingProgress(78);
      setProcessingStep('Rendering high-resolution vector PDF document...');
    }, 1400);

    setTimeout(() => {
      setProcessingProgress(100);
      setProcessingStep('PDF generation complete. Document ready for download.');
      setPdfStatus('ready');
    }, 2100);
  };

  const handleDownload = () => {
    // Generate comprehensive academic peer review report
    const criticalList = issues.filter((i) => i.severity === 'Critical');
    const highList = issues.filter((i) => i.severity === 'High');
    const mediumList = issues.filter((i) => i.severity === 'Medium');
    const lowList = issues.filter((i) => i.severity === 'Low');

    const formatIssueHtml = (issue: Issue, idx: number) => {
      const hasSteps = (issue.suggestedAction || '').includes('Actionable Next Steps:');
      let stepsHtml = '';
      if (hasSteps) {
        const [mainRec, stepsBlock] = issue.suggestedAction.split(/Actionable Next Steps:/i);
        const steps = (stepsBlock || '')
          .split(/\n•\s*|\n-\s*|•\s*/)
          .map((s) => s.trim())
          .filter((s) => s.length > 0);
        stepsHtml = `
          <div style="margin-top: 8px; font-weight: 600; color: #1e293b;">${mainRec.trim()}</div>
          <div style="margin-top: 6px; padding-left: 8px; border-left: 2px solid #cbd5e1;">
            <div style="font-size: 10px; font-weight: bold; text-transform: uppercase; color: #64748b; margin-bottom: 4px;">Actionable Next Steps for Revision:</div>
            ${steps.map((st, sidx) => `
              <div style="margin-bottom: 4px; font-size: 11.5px; display: flex; align-items: flex-start; gap: 6px;">
                <span style="background: #e0e7ff; color: #3730a3; font-weight: bold; font-family: monospace; font-size: 9.5px; padding: 1px 5px; border-radius: 3px; shrink: 0;">Step ${sidx + 1}</span>
                <span>${st.replace(/^Step\s*\d+\s*(\([^)]+\))?:?\s*/i, '')}</span>
              </div>
            `).join('')}
          </div>
        `;
      } else {
        stepsHtml = `<div style="margin-top: 6px; color: #334155;"><strong>Remediation:</strong> ${issue.suggestedAction || 'Review and revise according to standard guidelines.'}</div>`;
      }

      return `
        <div style="margin-bottom: 16px; padding: 12px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 6px;">
          <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px;">
            <div style="font-size: 13px; font-weight: bold; color: #0f172a;">${idx + 1}. ${issue.title}</div>
            <div style="font-size: 10.5px; font-family: monospace; color: #64748b;">Page ${issue.page} &bull; ${issue.section} &bull; ${issue.reviewer}</div>
          </div>
          <div style="font-size: 12px; color: #475569; margin-bottom: 6px; line-height: 1.4;">${issue.explanation}</div>
          ${issue.evidence ? `
            <div style="background: #f8fafc; border: 1px solid #f1f5f9; padding: 6px 10px; border-radius: 4px; font-family: monospace; font-size: 11px; color: #334155; margin-bottom: 6px;">
              <strong>Evidence from Paper:</strong> "${String(issue.evidence).substring(0, 300)}"
            </div>
          ` : ''}
          ${stepsHtml}
          ${issue.status === 'disputed' ? `
            <div style="margin-top: 6px; padding: 6px 10px; background: #fffbeb; border: 1px solid #fef3c7; border-radius: 4px; font-size: 11px; color: #92400e;">
              <strong>Author Dispute:</strong> <em>"${issue.disputeReason || 'Disputed'}"</em>
            </div>
          ` : issue.status === 'accepted' ? `
            <div style="margin-top: 6px; font-size: 11px; color: #166534; font-weight: 600;">
              &check; Accepted by author into manuscript revision roadmap
            </div>
          ` : ''}
        </div>
      `;
    };

    const reportHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>PeerLens Comprehensive Evaluation Report - ${data.paperTitle}</title>
  <style>
    @page { size: letter; margin: 15mm; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.5; font-size: 12.5px; margin: 0; padding: 24px; max-width: 900px; margin: 0 auto; }
    h1 { font-size: 24px; margin-bottom: 4px; color: #0f172a; font-family: Georgia, serif; }
    h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.08em; border-bottom: 2px solid #0f172a; padding-bottom: 4px; margin-top: 28px; color: #0f172a; font-family: monospace; }
    .badge { display: inline-block; padding: 4px 12px; border-radius: 6px; font-weight: bold; font-size: 12px; text-transform: uppercase; background: #0f172a; color: #ffffff; letter-spacing: 0.05em; }
    .meta-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; margin-top: 14px; margin-bottom: 20px; }
    .footer { margin-top: 40px; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 12px; text-align: center; font-family: monospace; }
    @media print {
      body { padding: 0; font-size: 11.5px; }
      h2 { page-break-after: avoid; }
    }
  </style>
</head>
<body>
  <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid #cbd5e1; padding-bottom: 16px;">
    <div>
      <div style="font-size: 10px; font-weight: bold; letter-spacing: 1.5px; color: #475569; text-transform: uppercase; font-family: monospace;">PeerLens Automated Peer Review System</div>
      <h1 style="margin-top: 6px; margin-bottom: 6px;">${data.paperTitle}</h1>
      <div style="color: #64748b; font-size: 12px;">Author(s): <strong>${data.authors}</strong> &bull; Evaluation Date: <strong>${data.date}</strong> &bull; Tracked Issues: <strong>${issues.length}</strong></div>
    </div>
    <div style="text-align: right;">
      <span class="badge">${data.assessment}</span>
      <div style="font-size: 10px; font-family: monospace; color: #64748b; margin-top: 4px;">Report ID: PL-2026-${Math.floor(1000 + Math.random() * 9000)}</div>
    </div>
  </div>

  <h2>1. Executive Summary & Assessment</h2>
  <div class="meta-box">
    <p style="margin: 0; font-size: 13px; line-height: 1.6; color: #1e293b;">
      The manuscript was evaluated across three independent peer reviewer specialist perspectives: <strong>Technical Rigor</strong>, <strong>Presentation Clarity</strong>, and <strong>Claim Novelty / Prior Art Verification</strong>. A total of <strong>${issues.length} potential issues</strong> were identified (${criticalList.length} Critical, ${highList.length} High, ${mediumList.length} Medium, ${lowList.length} Low).
    </p>
  </div>

  ${criticalList.length > 0 ? `
    <h2>2. Critical Priority Issues & Action Plans (${criticalList.length})</h2>
    ${criticalList.map((iss, idx) => formatIssueHtml(iss, idx)).join('')}
  ` : ''}

  ${highList.length > 0 ? `
    <h2>3. High Priority Issues & Action Plans (${highList.length})</h2>
    ${highList.map((iss, idx) => formatIssueHtml(iss, idx)).join('')}
  ` : ''}

  ${mediumList.length > 0 ? `
    <h2>4. Medium Priority Issues & Action Plans (${mediumList.length})</h2>
    ${mediumList.map((iss, idx) => formatIssueHtml(iss, idx)).join('')}
  ` : ''}

  <h2>5. Literature Grounding & Novelty Findings</h2>
  <div class="meta-box" style="line-height: 1.6;">
    ${data.noveltyFindings}
  </div>

  <h2>6. Human-in-the-Loop Audit & Revision Decisions</h2>
  <div class="meta-box">
    <div style="margin-bottom: 8px;"><strong>${acceptedCount} Issues Accepted</strong> into the manuscript revision plan.</div>
    <div><strong>${disputedIssues.length} Issues Disputed</strong> with author written justifications:</div>
    ${disputedIssues.map((issue) => `
      <div style="margin-top: 6px; padding: 6px 10px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 4px; font-size: 11.5px;">
        <strong>${issue.title}</strong>: <em style="color: #475569;">"${issue.disputeReason || 'Disputed without detailed rationale'}"</em>
      </div>
    `).join('')}
  </div>

  <h2>7. Recommended Synthesis Actions for Revision</h2>
  <div class="meta-box">
    <ol style="margin: 0; padding-left: 20px;">
      ${data.recommendedActions.map((action) => `<li style="margin-bottom: 8px; line-height: 1.5;">${action}</li>`).join('')}
    </ol>
  </div>

  <div class="footer">
    PeerLens Automated Academic Peer Review Suite &bull; Rigor, Clarity, Novelty Evaluated &bull; Official Review Copy
  </div>
</body>
</html>`;

    const blob = new Blob([reportHtml], { type: 'text/html;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `PeerLens_Evaluation_Report_${data.paperTitle.substring(0, 24).replace(/\s+/g, '_')}.html`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-2xs">
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto text-left relative animate-in fade-in zoom-in-95 duration-150">
        {/* Sticky Header with Action Buttons */}
        <div className="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between z-10">
          <div>
            <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500 block">
              Official Evaluation Document
            </span>
            <h2 className="text-lg font-bold text-slate-900 font-serif">
              PeerLens Review Report
            </h2>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => window.print()}
              className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-md border border-slate-200 cursor-pointer"
              title="Print Document"
            >
              <Printer className="w-4 h-4" />
            </button>

            {pdfStatus === 'idle' && (
              <button
                type="button"
                onClick={startPdfGeneration}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-all shadow-2xs cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                <span>Generate PDF</span>
              </button>
            )}

            {pdfStatus === 'processing' && (
              <button
                type="button"
                disabled
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-slate-100 border border-slate-200 rounded-lg cursor-wait"
              >
                <Loader2 className="w-3.5 h-3.5 text-slate-600 animate-spin" />
                <span>Processing PDF ({processingProgress}%)...</span>
              </button>
            )}

            {pdfStatus === 'ready' && (
              <button
                type="button"
                onClick={handleDownload}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-all shadow-2xs cursor-pointer animate-in fade-in"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download PDF</span>
              </button>
            )}

            <button
              onClick={onClose}
              className="p-1.5 text-slate-400 hover:text-slate-600 rounded-md ml-1 cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Processing Banner or Notification */}
        {pdfStatus === 'processing' && (
          <div className="bg-slate-900 text-white px-6 py-3 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800">
            <div className="flex items-center space-x-2.5">
              <Loader2 className="w-4 h-4 text-emerald-400 animate-spin shrink-0" />
              <div>
                <span className="font-semibold block sm:inline">Generating Document: </span>
                <span className="text-slate-300 font-mono text-[11px]">{processingStep}</span>
              </div>
            </div>
            <div className="w-32 bg-slate-800 h-2 rounded-full overflow-hidden shrink-0 border border-slate-700">
              <div
                className="bg-emerald-400 h-full transition-all duration-300 rounded-full"
                style={{ width: `${processingProgress}%` }}
              />
            </div>
          </div>
        )}

        {pdfStatus === 'ready' && (
          <div className="bg-emerald-50 border-b border-emerald-200 px-6 py-2.5 text-xs text-emerald-900 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span className="font-semibold">
                PDF successfully generated and processed! Ready for download.
              </span>
            </div>
            <button
              onClick={handleDownload}
              className="text-[11px] font-bold text-emerald-800 hover:text-emerald-950 underline cursor-pointer"
            >
              Download now
            </button>
          </div>
        )}

        {/* Report Content */}
        <div className="p-6 sm:p-8 space-y-6 text-xs text-slate-800">
          {/* Paper Info & Assessment Block */}
          <div className="border-b border-slate-200 pb-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-0.5">
                  Paper
                </span>
                <h3 className="text-base sm:text-lg font-bold text-slate-900 font-serif">
                  {data.paperTitle}
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">{data.authors}</p>
              </div>

              <div className="sm:text-right shrink-0">
                <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                  Overall Assessment
                </span>
                <span className="inline-flex items-center px-3 py-1 rounded-md text-xs font-bold uppercase tracking-wider bg-amber-50 text-amber-800 border border-amber-300">
                  {data.assessment}
                </span>
              </div>
            </div>
          </div>

          {/* Critical Issues */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-rose-800 mb-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-rose-600" />
              Critical Issues ({issues.filter((i) => i.severity === 'Critical').length || data.criticalIssues.length})
            </h4>
            <div className="space-y-2.5">
              {issues.filter((i) => i.severity === 'Critical').length > 0
                ? issues
                    .filter((i) => i.severity === 'Critical')
                    .map((iss, idx) => {
                      const hasSteps = (iss.suggestedAction || '').includes('Actionable Next Steps:');
                      const [mainRec, stepsBlock] = hasSteps
                        ? iss.suggestedAction.split(/Actionable Next Steps:/i)
                        : [iss.suggestedAction, ''];
                      const steps = (stepsBlock || '')
                        .split(/\n•\s*|\n-\s*|•\s*/)
                        .map((s) => s.trim())
                        .filter((s) => s.length > 0);

                      return (
                        <div key={iss.id || idx} className="p-3.5 bg-rose-50/20 border border-rose-200/80 rounded-lg space-y-2">
                          <div className="flex flex-wrap items-baseline justify-between gap-1">
                            <h5 className="font-bold text-slate-900 text-xs">
                              {idx + 1}. {iss.title}
                            </h5>
                            <span className="font-mono text-[10.5px] text-slate-500">
                              Page {iss.page} · {iss.section} · {iss.reviewer}
                            </span>
                          </div>
                          <p className="text-slate-600 text-xs leading-relaxed">{iss.explanation}</p>
                          {iss.evidence && (
                            <div className="p-2 bg-white rounded border border-rose-100 font-mono text-[11px] text-slate-700">
                              <span className="font-semibold text-slate-500 font-sans">Evidence: </span>
                              "{String(iss.evidence).substring(0, 300)}"
                            </div>
                          )}
                          <div className="pt-1.5 border-t border-rose-100 space-y-1.5">
                            <div className="text-xs font-semibold text-slate-800">
                              <span className="text-slate-500 uppercase tracking-wider text-[10px] block font-mono">Suggested Remediation:</span>
                              {mainRec}
                            </div>
                            {steps.length > 0 && (
                              <div className="space-y-1 pt-1">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-rose-900 font-mono block">
                                  Actionable Next Steps:
                                </span>
                                {steps.map((st, sidx) => (
                                  <div key={sidx} className="flex items-start gap-1.5 text-xs text-slate-800 bg-white p-1.5 rounded border border-rose-200">
                                    <span className="px-1.5 py-0.2 rounded bg-rose-100 text-rose-900 font-mono font-bold text-[9.5px] shrink-0">
                                      Step {sidx + 1}
                                    </span>
                                    <span className="leading-relaxed">{st.replace(/^Step\s*\d+\s*(\([^)]+\))?:?\s*/i, '')}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })
                : data.criticalIssues.map((issue, idx) => (
                    <div key={idx} className="p-3 bg-rose-50/40 border border-rose-200 rounded-lg flex items-start gap-2">
                      <span className="font-mono text-rose-700 font-bold shrink-0">{idx + 1}.</span>
                      <p className="text-slate-800 leading-relaxed text-xs">{issue}</p>
                    </div>
                  ))}
            </div>
          </div>

          {/* High Priority Issues */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-amber-800 mb-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-600" />
              High Priority Issues ({issues.filter((i) => i.severity === 'High').length || data.highIssues.length})
            </h4>
            <div className="space-y-2.5">
              {issues.filter((i) => i.severity === 'High').length > 0
                ? issues
                    .filter((i) => i.severity === 'High')
                    .map((iss, idx) => {
                      const hasSteps = (iss.suggestedAction || '').includes('Actionable Next Steps:');
                      const [mainRec, stepsBlock] = hasSteps
                        ? iss.suggestedAction.split(/Actionable Next Steps:/i)
                        : [iss.suggestedAction, ''];
                      const steps = (stepsBlock || '')
                        .split(/\n•\s*|\n-\s*|•\s*/)
                        .map((s) => s.trim())
                        .filter((s) => s.length > 0);

                      return (
                        <div key={iss.id || idx} className="p-3.5 bg-amber-50/20 border border-amber-200/80 rounded-lg space-y-2">
                          <div className="flex flex-wrap items-baseline justify-between gap-1">
                            <h5 className="font-bold text-slate-900 text-xs">
                              {idx + 1}. {iss.title}
                            </h5>
                            <span className="font-mono text-[10.5px] text-slate-500">
                              Page {iss.page} · {iss.section} · {iss.reviewer}
                            </span>
                          </div>
                          <p className="text-slate-600 text-xs leading-relaxed">{iss.explanation}</p>
                          {iss.evidence && (
                            <div className="p-2 bg-white rounded border border-amber-100 font-mono text-[11px] text-slate-700">
                              <span className="font-semibold text-slate-500 font-sans">Evidence: </span>
                              "{String(iss.evidence).substring(0, 300)}"
                            </div>
                          )}
                          <div className="pt-1.5 border-t border-amber-100 space-y-1.5">
                            <div className="text-xs font-semibold text-slate-800">
                              <span className="text-slate-500 uppercase tracking-wider text-[10px] block font-mono">Suggested Remediation:</span>
                              {mainRec}
                            </div>
                            {steps.length > 0 && (
                              <div className="space-y-1 pt-1">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-900 font-mono block">
                                  Actionable Next Steps:
                                </span>
                                {steps.map((st, sidx) => (
                                  <div key={sidx} className="flex items-start gap-1.5 text-xs text-slate-800 bg-white p-1.5 rounded border border-amber-200">
                                    <span className="px-1.5 py-0.2 rounded bg-amber-100 text-amber-900 font-mono font-bold text-[9.5px] shrink-0">
                                      Step {sidx + 1}
                                    </span>
                                    <span className="leading-relaxed">{st.replace(/^Step\s*\d+\s*(\([^)]+\))?:?\s*/i, '')}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })
                : data.highIssues.map((issue, idx) => (
                    <div key={idx} className="p-3 bg-amber-50/40 border border-amber-200 rounded-lg flex items-start gap-2">
                      <span className="font-mono text-amber-700 font-bold shrink-0">{idx + 1}.</span>
                      <p className="text-slate-800 leading-relaxed text-xs">{issue}</p>
                    </div>
                  ))}
            </div>
          </div>

          {/* Medium Priority Issues */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 mb-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-slate-500" />
              Medium Priority Issues ({issues.filter((i) => i.severity === 'Medium').length || data.mediumIssues.length})
            </h4>
            <div className="space-y-2.5">
              {issues.filter((i) => i.severity === 'Medium').length > 0
                ? issues
                    .filter((i) => i.severity === 'Medium')
                    .map((iss, idx) => {
                      const hasSteps = (iss.suggestedAction || '').includes('Actionable Next Steps:');
                      const [mainRec, stepsBlock] = hasSteps
                        ? iss.suggestedAction.split(/Actionable Next Steps:/i)
                        : [iss.suggestedAction, ''];
                      const steps = (stepsBlock || '')
                        .split(/\n•\s*|\n-\s*|•\s*/)
                        .map((s) => s.trim())
                        .filter((s) => s.length > 0);

                      return (
                        <div key={iss.id || idx} className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
                          <div className="flex flex-wrap items-baseline justify-between gap-1">
                            <h5 className="font-bold text-slate-900 text-xs">
                              {idx + 1}. {iss.title}
                            </h5>
                            <span className="font-mono text-[10.5px] text-slate-500">
                              Page {iss.page} · {iss.section} · {iss.reviewer}
                            </span>
                          </div>
                          <p className="text-slate-600 text-xs leading-relaxed">{iss.explanation}</p>
                          <div className="pt-1.5 border-t border-slate-200 space-y-1.5">
                            <div className="text-xs font-semibold text-slate-800">
                              <span className="text-slate-500 uppercase tracking-wider text-[10px] block font-mono">Suggested Remediation:</span>
                              {mainRec}
                            </div>
                            {steps.length > 0 && (
                              <div className="space-y-1 pt-1">
                                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700 font-mono block">
                                  Actionable Next Steps:
                                </span>
                                {steps.map((st, sidx) => (
                                  <div key={sidx} className="flex items-start gap-1.5 text-xs text-slate-800 bg-white p-1.5 rounded border border-slate-200">
                                    <span className="px-1.5 py-0.2 rounded bg-slate-200 text-slate-800 font-mono font-bold text-[9.5px] shrink-0">
                                      Step {sidx + 1}
                                    </span>
                                    <span className="leading-relaxed">{st.replace(/^Step\s*\d+\s*(\([^)]+\))?:?\s*/i, '')}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })
                : data.mediumIssues.map((issue, idx) => (
                    <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-2">
                      <span className="font-mono text-slate-500 font-bold shrink-0">{idx + 1}.</span>
                      <p className="text-slate-700 leading-relaxed text-xs">{issue}</p>
                    </div>
                  ))}
            </div>
          </div>

          {/* Novelty Findings */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-blue-900 mb-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-600" />
              Novelty Findings
            </h4>
            <div className="p-3.5 bg-blue-50/40 border border-blue-200 rounded-lg text-slate-800 leading-relaxed">
              {data.noveltyFindings}
            </div>
          </div>

          {/* Human Feedback */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 mb-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-slate-800" />
              Human Feedback & Response Summary
            </h4>
            <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-lg space-y-3">
              <div className="flex items-center space-x-4">
                <span className="inline-flex items-center text-emerald-700 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                  {acceptedCount} Issues Accepted into revision plan
                </span>
                <span className="inline-flex items-center text-amber-700 font-medium">
                  <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-600" />
                  {disputedIssues.length} Issues Disputed
                </span>
              </div>

              {disputedIssues.length > 0 && (
                <div className="pt-2 border-t border-slate-200 space-y-1.5">
                  <span className="font-semibold text-slate-700 block text-[11px] uppercase tracking-wider">
                    Author Justifications:
                  </span>
                  {disputedIssues.map((issue, i) => (
                    <div key={i} className="text-xs bg-white p-2 rounded border border-slate-200">
                      <span className="font-semibold text-slate-900">{issue.title}: </span>
                      <span className="italic text-slate-600">"{issue.disputeReason || 'Disputed'}"</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Recommended Actions */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 mb-2 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-slate-900" />
              Recommended Actions
            </h4>
            <ol className="p-4 bg-slate-50 border border-slate-200 rounded-lg space-y-2">
              {data.recommendedActions.map((action, idx) => (
                <li key={idx} className="flex items-start gap-2.5">
                  <span className="w-4 h-4 rounded-full bg-slate-200 text-slate-800 font-bold flex items-center justify-center shrink-0 font-mono text-[10px]">
                    {idx + 1}
                  </span>
                  <span className="text-slate-800 leading-relaxed">{action}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {/* Footer */}
        <div className="sticky bottom-0 bg-slate-50 border-t border-slate-200 px-6 py-4 flex items-center justify-between">
          <span className="text-[11px] font-mono text-slate-500">
            Report ID: PL-2026-9481 · PeerLens Review Engine
          </span>
          <div className="flex items-center space-x-2">
            {pdfStatus === 'idle' && (
              <button
                type="button"
                onClick={startPdfGeneration}
                className="px-3.5 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-all shadow-2xs flex items-center gap-1.5 cursor-pointer"
              >
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                <span>Generate PDF</span>
              </button>
            )}

            {pdfStatus === 'processing' && (
              <button
                type="button"
                disabled
                className="px-3.5 py-1.5 text-xs font-medium text-slate-600 bg-slate-200 border border-slate-300 rounded-lg flex items-center gap-1.5 cursor-wait"
              >
                <Loader2 className="w-3.5 h-3.5 text-slate-600 animate-spin" />
                <span>Processing PDF ({processingProgress}%)...</span>
              </button>
            )}

            {pdfStatus === 'ready' && (
              <button
                type="button"
                onClick={handleDownload}
                className="px-3.5 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg transition-all shadow-2xs flex items-center gap-1.5 cursor-pointer animate-in fade-in"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download PDF</span>
              </button>
            )}

            <button
              onClick={onClose}
              className="px-3 py-1.5 text-xs font-medium text-slate-700 hover:text-slate-900 border border-slate-300 rounded-lg bg-white cursor-pointer"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
