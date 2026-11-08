"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { ConsentRecord, CurrentUser } from "@/lib/types";

const statusBadgeStyles: Record<string, string> = {
  GRANTED: "bg-emerald-50 text-emerald-700 border-emerald-200",
  PENDING: "bg-amber-50 text-amber-700 border-amber-200",
  WITHDRAWN: "bg-red-50 text-red-700 border-red-200",
  DECLINED: "bg-rose-50 text-rose-700 border-rose-200",
  EXPIRED: "bg-slate-100 text-slate-600 border-slate-200",
  NOT_REQUIRED: "bg-slate-50 text-slate-500 border-slate-200",
};

export default function ConsentManagementPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [records, setRecords] = useState<ConsentRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [candIdInput, setCandIdInput] = useState("");
  const [purposeInput, setPurposeInput] = useState("resume_screening_and_shortlisting");
  const [methodInput, setMethodInput] = useState("PUBLIC_LINK");
  const [generatedLink, setGeneratedLink] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Withdraw modal state
  const [withdrawRecord, setWithdrawRecord] = useState<ConsentRecord | null>(null);
  const [withdrawReason, setWithdrawReason] = useState("");

  async function loadRecords(status?: string) {
    setLoading(true);
    try {
      const res = await api.listConsentRecords({ status: status || undefined });
      setRecords(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load consent records.");
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
        await loadRecords(statusFilter);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Initialization failed.");
        setLoading(false);
      }
    }
    init();
  }, [router, statusFilter]);

  async function handleCreateConsent(e: React.FormEvent) {
    e.preventDefault();
    if (!candIdInput.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const res = await api.createConsentRequest(candIdInput.trim(), {
        purpose: purposeInput,
        collection_method: methodInput,
      });
      if (res.consent_url) {
        const fullUrl = `${window.location.origin}${res.consent_url}`;
        setGeneratedLink(fullUrl);
      }
      await loadRecords(statusFilter);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create consent request.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleWithdrawConsent(e: React.FormEvent) {
    e.preventDefault();
    if (!withdrawRecord) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await api.withdrawCandidateConsent(withdrawRecord.candidate_id, {
        reason: withdrawReason,
      });
      setWithdrawRecord(null);
      setWithdrawReason("");
      await loadRecords(statusFilter);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to withdraw candidate consent.");
    } finally {
      setIsSubmitting(false);
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
            <h1 className="text-2xl font-bold text-slate-900">Candidate Consent Records</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Persistent, cryptographically hashed consent authorization logs for recruitment data processing.
            </p>
          </div>

          <button
            onClick={() => {
              setIsCreateOpen(true);
              setGeneratedLink(null);
              setCandIdInput("");
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm transition-colors"
          >
            + Create Consent Request
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
              <option value="GRANTED">Granted</option>
              <option value="PENDING">Pending</option>
              <option value="WITHDRAWN">Withdrawn</option>
              <option value="DECLINED">Declined</option>
              <option value="EXPIRED">Expired</option>
            </select>
          </div>

          <span className="text-xs text-slate-400">
            Showing {records.length} of {total} records
          </span>
        </div>

        {/* Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-6 py-3.5">Candidate ID</th>
                  <th className="px-6 py-3.5">Legal Basis</th>
                  <th className="px-6 py-3.5">Purpose</th>
                  <th className="px-6 py-3.5">Collection Method</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Created At</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-slate-400">
                      Loading consent records...
                    </td>
                  </tr>
                ) : records.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-slate-500">
                      No consent records found.
                    </td>
                  </tr>
                ) : (
                  records.map((r) => (
                    <tr key={r.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-4 font-mono font-medium text-slate-900">
                        <Link href={`/candidates/${r.candidate_id}`} className="hover:underline text-indigo-600">
                          {r.candidate_id.slice(0, 8)}...
                        </Link>
                      </td>
                      <td className="px-6 py-4 text-slate-600 font-mono text-[11px]">{r.legal_basis}</td>
                      <td className="px-6 py-4 text-slate-700 max-w-xs truncate">{r.purpose}</td>
                      <td className="px-6 py-4 text-slate-500 font-mono text-[11px]">{r.collection_method}</td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                            statusBadgeStyles[r.status] || "bg-slate-100 text-slate-700 border-slate-200"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-400 text-[11px]">
                        {new Date(r.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {r.status === "GRANTED" ? (
                          <button
                            onClick={() => setWithdrawRecord(r)}
                            className="text-xs font-semibold text-rose-600 hover:text-rose-800 transition-colors"
                          >
                            Withdraw
                          </button>
                        ) : r.status === "PENDING" ? (
                          <span className="text-[11px] text-amber-600 font-medium">Awaiting Candidate</span>
                        ) : (
                          <span className="text-[11px] text-slate-400">Archived</span>
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
              <h2 className="text-lg font-bold text-slate-900 mb-1">Create Candidate Consent Request</h2>
              <p className="text-xs text-slate-500 mb-4">
                Generates a secure, expiring, single-use tokenized link for candidate authorization.
              </p>

              {generatedLink ? (
                <div className="space-y-4">
                  <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-xs">
                    <p className="font-semibold mb-1">Consent Request Link Created!</p>
                    <p className="text-[11px] text-emerald-700">Share this link directly with the candidate:</p>
                    <input
                      type="text"
                      readOnly
                      value={generatedLink}
                      onClick={(e) => (e.target as HTMLInputElement).select()}
                      className="mt-2 w-full p-2 bg-white border border-emerald-300 rounded text-xs font-mono text-slate-800 select-all"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => {
                        setIsCreateOpen(false);
                        setGeneratedLink(null);
                      }}
                      className="px-4 py-2 bg-slate-100 text-slate-700 text-xs font-semibold rounded-lg hover:bg-slate-200"
                    >
                      Done
                    </button>
                    <a
                      href={generatedLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700"
                    >
                      Open Candidate View ↗
                    </a>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleCreateConsent} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Candidate UUID <span className="text-rose-500">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
                      value={candIdInput}
                      onChange={(e) => setCandIdInput(e.target.value)}
                      className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Processing Purpose
                    </label>
                    <input
                      type="text"
                      value={purposeInput}
                      onChange={(e) => setPurposeInput(e.target.value)}
                      className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1">
                      Collection Method
                    </label>
                    <select
                      value={methodInput}
                      onChange={(e) => setMethodInput(e.target.value)}
                      className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                      <option value="PUBLIC_LINK">Public Tokenized Link (Demo & Direct)</option>
                      <option value="DIRECT_NOTICE">Direct Form Notice</option>
                      <option value="VERBAL_RECORDED">Recorded Verbal Authorization</option>
                    </select>
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
                      {isSubmitting ? "Generating..." : "Generate Request"}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {/* Withdraw Consent Confirmation Modal */}
        {withdrawRecord && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-xl border border-slate-200">
              <h2 className="text-lg font-bold text-slate-900 mb-1">Withdraw Candidate Consent</h2>
              <p className="text-xs text-slate-500 mb-4">
                Withdrawing consent immediately blocks future AI evaluations and client submissions for candidate{" "}
                <span className="font-mono text-slate-800">{withdrawRecord.candidate_id.slice(0, 8)}...</span>.
              </p>

              <form onSubmit={handleWithdrawConsent} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Withdrawal Reason / Candidate Notes
                  </label>
                  <textarea
                    rows={3}
                    placeholder="e.g. Candidate requested withdrawal via email on 2026-11-08."
                    value={withdrawReason}
                    onChange={(e) => setWithdrawReason(e.target.value)}
                    className="w-full text-xs border border-slate-200 rounded-lg p-2.5 focus:outline-none focus:ring-2 focus:ring-rose-500"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setWithdrawRecord(null)}
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-2 text-xs font-semibold rounded-lg bg-rose-600 text-white hover:bg-rose-700 disabled:opacity-50"
                  >
                    {isSubmitting ? "Withdrawing..." : "Confirm Withdrawal"}
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
