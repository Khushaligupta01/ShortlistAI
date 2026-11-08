"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { CurrentUser, DeletionRequest } from "@/lib/types";

const statusBadgeStyles: Record<string, string> = {
  COMPLETED: "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]",
  APPROVED: "bg-[#EDF4F9] text-[#264D6B] border-[#C6DDEE]",
  REQUESTED: "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]",
  UNDER_REVIEW: "bg-[#EDE5D9] text-[#756653] border-[#D9D1C5]",
  REJECTED: "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]",
  SCHEDULED: "bg-[#EDF4F9] text-[#264D6B] border-[#C6DDEE]",
};

export default function DeletionRequestsPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [requests, setRequests] = useState<DeletionRequest[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Create request modal state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [candidateIdInput, setCandidateIdInput] = useState("");
  const [reasonInput, setReasonInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Review modal state
  const [reviewTarget, setReviewTarget] = useState<DeletionRequest | null>(null);
  const [reviewDecision, setReviewDecision] = useState<"APPROVE" | "REJECT" | "HOLD">("APPROVE");
  const [reviewNotes, setReviewNotes] = useState("");
  const [retentionNotes, setRetentionNotes] = useState("");
  const [isLegalHold, setIsLegalHold] = useState(false);
  const [legalHoldReason, setLegalHoldReason] = useState("");

  // Execute confirmation modal state
  const [executeTarget, setExecuteTarget] = useState<DeletionRequest | null>(null);
  const [isExecuting, setIsExecuting] = useState(false);

  async function loadRequests(status?: string) {
    setLoading(true);
    try {
      const res = await api.listDeletionRequests({ status: status || undefined });
      setRequests(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load deletion requests.");
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
      await api.createDeletionRequest(candidateIdInput.trim(), {
        reason: reasonInput || undefined,
      });
      setIsCreateOpen(false);
      setCandidateIdInput("");
      setReasonInput("");
      setSuccessMessage("Candidate deletion request submitted successfully.");
      await loadRequests(statusFilter);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create deletion request.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleReview(e: React.FormEvent) {
    e.preventDefault();
    if (!reviewTarget) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await api.reviewDeletionRequest(reviewTarget.id, {
        decision: reviewDecision,
        review_notes: reviewNotes || undefined,
        retention_policy_notes: retentionNotes || undefined,
        is_legal_hold: isLegalHold,
        legal_hold_reason: isLegalHold ? legalHoldReason : undefined,
      });
      setReviewTarget(null);
      setSuccessMessage("Deletion request reviewed successfully.");
      await loadRequests(statusFilter);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to review deletion request.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleExecute() {
    if (!executeTarget) return;
    setIsExecuting(true);
    setError(null);
    try {
      const res = await api.executeDeletion(executeTarget.id);
      setExecuteTarget(null);
      setSuccessMessage(res.message);
      await loadRequests(statusFilter);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to execute candidate deletion.");
    } finally {
      setIsExecuting(false);
    }
  }

  const isPrivileged = user?.role === "delivery_head" || user?.role === "admin" || user?.role === "super_admin";

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
                <h1 className="text-2xl font-bold text-[#292722] tracking-tight">Candidate Data Erasure Requests</h1>
                <span className="text-[11px] font-semibold uppercase tracking-wider bg-[#EDE5D9] text-[#756653] px-2 py-0.5 rounded-full border border-[#D9D1C5]">
                  Right to be Forgotten
                </span>
              </div>
              <p className="text-xs text-[#6F6A61] mt-1">
                Controlled Right-to-be-Forgotten workflows with legal hold evaluation, private file purging, and database PII scrubbing.
              </p>
            </div>

            <button
              onClick={() => setIsCreateOpen(true)}
              className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-xl bg-[#7A2525] text-[#FAF9F6] hover:bg-[#5F1B1B] shadow-2xs transition-colors self-start md:self-auto"
            >
              + Create Deletion Request
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {successMessage && (
          <div className="p-4 bg-[#EEF6F0] border border-[#C4E2CC] text-[#2A5A35] rounded-xl text-xs font-semibold flex items-center justify-between shadow-xs">
            <span>{successMessage}</span>
            <button onClick={() => setSuccessMessage(null)} className="text-[#2A5A35] font-bold hover:text-[#1E4025]">
              ✕
            </button>
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
              <option value="REQUESTED">Requested</option>
              <option value="UNDER_REVIEW">Under Review / Legal Hold</option>
              <option value="APPROVED">Approved</option>
              <option value="COMPLETED">Completed</option>
              <option value="REJECTED">Rejected</option>
            </select>
          </div>

          <span className="text-xs text-[#918A80]">
            Showing {requests.length} of {total} requests
          </span>
        </div>

        {/* Deletion Table */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F5F1EA] border-b border-[#E8E2D8] text-[#6F6A61] font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-6 py-3.5">Candidate ID</th>
                  <th className="px-6 py-3.5">Status</th>
                  <th className="px-6 py-3.5">Review Decision</th>
                  <th className="px-6 py-3.5">Files Scrubbed</th>
                  <th className="px-6 py-3.5">Legal Hold</th>
                  <th className="px-6 py-3.5">Requested At</th>
                  <th className="px-6 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFEAE2]">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-[#918A80]">
                      Loading deletion requests...
                    </td>
                  </tr>
                ) : requests.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-12 text-[#918A80]">
                      No deletion requests found.
                    </td>
                  </tr>
                ) : (
                  requests.map((r) => (
                    <tr key={r.id} className="hover:bg-[#FAF9F6] transition-colors">
                      <td className="px-6 py-4 font-mono font-medium text-[#292722]">
                        <Link href={`/candidates/${r.candidate_id}`} className="hover:underline text-[#756653]">
                          {r.candidate_id.slice(0, 8)}...
                        </Link>
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                            statusBadgeStyles[r.status] || "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]"
                          }`}
                        >
                          {r.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-[#6F6A61] font-mono text-[11px]">
                        {r.review_decision || "Pending Review"}
                      </td>
                      <td className="px-6 py-4 text-[#292722] font-semibold">
                        {r.files_deleted_count} file(s)
                      </td>
                      <td className="px-6 py-4">
                        {r.is_legal_hold ? (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-[#FDF6E7] text-[#7A5212] border border-[#F1DCAC]">
                            LEGAL HOLD
                          </span>
                        ) : (
                          <span className="text-[11px] text-[#918A80]">None</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-[#918A80] text-[11px]">
                        {new Date(r.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right space-x-2">
                        {r.status === "REQUESTED" || r.status === "UNDER_REVIEW" ? (
                          isPrivileged ? (
                            <button
                              onClick={() => {
                                setReviewTarget(r);
                                setReviewDecision("APPROVE");
                                setReviewNotes("");
                                setRetentionNotes("");
                                setIsLegalHold(r.is_legal_hold);
                                setLegalHoldReason(r.legal_hold_reason || "");
                              }}
                              className="text-xs font-semibold text-[#756653] hover:text-[#5F5243]"
                            >
                              Review Request
                            </button>
                          ) : (
                            <span className="text-[11px] text-[#918A80]">Awaiting Delivery Head</span>
                          )
                        ) : r.status === "APPROVED" ? (
                          isPrivileged ? (
                            <button
                              onClick={() => setExecuteTarget(r)}
                              className="text-xs font-bold text-[#7A2525] hover:text-[#5F1B1B] underline"
                            >
                              Execute Deletion ⚠️
                            </button>
                          ) : (
                            <span className="text-[11px] text-[#918A80]">Approved</span>
                          )
                        ) : (
                          <span className="text-[11px] text-[#918A80]">Completed</span>
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
              <h2 className="text-lg font-bold text-[#292722] mb-1">Create Candidate Deletion Request</h2>
              <p className="text-xs text-[#6F6A61] mb-4">
                Submits a candidate erasure request for review by the organization Delivery Head.
              </p>

              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-[#6F6A61] mb-1">
                    Candidate UUID <span className="text-[#7A2525]">*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. 123e4567-e89b-12d3-a456-426614174000"
                    value={candidateIdInput}
                    onChange={(e) => setCandidateIdInput(e.target.value)}
                    className="w-full text-xs border border-[#E8E2D8] rounded-xl px-3 py-2 bg-[#FFFFFF] text-[#292722] font-mono focus:border-[#7A2525] focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#6F6A61] mb-1">Reason for Erasure</label>
                  <textarea
                    rows={3}
                    placeholder="e.g. Direct candidate right-to-be-forgotten request received on 2026-11-08."
                    value={reasonInput}
                    onChange={(e) => setReasonInput(e.target.value)}
                    className="w-full text-xs border border-[#E8E2D8] rounded-xl p-2.5 bg-[#FFFFFF] text-[#292722] focus:border-[#7A2525] focus:outline-none"
                  />
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
                    className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#7A2525] text-[#FAF9F6] hover:bg-[#5F1B1B] disabled:opacity-50 shadow-2xs"
                  >
                    {isSubmitting ? "Submitting..." : "Submit Deletion Request"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Review Modal */}
        {reviewTarget && (
          <div className="fixed inset-0 bg-[#292722]/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-[#FFFFFF] rounded-2xl max-w-lg w-full p-6 shadow-xl border border-[#E8E2D8]">
              <h2 className="text-lg font-bold text-[#292722] mb-1">Review Deletion Request</h2>
              <p className="text-xs text-[#6F6A61] mb-4">
                Evaluate candidate <span className="font-mono text-[#292722] font-semibold">{reviewTarget.candidate_id.slice(0, 8)}...</span> against retention obligations.
              </p>

              <form onSubmit={handleReview} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-[#6F6A61] mb-1">Review Decision</label>
                  <select
                    value={reviewDecision}
                    onChange={(e) => setReviewDecision(e.target.value as "APPROVE" | "REJECT" | "HOLD")}
                    className="w-full text-xs border border-[#E8E2D8] rounded-xl px-3 py-2 bg-[#FFFFFF] text-[#292722] focus:border-[#756653] focus:outline-none"
                  >
                    <option value="APPROVE">Approve for Controlled Execution</option>
                    <option value="HOLD">Place on Retention / Legal Hold</option>
                    <option value="REJECT">Reject Erasure Request</option>
                  </select>
                </div>

                <div className="p-3 bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl">
                  <label className="flex items-center gap-2 text-xs font-semibold text-[#292722] cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isLegalHold}
                      onChange={(e) => setIsLegalHold(e.target.checked)}
                      className="rounded text-[#756653]"
                    />
                    <span>Active Regulatory or Legal Hold Applies</span>
                  </label>
                  {isLegalHold && (
                    <div className="mt-2">
                      <input
                        type="text"
                        placeholder="Legal hold case number or justification..."
                        value={legalHoldReason}
                        onChange={(e) => setLegalHoldReason(e.target.value)}
                        className="w-full text-xs border border-[#F1DCAC] rounded-lg p-2 bg-[#FFFFFF] text-[#292722] focus:border-[#7A5212]"
                      />
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[#6F6A61] mb-1">Retention Policy Notes</label>
                  <textarea
                    rows={2}
                    placeholder="e.g. Audit retention permits non-identifying evaluation score preservation under Policy Sec 4.2."
                    value={retentionNotes}
                    onChange={(e) => setRetentionNotes(e.target.value)}
                    className="w-full text-xs border border-[#E8E2D8] rounded-xl p-2.5 bg-[#FFFFFF] text-[#292722] focus:border-[#756653] focus:outline-none"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => setReviewTarget(null)}
                    className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#F5F1EA] text-[#6F6A61] hover:bg-[#EEE8DD]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#756653] text-[#FAF9F6] hover:bg-[#5F5243] disabled:opacity-50 shadow-2xs"
                  >
                    {isSubmitting ? "Saving..." : "Save Review Decision"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Execute Confirmation Modal */}
        {executeTarget && (
          <div className="fixed inset-0 bg-[#292722]/50 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-[#FFFFFF] rounded-2xl max-w-md w-full p-6 shadow-2xl border border-[#EFC2C2]">
              <div className="w-12 h-12 rounded-full bg-[#FDF0F0] text-[#7A2525] flex items-center justify-center mx-auto mb-3 font-bold text-xl">
                ⚠️
              </div>
              <h2 className="text-lg font-bold text-center text-[#292722] mb-1">Execute Permanent Erasure?</h2>
              <p className="text-xs text-[#6F6A61] text-center mb-4 leading-relaxed">
                This action is <strong className="text-[#7A2525]">irreversible</strong>. The system will permanently delete all uploaded resume files from physical storage, zero out candidate personal contact details (name, email, phone, location), and block all future processing.
              </p>

              <div className="p-3 bg-[#FDF0F0] border border-[#EFC2C2] rounded-xl text-xs font-mono text-[#7A2525] mb-4">
                Candidate: {executeTarget.candidate_id}
              </div>

              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  disabled={isExecuting}
                  onClick={() => setExecuteTarget(null)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#F5F1EA] text-[#6F6A61] hover:bg-[#EEE8DD]"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={isExecuting}
                  onClick={handleExecute}
                  className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#7A2525] text-[#FAF9F6] hover:bg-[#5F1B1B] shadow-2xs disabled:opacity-50"
                >
                  {isExecuting ? "Executing Purge..." : "Confirm & Execute Wipe"}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
