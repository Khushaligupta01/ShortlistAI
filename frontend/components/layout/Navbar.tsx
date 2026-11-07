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
