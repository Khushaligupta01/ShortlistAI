"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type { CurrentUser, Requisition } from "@/lib/types";

export default function RequisitionsListPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [requisitions, setRequisitions] = useState<Requisition[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    async function init() {
      try {
        const u = await api.getCurrentUser();
        if (u.role === "client_hiring_manager") {
          router.replace("/client");
          return;
        }
        setUser(u);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Authentication failed");
      }
    }
    init();
  }, [router]);

  useEffect(() => {
    if (!user) return;
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const resp = await api.getRequisitions(
          page,
          20,
          statusFilter || undefined,
          search || undefined
        );
        setRequisitions(resp.items);
        setTotal(resp.total);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load requisitions");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [user, page, statusFilter, search]);

  const isRecruiter = user?.role === "recruiter";

  return (
    <div className="min-h-screen bg-[#FAF9F6] flex flex-col selection:bg-[#EDE5D9] selection:text-[#292722]">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-[#E8E2D8]">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-[#292722] tracking-tight">Requisitions</h1>
              <span className="text-[11px] font-semibold uppercase tracking-wider bg-[#EDE5D9] text-[#756653] px-2 py-0.5 rounded-full border border-[#D9D1C5]">
                Positions
              </span>
            </div>
            <p className="text-xs text-[#6F6A61] mt-1">
              Manage job descriptions, AI requirement extractions, and scoring scorecards.
            </p>
          </div>
          {isRecruiter && (
            <Link
              href="/requisitions/new"
              className="inline-flex items-center gap-2 bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] text-xs font-semibold px-4 py-2.5 rounded-xl transition-colors shadow-2xs self-start sm:self-auto"
            >
              + Create Requisition
            </Link>
          )}
        </div>

        {/* Filters and Search */}
        <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl p-4 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 bg-[#F5F1EA] p-1 rounded-xl border border-[#E8E2D8]">
            {[
              { id: "", label: "All" },
              { id: "draft", label: "Draft" },
              { id: "active", label: "Active" },
              { id: "archived", label: "Archived" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setStatusFilter(tab.id);
                  setPage(1);
                }}
                className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors ${
                  statusFilter === tab.id
                    ? "bg-[#FFFFFF] text-[#292722] shadow-2xs border border-[#E8E2D8]"
                    : "text-[#6F6A61] hover:text-[#292722]"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative w-full sm:w-72">
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
              placeholder="Search by job title..."
              className="w-full text-xs border border-[#E8E2D8] rounded-xl pl-9 pr-3 py-2 bg-[#FFFFFF] text-[#292722] placeholder:text-[#AAA49B] focus:border-[#756653] focus:outline-none transition-colors"
            />
            <svg
              className="w-4 h-4 text-[#918A80] absolute left-3 top-2.5 pointer-events-none"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] text-xs font-medium p-4 rounded-xl">
            {error}
          </div>
        )}

        {/* Requisitions Table */}
        <div className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl shadow-xs overflow-hidden">
          {loading ? (
            <div className="py-16 text-center">
              <div className="w-8 h-8 border-2 border-[#756653] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-xs text-[#6F6A61] font-medium">Loading requisitions...</p>
            </div>
          ) : requisitions.length === 0 ? (
            <div className="py-16 text-center px-4">
              <p className="text-sm font-semibold text-[#292722]">No requisitions found</p>
              <p className="text-xs text-[#918A80] mt-1 max-w-sm mx-auto">
                {search || statusFilter
                  ? "Try clearing your filters or search keywords."
                  : "Create your first job requisition to extract requirements with AI and configure dynamic scorecards."}
              </p>
              {isRecruiter && !search && !statusFilter && (
                <Link
                  href="/requisitions/new"
                  className="mt-4 inline-block text-xs font-semibold text-[#FAF9F6] bg-[#756653] hover:bg-[#5F5243] px-4 py-2 rounded-xl transition-colors shadow-2xs"
                >
                  Create Requisition Now
                </Link>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#F5F1EA] border-b border-[#E8E2D8] text-[#6F6A61] uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="px-6 py-3.5">Job Title</th>
                    <th className="px-6 py-3.5">Location</th>
                    <th className="px-6 py-3.5">Status</th>
                    <th className="px-6 py-3.5">Created</th>
                    <th className="px-6 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EFEAE2]">
                  {requisitions.map((req) => (
                    <tr
                      key={req.id}
                      className="hover:bg-[#FAF9F6] transition-colors cursor-pointer"
                      onClick={() => router.push(`/requisitions/${req.id}`)}
                    >
                      <td className="px-6 py-4">
                        <p className="font-semibold text-[#292722] text-sm hover:text-[#756653]">{req.title}</p>
                        <p className="text-[#918A80] text-[11px] line-clamp-1 mt-0.5">
                          {req.job_description.slice(0, 100)}...
                        </p>
                      </td>
                      <td className="px-6 py-4 text-[#6F6A61] font-medium">
                        {req.location || "Unspecified"}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${
                            req.status === "active"
                              ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                              : req.status === "archived"
                              ? "bg-[#F2EFEB] text-[#5E5950] border-[#DFD9D0]"
                              : "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                          }`}
                        >
                          {req.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-[#918A80]">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <Link
                          href={`/requisitions/${req.id}`}
                          className="text-xs font-semibold text-[#756653] hover:text-[#5F5243] hover:underline px-2 py-1"
                        >
                          View Details →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Footer summary */}
          {!loading && requisitions.length > 0 && (
            <div className="px-6 py-3 border-t border-[#E8E2D8] bg-[#F5F1EA] flex items-center justify-between text-xs text-[#6F6A61]">
              <span>Showing {requisitions.length} of {total} requisitions</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="px-2.5 py-1 border border-[#E8E2D8] rounded-lg bg-[#FFFFFF] text-[#292722] disabled:opacity-40 hover:bg-[#FAF9F6] font-medium"
                >
                  Previous
                </button>
                <span className="font-semibold text-[#292722]">Page {page}</span>
                <button
                  type="button"
                  disabled={requisitions.length < 20}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-2.5 py-1 border border-[#E8E2D8] rounded-lg bg-[#FFFFFF] text-[#292722] disabled:opacity-40 hover:bg-[#FAF9F6] font-medium"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
