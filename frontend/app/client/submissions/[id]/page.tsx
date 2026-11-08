"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import ClientNavbar from "@/components/layout/ClientNavbar";
import type { CurrentUser, MaskedCandidateProfile } from "@/lib/types";

export default function ClientSubmissionDetailPage() {
  const router = useRouter();
  const params = useParams();
  const submissionId = params?.id as string;

  const [user, setUser] = useState<CurrentUser | null>(null);
  const [profile, setProfile] = useState<MaskedCandidateProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Decision Modal State
  const [activeModal, setActiveModal] = useState<
    "SHORTLIST" | "INTERVIEW" | "INFO" | "REJECT" | null
  >(null);
  const [decisionNote, setDecisionNote] = useState("");
  const [interviewDetails, setInterviewDetails] = useState("");
  const [infoRequestDetails, setInfoRequestDetails] = useState("");
  const [submittingDecision, setSubmittingDecision] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }
    if (!submissionId) return;

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

        const data = await api.getClientSubmission(submissionId);
        setProfile(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load candidate profile");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [submissionId, router]);

  async function handleDecisionSubmit() {
    if (!profile) return;
    setSubmittingDecision(true);
    setActionSuccess(null);

    let decisionCode = "";
    if (activeModal === "SHORTLIST") decisionCode = "CLIENT_SHORTLISTED";
    else if (activeModal === "INTERVIEW") decisionCode = "INTERVIEW_REQUESTED";
    else if (activeModal === "INFO") decisionCode = "ADDITIONAL_INFO_REQUESTED";
    else if (activeModal === "REJECT") decisionCode = "CLIENT_REJECTED";

    try {
      const updated = await api.submitClientDecision(profile.submission_id, {
        decision: decisionCode,
        reason_note: decisionNote.trim() || undefined,
        interview_details: activeModal === "INTERVIEW" ? interviewDetails.trim() || undefined : undefined,
        info_request_details: activeModal === "INFO" ? infoRequestDetails.trim() || undefined : undefined,
      });
      setProfile(updated);
      setActiveModal(null);
      setDecisionNote("");
      setInterviewDetails("");
      setInfoRequestDetails("");
      setActionSuccess(`Decision recorded: ${decisionCode.replace(/_/g, " ")}`);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to record decision");
    } finally {
      setSubmittingDecision(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="bg-white border border-red-200 rounded-xl p-8 max-w-sm text-center shadow-sm">
          <p className="text-red-600 font-medium mb-4">{error || "Candidate submission not found"}</p>
          <Link href="/client/submissions" className="text-emerald-700 text-sm font-semibold hover:underline">
            Back to submissions
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <ClientNavbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Navigation Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Link href="/client/submissions" className="hover:underline">Submissions</Link>
          <span>/</span>
          <span className="text-slate-800 font-semibold">{profile.candidate_reference}</span>
        </div>

        {/* Privacy & Compliance Banner */}
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 flex items-start gap-3">
          <svg className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <div className="text-xs text-emerald-900 leading-relaxed">
            <strong>Fair Hiring Anonymization Active:</strong> This candidate profile has been sanitized to eliminate unconscious bias and protect candidate PII. Direct contact details and raw resumes are retained by the staffing firm until interview scheduling is confirmed.
          </div>
        </div>

        {actionSuccess && (
          <div className="bg-emerald-600 text-white p-4 rounded-xl text-xs font-semibold flex items-center justify-between shadow">
            <span>{actionSuccess}</span>
            <button onClick={() => setActionSuccess(null)} className="text-emerald-100 hover:text-white">✕</button>
          </div>
        )}

        {/* Candidate Top Header Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div className="space-y-2">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900">
                  {profile.candidate_reference}
                </h1>
                <span
                  className={`text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-wider ${
                    profile.current_stage === "CLIENT_SHORTLISTED"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                      : profile.current_stage === "CLIENT_REJECTED"
                      ? "bg-red-100 text-red-800 border border-red-200"
                      : profile.current_stage === "INTERVIEW_REQUESTED"
                      ? "bg-blue-100 text-blue-800 border border-blue-200"
                      : profile.current_stage === "ADDITIONAL_INFO_REQUESTED"
                      ? "bg-purple-100 text-purple-800 border border-purple-200"
                      : "bg-amber-100 text-amber-800 border border-amber-200"
                  }`}
                >
                  {profile.current_stage.replace(/_/g, " ")}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                Submitted for Requisition:{" "}
                <Link
                  href={`/client/requisitions/${profile.requisition_id}`}
                  className="font-semibold text-slate-800 hover:underline"
                >
                  {profile.requisition_title}
                </Link>{" "}
                • Submitted on {new Date(profile.submitted_at).toLocaleDateString()}
              </p>
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-600 pt-1">
                {profile.location && <span>📍 Location: <strong>{profile.location}</strong></span>}
                {profile.total_experience_years !== null && profile.total_experience_years !== undefined && (
                  <span>💼 Experience: <strong>{profile.total_experience_years} years</strong></span>
                )}
                {profile.notice_period_days !== null && profile.notice_period_days !== undefined && (
                  <span>⏱ Notice Period: <strong>{profile.notice_period_days} days</strong></span>
                )}
              </div>
            </div>

            {/* Scorecard Match Gauge */}
            {profile.overall_score !== null && profile.overall_score !== undefined && (
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-center shrink-0 min-w-[140px]">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Scorecard Match</p>
                <p className="text-3xl font-black text-emerald-600 mt-1">
                  {Math.round(profile.overall_score)}%
                </p>
                <p className="text-[11px] text-slate-400 mt-0.5">Objective evaluation</p>
              </div>
            )}
          </div>

          {/* Recruiter Note for Client */}
          {profile.recruiter_notes_for_client && (
            <div className="mt-6 pt-6 border-t border-slate-100">
              <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
                Recruiter Recommendation Notes
              </h3>
              <div className="bg-indigo-50/50 border border-indigo-100 text-slate-800 text-xs p-3.5 rounded-xl whitespace-pre-wrap leading-relaxed">
                {profile.recruiter_notes_for_client}
              </div>
            </div>
          )}

          {/* Client Action Buttons */}
          <div className="mt-6 pt-6 border-t border-slate-100 flex flex-wrap items-center gap-3">
            <button
              onClick={() => {
                setActiveModal("SHORTLIST");
                setDecisionNote("");
              }}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow-sm flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Shortlist Candidate
            </button>

            <button
              onClick={() => {
                setActiveModal("INTERVIEW");
                setInterviewDetails("");
                setDecisionNote("");
              }}
              className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow-sm flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              Request Interview
            </button>

            <button
              onClick={() => {
                setActiveModal("INFO");
                setInfoRequestDetails("");
                setDecisionNote("");
              }}
              className="bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl transition shadow-sm flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              Request Additional Info
            </button>

            <button
              onClick={() => {
                setActiveModal("REJECT");
                setDecisionNote("");
              }}
              className="border border-red-300 text-red-700 hover:bg-red-50 text-xs font-bold px-4 py-2.5 rounded-xl transition"
            >
              Reject Candidate
            </button>
          </div>
        </div>

        {/* Evaluation Summary & Criterion Evidence Breakdown */}
        {profile.evaluation_summary && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900">Executive Match Summary</h2>
            <p className="text-xs text-slate-700 leading-relaxed bg-slate-50 p-4 rounded-xl border border-slate-200">
              {profile.evaluation_summary}
            </p>
          </div>
        )}

        {profile.criterion_evaluations && profile.criterion_evaluations.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900">Scorecard Criteria Evidence Grounding</h2>
            <p className="text-xs text-slate-500">
              Transparent, evidence-based assessment of candidate qualifications against job requirements.
            </p>

            <div className="grid gap-3">
              {profile.criterion_evaluations.map((ev, i) => (
                <div
                  key={i}
                  className="border border-slate-200 rounded-xl p-4 bg-slate-50/50 space-y-2"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-[10px] uppercase font-bold text-slate-500 mr-2 bg-slate-200 px-1.5 py-0.5 rounded">
                        {ev.category}
                      </span>
                      <span className="font-bold text-xs text-slate-900">
                        {ev.criterion_name}
                      </span>
                    </div>
                    <span
                      className={`text-[11px] font-bold px-2 py-0.5 rounded ${
                        ev.status === "MATCH"
                          ? "bg-emerald-100 text-emerald-800"
                          : ev.status === "PARTIAL_MATCH"
                          ? "bg-amber-100 text-amber-800"
                          : ev.status === "NO_MATCH"
                          ? "bg-red-100 text-red-800"
                          : "bg-slate-200 text-slate-700"
                      }`}
                    >
                      {ev.status.replace(/_/g, " ")}
                    </span>
                  </div>

                  {ev.evidence_excerpt && (
                    <div className="text-xs text-slate-700 bg-white border border-slate-200 p-2.5 rounded-lg italic">
                      &ldquo;{ev.evidence_excerpt}&rdquo;
                    </div>
                  )}

                  {ev.reasoning && (
                    <p className="text-xs text-slate-600">
                      <strong>Analysis:</strong> {ev.reasoning}
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Skills & Experience */}
        <div className="grid md:grid-cols-3 gap-6">
          {/* Work Experience */}
          <div className="md:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900">Work Experience</h2>
            {profile.employments.length === 0 ? (
              <p className="text-xs text-slate-400">No employment records available.</p>
            ) : (
              <div className="space-y-4">
                {profile.employments.map((emp, i) => (
                  <div key={i} className="border-l-2 border-emerald-500 pl-4 py-1 space-y-1">
                    <div className="flex items-center justify-between">
                      <h3 className="font-bold text-xs text-slate-900">{emp.title}</h3>
                      <span className="text-[11px] text-slate-400">
                        {emp.start_date || "?"} &mdash; {emp.is_current ? "Present" : emp.end_date || "?"}
                      </span>
                    </div>
                    <p className="text-xs font-medium text-emerald-700">{emp.company}</p>
                    {emp.description && (
                      <p className="text-xs text-slate-600 leading-relaxed pt-1 whitespace-pre-wrap">
                        {emp.description}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Education & Skills */}
          <div className="space-y-6">
            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
              <h2 className="text-base font-bold text-slate-900">Skills</h2>
              <div className="flex flex-wrap gap-1.5">
                {profile.skills.length === 0 ? (
                  <p className="text-xs text-slate-400">No skills listed.</p>
                ) : (
                  profile.skills.map((s) => (
                    <span key={s} className="bg-slate-100 text-slate-700 text-xs px-2.5 py-1 rounded-md font-medium">
                      {s}
                    </span>
                  ))
                )}
              </div>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
              <h2 className="text-base font-bold text-slate-900">Education</h2>
              {profile.educations.length === 0 ? (
                <p className="text-xs text-slate-400">No education records.</p>
              ) : (
                <div className="space-y-3">
                  {profile.educations.map((edu, i) => (
                    <div key={i} className="text-xs">
                      <p className="font-bold text-slate-900">{edu.degree} in {edu.field_of_study}</p>
                      <p className="text-slate-500">{edu.institution} {edu.graduation_year ? `(${edu.graduation_year})` : ""}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {profile.certifications.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-3">
                <h2 className="text-base font-bold text-slate-900">Certifications</h2>
                <ul className="list-disc list-inside text-xs text-slate-700 space-y-1">
                  {profile.certifications.map((c, i) => (
                    <li key={i}>{c}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Requests & Inquiries Thread */}
        {profile.requests && profile.requests.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
            <h2 className="text-base font-bold text-slate-900">Inquiries & Interview Requests</h2>
            <div className="space-y-3">
              {profile.requests.map((r) => (
                <div key={r.id} className="border border-slate-200 rounded-xl p-4 bg-slate-50 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-purple-700 uppercase">
                      {r.request_type.replace(/_/g, " ")}
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      r.status === "RESPONDED"
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-amber-100 text-amber-800"
                    }`}>
                      {r.status}
                    </span>
                  </div>
                  <p className="text-xs text-slate-800">
                    <strong>Your Request:</strong> {r.details}
                  </p>
                  {r.recruiter_response ? (
                    <div className="mt-2 pt-2 border-t border-slate-200 text-xs text-slate-800 bg-white p-2.5 rounded-lg">
                      <strong className="text-emerald-700">Recruiter Response:</strong> {r.recruiter_response}
                      {r.responded_at && (
                        <span className="block text-[10px] text-slate-400 mt-1">
                          Responded on {new Date(r.responded_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  ) : (
                    <p className="text-[11px] text-slate-400 italic">
                      Awaiting response from staffing firm recruiter...
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Decision & Pipeline History Timeline */}
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
          <h2 className="text-base font-bold text-slate-900">Audit History & Stage Progression</h2>
          {profile.pipeline_history.length === 0 ? (
            <p className="text-xs text-slate-400">No activity recorded yet.</p>
          ) : (
            <div className="relative border-l-2 border-slate-200 ml-3 space-y-6">
              {profile.pipeline_history.map((h) => (
                <div key={h.id} className="relative pl-6">
                  <span className="absolute -left-1.5 top-1.5 w-3 h-3 rounded-full bg-emerald-500 border-2 border-white ring-1 ring-emerald-300" />
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-slate-900">
                      {h.current_stage.replace(/_/g, " ")}
                    </span>
                    <span className="text-slate-400">
                      {new Date(h.changed_at).toLocaleString()}
                    </span>
                  </div>
                  {h.reason_note && (
                    <p className="text-xs text-slate-600 mt-0.5">{h.reason_note}</p>
                  )}
                  {h.actor_name && (
                    <p className="text-[10px] text-slate-400 mt-0.5">By: {h.actor_name}</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Decision Action Modal */}
      {activeModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl space-y-4">
            <h3 className="text-lg font-bold text-slate-900">
              {activeModal === "SHORTLIST" && "Shortlist Candidate"}
              {activeModal === "INTERVIEW" && "Request Candidate Interview"}
              {activeModal === "INFO" && "Request Additional Information"}
              {activeModal === "REJECT" && "Reject Candidate"}
            </h3>

            {activeModal === "SHORTLIST" && (
              <p className="text-xs text-slate-500">
                Confirm your decision to shortlist this candidate for {profile.requisition_title}.
              </p>
            )}

            {activeModal === "INTERVIEW" && (
              <div className="space-y-3">
                <p className="text-xs text-slate-500">
                  Provide interview details such as interview type (technical, managerial), suggested dates, or interviewer details.
                </p>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    Interview Details & Preferred Times
                  </label>
                  <textarea
                    rows={3}
                    value={interviewDetails}
                    onChange={(e) => setInterviewDetails(e.target.value)}
                    placeholder="e.g. 45-min Zoom technical screen next Tuesday afternoon..."
                    className="w-full border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </div>
            )}

            {activeModal === "INFO" && (
              <div className="space-y-3">
                <p className="text-xs text-slate-500">
                  Ask the recruiter for clarification on background, skills, or availability.
                </p>
                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    Information or Questions Needed
                  </label>
                  <textarea
                    rows={3}
                    value={infoRequestDetails}
                    onChange={(e) => setInfoRequestDetails(e.target.value)}
                    placeholder="e.g. Please clarify hands-on experience with Kubernetes in production..."
                    className="w-full border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-purple-500"
                  />
                </div>
              </div>
            )}

            {activeModal === "REJECT" && (
              <div className="space-y-3">
                <p className="text-xs text-slate-500">
                  Please provide constructive feedback or rationale for declining this candidate.
                </p>
              </div>
            )}

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Internal Decision Notes (Optional)
              </label>
              <textarea
                rows={2}
                value={decisionNote}
                onChange={(e) => setDecisionNote(e.target.value)}
                placeholder="Add any internal comments or feedback..."
                className="w-full border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                className="text-xs font-semibold text-slate-600 hover:text-slate-800 px-4 py-2 rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={submittingDecision}
                onClick={handleDecisionSubmit}
                className={`text-xs font-bold text-white px-5 py-2.5 rounded-xl transition shadow-sm ${
                  activeModal === "REJECT"
                    ? "bg-red-600 hover:bg-red-700"
                    : activeModal === "INTERVIEW"
                    ? "bg-blue-600 hover:bg-blue-700"
                    : activeModal === "INFO"
                    ? "bg-purple-600 hover:bg-purple-700"
                    : "bg-emerald-600 hover:bg-emerald-700"
                }`}
              >
                {submittingDecision ? "Submitting..." : "Confirm Decision"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

