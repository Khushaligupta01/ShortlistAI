"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import Navbar from "@/components/layout/Navbar";
import type {
  ClientOrgOption,
  CurrentUser,
  RecruiterSubmissionListItem,
} from "@/lib/types";

const STAGES = [
  { value: "ALL", label: "All Stages" },
  { value: "SUBMITTED", label: "Submitted" },
  { value: "CLIENT_SHORTLISTED", label: "Client Shortlisted" },
  { value: "INTERVIEW_REQUESTED", label: "Interview Requested" },
  { value: "INTERVIEW_SCHEDULED", label: "Interview Scheduled" },
  { value: "ADDITIONAL_INFO_REQUESTED", label: "Info Requested" },
  { value: "OFFER_EXTENDED", label: "Offer Extended" },
  { value: "HIRED", label: "Hired" },
  { value: "CLIENT_REJECTED", label: "Rejected" },
  { value: "WITHDRAWN", label: "Withdrawn" },
];

export default function RecruiterSubmissionsPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [submissions, setSubmissions] = useState<RecruiterSubmissionListItem[]>([]);
  const [clients, setClients] = useState<ClientOrgOption[]>([]);
  const [selectedClient, setSelectedClient] = useState<string>("");
  const [selectedStage, setSelectedStage] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Stage update modal
  const [stageModalSub, setStageModalSub] = useState<RecruiterSubmissionListItem | null>(null);
  const [targetStage, setTargetStage] = useState<string>("INTERVIEW_SCHEDULED");
  const [stageNote, setStageNote] = useState<string>("");
  const [updatingStage, setUpdatingStage] = useState(false);

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

        const [subs, clientList] = await Promise.all([
          api.getRecruiterSubmissions({
            client_org_id: selectedClient || undefined,
            stage: selectedStage !== "ALL" ? selectedStage : undefined,
          }),
          api.getClientOrganizations(),
        ]);
        setSubmissions(subs);
        setClients(clientList);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load submissions");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [selectedClient, selectedStage, router]);

  async function handleStageUpdate() {
    if (!stageModalSub) return;
    setUpdatingStage(true);
    try {
      await api.updatePipelineStage(stageModalSub.submission_id, {
        stage: targetStage,
        reason_note: stageNote.trim() || undefined,
      });
      // Refresh list
      const subs = await api.getRecruiterSubmissions({
        client_org_id: selectedClient || undefined,
        stage: selectedStage !== "ALL" ? selectedStage : undefined,
      });
      setSubmissions(subs);
      setStageModalSub(null);
      setStageNote("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update stage");
    } finally {
      setUpdatingStage(false);
    }
  }

  const filtered = submissions.filter((sub) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      sub.candidate_name.toLowerCase().includes(q) ||
      sub.candidate_email.toLowerCase().includes(q) ||
      sub.candidate_reference.toLowerCase().includes(q) ||
      sub.client_organization_name.toLowerCase().includes(q) ||
      sub.requisition_title.toLowerCase().includes(q)
    );
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#756653] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF9F6] selection:bg-[#EDE5D9] selection:text-[#292722]">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-[#E8E2D8]">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-[#292722] tracking-tight">Client Submissions Workspace</h1>
              <span className="text-[11px] font-semibold uppercase tracking-wider bg-[#EDE5D9] text-[#756653] px-2 py-0.5 rounded-full border border-[#D9D1C5]">
                Tracking
              </span>
            </div>
            <p className="text-xs text-[#6F6A61] mt-1">
              Track candidate submissions sent to clients, monitor client decisions, and advance candidate pipelines.
            </p>
          </div>
          <Link
            href="/pipeline"
            className="inline-flex items-center gap-1.5 bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] text-xs font-semibold px-4 py-2 rounded-xl transition shadow-2xs self-start sm:self-auto"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
            </svg>
            View Pipeline Kanban
          </Link>
        </div>

        {/* Filters */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-4 shadow-xs flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <input
              type="text"
              placeholder="Search candidate, client, email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="border border-[#E8E2D8] rounded-xl px-3 py-1.5 text-xs text-[#292722] bg-[#FFFFFF] placeholder:text-[#AAA49B] focus:border-[#756653] focus:outline-none w-full sm:w-60"
            />

            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="border border-[#E8E2D8] rounded-xl px-3 py-1.5 text-xs text-[#292722] bg-[#FFFFFF] focus:border-[#756653] focus:outline-none"
            >
              <option value="">All Client Companies</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>

            <select
              value={selectedStage}
              onChange={(e) => setSelectedStage(e.target.value)}
              className="border border-[#E8E2D8] rounded-xl px-3 py-1.5 text-xs text-[#292722] bg-[#FFFFFF] focus:border-[#756653] focus:outline-none"
            >
              {STAGES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          <div className="text-xs text-[#6F6A61] font-medium">
            Showing {filtered.length} submission{filtered.length === 1 ? "" : "s"}
          </div>
        </div>

        {error && (
          <div className="bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] p-4 rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {/* Submissions Table */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] shadow-xs overflow-hidden">
          {filtered.length === 0 ? (
            <div className="p-12 text-center text-[#918A80] text-xs">
              No client submissions found. Submit candidates from the Candidate Profile screen.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#F5F1EA] border-b border-[#E8E2D8] text-[#6F6A61] font-semibold uppercase tracking-wider">
                    <th className="px-6 py-3.5">Candidate</th>
                    <th className="px-6 py-3.5">Client Company</th>
                    <th className="px-6 py-3.5">Requisition</th>
                    <th className="px-6 py-3.5">Score</th>
                    <th className="px-6 py-3.5">Current Stage</th>
                    <th className="px-6 py-3.5">Submitted</th>
                    <th className="px-6 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EFEAE2]">
                  {filtered.map((sub) => (
                    <tr key={sub.submission_id} className="hover:bg-[#FAF9F6] transition">
                      <td className="px-6 py-4">
                        <Link
                          href={`/candidates/${sub.candidate_id}`}
                          className="font-bold text-[#292722] hover:text-[#756653] block text-sm"
                        >
                          {sub.candidate_name}
                        </Link>
                        <span className="text-[11px] text-[#918A80] block">
                          {sub.candidate_email}
                        </span>
                        <span className="inline-block bg-[#F5F1EA] text-[#6F6A61] font-mono text-[10px] px-1.5 py-0.5 rounded border border-[#E8E2D8] mt-0.5">
                          {sub.candidate_reference}
                        </span>
                      </td>

                      <td className="px-6 py-4 font-semibold text-[#292722]">
                        {sub.client_organization_name}
                      </td>

                      <td className="px-6 py-4">
                        <Link
                          href={`/requisitions/${sub.requisition_id}`}
                          className="font-medium text-[#756653] hover:underline"
                        >
                          {sub.requisition_title}
                        </Link>
                      </td>

                      <td className="px-6 py-4">
                        {sub.overall_score !== null && sub.overall_score !== undefined ? (
                          <span className="font-bold text-[#2A5A35] bg-[#EEF6F0] px-2 py-0.5 rounded-full border border-[#C4E2CC]">
                            {Math.round(sub.overall_score)}%
                          </span>
                        ) : (
                          <span className="text-[#918A80]">&mdash;</span>
                        )}
                      </td>

                      <td className="px-6 py-4">
                        <div className="space-y-1">
                          <span
                            className={`inline-block text-[11px] font-bold px-2.5 py-0.5 rounded-full border ${
                              sub.current_stage === "CLIENT_SHORTLISTED"
                                ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                                : sub.current_stage === "CLIENT_REJECTED"
                                ? "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]"
                                : sub.current_stage === "INTERVIEW_REQUESTED" || sub.current_stage === "INTERVIEW_SCHEDULED"
                                ? "bg-[#EDF4F9] text-[#264D6B] border-[#C6DDEE]"
                                : sub.current_stage === "ADDITIONAL_INFO_REQUESTED"
                                ? "bg-[#EDE5D9] text-[#756653] border-[#D9D1C5]"
                                : sub.current_stage === "HIRED"
                                ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                                : "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                            }`}
                          >
                            {sub.current_stage.replace(/_/g, " ")}
                          </span>
                          {sub.pending_requests_count > 0 && (
                            <span className="block text-[10px] text-[#7A5212] font-semibold">
                              ● {sub.pending_requests_count} client inquiry pending
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-6 py-4 text-[#918A80] whitespace-nowrap">
                        {new Date(sub.submitted_at).toLocaleDateString()}
                      </td>

                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => {
                            setStageModalSub(sub);
                            setTargetStage(
                              sub.current_stage === "INTERVIEW_REQUESTED"
                                ? "INTERVIEW_SCHEDULED"
                                : sub.current_stage === "CLIENT_SHORTLISTED"
                                ? "INTERVIEW_REQUESTED"
                                : "OFFER_EXTENDED"
                            );
                            setStageNote("");
                          }}
                          className="bg-[#F5F1EA] hover:bg-[#EEE8DD] text-[#292722] border border-[#E8E2D8] text-xs font-semibold px-3 py-1.5 rounded-xl transition shadow-2xs"
                        >
                          Update Stage
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Stage Update Dialog */}
      {stageModalSub && (
        <div className="fixed inset-0 bg-[#292722]/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-[#292722]">
              Update Candidate Stage: {stageModalSub.candidate_name}
            </h3>
            <p className="text-xs text-[#6F6A61]">
              Client: <strong className="text-[#292722]">{stageModalSub.client_organization_name}</strong> • Current: <strong className="text-[#292722]">{stageModalSub.current_stage}</strong>
            </p>

            <div>
              <label className="text-xs font-semibold text-[#6F6A61] block mb-1">
                New Stage
              </label>
              <select
                value={targetStage}
                onChange={(e) => setTargetStage(e.target.value)}
                className="w-full border border-[#E8E2D8] rounded-xl p-2.5 text-xs text-[#292722] bg-[#FFFFFF] focus:border-[#756653]"
              >
                <option value="INTERVIEW_SCHEDULED">Interview Scheduled</option>
                <option value="OFFER_EXTENDED">Offer Extended</option>
                <option value="HIRED">Hired</option>
                <option value="CLIENT_SHORTLISTED">Client Shortlisted</option>
                <option value="WITHDRAWN">Withdrawn</option>
                <option value="CLIENT_REJECTED">Client Rejected</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-[#6F6A61] block mb-1">
                Reason / Internal Note (Optional)
              </label>
              <textarea
                rows={3}
                value={stageNote}
                onChange={(e) => setStageNote(e.target.value)}
                placeholder="e.g. Confirmed 1st round technical interview on Friday 2pm..."
                className="w-full border border-[#E8E2D8] rounded-xl p-2.5 text-xs text-[#292722] bg-[#FFFFFF] focus:border-[#756653]"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#E8E2D8]">
              <button
                type="button"
                onClick={() => setStageModalSub(null)}
                className="text-xs font-semibold text-[#6F6A61] hover:text-[#292722] px-4 py-2"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={updatingStage}
                onClick={handleStageUpdate}
                className="bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] text-xs font-semibold px-4 py-2 rounded-xl transition shadow-2xs disabled:opacity-50"
              >
                {updatingStage ? "Updating..." : "Confirm Stage Update"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
