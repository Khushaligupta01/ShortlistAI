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
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 flex-1 w-full">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Requisitions</h1>
            <p className="text-xs text-slate-500 mt-1">
              Manage job descriptions, AI requirement extractions, and scoring scorecards.
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

        {/* Filters and Search */}
        <div className="bg-white border border-slate-200 rounded-xl p-4 mb-6 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg">
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
                className={`text-xs font-medium px-3 py-1.5 rounded-md transition-colors ${
                  statusFilter === tab.id
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-600 hover:text-slate-900"
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
              className="w-full text-xs border border-slate-300 rounded-lg pl-9 pr-3 py-2 bg-slate-50 focus:bg-white focus:outline-hidden focus:border-indigo-500"
            />
            <svg
              className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none"
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
          <div className="bg-red-50 border border-red-200 text-red-700 text-xs font-medium p-4 rounded-xl mb-6">
            {error}
          </div>
        )}

        {/* Requisitions Table */}
        <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          {loading ? (
            <div className="py-16 text-center">
              <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-xs text-slate-500">Loading requisitions...</p>
            </div>
          ) : requisitions.length === 0 ? (
            <div className="py-16 text-center px-4">
              <p className="text-sm font-semibold text-slate-700">No requisitions found</p>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                {search || statusFilter
                  ? "Try clearing your filters or search keywords."
                  : "Create your first job requisition to extract requirements with AI and configure dynamic scorecards."}
              </p>
              {isRecruiter && !search && !statusFilter && (
                <Link
                  href="/requisitions/new"
                  className="mt-4 inline-block text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 px-4 py-2 rounded-lg transition-colors"
                >
                  Create Requisition Now
                </Link>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 uppercase tracking-wider font-semibold">
                  <tr>
                    <th className="px-6 py-3.5">Job Title</th>
                    <th className="px-6 py-3.5">Location</th>
                    <th className="px-6 py-3.5">Status</th>
                    <th className="px-6 py-3.5">Created</th>
                    <th className="px-6 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {requisitions.map((req) => (
                    <tr
                      key={req.id}
                      className="hover:bg-slate-50/80 transition-colors cursor-pointer"
                      onClick={() => router.push(`/requisitions/${req.id}`)}
                    >
                      <td className="px-6 py-4">
                        <p className="font-semibold text-slate-900 text-sm">{req.title}</p>
                        <p className="text-slate-400 text-[11px] line-clamp-1 mt-0.5">
                          {req.job_description.slice(0, 100)}...
                        </p>
                      </td>
                      <td className="px-6 py-4 text-slate-600 font-medium">
                        {req.location || "Unspecified"}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                            req.status === "active"
                              ? "bg-emerald-100 text-emerald-800"
                              : req.status === "archived"
                              ? "bg-slate-100 text-slate-600"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {req.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-400">
                        {new Date(req.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right" onClick={(e) => e.stopPropagation()}>
                        <Link
                          href={`/requisitions/${req.id}`}
                          className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 hover:underline px-2 py-1"
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
            <div className="px-6 py-3 border-t border-slate-100 bg-slate-50 flex items-center justify-between text-xs text-slate-500">
              <span>Showing {requisitions.length} of {total} requisitions</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="px-2.5 py-1 border border-slate-300 rounded bg-white disabled:opacity-40"
                >
                  Previous
                </button>
                <span>Page {page}</span>
                <button
                  type="button"
                  disabled={requisitions.length < 20}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-2.5 py-1 border border-slate-300 rounded bg-white disabled:opacity-40"
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
