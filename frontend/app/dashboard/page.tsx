"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { clearTokens, getRefreshToken, isAuthenticated } from "@/lib/auth";
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
        setError(err instanceof Error ? err.message : "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [router]);

  async function handleLogout() {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      await api.logout(refreshToken).catch(() => null);
    }
    clearTokens();
    router.push("/login");
  }

  const roleLabel: Record<string, string> = {
    recruiter: "Recruiter",
    delivery_head: "Delivery Head",
    client_hiring_manager: "Client Hiring Manager",
  };

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

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Nav */}
      <nav className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="font-bold text-slate-900 text-lg">ShortlistAI</span>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600">
              {user?.display_name ?? user?.email}
              <span className="ml-2 text-xs bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full font-medium">
                {roleLabel[user?.role ?? ""] ?? user?.role}
              </span>
            </span>
            <button
              onClick={handleLogout}
              className="text-sm text-slate-500 hover:text-slate-700 transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Dashboard</h1>
        <p className="text-slate-500 text-sm mb-8">
          Welcome back, {user?.display_name ?? user?.email}
        </p>

        {/* Stats */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
              Active Requisitions
            </p>
            <p className="text-3xl font-bold text-slate-900 mt-1">
              {requisitions?.total ?? 0}
            </p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
              Total Candidates
            </p>
            <p className="text-3xl font-bold text-slate-900 mt-1">—</p>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
              Pending Submissions
            </p>
            <p className="text-3xl font-bold text-slate-900 mt-1">—</p>
          </div>
        </div>

        {/* Requisitions */}
        <div className="bg-white rounded-xl border border-slate-200">
          <div className="px-6 py-4 border-b border-slate-100">
            <h2 className="font-semibold text-slate-800">Requisitions</h2>
          </div>
          {requisitions?.items.length === 0 ? (
            <div className="px-6 py-12 text-center">
              <p className="text-slate-500 text-sm">
                No requisitions yet. Create your first requisition to get started.
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {requisitions?.items.map((req) => (
                <li key={req.id} className="px-6 py-4 flex items-center justify-between hover:bg-slate-50 transition-colors">
                  <div>
                    <p className="font-medium text-slate-800 text-sm">{req.title}</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Created {new Date(req.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${
                    req.status === "active"
                      ? "bg-emerald-100 text-emerald-700"
                      : req.status === "archived"
                      ? "bg-slate-100 text-slate-500"
                      : "bg-amber-100 text-amber-700"
                  }`}>
                    {req.status}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </main>
    </div>
  );
}
