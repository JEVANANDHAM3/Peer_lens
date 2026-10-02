import React, { useState, useEffect, useRef } from 'react';
import {
  ReviewMode,
  ReviewStatus,
  Issue,
  PaperInfo,
  ReviewerType,
  ReviewRound,
  PaperVersion,
  ReviewResult,
  HumanFeedback,
  FinalReportData,
  RetrievedPaper,
  PaperSummary,
} from './types';
import {
  startReview,
  getReviewStatus,
  getReview,
  submitFeedback,
  uploadAndReview,
  getPapers,
  getPaper,
  deletePaper,
  savePaperVersion,
  reReviewPaper,
  reconsiderIssue,
} from './lib/api';
import { Header } from './components/Header';
import { Sidebar } from './components/Sidebar';

const defaultPaperInfo: PaperInfo = {
  title: 'Uploaded Paper',
  fileName: '',
  fileSize: '',
  pages: 0,
  sections: [],
  authors: '',
  abstract: '',
};
import { PDFUploader } from './components/PDFUploader';
import { AnalysisProgress } from './components/AnalysisProgress';
import { ArrowRight, FileText, UploadCloud, Lock, CheckCircle2, FileCheck2, Layers } from 'lucide-react';
import { ReviewSummary } from './components/ReviewSummary';
import { OverviewTab } from './components/OverviewTab';
import { IssuesTab } from './components/IssuesTab';
import { RAGEvidence } from './components/RAGEvidence';
import { ReviewHistory } from './components/ReviewHistory';
import { IssueDetailModal } from './components/IssueDetailModal';
import { FeedbackModal } from './components/FeedbackModal';
import { RevisionComparison } from './components/RevisionComparison';
import { FinalReport } from './components/FinalReport';
import { ReviewModeSelector } from './components/ReviewModeSelector';

