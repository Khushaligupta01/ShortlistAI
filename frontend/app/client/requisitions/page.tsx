"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import ClientNavbar from "@/components/layout/ClientNavbar";
import type { ClientRequisitionListItem, CurrentUser } from "@/lib/types";

export default function ClientRequisitionsPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [requisitions, setRequisitions] = useState<ClientRequisitionListItem[]>([]);
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

        const reqs = await api.getClientRequisitions();
        setRequisitions(reqs);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load requisitions");
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
      <ClientNavbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="pb-2 border-b border-[#E8E2D8]">
          <h1 className="text-2xl font-bold text-[#292722] tracking-tight">Shared Requisitions</h1>
          <p className="text-xs text-[#6F6A61] mt-1">
            Job requisitions assigned to your organization for candidate shortlisting.
          </p>
        </div>

        {error && (
          <div className="bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] p-4 rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {requisitions.length === 0 ? (
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-12 text-center text-[#918A80] text-xs">
            No requisitions currently shared with your organization.
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {requisitions.map((req) => (
              <div
                key={req.id}
                className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl p-5 shadow-xs flex flex-col justify-between hover:border-[#D9D1C5] transition"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-semibold text-[#2A5A35] bg-[#EEF6F0] border border-[#C4E2CC] px-2 py-0.5 rounded-full">
                      {req.status}
                    </span>
                    <span className="text-[11px] text-[#918A80]">
                      {new Date(req.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <h3 className="font-bold text-[#292722] text-base">{req.title}</h3>
                  {req.location && (
                    <p className="text-xs text-[#6F6A61] mt-1 flex items-center gap-1">
                      <svg className="w-3.5 h-3.5 text-[#918A80]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      {req.location}
                    </p>
                  )}
                </div>

                <div className="mt-6 pt-4 border-t border-[#EFEAE2] flex items-center justify-between">
                  <div className="text-xs">
                    <span className="font-bold text-[#292722]">
                      {req.submissions_count}
                    </span>{" "}
                    <span className="text-[#6F6A61]">submitted</span>
                    {req.awaiting_review_count > 0 && (
                      <span className="ml-2 bg-[#FDF6E7] text-[#7A5212] border border-[#F1DCAC] font-semibold px-2 py-0.5 rounded-full text-[10px]">
                        {req.awaiting_review_count} to review
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/client/submissions?requisition_id=${req.id}`}
                      className="text-xs font-semibold text-[#756653] hover:text-[#5F5243]"
                    >
                      Candidates →
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
