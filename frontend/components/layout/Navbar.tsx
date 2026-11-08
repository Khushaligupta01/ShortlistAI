"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { clearTokens, getRefreshToken } from "@/lib/auth";
import type { CurrentUser } from "@/lib/types";

interface NavbarProps {
  user: CurrentUser | null;
}

const roleLabels: Record<string, string> = {
  recruiter: "Recruiter",
  delivery_head: "Delivery Head",
  client_hiring_manager: "Client Hiring Manager",
};

export default function Navbar({ user }: NavbarProps) {
  const router = useRouter();
  const pathname = usePathname();

  async function handleLogout() {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      await api.logout(refreshToken).catch(() => null);
    }
    clearTokens();
    router.push("/login");
  }

  const isRecruiter = user?.role === "recruiter";
  const isDeliveryHead = user?.role === "delivery_head";
  const isClient = user?.role === "client_hiring_manager";

  if (isClient) {
    return (
      <nav className="bg-white border-b border-slate-200 sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link
              href="/client"
              className="flex items-center gap-2 font-bold text-slate-900 text-lg hover:text-emerald-700 transition-colors"
            >
              <span className="w-6 h-6 rounded bg-emerald-600 text-white flex items-center justify-center text-xs font-black">
                S
              </span>
              <span>ShortlistAI</span>
              <span className="text-[11px] font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full uppercase tracking-wider">
                Client Portal
              </span>
            </Link>
            <div className="flex items-center gap-1">
              <Link
                href="/client"
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  pathname === "/client"
                    ? "bg-slate-100 text-slate-900 font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                Dashboard
              </Link>
              <Link
                href="/client/requisitions"
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  pathname?.startsWith("/client/requisitions")
                    ? "bg-slate-100 text-slate-900 font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                Shared Requisitions
              </Link>
              <Link
                href="/client/submissions"
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  pathname?.startsWith("/client/submissions")
                    ? "bg-slate-100 text-slate-900 font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                Candidates / Shortlist
              </Link>
              <Link
                href="/client/requests"
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  pathname?.startsWith("/client/requests")
                    ? "bg-slate-100 text-slate-900 font-semibold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                My Requests
              </Link>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="text-right">
                <p className="text-xs font-medium text-slate-800">
                  {user?.display_name || user?.email}
                </p>
                <span className="text-[10px] uppercase tracking-wide bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded font-semibold">
                  Client Hiring Manager
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="text-xs font-medium text-slate-500 hover:text-slate-800 transition-colors px-2 py-1 rounded hover:bg-slate-100"
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </nav>
    );
  }

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Left: Brand + Nav Links */}
        <div className="flex items-center gap-8">
          <Link
            href="/dashboard"
            className="font-bold text-slate-900 text-lg hover:text-indigo-600 transition-colors"
          >
            ShortlistAI
          </Link>
          <div className="flex items-center gap-1">
            <Link
              href="/dashboard"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname === "/dashboard"
                  ? "bg-slate-100 text-slate-900"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              Dashboard
            </Link>
            <Link
              href="/requisitions"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname?.startsWith("/requisitions") && pathname !== "/requisitions/new"
                  ? "bg-slate-100 text-slate-900"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              Requisitions
            </Link>
            <Link
              href="/candidates"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname?.startsWith("/candidates")
                  ? "bg-slate-100 text-slate-900"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              Candidates
            </Link>
            <Link
              href="/pipeline"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname === "/pipeline"
                  ? "bg-slate-100 text-slate-900"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              Pipeline
            </Link>
            <Link
              href="/submissions"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname === "/submissions"
                  ? "bg-slate-100 text-slate-900"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              Client Submissions
            </Link>
            <Link
              href="/privacy"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname?.startsWith("/privacy")
                  ? "bg-slate-100 text-slate-900 font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              Privacy & Consent
            </Link>
            <Link
              href="/governance"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname === "/governance"
                  ? "bg-slate-100 text-slate-900 font-semibold"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              AI Governance
            </Link>
            {isDeliveryHead && (
              <Link
                href="/delivery"
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  pathname === "/delivery"
                    ? "bg-slate-100 text-slate-900"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
                }`}
              >
                Delivery Overview
              </Link>
            )}
          </div>
        </div>

        {/* Right: Actions + User Profile */}
        <div className="flex items-center gap-4">
          {isRecruiter && (
            <Link
              href="/requisitions/new"
              className="inline-flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors shadow-sm"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
              New Requisition
            </Link>
          )}

          <div className="h-4 w-px bg-slate-200" />

          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs font-medium text-slate-800">
                {user?.display_name || user?.email}
              </p>
              <span className="text-[10px] uppercase tracking-wide bg-indigo-50 text-indigo-700 px-1.5 py-0.5 rounded font-semibold">
                {roleLabels[user?.role ?? ""] ?? user?.role}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="text-xs font-medium text-slate-500 hover:text-slate-800 transition-colors px-2 py-1 rounded hover:bg-slate-100"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}

