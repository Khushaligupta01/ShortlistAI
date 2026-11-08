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
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <ClientNavbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Shared Requisitions</h1>
          <p className="text-sm text-slate-500 mt-1">
            Job requisitions assigned to your organization for candidate shortlisting.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">
            {error}
          </div>
        )}

        {requisitions.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400 text-sm">
            No requisitions currently shared with your organization.
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {requisitions.map((req) => (
              <div
                key={req.id}
                className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm flex flex-col justify-between hover:border-emerald-300 transition"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] uppercase font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                      {req.status}
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {new Date(req.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <h3 className="font-bold text-slate-900 text-base">{req.title}</h3>
                  {req.location && (
                    <p className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                      <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                      {req.location}
                    </p>
                  )}
                </div>

                <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <div className="text-xs">
                    <span className="font-semibold text-slate-800">
                      {req.submissions_count}
                    </span>{" "}
                    <span className="text-slate-500">submitted</span>
                    {req.awaiting_review_count > 0 && (
                      <span className="ml-2 bg-amber-100 text-amber-800 font-bold px-1.5 py-0.5 rounded text-[10px]">
                        {req.awaiting_review_count} to review
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Link
                      href={`/client/submissions?requisition_id=${req.id}`}
                      className="text-xs font-semibold text-slate-600 hover:text-slate-900"
                    >
                      Candidates
                    </Link>
                    <Link
                      href={`/client/requisitions/${req.id}`}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition"
                    >
                      View Details
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
