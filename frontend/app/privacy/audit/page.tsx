"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { AuditEvent, CurrentUser } from "@/lib/types";

export default function AuditExplorerPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [eventTypeFilter, setEventTypeFilter] = useState("");
  const [resourceTypeFilter, setResourceTypeFilter] = useState("");
  const [page, setPage] = useState(1);
  const pageSize = 25;

  // Selected event modal
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);

  async function loadAuditLogs(p: number, evt?: string, res?: string) {
    setLoading(true);
    try {
      const resData = await api.listAuditEvents({
        page: p,
        page_size: pageSize,
        event_type: evt || undefined,
        resource_type: res || undefined,
      });
      setEvents(resData.items);
      setTotal(resData.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load audit events.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function init() {
      const token = getAccessToken();
      if (!token) {
        router.push("/login");
        return;
      }
      try {
        const u = await api.getCurrentUser();
        setUser(u);
        if (u.role === "client_hiring_manager") {
          router.push("/client");
          return;
        }
        await loadAuditLogs(page, eventTypeFilter, resourceTypeFilter);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Initialization failed.");
        setLoading(false);
      }
    }
    init();
  }, [router, page, eventTypeFilter, resourceTypeFilter]);

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="flex items-center gap-2 mb-2">
          <Link href="/privacy" className="text-xs font-semibold text-indigo-600 hover:text-indigo-800">
            ← Privacy Governance
          </Link>
        </div>

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Security & Privacy Audit Log Explorer</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Immutable, append-only security journal capturing authentication, candidate processing, client submissions, and privacy workflows.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-500 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-sm">
              Total Logged Events: <span className="font-bold text-slate-900">{total}</span>
            </span>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Filters */}
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3 flex-wrap">
            <div>
              <input
                type="text"
                placeholder="Filter by Event Type (e.g. CONSENT_GRANTED)"
                value={eventTypeFilter}
                onChange={(e) => {
                  setEventTypeFilter(e.target.value);
                  setPage(1);
                }}
                className="text-xs border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-64"
              />
            </div>
            <div>
              <input
                type="text"
                placeholder="Filter by Resource (e.g. candidate)"
                value={resourceTypeFilter}
                onChange={(e) => {
                  setResourceTypeFilter(e.target.value);
                  setPage(1);
                }}
                className="text-xs border border-slate-200 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-52"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:opacity-50"
            >
              Previous
            </button>
            <span className="text-xs text-slate-600">
              Page {page} of {Math.max(1, totalPages)}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>

        {/* Audit Table */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-6 py-3.5">Timestamp (UTC)</th>
                  <th className="px-6 py-3.5">Event Type</th>
                  <th className="px-6 py-3.5">Actor</th>
                  <th className="px-6 py-3.5">Resource</th>
                  <th className="px-6 py-3.5">Resource ID</th>
                  <th className="px-6 py-3.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 font-mono">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-slate-400 font-sans">
                      Loading audit events...
                    </td>
                  </tr>
                ) : events.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-slate-500 font-sans">
                      No audit events match your search criteria.
                    </td>
                  </tr>
                ) : (
                  events.map((e) => (
                    <tr key={e.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-6 py-4 text-slate-500 text-[11px] whitespace-nowrap font-sans">
                        {new Date(e.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 font-bold text-slate-900 text-xs">
                        {e.event_type}
                      </td>
                      <td className="px-6 py-4 text-slate-700 font-sans">
                        {e.actor_name || "System"}
                      </td>
                      <td className="px-6 py-4">
                        {e.resource_type ? (
                          <span className="text-[10px] uppercase font-bold tracking-wider bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded">
                            {e.resource_type}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-6 py-4 text-slate-400 text-[11px]">
                        {e.resource_id ? e.resource_id.slice(0, 8) + "..." : "—"}
                      </td>
                      <td className="px-6 py-4 text-right font-sans">
                        <button
                          onClick={() => setSelectedEvent(e)}
                          className="text-xs font-semibold text-indigo-600 hover:text-indigo-800"
                        >
                          View JSON
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Event Payload Detail Modal */}
        {selectedEvent && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-xl border border-slate-200">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h2 className="text-base font-bold text-slate-900">{selectedEvent.event_type}</h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    ID: <span className="font-mono">{selectedEvent.id}</span>
                  </p>
                </div>
                <button
                  onClick={() => setSelectedEvent(null)}
                  className="text-slate-400 hover:text-slate-600 font-bold"
                >
                  ✕
                </button>
              </div>

              <div className="my-4 space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-2 text-slate-600 bg-slate-50 p-3 rounded-lg">
                  <div>
                    <span className="font-medium text-slate-500">Actor:</span> {selectedEvent.actor_name || "System"}
                  </div>
                  <div>
                    <span className="font-medium text-slate-500">Timestamp:</span>{" "}
                    {new Date(selectedEvent.created_at).toUTCString()}
                  </div>
                  <div>
                    <span className="font-medium text-slate-500">Resource:</span> {selectedEvent.resource_type || "N/A"}
                  </div>
                  <div>
                    <span className="font-medium text-slate-500">Resource ID:</span>{" "}
                    {selectedEvent.resource_id || "N/A"}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold text-slate-800 mb-1">Sanitized Event Payload (Redacted):</h4>
                  <pre className="p-3 bg-slate-900 text-slate-100 rounded-lg text-[11px] font-mono overflow-auto max-h-64">
                    {JSON.stringify(selectedEvent.payload_json || {}, null, 2)}
                  </pre>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setSelectedEvent(null)}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
