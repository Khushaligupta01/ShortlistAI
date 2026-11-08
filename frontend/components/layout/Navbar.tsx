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
      <nav className="bg-[#FFFFFF] border-b border-[#E8E2D8] sticky top-0 z-30 shadow-2xs">
        <div className="max-w-7xl mx-auto px-6 h-15 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link
              href="/client"
              className="flex items-center gap-2 font-bold text-[#292722] text-lg hover:text-[#756653] transition-colors"
            >
              <span className="w-7 h-7 rounded-md bg-[#756653] text-[#FAF9F6] flex items-center justify-center text-xs font-black shadow-xs">
                S
              </span>
              <span>ShortlistAI</span>
              <span className="text-[10px] font-semibold bg-[#EDE5D9] text-[#756653] px-2 py-0.5 rounded-full uppercase tracking-wider">
                Client Portal
              </span>
            </Link>
            <div className="flex items-center gap-1">
              <Link
                href="/client"
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  pathname === "/client"
                    ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                    : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
                }`}
              >
                Dashboard
              </Link>
              <Link
                href="/client/requisitions"
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  pathname?.startsWith("/client/requisitions")
                    ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                    : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
                }`}
              >
                Shared Requisitions
              </Link>
              <Link
                href="/client/submissions"
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  pathname?.startsWith("/client/submissions")
                    ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                    : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
                }`}
              >
                Candidates / Shortlist
              </Link>
              <Link
                href="/client/requests"
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  pathname?.startsWith("/client/requests")
                    ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                    : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
                }`}
              >
                My Requests
              </Link>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-3">
              <div className="text-right">
                <p className="text-xs font-semibold text-[#292722]">
                  {user?.display_name || user?.email}
                </p>
                <span className="text-[10px] uppercase tracking-wide bg-[#EDE5D9] text-[#756653] px-1.5 py-0.5 rounded font-semibold">
                  Client Hiring Manager
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="text-xs font-semibold text-[#6F6A61] hover:text-[#292722] transition-colors px-2.5 py-1.5 rounded-md hover:bg-[#E8E2D8]"
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
    <nav className="bg-[#FFFFFF] border-b border-[#E8E2D8] sticky top-0 z-30 shadow-2xs">
      <div className="max-w-7xl mx-auto px-6 h-15 flex items-center justify-between">
        {/* Left: Brand + Nav Links */}
        <div className="flex items-center gap-8">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 font-bold text-[#292722] text-lg hover:text-[#756653] transition-colors"
          >
            <span className="w-7 h-7 rounded-md bg-[#756653] text-[#FAF9F6] flex items-center justify-center text-xs font-black shadow-xs">
              S
            </span>
            <span>ShortlistAI</span>
          </Link>
          <div className="flex items-center gap-1">
            <Link
              href="/dashboard"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname === "/dashboard"
                  ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                  : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
              }`}
            >
              Dashboard
            </Link>
            <Link
              href="/requisitions"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname?.startsWith("/requisitions") && pathname !== "/requisitions/new"
                  ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                  : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
              }`}
            >
              Requisitions
            </Link>
            <Link
              href="/candidates"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname?.startsWith("/candidates")
                  ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                  : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
              }`}
            >
              Candidates
            </Link>
            <Link
              href="/pipeline"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname === "/pipeline"
                  ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                  : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
              }`}
            >
              Pipeline
            </Link>
            <Link
              href="/submissions"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname === "/submissions"
                  ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                  : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
              }`}
            >
              Client Submissions
            </Link>
            <Link
              href="/privacy"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname?.startsWith("/privacy")
                  ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                  : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
              }`}
            >
              Privacy & Consent
            </Link>
            <Link
              href="/governance"
              className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                pathname === "/governance"
                  ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                  : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
              }`}
            >
              AI Governance
            </Link>
            {isDeliveryHead && (
              <Link
                href="/delivery"
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  pathname === "/delivery"
                    ? "bg-[#EDE5D9] text-[#292722] font-semibold border border-[#E8E2D8]"
                    : "text-[#6F6A61] hover:text-[#292722] hover:bg-[#F5F1EA]"
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
              className="inline-flex items-center gap-1.5 bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors shadow-2xs"
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

          <div className="h-4 w-px bg-[#E8E2D8]" />

          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs font-semibold text-[#292722]">
                {user?.display_name || user?.email}
              </p>
              <span className="text-[10px] uppercase tracking-wide bg-[#EDE5D9] text-[#756653] px-1.5 py-0.5 rounded font-semibold">
                {roleLabels[user?.role ?? ""] ?? user?.role}
              </span>
            </div>
            <button
              onClick={handleLogout}
              className="text-xs font-semibold text-[#6F6A61] hover:text-[#292722] transition-colors px-2.5 py-1.5 rounded-md hover:bg-[#E8E2D8]"
            >
              Sign out
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
