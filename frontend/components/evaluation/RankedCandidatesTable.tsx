"use client";

import React, { useState } from "react";
import {
  Search,
  Filter,
  ArrowUpDown,
  FileSearch,
  Eye,
  RotateCw,
  Loader2,
} from "lucide-react";
import type { CurrentUser, EvaluationResponse } from "@/lib/types";

interface RankedCandidatesTableProps {
  evaluations: EvaluationResponse[];
  total: number;
  page: number;
  pageSize: number;
  loading: boolean;
  onPageChange: (newPage: number) => void;
  sortBy: string;
  onSortByChange: (val: string) => void;
  search: string;
  onSearchChange: (val: string) => void;
  confidenceFilter: string;
  onConfidenceFilterChange: (val: string) => void;
  reviewFilter: string;
  onReviewFilterChange: (val: string) => void;
  scoreMin: string;
  onScoreMinChange: (val: string) => void;
  scoreMax: string;
  onScoreMaxChange: (val: string) => void;
  missingEvidenceOnly: boolean;
  onMissingEvidenceOnlyChange: (val: boolean) => void;
  mustHaveMatchedOnly: boolean;
  onMustHaveMatchedOnlyChange: (val: boolean) => void;
  onSelectEvaluation: (evaluationId: string) => void;
  onSingleEvaluate: (candidateId: string) => void;
  isEvaluatingCandidateId: string | null;
  currentUser: CurrentUser | null;
}

