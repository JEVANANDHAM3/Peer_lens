/**
 * PeerLens Frontend API Client
 *
 * Communicates with exactly 6 backend endpoints:
 *
 *   1. GET  /api/health              – Liveness probe
 *   2. POST /api/review/upload       – Upload a PDF manuscript
 *   3. POST /api/review/start        – Start the LangGraph review pipeline
 *   4. GET  /api/review/{id}/status  – Poll lightweight review progress
 *   5. GET  /api/review/{id}/result  – Fetch the full review payload
 *   6. POST /api/review/{id}/feedback – Submit author accept / dispute
 */

import type {
  PaperSummary,
  ReviewMode,
  ReviewResult,
  ReviewStartResponse,
  ReviewStatus,
  UploadPaperResponse,
} from '../types';

// ---------------------------------------------------------------------------
// Base URL – resolved from environment or falls back to localhost
// ---------------------------------------------------------------------------

const API_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ||
  (import.meta.env.VITE_BACKEND_URL as string | undefined) ||
  'http://localhost:8000';

// ---------------------------------------------------------------------------
// Request body types (mirrors backend Pydantic schemas)
// ---------------------------------------------------------------------------

/** Body for POST /api/review/start */
export interface ReviewSubmissionRequest {
  paper_id: string;
  review_mode?: ReviewMode;
}

/** Response shape from GET /api/review/{id}/status */
export interface ReviewStatusResponse {
  review_id: string;
  paper_id: string;
  status: ReviewStatus;
  review_mode: ReviewMode;
  needs_human_feedback?: boolean;
  message?: string;
}

/** Response shape from POST /api/review/{id}/feedback */
export interface FeedbackResponse {
  status: string;
  message: string;
  review_status?: ReviewStatus;
  human_feedback?: Array<{ issue_id: string; decision: string; reason?: string }>;
}

// ---------------------------------------------------------------------------
// Generic fetch wrapper with error handling
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  init: RequestInit = {},
  isFormData = false,
): Promise<T> {
  const headers = new Headers(init.headers || {});
  if (!isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers,
  });

  const text = await response.text();
  const json = text ? JSON.parse(text) : {};

  if (!response.ok) {
    throw new Error(json?.detail || json?.message || 'Request failed');
  }

  return json as T;
}

// ---------------------------------------------------------------------------
// API functions (one per backend endpoint)
// ---------------------------------------------------------------------------

/**
 * **POST /api/review/upload**
 *
 * Upload a PDF file. Returns a `paper_id` to use with `startReview()`.
 */
export async function uploadPaper(file: File): Promise<UploadPaperResponse> {
  const formData = new FormData();
  formData.append('file', file);
  return request<UploadPaperResponse>(
    '/api/review/upload',
    { method: 'POST', body: formData },
    true,
  );
}

/**
 * **POST /api/review/upload-and-review**
 *
 * All-in-one: upload file, run multi-agent review pipeline, and return
 * the complete result including all identified mistakes and issues.
 */
export async function uploadAndReview(
  file: File,
  reviewMode: ReviewMode = 'agentic_rag',
): Promise<ReviewResult & { all_mistakes?: any[]; mistakes_summary?: any }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('review_mode', reviewMode);
  return request<ReviewResult & { all_mistakes?: any[]; mistakes_summary?: any }>(
    '/api/review/upload-and-review',
    { method: 'POST', body: formData },
    true,
  );
}

/**
 * **POST /api/review/start**
 *
 * Kick off the multi-agent review pipeline. The review runs in the
 * background; poll `getReviewStatus()` until the status is terminal.
 */
