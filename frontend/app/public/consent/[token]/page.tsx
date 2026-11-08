"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { ConsentPublicInfo } from "@/lib/types";

export default function PublicConsentDecisionPage() {
  const params = useParams();
  const token = params?.token as string;

  const [info, setInfo] = useState<ConsentPublicInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completedDecision, setCompletedDecision] = useState<string | null>(null);
  const [reasonInput, setReasonInput] = useState("");

  useEffect(() => {
    async function loadTokenInfo() {
      if (!token) return;
      try {
        const res = await api.getPublicConsentInfo(token);
        setInfo(res);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Invalid, expired, or unknown consent link.");
      } finally {
        setLoading(false);
      }
    }
    loadTokenInfo();
  }, [token]);

  async function handleDecision(decision: "GRANTED" | "DECLINED") {
    if (!token) return;
    setSubmitting(true);
    setError(null);
    try {
      await api.submitPublicConsentDecision(token, {
        decision,
        reason: reasonInput.trim() || undefined,
      });
      setCompletedDecision(decision);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to record your decision. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-xl">
        <div className="text-center mb-6">
          <div className="inline-flex items-center gap-2 font-bold text-slate-900 text-xl">
            <span className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center text-sm font-black shadow-sm">
              S
            </span>
            <span>ShortlistAI</span>
          </div>
          <h2 className="mt-3 text-2xl font-bold tracking-tight text-slate-900">
            Candidate Privacy & Processing Notice
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            Secure, tokenized consent authorization requested by our recruitment team
          </p>
        </div>

        <div className="bg-white py-8 px-6 shadow-xl rounded-2xl border border-slate-200 sm:px-10">
          {loading ? (
            <div className="text-center py-12 text-sm text-slate-400">
              Verifying secure authorization token...
            </div>
          ) : error ? (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mx-auto mb-3 font-bold text-xl">
                !
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-1">Authorization Notice Unavailable</h3>
              <p className="text-xs text-slate-600 mb-6">{error}</p>
              <p className="text-[11px] text-slate-400">
                If you believe this link is expired, please contact your recruitment representative to issue a fresh authorization link.
              </p>
            </div>
          ) : completedDecision ? (
            <div className="text-center py-8">
              <div
                className={`w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 font-bold text-xl ${
                  completedDecision === "GRANTED"
                    ? "bg-emerald-100 text-emerald-600"
                    : "bg-amber-100 text-amber-600"
                }`}
              >
                {completedDecision === "GRANTED" ? "✓" : "—"}
              </div>
              <h3 className="text-lg font-bold text-slate-900 mb-1">
                {completedDecision === "GRANTED"
                  ? "Thank You — Consent Granted"
                  : "Decision Recorded — Consent Declined"}
              </h3>
              <p className="text-xs text-slate-600 mb-6">
                Your decision has been securely registered with an immutable audit timestamp in our records.
              </p>
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-left text-xs text-slate-600 space-y-1">
                <p>
                  <span className="font-semibold text-slate-700">Reference:</span> {info?.candidate_reference}
                </p>
                <p>
                  <span className="font-semibold text-slate-700">Organization:</span> {info?.organization_name}
                </p>
                <p>
                  <span className="font-semibold text-slate-700">Status:</span>{" "}
                  <span className="font-bold text-slate-900">{completedDecision}</span>
                </p>
              </div>
              <p className="text-[11px] text-slate-400 mt-6">
                You may withdraw your consent or request data deletion at any point by contacting{" "}
                <span className="font-semibold text-slate-600">{info?.organization_name}</span>.
              </p>
            </div>
          ) : !info?.is_valid ? (
            <div className="text-center py-8">
              <div className="w-12 h-12 rounded-full bg-slate-100 text-slate-600 flex items-center justify-center mx-auto mb-3 font-bold text-xl">
                ✕
              </div>
              <h3 className="text-base font-bold text-slate-900 mb-1">Consent Link No Longer Active</h3>
              <p className="text-xs text-slate-600">
                This consent link is either expired or has already been used to record a decision (Status: {info?.status}).
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Context Card */}
              <div className="p-4 bg-indigo-50/50 border border-indigo-100 rounded-xl space-y-2">
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-500 font-medium">Candidate Reference:</span>
                  <span className="font-mono font-bold text-indigo-900">{info.candidate_reference}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-500 font-medium">Hiring Organization:</span>
                  <span className="font-bold text-slate-900">{info.organization_name}</span>
                </div>
                <div className="flex justify-between items-center text-xs">
                  <span className="text-slate-500 font-medium">Policy Version:</span>
                  <span className="text-slate-700 font-mono text-[11px]">{info.version}</span>
                </div>
              </div>

              {/* Notice Details */}
              <div className="text-xs text-slate-600 space-y-3 leading-relaxed">
                <h4 className="font-bold text-slate-900 text-sm">Purpose of Data Processing</h4>
                <p>
                  <strong className="text-slate-800">{info.organization_name}</strong> is requesting your consent to process your resume, employment history, and professional skills for the purpose of{" "}
                  <span className="font-semibold text-slate-900">{info.purpose.replace(/_/g, " ")}</span>.
                </p>

                <h4 className="font-bold text-slate-900 text-sm pt-2">Candidate Rights & Safeguards</h4>
                <ul className="list-disc pl-5 space-y-1.5 text-slate-600">
                  <li>
                    <strong className="text-slate-800">PII Contact Masking:</strong> Direct contact details (email, phone, street address) are strictly masked and protected from client browsing.
                  </li>
                  <li>
                    <strong className="text-slate-800">Protected Attribute Exclusion:</strong> AI scoring excludes candidate name, gender, age, photograph, and demographic variables.
                  </li>
                  <li>
                    <strong className="text-slate-800">Right of Access & Portability:</strong> You may request a full export of your personal candidate records at any time.
                  </li>
                  <li>
                    <strong className="text-slate-800">Right to Withdraw & Erasure:</strong> You can withdraw consent or request complete file deletion at any time without adverse consequence.
                  </li>
                </ul>
              </div>

              {/* Optional comments */}
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">
                  Optional Candidate Notes / Comments:
                </label>
                <input
                  type="text"
                  placeholder="e.g. Authorized for current Senior Java Requisition only"
                  value={reasonInput}
                  onChange={(e) => setReasonInput(e.target.value)}
                  className="w-full text-xs border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              {/* Decision Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision("GRANTED")}
                  className="flex-1 py-2.5 px-4 bg-emerald-600 text-white rounded-xl text-xs font-semibold hover:bg-emerald-700 transition-colors shadow-sm disabled:opacity-50"
                >
                  {submitting ? "Registering..." : "✓ Grant Processing Consent"}
                </button>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision("DECLINED")}
                  className="flex-1 py-2.5 px-4 bg-slate-100 text-slate-700 rounded-xl text-xs font-semibold hover:bg-slate-200 transition-colors disabled:opacity-50"
                >
                  Decline Consent
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
