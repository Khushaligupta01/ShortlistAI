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
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to download resume file");
    }
  }

  async function handleSubmitReview() {
    if (!currentEval) return;
    setReviewSubmitting(true);
    setReviewSuccess(false);
    try {
      await api.submitRecruiterReview(currentEval.id, {
        decision: reviewDecision as "SHORTLIST" | "REJECT" | "HOLD" | "REQUEST_INFO",
        notes: reviewNotes.trim() || undefined,
      });
      const updated = await api.getEvaluation(currentEval.id);
      setCurrentEval(updated);
      setReviewSuccess(true);
      setTimeout(() => setReviewSuccess(false), 2000);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to record recruiter review");
    } finally {
      setReviewSubmitting(false);
    }
  }

  async function handleOpenSubmitModal() {
    try {
      const orgs = await api.getClientOrganizations();
      setClientOrgs(orgs);
      if (orgs.length > 0) {
        setSelectedClientOrgId(orgs[0].id);
      }
      setShowSubmitModal(true);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to fetch client organizations");
    }
  }

  async function handleSubmitToClient() {
    if (!currentEval?.requisition_id || !selectedClientOrgId) return;
    setSubmittingToClient(true);
    try {
      await api.submitCandidateToClient(currentEval.requisition_id, {
        candidate_id: candidateId,
        client_organization_id: selectedClientOrgId,
        recruiter_notes_for_client: clientNotes.trim() || undefined,
      });
      setShowSubmitModal(false);
      setClientNotes("");
      setSubmitSuccessMsg("Candidate submitted successfully to client hiring portal!");
      setTimeout(() => setSubmitSuccessMsg(null), 6000);
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
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-[#756653] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-[#6F6A61] text-xs font-medium">Loading candidate profile & evaluations…</p>
        </div>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="bg-[#FFFFFF] border border-[#EFC2C2] rounded-2xl p-8 max-w-sm text-center shadow-xs">
          <p className="text-[#7A2525] font-semibold mb-4 text-sm">{error || "Candidate not found"}</p>
          <button
            onClick={() => router.push("/candidates")}
            className="text-[#756653] text-xs font-semibold hover:underline"
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
    <div className="min-h-screen bg-[#FAF9F6] flex flex-col selection:bg-[#EDE5D9] selection:text-[#292722]">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        {/* Back Link & Title */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#E8E2D8]">
          <div>
            <div className="flex items-center gap-2 text-xs text-[#6F6A61] mb-1">
              <Link href="/candidates" className="hover:text-[#756653] hover:underline font-medium">
                ← Candidate Directory
              </Link>
              {currentEval?.requisition_id && (
                <>
                  <span className="text-[#918A80]">•</span>
                  <Link
                    href={`/requisitions/${currentEval.requisition_id}`}
                    className="hover:text-[#756653] hover:underline font-medium"
                  >
                    View Requisition Workspace
                  </Link>
                </>
              )}
            </div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-[#292722] tracking-tight">
                {candidate.full_name || "Unnamed Candidate"}
              </h1>
              {candidate.is_anonymized ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#292722] text-[#FAF9F6] uppercase tracking-wider">
                  Anonymized / Scrubbed
                </span>
              ) : candidate.consent_status === "WITHDRAWN" ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#FDF0F0] text-[#7A2525] border border-[#EFC2C2] uppercase tracking-wider">
                  Consent Withdrawn (Blocked)
                </span>
              ) : candidate.consent_status === "PENDING" ? (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#FDF6E7] text-[#7A5212] border border-[#F1DCAC] uppercase tracking-wider">
                  Consent Pending
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[#EEF6F0] text-[#2A5A35] border border-[#C4E2CC]">
                  Consent Granted
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-[#6F6A61] text-xs mt-1">
              <span>
                Candidate ID: <code className="bg-[#F5F1EA] px-1 py-0.5 rounded text-[11px] font-mono border border-[#E8E2D8]">{candidate.id}</code>
              </span>
              <span className="text-[#918A80]">•</span>
              <Link href="/privacy/consent" className="text-[#756653] hover:underline font-medium">
                Manage Consent
              </Link>
              <span className="text-[#918A80]">•</span>
              <Link href="/privacy/data-requests" className="text-[#756653] hover:underline font-medium">
                Data Portability Export
              </Link>
              <span className="text-[#918A80]">•</span>
              <Link href="/privacy/deletions" className="text-[#7A2525] hover:underline font-medium">
                Request Erasure
              </Link>
            </div>
          </div>

          {/* Quick Decision Badge & Score Header */}
          <div className="flex items-center gap-3">
            {score !== null && (
              <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl px-4 py-2 text-right shadow-xs">
                <span className="text-[10px] uppercase font-bold text-[#918A80] block tracking-wider">
                  Grounded Score
                </span>
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xl font-extrabold ${
                      score >= 80 ? "text-[#2A5A35]" : score >= 60 ? "text-[#264D6B]" : "text-[#7A5212]"
                    }`}
                  >
                    {score.toFixed(1)} <span className="text-xs font-normal text-[#918A80]">/ 100</span>
                  </span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      confidence === "HIGH"
                        ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                        : confidence === "NEEDS_REVIEW"
                        ? "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                        : "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]"
                    }`}
                  >
                    {confidence}
                  </span>
                </div>
              </div>
            )}

            <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl px-4 py-2 shadow-xs">
              <span className="text-[10px] uppercase font-bold text-[#918A80] block tracking-wider">
                Recruiter Decision
              </span>
              <span
                className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider mt-1 border ${
                  reviewDecision === "SHORTLIST"
                    ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                    : reviewDecision === "REJECT"
                    ? "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]"
                    : reviewDecision === "HOLD"
                    ? "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                    : reviewDecision === "REQUEST_INFO"
                    ? "bg-[#EDF4F9] text-[#264D6B] border-[#C6DDEE]"
                    : "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]"
                }`}
              >
                {reviewDecision}
              </span>
            </div>

            {currentEval?.requisition_id && (
              <button
                type="button"
                onClick={handleOpenSubmitModal}
                className="bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] text-xs font-semibold px-4 py-2.5 rounded-xl transition shadow-2xs flex items-center gap-1.5 whitespace-nowrap"
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
          <div className="bg-[#EEF6F0] border border-[#C4E2CC] text-[#2A5A35] p-4 rounded-2xl text-xs font-semibold flex items-center justify-between shadow-xs">
            <span>{submitSuccessMsg}</span>
            <Link href="/submissions" className="text-[#2A5A35] underline ml-2 font-bold">
              View in Submissions Workspace &rarr;
            </Link>
          </div>
        )}

        {/* Workspace Navigation Tabs */}
        <div className="border-b border-[#E8E2D8] flex gap-2">
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
                  ? "border-[#756653] text-[#756653] bg-[#F5F1EA]/50 rounded-t-lg"
                  : "border-transparent text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
              }`}
            >
              {tab.label}
              {tab.count !== undefined && (
                <span className="text-[10px] bg-[#EDE5D9] text-[#756653] px-1.5 py-0.2 rounded-full font-bold">
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
              <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl p-12 text-center text-[#6F6A61] text-xs">
                No evaluation record found for this candidate. Run an evaluation from the requisition workspace.
              </div>
            ) : (
              <>
                {/* Score breakdown banner & Recruiter Review Action Box */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Score breakdown categories */}
                  <div className="lg:col-span-2 bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-6 shadow-xs space-y-4">
                    <h3 className="text-sm font-bold text-[#292722]">Deterministic Scoring Breakdown</h3>
                    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                      {Object.entries(currentEval.score_breakdown || {}).map(([category, val]) => {
                        const cat = val as { awarded?: number; max?: number };
                        return (
                          <div key={category} className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-3">
                            <span className="text-[10px] uppercase font-bold text-[#6F6A61] block truncate">
                              {category.replace(/_/g, " ")}
                            </span>
                            <div className="text-base font-bold text-[#292722] mt-1">
                              {cat.awarded ?? 0}{" "}
                              <span className="text-xs text-[#918A80] font-normal">/ {cat.max ?? 0}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {/* Coverage & Confidence Meta */}
                    <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-[#6F6A61] border-t border-[#E8E2D8]">
                      <div>
                        <span className="text-[#918A80]">Evidence Coverage:</span>{" "}
                        <span className="font-semibold text-[#292722]">
                          {Math.round(currentEval.evidence_coverage * 100)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-[#918A80]">Scorecard Version:</span>{" "}
                        <span className="font-semibold text-[#292722]">v{currentEval.scorecard_version}</span>
                      </div>
                      <div>
                        <span className="text-[#918A80]">Evaluated At:</span>{" "}
                        <span className="font-semibold text-[#292722]">
                          {currentEval.evaluated_at
                            ? new Date(currentEval.evaluated_at).toLocaleString()
                            : new Date(currentEval.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Recruiter Review Form Box */}
                  <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-6 shadow-xs space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-bold text-[#292722]">Record Human Review</h3>
                      {reviewSuccess && (
                        <span className="text-[11px] text-[#2A5A35] font-semibold animate-pulse">
                          ✓ Saved!
                        </span>
                      )}
                    </div>
                    <div>
                      <label className="block text-[11px] font-semibold text-[#6F6A61] uppercase mb-1">
                        Decision
                      </label>
                      <select
                        value={reviewDecision}
                        onChange={(e) => setReviewDecision(e.target.value as RecruiterReviewDecision)}
                        className="w-full border border-[#E8E2D8] rounded-xl p-2 text-xs bg-[#FFFFFF] text-[#292722] font-medium focus:border-[#756653]"
                      >
                        <option value="UNREVIEWED">Unreviewed</option>
                        <option value="SHORTLIST">Shortlist</option>
                        <option value="HOLD">Hold</option>
                        <option value="REJECT">Reject</option>
                        <option value="REQUEST_INFO">Request More Info</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-[#6F6A61] uppercase mb-1">
                        Decision Notes / Rationale
                      </label>
                      <textarea
                        rows={3}
                        placeholder="Reasoning for decision (e.g. strong backend depth, notice period verified)..."
                        value={reviewNotes}
                        onChange={(e) => setReviewNotes(e.target.value)}
                        className="w-full border border-[#E8E2D8] rounded-xl p-2.5 text-xs bg-[#FFFFFF] text-[#292722] placeholder:text-[#AAA49B] focus:border-[#756653]"
                      />
                    </div>

                    <button
                      disabled={reviewSubmitting || reviewDecision === "UNREVIEWED"}
                      onClick={handleSubmitReview}
                      className="w-full py-2 bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] rounded-xl text-xs font-semibold shadow-2xs disabled:opacity-50 transition-colors"
                    >
                      {reviewSubmitting ? "Saving Decision..." : "Save Review Decision"}
                    </button>
                  </div>
                </div>

                {/* Criterion-Level Evidence Cards */}
                <div className="space-y-3">
                  <h3 className="text-sm font-bold text-[#292722]">Criterion Evidence & Citations</h3>
                  <div className="grid grid-cols-1 gap-3">
                    {evidenceList.map((ev) => {
                      const isMatch = ev.evidence_status === "MATCHED";
                      const isPartial = ev.evidence_status === "PARTIAL";
                      const isNotMatch = ev.evidence_status === "NOT_MATCHED";
                      const isUnknown = ev.evidence_status === "UNKNOWN";

                      let badgeClass = "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]";
                      if (isMatch) badgeClass = "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]";
                      if (isPartial) badgeClass = "bg-[#EDF4F9] text-[#264D6B] border-[#C6DDEE]";
                      if (isNotMatch) badgeClass = "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]";
                      if (isUnknown) badgeClass = "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]";

                      return (
                        <div
                          key={ev.id}
                          className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs space-y-3"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E8E2D8] pb-3">
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-[#292722] text-sm">
                                  {ev.criterion_name || "Criterion"}
                                </span>
                                {ev.criterion_type && (
                                  <span className="text-[10px] uppercase font-semibold bg-[#F5F1EA] text-[#6F6A61] px-2 py-0.5 rounded border border-[#E8E2D8]">
                                    {ev.criterion_type}
                                  </span>
                                )}
                              </div>
                              {ev.source_reference && (
                                <span className="text-[11px] text-[#918A80] block mt-0.5">
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
                                <span className="text-sm font-bold text-[#292722]">
                                  {ev.awarded_points} / {ev.maximum_points} pts
                                </span>
                                <span className="text-[10px] text-[#918A80] block">
                                  Conf: {Math.round(ev.confidence_score * 100)}%
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Excerpt Citation */}
                          {ev.evidence_text ? (
                            <div className="bg-[#F5F1EA] border-l-4 border-[#756653] p-3 rounded-r-xl">
                              <span className="text-[10px] font-bold uppercase tracking-wider text-[#6F6A61] block mb-1">
                                Resume Supporting Text
                              </span>
                              <p className="text-xs text-[#292722] italic leading-relaxed">
                                &ldquo;{ev.evidence_text}&rdquo;
                              </p>
                            </div>
                          ) : (
                            <div className="text-xs text-[#918A80] italic">
                              No explicit text found in resume for this criterion (classified as {ev.evidence_status}).
                            </div>
                          )}

                          {/* Explanation */}
                          {ev.explanation && (
                            <p className="text-xs text-[#6F6A61] leading-relaxed">
                              <span className="font-semibold text-[#292722]">Rationale:</span> {ev.explanation}
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
              <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-6 shadow-xs space-y-4">
                <h3 className="text-sm font-bold text-[#292722]">Employment History</h3>
                {candidate.employments.length === 0 ? (
                  <p className="text-xs text-[#918A80] italic">No structured employment history extracted.</p>
                ) : (
                  <div className="space-y-4">
                    {candidate.employments.map((emp) => (
                      <div key={emp.id} className="border-l-2 border-[#D9D1C5] pl-4 space-y-1">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-bold text-[#292722]">{emp.job_title}</h4>
                          <span className="text-[10px] text-[#918A80]">
                            {emp.start_date || "—"} to {emp.is_current ? "Present" : emp.end_date || "—"}
                          </span>
                        </div>
                        <p className="text-xs text-[#6F6A61] font-medium">{emp.company}</p>
                        {emp.description && (
                          <p className="text-xs text-[#6F6A61] leading-relaxed mt-1">{emp.description}</p>
                        )}
                        {emp.technologies && emp.technologies.length > 0 && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {emp.technologies.map((t, idx) => (
                              <span
                                key={idx}
                                className="bg-[#F5F1EA] text-[#6F6A61] border border-[#E8E2D8] px-1.5 py-0.5 rounded text-[10px]"
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
              <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-6 shadow-xs space-y-4">
                <h3 className="text-sm font-bold text-[#292722]">Education History</h3>
                {candidate.educations.length === 0 ? (
                  <p className="text-xs text-[#918A80] italic">No structured education records extracted.</p>
                ) : (
                  <div className="space-y-3">
                    {candidate.educations.map((edu) => (
                      <div key={edu.id} className="border-l-2 border-[#D9D1C5] pl-4 space-y-0.5">
                        <div className="flex items-center justify-between">
                          <h4 className="text-xs font-bold text-[#292722]">
                            {edu.qualification || "Degree"} {edu.field_of_study ? `in ${edu.field_of_study}` : ""}
                          </h4>
                          {edu.graduation_year && (
                            <span className="text-[10px] text-[#918A80]">Class of {edu.graduation_year}</span>
                          )}
                        </div>
                        <p className="text-xs text-[#6F6A61]">{edu.institution}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Right 1 Col: Contact, Overview & Skills */}
            <div className="space-y-6">
              {/* Contact Card */}
              <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#6F6A61]">Contact & Info</h3>
                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-[#918A80] block text-[10px]">Email</span>
                    <span className="font-semibold text-[#292722]">{candidate.email || "—"}</span>
                  </div>
                  <div>
                    <span className="text-[#918A80] block text-[10px]">Phone</span>
                    <span className="font-semibold text-[#292722]">{candidate.phone || "—"}</span>
                  </div>
                  <div>
                    <span className="text-[#918A80] block text-[10px]">Location</span>
                    <span className="font-semibold text-[#292722]">{candidate.location || "—"}</span>
                  </div>
                  <div>
                    <span className="text-[#918A80] block text-[10px]">Notice Period</span>
                    <span className="font-semibold text-[#292722]">
                      {candidate.notice_period_days !== null && candidate.notice_period_days !== undefined
                        ? `${candidate.notice_period_days} days`
                        : "—"}
                    </span>
                  </div>
                  <div>
                    <span className="text-[#918A80] block text-[10px]">Total Experience</span>
                    <span className="font-semibold text-[#292722]">
                      {candidate.total_experience_years !== null && candidate.total_experience_years !== undefined
                        ? `${candidate.total_experience_years} years`
                        : "—"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Skills List */}
              <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-[#6F6A61]">
                  Extracted Skills ({candidate.skills.length})
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {candidate.skills.map((s) => (
                    <span
                      key={s.id}
                      className="px-2 py-1 bg-[#F5F1EA] border border-[#E8E2D8] text-[#292722] rounded-lg text-xs font-medium"
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
            <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-6 shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-[#292722]">Associated Resume Documents</h3>
              {candidate.resumes.length === 0 ? (
                <p className="text-xs text-[#918A80] italic">No resume files attached.</p>
              ) : (
                <div className="divide-y divide-[#EFEAE2]">
                  {candidate.resumes.map((r) => {
                    const detail = resumeDetails[r.id];
                    return (
                      <div key={r.id} className="py-4 space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-sm font-semibold text-[#292722]">{r.file_name}</span>
                              <span className="text-[10px] font-semibold bg-[#F5F1EA] text-[#6F6A61] px-2 py-0.5 rounded border border-[#E8E2D8]">
                                {(r.file_size_bytes / 1024).toFixed(1)} KB
                              </span>
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                                  r.parse_status === "parsed"
                                    ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                                    : "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                                }`}
                              >
                                {r.parse_status}
                              </span>
                            </div>
                            <span className="text-[11px] text-[#918A80] mt-0.5 block">
                              Uploaded {new Date(r.created_at).toLocaleString()} • {r.mime_type}
                            </span>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => handleLoadResumeText(r.id)}
                              className="text-xs font-medium text-[#292722] hover:bg-[#EEE8DD] bg-[#F5F1EA] border border-[#E8E2D8] px-3 py-1.5 rounded-xl transition-colors"
                            >
                              {detail ? "View Extracted Text" : "Inspect Text"}
                            </button>
                            <button
                              onClick={() => handleDownloadResume(r.id)}
                              className="text-xs font-semibold text-[#FAF9F6] bg-[#756653] hover:bg-[#5F5243] px-3 py-1.5 rounded-xl transition-colors shadow-2xs"
                            >
                              Download File 📥
                            </button>
                          </div>
                        </div>

                        {detail && (
                          <div className="bg-[#292722] text-[#FAF9F6] rounded-xl p-4 font-mono text-[11px] max-h-72 overflow-y-auto leading-relaxed space-y-2">
                            <div className="text-[#AAA49B] font-bold uppercase tracking-wider text-[10px]">
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
            <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-6 shadow-xs space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-bold text-[#292722]">Internal Recruiter Notes</h3>
                <span className="text-[11px] text-[#7A5212] bg-[#FDF6E7] border border-[#F1DCAC] px-2 py-0.5 rounded-full font-medium">
                  🔒 Strictly Confidential (Recruiter Only)
                </span>
              </div>
              <textarea
                rows={3}
                placeholder="Record screening remarks, internal assessments, salary expectations, or client presentation strategy..."
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                className="w-full border border-[#E8E2D8] rounded-xl p-3 text-xs bg-[#FFFFFF] text-[#292722] placeholder:text-[#AAA49B] focus:border-[#756653]"
              />
              <div className="flex justify-end">
                <button
                  disabled={!newNote.trim() || noteSaving}
                  onClick={handleAddNote}
                  className="px-4 py-2 bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] rounded-xl text-xs font-semibold shadow-2xs disabled:opacity-50 transition-colors"
                >
                  {noteSaving ? "Saving..." : "Add Note"}
                </button>
              </div>
            </div>

            {/* Notes list */}
            <div className="space-y-3">
              {notes.length === 0 ? (
                <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl p-8 text-center text-[#918A80] text-xs">
                  No internal notes recorded yet.
                </div>
              ) : (
                notes.map((n) => (
                  <div
                    key={n.id}
                    className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs space-y-2"
                  >
                    <div className="flex items-center justify-between text-xs border-b border-[#E8E2D8] pb-2">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-[#292722]">{n.author_name || n.author_email}</span>
                        <span className="text-[#918A80] text-[10px]">
                          {new Date(n.created_at).toLocaleString()}
                        </span>
                        {n.requisition_title && (
                          <span className="text-[10px] bg-[#F5F1EA] text-[#6F6A61] border border-[#E8E2D8] px-2 py-0.5 rounded">
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
                            className="text-[#6F6A61] hover:text-[#756653]"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteNote(n.id)}
                            className="text-[#7A2525] hover:text-[#5F1B1B]"
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
                          className="w-full border border-[#E8E2D8] rounded-xl p-2 text-xs bg-[#FFFFFF] text-[#292722]"
                        />
                        <div className="flex justify-end gap-2">
                          <button
                            onClick={() => setEditingNoteId(null)}
                            className="px-3 py-1 text-xs text-[#6F6A61] hover:bg-[#F5F1EA] rounded-lg"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleUpdateNote(n.id)}
                            className="px-3 py-1 text-xs font-semibold text-[#FAF9F6] bg-[#756653] hover:bg-[#5F5243] rounded-lg shadow-2xs"
                          >
                            Save Changes
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-xs text-[#292722] whitespace-pre-wrap leading-relaxed">
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
            <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-6 shadow-xs space-y-4">
              <h3 className="text-sm font-bold text-[#292722]">
                Multi-Version Evaluation Trail ({evaluations.length})
              </h3>
              {evaluations.length === 0 ? (
                <p className="text-xs text-[#918A80] italic">No historical evaluations found.</p>
              ) : (
                <div className="divide-y divide-[#EFEAE2]">
                  {evaluations.map((ev) => (
                    <div key={ev.id} className="py-4 space-y-2">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-[#292722] text-sm">
                              Score: {ev.overall_score.toFixed(1)} / 100
                            </span>
                            {ev.is_current && (
                              <span className="text-[10px] uppercase font-bold bg-[#EEF6F0] text-[#2A5A35] border border-[#C4E2CC] px-2 py-0.5 rounded-full">
                                Current Active Version
                              </span>
                            )}
                            <span className="text-[10px] font-semibold bg-[#F5F1EA] text-[#6F6A61] border border-[#E8E2D8] px-2 py-0.5 rounded">
                              Scorecard v{ev.scorecard_version ?? 1}
                            </span>
                          </div>
                          <span className="text-[11px] text-[#918A80] mt-0.5 block">
                            Evaluated on {new Date(ev.created_at).toLocaleString()} •{" "}
                            {ev.requisition_title || "General Requisition"}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-xs font-medium text-[#6F6A61]">
                            Decision:{" "}
                            <span className="font-bold text-[#292722]">
                              {ev.review_decision || "UNREVIEWED"}
                            </span>
                          </span>
                        </div>
                      </div>

                      {ev.summary && (
                        <p className="text-xs text-[#6F6A61] italic bg-[#F5F1EA] p-3 rounded-xl border border-[#E8E2D8]">
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
        <div className="fixed inset-0 bg-[#292722]/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] max-w-lg w-full p-6 shadow-xl space-y-4">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="text-lg font-bold text-[#292722]">
                  Submit Candidate to Client
                </h3>
                <p className="text-xs text-[#6F6A61] mt-0.5">
                  Candidate: <strong className="text-[#292722]">{candidate.full_name}</strong>
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowSubmitModal(false)}
                className="text-[#918A80] hover:text-[#292722] text-sm"
              >
                ✕
              </button>
            </div>

            {/* Privacy Guarantee Info Box */}
            <div className="bg-[#EEF6F0] border border-[#C4E2CC] rounded-xl p-3.5 text-xs text-[#2A5A35] space-y-1">
              <p className="font-bold flex items-center gap-1.5">
                <svg className="w-4 h-4 text-[#2A5A35] shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
                Candidate Privacy Shield Active
              </p>
              <p className="text-[11px] text-[#2A5A35] leading-relaxed">
                The client hiring manager will receive a sanitized profile with an anonymous code (<code>Candidate CND-XXXXX</code>). Name, email, phone, private recruiter notes, and raw resume files are strictly withheld.
              </p>
            </div>

            <div>
              <label className="text-xs font-semibold text-[#292722] block mb-1">
                Select Client Organization
              </label>
              {clientOrgs.length === 0 ? (
                <p className="text-xs text-[#918A80] italic">No client organizations configured.</p>
              ) : (
                <select
                  value={selectedClientOrgId}
                  onChange={(e) => setSelectedClientOrgId(e.target.value)}
                  className="w-full border border-[#E8E2D8] rounded-xl p-2.5 text-xs bg-[#FFFFFF] text-[#292722] focus:border-[#756653]"
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
              <label className="text-xs font-semibold text-[#292722] block mb-1">
                Recruiter Recommendation Notes for Client (Visible to Client)
              </label>
              <textarea
                rows={3}
                value={clientNotes}
                onChange={(e) => setClientNotes(e.target.value)}
                placeholder="Highlight candidate strengths, salary alignment, or why they are a strong match for this role..."
                className="w-full border border-[#E8E2D8] rounded-xl p-2.5 text-xs bg-[#FFFFFF] text-[#292722] placeholder:text-[#AAA49B] focus:border-[#756653]"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#E8E2D8]">
              <button
                type="button"
                onClick={() => setShowSubmitModal(false)}
                className="text-xs font-semibold text-[#6F6A61] hover:text-[#292722] px-4 py-2"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submittingToClient || !selectedClientOrgId}
                onClick={handleSubmitToClient}
                className="bg-[#756653] hover:bg-[#5F5243] disabled:opacity-50 text-[#FAF9F6] text-xs font-semibold px-5 py-2.5 rounded-xl transition shadow-2xs"
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
