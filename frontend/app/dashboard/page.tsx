"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type { CurrentUser, RequisitionListResponse } from "@/lib/types";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [requisitions, setRequisitions] = useState<RequisitionListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    async function load() {
      try {
        const [currentUser, reqs] = await Promise.all([
          api.getCurrentUser(),
          api.getRequisitions(),
        ]);
        if (currentUser.role === "client_hiring_manager") {
          router.replace("/client");
          return;
        }
        setUser(currentUser);
        setRequisitions(reqs);
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
          <p className="text-slate-500 text-sm">Loading…</p>
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

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar user={user} />

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
            <p className="text-slate-500 text-sm mt-0.5">
              Welcome back, {user?.display_name ?? user?.email}
            </p>
          </div>
          {isRecruiter && (
            <Link
              href="/requisitions/new"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-4 py-2.5 rounded-lg transition-colors shadow-sm self-start sm:self-auto"
            >
              + Create Requisition
            </Link>
          )}
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
              Active Requisitions
            </p>
            <p className="text-3xl font-bold text-slate-900 mt-1">
              {requisitions?.total ?? 0}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
              Total Candidates
            </p>
            <p className="text-3xl font-bold text-slate-900 mt-1">—</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
              Pending Submissions
            </p>
            <p className="text-3xl font-bold text-slate-900 mt-1">—</p>
          </div>
        </div>

        {/* Requisitions List */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs">
          <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
            <h2 className="font-semibold text-slate-800 text-sm">Recent Requisitions</h2>
            <Link
              href="/requisitions"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:underline"
            >
              View all →
            </Link>
          </div>
          {requisitions?.items.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-slate-500 text-sm">
                No requisitions yet. Create your first requisition to get started.
              </p>
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
            <ul className="divide-y divide-slate-100">
              {requisitions?.items.map((req) => (
                <li
                  key={req.id}
                  onClick={() => router.push(`/requisitions/${req.id}`)}
                  className="px-6 py-4 flex items-center justify-between hover:bg-slate-50 transition-colors cursor-pointer"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-slate-800 text-sm">{req.title}</p>
                      {req.location && (
                        <span className="text-xs text-slate-400">• {req.location}</span>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Created {new Date(req.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${
                        req.status === "active"
                          ? "bg-emerald-100 text-emerald-700"
                          : req.status === "archived"
                          ? "bg-slate-100 text-slate-500"
                          : "bg-amber-100 text-amber-700"
                      }`}
                    >
                      {req.status}
                    </span>
                    <span className="text-xs text-slate-400">→</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
