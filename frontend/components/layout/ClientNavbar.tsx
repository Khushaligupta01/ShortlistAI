"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { clearTokens, getRefreshToken } from "@/lib/auth";
import type { CurrentUser } from "@/lib/types";

interface ClientNavbarProps {
  user: CurrentUser | null;
}

export default function ClientNavbar({ user }: ClientNavbarProps) {
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

  return (
    <nav className="bg-white border-b border-slate-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Left: Brand + Nav Links */}
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

        {/* Right: Security Badge & Profile */}
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500 bg-slate-50 border border-slate-200 px-2.5 py-1 rounded-md">
            <svg className="w-3.5 h-3.5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <span>Anonymized PII Protected</span>
          </div>

          <div className="h-4 w-px bg-slate-200" />

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

