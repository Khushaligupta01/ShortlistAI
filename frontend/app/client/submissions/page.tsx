"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import ClientNavbar from "@/components/layout/ClientNavbar";
import type {
  ClientRequisitionListItem,
  ClientSubmissionListItem,
  CurrentUser,
} from "@/lib/types";

function ClientSubmissionsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialReqId = searchParams.get("requisition_id") || "";

  const [user, setUser] = useState<CurrentUser | null>(null);
  const [submissions, setSubmissions] = useState<ClientSubmissionListItem[]>([]);
  const [requisitions, setRequisitions] = useState<ClientRequisitionListItem[]>([]);
  const [selectedReq, setSelectedReq] = useState<string>(initialReqId);
  const [selectedStage, setSelectedStage] = useState<string>("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");
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
        if (currentUser.role !== "client_hiring_manager" && currentUser.role !== "admin" && currentUser.role !== "super_admin") {
          router.replace("/dashboard");
          return;
        }
        setUser(currentUser);

        const [reqs, subs] = await Promise.all([
          api.getClientRequisitions(),
          api.getClientSubmissions({
            requisition_id: selectedReq || undefined,
            stage: selectedStage !== "ALL" ? selectedStage : undefined,
          }),
        ]);
        setRequisitions(reqs);
        setSubmissions(subs);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load submissions");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [selectedReq, selectedStage, router]);

  const filteredSubmissions = submissions.filter((sub) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const matchesRef = sub.candidate_reference.toLowerCase().includes(q);
    const matchesReq = sub.requisition_title.toLowerCase().includes(q);
    const matchesSkill = sub.skills?.some((s) => s.toLowerCase().includes(q));
    const matchesLoc = sub.location?.toLowerCase().includes(q);
    return matchesRef || matchesReq || matchesSkill || matchesLoc;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-[#756653] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FAF9F6] selection:bg-[#EDE5D9] selection:text-[#292722]">
      <ClientNavbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        <div className="pb-2 border-b border-[#E8E2D8]">
          <h1 className="text-2xl font-bold text-[#292722] tracking-tight">Candidate Shortlist & Submissions</h1>
          <p className="text-xs text-[#6F6A61] mt-1">
            Browse and review candidate profiles submitted to your organization with full anonymity protection.
          </p>
        </div>

        {/* Filter Controls */}
        <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-4 shadow-xs flex flex-col md:flex-row gap-4 items-center justify-between">
          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            <input
              type="text"
              placeholder="Search reference, skill, title..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="border border-[#E8E2D8] rounded-xl px-3 py-1.5 text-xs text-[#292722] bg-[#FFFFFF] placeholder:text-[#AAA49B] focus:border-[#756653] focus:outline-none w-full sm:w-64"
            />

            <select
              value={selectedReq}
              onChange={(e) => setSelectedReq(e.target.value)}
              className="border border-[#E8E2D8] rounded-xl px-3 py-1.5 text-xs text-[#292722] bg-[#FFFFFF] focus:border-[#756653] focus:outline-none"
            >
              <option value="">All Requisitions</option>
              {requisitions.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.title}
                </option>
              ))}
            </select>

            <select
              value={selectedStage}
              onChange={(e) => setSelectedStage(e.target.value)}
              className="border border-[#E8E2D8] rounded-xl px-3 py-1.5 text-xs text-[#292722] bg-[#FFFFFF] focus:border-[#756653] focus:outline-none"
            >
              <option value="ALL">All Stages</option>
              <option value="SUBMITTED">Awaiting Review</option>
              <option value="CLIENT_SHORTLISTED">Shortlisted</option>
              <option value="INTERVIEW_REQUESTED">Interview Requested</option>
              <option value="INTERVIEW_SCHEDULED">Interview Scheduled</option>
              <option value="ADDITIONAL_INFO_REQUESTED">Info Requested</option>
              <option value="CLIENT_REJECTED">Rejected</option>
            </select>
          </div>

          <div className="text-xs text-[#6F6A61] font-medium">
            Showing {filteredSubmissions.length} candidate{filteredSubmissions.length === 1 ? "" : "s"}
          </div>
        </div>

        {/* Candidate List */}
        {error && (
          <div className="bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] p-4 rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {filteredSubmissions.length === 0 ? (
          <div className="bg-[#FFFFFF] rounded-2xl border border-[#E8E2D8] p-12 text-center text-[#918A80] text-xs">
            No candidate submissions found matching your filters.
          </div>
        ) : (
          <div className="grid gap-4">
            {filteredSubmissions.map((sub) => (
              <div
                key={sub.submission_id}
                className="bg-[#FFFFFF] border border-[#E8E2D8] rounded-2xl p-5 shadow-xs hover:border-[#D9D1C5] transition flex flex-col md:flex-row md:items-center md:justify-between gap-4"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-3">
                    <span className="font-bold text-[#292722] text-base">
                      {sub.candidate_reference}
                    </span>
                    {sub.overall_score !== null && sub.overall_score !== undefined && (
                      <span className="text-xs bg-[#EEF6F0] text-[#2A5A35] font-bold px-2 py-0.5 rounded-full border border-[#C4E2CC]">
                        {Math.round(sub.overall_score)}% Scorecard Match
                      </span>
                    )}
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${
                        sub.current_stage === "CLIENT_SHORTLISTED"
                          ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                          : sub.current_stage === "CLIENT_REJECTED"
                          ? "bg-[#FDF0F0] text-[#7A2525] border-[#EFC2C2]"
                          : sub.current_stage === "INTERVIEW_REQUESTED" || sub.current_stage === "INTERVIEW_SCHEDULED"
                          ? "bg-[#EDF4F9] text-[#264D6B] border-[#C6DDEE]"
                          : sub.current_stage === "ADDITIONAL_INFO_REQUESTED"
                          ? "bg-[#EDE5D9] text-[#756653] border-[#D9D1C5]"
                          : "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                      }`}
                    >
                      {sub.current_stage.replace(/_/g, " ")}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-[#6F6A61]">
                    <span>Requisition: <strong>{sub.requisition_title}</strong></span>
                    {sub.location && <span>• Location: {sub.location}</span>}
                    {sub.total_experience_years !== null && sub.total_experience_years !== undefined && (
                      <span>• Experience: {sub.total_experience_years} years</span>
                    )}
                    <span>• Submitted: {new Date(sub.submitted_at).toLocaleDateString()}</span>
                  </div>

                  {sub.skills && sub.skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {sub.skills.map((s) => (
                        <span key={s} className="bg-[#F5F1EA] text-[#6F6A61] border border-[#E8E2D8] text-[10px] px-2 py-0.5 rounded-md font-medium">
                          {s}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <Link
                    href={`/client/submissions/${sub.submission_id}`}
                    className="bg-[#756653] hover:bg-[#5F5243] text-[#FAF9F6] text-xs font-semibold px-4 py-2 rounded-xl transition shadow-2xs whitespace-nowrap"
                  >
                    Review & Decide &rarr;
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

export default function ClientSubmissionsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-[#FAF9F6] flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-[#756653] border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <ClientSubmissionsContent />
    </Suspense>
  );
}
