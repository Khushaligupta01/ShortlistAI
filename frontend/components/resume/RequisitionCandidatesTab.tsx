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
    <div className="space-y-6 text-[#292722]">
      {/* Tab Top Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[#FFFFFF] border border-[#E8E2D8] rounded-xl p-4 shadow-sm">
        <div>
          <h2 className="text-base font-serif font-bold text-[#292722] flex items-center gap-2">
            <Users className="w-5 h-5 text-[#756653]" />
            Candidate Pipeline & Parsed Resumes
          </h2>
          <p className="text-xs text-[#6F6A61] mt-0.5">
            Bulk ingestion, extracted profiles, and verified skills for this requisition.
          </p>
        </div>

        {isRecruiter && (
          <button
            type="button"
            onClick={() => setIsUploadModalOpen(true)}
            className="inline-flex items-center gap-2 bg-[#756653] hover:bg-[#5F5243] text-white font-bold text-xs px-4 py-2.5 rounded-xl shadow-sm transition-all shrink-0"
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
      <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-xl p-3 shadow-sm flex flex-col md:flex-row items-center gap-3 text-xs">
        <div className="relative flex-1 w-full">
          <Search className="w-4 h-4 text-[#918A80] absolute left-3 top-2.5" />
          <input
            type="text"
            placeholder="Search by candidate name or email..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="w-full pl-9 pr-3 py-2 bg-[#FAF9F6] border border-[#D9D1C5] rounded-lg text-xs text-[#292722] placeholder-[#918A80] focus:outline-none focus:ring-2 focus:ring-[#756653]"
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
            className="px-3 py-2 bg-[#FAF9F6] border border-[#D9D1C5] rounded-lg text-xs text-[#292722] placeholder-[#918A80] focus:outline-none focus:ring-2 focus:ring-[#756653] w-full md:w-44"
          />
          <input
            type="text"
            placeholder="Filter by location..."
            value={locationFilter}
            onChange={(e) => {
              setLocationFilter(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 bg-[#FAF9F6] border border-[#D9D1C5] rounded-lg text-xs text-[#292722] placeholder-[#918A80] focus:outline-none focus:ring-2 focus:ring-[#756653] w-full md:w-40"
          />
        </div>
      </div>

      {/* Candidate List Table */}
      <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="py-16 text-center text-xs text-[#918A80]">Loading candidate records...</div>
        ) : candidates.length === 0 ? (
          <div className="py-16 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-[#F5F1EA] text-[#918A80] flex items-center justify-center mx-auto border border-[#E8E2D8]">
              <Users className="w-6 h-6" />
            </div>
            <div>
              <p className="text-sm font-serif font-bold text-[#292722]">No candidates found</p>
              <p className="text-xs text-[#6F6A61] mt-1 max-w-sm mx-auto">
                No candidates have been ingested for this requisition yet. Use the upload button to
                parse PDF or DOCX resumes.
              </p>
            </div>
            {isRecruiter && (
              <button
                type="button"
                onClick={() => setIsUploadModalOpen(true)}
                className="inline-flex items-center gap-1.5 text-xs font-bold text-[#756653] bg-[#F5F1EA] hover:bg-[#EEE8DD] border border-[#D9D1C5] px-3.5 py-1.5 rounded-xl transition-colors"
              >
                <UploadCloud className="w-3.5 h-3.5" />
                Upload Resumes Now
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-[#6F6A61]">
              <thead className="bg-[#F5F1EA] border-b border-[#E8E2D8] text-[#6F6A61] font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Candidate</th>
                  <th className="py-3 px-4">Experience</th>
                  <th className="py-3 px-4">Location</th>
                  <th className="py-3 px-4">Notice Period</th>
                  <th className="py-3 px-4">Key Skills</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFEAE2]">
                {candidates.map((cand) => (
                  <tr key={cand.id} className="hover:bg-[#F5F1EA]/60 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-serif font-bold text-[#292722]">
                        {cand.full_name || "Unnamed Candidate"}
                      </div>
                      <div className="text-[11px] text-[#918A80] truncate max-w-[200px]">
                        {cand.email || "No email available"}
                      </div>
                    </td>
                    <td className="py-3 px-4 font-medium text-[#292722]">
                      {cand.total_experience_years !== null && cand.total_experience_years !== undefined
                        ? `${cand.total_experience_years} yrs`
                        : "—"}
                    </td>
                    <td className="py-3 px-4 text-[#6F6A61]">
                      {cand.location || "—"}
                    </td>
                    <td className="py-3 px-4">
                      {cand.notice_period_days !== null && cand.notice_period_days !== undefined ? (
                        <span className="bg-[#F5F1EA] text-[#292722] border border-[#E8E2D8] font-semibold px-2 py-0.5 rounded text-[10px]">
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
                            className="bg-[#F5F1EA] text-[#292722] font-medium px-1.5 py-0.5 rounded text-[10px] border border-[#E8E2D8]"
                          >
                            {s.raw_name}
                          </span>
                        ))}
                        {cand.skills.length > 4 && (
                          <span className="text-[10px] text-[#918A80] self-center">
                            +{cand.skills.length - 4} more
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        type="button"
                        onClick={() => setSelectedCandidateId(cand.id)}
                        className="inline-flex items-center gap-1 font-semibold text-[#756653] hover:text-[#292722] bg-[#F5F1EA] hover:bg-[#EEE8DD] border border-[#D9D1C5] px-2.5 py-1 rounded-lg text-[11px] transition-colors shadow-sm"
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
          <div className="p-3 px-4 border-t border-[#E8E2D8] flex items-center justify-between text-xs text-[#6F6A61]">
            <span>
              Showing {candidates.length} of {total} candidates
            </span>
            <div className="flex items-center gap-1">
              <button
                type="button"
                disabled={page === 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-2.5 py-1 border border-[#D9D1C5] rounded hover:bg-[#F5F1EA] disabled:opacity-40"
              >
                Previous
              </button>
              <button
                type="button"
                disabled={page * 20 >= total}
                onClick={() => setPage((p) => p + 1)}
                className="px-2.5 py-1 border border-[#D9D1C5] rounded hover:bg-[#F5F1EA] disabled:opacity-40"
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