export async function startReview(
  payload: ReviewSubmissionRequest,
): Promise<ReviewStartResponse> {
  return request<ReviewStartResponse>('/api/review/start', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * **GET /api/review/{reviewId}/status**
 *
 * Lightweight status check. Returns review progress without the heavy
 * review payload. Called every 2 s by the frontend polling loop.
 */
export async function getReviewStatus(
  reviewId: string,
): Promise<ReviewStatusResponse> {
  return request<ReviewStatusResponse>(`/api/review/${reviewId}/status`);
}

/**
 * **GET /api/review/{reviewId}/result**
 *
 * Fetch the full review payload including all specialist reviews,
 * meta-review, final report, issues, evidence, and feedback.
 */
export async function getReview(reviewId: string): Promise<ReviewResult> {
  return request<ReviewResult>(`/api/review/${reviewId}/result`);
}

/**
 * **POST /api/review/{reviewId}/feedback**
 *
 * Submit the author's accept / dispute decision on a specific issue.
 * If the review was paused for human input, this triggers a background
 * re-review cycle automatically.
 */
export async function submitFeedback(
  reviewId: string,
  issueId: string,
  decision: 'approve' | 'dispute',
  reason: string,
): Promise<FeedbackResponse> {
  return request<FeedbackResponse>(`/api/review/${reviewId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ issue_id: issueId, decision, reason }),
  });
}

/**
 * **GET /api/papers**
 *
 * Fetch all papers and ongoing reviews stored in the SQLite database.
 */
export async function getPapers(): Promise<PaperSummary[]> {
  return request<PaperSummary[]>('/api/papers');
}

/**
 * **GET /api/papers/{paperId}**
 *
 * Fetch full manuscript details, saved revision versions, and associated review runs.
 */
export async function getPaper(paperId: string): Promise<{
  paper: any;
  versions: any[];
  reviews: any[];
}> {
  return request<{ paper: any; versions: any[]; reviews: any[] }>(`/api/papers/${paperId}`);
}

/**
 * **DELETE /api/papers/{paperId}**
 *
 * Delete a paper and all associated reviews, statuses, and versions from SQLite.
 */
export async function deletePaper(
  paperId: string,
): Promise<{ status: string; message: string }> {
  return request<{ status: string; message: string }>(`/api/papers/${paperId}`, {
    method: 'DELETE',
  });
}

/**
 * **POST /api/papers/{paperId}/version**
 *
 * Record a revision version for a manuscript in the database.
 */
export async function savePaperVersion(
  paperId: string,
  versionData: {
    version: number;
    version_tag: string;
    filename: string;
    file_size?: string;
    total_issues?: number;
    resolved_issues?: number;
  },
): Promise<{ status: string; version: any }> {
  return request<{ status: string; version: any }>(`/api/papers/${paperId}/version`, {
    method: 'POST',
    body: JSON.stringify(versionData),
  });
}

/**
 * **POST /api/review/{paperId}/re-review**
 *
 * Upload a revised manuscript and execute error change verification to check
 * whether previously identified issues were changed and resolved.
 */
export async function reReviewPaper(
  paperId: string,
  file: File,
  reviewMode: ReviewMode = 'agentic_rag',
): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('review_mode', reviewMode);
  return request<any>(
    `/api/review/${paperId}/re-review`,
    { method: 'POST', body: formData },
    true,
  );
}

/**
 * **POST /api/review/{reviewId}/issue/{issueId}/reconsider**
 *
 * Reconsider a flagged issue based on author counter-argument or perspective.
 * If argument is correct -> removes/retracts issue.
 * If argument changes perspective -> reframes description and provides suitable solutions.
 */
export async function reconsiderIssue(
  reviewId: string,
  issueId: string,
  authorArgument: string,
): Promise<{
  status: string;
  outcome: 'remove' | 'reframe' | 'upheld';
  verdict_reason: string;
  updated_issue: any;
  issues: any[];
  message: string;
}> {
  return request(`/api/review/${reviewId}/issue/${issueId}/reconsider`, {
    method: 'POST',
    body: JSON.stringify({ author_argument: authorArgument }),
  });
}

/**
 * **POST /api/review/{reviewId}/generate-report**
 *
 * Generate actionable solutions and 3-step remediation plans for all issues on demand.
 * Invoked when author clicks "Give Report".
 */
export async function generateReport(
  reviewId: string,
): Promise<{
  status: string;
  review_id: string;
  solutions_generated: boolean;
  issues: any[];
  all_mistakes?: any[];
  final_report?: any;
  page_coverage?: Record<number, Record<string, string>>;
  message: string;
}> {
  return request(`/api/review/${reviewId}/generate-report`, {
    method: 'POST',
  });
}

