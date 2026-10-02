import React, { useState } from 'react';
import { Issue } from '../types';
import { X, CheckCircle, MessageSquare, Sparkles, Loader2 } from 'lucide-react';

interface FeedbackModalProps {
  issue: Issue | null;
  isOpen: boolean;
  onClose: () => void;
  onSubmitFeedback: (issueId: string, feedback: string) => void;
  onReconsiderIssue?: (issueId: string, feedback: string) => Promise<any>;
}

export const FeedbackModal: React.FC<FeedbackModalProps> = ({
  issue,
  isOpen,
  onClose,
  onSubmitFeedback,
  onReconsiderIssue,
}) => {
  const [feedback, setFeedback] = useState(issue?.disputeReason || '');
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [isReconsidering, setIsReconsidering] = useState(false);
  const [reconsiderMessage, setReconsiderMessage] = useState<string | null>(null);

  if (!isOpen || !issue) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedback.trim()) return;
    onSubmitFeedback(issue.id, feedback);
    setIsSubmitted(true);
    setTimeout(() => {
      setIsSubmitted(false);
      onClose();
    }, 1200);
  };

  const handleReconsiderSubmit = async () => {
    if (!feedback.trim() || !onReconsiderIssue) return;
    onSubmitFeedback(issue.id, feedback);
    setIsReconsidering(true);
    try {
      const res = await onReconsiderIssue(issue.id, feedback);
      if (res && res.outcome) {
        if (res.outcome === 'remove') {
          setReconsiderMessage('Issue dismissed and removed! Author argument verified as correct.');
        } else if (res.outcome === 'reframe') {
          setReconsiderMessage('Perspective reframed! Issue description and solutions updated.');
        } else {
          setReconsiderMessage('Argument recorded. Issue upheld with reviewer rationale.');
        }
      }
      setIsSubmitted(true);
      setTimeout(() => {
        setIsSubmitted(false);
        setIsReconsidering(false);
        setReconsiderMessage(null);
        onClose();
      }, 2000);
    } catch (err) {
      console.error('Reconsider error:', err);
      setIsSubmitted(true);
      setTimeout(() => {
        setIsSubmitted(false);
        setIsReconsidering(false);
        onClose();
      }, 1200);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-2xs">
      <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-lg w-full p-6 text-left relative animate-in fade-in zoom-in-95 duration-150">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 p-1 rounded-md"
        >
          <X className="w-5 h-5" />
        </button>

        {isSubmitted ? (
          <div className="py-8 text-center space-y-2">
            <CheckCircle className="w-10 h-10 text-emerald-600 mx-auto" />
            <h3 className="text-base font-semibold text-slate-900">Feedback submitted</h3>
            <p className="text-xs text-slate-600 max-w-sm mx-auto leading-relaxed">
              {reconsiderMessage ||
                'The issue has been marked as disputed with your explanation recorded.'}
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex items-center space-x-2 text-slate-900">
              <MessageSquare className="w-5 h-5 text-amber-600" />
              <h3 className="text-base font-semibold">Dispute Potential Issue</h3>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
              <div className="font-semibold text-slate-800">{issue.title}</div>
              <div className="text-slate-500">
                {issue.reviewer} · Page {issue.page} ({issue.section})
              </div>
            </div>

            <div>
              <label htmlFor="dispute-reason" className="block text-xs font-semibold text-slate-800 mb-1.5">
                Why do you disagree?
              </label>
              <textarea
                id="dispute-reason"
                rows={4}
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="Explain why this flagged item is intentional, already addressed in another section, or outside the study's scope..."
                className="w-full text-xs text-slate-900 border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-1 focus:ring-slate-900 focus:border-slate-900 placeholder:text-slate-400"
                required
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Tip: The AI evaluates your feedback to determine whether to delete the issue (if verified correct or no problem) or change the perspective and solution.
              </p>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-3 py-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!feedback.trim() || isReconsidering}
                className="px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-300 hover:bg-slate-50 disabled:bg-slate-100 rounded-lg transition-colors shadow-2xs cursor-pointer"
              >
                Save Feedback
              </button>
              {onReconsiderIssue && (
                <button
                  type="button"
                  onClick={handleReconsiderSubmit}
                  disabled={!feedback.trim() || isReconsidering}
                  className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 rounded-lg transition-colors shadow-2xs cursor-pointer"
                >
                  {isReconsidering ? (
                    <>
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>Evaluating Feedback...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>Submit & Reconsider with AI</span>
                    </>
                  )}
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
