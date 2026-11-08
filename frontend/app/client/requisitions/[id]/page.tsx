"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import ClientNavbar from "@/components/layout/ClientNavbar";
import type {
  ClientRequisitionDetail,
  ClientSubmissionListItem,
  CurrentUser,
} from "@/lib/types";

export default function ClientRequisitionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const reqId = params?.id as string;

  const [user, setUser] = useState<CurrentUser | null>(null);
  const [requisition, setRequisition] = useState<ClientRequisitionDetail | null>(null);
  const [submissions, setSubmissions] = useState<ClientSubmissionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    if (!reqId) return;

    async function loadData() {
      try {
        const currentUser = await api.getCurrentUser();
        if (currentUser.role !== "client_hiring_manager" && currentUser.role !== "admin" && currentUser.role !== "super_admin") {
          router.replace("/dashboard");
          return;
        }
        setUser(currentUser);

        const [r, subs] = await Promise.all([
          api.getClientRequisition(reqId),
          api.getClientSubmissions({ requisition_id: reqId }),
        ]);
        setRequisition(r);
        setSubmissions(subs);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load requisition");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [reqId, router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#756653] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !requisition) {
    return (
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="bg-[#FFFFFF] border border-[#EFC2C2] rounded-xl p-8 max-w-sm text-center shadow-sm">
          <p className="text-[#7A2525] font-medium mb-4">{error || "Requisition not found"}</p>
          <Link href="/client/requisitions" className="text-[#756653] text-sm font-semibold hover:underline">
            Back to shared requisitions
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF9F6] text-[#292722]">
      <ClientNavbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        <div className="flex items-center gap-2 text-xs text-[#918A80]">
          <Link href="/client/requisitions" className="hover:text-[#292722] transition">Shared Requisitions</Link>
          <span>/</span>
          <span className="text-[#292722] font-semibold">{requisition.title}</span>
        </div>

        {/* Requisition Header */}
        <div className="bg-[#FFFFFF] rounded-xl border border-[#E8E2D8] p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase font-bold text-[#2A5A35] bg-[#EEF6F0] border border-[#C4E2CC] px-2 py-0.5 rounded">
                  {requisition.status}
                </span>
                <span className="text-xs text-[#918A80]">
                  Shared on {new Date(requisition.created_at).toLocaleDateString()}
                </span>
              </div>
              <h1 className="text-2xl font-serif font-bold text-[#292722] mt-2">{requisition.title}</h1>
              {requisition.location && (
                <p className="text-sm text-[#6F6A61] mt-1">{requisition.location}</p>
              )}
            </div>
            <div className="text-right">
              <span className="text-3xl font-serif font-bold text-[#292722]">
                {submissions.length}
              </span>
              <p className="text-xs text-[#918A80] font-medium">Candidate Submissions</p>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-[#EFEAE2]">
            <h3 className="text-xs font-bold text-[#6F6A61] uppercase tracking-wider mb-2">
              Job Description
            </h3>
            <div className="text-xs text-[#292722] leading-relaxed whitespace-pre-wrap bg-[#F5F1EA] p-4 rounded-xl border border-[#E8E2D8] max-h-60 overflow-y-auto">
              {requisition.job_description}
            </div>
          </div>
        </div>

        {/* Submitted Candidates List */}
        <div className="bg-[#FFFFFF] rounded-xl border border-[#E8E2D8] shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-[#EFEAE2] flex items-center justify-between">
            <h2 className="text-base font-serif font-bold text-[#292722]">
              Submitted Candidates ({submissions.length})
            </h2>
          </div>

          {submissions.length === 0 ? (
            <div className="px-6 py-12 text-center text-[#918A80] text-sm">
              No candidates have been submitted to this requisition yet.
            </div>
          ) : (
            <div className="divide-y divide-[#EFEAE2]">
              {submissions.map((sub) => (
                <div
                  key={sub.submission_id}
                  className="px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 hover:bg-[#F5F1EA]/60 transition"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <span className="font-serif font-bold text-[#292722] text-sm">
                        {sub.candidate_reference}
                      </span>
                      {sub.overall_score !== null && sub.overall_score !== undefined && (
                        <span className="text-xs bg-[#EEF6F0] text-[#2A5A35] font-bold px-2 py-0.5 rounded border border-[#C4E2CC]">
                          {Math.round(sub.overall_score)}% Match
                        </span>
                      )}
                      <span className={`text-xs px-2 py-0.5 rounded font-medium border ${
                        sub.current_stage === "CLIENT_SHORTLISTED"
                          ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                          : sub.current_stage === "CLIENT_REJECTED"
                          ? "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]"
                          : sub.current_stage === "INTERVIEW_REQUESTED"
                          ? "bg-[#EDE5D9] text-[#5F5243] border-[#D9D1C5]"
                          : sub.current_stage === "ADDITIONAL_INFO_REQUESTED"
                          ? "bg-[#F5F1EA] text-[#6F6A61] border-[#E8E2D8]"
                          : "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                      }`}>
                        {sub.current_stage.replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-[#918A80]">
                      {sub.location && <span>{sub.location}</span>}
                      {sub.total_experience_years !== null && sub.total_experience_years !== undefined && (
                        <span>• {sub.total_experience_years} yrs exp</span>
                      )}
                      <span>• Submitted {new Date(sub.submitted_at).toLocaleDateString()}</span>
                    </div>

                    {sub.skills && sub.skills.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {sub.skills.slice(0, 5).map((s) => (
                          <span key={s} className="bg-[#F5F1EA] text-[#292722] border border-[#E8E2D8] text-[11px] px-2 py-0.5 rounded font-medium">
                            {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <Link
                      href={`/client/submissions/${sub.submission_id}`}
                      className="inline-flex items-center gap-1 bg-[#756653] hover:bg-[#5F5243] text-white text-xs font-semibold px-4 py-2 rounded-xl transition shadow-sm"
                    >
                      Review Profile & Decision
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
