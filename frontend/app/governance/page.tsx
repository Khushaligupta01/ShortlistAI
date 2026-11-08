"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import { api } from "@/lib/api";
import { getAccessToken } from "@/lib/auth";
import type { CurrentUser, EvaluationQuality, GovernanceAIMetrics } from "@/lib/types";

export default function GovernancePage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [metrics, setMetrics] = useState<GovernanceAIMetrics | null>(null);
  const [quality, setQuality] = useState<EvaluationQuality | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
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
        const [m, q] = await Promise.all([
          api.getGovernanceAIMetrics(),
          api.getEvaluationQuality(),
        ]);
        setMetrics(m);
        setQuality(q);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load AI governance metrics.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [router]);

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse" />
              <span className="text-xs font-semibold tracking-wider uppercase text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded-full border border-indigo-200">
                Ethical AI Architecture
              </span>
            </div>
            <h1 className="text-2xl font-bold text-slate-900 mt-1">Responsible AI & Evaluation Governance</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Deterministic mathematical scoring observability, protected attribute exclusion, and human review oversight telemetry.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-slate-500 bg-white border border-slate-200 px-3 py-1.5 rounded-lg shadow-sm">
              Total Evaluations: <span className="font-bold text-slate-900">{metrics?.total_evaluations ?? 0}</span>
            </span>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Bias & Statistical Fairness Statutory Notice */}
        <div className="mb-8 p-4 bg-amber-50/80 border border-amber-200 rounded-xl flex items-start gap-3">
          <svg className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div className="text-xs text-amber-950 leading-relaxed">
            <span className="font-bold">Algorithmic Fairness & Bias Governance Boundary:</span> {metrics?.fairness_and_bias_disclaimer || "Operational metrics reflect system score distributions and evidence verification. They do not constitute statutory proof of demographic parity without formal external adverse impact auditing."}
          </div>
        </div>

        {/* Top KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Average Score</p>
            <p className="text-2xl font-bold text-slate-900 mt-2">
              {loading ? "..." : `${metrics?.average_score ?? 0} / 100`}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">Deterministic category weights</p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Evidence Coverage</p>
            <p className="text-2xl font-bold text-emerald-600 mt-2">
              {loading ? "..." : `${metrics?.average_evidence_coverage_pct ?? 0}%`}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">Verifiable criteria citation rate</p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Token Verification</p>
            <p className="text-2xl font-bold text-indigo-600 mt-2">
              {loading ? "..." : `${quality?.token_verification_pass_rate_pct ?? 100}%`}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">Anti-fabrication match rate</p>
          </div>

          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Recruiter Overrides</p>
            <p className="text-2xl font-bold text-purple-600 mt-2">
              {loading ? "..." : `${metrics?.override_rate_pct ?? 0}%`}
            </p>
            <p className="text-[11px] text-slate-400 mt-1">Human-in-the-loop decisions</p>
          </div>
        </div>

        {/* Visual Score Distribution & Review Oversight Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          {/* Score Distribution */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 mb-1">Candidate Score Distribution</h3>
            <p className="text-xs text-slate-500 mb-6">
              Deterministic scoring tiers calculated from scorecard category weights.
            </p>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-semibold text-emerald-700">High Match (≥ 70)</span>
                  <span className="font-mono font-bold text-slate-900">{metrics?.score_distribution.high ?? 0}</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-emerald-500 h-2.5 rounded-full transition-all"
                    style={{
                      width: `${
                        metrics?.total_evaluations
                          ? Math.round(((metrics.score_distribution.high || 0) / metrics.total_evaluations) * 100)
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-semibold text-amber-700">Medium Match (50 – 69)</span>
                  <span className="font-mono font-bold text-slate-900">{metrics?.score_distribution.medium ?? 0}</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-amber-500 h-2.5 rounded-full transition-all"
                    style={{
                      width: `${
                        metrics?.total_evaluations
                          ? Math.round(((metrics.score_distribution.medium || 0) / metrics.total_evaluations) * 100)
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1">
                  <span className="font-semibold text-rose-700">Low Match (&lt; 50)</span>
                  <span className="font-mono font-bold text-slate-900">{metrics?.score_distribution.low ?? 0}</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-rose-500 h-2.5 rounded-full transition-all"
                    style={{
                      width: `${
                        metrics?.total_evaluations
                          ? Math.round(((metrics.score_distribution.low || 0) / metrics.total_evaluations) * 100)
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="mt-6 p-3 bg-slate-50 rounded-lg text-[11px] text-slate-500">
              💡 <span className="font-semibold text-slate-700">Zero Auto-Rejection Invariant:</span> Candidates scoring below 50 are never rejected automatically; they remain fully searchable and reviewable by recruiters.
            </div>
          </div>

          {/* Human Oversight & Reviews */}
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
            <h3 className="text-sm font-bold text-slate-900 mb-1">Human Recruiter Review Oversight</h3>
            <p className="text-xs text-slate-500 mb-6">
              Recruiter review decisions recorded separately from AI evaluation outputs.
            </p>

            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="p-3 bg-emerald-50 rounded-xl border border-emerald-100">
                <p className="text-[10px] font-semibold text-emerald-800 uppercase">Shortlisted</p>
                <p className="text-xl font-bold text-emerald-900 mt-1">
                  {metrics?.recruiter_review_distribution["SHORTLIST"] ?? 0}
                </p>
              </div>
              <div className="p-3 bg-rose-50 rounded-xl border border-rose-100">
                <p className="text-[10px] font-semibold text-rose-800 uppercase">Rejected</p>
                <p className="text-xl font-bold text-rose-900 mt-1">
                  {metrics?.recruiter_review_distribution["REJECT"] ?? 0}
                </p>
              </div>
              <div className="p-3 bg-amber-50 rounded-xl border border-amber-100">
                <p className="text-[10px] font-semibold text-amber-800 uppercase">On Hold</p>
                <p className="text-xl font-bold text-amber-900 mt-1">
                  {metrics?.recruiter_review_distribution["HOLD"] ?? 0}
                </p>
              </div>
              <div className="p-3 bg-slate-50 rounded-xl border border-slate-200">
                <p className="text-[10px] font-semibold text-slate-600 uppercase">Unreviewed</p>
                <p className="text-xl font-bold text-slate-900 mt-1">
                  {metrics?.recruiter_review_distribution["UNREVIEWED"] ?? 0}
                </p>
              </div>
            </div>

            <div className="mt-6 p-3 bg-slate-50 rounded-lg text-[11px] text-slate-500">
              👤 <span className="font-semibold text-slate-700">Human Discretion:</span> AI outputs serve as transparent evidence summaries. Client submissions require explicit human recruiter authorization.
            </div>
          </div>
        </div>

        {/* Quality Assurance Guarantees */}
        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
          <h3 className="text-sm font-bold text-slate-900 mb-4">Core Ethical AI Architecture Safeguards</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {quality?.quality_assurance_notes?.map((note, idx) => (
              <div key={idx} className="flex items-start gap-2.5 p-3 rounded-lg bg-slate-50 border border-slate-100">
                <span className="text-emerald-600 font-bold text-sm">✓</span>
                <span className="text-xs text-slate-700 leading-relaxed">{note}</span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
