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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-xs p-4 animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden border border-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-2">
            {!isFinished ? (
              <Loader2 className="w-5 h-5 text-indigo-600 animate-spin" />
            ) : run?.status === "COMPLETED" ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            ) : (
              <AlertCircle className="w-5 h-5 text-amber-600" />
            )}
            <div>
              <h3 className="text-sm font-bold text-slate-900">
                Batch Candidate Evaluation
              </h3>
              <p className="text-[11px] text-slate-500">
                Run ID: <span className="font-mono">{runId.slice(0, 8)}...</span>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-slate-600 rounded-lg p-1 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-5">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-xs p-3 rounded-lg">
              {error}
            </div>
          )}

          {loading && !run ? (
            <div className="py-8 text-center text-xs text-slate-500">
              <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-indigo-600" />
              Loading run status...
            </div>
          ) : (
            <>
              {/* Status Badge */}
              <div className="flex items-center justify-between text-xs">
                <span className="text-slate-500 font-medium">Status</span>
                <span
                  className={`font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider text-[11px] ${
                    run?.status === "COMPLETED"
                      ? "bg-emerald-100 text-emerald-800"
                      : run?.status === "PROCESSING" || run?.status === "PENDING"
                      ? "bg-indigo-100 text-indigo-800"
                      : "bg-amber-100 text-amber-800"
                  }`}
                >
                  {run?.status}
                </span>
              </div>

              {/* Progress Bar */}
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs">
                  <span className="font-medium text-slate-700">Overall Progress</span>
                  <span className="font-bold text-slate-900">{progressPercent}%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-2.5 rounded-full transition-all duration-300"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>

              {/* Stats Counters */}
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-slate-50 border border-slate-200/60 rounded-xl p-3">
                  <div className="text-lg font-bold text-slate-900">{total}</div>
                  <div className="text-[11px] text-slate-500 font-medium">Total Candidates</div>
                </div>
                <div className="bg-emerald-50 border border-emerald-200/60 rounded-xl p-3">
                  <div className="text-lg font-bold text-emerald-700">{completed}</div>
                  <div className="text-[11px] text-emerald-600 font-medium">Completed</div>
                </div>
                <div className="bg-rose-50 border border-rose-200/60 rounded-xl p-3">
                  <div className="text-lg font-bold text-rose-700">{failed}</div>
                  <div className="text-[11px] text-rose-600 font-medium">Failed</div>
                </div>
              </div>

              {/* Errors list if any */}
              {run?.error_summary?.errors && run.error_summary.errors.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-bold text-slate-700">Failed Candidates:</h4>
                  <div className="max-h-36 overflow-y-auto space-y-1.5 bg-slate-50 p-2 rounded-lg border border-slate-200">
                    {run.error_summary.errors.map((err, idx) => (
                      <div key={idx} className="text-[11px] text-slate-700">
                        <span className="font-mono text-slate-500">
                          {err.candidate_id.slice(0, 8)}...:
                        </span>{" "}
                        <span className="text-rose-600">{err.error}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow-xs"
          >
            {isFinished ? "Done" : "Run in Background"}
          </button>
        </div>
      </div>
    </div>
  );
}
