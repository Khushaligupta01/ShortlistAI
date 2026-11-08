"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type {
  CandidateListItem,
  CurrentUser,
  Requisition,
} from "@/lib/types";

export default function CandidateManagementPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [candidates, setCandidates] = useState<CandidateListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Available requisitions for filter dropdown
  const [requisitions, setRequisitions] = useState<Requisition[]>([]);

  // Filters
  const [search, setSearch] = useState("");
  const [requisitionId, setRequisitionId] = useState("");
  const [evaluationStatus, setEvaluationStatus] = useState("");
  const [reviewDecision, setReviewDecision] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const [skillFilter, setSkillFilter] = useState("");
  const [minExp, setMinExp] = useState<string>("");
  const [maxExp, setMaxExp] = useState<string>("");
  const [maxNoticeDays, setMaxNoticeDays] = useState<string>("");
  const [minScore, setMinScore] = useState<string>("");
  const [maxScore, setMaxScore] = useState<string>("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");

  // Filter drawer toggle
  const [showFilters, setShowFilters] = useState(false);

  // Quick note modal
  const [noteModalCandidate, setNoteModalCandidate] = useState<CandidateListItem | null>(null);
  const [noteContent, setNoteContent] = useState("");
  const [noteSaving, setNoteSaving] = useState(false);
  const [noteSuccess, setNoteSuccess] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    async function init() {
      try {
        const u = await api.getCurrentUser();
        if (u.role === "client_hiring_manager") {
          router.replace("/client");
          return;
        }
        setUser(u);
        const reqsResp = await api.getRequisitions(1, 100);
        setRequisitions(reqsResp.items);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Authentication failed");
      }
    }
    init();
  }, [router]);

  const loadCandidates = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await api.listCandidates({
        page,
        pageSize,
        search: search.trim() || undefined,
        requisitionId: requisitionId || undefined,
        skill: skillFilter.trim() || undefined,
        location: locationFilter.trim() || undefined,
        minExperience: minExp ? parseFloat(minExp) : undefined,
        maxExperience: maxExp ? parseFloat(maxExp) : undefined,
        maxNoticeDays: maxNoticeDays ? parseInt(maxNoticeDays, 10) : undefined,
        evaluationStatus: evaluationStatus || undefined,
        reviewDecision: reviewDecision || undefined,
        minScore: minScore ? parseFloat(minScore) : undefined,
        maxScore: maxScore ? parseFloat(maxScore) : undefined,
        sortBy,
        sortOrder,
      });
      setCandidates(resp.items);
      setTotal(resp.total);
      setTotalPages(resp.total_pages);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load candidates");
    } finally {
      setLoading(false);
    }
  }, [
    user,
    page,
    pageSize,
    search,
    requisitionId,
    skillFilter,
    locationFilter,
    minExp,
    maxExp,
    maxNoticeDays,
    evaluationStatus,
    reviewDecision,
    minScore,
    maxScore,
    sortBy,
    sortOrder,
  ]);

  useEffect(() => {
    loadCandidates();
  }, [loadCandidates]);

  function handleResetFilters() {
    setSearch("");
    setRequisitionId("");
    setEvaluationStatus("");
    setReviewDecision("");
    setLocationFilter("");
    setSkillFilter("");
    setMinExp("");
    setMaxExp("");
    setMaxNoticeDays("");
    setMinScore("");
    setMaxScore("");
    setSortBy("created_at");
    setSortOrder("desc");
    setPage(1);
  }

  async function handleSaveNote() {
    if (!noteModalCandidate || !noteContent.trim()) return;
    setNoteSaving(true);
    try {
      await api.createCandidateNote(
        noteModalCandidate.id,
        noteContent.trim(),
        noteModalCandidate.requisition_id || undefined
      );
      setNoteSuccess(true);
      setTimeout(() => {
        setNoteModalCandidate(null);
        setNoteContent("");
        setNoteSuccess(false);
      }, 900);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to save note");
    } finally {
      setNoteSaving(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Candidate Management</h1>
            <p className="text-slate-500 text-xs mt-0.5">
              Unified recruiter directory across all requisitions with evidence scores, reviews, and profiles.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-lg border transition-colors ${
                showFilters
                  ? "bg-indigo-50 border-indigo-300 text-indigo-700"
                  : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
              }`}
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
              </svg>
              Filters {(requisitionId || evaluationStatus || reviewDecision || skillFilter || minExp || minScore) ? "(Active)" : ""}
            </button>
            <button
              onClick={handleResetFilters}
              className="text-xs text-slate-500 hover:text-slate-800 px-2.5 py-2 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Reset
            </button>
          </div>
        </div>

        {/* Quick Search & Sort Bar */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="relative flex-1 w-full">
            <span className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
            <input
              type="text"
              placeholder="Search by candidate name, email, skills, job title, company..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              className="w-full pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-xs placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
            />
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto justify-end">
            <div className="flex items-center gap-1 text-xs text-slate-600">
              <span className="whitespace-nowrap">Sort by:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="border border-slate-200 rounded-md px-2 py-1.5 text-xs bg-white text-slate-700 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
              >
                <option value="created_at">Date Added</option>
                <option value="score">Evaluation Score</option>
                <option value="experience">Experience</option>
                <option value="name">Candidate Name</option>
              </select>
              <button
                type="button"
                onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
                className="p-1.5 border border-slate-200 rounded-md hover:bg-slate-50 text-slate-600 text-xs"
                title={`Sort ${sortOrder === "asc" ? "Ascending" : "Descending"}`}
              >
                {sortOrder === "asc" ? "▲" : "▼"}
              </button>
            </div>

            <div className="flex items-center gap-1 text-xs text-slate-600">
              <span className="whitespace-nowrap">Show:</span>
              <select
                value={pageSize}
                onChange={(e) => {
                  setPageSize(parseInt(e.target.value, 10));
                  setPage(1);
                }}
                className="border border-slate-200 rounded-md px-2 py-1.5 text-xs bg-white text-slate-700"
              >
                <option value="10">10</option>
                <option value="25">25</option>
                <option value="50">50</option>
              </select>
            </div>
          </div>
        </div>

        {/* Collapsible Filter Drawer */}
        {showFilters && (
          <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 animate-in fade-in duration-150">
            <div>
              <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Requisition
              </label>
              <select
                value={requisitionId}
                onChange={(e) => {
                  setRequisitionId(e.target.value);
                  setPage(1);
                }}
                className="w-full border border-slate-200 rounded-lg p-2 text-xs bg-white text-slate-800"
              >
                <option value="">All Requisitions</option>
                {requisitions.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Evaluation Status
              </label>
              <select
                value={evaluationStatus}
                onChange={(e) => {
                  setEvaluationStatus(e.target.value);
                  setPage(1);
                }}
                className="w-full border border-slate-200 rounded-lg p-2 text-xs bg-white text-slate-800"
              >
                <option value="">All Statuses</option>
                <option value="evaluated">Evaluated</option>
                <option value="unreviewed">Unreviewed (Evaluated)</option>
                <option value="pending">Ingestion Pending</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Review Decision
              </label>
              <select
                value={reviewDecision}
                onChange={(e) => {
                  setReviewDecision(e.target.value);
                  setPage(1);
                }}
                className="w-full border border-slate-200 rounded-lg p-2 text-xs bg-white text-slate-800"
              >
                <option value="">All Decisions</option>
                <option value="SHORTLIST">Shortlist</option>
                <option value="HOLD">Hold</option>
                <option value="REJECT">Reject</option>
                <option value="REQUEST_INFO">Request Info</option>
                <option value="UNREVIEWED">Unreviewed</option>
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Specific Skill
              </label>
              <input
                type="text"
                placeholder="e.g. Python, AWS, React"
                value={skillFilter}
                onChange={(e) => {
                  setSkillFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full border border-slate-200 rounded-lg p-2 text-xs placeholder:text-slate-400"
              >
              </input>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Experience (Years)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  placeholder="Min"
                  value={minExp}
                  onChange={(e) => {
                    setMinExp(e.target.value);
                    setPage(1);
                  }}
                  className="w-1/2 border border-slate-200 rounded-lg p-2 text-xs"
                />
                <span className="text-slate-400 text-xs">to</span>
                <input
                  type="number"
                  placeholder="Max"
                  value={maxExp}
                  onChange={(e) => {
                    setMaxExp(e.target.value);
                    setPage(1);
                  }}
                  className="w-1/2 border border-slate-200 rounded-lg p-2 text-xs"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Score Range (0 - 100)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="number"
                  placeholder="Min Score"
                  value={minScore}
                  onChange={(e) => {
                    setMinScore(e.target.value);
                    setPage(1);
                  }}
                  className="w-1/2 border border-slate-200 rounded-lg p-2 text-xs"
                />
                <span className="text-slate-400 text-xs">to</span>
                <input
                  type="number"
                  placeholder="Max Score"
                  value={maxScore}
                  onChange={(e) => {
                    setMaxScore(e.target.value);
                    setPage(1);
                  }}
                  className="w-1/2 border border-slate-200 rounded-lg p-2 text-xs"
                />
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Location
              </label>
              <input
                type="text"
                placeholder="City, State, or Country"
                value={locationFilter}
                onChange={(e) => {
                  setLocationFilter(e.target.value);
                  setPage(1);
                }}
                className="w-full border border-slate-200 rounded-lg p-2 text-xs placeholder:text-slate-400"
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-600 uppercase tracking-wider mb-1">
                Max Notice Period
              </label>
              <select
                value={maxNoticeDays}
                onChange={(e) => {
                  setMaxNoticeDays(e.target.value);
                  setPage(1);
                }}
                className="w-full border border-slate-200 rounded-lg p-2 text-xs bg-white text-slate-800"
              >
                <option value="">Any notice period</option>
                <option value="15">Immediate / ≤ 15 days</option>
                <option value="30">≤ 30 days (1 month)</option>
                <option value="60">≤ 60 days (2 months)</option>
                <option value="90">≤ 90 days (3 months)</option>
              </select>
            </div>
          </div>
        )}

        {/* Candidate Table */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
          {loading ? (
            <div className="py-16 text-center">
              <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-slate-500 text-xs">Loading candidates...</p>
            </div>
          ) : error ? (
            <div className="py-12 text-center text-red-600 text-xs">{error}</div>
          ) : candidates.length === 0 ? (
            <div className="py-16 text-center">
              <p className="text-slate-600 font-medium text-sm">No candidates match your search or filter criteria.</p>
              <p className="text-slate-400 text-xs mt-1">Try clearing some filters or searching for different terms.</p>
              <button
                onClick={handleResetFilters}
                className="mt-4 text-xs font-semibold text-indigo-600 hover:underline"
              >
                Reset all filters
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-100 text-slate-500 uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="px-5 py-3">Candidate</th>
                    <th className="px-4 py-3">Position / Role</th>
                    <th className="px-4 py-3">Key Skills</th>
                    <th className="px-4 py-3 text-center">Experience</th>
                    <th className="px-4 py-3 text-center">Score</th>
                    <th className="px-4 py-3 text-center">Review Decision</th>
                    <th className="px-4 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {candidates.map((cand) => {
                    const score = cand.evaluation_score;
                    const decision = cand.review_decision || "UNREVIEWED";

                    return (
                      <tr key={cand.id} className="hover:bg-slate-50/80 transition-colors">
                        {/* Name & Contact */}
                        <td className="px-5 py-3.5">
                          <Link
                            href={`/candidates/${cand.id}`}
                            className="font-bold text-slate-900 hover:text-indigo-600 text-sm"
                          >
                            {cand.full_name || "Unnamed Candidate"}
                          </Link>
                          <div className="text-slate-400 text-[11px] mt-0.5 space-y-0.5">
                            {cand.email && <div>{cand.email}</div>}
                            <div className="flex items-center gap-2">
                              {cand.location && <span>📍 {cand.location}</span>}
                              {cand.notice_period_days !== null && cand.notice_period_days !== undefined && (
                                <span>⏱ {cand.notice_period_days}d notice</span>
                              )}
                            </div>
                          </div>
                        </td>

                        {/* Associated Requisition & Current Title */}
                        <td className="px-4 py-3.5">
                          {cand.primary_job_title && (
                            <div className="font-medium text-slate-800">
                              {cand.primary_job_title}
                              {cand.primary_company && (
                                <span className="text-slate-400 font-normal"> at {cand.primary_company}</span>
                              )}
                            </div>
                          )}
                          {cand.requisition_title ? (
                            <Link
                              href={`/requisitions/${cand.requisition_id}`}
                              className="inline-block text-[11px] text-indigo-600 hover:underline mt-0.5"
                            >
                              📋 {cand.requisition_title}
                            </Link>
                          ) : (
                            <span className="text-slate-400 text-[11px]">Unattached</span>
                          )}
                        </td>

                        {/* Skills */}
                        <td className="px-4 py-3.5">
                          <div className="flex flex-wrap gap-1 max-w-xs">
                            {cand.skills?.slice(0, 4).map((s) => (
                              <span
                                key={s.id}
                                className="inline-block px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded text-[10px] font-medium"
                              >
                                {s.name}
                              </span>
                            ))}
                            {(cand.skills?.length ?? 0) > 4 && (
                              <span className="text-[10px] text-slate-400 self-center">
                                +{(cand.skills?.length ?? 0) - 4}
                              </span>
                            )}
                          </div>
                        </td>

                        {/* Total Experience */}
                        <td className="px-4 py-3.5 text-center font-medium">
                          {cand.total_experience_years !== null && cand.total_experience_years !== undefined
                            ? `${cand.total_experience_years} yrs`
                            : "—"}
                        </td>

                        {/* Score */}
                        <td className="px-4 py-3.5 text-center">
                          {score !== null && score !== undefined ? (
                            <div className="inline-flex flex-col items-center">
                              <span
                                className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                                  score >= 80
                                    ? "bg-emerald-100 text-emerald-800"
                                    : score >= 60
                                    ? "bg-blue-100 text-blue-800"
                                    : "bg-amber-100 text-amber-800"
                                }`}
                              >
                                {score.toFixed(1)} / 100
                              </span>
                              {cand.evidence_coverage !== null && cand.evidence_coverage !== undefined && (
                                <span className="text-[10px] text-slate-400 mt-0.5">
                                  {Math.round(cand.evidence_coverage * 100)}% coverage
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-400 text-[11px]">Pending Eval</span>
                          )}
                        </td>

                        {/* Decision */}
                        <td className="px-4 py-3.5 text-center">
                          <span
                            className={`inline-block px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                              decision === "SHORTLIST"
                                ? "bg-emerald-100 text-emerald-700 border border-emerald-200"
                                : decision === "REJECT"
                                ? "bg-red-100 text-red-700 border border-red-200"
                                : decision === "HOLD"
                                ? "bg-amber-100 text-amber-700 border border-amber-200"
                                : decision === "REQUEST_INFO"
                                ? "bg-blue-100 text-blue-700 border border-blue-200"
                                : "bg-slate-100 text-slate-500 border border-slate-200"
                            }`}
                          >
                            {decision}
                          </span>
                        </td>

                        {/* Actions */}
                        <td className="px-4 py-3.5 text-right space-x-2">
                          <button
                            onClick={() => setNoteModalCandidate(cand)}
                            className="text-xs font-medium text-slate-600 hover:text-indigo-600 hover:bg-slate-100 px-2 py-1 rounded transition-colors"
                            title="Add recruiter note"
                          >
                            📝 Note
                          </button>
                          <Link
                            href={`/candidates/${cand.id}`}
                            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:underline px-2 py-1"
                          >
                            Profile →
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Bar */}
          <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <div>
              Showing {candidates.length > 0 ? (page - 1) * pageSize + 1 : 0} to{" "}
              {Math.min(page * pageSize, total)} of {total} candidates
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
                className="px-3 py-1.5 border border-slate-200 rounded-md bg-white text-slate-700 disabled:opacity-50 hover:bg-slate-50 font-medium"
              >
                Previous
              </button>
              <span className="font-semibold text-slate-700">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
                className="px-3 py-1.5 border border-slate-200 rounded-md bg-white text-slate-700 disabled:opacity-50 hover:bg-slate-50 font-medium"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Quick Note Modal */}
      {noteModalCandidate && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4 animate-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div>
                <h3 className="text-sm font-bold text-slate-800">Add Internal Recruiter Note</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Candidate: <span className="font-semibold text-slate-700">{noteModalCandidate.full_name}</span>
                </p>
              </div>
              <button
                onClick={() => setNoteModalCandidate(null)}
                className="text-slate-400 hover:text-slate-600 text-sm"
              >
                ✕
              </button>
            </div>

            {noteSuccess ? (
              <div className="p-4 bg-emerald-50 text-emerald-700 text-xs rounded-lg text-center font-medium">
                Note recorded successfully!
              </div>
            ) : (
              <>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Internal Recruiter Notes (Confidential)
                  </label>
                  <textarea
                    rows={4}
                    placeholder="Enter candidate observations, interview feedback, compensation constraints, or screening notes..."
                    value={noteContent}
                    onChange={(e) => setNoteContent(e.target.value)}
                    className="w-full border border-slate-200 rounded-lg p-3 text-xs placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600"
                  />
                  <p className="text-[10px] text-slate-400 mt-1">
                    🔒 These notes are internal to recruiters and are never visible to client hiring managers.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2">
                  <button
                    onClick={() => setNoteModalCandidate(null)}
                    className="px-3.5 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    disabled={!noteContent.trim() || noteSaving}
                    onClick={handleSaveNote}
                    className="px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50 shadow-sm transition-colors"
                  >
                    {noteSaving ? "Saving..." : "Save Note"}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
