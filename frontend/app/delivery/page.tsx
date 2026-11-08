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
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#756653] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF9F6] selection:bg-[#EDE5D9] selection:text-[#292722]">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        <div className="pb-2 border-b border-[#E8E2D8]">
          <span className="text-xs uppercase tracking-wider font-semibold text-[#756653] bg-[#EDE5D9] border border-[#D9D1C5] px-2.5 py-0.5 rounded-full">
            Executive Telemetry
          </span>
          <h1 className="text-2xl sm:text-3xl font-bold text-[#292722] tracking-tight mt-2">
            Client Delivery & Pipeline Performance
          </h1>
          <p className="text-xs text-[#6F6A61] mt-1">
            Organization-wide hiring pipeline health, submission throughput, and client conversion ratios.
          </p>
        </div>

        {error && (
          <div className="bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] p-4 rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {/* Funnel Conversion Metrics */}
        <div className="grid sm:grid-cols-4 gap-4">
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Total Submissions</p>
            <p className="text-3xl font-black text-[#292722] mt-2">
              {summary?.total_submissions ?? 0}
            </p>
            <p className="text-xs text-[#918A80] mt-1">Across all active requisitions</p>
          </div>

          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Shortlist Conversion</p>
            <p className="text-3xl font-black text-[#2A5A35] mt-2">
              {summary?.conversion_shortlist_rate ?? 0}%
            </p>
            <p className="text-xs text-[#918A80] mt-1">Submitted to shortlisted</p>
          </div>

          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Interview Conversion</p>
            <p className="text-3xl font-black text-[#264D6B] mt-2">
              {summary?.conversion_interview_rate ?? 0}%
            </p>
            <p className="text-xs text-[#918A80] mt-1">Submitted to interview</p>
          </div>

          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-5 shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Hire Conversion</p>
            <p className="text-3xl font-black text-[#756653] mt-2">
              {summary?.conversion_hire_rate ?? 0}%
            </p>
            <p className="text-xs text-[#918A80] mt-1">Submitted to placed / hired</p>
          </div>
        </div>

        {/* Client Accounts Breakdown Table */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] shadow-xs overflow-hidden">
          <div className="px-6 py-4 border-b border-[#E8E2D8] bg-[#F5F1EA] flex items-center justify-between">
            <h2 className="text-base font-bold text-[#292722]">
              Client Accounts Breakdown
            </h2>
            <Link
              href="/submissions"
              className="text-xs font-semibold text-[#756653] hover:text-[#5F5243]"
            >
              Manage submissions &rarr;
            </Link>
          </div>

          {!summary?.clients || summary.clients.length === 0 ? (
            <div className="p-12 text-center text-[#918A80] text-xs">
              No client activity recorded yet.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="bg-[#F5F1EA] border-b border-[#E8E2D8] text-[#6F6A61] font-semibold uppercase tracking-wider">
                    <th className="px-6 py-3.5">Client Company</th>
                    <th className="px-6 py-3.5">Active Requisitions</th>
                    <th className="px-6 py-3.5">Total Submissions</th>
                    <th className="px-6 py-3.5">Shortlisted</th>
                    <th className="px-6 py-3.5">Interviews</th>
                    <th className="px-6 py-3.5">Hires</th>
                    <th className="px-6 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EFEAE2]">
                  {summary.clients.map((c) => (
                    <tr key={c.client_organization_id} className="hover:bg-[#FAF9F6] transition">
                      <td className="px-6 py-4 font-bold text-[#292722] text-sm">
                        {c.client_organization_name}
                      </td>
                      <td className="px-6 py-4 font-semibold text-[#6F6A61]">
                        {c.active_requisitions_count}
                      </td>
                      <td className="px-6 py-4 font-bold text-[#292722]">
                        {c.total_submissions}
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-[#EEF6F0] text-[#2A5A35] border border-[#C4E2CC] font-bold px-2 py-0.5 rounded-full">
                          {c.shortlisted_count}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-[#EDF4F9] text-[#264D6B] border border-[#C6DDEE] font-bold px-2 py-0.5 rounded-full">
                          {c.interview_count}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className="bg-[#EDE5D9] text-[#756653] border border-[#D9D1C5] font-bold px-2 py-0.5 rounded-full">
                          {c.hired_count}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href={`/submissions?client_org_id=${c.client_organization_id}`}
                          className="text-[#756653] hover:text-[#5F5243] font-semibold text-xs"
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
