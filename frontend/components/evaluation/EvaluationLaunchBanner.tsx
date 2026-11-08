"use client";

import React from "react";
import { Sparkles, AlertTriangle, ShieldCheck, HelpCircle, Loader2 } from "lucide-react";
import type { ScorecardResponse } from "@/lib/types";

interface EvaluationLaunchBannerProps {
  scorecard: ScorecardResponse | null;
  totalCandidates: number;
  isEvaluating: boolean;
  onEvaluateAll: () => void;
  onOpenProgress?: () => void;
  onOpenExplanation: () => void;
  onSwitchToScorecardTab: () => void;
  activeRunId: string | null;
  isRecruiter: boolean;
}

export default function EvaluationLaunchBanner({
  scorecard,
  totalCandidates,
  isEvaluating,
  onEvaluateAll,
  onOpenProgress,
  onOpenExplanation,
  onSwitchToScorecardTab,
  activeRunId,
  isRecruiter,
}: EvaluationLaunchBannerProps) {
  const isApproved = scorecard?.status === "approved";

  if (!isApproved) {
    return (
      <div className="bg-[#FDF6E7] border border-[#F1DCAC] rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-[#7A5212] shrink-0 mt-0.5" />
          <div>
            <h3 className="text-xs font-serif font-bold text-[#7A5212]">
              Approved Scorecard Required For AI Evaluation
            </h3>
            <p className="text-xs text-[#7A5212]/80 mt-0.5">
              To guarantee objective, grounded evaluation, candidates can only be evaluated against an approved scorecard version.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onSwitchToScorecardTab}
          className="bg-[#7A5212] hover:bg-[#5E3E0C] text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shrink-0 shadow-sm"
        >
          View & Approve Scorecard →
        </button>
      </div>
    );
  }

  return (
    <div className="bg-[#F5F1EA] border border-[#E8E2D8] text-[#292722] rounded-xl p-5 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 bg-[#EEF6F0] text-[#2A5A35] border border-[#C4E2CC] text-[11px] font-semibold px-2 py-0.5 rounded-full">
            <ShieldCheck className="w-3.5 h-3.5" />
            Approved Scorecard v{scorecard.version_number}
          </span>
          <button
            type="button"
            onClick={onOpenExplanation}
            className="inline-flex items-center gap-1 text-[11px] text-[#756653] hover:text-[#292722] underline underline-offset-2 ml-1 transition"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            How scoring works
          </button>
        </div>
        <h2 className="text-base font-serif font-bold text-[#292722] tracking-tight">
          Evidence-Grounded Candidate Evaluation & Deterministic Ranking
        </h2>
        <p className="text-xs text-[#6F6A61] max-w-2xl leading-relaxed">
          Evaluates resume evidence against criteria with zero hallucination. Scores are calculated deterministically by mathematical weights, preserving human recruiter judgment.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 shrink-0">
        {activeRunId && onOpenProgress && (
          <button
            type="button"
            onClick={onOpenProgress}
            className="bg-[#FFFFFF] hover:bg-[#FAF9F6] text-[#292722] text-xs font-semibold px-3.5 py-2 rounded-xl transition-colors border border-[#D9D1C5] shadow-sm inline-flex items-center gap-1.5"
          >
            {isEvaluating && <Loader2 className="w-3.5 h-3.5 animate-spin text-[#756653]" />}
            Batch Run Status
          </button>
        )}

        {isRecruiter && (
          <button
            type="button"
            disabled={isEvaluating || totalCandidates === 0}
            onClick={onEvaluateAll}
            className="bg-[#756653] hover:bg-[#5F5243] text-white text-xs font-bold px-4 py-2 rounded-xl transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
          >
            {isEvaluating ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Evaluating Batch...
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                Evaluate All Candidates ({totalCandidates})
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
