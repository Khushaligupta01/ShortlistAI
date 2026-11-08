"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { CurrentUser, DataRequest } from "@/lib/types";

const statusBadgeStyles: Record<string, string> = {
  COMPLETED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  PENDING: "bg-amber-50 text-amber-700 border-amber-200",
  PROCESSING: "bg-indigo-50 text-indigo-700 border-indigo-200",
  EXPIRED: "bg-slate-100 text-slate-600 border-slate-200",
  FAILED: "bg-rose-50 text-rose-700 border-rose-200",
};

export default function DataRequestsPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [requests, setRequests] = useState<DataRequest[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Create modal state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [candidateIdInput, setCandidateIdInput] = useState("");
  const [requestType, setRequestType] = useState<"EXPORT" | "ACCESS">("EXPORT");
  const [reasonInput, setReasonInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Active generating state
  const [generatingId, setGeneratingId] = useState<string | null>(null);

  async function loadRequests(status?: string) {
    setLoading(true);
    try {
      const res = await api.listDataRequests({ status: status || undefined });
      setRequests(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load data requests.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function init() {
      const token = getAccessToken();
      if (!token) {
        router.push("/login");
        return;
      }
      try {
        const u = await api.getCurrentUser();
        setUser(u);
        if (u.role === "client_hiring_manager") {
          router.push("/client");
          return;
        }
        await loadRequests(statusFilter);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Initialization failed.");
        setLoading(false);
      }
    }
    init();
  }, [router, statusFilter]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!candidateIdInput.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await api.createDataRequest(candidateIdInput.trim(), {
        request_type: requestType,
        reason: reasonInput || undefined,
      });
      setIsCreateOpen(false);
      setCandidateIdInput("");
      setReasonInput("");
      await loadRequests(statusFilter);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create data request.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleGenerateExport(requestId: string) {
    setGeneratingId(requestId);
    setError(null);
    try {
      await api.generateDataExport(requestId);
      await loadRequests(statusFilter);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Export generation failed.");
    } finally {
      setGeneratingId(null);
    }
  }

  async function handleDownload(requestId: string, candidateId: string) {
    try {
      const blob = await api.downloadDataExport(requestId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `candidate_export_${candidateId.slice(0, 8)}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Download failed.");
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-center gap-2 mb-2">
          <Link href="/privacy" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
            ← Privacy Governance
          </Link>
        </div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Candidate Data Access & Portability Requests</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Generate structured, portable JSON exports of candidate personal profiles, employment history, evaluations, and consent trails.
            </p>
          </div>

          <button
            onClick={() => setIsCreateOpen(true)}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm transition-colors"
          >
            + Create Data Access Request
          </button>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Filter bar */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-xs font-medium text-slate-600">Filter by Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">All Statuses ({total})</option>
              <option value="PENDING">Pending</option>
              <option value="PROCESSING">Processing</option>
              <option value="COMPLETED">Completed</option>
              <option value="EXPIRED">Expired</option>
              <option value="FAILED">Failed</option>
            </select>
          </div>

          <span className="text-xs text-slate-400">
            Showing {requests.length} of {total} requests
          </span>
        </div>

        {/* Requests Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-6 py-3.5">Candidate ID</th>
                  <th className="px-6 py-3.5">Request Type</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Metadata</th>
                  <th className="px-6 py-3.5">Created At</th>
                  <th className="px-6 py-3.5">Expires At</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-slate-400">
                      Loading data requests...
                    </td>
                  </tr>
                ) : requests.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-slate-500">
                      No data access requests found.
                    </td>
                  </tr>
                ) : (
                  requests.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-4 font-mono font-medium text-slate-900">
                        <Link href={`/candidates/${r.candidate_id}`} className="hover:underline text-indigo-600">
                          {r.candidate_id.slice(0, 8)}...
                        </Link>
                      </td>
                      <td className="px-6 py-4 font-mono font-semibold text-slate-700">{r.request_type}</td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                            statusBadgeStyles[r.status] || "bg-slate-100 text-slate-700 border-slate-200"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-500 text-[11px]">
                        {r.export_metadata ? (
                          <span>
                            {r.export_metadata.file_size_bytes
                              ? `${Math.round(Number(r.export_metadata.file_size_bytes) / 1024)} KB`
                              : "Generated"}
                            {" • "}
                            {String(r.export_metadata.evaluations_count ?? 0)} eval(s)
                          </span>
                        ) : (
                          "Pending generation"
                        )}
                      </td>
                      <td className="px-6 py-4 text-slate-400 text-[11px]">
                        {new Date(r.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-slate-400 text-[11px]">
                        {r.expires_at ? new Date(r.expires_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {r.status === "PENDING" ? (
                          <button
                            onClick={() => handleGenerateExport(r.id)}
                            disabled={generatingId === r.id}
                            className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 disabled:opacity-50"
                          >
                            {generatingId === r.id ? "Generating..." : "Generate JSON"}
                          </button>
                        ) : r.status === "COMPLETED" ? (
                          <button
                            onClick={() => handleDownload(r.id, r.candidate_id)}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-600 hover:text-emerald-800"
                          >
                            Download Export ↓
                          </button>
                        ) : (
                          <span className="text-[11px] text-slate-400">Unavailable</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Create Request Modal */}
        {isCreateOpen && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200">
              <h2 className="text-lg font-bold text-slate-900 mb-1">Create Data Access / Export Request</h2>
              <p className="text-xs text-slate-500 mb-4">
                Initiates a formal data subject access request to compile structured personal records.
              </p>

              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Candidate UUID <span className="text-rose-500">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
                    value={candidateIdInput}
                    onChange={(e) => setCandidateIdInput(e.target.value)}
                    className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Request Type</label>
                  <select
                    value={requestType}
                    onChange={(e) => setRequestType(e.target.value as "EXPORT" | "ACCESS")}
                    className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="EXPORT">Full Machine-Readable JSON Export</option>
                    <option value="ACCESS">Data Subject Access Overview</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Justification / Reference Notes</label>
                  <textarea
                    rows={2}
                    placeholder="e.g. Candidate subject access request received via portal on 2026-11-08"
                    value={reasonInput}
                    onChange={(e) => setReasonInput(e.target.value)}
                    className="w-full text-xs border border-slate-200 rounded-lg p-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {isSubmitting ? "Submitting..." : "Create Request"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
