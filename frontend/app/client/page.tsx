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
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#756653] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="bg-[#FFFFFF] border border-[#EFC2C2] rounded-2xl p-8 max-w-sm text-center shadow-xs">
          <p className="text-[#7A2525] font-semibold mb-4 text-sm">{error}</p>
          <button
            onClick={() => router.push("/login")}
            className="text-[#756653] text-xs font-semibold hover:underline"
          >
            Back to login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF9F6] selection:bg-[#EDE5D9] selection:text-[#292722]">
      <ClientNavbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Welcome & Security Banner */}
        <div className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-2xl p-6 sm:p-8 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <span className="text-[11px] uppercase tracking-wider font-semibold text-[#756653] bg-[#EDE5D9] border border-[#D9D1C5] px-2.5 py-0.5 rounded-full">
                Hiring Manager Shortlist
              </span>
              <h1 className="text-2xl sm:text-3xl font-bold text-[#292722] tracking-tight mt-2">
                Candidate Review & Decision Center
              </h1>
              <p className="text-[#6F6A61] text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
                Review screened candidates submitted by your staffing partner. Candidate contact details are masked to ensure fair and compliant hiring.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href="/client/submissions"
                className="bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] text-xs font-semibold px-4 py-2.5 rounded-xl transition shadow-2xs"
              >
                View All Submissions
              </Link>
            </div>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-4 shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] text-[#6F6A61] font-semibold uppercase tracking-wider">Shared Positions</p>
            <p className="text-2xl font-bold text-[#292722] mt-1.5">
              {metrics?.active_requisitions_count ?? 0}
            </p>
          </div>
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-4 shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] text-[#7A5212] font-semibold uppercase tracking-wider">Awaiting Review</p>
            <p className="text-2xl font-bold text-[#7A5212] mt-1.5">
              {metrics?.awaiting_review_count ?? 0}
            </p>
          </div>
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-4 shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] text-[#2A5A35] font-semibold uppercase tracking-wider">Shortlisted</p>
            <p className="text-2xl font-bold text-[#2A5A35] mt-1.5">
              {metrics?.shortlisted_count ?? 0}
            </p>
          </div>
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-4 shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] text-[#264D6B] font-semibold uppercase tracking-wider">Interview Requested</p>
            <p className="text-2xl font-bold text-[#264D6B] mt-1.5">
              {metrics?.interview_requested_count ?? 0}
            </p>
          </div>
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-4 shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] text-[#756653] font-semibold uppercase tracking-wider">Info Inquiries</p>
            <p className="text-2xl font-bold text-[#756653] mt-1.5">
              {metrics?.additional_info_requested_count ?? 0}
            </p>
          </div>
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-4 shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] text-[#6F6A61] font-semibold uppercase tracking-wider">Rejected</p>
            <p className="text-2xl font-bold text-[#918A80] mt-1.5">
              {metrics?.rejected_count ?? 0}
            </p>
          </div>
        </div>

        {/* Priority Section: Candidates Awaiting Review */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] overflow-hidden shadow-xs">
          <div className="px-6 py-4 border-b border-[#E8E2D8] bg-[#F5F1EA] flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#292722] flex items-center gap-2">
                <span>Candidates Awaiting Your Decision</span>
                {pendingSubmissions.length > 0 && (
                  <span className="bg-[#FDF6E7] text-[#7A5212] border border-[#F1DCAC] text-[10px] px-2 py-0.5 rounded-full font-semibold">
                    {pendingSubmissions.length} Action Needed
                  </span>
                )}
              </h2>
              <p className="text-xs text-[#6F6A61] mt-0.5">
                Profiles explicitly approved by recruiters ready for your shortlist or interview request
              </p>
            </div>
            <Link
              href="/client/submissions"
              className="text-xs font-semibold text-[#756653] hover:text-[#5F5243]"
            >
              See all &rarr;
            </Link>
          </div>

          {pendingSubmissions.length === 0 ? (
            <div className="px-6 py-12 text-center text-[#918A80] text-xs">
              <div className="w-10 h-10 rounded-full bg-[#EEF6F0] text-[#2A5A35] flex items-center justify-center mx-auto mb-2 text-lg">
                ✓
              </div>
              All submitted candidates have been reviewed!
            </div>
          ) : (
            <div className="divide-y divide-[#EFEAE2]">
              {pendingSubmissions.slice(0, 5).map((sub) => (
                <div
                  key={sub.submission_id}
                  className="px-6 py-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 hover:bg-[#FAF9F6] transition"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-[#292722] text-sm">
                        {sub.candidate_reference}
                      </span>
                      {sub.overall_score !== null && sub.overall_score !== undefined && (
                        <span className="text-xs bg-[#EEF6F0] text-[#2A5A35] font-bold px-2 py-0.5 rounded-full border border-[#C4E2CC]">
                          {Math.round(sub.overall_score)}% Match
                        </span>
                      )}
                      <span className="text-[10px] bg-[#FDF6E7] text-[#7A5212] border border-[#F1DCAC] px-2 py-0.5 rounded-full font-semibold">
                        Review Required
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-3 text-xs text-[#6F6A61]">
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
                            className="bg-[#F5F1EA] text-[#6F6A61] border border-[#E8E2D8] text-[10px] px-2 py-0.5 rounded-md font-medium"
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
                      className="inline-flex items-center gap-1 bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] text-xs font-semibold px-3.5 py-1.5 rounded-xl transition shadow-2xs"
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
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] overflow-hidden shadow-xs">
          <div className="px-6 py-4 border-b border-[#E8E2D8] bg-[#F5F1EA] flex items-center justify-between">
            <h2 className="text-sm font-bold text-[#292722]">
              Shared Requisitions ({requisitions.length})
            </h2>
            <Link
              href="/client/requisitions"
              className="text-xs font-semibold text-[#756653] hover:text-[#5F5243]"
            >
              Manage &rarr;
            </Link>
          </div>
          {requisitions.length === 0 ? (
            <div className="px-6 py-10 text-center text-[#918A80] text-xs">
              No shared requisitions found. Requisitions assigned to your organization will appear here.
            </div>
          ) : (
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 p-6">
              {requisitions.map((req) => (
                <div
                  key={req.id}
                  className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl p-5 hover:border-[#D9D1C5] transition flex flex-col justify-between shadow-2xs"
                >
                  <div>
                    <span className="text-[10px] font-semibold text-[#2A5A35] bg-[#EEF6F0] border border-[#C4E2CC] px-2 py-0.5 rounded-full uppercase">
                      {req.status}
                    </span>
                    <h3 className="font-semibold text-[#292722] text-sm mt-2">
                      {req.title}
                    </h3>
                    {req.location && (
                      <p className="text-xs text-[#6F6A61] mt-0.5">{req.location}</p>
                    )}
                  </div>
                  <div className="mt-4 pt-3 border-t border-[#EFEAE2] flex items-center justify-between text-xs">
                    <span className="text-[#6F6A61] font-medium">
                      {req.submissions_count} candidate{req.submissions_count === 1 ? "" : "s"} submitted
                    </span>
                    <Link
                      href={`/client/requisitions/${req.id}`}
                      className="text-[#756653] font-semibold hover:underline"
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
