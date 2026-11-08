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
    <div className="min-h-screen bg-[#FAF9F6] selection:bg-[#EDE5D9] selection:text-[#292722]">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#E8E2D8]">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#2A5A35]" />
              <span className="text-xs font-semibold tracking-wider uppercase text-[#756653] bg-[#EDE5D9] px-2.5 py-0.5 rounded-full border border-[#D9D1C5]">
                Responsible AI & Privacy Layer
              </span>
            </div>
            <h1 className="text-2xl font-bold text-[#292722] tracking-tight mt-1">Privacy & Consent Governance</h1>
            <p className="text-xs text-[#6F6A61] mt-1">
              Persistent consent tracking, GDPR/DPDP data subject rights, secure deletion lifecycles, and tamper-resistant audit trails.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href="/privacy/consent"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-[#756653] text-[#FAF9F6] hover:bg-[#5F5243] transition-colors shadow-2xs"
            >
              Manage Consents
            </Link>
            <Link
              href="/privacy/deletions"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-xl bg-[#FFFFFF] border border-[#E8E2D8] text-[#292722] hover:bg-[#F5F1EA] transition-colors shadow-2xs"
            >
              Deletion Requests
            </Link>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {/* Regulatory Disclaimer Banner */}
        <div className="p-4 bg-[#F5F1EA] border border-[#E8E2D8] rounded-2xl flex items-start gap-3 shadow-xs">
          <svg className="w-5 h-5 text-[#756653] shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-xs text-[#6F6A61] leading-relaxed">
            <span className="font-semibold text-[#292722]">Statutory Privacy & Governance Notice:</span> ShortlistAI enforces server-side candidate data isolation, cryptographic tokenized consent verification, and secure file scrubbing. Implementation of these automated workflows does not substitute for qualified legal review or organization-specific retention policies under GDPR, India DPDP Act 2023, or SOC 2 frameworks.
          </div>
        </div>

        {/* Live Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-[#E8E2D8] shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Granted Consents</p>
            <p className="text-2xl font-bold text-[#2A5A35] mt-2">
              {loading ? "..." : stats?.granted_consents_count ?? 0}
            </p>
            <p className="text-[11px] text-[#918A80] mt-1">Active processing authorizations</p>
          </div>

          <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-[#E8E2D8] shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Withdrawn Consents</p>
            <p className="text-2xl font-bold text-[#7A5212] mt-2">
              {loading ? "..." : stats?.withdrawn_consents_count ?? 0}
            </p>
            <p className="text-[11px] text-[#918A80] mt-1">Processing restricted</p>
          </div>

          <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-[#E8E2D8] shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Data Exports Ready</p>
            <p className="text-2xl font-bold text-[#264D6B] mt-2">
              {loading ? "..." : stats?.completed_exports_count ?? 0}
            </p>
            <p className="text-[11px] text-[#918A80] mt-1">
              {stats?.pending_data_requests_count ? `${stats.pending_data_requests_count} pending` : "All requests served"}
            </p>
          </div>

          <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-[#E8E2D8] shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Completed Deletions</p>
            <p className="text-2xl font-bold text-[#292722] mt-2">
              {loading ? "..." : stats?.completed_deletions_count ?? 0}
            </p>
            <p className="text-[11px] text-[#918A80] mt-1">
              {stats?.active_legal_holds_count ? `${stats.active_legal_holds_count} legal hold(s)` : "Files & PII scrubbed"}
            </p>
          </div>
        </div>

        {/* Quick Navigation Hub */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Link
            href="/privacy/consent"
            className="group p-5 bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] hover:border-[#D9D1C5] hover:shadow-sm transition-all"
          >
            <div className="w-9 h-9 rounded-xl bg-[#EDE5D9] text-[#756653] border border-[#D9D1C5] flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-[#756653] group-hover:text-[#FAF9F6] transition-colors">
              C
            </div>
            <h3 className="font-semibold text-[#292722] text-sm">Consent Management</h3>
            <p className="text-xs text-[#6F6A61] mt-1">Create consent links, inspect purpose, and manage candidate withdrawals.</p>
          </Link>

          <Link
            href="/privacy/data-requests"
            className="group p-5 bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] hover:border-[#D9D1C5] hover:shadow-sm transition-all"
          >
            <div className="w-9 h-9 rounded-xl bg-[#EDE5D9] text-[#756653] border border-[#D9D1C5] flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-[#756653] group-hover:text-[#FAF9F6] transition-colors">
              E
            </div>
            <h3 className="font-semibold text-[#292722] text-sm">Data Access & Export</h3>
            <p className="text-xs text-[#6F6A61] mt-1">Generate comprehensive portable JSON exports of candidate personal records.</p>
          </Link>

          <Link
            href="/privacy/deletions"
            className="group p-5 bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] hover:border-[#D9D1C5] hover:shadow-sm transition-all"
          >
            <div className="w-9 h-9 rounded-xl bg-[#EDE5D9] text-[#756653] border border-[#D9D1C5] flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-[#756653] group-hover:text-[#FAF9F6] transition-colors">
              D
            </div>
            <h3 className="font-semibold text-[#292722] text-sm">Deletion Requests</h3>
            <p className="text-xs text-[#6F6A61] mt-1">Review &ldquo;Right to be Forgotten&rdquo; requests, evaluate legal holds, and execute file wipes.</p>
          </Link>

          <Link
            href="/privacy/audit"
            className="group p-5 bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] hover:border-[#D9D1C5] hover:shadow-sm transition-all"
          >
            <div className="w-9 h-9 rounded-xl bg-[#EDE5D9] text-[#756653] border border-[#D9D1C5] flex items-center justify-center font-bold text-sm mb-3 group-hover:bg-[#756653] group-hover:text-[#FAF9F6] transition-colors">
              A
            </div>
            <h3 className="font-semibold text-[#292722] text-sm">Audit Log Explorer</h3>
            <p className="text-xs text-[#6F6A61] mt-1">Inspect immutable, append-only security and privacy events with sanitized metadata.</p>
          </Link>
        </div>

        {/* Recent Audit Events Stream */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] overflow-hidden shadow-xs">
          <div className="px-6 py-4 border-b border-[#E8E2D8] bg-[#F5F1EA] flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-[#292722]">Recent Privacy & Security Audit Events</h2>
              <p className="text-xs text-[#6F6A61]">Live immutable activity feed for your organization</p>
            </div>
            <Link
              href="/privacy/audit"
              className="text-xs font-semibold text-[#756653] hover:text-[#5F5243] transition-colors"
            >
              View all events →
            </Link>
          </div>

          <div className="divide-y divide-[#EFEAE2]">
            {loading ? (
              <div className="p-8 text-center text-sm text-[#918A80]">Loading audit feed...</div>
            ) : !stats?.recent_audit_events?.length ? (
              <div className="p-8 text-center text-sm text-[#918A80]">No recent audit events recorded.</div>
            ) : (
              stats.recent_audit_events.map((event) => (
                <div key={event.id} className="p-4 hover:bg-[#FAF9F6] transition-colors flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <span className="w-2 h-2 rounded-full bg-[#756653] mt-1.5 shrink-0" />
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold text-[#292722] font-mono">
                          {event.event_type}
                        </span>
                        {event.resource_type && (
                          <span className="text-[10px] uppercase font-semibold tracking-wider bg-[#F5F1EA] text-[#6F6A61] px-1.5 py-0.5 rounded border border-[#E8E2D8]">
                            {event.resource_type}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-[#6F6A61] mt-0.5">
                        Actor: {event.actor_name || "System"} • Resource: {event.resource_id ? event.resource_id.slice(0, 8) + "..." : "N/A"}
                      </p>
                    </div>
                  </div>
                  <span className="text-[11px] text-[#918A80] whitespace-nowrap">
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
