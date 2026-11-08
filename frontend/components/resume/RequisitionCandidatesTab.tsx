"use client";

import { useEffect, useState, useCallback } from "react";
import {
  UploadCloud,
  Search,
  Users,
  Eye,
} from "lucide-react";
import { api } from "@/lib/api";
import type { CandidateListItem, CurrentUser, UploadBatch } from "@/lib/types";
import ResumeUploadModal from "./ResumeUploadModal";
import BatchProcessingDashboard from "./BatchProcessingDashboard";
import CandidateDetailModal from "./CandidateDetailModal";

interface RequisitionCandidatesTabProps {
  requisitionId: string;
  currentUser: CurrentUser | null;
}

export default function RequisitionCandidatesTab({
  requisitionId,
  currentUser,
}: RequisitionCandidatesTabProps) {
  const [candidates, setCandidates] = useState<CandidateListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [skillFilter, setSkillFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");

  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);

  const fetchCandidates = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await api.listCandidates({
        page,
        pageSize: 20,
        requisitionId,
        search: search.trim() || undefined,
        skill: skillFilter.trim() || undefined,
        location: locationFilter.trim() || undefined,
      });
      setCandidates(resp.items);
      setTotal(resp.total);
    } catch (err) {
      console.error("Failed to load candidates:", err);
    } finally {
      setLoading(false);
    }
  }, [requisitionId, page, search, skillFilter, locationFilter]);

  useEffect(() => {
    fetchCandidates();
  }, [fetchCandidates]);

  function handleUploadSuccess(batch: UploadBatch) {
    setActiveBatchId(batch.id);
    fetchCandidates();
  }

  const isRecruiter = currentUser?.role === "recruiter" || currentUser?.role === "delivery_head";

  return (
    <div className="space-y-6">
      {/* Tab Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Users className="w-5 h-5 text-indigo-600" />
            Candidate Pipeline & Parsed Resumes
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Bulk ingestion, extracted profiles, and verified skills for this requisition.
          </p>
        </div>

        {isRecruiter && (
          <button
            type="button"
            onClick={() => setIsUploadModalOpen(true)}
            className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs px-4 py-2.5 rounded-lg shadow-sm transition-all shrink-0"
          >
            <UploadCloud className="w-4 h-4" />
            Bulk Upload Resumes
          </button>
        )}
      </div>

      {/* Active Batch Dashboard Banner (if uploading or recently uploaded) */}
      {activeBatchId && (
        <BatchProcessingDashboard
          batchId={activeBatchId}
          onRefreshCandidates={fetchCandidates}
          onSelectCandidate={(candId) => setSelectedCandidateId(candId)}
        />
      )}

      {/* Filters & Search */}
      <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-xs flex flex-col md:flex-row items-center gap-3 text-xs">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by candidate name or email..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <input
            type="text"
            placeholder="Filter by skill (e.g. Java)..."
            value={skillFilter}
            onChange={(e) => {
              setSkillFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-indigo-500 w-full md:w-44"
          />
          <input
            type="text"
            placeholder="Filter by location..."
            value={locationFilter}
            onChange={(e) => {
              setLocationFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 placeholder-slate-400 focus:outline-indigo-500 w-full md:w-40"
          />
        </div>
      </div>

      {/* Candidate List Table */}
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-xs text-slate-400">Loading candidate records...</div>
        ) : candidates.length === 0 ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-400 flex items-center justify-center mx-auto">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-bold text-slate-800">No candidates found</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                No candidates have been ingested for this requisition yet. Use the upload button to
                parse PDF or DOCX resumes.
              </p>
            </div>
            {isRecruiter && (
              <button
                type="button"
                onClick={() => setIsUploadModalOpen(true)}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 px-3 py-1.5 rounded-lg transition-colors"
              >
                <UploadCloud className="w-3.5 h-3.5" />
                Upload Resumes Now
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-700">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Candidate</th>
                  <th className="py-3 px-4">Experience</th>
                  <th className="py-3 px-4">Location</th>
                  <th className="py-3 px-4">Notice Period</th>
                  <th className="py-3 px-4">Key Skills</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {candidates.map((cand) => (
                  <tr key={cand.id} className="hover:bg-slate-50/80 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-bold text-slate-900">
                        {cand.full_name || "Unnamed Candidate"}
                      </div>
                      <div className="text-[11px] text-slate-500 truncate max-w-[200px]">
                        {cand.email || "No email available"}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-medium">
                      {cand.total_experience_years !== null && cand.total_experience_years !== undefined
                        ? `${cand.total_experience_years} yrs`
                        : "—"}
                    </td>
                    <td className="py-3 px-4 text-slate-600">
                      {cand.location || "—"}
                    </td>
                    <td className="py-3 px-4">
                      {cand.notice_period_days !== null && cand.notice_period_days !== undefined ? (
                        <span className="bg-slate-100 text-slate-700 font-semibold px-2 py-0.5 rounded text-[10px]">
                          {cand.notice_period_days === 0 ? "Immediate" : `${cand.notice_period_days}d`}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1 max-w-xs">
                        {cand.skills.slice(0, 4).map((s) => (
                          <span
                            key={s.id}
                            className="bg-indigo-50 text-indigo-700 font-medium px-1.5 py-0.5 rounded text-[10px] border border-indigo-100"
                          >
                            {s.raw_name}
                          </span>
                        ))}
                        {cand.skills.length > 4 && (
                          <span className="text-[10px] text-slate-400 self-center">
                            +{cand.skills.length - 4} more
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedCandidateId(cand.id)}
                        className="inline-flex items-center gap-1 font-semibold text-indigo-600 hover:text-indigo-800 bg-indigo-50/80 hover:bg-indigo-100 px-2.5 py-1 rounded text-[11px] transition-colors"
                      >
                        <Eye className="w-3 h-3" />
                        View Profile
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination Footer */}
        {total > 20 && (
          <div className="p-3 px-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>
              Showing {candidates.length} of {total} candidates
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-2.5 py-1 border border-slate-200 rounded hover:bg-slate-50 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={page * 20 >= total}
                onClick={() => setPage((p) => p + 1)}
                className="px-2.5 py-1 border border-slate-200 rounded hover:bg-slate-50 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Upload Modal */}
      <ResumeUploadModal
        requisitionId={requisitionId}
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />

      {/* Candidate Detail Modal */}
      <CandidateDetailModal
        candidateId={selectedCandidateId}
        isOpen={Boolean(selectedCandidateId)}
        onClose={() => setSelectedCandidateId(null)}
        onCandidateUpdated={fetchCandidates}
      />
    </div>
  );
}
