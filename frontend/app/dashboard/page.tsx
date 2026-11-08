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
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-slate-500 text-sm">Loading workspace dashboard…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="bg-white border border-red-200 rounded-xl p-8 max-w-sm text-center">
          <p className="text-red-600 font-medium mb-4">{error}</p>
          <button
            onClick={() => router.push("/login")}
            className="text-indigo-600 text-sm hover:underline"
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
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-8">
        {/* Top Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Recruiter Workspace</h1>
            <p className="text-slate-500 text-sm mt-0.5">
              Welcome back, {user?.display_name ?? user?.email}. Real-time hiring pipeline and candidate telemetry.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/candidates"
              className="inline-flex items-center gap-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold px-3.5 py-2 rounded-lg transition-colors shadow-xs"
            >
              Browse Candidates
            </Link>
            {isRecruiter && (
              <Link
                href="/requisitions/new"
                className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition-colors shadow-sm"
              >
                + Create Requisition
              </Link>
            )}
          </div>
        </div>

        {/* 8 Aggregated Metric Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Active Requisitions</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">{metrics?.active_requisitions ?? 0}</p>
            <p className="text-xs text-slate-400 mt-1">Live hiring requisitions</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Candidates</span>
              <span className="w-2 h-2 rounded-full bg-indigo-500" />
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">{metrics?.total_candidates ?? 0}</p>
            <p className="text-xs text-slate-400 mt-1">Unique parsed profiles</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Resumes Processed</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">{metrics?.resumes_processed ?? 0}</p>
            <p className="text-xs text-slate-400 mt-1">Successfully parsed</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Awaiting Processing</span>
              <span className="w-2 h-2 rounded-full bg-amber-400" />
            </div>
            <p className="text-2xl font-bold text-amber-600 mt-2">{metrics?.resumes_pending ?? 0}</p>
            <p className="text-xs text-slate-400 mt-1">In background ingestion</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Completed Evaluations</span>
              <span className="w-2 h-2 rounded-full bg-blue-500" />
            </div>
            <p className="text-2xl font-bold text-slate-900 mt-2">{metrics?.completed_evaluations ?? 0}</p>
            <p className="text-xs text-slate-400 mt-1">Scorecard grounded</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Awaiting Review</span>
              <span className="w-2 h-2 rounded-full bg-amber-500" />
            </div>
            <p className="text-2xl font-bold text-amber-600 mt-2">{metrics?.candidates_awaiting_review ?? 0}</p>
            <p className="text-xs text-slate-400 mt-1">Evaluated, pending decision</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Shortlisted</span>
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
            </div>
            <p className="text-2xl font-bold text-emerald-700 mt-2">{metrics?.candidates_shortlisted ?? 0}</p>
            <p className="text-xs text-slate-400 mt-1">Internally accepted</p>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">Failed Ingestion Jobs</span>
              <span className="w-2 h-2 rounded-full bg-red-400" />
            </div>
            <p className={`text-2xl font-bold mt-2 ${metrics?.failed_jobs ? "text-red-600" : "text-slate-900"}`}>
              {metrics?.failed_jobs ?? 0}
            </p>
            <p className="text-xs text-slate-400 mt-1">Eligible for retry</p>
          </div>
        </div>

        {/* Processing Health Overview Bar */}
        {processing && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-slate-800">Document Processing Telemetry</h3>
              <p className="text-xs text-slate-500">
                {processing.total_uploaded} total files uploaded across batches • {processing.total_processed} parsed • {processing.total_failed} parsing errors
              </p>
            </div>
            <div className="flex items-center gap-6">
              <div className="w-48">
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-medium text-slate-600">Parse Success Rate</span>
                  <span className="font-bold text-emerald-600">{processing.success_rate_percent}%</span>
                </div>
                <div className="w-full h-2.5 bg-slate-100 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-emerald-500 rounded-full transition-all"
                    style={{ width: `${Math.min(100, Math.max(0, processing.success_rate_percent))}%` }}
                  />
                </div>
              </div>
              <div className="text-right border-l border-slate-100 pl-6">
                <span className="text-xs text-slate-400 block">Queue Status</span>
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700">
                  <span className={`w-2 h-2 rounded-full ${processing.total_pending > 0 ? "bg-amber-400 animate-pulse" : "bg-emerald-500"}`} />
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
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
              <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <h2 className="font-semibold text-slate-800 text-sm">Active Requisition Performance</h2>
                  <p className="text-xs text-slate-400 mt-0.5">Evaluation progress and scores across positions</p>
                </div>
                <Link
                  href="/requisitions"
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:underline"
                >
                  Manage all ({requisitions.length}) →
                </Link>
              </div>

              {requisitions.length === 0 ? (
                <div className="px-6 py-12 text-center">
                  <p className="text-slate-500 text-sm">No requisitions created yet.</p>
                  {isRecruiter && (
                    <Link
                      href="/requisitions/new"
                      className="mt-3 inline-block text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 px-3.5 py-1.5 rounded-lg transition-colors"
                    >
                      Create Requisition
                    </Link>
                  )}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-50 border-b border-slate-100 text-slate-500 uppercase tracking-wider font-semibold">
                      <tr>
                        <th className="px-5 py-3">Position</th>
                        <th className="px-4 py-3 text-center">Candidates</th>
                        <th className="px-4 py-3 text-center">Evaluated</th>
                        <th className="px-4 py-3 text-center">Avg / Top Score</th>
                        <th className="px-4 py-3 text-center">Pending Review</th>
                        <th className="px-4 py-3 text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100 text-slate-700">
                      {requisitions.map((req) => (
                        <tr
                          key={req.id}
                          className="hover:bg-slate-50/80 transition-colors"
                        >
                          <td className="px-5 py-3.5">
                            <Link href={`/requisitions/${req.id}`} className="font-semibold text-slate-900 hover:text-indigo-600">
                              {req.title}
                            </Link>
                            <div className="flex items-center gap-2 mt-0.5 text-slate-400">
                              {req.location && <span>{req.location}</span>}
                              <span
                                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                                  req.status === "active"
                                    ? "bg-emerald-100 text-emerald-700"
                                    : req.status === "archived"
                                    ? "bg-slate-100 text-slate-500"
                                    : "bg-amber-100 text-amber-700"
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
                            <span className="font-semibold text-slate-800">{req.evaluated_count}</span>
                            {req.candidate_count > 0 && (
                              <span className="text-[10px] text-slate-400 block">
                                ({Math.round((req.evaluated_count / req.candidate_count) * 100)}%)
                              </span>
                            )}
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            {req.average_score !== null ? (
                              <div>
                                <span className="font-bold text-slate-900">{req.average_score}</span>
                                <span className="text-slate-400"> / {req.top_score}</span>
                              </div>
                            ) : (
                              <span className="text-slate-400">—</span>
                            )}
                          </td>
                          <td className="px-4 py-3.5 text-center">
                            {req.pending_reviews_count > 0 ? (
                              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                                {req.pending_reviews_count} pending
                              </span>
                            ) : (
                              <span className="text-slate-400">0</span>
                            )}
                          </td>
                          <td className="px-4 py-3.5 text-right">
                            <Link
                              href={`/requisitions/${req.id}`}
                              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:underline"
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
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-5">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h3 className="font-semibold text-slate-800 text-sm">Recent Activity</h3>
                <span className="text-[10px] uppercase font-bold text-slate-400">Live Timeline</span>
              </div>

              {activities.length === 0 ? (
                <div className="py-8 text-center text-slate-400 text-xs">
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
                      let dotColor = "bg-indigo-500";
                      if (act.type === "evaluation_completed") dotColor = "bg-emerald-500";
                      if (act.type === "review_recorded") dotColor = "bg-amber-500";
                      if (act.type === "note_added") dotColor = "bg-purple-500";

                      return (
                        <li key={act.id}>
                          <div className="relative pb-6">
                            {!isLast && (
                              <span
                                className="absolute top-3 left-2 -ml-px h-full w-0.5 bg-slate-200"
                                aria-hidden="true"
                              />
                            )}
                            <div className="relative flex items-start space-x-3">
                              <div>
                                <span className={`h-4 w-4 rounded-full ${dotColor} flex items-center justify-center ring-4 ring-white`} />
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="text-xs font-semibold text-slate-800">
                                  {act.title}
                                </div>
                                <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                                  {act.description}
                                </p>
                                <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-400">
                                  <span>{dateStr} at {timeStr}</span>
                                  {act.actor_name && (
                                    <>
                                      <span>•</span>
                                      <span className="font-medium text-slate-600">{act.actor_name}</span>
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
