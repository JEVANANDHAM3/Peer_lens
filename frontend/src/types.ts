export type ReviewMode = 'no_rag' | 'basic_rag' | 'agentic_rag';
export type ReviewStatus = 'idle' | 'running' | 'reviewing' | 'waiting_for_human' | 're_reviewing' | 'completed' | 'failed';
export type Severity = 'Critical' | 'High' | 'Medium' | 'Low';
export type ReviewerType = 'Rigor Reviewer' | 'Clarity Reviewer' | 'Novelty Reviewer';
export type IssueStatus = 'open' | 'accepted' | 'disputed' | 'dismissed';

export interface HumanFeedback {
  issue_id: string;
  decision: 'approve' | 'dispute' | 'approved' | 'disputed' | 'reconsidered';
  reason?: string;
}

export interface Issue {
  id: string;
  severity: Severity;
  reviewer: ReviewerType;
  page: number;
  section: string;
  title: string;
  explanation: string;
  evidence: string;
  suggestedAction: string;
  status: IssueStatus;
  disputeReason?: string;
  hasLiteratureEvidence?: boolean;
  deepExplanation?: string;
  resolvedInRevision?: boolean;
  introducedInVersion?: string;
  resolvedInVersion?: string;
  resolutionNote?: string;
  revisedEvidence?: string;
  reconsidered?: boolean;
  reconsiderationOutcome?: 'dismissed' | 'reframed' | 'upheld';
  reconsiderationNote?: string;
  actionPlan?: string[];
  dismissed?: boolean;
}

export interface PaperVersion {
  version: number;
  versionTag: string;
  title: string;
  fileName: string;
  fileSize: string;
  uploadedAt: string;
  round: number;
  totalIssues: number;
  activeIssues: number;
  resolvedIssues: number;
}

export interface PaperInfo {
  title: string;
  fileName: string;
  fileSize: string;
  pages: number;
  sections: string[];
  authors: string;
  abstract: string;
}

export interface RetrievedPaper {
  id: string;
  title: string;
  type: string;
  year: number;
  authors: string;
  snippet: string;
  relevance: string;
  matchedExcerpt: string;
  paperExcerpt: string;
  sourceUrl?: string;
  pdfUrl?: string;
}

export interface ReviewRound {
  round: number;
  title: string;
  date: string;
  issuesIdentified: number;
  issuesRemaining: number;
  summary: string;
  resolvedIssues: string[];
  activeIssues: string[];
  fileName?: string;
  versionTag?: string;
}

export interface FinalReportData {
  paperTitle: string;
  authors: string;
  assessment: 'Needs Revision' | 'Accept with Minor Changes' | 'Reject';
  date: string;
  criticalIssues: string[];
  highIssues: string[];
  mediumIssues: string[];
  noveltyFindings: string;
  recommendedActions: string[];
}

export interface ReviewResult {
  review_id: string;
  paper_id: string;
  status: ReviewStatus;
  review_mode: ReviewMode;
  final_report?: Record<string, unknown> | null;
  meta_review?: Record<string, unknown> | null;
  rigor_review?: Record<string, unknown> | null;
  clarity_review?: Record<string, unknown> | null;
  novelty_review?: Record<string, unknown> | null;
  retrieval_history?: Array<Record<string, unknown>>;
  retrieved_documents?: Array<Record<string, unknown>>;
  issues?: Array<Record<string, unknown>>;
  conflicts?: Array<Record<string, unknown>>;
  human_feedback?: HumanFeedback[];
  message?: string;
}

export interface UploadPaperResponse {
  paper_id: string;
  filename: string;
  title?: string;
  status: 'uploaded';
}

export interface ReviewStartResponse {
  review_id: string;
  paper_id: string;
  status: ReviewStatus;
  review_mode: ReviewMode;
  message?: string;
}

export interface PaperSummary {
  paper_id: string;
  filename: string;
  title: string;
  abstract?: string;
  authors?: string;
  file_size?: string;
  page_count?: number;
  created_at: string;
  updated_at: string;
  latest_review_id?: string;
  status: ReviewStatus;
  status_message?: string;
  review_mode?: ReviewMode;
  total_issues?: number;
  active_issues_count?: number;
  resolved_issues_count?: number;
  all_issues_count?: number;
  critical_issues_count?: number;
  high_issues_count?: number;
  medium_issues_count?: number;
  low_issues_count?: number;
  version_count?: number;
}

