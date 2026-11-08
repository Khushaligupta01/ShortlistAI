"use client";

import { useEffect, useState, useCallback } from "react";
import {
  CheckCircle2,
  Clock,
  Copy,
  AlertTriangle,
  XCircle,
  RefreshCw,
  FileText,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { api } from "@/lib/api";
import type { ResumeFile, UploadBatch } from "@/lib/types";

interface BatchProcessingDashboardProps {
  batchId: string;
  onRefreshCandidates?: () => void;
  onSelectCandidate?: (candidateId: string) => void;
}

export default function BatchProcessingDashboard({
  batchId,
  onRefreshCandidates,
  onSelectCandidate,
}: BatchProcessingDashboardProps) {
  const [batch, setBatch] = useState<UploadBatch | null>(null);
  const [files, setFiles] = useState<ResumeFile[]>([]);
  const [isExpanded, setIsExpanded] = useState(true);
  const [loading, setLoading] = useState(true);
  const [retryingId, setRetryingId] = useState<string | null>(null);

  const fetchBatchData = useCallback(async () => {
    try {
      const [bData, fData] = await Promise.all([
        api.getBatchStatus(batchId),
        api.getBatchFiles(batchId),
      ]);
      setBatch(bData);
      setFiles(fData);

      if (bData.status === "completed" || bData.status === "partial_failure") {
        onRefreshCandidates?.();
      }
    } catch (err) {
      console.error("Failed to fetch batch status:", err);
    } finally {
      setLoading(false);
    }
  }, [batchId, onRefreshCandidates]);

  useEffect(() => {
    fetchBatchData();
    // Poll every 3 seconds while processing
    const interval = setInterval(() => {
      if (batch?.status === "processing") {
        fetchBatchData();
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [batch?.status, fetchBatchData]);

  async function handleRetry(fileId: string) {
    setRetryingId(fileId);
    try {
      await api.retryResume(fileId);
      await fetchBatchData();
      onRefreshCandidates?.();
    } catch (err) {
      console.error("Failed to retry resume:", err);
    } finally {
      setRetryingId(null);
    }
  }

  if (loading && !batch) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl p-4 flex items-center justify-center gap-2 text-xs text-slate-500">
        <RefreshCw className="w-4 h-4 animate-spin text-indigo-600" />
        Loading batch status...
      </div>
    );
  }

  if (!batch) return null;

  const total = batch.total_files || 1;
  const processed = batch.completed_files + batch.duplicate_files + batch.failed_files;
  const progressPercent = Math.min(100, Math.round((processed / total) * 100));

  function getStatusBadge(f: ResumeFile) {
    switch (f.parse_status) {
      case "parsed":
        return (
          <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 text-[11px] font-semibold px-2 py-0.5 rounded-full border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" /> Parsed
          </span>
        );
      case "duplicate":
        return (
          <span className="inline-flex items-center gap-1 bg-amber-50 text-amber-700 text-[11px] font-semibold px-2 py-0.5 rounded-full border border-amber-200">
            <Copy className="w-3 h-3 text-amber-600" /> Duplicate ({f.duplicate_type || "file"})
          </span>
        );
      case "needs_review":
        return (
          <span className="inline-flex items-center gap-1 bg-amber-50 text-amber-800 text-[11px] font-semibold px-2 py-0.5 rounded-full border border-amber-300">
            <AlertTriangle className="w-3 h-3 text-amber-600" /> Needs Review
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1 bg-red-50 text-red-700 text-[11px] font-semibold px-2 py-0.5 rounded-full border border-red-200">
            <XCircle className="w-3 h-3 text-red-600" /> Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 bg-blue-50 text-blue-700 text-[11px] font-semibold px-2 py-0.5 rounded-full border border-blue-200">
            <Clock className="w-3 h-3 text-blue-600 animate-spin" />{" "}
            {f.extraction_status === "extracting" ? "Extracting Text" : "Processing"}
          </span>
        );
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden transition-all">
      {/* Header Banner */}
      <div className="p-4 px-5 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-slate-50/50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 font-bold text-xs">
            {progressPercent}%
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-bold text-slate-900">
                Batch Ingestion: {batch.status.toUpperCase().replace("_", " ")}
              </h3>
              {batch.status === "processing" && (
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Batch ID: <span className="font-mono text-slate-600">{batch.id.substring(0, 8)}...</span> • Uploaded:{" "}
              {new Date(batch.created_at).toLocaleTimeString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={fetchBatchData}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg text-xs font-medium flex items-center gap-1"
            title="Refresh Status"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Refresh
          </button>
          <button
            type="button"
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-100 rounded-lg text-xs font-medium flex items-center gap-1"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-100 h-1.5 overflow-hidden">
        <div
          className={`h-full transition-all duration-500 ${
            batch.status === "completed"
              ? "bg-emerald-500"
              : batch.status === "partial_failure"
              ? "bg-amber-500"
              : "bg-indigo-600"
          }`}
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      {isExpanded && (
        <div className="p-5 space-y-5">
          {/* Metric Badges */}
          <div className="grid grid-cols-2 sm:grid-cols-6 gap-3">
            <div className="bg-slate-50 border border-slate-100 rounded-lg p-2.5 text-center">
              <span className="text-[11px] font-medium text-slate-500 block">Total Files</span>
              <span className="text-base font-bold text-slate-800">{batch.total_files}</span>
            </div>
            <div className="bg-emerald-50/50 border border-emerald-100 rounded-lg p-2.5 text-center">
              <span className="text-[11px] font-medium text-emerald-600 block">Parsed</span>
              <span className="text-base font-bold text-emerald-700">{batch.completed_files}</span>
            </div>
            <div className="bg-blue-50/50 border border-blue-100 rounded-lg p-2.5 text-center">
              <span className="text-[11px] font-medium text-blue-600 block">Processing</span>
              <span className="text-base font-bold text-blue-700">{batch.processing_files}</span>
            </div>
            <div className="bg-amber-50/50 border border-amber-100 rounded-lg p-2.5 text-center">
              <span className="text-[11px] font-medium text-amber-600 block">Duplicates</span>
              <span className="text-base font-bold text-amber-700">{batch.duplicate_files}</span>
            </div>
            <div className="bg-yellow-50/50 border border-yellow-100 rounded-lg p-2.5 text-center">
              <span className="text-[11px] font-medium text-yellow-700 block">Needs Review</span>
              <span className="text-base font-bold text-yellow-800">
                {files.filter((f) => f.parse_status === "needs_review").length}
              </span>
            </div>
            <div className="bg-red-50/50 border border-red-100 rounded-lg p-2.5 text-center">
              <span className="text-[11px] font-medium text-red-600 block">Failed</span>
              <span className="text-base font-bold text-red-700">{batch.failed_files}</span>
            </div>
          </div>

          {/* Individual File List */}
          <div className="border border-slate-200 rounded-xl overflow-hidden divide-y divide-slate-100 max-h-72 overflow-y-auto">
            {files.map((file) => (
              <div
                key={file.id}
                className="p-3 px-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 hover:bg-slate-50/80 transition-colors text-xs"
              >
                <div className="flex items-center gap-2.5 min-w-0 pr-3">
                  <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                  <div className="truncate">
                    <p className="font-semibold text-slate-800 truncate">{file.file_name}</p>
                    {file.error_message_safe && (
                      <p className="text-[11px] text-red-600 truncate mt-0.5">
                        {file.error_message_safe}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0 self-end sm:self-center">
                  {getStatusBadge(file)}

                  {file.candidate_id && (
                    <button
                      type="button"
                      onClick={() => onSelectCandidate?.(file.candidate_id!)}
                      className="text-xs font-semibold text-indigo-600 hover:underline"
                    >
                      View Profile
                    </button>
                  )}

                  {(file.parse_status === "failed" || file.parse_status === "needs_review") && (
                    <button
                      type="button"
                      disabled={retryingId === file.id}
                      onClick={() => handleRetry(file.id)}
                      className="inline-flex items-center gap-1 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold px-2.5 py-1 rounded text-[11px] transition-colors disabled:opacity-50"
                    >
                      <RefreshCw className={`w-3 h-3 ${retryingId === file.id ? "animate-spin" : ""}`} />
                      {retryingId === file.id ? "Retrying..." : "Retry"}
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

