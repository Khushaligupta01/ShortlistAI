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
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !requisition) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="bg-white border border-red-200 rounded-xl p-8 max-w-sm text-center shadow-sm">
          <p className="text-red-600 font-medium mb-4">{error || "Requisition not found"}</p>
          <Link href="/client/requisitions" className="text-emerald-700 text-sm font-semibold hover:underline">
            Back to shared requisitions
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <ClientNavbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Link href="/client/requisitions" className="hover:underline">Shared Requisitions</Link>
          <span>/</span>
          <span className="text-slate-800 font-medium">{requisition.title}</span>
        </div>

        {/* Requisition Header */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] uppercase font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                  {requisition.status}
                </span>
                <span className="text-xs text-slate-400">
                  Shared on {new Date(requisition.created_at).toLocaleDateString()}
                </span>
              </div>
              <h1 className="text-2xl font-bold text-slate-900 mt-2">{requisition.title}</h1>
              {requisition.location && (
                <p className="text-sm text-slate-500 mt-1">{requisition.location}</p>
              )}
            </div>
            <div className="text-right">
              <span className="text-2xl font-black text-slate-900">
                {submissions.length}
              </span>
              <p className="text-xs text-slate-500 font-medium">Candidate Submissions</p>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-slate-100">
            <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-2">
              Job Description
            </h3>
            <div className="text-sm text-slate-700 whitespace-pre-wrap bg-slate-50 p-4 rounded-xl border border-slate-200 max-h-60 overflow-y-auto">
              {requisition.job_description}
            </div>
          </div>
        </div>

        {/* Submitted Candidates List */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">
              Submitted Candidates ({submissions.length})
            </h2>
          </div>

          {submissions.length === 0 ? (
            <div className="px-6 py-12 text-center text-slate-400 text-sm">
              No candidates have been submitted to this requisition yet.
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {submissions.map((sub) => (
                <div
                  key={sub.submission_id}
                  className="px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 hover:bg-slate-50 transition"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-slate-900 text-sm">
                        {sub.candidate_reference}
                      </span>
                      {sub.overall_score !== null && sub.overall_score !== undefined && (
                        <span className="text-xs bg-emerald-50 text-emerald-800 font-bold px-2 py-0.5 rounded border border-emerald-200">
                          {Math.round(sub.overall_score)}% Match
                        </span>
                      )}
                      <span className={`text-xs px-2 py-0.5 rounded font-medium ${
                        sub.current_stage === "CLIENT_SHORTLISTED"
                          ? "bg-emerald-100 text-emerald-800"
                          : sub.current_stage === "CLIENT_REJECTED"
                          ? "bg-red-100 text-red-800"
                          : sub.current_stage === "INTERVIEW_REQUESTED"
                          ? "bg-blue-100 text-blue-800"
                          : sub.current_stage === "ADDITIONAL_INFO_REQUESTED"
                          ? "bg-purple-100 text-purple-800"
                          : "bg-amber-100 text-amber-800"
                      }`}>
                        {sub.current_stage.replace(/_/g, " ")}
                      </span>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                      {sub.location && <span>{sub.location}</span>}
                      {sub.total_experience_years !== null && sub.total_experience_years !== undefined && (
                        <span>• {sub.total_experience_years} yrs exp</span>
                      )}
                      <span>• Submitted {new Date(sub.submitted_at).toLocaleDateString()}</span>
                    </div>

                    {sub.skills && sub.skills.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {sub.skills.slice(0, 5).map((s) => (
                          <span key={s} className="bg-slate-100 text-slate-600 text-[11px] px-2 py-0.5 rounded">
                            {s}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div>
                    <Link
                      href={`/client/submissions/${sub.submission_id}`}
                      className="inline-flex items-center gap-1 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-4 py-2 rounded-lg transition shadow-sm"
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
