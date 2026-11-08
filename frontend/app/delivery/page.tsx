"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import Navbar from "@/components/layout/Navbar";
import type { CurrentUser, DeliveryPipelineSummary } from "@/lib/types";

export default function DeliveryHeadOverviewPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [summary, setSummary] = useState<DeliveryPipelineSummary | null>(null);
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
        if (currentUser.role !== "delivery_head" && currentUser.role !== "admin" && currentUser.role !== "super_admin") {
          router.replace("/dashboard");
          return;
        }
        setUser(currentUser);

        const data = await api.getDeliveryPipelineSummary();
        setSummary(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load delivery summary");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        <div>
          <span className="text-xs uppercase tracking-widest font-bold text-indigo-700 bg-indigo-50 border border-indigo-200 px-2.5 py-1 rounded-full">
            Delivery Head Workspace
          </span>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-2">
            Client Delivery & Pipeline Performance
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Organization-wide hiring pipeline health, submission throughput, and client conversion ratios.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">
            {error}
          </div>
        )}

        {/* Funnel Conversion Metrics */}
        <div className="grid sm:grid-cols-4 gap-4">
          <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Submissions</p>
            <p className="text-3xl font-black text-slate-900 mt-2">
              {summary?.total_submissions ?? 0}
            </p>
            <p className="text-xs text-slate-400 mt-1">Across all active requisitions</p>
          </div>

          <div className="bg-white rounded-2xl border border-emerald-200 bg-emerald-50/20 p-5 shadow-sm">
            <p className="text-xs font-semibold text-emerald-700 uppercase tracking-wider">Shortlist Conversion</p>
            <p className="text-3xl font-black text-emerald-700 mt-2">
              {summary?.conversion_shortlist_rate ?? 0}%
            </p>
            <p className="text-xs text-emerald-600 mt-1">Submitted to shortlisted</p>
          </div>

          <div className="bg-white rounded-2xl border border-blue-200 bg-blue-50/20 p-5 shadow-sm">
            <p className="text-xs font-semibold text-blue-700 uppercase tracking-wider">Interview Conversion</p>
            <p className="text-3xl font-black text-blue-700 mt-2">
              {summary?.conversion_interview_rate ?? 0}%
            </p>
            <p className="text-xs text-blue-600 mt-1">Submitted to interview</p>
          </div>

          <div className="bg-white rounded-2xl border border-purple-200 bg-purple-50/20 p-5 shadow-sm">
            <p className="text-xs font-semibold text-purple-700 uppercase tracking-wider">Hire Conversion</p>
            <p className="text-3xl font-black text-purple-700 mt-2">
              {summary?.conversion_hire_rate ?? 0}%
            </p>
            <p className="text-xs text-purple-600 mt-1">Submitted to placed / hired</p>
          </div>
        </div>

        {/* Client Accounts Breakdown Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="text-base font-bold text-slate-900">
              Client Accounts Breakdown
            </h2>
            <Link
              href="/submissions"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
            >
              Manage submissions &rarr;
            </Link>
          </div>

          {!summary?.clients || summary.clients.length === 0 ? (
            <div className="p-12 text-center text-slate-400 text-sm">
              No client activity recorded yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-semibold uppercase tracking-wider">
                    <th className="px-6 py-3">Client Company</th>
                    <th className="px-6 py-3">Active Requisitions</th>
                    <th className="px-6 py-3">Total Submissions</th>
                    <th className="px-6 py-3">Shortlisted</th>
                    <th className="px-6 py-3">Interviews</th>
                    <th className="px-6 py-3">Hires</th>
                    <th className="px-6 py-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {summary.clients.map((c) => (
                    <tr key={c.client_organization_id} className="hover:bg-slate-50 transition">
                      <td className="px-6 py-4 font-bold text-slate-900 text-sm">
                        {c.client_organization_name}
                      </td>
                      <td className="px-6 py-4 font-semibold text-slate-700">
                        {c.active_requisitions_count}
                      </td>
                      <td className="px-6 py-4 font-bold text-slate-800">
                        {c.total_submissions}
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded">
                          {c.shortlisted_count}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-blue-100 text-blue-800 font-bold px-2 py-0.5 rounded">
                          {c.interview_count}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-green-100 text-green-900 font-black px-2 py-0.5 rounded">
                          {c.hired_count}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href={`/submissions?client_org_id=${c.client_organization_id}`}
                          className="text-indigo-600 hover:text-indigo-800 font-semibold text-xs"
                        >
                          View Candidates &rarr;
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

