"use client";

import { useEffect, useState, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type {
  CandidateDetail,
  CandidateEvaluationHistoryItem,
  CandidateNote,
  ClientOrgOption,
  CurrentUser,
  EvaluationResponse,
  RecruiterReviewDecision,
  ResumeDetail,
} from "@/lib/types";

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function CandidateDetailPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const candidateId = resolvedParams.id;
  const router = useRouter();

  const [user, setUser] = useState<CurrentUser | null>(null);
  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [evaluations, setEvaluations] = useState<CandidateEvaluationHistoryItem[]>([]);
  const [currentEval, setCurrentEval] = useState<EvaluationResponse | null>(null);
  const [notes, setNotes] = useState<CandidateNote[]>([]);
  const [resumeDetails, setResumeDetails] = useState<Record<string, ResumeDetail>>({});

  const [activeTab, setActiveTab] = useState<
    "overview" | "evaluation" | "resumes" | "notes" | "history"
  >("evaluation");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Review decision form state
  const [reviewDecision, setReviewDecision] = useState<RecruiterReviewDecision>("UNREVIEWED");
  const [reviewNotes, setReviewNotes] = useState("");
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [reviewSuccess, setReviewSuccess] = useState(false);

  // Recruiter note state
  const [newNote, setNewNote] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);

  // Submit to Client modal state
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [clientOrgs, setClientOrgs] = useState<ClientOrgOption[]>([]);
  const [selectedClientOrgId, setSelectedClientOrgId] = useState("");
  const [clientNotes, setClientNotes] = useState("");
  const [submittingToClient, setSubmittingToClient] = useState(false);
  const [submitSuccessMsg, setSubmitSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    async function loadData() {
      try {
        const currentUser = await api.getCurrentUser();
        if (currentUser.role === "client_hiring_manager") {
          router.replace("/client");
          return;
        }
        setUser(currentUser);

        const [cand, evalHistory, candNotes] = await Promise.all([
          api.getCandidateDetail(candidateId),
          api.getCandidateEvaluationHistory(candidateId).catch(() => []),
          api.getCandidateNotes(candidateId).catch(() => ({ notes: [], total: 0 })),
        ]);

        setCandidate(cand);
        setEvaluations(evalHistory);
        setNotes(candNotes.notes);

        // Find current evaluation
        const curr = evalHistory.find((e) => e.is_current) || evalHistory[0];
        if (curr) {
          try {
            const fullEval = await api.getEvaluation(curr.id);
            setCurrentEval(fullEval);
            if (fullEval.latest_review_decision) {
              setReviewDecision(fullEval.latest_review_decision);
            }
          } catch {
            // Ignore if full eval cannot be retrieved
          }
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load candidate profile");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [candidateId, router]);

  async function handleLoadResumeText(resumeId: string) {
    if (resumeDetails[resumeId]) return;
    try {
      const detail = await api.getResumeDetail(resumeId);
      setResumeDetails((prev) => ({ ...prev, [resumeId]: detail }));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to load resume text");
    }
  }

  async function handleDownloadResume(resumeId: string) {
    try {
      const { blob, filename } = await api.downloadResumeDocument(resumeId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Download failed");
    }
  }

  async function handleSubmitReview() {
    if (!currentEval || reviewDecision === "UNREVIEWED") return;
    setReviewSubmitting(true);
    try {
      await api.submitRecruiterReview(currentEval.id, {
        decision: reviewDecision,
        notes: reviewNotes.trim() || undefined,
      });
      // Refresh current evaluation
      const updated = await api.getEvaluation(currentEval.id);
      setCurrentEval(updated);
      setReviewSuccess(true);
      setTimeout(() => setReviewSuccess(false), 2000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to record review decision");
    } finally {
      setReviewSubmitting(false);
    }
  }

  async function handleOpenSubmitModal() {
    try {
      const orgs = await api.getClientOrganizations();
      setClientOrgs(orgs);
      if (orgs.length > 0 && !selectedClientOrgId) {
        setSelectedClientOrgId(orgs[0].id);
      }
      setShowSubmitModal(true);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to load client organizations");
    }
  }

  async function handleSubmitToClient() {
    if (!currentEval?.requisition_id || !selectedClientOrgId) return;
    setSubmittingToClient(true);
    try {
      const res = await api.submitCandidateToClient(currentEval.requisition_id, {
        candidate_id: candidateId,
        client_organization_id: selectedClientOrgId,
        recruiter_notes_for_client: clientNotes.trim() || undefined,
      });
      setSubmitSuccessMsg(
        `Submitted successfully! Masked reference: ${res.candidate_reference}. The client can now review this profile.`
      );
      setShowSubmitModal(false);
      setClientNotes("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to submit candidate to client");
    } finally {
      setSubmittingToClient(false);
    }
  }

  async function handleAddNote() {
    if (!newNote.trim()) return;
    setNoteSaving(true);
    try {
      const added = await api.createCandidateNote(
        candidateId,
        newNote.trim(),
        currentEval?.requisition_id || undefined
      );
      setNotes((prev) => [added, ...prev]);
      setNewNote("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to add internal note");
    } finally {
      setNoteSaving(false);
    }
  }

  async function handleUpdateNote(noteId: string) {
    if (!editContent.trim()) return;
    try {
      const updated = await api.updateCandidateNote(noteId, editContent.trim());
      setNotes((prev) => prev.map((n) => (n.id === noteId ? updated : n)));
      setEditingNoteId(null);
      setEditContent("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update note");
    }
  }

  async function handleDeleteNote(noteId: string) {
    if (!confirm("Are you sure you want to delete this confidential note?")) return;
    try {
      await api.deleteCandidateNote(noteId);
      setNotes((prev) => prev.filter((n) => n.id !== noteId));
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete note");
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-slate-500 text-xs">Loading candidate profile & evaluations…</p>
        </div>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="bg-white border border-red-200 rounded-xl p-8 max-w-sm text-center">
          <p className="text-red-600 font-medium mb-4">{error || "Candidate not found"}</p>
          <button
            onClick={() => router.push("/candidates")}
            className="text-indigo-600 text-sm hover:underline"
          >
            ← Back to Candidates
          </button>
        </div>
      </div>
    );
  }

  const score = currentEval ? currentEval.total_score : null;
  const confidence = currentEval?.confidence_level;
  const evidenceList = currentEval?.evidence ?? [];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        {/* Back Link & Title */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs text-slate-500 mb-1">
              <Link href="/candidates" className="hover:text-indigo-600 hover:underline">
                ← Candidate Directory
              </Link>
              {currentEval?.requisition_id && (
                <>
                  <span>•</span>
                  <Link
                    href={`/requisitions/${currentEval.requisition_id}`}
                    className="hover:text-indigo-600 hover:underline"
                  >
                    View Requisition Workspace
                  </Link>
                </>
              )}
            </div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                {candidate.full_name || "Unnamed Candidate"}
              </h1>
              {candidate.is_anonymized ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-900 text-white uppercase tracking-wider">
                  Anonymized / Scrubbed
                </span>
              ) : candidate.consent_status === "WITHDRAWN" ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-800 border border-rose-200 uppercase tracking-wider">
                  Consent Withdrawn (Blocked)
                </span>
              ) : candidate.consent_status === "PENDING" ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200 uppercase tracking-wider">
                  Consent Pending
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Consent Granted
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-slate-500 text-xs mt-1">
              <span>
                Candidate ID: <code className="bg-slate-100 px-1 py-0.5 rounded text-[11px]">{candidate.id}</code>
              </span>
              <span>•</span>
              <Link href="/privacy/consent" className="text-indigo-600 hover:underline">
                Manage Consent
              </Link>
              <span>•</span>
              <Link href="/privacy/data-requests" className="text-indigo-600 hover:underline">
                Data Portability Export
              </Link>
              <span>•</span>
              <Link href="/privacy/deletions" className="text-rose-600 hover:underline">
                Request Erasure
              </Link>
            </div>
          </div>

          {/* Quick Decision Badge & Score Header */}
          <div className="flex items-center gap-4">
            {score !== null && (
              <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-right shadow-xs">
                <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                  Grounded Score
                </span>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xl font-extrabold ${
                      score >= 80 ? "text-emerald-600" : score >= 60 ? "text-blue-600" : "text-amber-600"
                    }`}
                  >
                    {score.toFixed(1)} <span className="text-xs font-normal text-slate-400">/ 100</span>
                  </span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      confidence === "HIGH"
                        ? "bg-emerald-100 text-emerald-800"
                        : confidence === "NEEDS_REVIEW"
                        ? "bg-amber-100 text-amber-800"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {confidence}
                  </span>
                </div>
              </div>
            )}

            <div className="bg-white border border-slate-200 rounded-xl px-4 py-2.5 shadow-xs">
              <span className="text-[10px] uppercase font-bold text-slate-400 block tracking-wider">
                Recruiter Decision
              </span>
              <span
                className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider mt-1 ${
                  reviewDecision === "SHORTLIST"
                    ? "bg-emerald-100 text-emerald-700 border border-emerald-200"
                    : reviewDecision === "REJECT"
                    ? "bg-red-100 text-red-700 border border-red-200"
                    : reviewDecision === "HOLD"
                    ? "bg-amber-100 text-amber-700 border border-amber-200"
                    : reviewDecision === "REQUEST_INFO"
                    ? "bg-blue-100 text-blue-700 border border-blue-200"
                    : "bg-slate-100 text-slate-600 border border-slate-200"
                }`}
              >
                {reviewDecision}
              </span>
            </div>

            {currentEval?.requisition_id && (
              <button
                type="button"
                onClick={handleOpenSubmitModal}
                className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow-sm flex items-center gap-1.5 whitespace-nowrap"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                Submit to Client
              </button>
            )}
          </div>
        </div>

        {submitSuccessMsg && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 p-4 rounded-xl text-xs font-semibold flex items-center justify-between shadow-xs">
            <span>{submitSuccessMsg}</span>
            <Link href="/submissions" className="text-emerald-950 underline ml-2">
              View in Submissions Workspace &rarr;
            </Link>
          </div>
        )}

        {/* Workspace Navigation Tabs */}
        <div className="border-b border-slate-200 flex gap-2">
          {[
            { id: "evaluation", label: "Evidence & Scorecard", count: evidenceList.length },
            { id: "overview", label: "Profile & Experience", count: candidate.employments.length },
            { id: "resumes", label: "Resumes & Text", count: candidate.resumes.length },
            { id: "notes", label: "Internal Notes", count: notes.length },
            { id: "history", label: "Evaluation History", count: evaluations.length },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === tab.id
                  ? "border-indigo-600 text-indigo-600"
                  : "border-transparent text-slate-500 hover:text-slate-800"
              }`}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className="text-[10px] bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded-full font-bold">
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Tab 1: Evidence & Scorecard Evaluation */}
        {activeTab === "evaluation" && (
          <div className="space-y-6">
            {!currentEval ? (
              <div className="bg-white border border-slate-200 rounded-xl p-12 text-center text-slate-500 text-xs">
                No evaluation record found for this candidate. Run an evaluation from the requisition workspace.
              </div>
            ) : (
              <>
                {/* Score breakdown banner & Recruiter Review Action Box */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Score breakdown categories */}
                  <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
                    <h3 className="text-sm font-bold text-slate-800">Deterministic Scoring Breakdown</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {Object.entries(currentEval.score_breakdown || {}).map(([category, val]) => {
                        const cat = val as { awarded?: number; max?: number };
                        return (
                          <div key={category} className="bg-slate-50 border border-slate-100 rounded-lg p-3">
                            <span className="text-[10px] uppercase font-bold text-slate-500 block truncate">
                              {category.replace(/_/g, " ")}
                            </span>
                            <div className="text-base font-bold text-slate-900 mt-1">
                              {cat.awarded ?? 0}{" "}
                              <span className="text-xs text-slate-400 font-normal">/ {cat.max ?? 0}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Coverage & Confidence Meta */}
                    <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-slate-600 border-t border-slate-100">
                      <div>
                        <span className="text-slate-400">Evidence Coverage:</span>{" "}
                        <span className="font-semibold text-slate-800">
                          {Math.round(currentEval.evidence_coverage * 100)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400">Scorecard Version:</span>{" "}
                        <span className="font-semibold text-slate-800">v{currentEval.scorecard_version}</span>
                      </div>
                      <div>
                        <span className="text-slate-400">Evaluated At:</span>{" "}
                        <span className="font-semibold text-slate-800">
                          {currentEval.evaluated_at
                            ? new Date(currentEval.evaluated_at).toLocaleString()
                            : new Date(currentEval.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Recruiter Review Form Box */}
                  <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold text-slate-800">Record Human Review</h3>
                      {reviewSuccess && (
                        <span className="text-[11px] text-emerald-600 font-semibold animate-pulse">
                          ✓ Saved!
                        </span>
                      )}
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 uppercase mb-1">
                        Decision
                      </label>
                      <select
                        value={reviewDecision}
                        onChange={(e) => setReviewDecision(e.target.value as RecruiterReviewDecision)}
                        className="w-full border border-slate-200 rounded-lg p-2 text-xs bg-white text-slate-800 font-medium"
                      >
                        <option value="UNREVIEWED">Unreviewed</option>
                        <option value="SHORTLIST">Shortlist</option>
                        <option value="HOLD">Hold</option>
                        <option value="REJECT">Reject</option>
                        <option value="REQUEST_INFO">Request More Info</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-600 uppercase mb-1">
                        Decision Notes / Rationale
                      </label>
                      <textarea
                        rows={3}
                        placeholder="Reasoning for decision (e.g. strong backend depth, notice period verified)..."
                        value={reviewNotes}
                        onChange={(e) => setReviewNotes(e.target.value)}
                        className="w-full border border-slate-200 rounded-lg p-2.5 text-xs placeholder:text-slate-400"
                      />
                    </div>

                    <button
                      disabled={reviewSubmitting || reviewDecision === "UNREVIEWED"}
                      onClick={handleSubmitReview}
                      className="w-full py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50 transition-colors"
                    >
                      {reviewSubmitting ? "Saving Decision..." : "Save Review Decision"}
                    </button>
                  </div>
                </div>

                {/* Criterion-Level Evidence Cards */}
                <div className="space-y-3">
                  <h3 className="text-sm font-bold text-slate-800">Criterion Evidence & Citations</h3>
                  <div className="grid grid-cols-1 gap-3">
                    {evidenceList.map((ev) => {
                      const isMatch = ev.evidence_status === "MATCHED";
                      const isPartial = ev.evidence_status === "PARTIAL";
                      const isNotMatch = ev.evidence_status === "NOT_MATCHED";
                      const isUnknown = ev.evidence_status === "UNKNOWN";

                      let badgeClass = "bg-slate-100 text-slate-700 border-slate-200";
                      if (isMatch) badgeClass = "bg-emerald-50 text-emerald-700 border-emerald-200";
                      if (isPartial) badgeClass = "bg-blue-50 text-blue-700 border-blue-200";
                      if (isNotMatch) badgeClass = "bg-red-50 text-red-700 border-red-200";
                      if (isUnknown) badgeClass = "bg-amber-50 text-amber-700 border-amber-200";

                      return (
                        <div
                          key={ev.id}
                          className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-900 text-sm">
                                  {ev.criterion_name || "Criterion"}
                                </span>
                                {ev.criterion_type && (
                                  <span className="text-[10px] uppercase font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                                    {ev.criterion_type}
                                  </span>
                                )}
                              </div>
                              {ev.source_reference && (
                                <span className="text-[11px] text-slate-400 block mt-0.5">
                                  Source Citation: {ev.source_reference}
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-3">
                              <span
                                className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${badgeClass}`}
                              >
                                {ev.evidence_status}
                              </span>
                              <div className="text-right">
                                <span className="text-sm font-bold text-slate-900">
                                  {ev.awarded_points} / {ev.maximum_points} pts
                                </span>
                                <span className="text-[10px] text-slate-400 block">
                                  Conf: {Math.round(ev.confidence_score * 100)}%
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Excerpt Citation */}
                          {ev.evidence_text ? (
                            <div className="bg-slate-50 border-l-4 border-indigo-500 p-3 rounded-r-lg">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block mb-1">
                                Resume Supporting Text
                              </span>
                              <p className="text-xs text-slate-700 italic leading-relaxed">
                                &ldquo;{ev.evidence_text}&rdquo;
                              </p>
                            </div>
                          ) : (
                            <div className="text-xs text-slate-400 italic">
                              No explicit text found in resume for this criterion (classified as {ev.evidence_status}).
                            </div>
                          )}

                          {/* Explanation */}
                          {ev.explanation && (
                            <p className="text-xs text-slate-600 leading-relaxed">
                              <span className="font-semibold text-slate-700">Rationale:</span> {ev.explanation}
                            </p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* Tab 2: Profile & Experience */}
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Cols: Employments & Educations */}
            <div className="lg:col-span-2 space-y-6">
              {/* Employments */}
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
                <h3 className="text-sm font-bold text-slate-800">Employment History</h3>
                {candidate.employments.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No structured employment history extracted.</p>
                ) : (
                  <div className="space-y-4">
                    {candidate.employments.map((emp) => (
                      <div key={emp.id} className="border-l-2 border-indigo-200 pl-4 space-y-1">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-bold text-slate-900">{emp.job_title}</h4>
                          <span className="text-[10px] text-slate-400">
                            {emp.start_date || "—"} to {emp.is_current ? "Present" : emp.end_date || "—"}
                          </span>
                        </div>
                        <p className="text-xs text-slate-600 font-medium">{emp.company}</p>
                        {emp.description && (
                          <p className="text-xs text-slate-500 leading-relaxed mt-1">{emp.description}</p>
                        )}
                        {emp.technologies && emp.technologies.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {emp.technologies.map((t, idx) => (
                              <span
                                key={idx}
                                className="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px]"
                              >
                                {t}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Educations */}
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
                <h3 className="text-sm font-bold text-slate-800">Education History</h3>
                {candidate.educations.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">No structured education records extracted.</p>
                ) : (
                  <div className="space-y-3">
                    {candidate.educations.map((edu) => (
                      <div key={edu.id} className="border-l-2 border-slate-200 pl-4 space-y-0.5">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-bold text-slate-900">
                            {edu.qualification || "Degree"} {edu.field_of_study ? `in ${edu.field_of_study}` : ""}
                          </h4>
                          {edu.graduation_year && (
                            <span className="text-[10px] text-slate-400">Class of {edu.graduation_year}</span>
                          )}
                        </div>
                        <p className="text-xs text-slate-600">{edu.institution}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right 1 Col: Contact, Overview & Skills */}
            <div className="space-y-6">
              {/* Contact Card */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">Contact & Info</h3>
                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-slate-400 block text-[10px]">Email</span>
                    <span className="font-semibold text-slate-800">{candidate.email || "—"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Phone</span>
                    <span className="font-semibold text-slate-800">{candidate.phone || "—"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Location</span>
                    <span className="font-semibold text-slate-800">{candidate.location || "—"}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Notice Period</span>
                    <span className="font-semibold text-slate-800">
                      {candidate.notice_period_days !== null && candidate.notice_period_days !== undefined
                        ? `${candidate.notice_period_days} days`
                        : "—"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block text-[10px]">Total Experience</span>
                    <span className="font-semibold text-slate-800">
                      {candidate.total_experience_years !== null && candidate.total_experience_years !== undefined
                        ? `${candidate.total_experience_years} years`
                        : "—"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Skills List */}
              <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500">
                  Extracted Skills ({candidate.skills.length})
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {candidate.skills.map((s) => (
                    <span
                      key={s.id}
                      className="px-2 py-1 bg-indigo-50 border border-indigo-100 text-indigo-700 rounded-md text-xs font-medium"
                    >
                      {s.name}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Resumes & Raw Documents */}
        {activeTab === "resumes" && (
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-slate-800">Associated Resume Documents</h3>
              {candidate.resumes.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No resume files attached.</p>
              ) : (
                <div className="divide-y divide-slate-100">
                  {candidate.resumes.map((r) => {
                    const detail = resumeDetails[r.id];
                    return (
                      <div key={r.id} className="py-4 space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-slate-900">{r.file_name}</span>
                              <span className="text-[10px] font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                                {(r.file_size_bytes / 1024).toFixed(1)} KB
                              </span>
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                                  r.parse_status === "parsed"
                                    ? "bg-emerald-100 text-emerald-800"
                                    : "bg-amber-100 text-amber-800"
                                }`}
                              >
                                {r.parse_status}
                              </span>
                            </div>
                            <span className="text-[11px] text-slate-400 mt-0.5 block">
                              Uploaded {new Date(r.created_at).toLocaleString()} • {r.mime_type}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleLoadResumeText(r.id)}
                              className="text-xs font-medium text-slate-700 hover:text-indigo-600 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded-lg transition-colors"
                            >
                              {detail ? "View Extracted Text" : "Inspect Text"}
                            </button>
                            <button
                              onClick={() => handleDownloadResume(r.id)}
                              className="text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 px-3 py-1.5 rounded-lg transition-colors shadow-xs"
                            >
                              Download File 📥
                            </button>
                          </div>
                        </div>

                        {detail && (
                          <div className="bg-slate-900 text-slate-100 rounded-lg p-4 font-mono text-[11px] max-h-72 overflow-y-auto leading-relaxed space-y-2">
                            <div className="text-slate-400 font-bold uppercase tracking-wider text-[10px]">
                              Normalized Document Text
                            </div>
                            <pre className="whitespace-pre-wrap">
                              {detail.normalized_text || detail.raw_text || "No text available."}
                            </pre>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 4: Internal Recruiter Notes */}
        {activeTab === "notes" && (
          <div className="space-y-6">
            {/* Add note card */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-slate-800">Internal Recruiter Notes</h3>
                <span className="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full font-medium">
                  🔒 Strictly Confidential (Recruiter Only)
                </span>
              </div>
              <textarea
                rows={3}
                placeholder="Record screening remarks, internal assessments, salary expectations, or client presentation strategy..."
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                className="w-full border border-slate-200 rounded-lg p-3 text-xs placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
              />
              <div className="flex justify-end">
                <button
                  disabled={!newNote.trim() || noteSaving}
                  onClick={handleAddNote}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-xs disabled:opacity-50 transition-colors"
                >
                  {noteSaving ? "Saving..." : "Add Note"}
                </button>
              </div>
            </div>

            {/* Notes list */}
            <div className="space-y-3">
              {notes.length === 0 ? (
                <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-slate-400 text-xs">
                  No internal notes recorded yet.
                </div>
              ) : (
                notes.map((n) => (
                  <div
                    key={n.id}
                    className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs border-b border-slate-100 pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-800">{n.author_name || n.author_email}</span>
                        <span className="text-slate-400 text-[10px]">
                          {new Date(n.created_at).toLocaleString()}
                        </span>
                        {n.requisition_title && (
                          <span className="text-[10px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                            Requisition: {n.requisition_title}
                          </span>
                        )}
                      </div>
                      {n.is_author && (
                        <div className="flex items-center gap-2 text-[11px]">
                          <button
                            onClick={() => {
                              setEditingNoteId(n.id);
                              setEditContent(n.content);
                            }}
                            className="text-slate-500 hover:text-indigo-600"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteNote(n.id)}
                            className="text-red-500 hover:text-red-700"
                          >
                            Delete
                          </button>
                        </div>
                      )}
                    </div>

                    {editingNoteId === n.id ? (
                      <div className="space-y-2 pt-2">
                        <textarea
                          rows={3}
                          value={editContent}
                          onChange={(e) => setEditContent(e.target.value)}
                          className="w-full border border-slate-200 rounded-lg p-2 text-xs"
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => setEditingNoteId(null)}
                            className="px-3 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleUpdateNote(n.id)}
                            className="px-3 py-1 text-xs font-semibold text-white bg-indigo-600 rounded"
                          >
                            Save Changes
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-slate-700 whitespace-pre-wrap leading-relaxed">
                        {n.content}
                      </p>
                    )}
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Tab 5: Evaluation History Across Scorecard Versions */}
        {activeTab === "history" && (
          <div className="space-y-4">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-slate-800">
                Multi-Version Evaluation Trail ({evaluations.length})
              </h3>
              {evaluations.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No historical evaluations found.</p>
              ) : (
                <div className="divide-y divide-slate-100">
                  {evaluations.map((ev) => (
                    <div key={ev.id} className="py-4 space-y-2">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900 text-sm">
                              Score: {ev.overall_score.toFixed(1)} / 100
                            </span>
                            {ev.is_current && (
                              <span className="text-[10px] uppercase font-bold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full">
                                Current Active Version
                              </span>
                            )}
                            <span className="text-[10px] font-semibold bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                              Scorecard v{ev.scorecard_version ?? 1}
                            </span>
                          </div>
                          <span className="text-[11px] text-slate-400 mt-0.5 block">
                            Evaluated on {new Date(ev.created_at).toLocaleString()} •{" "}
                            {ev.requisition_title || "General Requisition"}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-slate-600">
                            Decision:{" "}
                            <span className="font-bold text-slate-800">
                              {ev.review_decision || "UNREVIEWED"}
                            </span>
                          </span>
                        </div>
                      </div>

                      {ev.summary && (
                        <p className="text-xs text-slate-600 italic bg-slate-50 p-2.5 rounded-lg">
                          &ldquo;{ev.summary}&rdquo;
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Submit to Client Modal */}
      {showSubmitModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-slate-900">
                  Submit Candidate to Client
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Candidate: <strong>{candidate.full_name}</strong>
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowSubmitModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm"
              >
                ✕
              </button>
            </div>

            {/* Privacy Guarantee Info Box */}
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 text-xs text-emerald-900 space-y-1">
              <p className="font-bold flex items-center gap-1.5">
                <svg className="w-4 h-4 text-emerald-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                Candidate Privacy Shield Active
              </p>
              <p className="text-[11px] text-emerald-800 leading-relaxed">
                The client hiring manager will receive a sanitized profile with an anonymous code (<code>Candidate CND-XXXXX</code>). Name, email, phone, private recruiter notes, and raw resume files are strictly withheld.
              </p>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Select Client Organization
              </label>
              {clientOrgs.length === 0 ? (
                <p className="text-xs text-slate-400 italic">No client organizations configured.</p>
              ) : (
                <select
                  value={selectedClientOrgId}
                  onChange={(e) => setSelectedClientOrgId(e.target.value)}
                  className="w-full border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  {clientOrgs.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.name}
                    </option>
                  ))}
                </select>
              )}
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Recruiter Recommendation Notes for Client (Visible to Client)
              </label>
              <textarea
                rows={3}
                value={clientNotes}
                onChange={(e) => setClientNotes(e.target.value)}
                placeholder="Highlight candidate strengths, salary alignment, or why they are a strong match for this role..."
                className="w-full border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setShowSubmitModal(false)}
                className="text-xs font-semibold text-slate-600 hover:text-slate-800 px-4 py-2"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submittingToClient || !selectedClientOrgId}
                onClick={handleSubmitToClient}
                className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-xs font-bold px-5 py-2.5 rounded-xl transition shadow-sm"
              >
                {submittingToClient ? "Submitting..." : "Confirm Client Submission"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
