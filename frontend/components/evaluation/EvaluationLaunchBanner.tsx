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
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-sm">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          <div>
            <h3 className="text-xs font-bold text-amber-900">
              Approved Scorecard Required For AI Evaluation
            </h3>
            <p className="text-xs text-amber-700 mt-0.5">
              To guarantee objective, grounded evaluation, candidates can only be evaluated against an approved scorecard version.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={onSwitchToScorecardTab}
          className="bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shrink-0 shadow-xs"
        >
          View & Approve Scorecard →
        </button>
      </div>
    );
  }

  return (
    <div className="bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white rounded-xl p-5 shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1 bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[11px] font-semibold px-2 py-0.5 rounded-full">
            <ShieldCheck className="w-3.5 h-3.5" />
            Approved Scorecard v{scorecard.version_number}
          </span>
          <button
            type="button"
            onClick={onOpenExplanation}
            className="inline-flex items-center gap-1 text-[11px] text-indigo-200 hover:text-white underline underline-offset-2 ml-1"
          >
            <HelpCircle className="w-3.5 h-3.5" />
            How scoring works
          </button>
        </div>
        <h2 className="text-base font-bold text-white tracking-tight">
          Evidence-Grounded Candidate Evaluation & Deterministic Ranking
        </h2>
        <p className="text-xs text-indigo-200 max-w-2xl leading-relaxed">
          Evaluates resume evidence against criteria with zero hallucination. Scores are calculated deterministically by mathematical weights, preserving human recruiter judgment.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2 shrink-0">
        {activeRunId && onOpenProgress && (
          <button
            type="button"
            onClick={onOpenProgress}
            className="bg-indigo-700/80 hover:bg-indigo-600 text-white text-xs font-semibold px-3.5 py-2 rounded-lg transition-colors border border-indigo-500/40 shadow-xs inline-flex items-center gap-1.5"
          >
            {isEvaluating && <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-300" />}
            Batch Run Status
          </button>
        )}

        {isRecruiter && (
          <button
            type="button"
            disabled={isEvaluating || totalCandidates === 0}
            onClick={onEvaluateAll}
            className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-bold px-4 py-2 rounded-lg transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-1.5"
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

