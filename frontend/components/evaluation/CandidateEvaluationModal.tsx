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
      ? "bg-[#EEF6F0] text-[#2A5A35] border border-[#C4E2CC]"
      : (evaluation?.normalized_score ?? 0) >= 50
      ? "bg-[#FDF6E7] text-[#7A5212] border border-[#F1DCAC]"
      : "bg-[#FDF0F0] text-[#7A2525] border border-[#EFC2C2]";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#292722]/50 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-[#FFFFFF] rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] overflow-hidden border border-[#E8E2D8] flex flex-col text-[#292722]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E8E2D8] bg-[#F5F1EA] shrink-0">
          <div className="flex items-center gap-3">
            <div
              className={`w-11 h-11 rounded-xl flex items-center justify-center font-serif font-bold text-base shadow-sm ${scoreBadgeBg}`}
            >
              {evaluation ? Math.round(evaluation.normalized_score) : "--"}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-serif font-bold text-[#292722]">
                  {evaluation?.candidate_name || "Candidate Evaluation"}
                </h3>
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#EEE8DD] text-[#292722] border border-[#D9D1C5]">
                  Scorecard v{evaluation?.scorecard_version ?? 1}
                </span>
                <span
                  className={`text-[11px] font-semibold px-2 py-0.5 rounded-full uppercase border ${
                    evaluation?.confidence_level === "HIGH"
                      ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                      : evaluation?.confidence_level === "NEEDS_REVIEW"
                      ? "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                      : "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]"
                  }`}
                >
                  {evaluation?.confidence_level} Confidence
                </span>
              </div>
              <p className="text-xs text-[#6F6A61]">
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
            className="text-[#918A80] hover:text-[#292722] rounded-lg p-1 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 overflow-y-auto flex-1">
          {error && (
            <div className="bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] text-xs p-3 rounded-xl flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-[#7A2525]" />
              <span>{error}</span>
            </div>
          )}

          {actionSuccess && (
            <div className="bg-[#EEF6F0] border border-[#C4E2CC] text-[#2A5A35] text-xs p-3 rounded-xl flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-[#2A5A35]" />
              <span>{actionSuccess}</span>
            </div>
          )}

          {loading && !evaluation ? (
            <div className="py-12 text-center text-xs text-[#6F6A61]">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-[#756653]" />
              Loading grounded evaluation details...
            </div>
          ) : (
            evaluation && (
              <>
                {/* Score Summary Metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-3.5">
                    <div className="text-[11px] font-medium text-[#6F6A61]">
                      Normalized Score
                    </div>
                    <div className="text-xl font-serif font-bold text-[#292722] mt-1">
                      {evaluation.normalized_score.toFixed(1)} / 100
                    </div>
                    <div className="text-[10px] text-[#918A80] mt-0.5">
                      Provisional normalized
                    </div>
                  </div>

                  <div className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-3.5">
                    <div className="text-[11px] font-medium text-[#6F6A61]">
                      Raw Score
                    </div>
                    <div className="text-xl font-serif font-bold text-[#292722] mt-1">
                      {evaluation.raw_score.toFixed(1)} pts
                    </div>
                    <div className="text-[10px] text-[#918A80] mt-0.5">
                      Points actually earned
                    </div>
                  </div>

                  <div className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-3.5">
                    <div className="text-[11px] font-medium text-[#6F6A61]">
                      Evidence Coverage
                    </div>
                    <div className="text-xl font-serif font-bold text-[#756653] mt-1">
                      {evaluation.evidence_coverage.toFixed(0)}%
                    </div>
                    <div className="text-[10px] text-[#918A80] mt-0.5">
                      Criteria with explicit evidence
                    </div>
                  </div>

                  <div className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-3.5 flex flex-col justify-between">
                    <div>
                      <div className="text-[11px] font-medium text-[#6F6A61]">
                        Audit Provenance
                      </div>
                      <div className="text-xs font-semibold text-[#292722] mt-1 truncate">
                        {evaluation.model_provider || "AI Engine"}
                      </div>
                    </div>
                    {isRecruiter && (
                      <button
                        type="button"
                        disabled={recalculating}
                        onClick={handleRecalculate}
                        className="text-[11px] font-bold text-[#756653] hover:text-[#292722] inline-flex items-center gap-1 mt-2 disabled:opacity-50 transition"
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
                <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-xl p-4 space-y-3">
                  <h4 className="text-xs font-bold text-[#6F6A61] uppercase tracking-wider">
                    Score Breakdown By Category
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3">
                    {/* Must-Have Skills */}
                    <div className="bg-[#F5F1EA] border border-[#E8E2D8] p-2.5 rounded-lg">
                      <div className="flex justify-between text-xs font-semibold text-[#292722]">
                        <span>Must-Have</span>
                        <span className="text-[#756653]">
                          {evaluation.score_breakdown?.must_have_skills?.awarded ?? 0} /{" "}
                          {evaluation.score_breakdown?.must_have_skills?.max ?? 40}
                        </span>
                      </div>
                      <div className="w-full bg-[#EEE8DD] h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-[#756653] h-1.5 rounded-full"
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
                    <div className="bg-[#F5F1EA] border border-[#E8E2D8] p-2.5 rounded-lg">
                      <div className="flex justify-between text-xs font-semibold text-[#292722]">
                        <span>Experience</span>
                        <span className="text-[#756653]">
                          {evaluation.score_breakdown?.experience?.awarded ?? 0} /{" "}
                          {evaluation.score_breakdown?.experience?.max ?? 30}
                        </span>
                      </div>
                      <div className="w-full bg-[#EEE8DD] h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-[#756653] h-1.5 rounded-full"
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
                    <div className="bg-[#F5F1EA] border border-[#E8E2D8] p-2.5 rounded-lg">
                      <div className="flex justify-between text-xs font-semibold text-[#292722]">
                        <span>Notice Period</span>
                        <span className="text-[#756653]">
                          {evaluation.score_breakdown?.notice_period?.awarded ?? 0} /{" "}
                          {evaluation.score_breakdown?.notice_period?.max ?? 15}
                        </span>
                      </div>
                      <div className="w-full bg-[#EEE8DD] h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-[#756653] h-1.5 rounded-full"
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
                    <div className="bg-[#F5F1EA] border border-[#E8E2D8] p-2.5 rounded-lg">
                      <div className="flex justify-between text-xs font-semibold text-[#292722]">
                        <span>Location</span>
                        <span className="text-[#756653]">
                          {evaluation.score_breakdown?.location?.awarded ?? 0} /{" "}
                          {evaluation.score_breakdown?.location?.max ?? 10}
                        </span>
                      </div>
                      <div className="w-full bg-[#EEE8DD] h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-[#756653] h-1.5 rounded-full"
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
                    <div className="bg-[#F5F1EA] border border-[#E8E2D8] p-2.5 rounded-lg">
                      <div className="flex justify-between text-xs font-semibold text-[#292722]">
                        <span>Nice-To-Have</span>
                        <span className="text-[#756653]">
                          {evaluation.score_breakdown?.nice_to_have_skills?.awarded ?? 0} /{" "}
                          {evaluation.score_breakdown?.nice_to_have_skills?.max ?? 5}
                        </span>
                      </div>
                      <div className="w-full bg-[#EEE8DD] h-1.5 rounded-full mt-2 overflow-hidden">
                        <div
                          className="bg-[#756653] h-1.5 rounded-full"
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
                    <h4 className="text-xs font-bold text-[#6F6A61] uppercase tracking-wider flex items-center gap-1.5">
                      <FileText className="w-4 h-4 text-[#756653]" />
                      Criterion-Level Resume Evidence ({evidence.length})
                    </h4>
                    <span className="text-[11px] text-[#918A80]">
                      Grounded citations from resume
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {evidence.map((ev) => {
                      const statusColor =
                        ev.evidence_status === "MATCHED"
                          ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                          : ev.evidence_status === "PARTIAL"
                          ? "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                          : ev.evidence_status === "NOT_MATCHED"
                          ? "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]"
                          : ev.evidence_status === "UNKNOWN"
                          ? "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]"
                          : "bg-[#EDE5D9] text-[#5F5243] border-[#D9D1C5]";

                      return (
                        <div
                          key={ev.id}
                          className="bg-[#F5F1EA]/70 border border-[#E8E2D8] rounded-xl p-4 space-y-2"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                            <div className="flex items-center gap-2">
                              <span
                                className={`text-[10px] font-bold px-2 py-0.5 rounded-md border uppercase ${statusColor}`}
                              >
                                {ev.evidence_status}
                              </span>
                              <span className="text-xs font-bold text-[#292722]">
                                {ev.criterion_name || "Criterion"}
                              </span>
                              {ev.criterion_type && (
                                <span className="text-[10px] text-[#6F6A61] capitalize bg-[#FFFFFF] px-1.5 py-0.5 rounded border border-[#E8E2D8]">
                                  {ev.criterion_type.replace(/_/g, " ")}
                                </span>
                              )}
                            </div>

                            <div className="text-xs font-mono font-bold text-[#292722]">
                              {ev.awarded_points.toFixed(1)} / {ev.maximum_points.toFixed(1)} pts
                            </div>
                          </div>

                          {/* Supporting Evidence Excerpt */}
                          {ev.evidence_text ? (
                            <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-lg p-3 text-xs text-[#292722] italic font-serif">
                              &ldquo;{ev.evidence_text}&rdquo;
                            </div>
                          ) : (
                            <div className="text-[11px] text-[#918A80] italic">
                              No explicit evidence statement found in resume text.
                            </div>
                          )}

                          {/* Source Location & Explanation */}
                          <div className="flex flex-wrap items-center justify-between text-[11px] text-[#918A80] pt-1 border-t border-[#E8E2D8]/50">
                            <span>
                              {ev.source_reference ? (
                                <span className="font-medium text-[#292722]">
                                  Source: {ev.source_reference}
                                </span>
                              ) : (
                                "Location: Parsed Resume Content"
                              )}
                            </span>
                            {ev.explanation && (
                              <span className="text-[#6F6A61]">
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
                  <div className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-5 space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-serif font-bold text-[#292722] uppercase tracking-wider flex items-center gap-2">
                        <ShieldCheck className="w-4 h-4 text-[#756653]" />
                        Recruiter Decision & Review
                      </h4>
                      <span className="text-[11px] text-[#918A80]">
                        Decisions are recorded with immutable audit history
                      </span>
                    </div>

                    <form onSubmit={handleSubmitReview} className="space-y-3">
                      <div>
                        <label className="block text-[11px] font-semibold text-[#6F6A61] mb-1.5">
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
                                      ? "bg-[#2A5A35] text-white border-[#2A5A35] shadow-sm"
                                      : dec === "REJECT"
                                      ? "bg-[#7A2525] text-white border-[#7A2525] shadow-sm"
                                      : dec === "HOLD"
                                      ? "bg-[#7A5212] text-white border-[#7A5212] shadow-sm"
                                      : "bg-[#756653] text-white border-[#756653] shadow-sm"
                                    : "bg-[#FFFFFF] text-[#292722] border-[#D9D1C5] hover:bg-[#FAF9F6]"
                                }`}
                              >
                                {dec.replace("_", " ")}
                              </button>
                            )
                          )}
                        </div>
                      </div>

                      <div>
                        <label className="block text-[11px] font-semibold text-[#6F6A61] mb-1">
                          Recruiter Evaluation Notes:
                        </label>
                        <textarea
                          rows={2}
                          value={reviewNotes}
                          onChange={(e) => setReviewNotes(e.target.value)}
                          placeholder="Provide rationale for decision (e.g. strong Spring Boot experience, verified notice period)..."
                          className="w-full text-xs p-2.5 rounded-lg border border-[#D9D1C5] bg-[#FFFFFF] text-[#292722] placeholder-[#918A80] focus:outline-none focus:ring-2 focus:ring-[#756653]"
                        />
                      </div>

                      <div className="flex justify-end">
                        <button
                          type="submit"
                          disabled={submittingReview}
                          className="bg-[#756653] hover:bg-[#5F5243] text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-sm inline-flex items-center gap-1.5 disabled:opacity-50"
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
        <div className="px-6 py-4 bg-[#F5F1EA] border-t border-[#E8E2D8] flex justify-end shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="bg-[#756653] hover:bg-[#5F5243] text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-sm"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
