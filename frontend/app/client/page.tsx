"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { clearTokens, getRefreshToken, isAuthenticated } from "@/lib/auth";
import type { CurrentUser } from "@/lib/types";

export default function ClientPortalPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    api.getCurrentUser()
      .then((u) => {
        if (u.role !== "client_hiring_manager") {
          router.replace("/dashboard");
          return;
        }
        setUser(u);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load");
      })
      .finally(() => setLoading(false));
  }, [router]);

  async function handleLogout() {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      await api.logout(refreshToken).catch(() => null);
    }
    clearTokens();
    router.push("/login");
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="bg-white border border-red-200 rounded-xl p-8 max-w-sm text-center">
          <p className="text-red-600 font-medium mb-4">{error}</p>
          <button onClick={() => router.push("/login")} className="text-indigo-600 text-sm hover:underline">
            Back to login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <nav className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <span className="font-bold text-slate-900 text-lg">ShortlistAI</span>
          <div className="flex items-center gap-4">
            <span className="text-sm text-slate-600">
              {user?.display_name ?? user?.email}
              <span className="ml-2 text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-medium">
                Client Portal
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

      <main className="max-w-7xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Client Portal</h1>
        <p className="text-slate-500 text-sm mb-8">
          Review candidates submitted to your organization.
        </p>

        <div className="bg-white rounded-xl border border-slate-200 px-6 py-12 text-center">
          <p className="text-slate-500 text-sm">
            No candidates have been submitted to your organization yet.
          </p>
          <p className="text-slate-400 text-xs mt-2">
            Candidates will appear here once a recruiter submits them for your review.
          </p>
        </div>
      </main>
    </div>
  );
}