export default function App() {
  // Screens: 'upload' | 'analyzing' | 'review'
  const [screen, setScreen] = useState<'upload' | 'analyzing' | 'review'>('upload');
  
  // Paper & Mode State
  const [paperInfo, setPaperInfo] = useState<PaperInfo | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [paperId, setPaperId] = useState<string | null>(null);
  const [reviewMode, setReviewMode] = useState<ReviewMode>('agentic_rag');

  // Review Tab State: 'overview' | 'issues' | 'evidence' | 'history'
  const [activeTab, setActiveTab] = useState<'overview' | 'issues' | 'evidence' | 'history'>('overview');

  // Issues State (Dynamic: allows Accept, Dispute, Reset, Revisions)
  const [issues, setIssues] = useState<Issue[]>([]);
  const [selectedReviewerFilter, setSelectedReviewerFilter] = useState<ReviewerType | 'All'>('All');
  const [reviewError, setReviewError] = useState<string | null>(null);
  const [reviewId, setReviewId] = useState<string | null>(null);
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>('idle');
  const [reviewResult, setReviewResult] = useState<ReviewResult | null>(null);

  // Paper Versions (Dynamic: tracks all manuscript uploads version by version)
  const [paperVersions, setPaperVersions] = useState<PaperVersion[]>([]);
  const [currentVersion, setCurrentVersion] = useState<number>(1);

  // Review Rounds (Dynamic for revision progress & tracking history)
  const [reviewRounds, setReviewRounds] = useState<ReviewRound[]>([]);
  const [isRevisionAnalysis, setIsRevisionAnalysis] = useState<boolean>(false);
  const [pendingRevisionFile, setPendingRevisionFile] = useState<string>('');

  // Modals
  const [selectedIssueForDetail, setSelectedIssueForDetail] = useState<Issue | null>(null);
  const [selectedIssueForDispute, setSelectedIssueForDispute] = useState<Issue | null>(null);
  const [isRevisionModalOpen, setIsRevisionModalOpen] = useState(false);
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);

  // Sidebar & Database Tracking State
  const [papersList, setPapersList] = useState<PaperSummary[]>([]);
  const [isLoadingPapers, setIsLoadingPapers] = useState<boolean>(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState<boolean>(true);
  const revisionFileInputRef = useRef<HTMLInputElement>(null);

  // Stats calculation
  const rigorCount = issues.filter((i) => i.reviewer === 'Rigor Reviewer' && !i.resolvedInRevision).length;
  const clarityCount = issues.filter((i) => i.reviewer === 'Clarity Reviewer' && !i.resolvedInRevision).length;
  const noveltyCount = issues.filter((i) => i.reviewer === 'Novelty Reviewer' && !i.resolvedInRevision).length;

  const normalizeSeverity = (severity: string | undefined): Issue['severity'] => {
    const value = (severity || 'Medium').toString().toLowerCase();
    if (value === 'critical') return 'Critical';
    if (value === 'high') return 'High';
    if (value === 'medium') return 'Medium';
    if (value === 'low') return 'Low';
    return 'Medium';
  };

  const mapBackendIssues = (payload: ReviewResult | null): Issue[] => {
    if (!payload) return [];

    const issuesSource = Array.isArray((payload as any)?.all_mistakes)
      ? (payload as any).all_mistakes
      : Array.isArray(payload?.issues) && payload.issues.length > 0
        ? payload.issues
        : null;

    const mapReviewer = (rev: string | undefined): ReviewerType => {
      const lower = (rev || '').toLowerCase();
      if (lower.includes('clarity')) return 'Clarity Reviewer';
      if (lower.includes('novelty')) return 'Novelty Reviewer';
      return 'Rigor Reviewer';
    };

    if (issuesSource && issuesSource.length > 0) {
      return issuesSource.map((item: any, index: number) => {
        const reviewer = mapReviewer(item.reviewer);
        return {
          id: String(item.id || `issue-${index}`),
          severity: normalizeSeverity(String(item.severity || 'Medium')),
          reviewer,
          page: Number(item.page || 1),
          section: String(item.section || 'General'),
          title: String(item.issue || item.title || `${reviewer} finding`),
          explanation: String(item.explanation || 'The reviewer identified a concern.'),
          evidence: Array.isArray(item.evidence)
            ? item.evidence.map((entry: any) => entry?.text || entry?.section || '').filter(Boolean).join(' • ')
            : String(item.evidence || 'No direct evidence captured.'),
          suggestedAction: String(item.recommendation || 'Clarify the issue with supporting evidence.'),
          status: item.resolvedInRevision ? 'accepted' : (item.status || 'open'),
          hasLiteratureEvidence: reviewer === 'Novelty Reviewer',
          deepExplanation: String(item.explanation || item.description || 'No additional explanation.'),
          introducedInVersion: item.introducedInVersion || 'v1.0',
          resolvedInRevision: Boolean(item.resolvedInRevision),
          resolvedInVersion: item.resolvedInVersion,
          resolutionNote: item.resolutionNote,
          revisedEvidence: item.revisedEvidence,
        };
      });
    }

    const sources = [
      { key: 'rigor_review', label: 'Rigor Reviewer' as const },
      { key: 'clarity_review', label: 'Clarity Reviewer' as const },
      { key: 'novelty_review', label: 'Novelty Reviewer' as const },
    ] as const;

    const incomingIssues: Issue[] = [];
    sources.forEach(({ key, label }) => {
      const review = payload?.[key] as Record<string, unknown> | undefined;
      const items = Array.isArray(review?.issues) ? review.issues : [];
      items.forEach((item: any, index: number) => {
        const evidence = Array.isArray(item.evidence)
          ? item.evidence.map((entry: any) => entry?.text || entry?.section || '').filter(Boolean).join(' • ')
          : typeof item.evidence === 'string'
            ? item.evidence
            : 'No direct evidence captured.';

        incomingIssues.push({
          id: String(item.id || `${key}-${index}`),
          severity: normalizeSeverity(String(item.severity || review?.severity || 'Medium')),
          reviewer: label,
          page: Number(item.page || 1),
          section: String(item.section || 'General'),
          title: String(item.issue || item.title || `${label} finding`),
          explanation: String(item.explanation || review?.summary || 'The reviewer identified a potential concern.'),
          evidence,
          suggestedAction: String(item.recommendation || 'Clarify the issue with additional evidence or documentation.'),
          status: 'open',
          hasLiteratureEvidence: key === 'novelty_review',
          deepExplanation: String(item.explanation || item.description || 'No additional explanation was returned by the backend.'),
          introducedInVersion: 'v1.0',
        });
      });
    });

    return incomingIssues;
  };

  const buildFinalReportData = (payload: ReviewResult | null): FinalReportData => {
    const summary = (payload?.final_report as Record<string, unknown> | undefined) || payload?.meta_review || {};
    const issuesFromPayload = mapBackendIssues(payload);
    const recommendedActions = Array.isArray((summary as any)?.recommended_actions)
      ? (summary as any).recommended_actions
      : Array.isArray((summary as any)?.recommendations)
        ? (summary as any).recommendations
        : ['Address the flagged issues with specific author responses.'];

    const highIssues = issuesFromPayload.filter((item) => item.severity === 'High').map((item) => item.title);
    const mediumIssues = issuesFromPayload.filter((item) => item.severity === 'Medium').map((item) => item.title);
    const criticalIssues = issuesFromPayload.filter((item) => item.severity === 'Critical').map((item) => item.title);

    return {
      paperTitle: paperInfo?.title || 'Uploaded Paper',
      authors: paperInfo?.authors || 'Unknown authors',
      assessment: highIssues.length > 0 || criticalIssues.length > 0 ? 'Needs Revision' : 'Accept with Minor Changes',
      date: new Date().toISOString().slice(0, 10),
      criticalIssues,
      highIssues,
      mediumIssues,
      noveltyFindings: String((payload?.novelty_review as any)?.summary || 'Novelty validation completed.'),
      recommendedActions: recommendedActions.map((value: unknown) => String(value)),
    };
  };

  const fetchPapersList = async () => {
    try {
      setIsLoadingPapers(true);
      const data = await getPapers();
      setPapersList(data);
    } catch (err) {
      console.error('Failed to fetch tracked papers list:', err);
    } finally {
      setIsLoadingPapers(false);
    }
  };

  useEffect(() => {
    void fetchPapersList();
  }, []);

  // Poll papers list if any paper is currently ongoing
  useEffect(() => {
    const hasOngoing = papersList.some((p) =>
      ['running', 'reviewing', 'waiting_for_human', 're_reviewing'].includes(p.status)
    );
    if (!hasOngoing && reviewStatus !== 'running' && reviewStatus !== 'reviewing') {
      return;
    }

    const interval = window.setInterval(() => {
      void fetchPapersList();
    }, 4000);

    return () => window.clearInterval(interval);
  }, [papersList, reviewStatus]);

  useEffect(() => {
    if (!reviewId) {
      return;
    }

    let isPolling = true;

    const pollReview = async () => {
      try {
        const status = await getReviewStatus(reviewId);
        if (!isPolling) return;

        if (status.status === 'waiting_for_human') {
          setScreen('review');
        }

        if (['completed', 'failed', 'waiting_for_human'].includes(status.status)) {
          isPolling = false;
          const nextResult = await getReview(reviewId);
          setReviewResult(nextResult);
          setReviewStatus((nextResult.status as ReviewStatus) || (status.status as ReviewStatus));
          const mapped = mapBackendIssues(nextResult);
          setIssues(mapped);
          setPaperVersions((prev) =>
            prev.length > 0
              ? prev
              : [
                  {
                    version: 1,
                    versionTag: 'v1.0',
                    title: paperInfo?.title || 'Initial Manuscript Draft',
                    fileName: selectedFile?.name || paperInfo?.fileName || 'manuscript.pdf',
                    fileSize: paperInfo?.fileSize || '1.0 MB',
                    uploadedAt: new Date().toISOString().slice(0, 10),
                    round: 1,
                    totalIssues: mapped.length,
                    activeIssues: mapped.length,
                    resolvedIssues: 0,
                  },
                ]
          );
          setReviewRounds((prev) =>
            prev.length > 0
              ? prev
              : [
                  {
                    round: 1,
                    title: 'Initial Review (v1.0)',
                    date: new Date().toISOString().slice(0, 10),
                    fileName: selectedFile?.name || paperInfo?.fileName || 'manuscript.pdf',
                    issuesIdentified: mapped.length,
                    issuesRemaining: mapped.length,
                    summary: `Initial automated review for "${paperInfo?.title || 'Manuscript'}". Evaluated across methodology, literature novelty, and clarity, identifying ${mapped.length} potential issue(s).`,
                    resolvedIssues: [],
                    activeIssues: mapped.map((i) => i.title),
                    versionTag: 'v1.0',
                  },
                ]
          );
          void fetchPapersList();
          setScreen('review');
          return;
        }

        setReviewStatus(status.status as ReviewStatus);
      } catch (error) {
        if (isPolling) {
          setReviewError(error instanceof Error ? error.message : 'Review status check failed.');
        }
      }
    };

    const timer = window.setInterval(() => {
      void pollReview();
    }, 2000);

    void pollReview();

    return () => {
      isPolling = false;
      window.clearInterval(timer);
    };
  }, [reviewId]);

  const handleSelectPaper = async (selected: PaperSummary) => {
    setPaperId(selected.paper_id);
    setReviewId(selected.latest_review_id || null);
    setReviewError(null);

    // If paper review is currently in progress
    if (['running', 'reviewing', 'waiting_for_human', 're_reviewing'].includes(selected.status)) {
      setPaperInfo({
        title: selected.title,
        fileName: selected.filename,
        fileSize: selected.file_size || '1.0 MB',
        pages: selected.page_count || 1,
        sections: [],
        authors: selected.authors || 'Manuscript Author(s)',
        abstract: selected.abstract || '',
      });
      setSelectedFile(null);
      setReviewStatus(selected.status);
      setScreen('analyzing');
      return;
    }

    // If review is completed
    if (selected.status === 'completed' && selected.latest_review_id) {
      try {
        const [result, details] = await Promise.all([
          getReview(selected.latest_review_id),
          getPaper(selected.paper_id).catch(() => null),
        ]);

        const paperData = details?.paper || {};
        setPaperInfo({
          title: paperData.title || selected.title,
          fileName: paperData.filename || selected.filename,
          fileSize: paperData.file_size || selected.file_size || '1.0 MB',
          pages: paperData.page_count || selected.page_count || 1,
          sections: Array.isArray(paperData.sections) ? paperData.sections : [],
          authors: paperData.authors || selected.authors || 'Manuscript Author(s)',
          abstract: paperData.abstract || selected.abstract || '',
        });
        setSelectedFile(null);
        setReviewResult(result);
        setReviewStatus((result.status as ReviewStatus) || 'completed');
        const mapped = mapBackendIssues(result);
        setIssues(mapped);

        if (details?.versions && details.versions.length > 0) {
          let rawVersions = [...details.versions];
          if (!rawVersions.some((v: any) => v.version === 1)) {
            rawVersions.unshift({
              version: 1,
              version_tag: 'v1.0',
              filename: paperData.filename || selected.filename,
              file_size: paperData.file_size || selected.file_size || '1.0 MB',
              created_at: selected.created_at,
              total_issues: mapped.length,
              resolved_issues: 0,
            });
          }

          const versionsList = rawVersions.map((v: any) => ({
            version: v.version,
            versionTag: v.version_tag || `v${v.version}.0`,
            title: selected.title,
            fileName: v.filename,
            fileSize: v.file_size || '1.0 MB',
            uploadedAt: v.created_at ? v.created_at.slice(0, 10) : 'Recently',
            round: v.version,
            totalIssues: v.total_issues || mapped.length,
            activeIssues: Math.max(0, (v.total_issues || mapped.length) - (v.resolved_issues || 0)),
            resolvedIssues: v.resolved_issues || 0,
          }));
          setPaperVersions(versionsList);
          setCurrentVersion(versionsList[versionsList.length - 1].version);

          const rounds: ReviewRound[] = versionsList.map((v: any, idx: number) => {
            const isFirst = idx === 0 || v.version === 1;
            const resolved = v.resolvedIssues || 0;
            const total = v.totalIssues || mapped.length;
            const active = v.activeIssues || Math.max(0, total - resolved);
            const resolvedNames = mapped
              .filter((i) => i.resolvedInRevision && i.resolvedInVersion === v.versionTag)
              .map((i) => i.title);
            const activeNames = mapped
              .filter((i) => !i.resolvedInRevision)
              .map((i) => i.title);

            return {
              round: v.version,
              title: isFirst ? 'Initial Review (v1.0)' : `Revision Round ${v.version} (${v.versionTag})`,
              date: v.uploadedAt,
              fileName: v.fileName,
              issuesIdentified: total,
              issuesRemaining: active,
              summary: isFirst
                ? `Initial review for "${selected.title}". Flagged ${total} issues across rigor, clarity, and novelty.`
                : `Re-analysis of revision ${v.versionTag} ("${v.fileName}"): verified ${resolved} error(s) resolved, ${active} error(s) remaining.`,
              resolvedIssues: resolvedNames.length > 0 ? resolvedNames : (resolved > 0 ? [`${resolved} error(s) corrected in this draft`] : []),
              activeIssues: activeNames,
              versionTag: v.versionTag,
            };
          });
          setReviewRounds(rounds);
        } else {
          setPaperVersions([
            {
              version: 1,
              versionTag: 'v1.0',
              title: selected.title,
              fileName: selected.filename,
              fileSize: selected.file_size || '1.0 MB',
              uploadedAt: selected.created_at ? selected.created_at.slice(0, 10) : 'Recently',
              round: 1,
              totalIssues: mapped.length,
              activeIssues: mapped.length,
              resolvedIssues: 0,
            },
          ]);
          setCurrentVersion(1);
          setReviewRounds([
            {
              round: 1,
              title: 'Initial Review (v1.0)',
              date: selected.created_at ? selected.created_at.slice(0, 10) : 'Recently',
              fileName: selected.filename,
              issuesIdentified: mapped.length,
              issuesRemaining: mapped.length,
              summary: `Initial automated review for "${selected.title}". Evaluated across methodology, literature novelty, and clarity.`,
              resolvedIssues: [],
              activeIssues: mapped.map((i) => i.title),
              versionTag: 'v1.0',
            },
          ]);
        }

        setScreen('review');
        setActiveTab('overview');
      } catch (err) {
        console.error('Failed to load review from database:', err);
        setReviewError('Failed to load review details from SQLite database.');
      }
      return;
    }

    // If uploaded but not reviewed yet
    try {
      const details = await getPaper(selected.paper_id).catch(() => null);
      const paperData = details?.paper || {};
      setPaperInfo({
        title: paperData.title || selected.title,
        fileName: paperData.filename || selected.filename,
        fileSize: paperData.file_size || selected.file_size || '1.0 MB',
        pages: paperData.page_count || selected.page_count || 1,
        sections: Array.isArray(paperData.sections) ? paperData.sections : [],
        authors: paperData.authors || selected.authors || 'Manuscript Author(s)',
        abstract: paperData.abstract || selected.abstract || '',
      });
      setSelectedFile(null);
      setScreen('upload');
    } catch {
      setScreen('upload');
    }
  };

  const handleDeletePaper = async (targetPaperId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await deletePaper(targetPaperId);
      await fetchPapersList();
      if (paperId === targetPaperId) {
        handleNewReview();
      }
    } catch (err) {
      console.error('Failed to delete paper:', err);
    }
  };

  const handleStartAnalysis = async () => {
    if (!paperInfo || (!selectedFile && !paperId)) {
      setReviewError('Upload a PDF, TXT, or Markdown paper before starting the review.');
      setScreen('upload');
      return;
    }

    setReviewError(null);
    setReviewResult(null);
    setIssues([]);
    setScreen('analyzing');
    setReviewStatus('reviewing');
    void fetchPapersList();

    try {
      let finalResult: ReviewResult & { all_mistakes?: any[]; mistakes_summary?: any };

      if (selectedFile) {
        finalResult = await uploadAndReview(selectedFile, reviewMode);
      } else {
        const review = await startReview({
          paper_id: paperId!,
          review_mode: reviewMode,
        });
        setReviewId(review.review_id);
        setReviewStatus(review.status as ReviewStatus);
        void fetchPapersList();

        let status = review.status;
        let attempts = 0;
        while (!['completed', 'failed', 'waiting_for_human'].includes(status) && attempts < 90) {
          await new Promise((resolve) => setTimeout(resolve, 2000));
          attempts++;
          const statusResp = await getReviewStatus(review.review_id);
          status = statusResp.status;
          setReviewStatus(statusResp.status as ReviewStatus);
        }
        finalResult = await getReview(review.review_id);
      }

      setReviewResult(finalResult);
      setPaperId(finalResult.paper_id);
      setReviewId(finalResult.review_id);
      setReviewStatus((finalResult.status as ReviewStatus) || 'completed');
      const mapped = mapBackendIssues(finalResult);
      setIssues(mapped);

      setPaperVersions([
        {
          version: 1,
          versionTag: 'v1.0',
          title: paperInfo?.title || 'Initial Manuscript Draft',
          fileName: selectedFile?.name || paperInfo?.fileName || 'manuscript.pdf',
          fileSize: paperInfo?.fileSize || '1.0 MB',
          uploadedAt: new Date().toISOString().slice(0, 10),
          round: 1,
          totalIssues: mapped.length,
          activeIssues: mapped.length,
          resolvedIssues: 0,
        },
      ]);
      setCurrentVersion(1);
      setReviewRounds([
        {
          round: 1,
          title: 'Initial Review (v1.0)',
          date: new Date().toISOString().slice(0, 10),
          fileName: selectedFile?.name || paperInfo?.fileName || 'manuscript.pdf',
          issuesIdentified: mapped.length,
          issuesRemaining: mapped.length,
          summary: `Initial automated review for "${paperInfo?.title || 'Manuscript'}". Evaluated across methodology, literature novelty, and clarity, identifying ${mapped.length} potential issue(s).`,
          resolvedIssues: [],
          activeIssues: mapped.map((i) => i.title),
          versionTag: 'v1.0',
        },
      ]);
      void fetchPapersList();

      setScreen('review');
    } catch (error) {
      console.error('Review workflow error:', error);
      setReviewError(error instanceof Error ? error.message : 'Review request failed.');
      void fetchPapersList();
      setScreen('upload');
    }
  };

  const handleStartRevisionAnalysis = async (revisedFile: File) => {
    if (!paperId) {
      alert('Please select or upload a paper first before submitting a revision.');
      return;
    }

    try {
      setPendingRevisionFile(revisedFile.name);
      setIsRevisionAnalysis(true);
      setReviewStatus('re_reviewing');
      setScreen('analyzing');

      // Immediately move paper under "Ongoing" in the sidebar with live pulsing badge
      setPapersList((prev) =>
        prev.map((p) =>
          p.paper_id === paperId
            ? {
                ...p,
                status: 're_reviewing',
                status_message: `Re-reviewing revision (v${Math.max(2, paperVersions.length + 1)}.0)...`,
                filename: revisedFile.name,
              }
            : p
        )
      );

      const result = await reReviewPaper(paperId, revisedFile, reviewMode);

      setReviewResult(result);
      setReviewId(result.review_id);
      setReviewStatus('completed');

      const mapped = mapBackendIssues(result);
      setIssues(mapped);

      setPaperInfo((prev) =>
        prev
          ? {
              ...prev,
              fileName: result.filename || revisedFile.name,
              fileSize: result.file_size || prev.fileSize,
            }
          : prev
      );

      const resolvedCount = mapped.filter((i) => i.resolvedInRevision).length;
      const activeCount = mapped.length - resolvedCount;
      const fallbackVer = (paperVersions.length > 0 ? Math.max(...paperVersions.map((v) => v.version)) : 1) + 1;
      const newVersionNum = Math.max(2, Number(result.version || fallbackVer));
      const newVersionTag = result.version_tag || `v${newVersionNum}.0`;

      const newVersion: PaperVersion = {
        version: newVersionNum,
        versionTag: newVersionTag,
        title: `Revised Manuscript Draft ${newVersionNum}`,
        fileName: result.filename || revisedFile.name,
        fileSize: result.file_size || '2.0 MB',
        uploadedAt: new Date().toISOString().slice(0, 10),
        round: newVersionNum,
        totalIssues: mapped.length,
        activeIssues: activeCount,
        resolvedIssues: resolvedCount,
      };

      setPaperVersions((prev) => {
        let base = prev;
        if (base.length === 0) {
          base = [
            {
              version: 1,
              versionTag: 'v1.0',
              title: paperInfo?.title || 'Initial Manuscript Draft',
              fileName: paperInfo?.fileName || 'manuscript.pdf',
              fileSize: paperInfo?.fileSize || '1.0 MB',
              uploadedAt: new Date().toISOString().slice(0, 10),
              round: 1,
              totalIssues: mapped.length + resolvedCount,
              activeIssues: mapped.length + resolvedCount,
              resolvedIssues: 0,
            },
          ];
        }
        const filtered = base.filter((v) => v.version !== newVersionNum);
        return [...filtered, newVersion].sort((a, b) => a.version - b.version);
      });
      setCurrentVersion(newVersionNum);

      const resolvedList = mapped.filter((i) => i.resolvedInRevision).map((i) => i.title);
      const activeList = mapped.filter((i) => !i.resolvedInRevision).map((i) => i.title);

      const comparison = result.revision_comparison;
      const summaryText = comparison?.verdict
        ? `Re-analysis of "${result.filename}": ${comparison.verdict}. ${resolvedList.length} issue(s) verified as changed/resolved, ${activeList.length} issue(s) remain open.`
        : `Re-analysis of "${result.filename}" verified that ${resolvedList.length} issue(s) were addressed. ${activeList.length} issue(s) remain open.`;

      setReviewRounds((prev) => {
        let baseRounds = prev;
        if (baseRounds.length === 0) {
          baseRounds = [
            {
              round: 1,
              title: 'Initial Review (v1.0)',
              date: new Date().toISOString().slice(0, 10),
              fileName: paperInfo?.fileName || 'manuscript.pdf',
              issuesIdentified: mapped.length + resolvedCount,
              issuesRemaining: mapped.length + resolvedCount,
              summary: `Initial automated review for "${paperInfo?.title || 'Manuscript'}". Identified ${mapped.length + resolvedCount} potential issue(s).`,
              resolvedIssues: [],
              activeIssues: mapped.map((i) => i.title),
              versionTag: 'v1.0',
            },
          ];
        }
        const nextRoundNum = Math.max(2, baseRounds.length + 1, newVersionNum);
        const newRound: ReviewRound = {
          round: nextRoundNum,
          title: `Revision Round ${nextRoundNum} (${newVersionTag})`,
          date: new Date().toISOString().slice(0, 10),
          fileName: result.filename || revisedFile.name,
          issuesIdentified: mapped.length,
          issuesRemaining: activeCount,
          summary: summaryText,
          resolvedIssues: resolvedList,
          activeIssues: activeList,
          versionTag: newVersionTag,
        };
        const filtered = baseRounds.filter((r) => r.round !== nextRoundNum);
        return [...filtered, newRound].sort((a, b) => a.round - b.round);
      });

      await fetchPapersList();

      setIsRevisionAnalysis(false);
      setScreen('review');
      setActiveTab('issues');
    } catch (error) {
      console.error('Re-review error:', error);
      alert(error instanceof Error ? error.message : 'Failed to re-review revised paper.');
      setIsRevisionAnalysis(false);
      setScreen('review');
      void fetchPapersList();
    }
  };

  const handleAnalysisComplete = () => {
    setIsRevisionAnalysis(false);
    setScreen('review');
  };

  const handleNewReview = () => {
    setScreen('upload');
    setPaperInfo(null);
    setSelectedFile(null);
    setPaperId(null);
    setReviewId(null);
    setReviewStatus('idle');
    setReviewResult(null);
    setIssues([]);
    setReviewRounds([]);
    setPaperVersions([]);
    setCurrentVersion(1);
    setIsRevisionAnalysis(false);
    setReviewError(null);
    setActiveTab('overview');
  };

  const handleAcceptIssue = async (issueId: string) => {
    if (reviewId) {
      try {
        await submitFeedback(reviewId, issueId, 'approve', 'Accepted by the author.');
      } catch (error) {
        setReviewError(error instanceof Error ? error.message : 'Feedback submission failed.');
      }
    }
    setIssues((prev) =>
      prev.map((iss) => (iss.id === issueId ? { ...iss, status: 'accepted' } : iss))
    );
    if (selectedIssueForDetail?.id === issueId) {
      setSelectedIssueForDetail((prev) => (prev ? { ...prev, status: 'accepted' } : null));
    }
  };

  const handleDisputeSubmit = async (issueId: string, feedback: string) => {
    if (reviewId) {
      try {
        await submitFeedback(reviewId, issueId, 'dispute', feedback);
      } catch (error) {
        setReviewError(error instanceof Error ? error.message : 'Feedback submission failed.');
      }
    }
    setIssues((prev) =>
      prev.map((iss) =>
        iss.id === issueId ? { ...iss, status: 'disputed', disputeReason: feedback } : iss
      )
    );
    if (selectedIssueForDetail?.id === issueId) {
      setSelectedIssueForDetail((prev) =>
        prev ? { ...prev, status: 'disputed', disputeReason: feedback } : null
      );
    }
  };

  const handleReconsiderIssue = async (issueId: string, authorArgument: string) => {
    if (!reviewId) {
      const fallback = issues.find((i) => i.id === issueId) || ({} as Issue);
      return {
        outcome: 'upheld' as const,
        verdict_reason: 'No active review session found.',
        updated_issue: fallback,
      };
    }
    try {
      const res = await reconsiderIssue(reviewId, issueId, authorArgument);
      if (res && res.outcome === 'remove') {
        // Human feedback or proof confirmed no problem: remove the issue!
        setIssues((prev) => prev.filter((iss) => iss.id !== issueId));
        if (selectedIssueForDetail?.id === issueId) {
          setSelectedIssueForDetail(null);
        }
      } else if (res && res.updated_issue) {
        const up = res.updated_issue as any;
        const normOutcome = res.outcome;
        const mergeWithExisting = (iss: Issue): Issue => ({
          ...iss,
          status: normOutcome === 'reframe' ? 'open' : 'disputed',
          reconsidered: true,
          reconsiderationOutcome: normOutcome,
          reconsiderationNote: res.verdict_reason,
          title: String(up.title || up.issue || iss.title),
          explanation: String(up.explanation || iss.explanation),
          suggestedAction: String(up.suggestedAction || up.recommendation || iss.suggestedAction),
          actionPlan: Array.isArray(up.actionPlan) ? up.actionPlan : iss.actionPlan,
          disputeReason: authorArgument,
        });

        setIssues((prev) =>
          prev.map((iss) => (iss.id === issueId ? mergeWithExisting(iss) : iss))
        );
        if (selectedIssueForDetail?.id === issueId) {
          setSelectedIssueForDetail((prev) => (prev ? mergeWithExisting(prev) : null));
        }
      }
      return {
        outcome: res.outcome,
        verdict_reason: res.verdict_reason,
        updated_issue: res.updated_issue,
      };
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Reconsideration failed.';
      setReviewError(msg);
      throw error;
    }
  };

  const handleUndoIssueStatus = (issueId: string) => {
    setIssues((prev) =>
      prev.map((iss) =>
        iss.id === issueId ? { ...iss, status: 'open', disputeReason: undefined } : iss
      )
    );
  };

  const handleAcceptAllRemaining = () => {
    setIssues((prev) =>
      prev.map((iss) =>
        iss.status === 'open' && !iss.resolvedInRevision
          ? { ...iss, status: 'accepted' }
          : iss
      )
    );
  };

  const handleViewEvidence = (issue: Issue) => {
    setActiveTab('evidence');
    if (selectedIssueForDetail) {
      setSelectedIssueForDetail(null);
    }
  };

  // Reviewer filter shortcut from Summary Cards
  const handleSelectReviewerFromSummary = (reviewer: ReviewerType) => {
    setSelectedReviewerFilter(reviewer);
    setActiveTab('issues');
  };

  // Top 3 priority issues for Overview tab
  const priorityIssues = issues.slice(0, 3);

  // Author decisions progress & final report readiness
  const isIssueAnswered = (iss: Issue) =>
    iss.status === 'accepted' ||
    iss.status === 'disputed' ||
    iss.status === 'dismissed' ||
    Boolean(iss.resolvedInRevision);

  const answeredCount = issues.filter(isIssueAnswered).length;
  const totalIssuesCount = issues.length;
  const unansweredCount = totalIssuesCount - answeredCount;
  const isReportEnabled = totalIssuesCount > 0 && unansweredCount === 0;

  return (
    <div className="min-h-screen bg-white text-slate-900 flex font-sans overflow-hidden">
      {/* Sidebar for Tracking Ongoing and Past Uploaded Papers */}
      <Sidebar
        papers={papersList}
        activePaperId={paperId}
        isLoading={isLoadingPapers}
        isOpen={isSidebarOpen}
        onToggleOpen={() => setIsSidebarOpen((prev) => !prev)}
        onSelectPaper={handleSelectPaper}
        onNewPaper={handleNewReview}
        onDeletePaper={handleDeletePaper}
        onRefresh={fetchPapersList}
      />

      {/* Main Scrollable Content Area */}
      <div className="flex-1 flex flex-col min-w-0 h-screen overflow-y-auto">
        {/* Top Header */}
        <Header
          currentScreen={screen}
          fileName={paperInfo?.fileName || 'research_paper.pdf'}
          onNewReview={handleNewReview}
          onOpenRevision={() => setIsRevisionModalOpen(true)}
          onOpenReport={() => setIsReportModalOpen(true)}
          isReportEnabled={isReportEnabled}
          answeredCount={answeredCount}
          totalIssuesCount={totalIssuesCount}
          onToggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
          isSidebarOpen={isSidebarOpen}
        />

        {/* Main Container */}
        <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {reviewError && (
          <div className="mb-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
            Review request failed: {reviewError}.
          </div>
        )}
        {/* ================================================== */}
        {/* PAGE 1: UPLOAD SCREEN */}
        {/* ================================================== */}
        {screen === 'upload' && (
          <div className="max-w-2xl mx-auto py-8 sm:py-12 text-center space-y-8 animate-in fade-in duration-200">
            {/* Main Headings */}
            <div className="space-y-3">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest font-mono">
                Academic Evaluation Suite
              </span>
              <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 font-serif">
                Find potential issues in your research paper.
              </h1>
              <p className="text-sm sm:text-base text-slate-600 max-w-xl mx-auto leading-relaxed">
                Upload your research paper and review its methodology, clarity, claims, and novelty.
              </p>
            </div>

            {/* Upload Area Card */}
            <PDFUploader
              paperInfo={paperInfo}
              onPaperSelected={(info) => setPaperInfo(info)}
              onFileSelected={(file) => setSelectedFile(file)}
              onPaperRemoved={() => {
                setPaperInfo(null);
                setSelectedFile(null);
                setPaperId(null);
              }}
              defaultPaper={defaultPaperInfo}
            />

            {/* Pipeline Architecture Selector (No-RAG, Basic RAG, Agentic RAG) */}
            <ReviewModeSelector
              selectedMode={reviewMode}
              onSelectMode={setReviewMode}
            />

            {/* Action */}
            <div className="pt-2">
              <button
                onClick={handleStartAnalysis}
                className="w-full py-3.5 px-4 bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white text-sm font-semibold rounded-xl transition-colors flex items-center justify-center space-x-2 shadow-xs cursor-pointer"
              >
                <span>Analyze Paper</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* ================================================== */}
        {/* PAGE 2: ANALYZING SCREEN */}
        {/* ================================================== */}
        {screen === 'analyzing' && (
          <AnalysisProgress
            mode={reviewMode}
            isRevision={isRevisionAnalysis}
            fileName={pendingRevisionFile || paperInfo?.fileName}
            status={reviewStatus}
            onComplete={handleAnalysisComplete}
          />
        )}

        {/* ================================================== */}
        {/* PAGE 3: REVIEW RESULTS */}
        {/* ================================================== */}
        {screen === 'review' && (
          <div className="space-y-6 animate-in fade-in duration-200">
            {/* Title & Actions Bar */}
            <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-3 border-b border-slate-200 pb-3">
              <div>
                <h1 className="text-2xl font-bold text-slate-900 font-serif">
                  Research Paper Review
                </h1>
                <div className="flex flex-wrap items-center gap-2 mt-1">
                  <p className="text-xs text-slate-500">
                    Evaluation across Rigor, Clarity, and Novelty Reviewers
                  </p>
                  <span className="hidden sm:inline text-slate-300">·</span>
                  <ReviewModeSelector
                    selectedMode={reviewMode}
                    onSelectMode={setReviewMode}
                    compact={true}
                  />
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <div
                  className={`px-2.5 py-1 rounded-lg text-xs font-mono flex items-center gap-1.5 border transition-all ${
                    isReportEnabled
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-200 shadow-2xs'
                      : 'bg-amber-50/70 text-amber-800 border-amber-200'
                  }`}
                >
                  {isReportEnabled ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Lock className="w-3 h-3 text-amber-600" />
                  )}
                  <span>
                    {isReportEnabled
                      ? 'All Issues Answered'
                      : `${answeredCount}/${totalIssuesCount} Answered`}
                  </span>
                </div>

                <button
                  onClick={() => {
                    if (isReportEnabled) {
                      setIsReportModalOpen(true);
                    }
                  }}
                  disabled={!isReportEnabled}
                  title={
                    isReportEnabled
                      ? 'Click to generate, process, and download the official PDF review report'
                      : `Answer all issues (${unansweredCount} remaining: Accept or Dispute each issue) to enable report generation`
                  }
                  className={`text-xs font-medium rounded-lg px-3.5 py-1.5 transition-all flex items-center space-x-1.5 ${
                    isReportEnabled
                      ? 'text-white bg-slate-900 hover:bg-slate-800 border border-slate-900 shadow-xs cursor-pointer'
                      : 'text-slate-400 bg-slate-100 border border-slate-200 cursor-not-allowed opacity-60'
                  }`}
                >
                  {isReportEnabled ? (
                    <FileCheck2 className="w-3.5 h-3.5 text-white" />
                  ) : (
                    <Lock className="w-3.5 h-3.5 text-slate-400" />
                  )}
                  <span>{isReportEnabled ? 'Generate PDF' : 'Generate PDF (Locked)'}</span>
                </button>
              </div>
            </div>

            {/* Tracked Manuscript Versions Navigation Bar */}
            <div className="bg-slate-50/90 border border-slate-200 rounded-xl p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-3 shadow-2xs">
              <div className="flex items-center space-x-2 overflow-x-auto pb-1 sm:pb-0">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider font-mono mr-1 shrink-0 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-slate-400" />
                  Manuscript Versions:
                </span>
                {paperVersions.map((v) => {
                  const isSelected = v.version === currentVersion;
                  return (
                    <button
                      key={v.version}
                      onClick={() => setCurrentVersion(v.version)}
                      className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-mono transition-all shrink-0 cursor-pointer ${
                        isSelected
                          ? 'bg-slate-900 text-white font-semibold shadow-2xs'
                          : 'bg-white text-slate-700 hover:bg-slate-100 border border-slate-200'
                      }`}
                      title={`View review results for ${v.versionTag}`}
                    >
                      <span>{v.versionTag}</span>
                      <span className="text-[10px] opacity-75">({v.fileName})</span>
                      {v.version === paperVersions.length && (
                        <span className="text-[9px] uppercase px-1 py-0.2 bg-emerald-500 text-white rounded font-sans font-bold">
                          Latest
                        </span>
                      )}
                    </button>
                  );
                })}
              </div>

              <div className="flex items-center gap-2 self-start sm:self-auto shrink-0">
                {/* Hidden input to pick revised manuscript file */}
                <input
                  ref={revisionFileInputRef}
                  type="file"
                  accept=".pdf,.txt,.md"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      void handleStartRevisionAnalysis(e.target.files[0]);
                      e.target.value = '';
                    }
                  }}
                  className="hidden"
                />

                <button
                  type="button"
                  onClick={() => revisionFileInputRef.current?.click()}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-medium transition-colors shadow-2xs cursor-pointer"
                  title="Upload revised manuscript to verify error fixes"
                >
                  <UploadCloud className="w-3.5 h-3.5 text-slate-300" />
                  <span>Re-Review Revised Manuscript (v{paperVersions.length + 1}.0)</span>
                </button>

                <button
                  type="button"
                  onClick={() => setIsRevisionModalOpen(true)}
                  className="inline-flex items-center space-x-1.5 px-2.5 py-1.5 bg-white hover:bg-slate-100 text-slate-700 border border-slate-300 rounded-lg text-xs font-medium transition-colors shadow-2xs cursor-pointer"
                  title="View tracked versions and diffs"
                >
                  <Layers className="w-3.5 h-3.5 text-slate-500" />
                  <span>Version History</span>
                </button>
              </div>
            </div>

            {/* 4 Summary Cards */}
            <ReviewSummary
              rigorCount={rigorCount}
              clarityCount={clarityCount}
              noveltyCount={noveltyCount}
              overallStatus="Needs Revision"
              onSelectReviewerFilter={handleSelectReviewerFromSummary}
            />

            {/* Simple Navigation Tabs */}
            <div className="border-b border-slate-200 flex space-x-6 text-sm font-medium">
              {[
                { id: 'overview', label: 'Overview' },
                {
                  id: 'issues',
                  label: `Issues (${issues.filter((i) => !i.resolvedInRevision).length} Active)`,
                },
                { id: 'evidence', label: 'Evidence' },
                { id: 'history', label: 'History' },
              ].map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as typeof activeTab)}
                    className={`pb-3 border-b-2 text-xs sm:text-sm font-semibold transition-all relative ${
                      isActive
                        ? 'border-slate-900 text-slate-900'
                        : 'border-transparent text-slate-500 hover:text-slate-800 hover:border-slate-300'
                    }`}
                  >
                    {tab.label}
                  </button>
                );
              })}
            </div>

            {/* TAB CONTENTS */}
            <div className="py-2">
              {activeTab === 'overview' && (
                <OverviewTab
                  paperInfo={paperInfo || defaultPaperInfo}
                  priorityIssues={priorityIssues}
                  onOpenDetail={(issue) => setSelectedIssueForDetail(issue)}
                  onAccept={handleAcceptIssue}
                  onDispute={(issue) => setSelectedIssueForDispute(issue)}
                  onExplainMore={(issue) => setSelectedIssueForDetail(issue)}
                  onViewEvidence={handleViewEvidence}
                  onViewAllIssues={() => setActiveTab('issues')}
                  onUndoStatus={handleUndoIssueStatus}
                  isReportEnabled={isReportEnabled}
                  answeredCount={answeredCount}
                  totalIssuesCount={totalIssuesCount}
                  onOpenReport={() => setIsReportModalOpen(true)}
                  onAcceptAllRemaining={handleAcceptAllRemaining}
                  aiReviewSummary={String(
                    (reviewResult?.final_report as any)?.overall_assessment ||
                      (reviewResult?.meta_review as any)?.summary ||
                      (reviewResult?.meta_review as any)?.final_summary ||
                      (reviewResult?.final_report as any)?.summary ||
                      ''
                  )}
                />
              )}

              {activeTab === 'issues' && (
                <IssuesTab
                  issues={issues}
                  selectedReviewerFilter={selectedReviewerFilter}
                  onClearReviewerFilter={() => setSelectedReviewerFilter('All')}
                  onOpenDetail={(issue) => setSelectedIssueForDetail(issue)}
                  onAccept={handleAcceptIssue}
                  onDispute={(issue) => setSelectedIssueForDispute(issue)}
                  onExplainMore={(issue) => setSelectedIssueForDetail(issue)}
                  onViewEvidence={handleViewEvidence}
                  onUndoStatus={handleUndoIssueStatus}
                  onAcceptAllRemaining={handleAcceptAllRemaining}
                  onOpenReport={() => setIsReportModalOpen(true)}
                  isReportEnabled={isReportEnabled}
                  onOpenRevisionModal={() => setIsRevisionModalOpen(true)}
                  currentVersion={currentVersion}
                />
              )}

              {activeTab === 'evidence' && (() => {
                const docs =
                  (reviewResult?.retrieved_documents && reviewResult.retrieved_documents.length > 0)
                    ? reviewResult.retrieved_documents
                    : ((reviewResult?.novelty_review as any)?.evidence || []);

                const mappedPapers: RetrievedPaper[] = (docs as any[]).map((item: any, index: number) => {
                  const title = String(item.title || item.document || 'arXiv Publication');
                  const source = String(item.source || item.entry_id || '');
                  const isArxiv = source.includes('arxiv.org') || source.startsWith('http');
                  const sourceUrl = isArxiv ? source : undefined;
                  const pdfUrl = item.pdf_url || (isArxiv ? source.replace('/abs/', '/pdf/') : undefined);
                  const year = item.year || (item.metadata && item.metadata.year) || new Date().getFullYear();
                  const authors = item.authors || (item.metadata && item.metadata.authors) || 'arXiv Researchers';
                  const snippet = item.relevant_text || item.abstract || item.content || item.text || 'Literature evidence retrieved from arXiv.';
                  const score =
                    item.similarity_score !== undefined
                      ? `${(Number(item.similarity_score) * 100).toFixed(0)}% match`
                      : 'Relevant';

                  return {
                    id: String(item.id || item.entry_id || `retrieval-${index}`),
                    title,
                    type: 'arXiv Publication',
                    year: Number(year),
                    authors: String(authors),
                    snippet: String(snippet),
                    relevance: score,
                    matchedExcerpt: String(snippet),
                    paperExcerpt: String(
                      item.paper_excerpt ||
                        (reviewResult?.novelty_review as any)?.claims_checked?.[0]?.claim ||
                        paperInfo?.abstract ||
                        'Manuscript Novelty Claim'
                    ),
                    sourceUrl,
                    pdfUrl,
                  };
                });

                const retrievalHist =
                  (reviewResult?.retrieval_history && reviewResult.retrieval_history.length > 0)
                    ? (reviewResult.retrieval_history as any[])
                    : ((reviewResult?.novelty_review as any)?.retrieval_history || []);

                const noveltyRev = reviewResult?.novelty_review as any;
                const claimText =
                  noveltyRev?.claims_checked?.[0]?.claim ||
                  noveltyRev?.claims_analyzed?.[0]?.claim ||
                  (issues.find((i) => i.reviewer === 'Novelty Reviewer')?.title) ||
                  paperInfo?.abstract?.slice(0, 200);

                return (
                  <RAGEvidence
                    papers={mappedPapers}
                    searchQuery={retrievalHist[0]?.query}
                    claimUnderInvestigation={claimText}
                    claimSource={noveltyRev?.claims_checked?.[0]?.claim ? "Abstract / Introduction" : undefined}
                    evidenceSummary={noveltyRev?.summary}
                    recommendation={noveltyRev?.issues?.[0]?.recommendation}
                    retrievalHistory={retrievalHist}
                  />
                );
              })()}

              {activeTab === 'history' && (
                <ReviewHistory
                  rounds={reviewRounds}
                  onUploadRevised={() => setIsRevisionModalOpen(true)}
                />
              )}
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-slate-50 py-6 text-center text-xs text-slate-500">
        <div className="max-w-5xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>PEERLENS — AI Research Paper Reviewer</span>
          <span className="font-mono text-[11px] text-slate-400">
            Final-Year Capstone Demonstration · Automated Peer Review System
          </span>
        </div>
      </footer>
      </div>

      {/* MODALS */}
      {/* 1. Issue Detail Modal */}
      <IssueDetailModal
        issue={selectedIssueForDetail}
        isOpen={!!selectedIssueForDetail}
        onClose={() => setSelectedIssueForDetail(null)}
        onAccept={handleAcceptIssue}
        onDisputeFeedback={handleDisputeSubmit}
        onViewEvidence={handleViewEvidence}
        onReconsiderIssue={handleReconsiderIssue}
      />

      {/* 2. Dispute Feedback Modal */}
      <FeedbackModal
        issue={selectedIssueForDispute}
        isOpen={!!selectedIssueForDispute}
        onClose={() => setSelectedIssueForDispute(null)}
        onSubmitFeedback={handleDisputeSubmit}
        onReconsiderIssue={handleReconsiderIssue}
      />

      {/* 3. Revision Comparison Modal */}
      <RevisionComparison
        isOpen={isRevisionModalOpen}
        onClose={() => setIsRevisionModalOpen(false)}
        versions={paperVersions}
        currentVersion={currentVersion}
        issues={issues}
        selectedMode={reviewMode}
        onSelectMode={setReviewMode}
        onSelectVersion={(ver) => setCurrentVersion(ver)}
        onStartRevisionAnalysis={handleStartRevisionAnalysis}
      />

      {/* 4. Final Review Report Modal */}
      <FinalReport
        data={buildFinalReportData(reviewResult)}
        issues={issues}
        isOpen={isReportModalOpen}
        onClose={() => setIsReportModalOpen(false)}
      />
    </div>
  );
}
