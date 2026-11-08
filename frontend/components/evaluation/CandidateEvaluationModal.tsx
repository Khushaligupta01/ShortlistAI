"use client";

import React, { useEffect, useState } from "react";
import {
  X,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FileText,
  RotateCw,
  Send,
  Loader2,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  CriterionEvidenceResponse,
  CurrentUser,
  EvaluationResponse,
  RecruiterReviewDecision,
} from "@/lib/types";

interface CandidateEvaluationModalProps {
  evaluationId: string;
  isOpen: boolean;
  onClose: () => void;
  currentUser: CurrentUser | null;
  onEvaluationUpdated?: (updated: EvaluationResponse) => void;
}

export default function CandidateEvaluationModal({
  evaluationId,
  isOpen,
  onClose,
  currentUser,
  onEvaluationUpdated,
}: CandidateEvaluationModalProps) {
  const [evaluation, setEvaluation] = useState<EvaluationResponse | null>(null);
  const [evidence, setEvidence] = useState<CriterionEvidenceResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [recalculating, setRecalculating] = useState(false);
  const [submittingReview, setSubmittingReview] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Review Form State
  const [reviewDecision, setReviewDecision] = useState<RecruiterReviewDecision>("SHORTLIST");
  const [reviewNotes, setReviewNotes] = useState("");

  const isRecruiter =
    currentUser?.role === "recruiter" || currentUser?.role === "delivery_head";

  useEffect(() => {
    if (!isOpen || !evaluationId) return;

    let isMounted = true;
    async function loadData() {
      setLoading(true);
      setError(null);
      setActionSuccess(null);
      try {
        const [evalData, evData] = await Promise.all([
          api.getEvaluation(evaluationId),
          api.getEvaluationEvidence(evaluationId).catch(() => []),
        ]);
        if (!isMounted) return;
        setEvaluation(evalData);
        setEvidence(evData);

        if (evalData.reviews && evalData.reviews.length > 0) {
          const latest = evalData.reviews[evalData.reviews.length - 1];
          setReviewDecision(latest.decision);
          setReviewNotes(latest.notes || "");
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : "Failed to load candidate evaluation");
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [evaluationId, isOpen]);

  // Recalculate deterministic score
  async function handleRecalculate() {
    if (!evaluation) return;
    setRecalculating(true);
    setError(null);
    setActionSuccess(null);
    try {
      const updated = await api.recalculateEvaluation(evaluation.id);
      setEvaluation(updated);
      setActionSuccess("Deterministic scores successfully recalculated.");
      if (onEvaluationUpdated) onEvaluationUpdated(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Recalculation failed");
    } finally {
      setRecalculating(false);
    }
  }

  // Submit recruiter review
  async function handleSubmitReview(e: React.FormEvent) {
    e.preventDefault();
    if (!evaluation) return;
    if (reviewDecision === "UNREVIEWED") {
      setError("Please select a valid recruiter decision.");
      return;
    }

    setSubmittingReview(true);
    setError(null);
    setActionSuccess(null);
    try {
      await api.submitRecruiterReview(evaluation.id, {
        decision: reviewDecision as "SHORTLIST" | "REJECT" | "HOLD" | "REQUEST_INFO",
        notes: reviewNotes.trim() || undefined,
      });
      // Reload evaluation
      const updated = await api.getEvaluation(evaluation.id);
      setEvaluation(updated);
      setActionSuccess(`Candidate marked as ${reviewDecision}.`);
      if (onEvaluationUpdated) onEvaluationUpdated(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to record review decision");
    } finally {
      setSubmittingReview(false);
    }
  }

  if (!isOpen) return null;

  const scoreBadgeBg =
    (evaluation?.normalized_score ?? 0) >= 70
      ? "bg-emerald-500 text-white"
      : (evaluation?.normalized_score ?? 0) >= 50
      ? "bg-amber-500 text-white"
      : "bg-rose-500 text-white";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] overflow-hidden border border-slate-200 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50 shrink-0">
          <div className="flex items-center gap-3">
            <div
              className={`w-11 h-11 rounded-xl flex items-center justify-center font-bold text-base shadow-sm ${scoreBadgeBg}`}
            >
              {evaluation ? Math.round(evaluation.normalized_score) : "--"}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">
                  {evaluation?.candidate_name || "Candidate Evaluation"}
                </h3>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-slate-200 text-slate-700">
                  Scorecard v{evaluation?.scorecard_version ?? 1}
                </span>
                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-full uppercase ${
                    evaluation?.confidence_level === "HIGH"
                      ? "bg-emerald-100 text-emerald-800"
                      : evaluation?.confidence_level === "NEEDS_REVIEW"
                      ? "bg-amber-100 text-amber-800"
                      : "bg-rose-100 text-rose-800"
                  }`}
                >
                  {evaluation?.confidence_level} Confidence
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {evaluation?.candidate_email} •{" "}
                {evaluation?.candidate_location || "Location not specified"} •{" "}
                {evaluation?.candidate_experience_years !== null &&
                evaluation?.candidate_experience_years !== undefined
                  ? `${evaluation.candidate_experience_years} yrs exp`
                  : "Experience not specified"}
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 rounded-lg p-1 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-xs p-3 rounded-xl flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-red-600" />
              <span>{error}</span>
            </div>
          )}

          {actionSuccess && (
            <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs p-3 rounded-xl flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
              <span>{actionSuccess}</span>
            </div>
          )}

          {loading && !evaluation ? (
            <div className="py-12 text-center text-xs text-slate-500">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
              Loading grounded evaluation details...
            </div>
          ) : (
            evaluation && (
              <>
                {/* Score Summary Metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-slate-50 border border-slate-200/60 rounded-xl p-3.5">
                    <div className="text-[11px] font-medium text-slate-500">
                      Normalized Score
                    </div>
                    <div className="text-xl font-bold text-slate-900 mt-1">
                      {evaluation.normalized_score.toFixed(1)} / 100
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      Provisional normalized
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200/60 rounded-xl p-3.5">
                    <div className="text-[11px] font-medium text-slate-500">
                      Raw Score
                    </div>
                    <div className="text-xl font-bold text-slate-900 mt-1">
                      {evaluation.raw_score.toFixed(1)} pts
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      Points actually earned
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200/60 rounded-xl p-3.5">
                    <div className="text-[11px] font-medium text-slate-500">
                      Evidence Coverage
                    </div>
                    <div className="text-xl font-bold text-indigo-600 mt-1">
                      {evaluation.evidence_coverage.toFixed(0)}%
                    </div>
                    <div className="text-[10px] text-slate-400 mt-0.5">
                      Criteria with explicit evidence
                    </div>
                  </div>

                  <div className="bg-slate-50 border border-slate-200/60 rounded-xl p-3.5 flex flex-col justify-between">
                    <div>
                      <div className="text-[11px] font-medium text-slate-500">
                        Audit Provenance
                      </div>
                      <div className="text-xs font-semibold text-slate-800 mt-1 truncate">
                        {evaluation.model_provider || "AI Engine"}
                      </div>
                    </div>
                    {isRecruiter && (
                      <button
                        type="button"
                        disabled={recalculating}
                        onClick={handleRecalculate}
                        className="text-[11px] font-bold text-indigo-600 hover:text-indigo-800 inline-flex items-center gap-1 mt-2 disabled:opacity-50"
                      >
                        <RotateCw
                          className={`w-3 h-3 ${recalculating ? "animate-spin" : ""}`}
                        />
                        Recalculate Deterministically
                      </button>
                    )}
                  </div>
                </div>

                {/* Category Breakdown Progress */}
                <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
                  <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                    Score Breakdown By Category
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
                    {/* Must-Have Skills */}
                    <div className="bg-slate-50 border border-slate-100 p-2.5 rounded-lg">
                      <div className="flex justify-between text-xs font-semibold text-slate-700">
                        <span>Must-Have</span>
                        <span>
                          {evaluation.score_breakdown?.must_have_skills?.awarded ?? 0} /{" "}
                          {evaluation.score_breakdown?.must_have_skills?.max ?? 40}
                        </span>
                      </div>
                      <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-indigo-600 h-1.5 rounded-full"
                          style={{
                            width: `${
                              ((evaluation.score_breakdown?.must_have_skills?.awarded ?? 0) /
                                (evaluation.score_breakdown?.must_have_skills?.max || 40)) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>

                    {/* Experience */}
                    <div className="bg-slate-50 border border-slate-100 p-2.5 rounded-lg">
                      <div className="flex justify-between text-xs font-semibold text-slate-700">
                        <span>Experience</span>
                        <span>
                          {evaluation.score_breakdown?.experience?.awarded ?? 0} /{" "}
                          {evaluation.score_breakdown?.experience?.max ?? 30}
                        </span>
                      </div>
                      <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-indigo-600 h-1.5 rounded-full"
                          style={{
                            width: `${
                              ((evaluation.score_breakdown?.experience?.awarded ?? 0) /
                                (evaluation.score_breakdown?.experience?.max || 30)) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>

                    {/* Notice Period */}
                    <div className="bg-slate-50 border border-slate-100 p-2.5 rounded-lg">
                      <div className="flex justify-between text-xs font-semibold text-slate-700">
                        <span>Notice Period</span>
                        <span>
                          {evaluation.score_breakdown?.notice_period?.awarded ?? 0} /{" "}
                          {evaluation.score_breakdown?.notice_period?.max ?? 15}
                        </span>
                      </div>
                      <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-indigo-600 h-1.5 rounded-full"
                          style={{
                            width: `${
                              ((evaluation.score_breakdown?.notice_period?.awarded ?? 0) /
                                (evaluation.score_breakdown?.notice_period?.max || 15)) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>

                    {/* Location */}
                    <div className="bg-slate-50 border border-slate-100 p-2.5 rounded-lg">
                      <div className="flex justify-between text-xs font-semibold text-slate-700">
                        <span>Location</span>
                        <span>
                          {evaluation.score_breakdown?.location?.awarded ?? 0} /{" "}
                          {evaluation.score_breakdown?.location?.max ?? 10}
                        </span>
                      </div>
                      <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-indigo-600 h-1.5 rounded-full"
                          style={{
                            width: `${
                              ((evaluation.score_breakdown?.location?.awarded ?? 0) /
                                (evaluation.score_breakdown?.location?.max || 10)) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>

                    {/* Nice to Have */}
                    <div className="bg-slate-50 border border-slate-100 p-2.5 rounded-lg">
                      <div className="flex justify-between text-xs font-semibold text-slate-700">
                        <span>Nice-To-Have</span>
                        <span>
                          {evaluation.score_breakdown?.nice_to_have_skills?.awarded ?? 0} /{" "}
                          {evaluation.score_breakdown?.nice_to_have_skills?.max ?? 5}
                        </span>
                      </div>
                      <div className="w-full bg-slate-200 h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-indigo-600 h-1.5 rounded-full"
                          style={{
                            width: `${
                              ((evaluation.score_breakdown?.nice_to_have_skills?.awarded ?? 0) /
                                (evaluation.score_breakdown?.nice_to_have_skills?.max || 5)) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Criterion Evidence Cards */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                      <FileText className="w-4 h-4 text-indigo-600" />
                      Criterion-Level Resume Evidence ({evidence.length})
                    </h4>
                    <span className="text-[11px] text-slate-500">
                      Grounded citations from resume
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {evidence.map((ev) => {
                      const statusColor =
                        ev.evidence_status === "MATCHED"
                          ? "bg-emerald-100 text-emerald-800 border-emerald-200"
                          : ev.evidence_status === "PARTIAL"
                          ? "bg-amber-100 text-amber-800 border-amber-200"
                          : ev.evidence_status === "NOT_MATCHED"
                          ? "bg-rose-100 text-rose-800 border-rose-200"
                          : ev.evidence_status === "UNKNOWN"
                          ? "bg-slate-100 text-slate-700 border-slate-300"
                          : "bg-purple-100 text-purple-800 border-purple-200";

                      return (
                        <div
                          key={ev.id}
                          className="bg-slate-50 border border-slate-200/80 rounded-xl p-4 space-y-2"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-md border uppercase ${statusColor}`}
                              >
                                {ev.evidence_status}
                              </span>
                              <span className="text-xs font-bold text-slate-900">
                                {ev.criterion_name || "Criterion"}
                              </span>
                              {ev.criterion_type && (
                                <span className="text-[10px] text-slate-500 capitalize bg-white px-1.5 py-0.5 rounded border border-slate-200">
                                  {ev.criterion_type.replace(/_/g, " ")}
                                </span>
                              )}
                            </div>

                            <div className="text-xs font-mono font-bold text-slate-800">
                              {ev.awarded_points.toFixed(1)} / {ev.maximum_points.toFixed(1)} pts
                            </div>
                          </div>

                          {/* Supporting Evidence Excerpt */}
                          {ev.evidence_text ? (
                            <div className="bg-white border border-slate-200 rounded-lg p-2.5 text-xs text-slate-700 italic font-serif">
                              &ldquo;{ev.evidence_text}&rdquo;
                            </div>
                          ) : (
                            <div className="text-[11px] text-slate-500 italic">
                              No explicit evidence statement found in resume text.
                            </div>
                          )}

                          {/* Source Location & Explanation */}
                          <div className="flex flex-wrap items-center justify-between text-[11px] text-slate-500 pt-1 border-t border-slate-200/50">
                            <span>
                              {ev.source_reference ? (
                                <span className="font-medium text-slate-700">
                                  Source: {ev.source_reference}
                                </span>
                              ) : (
                                "Location: Parsed Resume Content"
                              )}
                            </span>
                            {ev.explanation && (
                              <span className="text-slate-600">
                                Note: {ev.explanation}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Recruiter Review Action Section */}
                {isRecruiter && (
                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-indigo-600" />
                        Recruiter Decision & Review
                      </h4>
                      <span className="text-[11px] text-slate-500">
                        Decisions are recorded with immutable audit history
                      </span>
                    </div>

                    <form onSubmit={handleSubmitReview} className="space-y-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1.5">
                          Recruiter Decision:
                        </label>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                          {(["SHORTLIST", "REJECT", "HOLD", "REQUEST_INFO"] as const).map(
                            (dec) => (
                              <button
                                key={dec}
                                type="button"
                                onClick={() => setReviewDecision(dec)}
                                className={`py-2 px-3 rounded-lg text-xs font-bold border transition-all ${
                                  reviewDecision === dec
                                    ? dec === "SHORTLIST"
                                      ? "bg-emerald-600 text-white border-emerald-600 shadow-xs"
                                      : dec === "REJECT"
                                      ? "bg-rose-600 text-white border-rose-600 shadow-xs"
                                      : dec === "HOLD"
                                      ? "bg-amber-600 text-white border-amber-600 shadow-xs"
                                      : "bg-indigo-600 text-white border-indigo-600 shadow-xs"
                                    : "bg-white text-slate-700 border-slate-200 hover:border-slate-300"
                                }`}
                              >
                                {dec.replace("_", " ")}
                              </button>
                            )
                          )}
                        </div>
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                          Recruiter Evaluation Notes:
                        </label>
                        <textarea
                          rows={2}
                          value={reviewNotes}
                          onChange={(e) => setReviewNotes(e.target.value)}
                          placeholder="Provide rationale for decision (e.g. strong Spring Boot experience, verified notice period)..."
                          className="w-full text-xs p-2.5 rounded-lg border border-slate-200 bg-white text-slate-800 placeholder-slate-400 focus:outline-indigo-500"
                        />
                      </div>

                      <div className="flex justify-end">
                        <button
                          type="submit"
                          disabled={submittingReview}
                          className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow-xs inline-flex items-center gap-1.5 disabled:opacity-50"
                        >
                          {submittingReview ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                          ) : (
                            <Send className="w-3.5 h-3.5" />
                          )}
                          Save Recruiter Decision
                        </button>
                      </div>
                    </form>
                  </div>
                )}
              </>
            )
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
