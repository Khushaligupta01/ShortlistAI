"use client";

import React, { useState } from "react";
import Link from "next/link";
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
    <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-xl shadow-sm overflow-hidden space-y-0 text-[#292722]">
      {/* Search & Main Filter Controls */}
      <div className="p-4 border-b border-[#E8E2D8] space-y-3">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          {/* Search Bar */}
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-[#918A80] absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search ranked candidates by name or email..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-9 pr-3 py-2 bg-[#FAF9F6] border border-[#D9D1C5] rounded-lg text-xs text-[#292722] placeholder-[#918A80] focus:outline-none focus:ring-2 focus:ring-[#756653]"
            />
          </div>

          {/* Quick Controls */}
          <div className="flex items-center gap-2 w-full sm:w-auto shrink-0">
            {/* Sort Dropdown */}
            <div className="flex items-center gap-1.5 bg-[#FAF9F6] border border-[#D9D1C5] rounded-lg px-2.5 py-1.5 text-xs text-[#292722]">
              <ArrowUpDown className="w-3.5 h-3.5 text-[#6F6A61]" />
              <select
                value={sortBy}
                onChange={(e) => onSortByChange(e.target.value)}
                className="bg-transparent border-0 font-medium text-[#292722] focus:outline-none cursor-pointer"
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
                  ? "bg-[#EDE5D9] border-[#D9D1C5] text-[#5F5243]"
                  : "bg-[#FAF9F6] border-[#D9D1C5] text-[#292722] hover:bg-[#F5F1EA]"
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
                <span className="w-2 h-2 rounded-full bg-[#756653]" />
              )}
            </button>
          </div>
        </div>

        {/* Expandable Advanced Filters */}
        {showFilters && (
          <div className="pt-3 border-t border-[#EFEAE2] grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 text-xs bg-[#F5F1EA] p-3 rounded-lg border border-[#E8E2D8]">
            {/* Confidence Filter */}
            <div>
              <label className="block text-[11px] font-semibold text-[#6F6A61] mb-1">
                Confidence Level:
              </label>
              <select
                value={confidenceFilter}
                onChange={(e) => onConfidenceFilterChange(e.target.value)}
                className="w-full p-1.5 bg-[#FFFFFF] border border-[#D9D1C5] rounded-md text-xs text-[#292722] focus:outline-none focus:ring-1 focus:ring-[#756653]"
              >
                <option value="">All Confidence Levels</option>
                <option value="HIGH">High Confidence</option>
                <option value="NEEDS_REVIEW">Needs Review</option>
                <option value="LOW">Low Confidence</option>
              </select>
            </div>

            {/* Review Decision Filter */}
            <div>
              <label className="block text-[11px] font-semibold text-[#6F6A61] mb-1">
                Review Decision:
              </label>
              <select
                value={reviewFilter}
                onChange={(e) => onReviewFilterChange(e.target.value)}
                className="w-full p-1.5 bg-[#FFFFFF] border border-[#D9D1C5] rounded-md text-xs text-[#292722] focus:outline-none focus:ring-1 focus:ring-[#756653]"
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
              <label className="block text-[11px] font-semibold text-[#6F6A61] mb-1">
                Score Range (0 - 100):
              </label>
              <div className="flex items-center gap-1.5">
                <input
                  type="number"
                  placeholder="Min"
                  value={scoreMin}
                  onChange={(e) => onScoreMinChange(e.target.value)}
                  className="w-1/2 p-1.5 bg-[#FFFFFF] border border-[#D9D1C5] rounded-md text-xs text-[#292722] focus:outline-none focus:ring-1 focus:ring-[#756653]"
                />
                <span className="text-[#918A80]">-</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={scoreMax}
                  onChange={(e) => onScoreMaxChange(e.target.value)}
                  className="w-1/2 p-1.5 bg-[#FFFFFF] border border-[#D9D1C5] rounded-md text-xs text-[#292722] focus:outline-none focus:ring-1 focus:ring-[#756653]"
                />
              </div>
            </div>

            {/* Checkbox Toggles */}
            <div className="flex flex-col justify-end space-y-1.5 pt-1">
              <label className="flex items-center gap-2 cursor-pointer text-[11px] text-[#292722]">
                <input
                  type="checkbox"
                  checked={missingEvidenceOnly}
                  onChange={(e) => onMissingEvidenceOnlyChange(e.target.checked)}
                  className="rounded border-[#D9D1C5] text-[#756653] focus:ring-[#756653]"
                />
                Missing Evidence Only
              </label>
              <label className="flex items-center gap-2 cursor-pointer text-[11px] text-[#292722]">
                <input
                  type="checkbox"
                  checked={mustHaveMatchedOnly}
                  onChange={(e) => onMustHaveMatchedOnlyChange(e.target.checked)}
                  className="rounded border-[#D9D1C5] text-[#756653] focus:ring-[#756653]"
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
          <div className="py-16 text-center text-xs text-[#6F6A61]">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-[#756653]" />
            Loading ranked evaluations...
          </div>
        ) : evaluations.length === 0 ? (
          <div className="py-16 px-4 text-center">
            <FileSearch className="w-10 h-10 text-[#D9D1C5] mx-auto mb-3" />
            <p className="text-xs font-serif font-bold text-[#292722]">No evaluations found</p>
            <p className="text-[11px] text-[#6F6A61] mt-1 max-w-sm mx-auto">
              Run evaluation on candidates using the button above to extract evidence and calculate transparent scores.
            </p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead className="bg-[#F5F1EA] border-b border-[#E8E2D8] text-[11px] font-semibold text-[#6F6A61]">
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
            <tbody className="divide-y divide-[#EFEAE2] text-xs">
              {evaluations.map((ev, index) => {
                const rank = (page - 1) * pageSize + index + 1;
                const scoreColor =
                  ev.normalized_score >= 70
                    ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                    : ev.normalized_score >= 50
                    ? "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                    : "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]";

                const decision = ev.latest_review_decision || "UNREVIEWED";
                const decisionBadge =
                  decision === "SHORTLIST"
                    ? "bg-[#EEF6F0] text-[#2A5A35] border border-[#C4E2CC]"
                    : decision === "REJECT"
                    ? "bg-[#FDF0F0] text-[#7A2525] border border-[#EFC2C2]"
                    : decision === "HOLD"
                    ? "bg-[#FDF6E7] text-[#7A5212] border border-[#F1DCAC]"
                    : decision === "REQUEST_INFO"
                    ? "bg-[#EDE5D9] text-[#5F5243] border border-[#D9D1C5]"
                    : "bg-[#F2EFEB] text-[#5E5950] border border-[#DFD9D0]";

                return (
                  <tr
                    key={ev.id}
                    className="hover:bg-[#F5F1EA]/60 transition-colors cursor-pointer"
                    onClick={() => onSelectEvaluation(ev.id)}
                  >
                    {/* Rank */}
                    <td className="py-3 px-4 text-center font-bold text-[#918A80]">
                      #{rank}
                    </td>

                    {/* Candidate */}
                    <td className="py-3 px-4">
                      <Link
                        href={`/candidates/${ev.candidate_id}`}
                        onClick={(e) => e.stopPropagation()}
                        className="font-serif font-bold text-[#292722] hover:text-[#756653] hover:underline"
                      >
                        {ev.candidate_name || "Unknown Candidate"}
                      </Link>
                      <div className="text-[11px] text-[#6F6A61]">
                        {ev.candidate_email} • {ev.candidate_location || "Location N/A"}
                      </div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {ev.candidate_skills.slice(0, 3).map((sk, i) => (
                          <span
                            key={i}
                            className="bg-[#F5F1EA] text-[#292722] text-[10px] font-medium px-1.5 py-0.5 rounded border border-[#E8E2D8]"
                          >
                            {sk}
                          </span>
                        ))}
                        {ev.candidate_skills.length > 3 && (
                          <span className="text-[10px] text-[#918A80] font-medium self-center">
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
                        <span className="text-[9px] font-normal text-[#6F6A61]">
                          {ev.raw_score.toFixed(0)} raw pts
                        </span>
                      </div>
                    </td>

                    {/* Confidence */}
                    <td className="py-3 px-4 text-center">
                      <span
                        className={`inline-flex items-center gap-1 text-[11px] font-bold px-2 py-0.5 rounded-full border ${
                          ev.confidence_level === "HIGH"
                            ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                            : ev.confidence_level === "NEEDS_REVIEW"
                            ? "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                            : "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]"
                        }`}
                      >
                        {ev.confidence_level}
                      </span>
                    </td>

                    {/* Evidence Coverage */}
                    <td className="py-3 px-4">
                      <div className="w-28 space-y-1">
                        <div className="flex justify-between text-[10px] font-semibold text-[#6F6A61]">
                          <span>Coverage</span>
                          <span className="text-[#292722]">{Math.round(ev.evidence_coverage)}%</span>
                        </div>
                        <div className="w-full bg-[#EEE8DD] rounded-full h-1.5 overflow-hidden">
                          <div
                            className="bg-[#756653] h-1.5 rounded-full"
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
                          className="bg-[#F5F1EA] hover:bg-[#EEE8DD] text-[#292722] border border-[#E8E2D8] text-xs font-semibold px-2.5 py-1.5 rounded-lg transition-colors inline-flex items-center gap-1 shadow-sm"
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
                            className="text-[#918A80] hover:text-[#292722] p-1.5 rounded-md transition-colors"
                          >
                            {isEvaluatingCandidateId === ev.candidate_id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin text-[#756653]" />
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
        <div className="p-4 border-t border-[#E8E2D8] flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-[#6F6A61]">
          <div>
            Showing {(page - 1) * pageSize + 1} to{" "}
            {Math.min(page * pageSize, total)} of {total} ranked candidates
          </div>

          <div className="flex items-center gap-1">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => onPageChange(page - 1)}
              className="px-3 py-1.5 rounded-lg border border-[#D9D1C5] text-[#292722] font-medium hover:bg-[#F5F1EA] disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Previous
            </button>
            <span className="px-2 text-[#292722] font-semibold">
              Page {page} of {totalPages}
            </span>
            <button
              type="button"
              disabled={page >= totalPages}
              onClick={() => onPageChange(page + 1)}
              className="px-3 py-1.5 rounded-lg border border-[#D9D1C5] text-[#292722] font-medium hover:bg-[#F5F1EA] disabled:opacity-40 disabled:cursor-not-allowed transition"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
