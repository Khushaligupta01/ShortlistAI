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
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Client Submissions Workspace</h1>
            <p className="text-sm text-slate-500 mt-1">
              Track candidate submissions sent to clients, monitor client decisions, and advance candidate pipelines.
            </p>
          </div>
          <Link
            href="/pipeline"
            className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition shadow-sm self-start sm:self-auto"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7m0 10a2 2 0 002 2h2a2 2 0 002-2V7a2 2 0 00-2-2h-2a2 2 0 00-2 2" />
            </svg>
            View Pipeline Kanban
          </Link>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <input
              type="text"
              placeholder="Search candidate, client, email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full sm:w-60"
            />

            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
              className="border border-slate-300 rounded-lg px-3 py-1.5 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {STAGES.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          <div className="text-xs text-slate-500 font-medium">
            Showing {filtered.length} submission{filtered.length === 1 ? "" : "s"}
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">
            {error}
          </div>
        )}

        {/* Submissions Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          {filtered.length === 0 ? (
            <div className="p-12 text-center text-slate-400 text-sm">
              No client submissions found. Submit candidates from the Candidate Profile screen.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                    <th className="px-6 py-3">Candidate</th>
                    <th className="px-6 py-3">Client Company</th>
                    <th className="px-6 py-3">Requisition</th>
                    <th className="px-6 py-3">Score</th>
                    <th className="px-6 py-3">Current Stage</th>
                    <th className="px-6 py-3">Submitted</th>
                    <th className="px-6 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.map((sub) => (
                    <tr key={sub.submission_id} className="hover:bg-slate-50 transition">
                      <td className="px-6 py-4">
                        <Link
                          href={`/candidates/${sub.candidate_id}`}
                          className="font-bold text-slate-900 hover:text-indigo-600 block"
                        >
                          {sub.candidate_name}
                        </Link>
                        <span className="text-[11px] text-slate-400 block">
                          {sub.candidate_email}
                        </span>
                        <span className="inline-block bg-slate-100 text-slate-600 font-mono text-[10px] px-1.5 py-0.5 rounded mt-0.5">
                          {sub.candidate_reference}
                        </span>
                      </td>

                      <td className="px-6 py-4 font-semibold text-slate-800">
                        {sub.client_organization_name}
                      </td>

                      <td className="px-6 py-4">
                        <Link
                          href={`/requisitions/${sub.requisition_id}`}
                          className="font-medium text-slate-700 hover:underline"
                        >
                          {sub.requisition_title}
                        </Link>
                      </td>

                      <td className="px-6 py-4">
                        {sub.overall_score !== null && sub.overall_score !== undefined ? (
                          <span className="font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                            {Math.round(sub.overall_score)}%
                          </span>
                        ) : (
                          <span className="text-slate-400">&mdash;</span>
                        )}
                      </td>

                      <td className="px-6 py-4">
                        <div className="space-y-1">
                          <span
                            className={`inline-block text-[11px] font-bold px-2.5 py-0.5 rounded-full ${
                              sub.current_stage === "CLIENT_SHORTLISTED"
                                ? "bg-emerald-100 text-emerald-800"
                                : sub.current_stage === "CLIENT_REJECTED"
                                ? "bg-red-100 text-red-800"
                                : sub.current_stage === "INTERVIEW_REQUESTED" || sub.current_stage === "INTERVIEW_SCHEDULED"
                                ? "bg-blue-100 text-blue-800"
                                : sub.current_stage === "ADDITIONAL_INFO_REQUESTED"
                                ? "bg-purple-100 text-purple-800"
                                : sub.current_stage === "HIRED"
                                ? "bg-green-100 text-green-900"
                                : "bg-amber-100 text-amber-800"
                            }`}
                          >
                            {sub.current_stage.replace(/_/g, " ")}
                          </span>
                          {sub.pending_requests_count > 0 && (
                            <span className="block text-[10px] text-amber-700 font-bold">
                              ● {sub.pending_requests_count} client inquiry pending
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="px-6 py-4 text-slate-500 whitespace-nowrap">
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
                          className="bg-slate-100 hover:bg-slate-200 text-slate-800 text-xs font-semibold px-3 py-1.5 rounded-lg transition"
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
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-slate-900">
              Update Candidate Stage: {stageModalSub.candidate_name}
            </h3>
            <p className="text-xs text-slate-500">
              Client: <strong>{stageModalSub.client_organization_name}</strong> • Current: <strong>{stageModalSub.current_stage}</strong>
            </p>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                New Stage
              </label>
              <select
                value={targetStage}
                onChange={(e) => setTargetStage(e.target.value)}
                className="w-full border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
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
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Reason / Internal Note (Optional)
              </label>
              <textarea
                rows={3}
                value={stageNote}
                onChange={(e) => setStageNote(e.target.value)}
                placeholder="e.g. Confirmed 1st round technical interview on Friday 2pm..."
                className="w-full border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setStageModalSub(null)}
                className="text-xs font-semibold text-slate-600 hover:text-slate-800 px-4 py-2"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={updatingStage}
                onClick={handleStageUpdate}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2 rounded-xl transition shadow"
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
