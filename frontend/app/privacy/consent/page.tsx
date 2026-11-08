"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { ConsentRecord, CurrentUser } from "@/lib/types";

const statusBadgeStyles: Record<string, string> = {
  GRANTED: "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]",
  PENDING: "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]",
  WITHDRAWN: "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]",
  DECLINED: "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]",
  EXPIRED: "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]",
  NOT_REQUIRED: "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]",
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
    <div className="min-h-screen bg-[#FAF9F6] selection:bg-[#EDE5D9] selection:text-[#292722]">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="pb-2 border-b border-[#E8E2D8]">
          <Link href="/privacy" className="text-xs font-semibold text-[#6F6A61] hover:text-[#756653] inline-flex items-center gap-1 mb-2">
            ← Privacy Governance
          </Link>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-[#292722] tracking-tight">Candidate Consent Records</h1>
                <span className="text-[11px] font-semibold uppercase tracking-wider bg-[#EDE5D9] text-[#756653] px-2 py-0.5 rounded-full border border-[#D9D1C5]">
                  Registry
                </span>
              </div>
              <p className="text-xs text-[#6F6A61] mt-1">
                Persistent, cryptographically hashed consent authorization logs for recruitment data processing.
              </p>
            </div>

            <button
              onClick={() => {
                setIsCreateOpen(true);
                setGeneratedLink(null);
                setCandIdInput("");
              }}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-[#756653] text-[#FAF9F6] hover:bg-[#5F5243] shadow-2xs transition-colors self-start md:self-auto"
            >
              + Create Consent Request
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {/* Filter bar */}
        <div className="bg-[#FFFFFF] p-4 rounded-2xl border border-[#E8E2D8] shadow-xs flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <label className="text-xs font-semibold text-[#6F6A61]">Filter by Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-xs border border-[#E8E2D8] rounded-xl px-3 py-1.5 bg-[#FFFFFF] text-[#292722] focus:border-[#756653] focus:outline-none"
            >
              <option value="">All Statuses ({total})</option>
              <option value="GRANTED">Granted</option>
              <option value="PENDING">Pending</option>
              <option value="WITHDRAWN">Withdrawn</option>
              <option value="DECLINED">Declined</option>
              <option value="EXPIRED">Expired</option>
            </select>
          </div>

          <span className="text-xs text-[#918A80]">
            Showing {records.length} of {total} records
          </span>
        </div>

        {/* Table */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F5F1EA] border-b border-[#E8E2D8] text-[#6F6A61] font-semibold uppercase tracking-wider text-[11px]">
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
              <tbody className="divide-y divide-[#EFEAE2]">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-[#918A80]">
                      Loading consent records...
                    </td>
                  </tr>
                ) : records.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-[#918A80]">
                      No consent records found.
                    </td>
                  </tr>
                ) : (
                  records.map((r) => (
                    <tr key={r.id} className="hover:bg-[#FAF9F6] transition-colors">
                      <td className="px-6 py-4 font-mono font-medium text-[#292722]">
                        <Link href={`/candidates/${r.candidate_id}`} className="hover:underline text-[#756653]">
                          {r.candidate_id.slice(0, 8)}...
                        </Link>
                      </td>
                      <td className="px-6 py-4 text-[#6F6A61] font-mono text-[11px]">{r.legal_basis}</td>
                      <td className="px-6 py-4 text-[#292722] max-w-xs truncate">{r.purpose}</td>
                      <td className="px-6 py-4 text-[#918A80] font-mono text-[11px]">{r.collection_method}</td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                            statusBadgeStyles[r.status] || "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-[#918A80] text-[11px]">
                        {new Date(r.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        {r.status === "GRANTED" ? (
                          <button
                            onClick={() => setWithdrawRecord(r)}
                            className="text-xs font-semibold text-[#7A2525] hover:text-[#5F1B1B] transition-colors"
                          >
                            Withdraw
                          </button>
                        ) : r.status === "PENDING" ? (
                          <span className="text-[11px] text-[#7A5212] font-semibold">Awaiting Candidate</span>
                        ) : (
                          <span className="text-[11px] text-[#918A80]">Archived</span>
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
          <div className="fixed inset-0 bg-[#292722]/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-[#FFFFFF] rounded-2xl max-w-md w-full p-6 shadow-xl border border-[#E8E2D8]">
              <h2 className="text-lg font-bold text-[#292722] mb-1">Create Candidate Consent Request</h2>
              <p className="text-xs text-[#6F6A61] mb-4">
                Generates a secure, expiring, single-use tokenized link for candidate authorization.
              </p>

              {generatedLink ? (
                <div className="space-y-4">
                  <div className="p-3 bg-[#EEF6F0] border border-[#C4E2CC] rounded-xl text-[#2A5A35] text-xs">
                    <p className="font-bold mb-1">Consent Request Link Created!</p>
                    <p className="text-[11px] text-[#2A5A35]">Share this link directly with the candidate:</p>
                    <input
                      type="text"
                      readOnly
                      value={generatedLink}
                      onClick={(e) => (e.target as HTMLInputElement).select()}
                      className="mt-2 w-full p-2 bg-[#FFFFFF] border border-[#C4E2CC] rounded-lg text-xs font-mono text-[#292722] select-all"
                    />
                  </div>
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => {
                        setIsCreateOpen(false);
                        setGeneratedLink(null);
                      }}
                      className="px-4 py-2 bg-[#F5F1EA] text-[#292722] border border-[#E8E2D8] text-xs font-semibold rounded-xl hover:bg-[#EEE8DD]"
                    >
                      Done
                    </button>
                    <a
                      href={generatedLink}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-4 py-2 bg-[#756653] text-[#FAF9F6] text-xs font-semibold rounded-xl hover:bg-[#5F5243] shadow-2xs"
                    >
                      Open Candidate View ↗
                    </a>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleCreateConsent} className="space-y-4">
                  <div>
                    <label className="block text-xs font-semibold text-[#6F6A61] mb-1">
                      Candidate UUID <span className="text-[#7A2525]">*</span>
                    </label>
                    <input
                      type="text"
                      required
                      placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
                      value={candIdInput}
                      onChange={(e) => setCandIdInput(e.target.value)}
                      className="w-full text-xs border border-[#E8E2D8] rounded-xl px-3 py-2 bg-[#FFFFFF] text-[#292722] font-mono focus:border-[#756653] focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#6F6A61] mb-1">
                      Processing Purpose
                    </label>
                    <input
                      type="text"
                      value={purposeInput}
                      onChange={(e) => setPurposeInput(e.target.value)}
                      className="w-full text-xs border border-[#E8E2D8] rounded-xl px-3 py-2 bg-[#FFFFFF] text-[#292722] focus:border-[#756653] focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[#6F6A61] mb-1">
                      Collection Method
                    </label>
                    <select
                      value={methodInput}
                      onChange={(e) => setMethodInput(e.target.value)}
                      className="w-full text-xs border border-[#E8E2D8] rounded-xl px-3 py-2 bg-[#FFFFFF] text-[#292722] focus:border-[#756653] focus:outline-none"
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
                      className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#F5F1EA] text-[#6F6A61] hover:bg-[#EEE8DD]"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#756653] text-[#FAF9F6] hover:bg-[#5F5243] disabled:opacity-50 shadow-2xs"
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
          <div className="fixed inset-0 bg-[#292722]/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-[#FFFFFF] rounded-2xl max-w-md w-full p-6 shadow-xl border border-[#E8E2D8]">
              <h2 className="text-lg font-bold text-[#292722] mb-1">Withdraw Candidate Consent</h2>
              <p className="text-xs text-[#6F6A61] mb-4">
                Withdrawing consent immediately blocks future AI evaluations and client submissions for candidate{" "}
                <span className="font-mono text-[#292722] font-semibold">{withdrawRecord.candidate_id.slice(0, 8)}...</span>.
              </p>

              <form onSubmit={handleWithdrawConsent} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-[#6F6A61] mb-1">
                    Withdrawal Reason / Candidate Notes
                  </label>
                  <textarea
                    rows={3}
                    placeholder="e.g. Candidate requested withdrawal via email on 2026-11-08."
                    value={withdrawReason}
                    onChange={(e) => setWithdrawReason(e.target.value)}
                    className="w-full text-xs border border-[#E8E2D8] rounded-xl p-2.5 bg-[#FFFFFF] text-[#292722] focus:border-[#7A2525] focus:outline-none"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setWithdrawRecord(null)}
                    className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#F5F1EA] text-[#6F6A61] hover:bg-[#EEE8DD]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#7A2525] text-[#FAF9F6] hover:bg-[#5F1B1B] disabled:opacity-50 shadow-2xs"
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
