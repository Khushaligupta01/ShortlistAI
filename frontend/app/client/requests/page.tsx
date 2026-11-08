"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import ClientNavbar from "@/components/layout/ClientNavbar";
import type { CurrentUser } from "@/lib/types";

interface CombinedClientRequest {
  id: string;
  submission_id: string;
  candidate_reference: string;
  requisition_title: string;
  request_type: string;
  details: string;
  status: string;
  recruiter_response?: string | null;
  responded_at?: string | null;
  created_at: string;
}

export default function ClientRequestsPage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [requests, setRequests] = useState<CombinedClientRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    async function loadData() {
      try {
        const currentUser = await api.getCurrentUser();
        if (
          currentUser.role !== "client_hiring_manager" &&
          currentUser.role !== "admin" &&
          currentUser.role !== "super_admin"
        ) {
          router.replace("/dashboard");
          return;
        }
        setUser(currentUser);

        // Fetch submissions to extract their requests
        const subs = await api.getClientSubmissions();
        const fullProfiles = await Promise.all(
          subs.map((s) => api.getClientSubmission(s.submission_id).catch(() => null))
        );

        const allReqs: CombinedClientRequest[] = [];
        for (const p of fullProfiles) {
          if (p && p.requests) {
            for (const r of p.requests) {
              allReqs.push({
                id: r.id,
                submission_id: r.submission_id,
                candidate_reference: p.candidate_reference,
                requisition_title: p.requisition_title,
                request_type: r.request_type,
                details: r.details,
                status: r.status,
                recruiter_response: r.recruiter_response,
                responded_at: r.responded_at,
                created_at: r.created_at,
              });
            }
          }
        }
        allReqs.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
        setRequests(allReqs);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load requests");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <ClientNavbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Interview Requests & Information Inquiries</h1>
          <p className="text-sm text-slate-500 mt-1">
            Track interview scheduling requests and questions submitted to your staffing agency partner.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">
            {error}
          </div>
        )}

        {requests.length === 0 ? (
          <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-slate-400 text-sm">
            No interview or information requests submitted yet.
          </div>
        ) : (
          <div className="grid gap-4">
            {requests.map((r) => (
              <div
                key={r.id}
                className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div className="flex items-center gap-3">
                    <span
                      className={`text-xs uppercase font-bold px-2 py-0.5 rounded ${
                        r.request_type === "INTERVIEW"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-purple-100 text-purple-800"
                      }`}
                    >
                      {r.request_type.replace(/_/g, " ")}
                    </span>
                    <Link
                      href={`/client/submissions/${r.submission_id}`}
                      className="text-sm font-bold text-slate-900 hover:underline"
                    >
                      {r.candidate_reference}
                    </Link>
                    <span className="text-xs text-slate-400">
                      • {r.requisition_title}
                    </span>
                  </div>

                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-bold self-start sm:self-auto ${
                      r.status === "RESPONDED"
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-amber-100 text-amber-800"
                    }`}
                  >
                    {r.status}
                  </span>
                </div>

                <div className="bg-slate-50 p-3 rounded-lg text-xs text-slate-800">
                  <span className="font-semibold text-slate-500 block mb-0.5">Your Request:</span>
                  {r.details}
                </div>

                {r.recruiter_response ? (
                  <div className="bg-emerald-50/50 border border-emerald-100 p-3 rounded-lg text-xs text-slate-800 space-y-1">
                    <div className="flex items-center justify-between font-semibold text-emerald-800">
                      <span>Staffing Recruiter Response:</span>
                      {r.responded_at && (
                        <span className="text-[10px] text-slate-400 font-normal">
                          {new Date(r.responded_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                    <p className="whitespace-pre-wrap">{r.recruiter_response}</p>
                  </div>
                ) : (
                  <p className="text-[11px] text-slate-400 italic">
                    Awaiting staffing recruiter response.
                  </p>
                )}

                <div className="pt-1 flex items-center justify-between text-[11px] text-slate-400">
                  <span>Requested on {new Date(r.created_at).toLocaleString()}</span>
                  <Link
                    href={`/client/submissions/${r.submission_id}`}
                    className="text-emerald-700 font-semibold hover:underline"
                  >
                    View Candidate &rarr;
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
