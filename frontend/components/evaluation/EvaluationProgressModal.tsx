"use client";

import React, { useEffect, useState } from "react";
import { X, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import type { EvaluationRunResponse } from "@/lib/types";

interface EvaluationProgressModalProps {
  requisitionId: string;
  runId: string;
  isOpen: boolean;
  onClose: () => void;
  onRunCompleted?: () => void;
}

export default function EvaluationProgressModal({
  requisitionId,
  runId,
  isOpen,
  onClose,
  onRunCompleted,
}: EvaluationProgressModalProps) {
  const [run, setRun] = useState<EvaluationRunResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !runId) return;

    let isMounted = true;
    let pollInterval: NodeJS.Timeout | null = null;

    async function fetchStatus() {
      try {
        const data = await api.getEvaluationRun(requisitionId, runId);
        if (!isMounted) return;
        setRun(data);
        setError(null);

        if (data.status === "COMPLETED" || data.status === "PARTIALLY_FAILED" || data.status === "FAILED") {
          if (pollInterval) clearInterval(pollInterval);
          if (onRunCompleted) onRunCompleted();
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : "Failed to load evaluation status");
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchStatus();
    pollInterval = setInterval(fetchStatus, 2000);

    return () => {
      isMounted = false;
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [requisitionId, runId, isOpen, onRunCompleted]);

  if (!isOpen) return null;

  const total = run?.total_candidates ?? 0;
  const completed = run?.completed_count ?? 0;
  const failed = run?.failed_count ?? 0;
  const processed = completed + failed;
  const progressPercent = total > 0 ? Math.round((processed / total) * 100) : 0;

  const isFinished =
    run?.status === "COMPLETED" || run?.status === "PARTIALLY_FAILED" || run?.status === "FAILED";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#292722]/50 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-[#FFFFFF] rounded-2xl shadow-xl w-full max-w-lg overflow-hidden border border-[#E8E2D8] text-[#292722]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E8E2D8] bg-[#F5F1EA]">
          <div className="flex items-center gap-2">
            {!isFinished ? (
              <Loader2 className="w-5 h-5 text-[#756653] animate-spin" />
            ) : run?.status === "COMPLETED" ? (
              <CheckCircle2 className="w-5 h-5 text-[#2A5A35]" />
            ) : (
              <AlertCircle className="w-5 h-5 text-[#7A5212]" />
            )}
            <div>
              <h3 className="text-sm font-serif font-bold text-[#292722]">
                Batch Candidate Evaluation
              </h3>
              <p className="text-[11px] text-[#6F6A61]">
                Run ID: <span className="font-mono">{runId.slice(0, 8)}...</span>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-[#918A80] hover:text-[#292722] rounded-lg p-1 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {error && (
            <div className="bg-[#FDF0F0] border border-[#EFC2C2] text-[#7A2525] text-xs p-3 rounded-lg">
              {error}
            </div>
          )}

          {loading && !run ? (
            <div className="py-8 text-center text-xs text-[#6F6A61]">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-[#756653]" />
              Loading run status...
            </div>
          ) : (
            <>
              {/* Status Badge */}
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#6F6A61] font-medium">Status</span>
                <span
                  className={`font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider text-[11px] border ${
                    run?.status === "COMPLETED"
                      ? "bg-[#EEF6F0] text-[#2A5A35] border-[#C4E2CC]"
                      : run?.status === "PROCESSING" || run?.status === "PENDING"
                      ? "bg-[#EDE5D9] text-[#5F5243] border-[#D9D1C5]"
                      : "bg-[#FDF6E7] text-[#7A5212] border-[#F1DCAC]"
                  }`}
                >
                  {run?.status}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-medium text-[#292722]">Overall Progress</span>
                  <span className="font-bold text-[#292722]">{progressPercent}%</span>
                </div>
                <div className="w-full bg-[#EEE8DD] rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-[#756653] h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>

              {/* Stats Counters */}
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-[#F5F1EA] border border-[#E8E2D8] rounded-xl p-3">
                  <div className="text-lg font-serif font-bold text-[#292722]">{total}</div>
                  <div className="text-[11px] text-[#6F6A61] font-medium">Total Candidates</div>
                </div>
                <div className="bg-[#EEF6F0] border border-[#C4E2CC] rounded-xl p-3">
                  <div className="text-lg font-serif font-bold text-[#2A5A35]">{completed}</div>
                  <div className="text-[11px] text-[#2A5A35] font-medium">Completed</div>
                </div>
                <div className="bg-[#FDF0F0] border border-[#EFC2C2] rounded-xl p-3">
                  <div className="text-lg font-serif font-bold text-[#7A2525]">{failed}</div>
                  <div className="text-[11px] text-[#7A2525] font-medium">Failed</div>
                </div>
              </div>

              {/* Errors list if any */}
              {run?.error_summary?.errors && run.error_summary.errors.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-serif font-bold text-[#292722]">Failed Candidates:</h4>
                  <div className="max-h-36 overflow-y-auto space-y-1.5 bg-[#FAF9F6] p-2.5 rounded-lg border border-[#E8E2D8]">
                    {run.error_summary.errors.map((err, idx) => (
                      <div key={idx} className="text-[11px] text-[#292722]">
                        <span className="font-mono text-[#918A80]">
                          {err.candidate_id.slice(0, 8)}...:
                        </span>{" "}
                        <span className="text-[#7A2525]">{err.error}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-[#F5F1EA] border-t border-[#E8E2D8] flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="bg-[#756653] hover:bg-[#5F5243] text-white text-xs font-semibold px-4 py-2 rounded-xl transition-colors shadow-sm"
          >
            {isFinished ? "Done" : "Run in Background"}
          </button>
        </div>
      </div>
    </div>
  );
}
