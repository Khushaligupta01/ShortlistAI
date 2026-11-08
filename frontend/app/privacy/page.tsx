"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { CurrentUser, PrivacyDashboardStats } from "@/lib/types";

export default function PrivacyDashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [stats, setStats] = useState<PrivacyDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
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
        const data = await api.getPrivacyDashboardStats();
        setStats(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load privacy dashboard data.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-semibold tracking-wider uppercase text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                Responsible AI & Privacy Layer
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-1">Privacy & Consent Governance</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Persistent consent tracking, GDPR/DPDP data subject rights, secure deletion lifecycles, and tamper-resistant audit trails.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/privacy/consent"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 transition-colors shadow-sm"
            >
              Manage Consents
            </Link>
            <Link
              href="/privacy/deletions"
              className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-lg bg-slate-800 text-white hover:bg-slate-900 transition-colors shadow-sm"
            >
              Deletion Requests
            </Link>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Regulatory Disclaimer Banner */}
        <div className="mb-8 p-4 bg-blue-50/70 border border-blue-200 rounded-xl flex items-start gap-3">
          <svg className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-xs text-blue-900 leading-relaxed">
            <span className="font-semibold text-blue-950">Statutory Privacy & Governance Notice:</span> ShortlistAI enforces server-side candidate data isolation, cryptographic tokenized consent verification, and secure file scrubbing. Implementation of these automated workflows does not substitute for qualified legal review or organization-specific retention policies under GDPR, India DPDP Act 2023, or SOC 2 frameworks.
          </div>
        </div>

        {/* Live Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Granted Consents</p>
            <p className="text-2xl font-bold text-emerald-600 mt-2">
              {loading ? "..." : stats?.granted_consents_count ?? 0}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">Active processing authorizations</p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Withdrawn Consents</p>
            <p className="text-2xl font-bold text-amber-600 mt-2">
              {loading ? "..." : stats?.withdrawn_consents_count ?? 0}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">Processing restricted</p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Data Exports Ready</p>
            <p className="text-2xl font-bold text-indigo-600 mt-2">
              {loading ? "..." : stats?.completed_exports_count ?? 0}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              {stats?.pending_data_requests_count ? `${stats.pending_data_requests_count} pending` : "All requests served"}
            </p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Completed Deletions</p>
            <p className="text-2xl font-bold text-slate-900 mt-2">
              {loading ? "..." : stats?.completed_deletions_count ?? 0}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">
              {stats?.active_legal_holds_count ? `${stats.active_legal_holds_count} legal hold(s)` : "Files & PII scrubbed"}
            </p>
          </div>
        </div>

        {/* Quick Navigation Hub */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Link
            href="/privacy/consent"
            className="group p-5 bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all"
          >
            <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-indigo-600 group-hover:text-white transition-colors">
              C
            </div>
            <h3 className="font-semibold text-slate-900 text-sm">Consent Management</h3>
            <p className="text-xs text-slate-500 mt-1">Create consent links, inspect purpose, and manage candidate withdrawals.</p>
          </Link>

          <Link
            href="/privacy/data-requests"
            className="group p-5 bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all"
          >
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-emerald-600 group-hover:text-white transition-colors">
              E
            </div>
            <h3 className="font-semibold text-slate-900 text-sm">Data Access & Export</h3>
            <p className="text-xs text-slate-500 mt-1">Generate comprehensive portable JSON exports of candidate personal records.</p>
          </Link>

          <Link
            href="/privacy/deletions"
            className="group p-5 bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all"
          >
            <div className="w-9 h-9 rounded-lg bg-red-50 text-red-600 flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-red-600 group-hover:text-white transition-colors">
              D
            </div>
            <h3 className="font-semibold text-slate-900 text-sm">Deletion Requests</h3>
            <p className="text-xs text-slate-500 mt-1">Review &ldquo;Right to be Forgotten&rdquo; requests, evaluate legal holds, and execute file wipes.</p>
          </Link>

          <Link
            href="/privacy/audit"
            className="group p-5 bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all"
          >
            <div className="w-9 h-9 rounded-lg bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-slate-900 group-hover:text-white transition-colors">
              A
            </div>
            <h3 className="font-semibold text-slate-900 text-sm">Audit Log Explorer</h3>
            <p className="text-xs text-slate-500 mt-1">Inspect immutable, append-only security and privacy events with sanitized metadata.</p>
          </Link>
        </div>

        {/* Recent Audit Events Stream */}
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900">Recent Privacy & Security Audit Events</h2>
              <p className="text-xs text-slate-500">Live immutable activity feed for your organization</p>
            </div>
            <Link
              href="/privacy/audit"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 transition-colors"
            >
              View all events →
            </Link>
          </div>

          <div className="divide-y divide-slate-100">
            {loading ? (
              <div className="p-8 text-center text-sm text-slate-400">Loading audit feed...</div>
            ) : !stats?.recent_audit_events?.length ? (
              <div className="p-8 text-center text-sm text-slate-500">No recent audit events recorded.</div>
            ) : (
              stats.recent_audit_events.map((event) => (
                <div key={event.id} className="p-4 hover:bg-slate-50/60 transition-colors flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <span className="w-2 h-2 rounded-full bg-slate-400 mt-1.5 shrink-0" />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-slate-900 font-mono">
                          {event.event_type}
                        </span>
                        {event.resource_type && (
                          <span className="text-[10px] uppercase font-semibold tracking-wider bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">
                            {event.resource_type}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Actor: {event.actor_name || "System"} • Resource: {event.resource_id ? event.resource_id.slice(0, 8) + "..." : "N/A"}
                      </p>
                    </div>
                  </div>
                  <span className="text-[11px] text-slate-400 whitespace-nowrap">
                    {new Date(event.created_at).toLocaleString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
