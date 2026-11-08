"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type { CurrentUser, RecruiterDashboardData } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [data, setData] = useState<RecruiterDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    async function load() {
      try {
        const [currentUser, dashboardData] = await Promise.all([
          api.getCurrentUser(),
          api.getRecruiterDashboard(),
        ]);
        if (currentUser.role === "client_hiring_manager") {
          router.replace("/client");
          return;
        }
        setUser(currentUser);
        setData(dashboardData);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-[#756653] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-[#6F6A61] text-sm font-medium">Loading workspace dashboard…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="bg-[#FFFFFF] border border-[#EFC2C2] rounded-2xl p-8 max-w-sm text-center shadow-xs">
          <div className="w-10 h-10 rounded-full bg-[#FDF0F0] text-[#7A2525] flex items-center justify-center mx-auto mb-3">
            !
          </div>
          <p className="text-[#7A2525] font-semibold text-sm mb-4">{error}</p>
          <button
            onClick={() => router.push("/login")}
            className="text-xs font-semibold text-[#756653] hover:underline"
          >
            Back to login
          </button>
        </div>
      </div>
    );
  }

  const isRecruiter = user?.role === "recruiter";
  const metrics = data?.metrics;
  const processing = data?.processing;
  const requisitions = data?.requisitions ?? [];
  const activities = data?.recent_activity ?? [];

  return (
    <div className="min-h-screen bg-[#FAF9F6] flex flex-col selection:bg-[#EDE5D9] selection:text-[#292722]">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-8">
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#E8E2D8]">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-[#292722] tracking-tight">Recruiter Workspace</h1>
              <span className="text-[11px] font-semibold uppercase tracking-wider bg-[#EDE5D9] text-[#756653] px-2 py-0.5 rounded-full border border-[#D9D1C5]">
                Live Pipeline
              </span>
            </div>
            <p className="text-[#6F6A61] text-sm mt-1">
              Welcome back, <span className="font-medium text-[#292722]">{user?.display_name ?? user?.email}</span>. Real-time hiring pipeline and candidate telemetry.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/candidates"
              className="inline-flex items-center gap-1.5 bg-[#FFFFFF] border border-[#E8E2D8] hover:bg-[#F5F1EA] text-[#292722] text-xs font-semibold px-3.5 py-2 rounded-xl transition-colors shadow-2xs"
            >
              Browse Candidates
            </Link>
            {isRecruiter && (
              <Link
                href="/requisitions/new"
                className="inline-flex items-center gap-1.5 bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] text-xs font-semibold px-3.5 py-2 rounded-xl transition-colors shadow-2xs"
              >
                + Create Requisition
              </Link>
            )}
          </div>
        </div>

        {/* 8 Aggregated Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Active Requisitions</span>
              <span className="w-2 h-2 rounded-full bg-[#2A5A35]" />
            </div>
            <p className="text-2xl font-bold text-[#292722] mt-2">{metrics?.active_requisitions ?? 0}</p>
            <p className="text-xs text-[#918A80] mt-1">Live hiring requisitions</p>
          </div>

          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Total Candidates</span>
              <span className="w-2 h-2 rounded-full bg-[#756653]" />
            </div>
            <p className="text-2xl font-bold text-[#292722] mt-2">{metrics?.total_candidates ?? 0}</p>
            <p className="text-xs text-[#918A80] mt-1">Unique parsed profiles</p>
          </div>

          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Resumes Processed</span>
              <span className="w-2 h-2 rounded-full bg-[#2A5A35]" />
            </div>
            <p className="text-2xl font-bold text-[#292722] mt-2">{metrics?.resumes_processed ?? 0}</p>
            <p className="text-xs text-[#918A80] mt-1">Successfully parsed</p>
          </div>

          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Awaiting Processing</span>
              <span className="w-2 h-2 rounded-full bg-[#7A5212]" />
            </div>
            <p className="text-2xl font-bold text-[#7A5212] mt-2">{metrics?.resumes_pending ?? 0}</p>
            <p className="text-xs text-[#918A80] mt-1">In background ingestion</p>
          </div>

          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Completed Evaluations</span>
              <span className="w-2 h-2 rounded-full bg-[#264D6B]" />
            </div>
            <p className="text-2xl font-bold text-[#292722] mt-2">{metrics?.completed_evaluations ?? 0}</p>
            <p className="text-xs text-[#918A80] mt-1">Scorecard grounded</p>
          </div>

          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Awaiting Review</span>
              <span className="w-2 h-2 rounded-full bg-[#7A5212]" />
            </div>
            <p className="text-2xl font-bold text-[#7A5212] mt-2">{metrics?.candidates_awaiting_review ?? 0}</p>
            <p className="text-xs text-[#918A80] mt-1">Evaluated, pending decision</p>
          </div>

          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Shortlisted</span>
              <span className="w-2 h-2 rounded-full bg-[#2A5A35]" />
            </div>
            <p className="text-2xl font-bold text-[#2A5A35] mt-2">{metrics?.candidates_shortlisted ?? 0}</p>
            <p className="text-xs text-[#918A80] mt-1">Internally accepted</p>
          </div>

          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Failed Ingestion Jobs</span>
              <span className="w-2 h-2 rounded-full bg-[#7A2525]" />
            </div>
            <p className={`text-2xl font-bold mt-2 ${metrics?.failed_jobs ? "text-[#7A2525]" : "text-[#292722]"}`}>
              {metrics?.failed_jobs ?? 0}
            </p>
            <p className="text-xs text-[#918A80] mt-1">Eligible for retry</p>
          </div>
        </div>

        {/* Processing Health Overview Bar */}
        {processing && (
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-[#292722]">Document Processing Telemetry</h3>
              <p className="text-xs text-[#6F6A61]">
                {processing.total_uploaded} total files uploaded across batches • {processing.total_processed} parsed • {processing.total_failed} parsing errors
              </p>
            </div>
            <div className="flex items-center gap-6">
              <div className="w-48">
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-medium text-[#6F6A61]">Parse Success Rate</span>
                  <span className="font-bold text-[#2A5A35]">{processing.success_rate_percent}%</span>
                </div>
                <div className="w-full h-2.5 bg-[#F5F1EA] rounded-full overflow-hidden border border-[#E8E2D8]">
                  <div
                    className="h-full bg-[#2A5A35] rounded-full transition-all"
                    style={{ width: `${Math.min(100, Math.max(0, processing.success_rate_percent))}%` }}
                  />
                </div>
              </div>
              <div className="text-right border-l border-[#EFEAE2] pl-6">
                <span className="text-[11px] uppercase tracking-wider text-[#918A80] block font-semibold">Queue Status</span>
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#292722] mt-0.5">
                  <span className={`w-2 h-2 rounded-full ${processing.total_pending > 0 ? "bg-[#7A5212] animate-pulse" : "bg-[#2A5A35]"}`} />
                  {processing.total_pending > 0 ? `${processing.total_pending} In Progress` : "Idle / Up to Date"}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* 2-Column Section: Requisition Performance Table & Recent Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left: Requisition Performance Table (2 Cols) */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] shadow-xs overflow-hidden">
              <div className="px-6 py-4 border-b border-[#E8E2D8] bg-[#F5F1EA] flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-[#292722] text-sm">Active Requisition Performance</h2>
                  <p className="text-xs text-[#6F6A61] mt-0.5">Evaluation progress and scores across positions</p>
                </div>
                <Link
                  href="/requisitions"
                  className="text-xs font-semibold text-[#756653] hover:text-[#5F5243] hover:underline"
                >
                  Manage all ({requisitions.length}) →
                </Link>
              </div>

              {requisitions.length === 0 ? (
                <div className="px-6 py-12 text-center">
                  <p className="text-[#6F6A61] text-sm">No requisitions created yet.</p>
                  {isRecruiter && (
                    <Link
                      href="/requisitions/new"
                      className="mt-3 inline-block text-xs font-semibold text-[#FAF9F6] bg-[#756653] hover:bg-[#5F5243] px-3.5 py-1.5 rounded-xl transition-colors shadow-2xs"
                    >
                      Create Requisition
                    </Link>
                  )}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#F5F1EA] border-b border-[#E8E2D8] text-[#6F6A61] uppercase tracking-wider font-semibold">
                      <tr>
                        <th className="px-5 py-3">Position</th>
                        <th className="px-4 py-3 text-center">Candidates</th>
                        <th className="px-4 py-3 text-center">Evaluated</th>
                        <th className="px-4 py-3 text-center">Avg / Top Score</th>
                        <th className="px-4 py-3 text-center">Pending Review</th>
                        <th className="px-4 py-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#EFEAE2] text-[#292722]">
                      {requisitions.map((req) => (
                        <tr
                          key={req.id}
                          className="hover:bg-[#FAF9F6] transition-colors"
                        >
                          <td className="px-5 py-3.5">
                            <Link href={`/requisitions/${req.id}`} className="font-semibold text-[#292722] hover:text-[#756653]">
                              {req.title}
                            </Link>
                            <div className="flex items-center gap-2 mt-0.5 text-[#918A80]">
                              {req.location && <span>{req.location}</span>}
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                                  req.status === "active"
                                    ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                                    : req.status === "archived"
                                    ? "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]"
                                    : "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                                }`}
                              >
                                {req.status}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3.5 text-center font-medium">
                            {req.candidate_count}
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            <span className="font-semibold text-[#292722]">{req.evaluated_count}</span>
                            {req.candidate_count > 0 && (
                              <span className="text-[10px] text-[#918A80] block">
                                ({Math.round((req.evaluated_count / req.candidate_count) * 100)}%)
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            {req.average_score !== null ? (
                              <div>
                                <span className="font-bold text-[#292722]">{req.average_score}</span>
                                <span className="text-[#918A80]"> / {req.top_score}</span>
                              </div>
                            ) : (
                              <span className="text-[#918A80]">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            {req.pending_reviews_count > 0 ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-[#FDF6E7] text-[#7A5212] border border-[#F1DCAC]">
                                {req.pending_reviews_count} pending
                              </span>
                            ) : (
                              <span className="text-[#918A80]">0</span>
                            )}
                          </td>
                          <td className="px-4 py-3.5 text-right">
                            <Link
                              href={`/requisitions/${req.id}`}
                              className="text-xs font-semibold text-[#756653] hover:text-[#5F5243] hover:underline"
                            >
                              Open →
                            </Link>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Right: Recent Activity Timeline (1 Col) */}
          <div className="space-y-4">
            <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] shadow-xs p-5">
              <div className="flex items-center justify-between pb-3 border-b border-[#E8E2D8]">
                <h3 className="font-semibold text-[#292722] text-sm">Recent Activity</h3>
                <span className="text-[10px] uppercase font-bold text-[#918A80]">Live Timeline</span>
              </div>

              {activities.length === 0 ? (
                <div className="py-8 text-center text-[#918A80] text-xs">
                  No recent activity recorded yet.
                </div>
              ) : (
                <div className="flow-root mt-4">
                  <ul className="-mb-6">
                    {activities.slice(0, 10).map((act, idx) => {
                      const isLast = idx === Math.min(activities.length, 10) - 1;
                      const timeStr = new Date(act.timestamp).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      });
                      const dateStr = new Date(act.timestamp).toLocaleDateString([], {
                        month: "short",
                        day: "numeric",
                      });

                      // Type icons / badge colors
                      let dotColor = "bg-[#756653]";
                      if (act.type === "evaluation_completed") dotColor = "bg-[#2A5A35]";
                      if (act.type === "review_recorded") dotColor = "bg-[#7A5212]";
                      if (act.type === "note_added") dotColor = "bg-[#A8957D]";

                      return (
                        <li key={act.id}>
                          <div className="relative pb-6">
                            {!isLast && (
                              <span
                                className="absolute top-3 left-2 -ml-px h-full w-0.5 bg-[#E8E2D8]"
                                aria-hidden="true"
                              />
                            )}
                            <div className="relative flex items-start space-x-3">
                              <div>
                                <span className={`h-4 w-4 rounded-full ${dotColor} flex items-center justify-center ring-4 ring-[#FFFFFF]`} />
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="text-xs font-semibold text-[#292722]">
                                  {act.title}
                                </div>
                                <p className="text-xs text-[#6F6A61] mt-0.5 leading-relaxed">
                                  {act.description}
                                </p>
                                <div className="flex items-center gap-2 mt-1 text-[10px] text-[#918A80]">
                                  <span>{dateStr} at {timeStr}</span>
                                  {act.actor_name && (
                                    <>
                                      <span>•</span>
                                      <span className="font-medium text-[#6F6A61]">{act.actor_name}</span>
                                    </>
                                  )}
                                </div>
                              </div>
                            </div>
                          </div>
                        </li>
                      );
                    })}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
