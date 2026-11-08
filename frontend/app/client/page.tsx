"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import ClientNavbar from "@/components/layout/ClientNavbar";
import type {
  ClientDashboardMetrics,
  ClientRequisitionListItem,
  ClientSubmissionListItem,
  CurrentUser,
} from "@/lib/types";

export default function ClientDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [metrics, setMetrics] = useState<ClientDashboardMetrics | null>(null);
  const [requisitions, setRequisitions] = useState<ClientRequisitionListItem[]>([]);
  const [pendingSubmissions, setPendingSubmissions] = useState<ClientSubmissionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    async function loadData() {
      try {
        const currentUser = await api.getCurrentUser();
        if (currentUser.role !== "client_hiring_manager" && currentUser.role !== "admin" && currentUser.role !== "super_admin") {
          router.replace("/dashboard");
          return;
        }
        setUser(currentUser);

        const [m, reqs, subs] = await Promise.all([
          api.getClientDashboard(),
          api.getClientRequisitions(),
          api.getClientSubmissions(),
        ]);
        setMetrics(m);
        setRequisitions(reqs);
        setPendingSubmissions(
          subs.filter(
            (s) => s.current_stage === "SUBMITTED" || s.current_stage === "CLIENT_REVIEW_PENDING"
          )
        );
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="bg-white border border-red-200 rounded-xl p-8 max-w-sm text-center shadow-sm">
          <p className="text-red-600 font-medium mb-4">{error}</p>
          <button
            onClick={() => router.push("/login")}
            className="text-emerald-700 text-sm font-semibold hover:underline"
          >
            Back to login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <ClientNavbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Welcome & Security Banner */}
        <div className="bg-gradient-to-r from-emerald-900 to-slate-900 text-white rounded-2xl p-6 sm:p-8 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <span className="text-xs uppercase tracking-widest font-bold text-emerald-400 bg-emerald-950/60 border border-emerald-800/60 px-2.5 py-1 rounded-full">
                Hiring Manager Shortlist
              </span>
              <h1 className="text-2xl sm:text-3xl font-bold mt-2">
                Candidate Review & Decision Center
              </h1>
              <p className="text-slate-300 text-sm mt-1 max-w-2xl">
                Review screened candidates submitted by your staffing partner. Candidate contact details are masked to ensure fair and compliant hiring.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/client/submissions"
                className="bg-emerald-500 hover:bg-emerald-600 text-white text-xs font-semibold px-4 py-2 rounded-xl transition shadow"
              >
                View All Submissions
              </Link>
            </div>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 font-medium">Shared Requisitions</p>
            <p className="text-2xl font-bold text-slate-900 mt-1">
              {metrics?.active_requisitions_count ?? 0}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-amber-200 bg-amber-50/30 p-4">
            <p className="text-xs text-amber-700 font-medium">Awaiting Your Review</p>
            <p className="text-2xl font-bold text-amber-900 mt-1">
              {metrics?.awaiting_review_count ?? 0}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-emerald-200 bg-emerald-50/30 p-4">
            <p className="text-xs text-emerald-700 font-medium">Shortlisted</p>
            <p className="text-2xl font-bold text-emerald-900 mt-1">
              {metrics?.shortlisted_count ?? 0}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-blue-200 bg-blue-50/30 p-4">
            <p className="text-xs text-blue-700 font-medium">Interview Requested</p>
            <p className="text-2xl font-bold text-blue-900 mt-1">
              {metrics?.interview_requested_count ?? 0}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-purple-200 bg-purple-50/30 p-4">
            <p className="text-xs text-purple-700 font-medium">Info Inquiries</p>
            <p className="text-2xl font-bold text-purple-900 mt-1">
              {metrics?.additional_info_requested_count ?? 0}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-500 font-medium">Rejected</p>
            <p className="text-2xl font-bold text-slate-600 mt-1">
              {metrics?.rejected_count ?? 0}
            </p>
          </div>
        </div>

        {/* Priority Section: Candidates Awaiting Review */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
                <span>Candidates Awaiting Your Decision</span>
                {pendingSubmissions.length > 0 && (
                  <span className="bg-amber-100 text-amber-800 text-xs px-2 py-0.5 rounded-full font-semibold">
                    {pendingSubmissions.length} Action Needed
                  </span>
                )}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Profiles explicitly approved by recruiters ready for your shortlist or interview request
              </p>
            </div>
            <Link
              href="/client/submissions"
              className="text-xs font-semibold text-emerald-700 hover:text-emerald-800"
            >
              See all &rarr;
            </Link>
          </div>

          {pendingSubmissions.length === 0 ? (
            <div className="px-6 py-10 text-center text-slate-400 text-sm">
              <svg className="w-10 h-10 mx-auto mb-2 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              All submitted candidates have been reviewed!
            </div>
          ) : (
            <div className="divide-y divide-slate-100">
              {pendingSubmissions.slice(0, 5).map((sub) => (
                <div
                  key={sub.submission_id}
                  className="px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 hover:bg-slate-50 transition"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-slate-900 text-sm">
                        {sub.candidate_reference}
                      </span>
                      {sub.overall_score !== null && sub.overall_score !== undefined && (
                        <span className="text-xs bg-emerald-50 text-emerald-800 font-bold px-2 py-0.5 rounded border border-emerald-200">
                          {Math.round(sub.overall_score)}% Match
                        </span>
                      )}
                      <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-medium">
                        Review Required
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                      <span>Req: <strong>{sub.requisition_title}</strong></span>
                      {sub.location && <span>• {sub.location}</span>}
                      {sub.total_experience_years !== null && sub.total_experience_years !== undefined && (
                        <span>• {sub.total_experience_years} yrs exp</span>
                      )}
                    </div>
                    {sub.skills && sub.skills.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-1">
                        {sub.skills.slice(0, 4).map((skill) => (
                          <span
                            key={skill}
                            className="bg-slate-100 text-slate-600 text-[11px] px-2 py-0.5 rounded"
                          >
                            {skill}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <div>
                    <Link
                      href={`/client/submissions/${sub.submission_id}`}
                      className="inline-flex items-center gap-1 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3.5 py-1.5 rounded-lg transition"
                    >
                      Review & Decide
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Shared Requisitions Preview */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">
              Shared Requisitions ({requisitions.length})
            </h2>
            <Link
              href="/client/requisitions"
              className="text-xs font-semibold text-emerald-700 hover:text-emerald-800"
            >
              Manage &rarr;
            </Link>
          </div>
          {requisitions.length === 0 ? (
            <div className="px-6 py-10 text-center text-slate-400 text-sm">
              No shared requisitions found. Requisitions assigned to your organization will appear here.
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 p-6">
              {requisitions.map((req) => (
                <div
                  key={req.id}
                  className="border border-slate-200 rounded-xl p-4 hover:border-emerald-300 transition flex flex-col justify-between"
                >
                  <div>
                    <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded uppercase">
                      {req.status}
                    </span>
                    <h3 className="font-semibold text-slate-900 text-sm mt-2">
                      {req.title}
                    </h3>
                    {req.location && (
                      <p className="text-xs text-slate-500 mt-0.5">{req.location}</p>
                    )}
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs">
                    <span className="text-slate-600 font-medium">
                      {req.submissions_count} candidate{req.submissions_count === 1 ? "" : "s"} submitted
                    </span>
                    <Link
                      href={`/client/requisitions/${req.id}`}
                      className="text-emerald-700 font-semibold hover:underline"
                    >
                      View Req
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