export default function RankedCandidatesTable({
  evaluations,
  total,
  page,
  pageSize,
  loading,
  onPageChange,
  sortBy,
  onSortByChange,
  search,
  onSearchChange,
  confidenceFilter,
  onConfidenceFilterChange,
  reviewFilter,
  onReviewFilterChange,
  scoreMin,
  onScoreMinChange,
  scoreMax,
  onScoreMaxChange,
  missingEvidenceOnly,
  onMissingEvidenceOnlyChange,
  mustHaveMatchedOnly,
  onMustHaveMatchedOnlyChange,
  onSelectEvaluation,
  onSingleEvaluate,
  isEvaluatingCandidateId,
  currentUser,
}: RankedCandidatesTableProps) {
  const [showFilters, setShowFilters] = useState(false);

  const totalPages = Math.ceil(total / pageSize) || 1;
  const isRecruiter =
    currentUser?.role === "recruiter" || currentUser?.role === "delivery_head";

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden space-y-0">
      {/* Search & Main Filter Controls */}
      <div className="p-4 border-b border-slate-200 space-y-3">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          {/* Search Bar */}
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search ranked candidates by name or email..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-indigo-500"
            />
          </div>

          {/* Quick Controls */}
          <div className="flex items-center gap-2 w-full sm:w-auto shrink-0">
            {/* Sort Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-700">
              <ArrowUpDown className="w-3.5 h-3.5 text-slate-500" />
              <select
                value={sortBy}
                onChange={(e) => onSortByChange(e.target.value)}
                className="bg-transparent border-0 font-medium text-slate-800 focus:outline-none cursor-pointer"
              >
                <option value="score_desc">Score (Highest First)</option>
                <option value="score_asc">Score (Lowest First)</option>
                <option value="experience_desc">Experience (Highest First)</option>
                <option value="notice_asc">Notice Period (Shortest First)</option>
                <option value="evaluated_desc">Evaluated Date (Newest)</option>
              </select>
            </div>

            {/* Filter Toggle Button */}
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
                showFilters ||
                confidenceFilter ||
                reviewFilter ||
                scoreMin ||
                scoreMax ||
                missingEvidenceOnly ||
                mustHaveMatchedOnly
                  ? "bg-indigo-50 border-indigo-200 text-indigo-700"
                  : "bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100"
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              Filters
              {(confidenceFilter ||
                reviewFilter ||
                scoreMin ||
                scoreMax ||
                missingEvidenceOnly ||
                mustHaveMatchedOnly) && (
                <span className="w-2 h-2 rounded-full bg-indigo-600" />
              )}
            </button>
          </div>
        </div>

        {/* Expandable Advanced Filters */}
        {showFilters && (
          <div className="pt-3 border-t border-slate-100 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs bg-slate-50/50 p-3 rounded-lg">
            {/* Confidence Filter */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Confidence Level:
              </label>
              <select
                value={confidenceFilter}
                onChange={(e) => onConfidenceFilterChange(e.target.value)}
                className="w-full p-1.5 bg-white border border-slate-200 rounded-md text-xs text-slate-800 focus:outline-indigo-500"
              >
                <option value="">All Confidence Levels</option>
                <option value="HIGH">High Confidence</option>
                <option value="NEEDS_REVIEW">Needs Review</option>
                <option value="LOW">Low Confidence</option>
              </select>
            </div>

            {/* Review Decision Filter */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Review Decision:
              </label>
              <select
                value={reviewFilter}
                onChange={(e) => onReviewFilterChange(e.target.value)}
                className="w-full p-1.5 bg-white border border-slate-200 rounded-md text-xs text-slate-800 focus:outline-indigo-500"
              >
                <option value="">All Review Statuses</option>
                <option value="UNREVIEWED">Unreviewed</option>
                <option value="SHORTLIST">Shortlisted</option>
                <option value="HOLD">On Hold</option>
                <option value="REQUEST_INFO">Request Info</option>
                <option value="REJECT">Rejected</option>
              </select>
            </div>

            {/* Min / Max Score */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 mb-1">
                Score Range (0 - 100):
              </label>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  placeholder="Min"
                  value={scoreMin}
                  onChange={(e) => onScoreMinChange(e.target.value)}
                  className="w-1/2 p-1.5 bg-white border border-slate-200 rounded-md text-xs text-slate-800 focus:outline-indigo-500"
                />
                <span className="text-slate-400">-</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={scoreMax}
                  onChange={(e) => onScoreMaxChange(e.target.value)}
                  className="w-1/2 p-1.5 bg-white border border-slate-200 rounded-md text-xs text-slate-800 focus:outline-indigo-500"
                />
              </div>
            </div>

            {/* Checkbox Toggles */}
            <div className="flex flex-col justify-end space-y-1.5 pt-1">
              <label className="flex items-center gap-2 cursor-pointer text-[11px] text-slate-700">
                <input
                  type="checkbox"
                  checked={missingEvidenceOnly}
                  onChange={(e) => onMissingEvidenceOnlyChange(e.target.checked)}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                Missing Evidence Only
              </label>
              <label className="flex items-center gap-2 cursor-pointer text-[11px] text-slate-700">
                <input
                  type="checkbox"
                  checked={mustHaveMatchedOnly}
                  onChange={(e) => onMustHaveMatchedOnlyChange(e.target.checked)}
                  className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
                />
                Must-Have Matched Only
              </label>
            </div>
          </div>
        )}
      </div>

      {/* Candidates Evaluation Table */}
      <div className="overflow-x-auto">
        {loading ? (
          <div className="py-16 text-center text-xs text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
            Loading ranked evaluations...
          </div>
        ) : evaluations.length === 0 ? (
          <div className="py-16 px-4 text-center">
            <FileSearch className="w-10 h-10 text-slate-300 mx-auto mb-3" />
            <p className="text-xs font-bold text-slate-800">No evaluations found</p>
            <p className="text-[11px] text-slate-400 mt-1 max-w-sm mx-auto">
              Run evaluation on candidates using the button above to extract evidence and calculate transparent scores.
            </p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead className="bg-slate-50/75 border-b border-slate-200 text-[11px] font-semibold text-slate-500">
              <tr>
                <th className="py-3 px-4 w-12 text-center">Rank</th>
                <th className="py-3 px-4">Candidate</th>
                <th className="py-3 px-4 text-center">Deterministic Score</th>
                <th className="py-3 px-4 text-center">Confidence</th>
                <th className="py-3 px-4">Evidence Coverage</th>
                <th className="py-3 px-4 text-center">Recruiter Decision</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {evaluations.map((ev, index) => {
                const rank = (page - 1) * pageSize + index + 1;
                const scoreColor =
                  ev.normalized_score >= 70
                    ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                    : ev.normalized_score >= 50
                    ? "bg-amber-50 text-amber-800 border-amber-200"
                    : "bg-rose-50 text-rose-800 border-rose-200";

                const decision = ev.latest_review_decision || "UNREVIEWED";
                const decisionBadge =
                  decision === "SHORTLIST"
                    ? "bg-emerald-100 text-emerald-800"
                    : decision === "REJECT"
                    ? "bg-rose-100 text-rose-800"
                    : decision === "HOLD"
                    ? "bg-amber-100 text-amber-800"
                    : decision === "REQUEST_INFO"
                    ? "bg-indigo-100 text-indigo-800"
                    : "bg-slate-100 text-slate-600";

                return (
                  <tr
                    key={ev.id}
                    className="hover:bg-slate-50/60 transition-colors cursor-pointer"
                    onClick={() => onSelectEvaluation(ev.id)}
                  >
                    {/* Rank */}
                    <td className="py-3 px-4 text-center font-bold text-slate-400">
                      #{rank}
                    </td>

                    {/* Candidate */}
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900">
                        {ev.candidate_name || "Unknown Candidate"}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {ev.candidate_email} • {ev.candidate_location || "Location N/A"}
                      </div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {ev.candidate_skills.slice(0, 3).map((sk, i) => (
                          <span
                            key={i}
                            className="bg-slate-100 text-slate-700 text-[10px] font-medium px-1.5 py-0.5 rounded"
                          >
                            {sk}
                          </span>
                        ))}
                        {ev.candidate_skills.length > 3 && (
                          <span className="text-[10px] text-slate-400 font-medium self-center">
                            +{ev.candidate_skills.length - 3}
                          </span>
                        )}
                      </div>
                    </td>

                    {/* Score Badge */}
                    <td className="py-3 px-4 text-center">
                      <div
                        className={`inline-flex flex-col items-center justify-center px-2.5 py-1 rounded-lg border font-bold text-sm ${scoreColor}`}
                      >
                        <span>{Math.round(ev.normalized_score)}</span>
                        <span className="text-[9px] font-normal text-slate-500">
                          {ev.raw_score.toFixed(0)} raw pts
                        </span>
                      </div>
                    </td>

                    {/* Confidence */}
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full ${
                          ev.confidence_level === "HIGH"
                            ? "bg-emerald-100 text-emerald-800"
                            : ev.confidence_level === "NEEDS_REVIEW"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-rose-100 text-rose-800"
                        }`}
                      >
                        {ev.confidence_level}
                      </span>
                    </td>

                    {/* Evidence Coverage */}
                    <td className="py-3 px-4">
                      <div className="w-28 space-y-1">
                        <div className="flex justify-between text-[10px] font-semibold text-slate-600">
                          <span>Coverage</span>
                          <span>{Math.round(ev.evidence_coverage)}%</span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-indigo-600 h-1.5 rounded-full"
                            style={{ width: `${ev.evidence_coverage}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    {/* Recruiter Decision */}
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${decisionBadge}`}
                      >
                        {decision.replace("_", " ")}
                      </span>
                    </td>

                    {/* Actions */}
                    <td
                      className="py-3 px-4 text-right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          type="button"
                          onClick={() => onSelectEvaluation(ev.id)}
                          className="bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold px-2.5 py-1.5 rounded-md transition-colors inline-flex items-center gap-1 shadow-xs"
                        >
                          <Eye className="w-3.5 h-3.5" />
                          Details
                        </button>

                        {isRecruiter && (
                          <button
                            type="button"
                            disabled={isEvaluatingCandidateId === ev.candidate_id}
                            onClick={() => onSingleEvaluate(ev.candidate_id)}
                            title="Re-evaluate Candidate"
                            className="text-slate-400 hover:text-indigo-600 p-1.5 rounded-md transition-colors"
                          >
                            {isEvaluatingCandidateId === ev.candidate_id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                            ) : (
                              <RotateCw className="w-3.5 h-3.5" />
                            )}
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination Footer */}
      {total > 0 && (
        <div className="p-4 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
          <div>
            Showing {(page - 1) * pageSize + 1} to{" "}
            {Math.min(page * pageSize, total)} of {total} ranked candidates
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              className="px-3 py-1.5 rounded-md border border-slate-200 text-slate-700 font-medium hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <span className="px-2 text-slate-600 font-semibold">
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              className="px-3 py-1.5 rounded-md border border-slate-200 text-slate-700 font-medium hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
