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
    <div className="min-h-screen bg-[#FAF9F6] selection:bg-[#EDE5D9] selection:text-[#292722]">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="pb-2 border-b border-[#E8E2D8]">
          <Link href="/privacy" className="text-xs font-semibold text-[#6F6A61] hover:text-[#756653] inline-flex items-center gap-1 mb-2">
            ← Privacy Governance
          </Link>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold text-[#292722] tracking-tight">Security & Privacy Audit Log Explorer</h1>
                <span className="text-[11px] font-semibold uppercase tracking-wider bg-[#EDE5D9] text-[#756653] px-2 py-0.5 rounded-full border border-[#D9D1C5]">
                  Tamper-Resistant Journal
                </span>
              </div>
              <p className="text-xs text-[#6F6A61] mt-1">
                Immutable, append-only security journal capturing authentication, candidate processing, client submissions, and privacy workflows.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-[#6F6A61] bg-[#FFFFFF] border border-[#E8E2D8] px-3.5 py-1.5 rounded-xl shadow-2xs">
                Total Logged Events: <span className="font-bold text-[#292722]">{total}</span>
              </span>
            </div>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {/* Filters */}
        <div className="bg-[#FFFFFF] p-4 rounded-2xl border border-[#E8E2D8] shadow-xs flex items-center justify-between gap-4 flex-wrap">
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
                className="text-xs border border-[#E8E2D8] rounded-xl px-3 py-1.5 bg-[#FFFFFF] text-[#292722] placeholder:text-[#AAA49B] focus:border-[#756653] focus:outline-none w-64"
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
                className="text-xs border border-[#E8E2D8] rounded-xl px-3 py-1.5 bg-[#FFFFFF] text-[#292722] placeholder:text-[#AAA49B] focus:border-[#756653] focus:outline-none w-52"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-[#F5F1EA] text-[#292722] border border-[#E8E2D8] hover:bg-[#EEE8DD] disabled:opacity-40"
            >
              Previous
            </button>
            <span className="text-xs text-[#6F6A61] font-medium">
              Page {page} of {Math.max(1, totalPages)}
            </span>
            <button
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
              className="px-3 py-1.5 text-xs font-semibold rounded-xl bg-[#F5F1EA] text-[#292722] border border-[#E8E2D8] hover:bg-[#EEE8DD] disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>

        {/* Audit Table */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#F5F1EA] border-b border-[#E8E2D8] text-[#6F6A61] font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="px-6 py-3.5">Timestamp (UTC)</th>
                  <th className="px-6 py-3.5">Event Type</th>
                  <th className="px-6 py-3.5">Actor</th>
                  <th className="px-6 py-3.5">Resource</th>
                  <th className="px-6 py-3.5">Resource ID</th>
                  <th className="px-6 py-3.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EFEAE2] font-mono">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-[#918A80] font-sans">
                      Loading audit events...
                    </td>
                  </tr>
                ) : events.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="text-center py-12 text-[#918A80] font-sans">
                      No audit events match your search criteria.
                    </td>
                  </tr>
                ) : (
                  events.map((e) => (
                    <tr key={e.id} className="hover:bg-[#FAF9F6] transition-colors">
                      <td className="px-6 py-4 text-[#918A80] text-[11px] whitespace-nowrap font-sans">
                        {new Date(e.created_at).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 font-bold text-[#292722] text-xs">
                        {e.event_type}
                      </td>
                      <td className="px-6 py-4 text-[#6F6A61] font-sans">
                        {e.actor_name || "System"}
                      </td>
                      <td className="px-6 py-4">
                        {e.resource_type ? (
                          <span className="text-[10px] uppercase font-bold tracking-wider bg-[#F5F1EA] text-[#6F6A61] px-1.5 py-0.5 rounded border border-[#E8E2D8]">
                            {e.resource_type}
                          </span>
                        ) : (
                          "—"
                        )}
                      </td>
                      <td className="px-6 py-4 text-[#918A80] text-[11px]">
                        {e.resource_id ? e.resource_id.slice(0, 8) + "..." : "—"}
                      </td>
                      <td className="px-6 py-4 text-right font-sans">
                        <button
                          onClick={() => setSelectedEvent(e)}
                          className="text-xs font-semibold text-[#756653] hover:text-[#5F5243]"
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
          <div className="fixed inset-0 bg-[#292722]/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
            <div className="bg-[#FFFFFF] rounded-2xl max-w-xl w-full p-6 shadow-xl border border-[#E8E2D8]">
              <div className="flex items-center justify-between pb-3 border-b border-[#E8E2D8]">
                <div>
                  <h2 className="text-base font-bold text-[#292722]">{selectedEvent.event_type}</h2>
                  <p className="text-xs text-[#6F6A61] mt-0.5">
                    ID: <span className="font-mono text-[#292722]">{selectedEvent.id}</span>
                  </p>
                </div>
                <button
                  onClick={() => setSelectedEvent(null)}
                  className="text-[#918A80] hover:text-[#292722] font-bold"
                >
                  ✕
                </button>
              </div>

              <div className="my-4 space-y-3 text-xs">
                <div className="grid grid-cols-2 gap-2 text-[#6F6A61] bg-[#F5F1EA] p-3 rounded-xl border border-[#E8E2D8]">
                  <div>
                    <span className="font-semibold text-[#292722]">Actor:</span> {selectedEvent.actor_name || "System"}
                  </div>
                  <div>
                    <span className="font-semibold text-[#292722]">Timestamp:</span>{" "}
                    {new Date(selectedEvent.created_at).toUTCString()}
                  </div>
                  <div>
                    <span className="font-semibold text-[#292722]">Resource:</span> {selectedEvent.resource_type || "N/A"}
                  </div>
                  <div>
                    <span className="font-semibold text-[#292722]">Resource ID:</span>{" "}
                    {selectedEvent.resource_id || "N/A"}
                  </div>
                </div>

                <div>
                  <h4 className="font-semibold text-[#292722] mb-1">Sanitized Event Payload (Redacted):</h4>
                  <pre className="p-3 bg-[#292722] text-[#FAF9F6] rounded-xl text-[11px] font-mono overflow-auto max-h-64 leading-relaxed">
                    {JSON.stringify(selectedEvent.payload_json || {}, null, 2)}
                  </pre>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setSelectedEvent(null)}
                  className="px-4 py-2 text-xs font-semibold rounded-xl bg-[#F5F1EA] text-[#292722] border border-[#E8E2D8] hover:bg-[#EEE8DD]"
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
