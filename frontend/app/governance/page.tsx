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
    <div className="min-h-screen bg-[#FAF9F6] selection:bg-[#EDE5D9] selection:text-[#292722]">
      <Navbar user={user} />

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-[#E8E2D8]">
          <div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-[#756653] animate-pulse" />
              <span className="text-xs font-semibold tracking-wider uppercase text-[#756653] bg-[#EDE5D9] px-2.5 py-0.5 rounded-full border border-[#D9D1C5]">
                Ethical AI Architecture
              </span>
            </div>
            <h1 className="text-2xl font-bold text-[#292722] tracking-tight mt-1">Responsible AI & Evaluation Governance</h1>
            <p className="text-xs text-[#6F6A61] mt-1">
              Deterministic mathematical scoring observability, protected attribute exclusion, and human review oversight telemetry.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-[#6F6A61] bg-[#FFFFFF] border border-[#E8E2D8] px-3.5 py-1.5 rounded-xl shadow-2xs">
              Total Evaluations: <span className="font-bold text-[#292722]">{metrics?.total_evaluations ?? 0}</span>
            </span>
          </div>
        </div>

        {error && (
          <div className="p-4 bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] rounded-xl text-xs font-medium">
            {error}
          </div>
        )}

        {/* Bias & Statistical Fairness Statutory Notice */}
        <div className="p-4 bg-[#F5F1EA] border border-[#E8E2D8] rounded-2xl flex items-start gap-3 shadow-xs">
          <svg className="w-5 h-5 text-[#756653] shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div className="text-xs text-[#6F6A61] leading-relaxed">
            <span className="font-semibold text-[#292722]">Algorithmic Fairness & Bias Governance Boundary:</span> {metrics?.fairness_and_bias_disclaimer || "Operational metrics reflect system score distributions and evidence verification. They do not constitute statutory proof of demographic parity without formal external adverse impact auditing."}
          </div>
        </div>

        {/* Top KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-[#E8E2D8] shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Average Score</p>
            <p className="text-2xl font-bold text-[#292722] mt-2">
              {loading ? "..." : `${metrics?.average_score ?? 0} / 100`}
            </p>
            <p className="text-[11px] text-[#918A80] mt-1">Deterministic category weights</p>
          </div>

          <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-[#E8E2D8] shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Evidence Coverage</p>
            <p className="text-2xl font-bold text-[#2A5A35] mt-2">
              {loading ? "..." : `${metrics?.average_evidence_coverage_pct ?? 0}%`}
            </p>
            <p className="text-[11px] text-[#918A80] mt-1">Verifiable criteria citation rate</p>
          </div>

          <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-[#E8E2D8] shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Token Verification</p>
            <p className="text-2xl font-bold text-[#264D6B] mt-2">
              {loading ? "..." : `${quality?.token_verification_pass_rate_pct ?? 100}%`}
            </p>
            <p className="text-[11px] text-[#918A80] mt-1">Anti-fabrication match rate</p>
          </div>

          <div className="bg-[#FFFFFF] p-5 rounded-2xl border border-[#E8E2D8] shadow-xs transition-shadow hover:shadow-sm">
            <p className="text-[11px] font-semibold text-[#6F6A61] uppercase tracking-wider">Recruiter Overrides</p>
            <p className="text-2xl font-bold text-[#756653] mt-2">
              {loading ? "..." : `${metrics?.override_rate_pct ?? 0}%`}
            </p>
            <p className="text-[11px] text-[#918A80] mt-1">Human-in-the-loop decisions</p>
          </div>
        </div>

        {/* Visual Score Distribution & Review Oversight Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Score Distribution */}
          <div className="bg-[#FFFFFF] p-6 rounded-2xl border border-[#E8E2D8] shadow-xs">
            <h3 className="text-sm font-bold text-[#292722] mb-1">Candidate Score Distribution</h3>
            <p className="text-xs text-[#6F6A61] mb-6">
              Deterministic scoring tiers calculated from scorecard category weights.
            </p>

            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-[#2A5A35]">High Match (≥ 70)</span>
                  <span className="font-mono font-bold text-[#292722]">{metrics?.score_distribution.high ?? 0}</span>
                </div>
                <div className="w-full bg-[#F5F1EA] rounded-full h-2.5 overflow-hidden border border-[#E8E2D8]">
                  <div
                    className="bg-[#2A5A35] h-2.5 rounded-full transition-all"
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
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-[#7A5212]">Medium Match (50 – 69)</span>
                  <span className="font-mono font-bold text-[#292722]">{metrics?.score_distribution.medium ?? 0}</span>
                </div>
                <div className="w-full bg-[#F5F1EA] rounded-full h-2.5 overflow-hidden border border-[#E8E2D8]">
                  <div
                    className="bg-[#7A5212] h-2.5 rounded-full transition-all"
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
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="font-semibold text-[#7A2525]">Low Match (&lt; 50)</span>
                  <span className="font-mono font-bold text-[#292722]">{metrics?.score_distribution.low ?? 0}</span>
                </div>
                <div className="w-full bg-[#F5F1EA] rounded-full h-2.5 overflow-hidden border border-[#E8E2D8]">
                  <div
                    className="bg-[#7A2525] h-2.5 rounded-full transition-all"
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

            <div className="mt-6 p-3 bg-[#F5F1EA] rounded-xl text-[11px] text-[#6F6A61] border border-[#E8E2D8]">
              💡 <span className="font-semibold text-[#292722]">Zero Auto-Rejection Invariant:</span> Candidates scoring below 50 are never rejected automatically; they remain fully searchable and reviewable by recruiters.
            </div>
          </div>

          {/* Human Oversight & Reviews */}
          <div className="bg-[#FFFFFF] p-6 rounded-2xl border border-[#E8E2D8] shadow-xs">
            <h3 className="text-sm font-bold text-[#292722] mb-1">Human Recruiter Review Oversight</h3>
            <p className="text-xs text-[#6F6A61] mb-6">
              Recruiter review decisions recorded separately from AI evaluation outputs.
            </p>

            <div className="grid grid-cols-2 gap-3 text-center">
              <div className="p-3 bg-[#EEF6F0] rounded-xl border border-[#C4E2CC]">
                <p className="text-[10px] font-bold text-[#2A5A35] uppercase">Shortlisted</p>
                <p className="text-xl font-bold text-[#2A5A35] mt-1">
                  {metrics?.recruiter_review_distribution["SHORTLIST"] ?? 0}
                </p>
              </div>
              <div className="p-3 bg-[#FDF0F0] rounded-xl border border-[#EFC2C2]">
                <p className="text-[10px] font-bold text-[#7A2525] uppercase">Rejected</p>
                <p className="text-xl font-bold text-[#7A2525] mt-1">
                  {metrics?.recruiter_review_distribution["REJECT"] ?? 0}
                </p>
              </div>
              <div className="p-3 bg-[#FDF6E7] rounded-xl border border-[#F1DCAC]">
                <p className="text-[10px] font-bold text-[#7A5212] uppercase">On Hold</p>
                <p className="text-xl font-bold text-[#7A5212] mt-1">
                  {metrics?.recruiter_review_distribution["HOLD"] ?? 0}
                </p>
              </div>
              <div className="p-3 bg-[#F2EFEB] rounded-xl border border-[#DFD9D0]">
                <p className="text-[10px] font-bold text-[#5E5950] uppercase">Unreviewed</p>
                <p className="text-xl font-bold text-[#292722] mt-1">
                  {metrics?.recruiter_review_distribution["UNREVIEWED"] ?? 0}
                </p>
              </div>
            </div>

            <div className="mt-6 p-3 bg-[#F5F1EA] rounded-xl text-[11px] text-[#6F6A61] border border-[#E8E2D8]">
              👤 <span className="font-semibold text-[#292722]">Human Discretion:</span> AI outputs serve as transparent evidence summaries. Client submissions require explicit human recruiter authorization.
            </div>
          </div>
        </div>

        {/* Quality Assurance Guarantees */}
        <div className="bg-[#FFFFFF] p-6 rounded-2xl border border-[#E8E2D8] shadow-xs">
          <h3 className="text-sm font-bold text-[#292722] mb-4">Core Ethical AI Architecture Safeguards</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {quality?.quality_assurance_notes?.map((note, idx) => (
              <div key={idx} className="flex items-start gap-2.5 p-3.5 rounded-xl bg-[#F5F1EA] border border-[#E8E2D8]">
                <span className="text-[#2A5A35] font-bold text-sm">✓</span>
                <span className="text-xs text-[#292722] leading-relaxed">{note}</span>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
