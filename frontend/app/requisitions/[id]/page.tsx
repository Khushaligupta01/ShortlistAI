"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import Navbar from "@/components/layout/Navbar";
import ScorecardEditor, {
  ScorecardEditorState,
} from "@/components/scorecard/ScorecardEditor";
import RequisitionCandidatesTab from "@/components/resume/RequisitionCandidatesTab";
import RequisitionEvaluationsTab from "@/components/evaluation/RequisitionEvaluationsTab";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import type { CurrentUser, Requisition, ScorecardResponse } from "@/lib/types";

export default function RequisitionDetailPage() {
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const requisitionId = params.id;

  const [user, setUser] = useState<CurrentUser | null>(null);
  const [requisition, setRequisition] = useState<Requisition | null>(null);
  const [scorecard, setScorecard] = useState<ScorecardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"evaluations" | "candidates" | "scorecard">("evaluations");

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    async function load() {
      try {
        const u = await api.getCurrentUser();
        setUser(u);

        const [req, sc] = await Promise.all([
          api.getRequisition(requisitionId),
          api.getScorecard(requisitionId).catch(() => null),
        ]);
        setRequisition(req);
        setScorecard(sc);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load requisition");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [requisitionId, router]);

  const isRecruiter = user?.role === "recruiter";
  const isApproved = scorecard?.status === "approved";

  // Handle Save Draft Update
  async function handleSaveDraft(state: ScorecardEditorState) {
    if (!requisition) return;
    setError(null);
    setActionMessage(null);
    setActionLoading(true);
    try {
      let updated: ScorecardResponse;
      if (!scorecard) {
        // Create scorecard if not yet created
        updated = await api.createScorecard(requisition.id, {
          experience_min:
            state.experience_min === "" ? null : Number(state.experience_min),
          experience_max:
            state.experience_max === "" ? null : Number(state.experience_max),
          location: state.location || undefined,
          max_notice_days:
            state.max_notice_days === "" ? null : Number(state.max_notice_days),
          scoring_config: state.scoring_config,
          criteria: state.criteria,
        });
      } else {
        // Update existing scorecard
        updated = await api.updateScorecard(requisition.id, {
          experience_min:
            state.experience_min === "" ? null : Number(state.experience_min),
          experience_max:
            state.experience_max === "" ? null : Number(state.experience_max),
          location: state.location || undefined,
          max_notice_days:
            state.max_notice_days === "" ? null : Number(state.max_notice_days),
          scoring_config: state.scoring_config,
          criteria: state.criteria,
        });
      }
      setScorecard(updated);
      setActionMessage("Scorecard draft saved successfully.");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to save scorecard");
    } finally {
      setActionLoading(false);
    }
  }

  // Handle Approve
  async function handleApprove(state: ScorecardEditorState) {
    if (!requisition) return;
    setError(null);
    setActionMessage(null);
    setActionLoading(true);
    try {
      // First save latest edits
      await handleSaveDraft(state);
      // Then approve
      const approved = await api.approveScorecard(requisition.id);
      setScorecard(approved);
      setRequisition((prev) => (prev ? { ...prev, status: "active" } : null));
      setActionMessage("Scorecard approved and activated successfully!");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to approve scorecard");
    } finally {
      setActionLoading(false);
    }
  }

  // Handle Duplicate (Create new version)
  async function handleCreateNewVersion() {
    if (!requisition) return;
    setError(null);
    setActionMessage(null);
    setActionLoading(true);
    try {
      const newVersion = await api.duplicateScorecard(requisition.id);
      setScorecard(newVersion);
      setActionMessage(`Created new draft scorecard Version ${newVersion.version_number}.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to duplicate scorecard");
    } finally {
      setActionLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <Navbar user={user} />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
            <p className="text-xs text-slate-500">Loading requisition details...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!requisition) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col">
        <Navbar user={user} />
        <div className="flex-1 max-w-3xl mx-auto px-6 py-12 text-center">
          <p className="text-red-600 font-semibold text-sm">Requisition not found</p>
          <p className="text-xs text-slate-400 mt-1">
            This requisition may not exist or belongs to another organization.
          </p>
          <Link
            href="/requisitions"
            className="mt-4 inline-block text-xs font-semibold text-indigo-600 hover:underline"
          >
            ← Back to Requisitions
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <Navbar user={user} />

      <main className="max-w-5xl mx-auto px-6 py-8 flex-1 w-full space-y-6">
        {/* Breadcrumb & Header */}
        <div>
          <Link
            href="/requisitions"
            className="text-xs font-medium text-slate-500 hover:text-indigo-600 inline-flex items-center gap-1 mb-2"
          >
            ← Back to Requisitions
          </Link>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900">{requisition.title}</h1>
                <span
                  className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${
                    requisition.status === "active"
                      ? "bg-emerald-100 text-emerald-800"
                      : requisition.status === "archived"
                      ? "bg-slate-100 text-slate-600"
                      : "bg-amber-100 text-amber-800"
                  }`}
                >
                  {requisition.status}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                Location: <span className="font-medium text-slate-700">{requisition.location || "Unspecified"}</span> • Created:{" "}
                {new Date(requisition.created_at).toLocaleDateString()}
              </p>
            </div>

            {/* Version control action */}
            {isApproved && isRecruiter && (
              <button
                type="button"
                disabled={actionLoading}
                onClick={handleCreateNewVersion}
                className="inline-flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow-sm disabled:opacity-50"
              >
                + Create New Version (v{(scorecard?.version_number ?? 1) + 1})
              </button>
            )}
          </div>
        </div>

        {/* Alerts */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-xs font-medium p-4 rounded-xl">
            {error}
          </div>
        )}
        {actionMessage && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-700 text-xs font-medium p-4 rounded-xl">
            {actionMessage}
          </div>
        )}

        {/* Navigation Tabs */}
        <div className="flex border-b border-slate-200 gap-4">
          <button
            type="button"
            onClick={() => setActiveTab("evaluations")}
            className={`pb-3 text-xs font-bold transition-all relative ${
              activeTab === "evaluations"
                ? "text-indigo-600 border-b-2 border-indigo-600"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Evaluations & Ranking
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("candidates")}
            className={`pb-3 text-xs font-bold transition-all relative ${
              activeTab === "candidates"
                ? "text-indigo-600 border-b-2 border-indigo-600"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Candidates & Ingestion
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("scorecard")}
            className={`pb-3 text-xs font-bold transition-all relative ${
              activeTab === "scorecard"
                ? "text-indigo-600 border-b-2 border-indigo-600"
                : "text-slate-500 hover:text-slate-800"
            }`}
          >
            Scorecard & Requirements
          </button>
        </div>

        {/* Tab 1: AI Evidence Evaluations & Deterministic Ranking */}
        {activeTab === "evaluations" && (
          <RequisitionEvaluationsTab
            requisitionId={requisition.id}
            scorecard={scorecard}
            currentUser={user}
            onSwitchToScorecardTab={() => setActiveTab("scorecard")}
          />
        )}

        {/* Tab 2: Candidates Pipeline */}
        {activeTab === "candidates" && (
          <RequisitionCandidatesTab
            requisitionId={requisition.id}
            currentUser={user}
          />
        )}

        {/* Tab 3: Scorecard Editor & JD */}
        {activeTab === "scorecard" && (
          <div className="space-y-6">
            {/* Job Description Card */}
            <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-2">
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Job Description
              </h3>
              <p className="text-xs text-slate-700 font-mono whitespace-pre-wrap bg-slate-50 p-4 rounded-lg border border-slate-100 leading-relaxed max-h-60 overflow-y-auto">
                {requisition.job_description}
              </p>
            </div>

            {/* Scorecard Section */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-base font-bold text-slate-900">
                    Evaluation Scorecard
                  </h2>
                  <p className="text-xs text-slate-500">
                    Version {scorecard?.version_number ?? 1} • Status:{" "}
                    <span className="font-semibold capitalize text-slate-700">
                      {scorecard?.status ?? "draft"}
                    </span>
                    {scorecard?.approved_at && (
                      <span>
                        {" "}• Approved: {new Date(scorecard.approved_at).toLocaleString()}
                      </span>
                    )}
                  </p>
                </div>
              </div>

              <ScorecardEditor
                initialState={
                  scorecard
                    ? {
                        experience_min: scorecard.experience_min ?? "",
                        experience_max: scorecard.experience_max ?? "",
                        location: scorecard.location ?? "",
                        max_notice_days: scorecard.max_notice_days ?? "",
                        scoring_config: scorecard.scoring_config ?? undefined,
                        criteria: scorecard.criteria,
                      }
                    : undefined
                }
                isLocked={isApproved || !isRecruiter}
                versionNumber={scorecard?.version_number ?? 1}
                onSaveDraft={isRecruiter && !isApproved ? handleSaveDraft : undefined}
                onApprove={isRecruiter && !isApproved ? handleApprove : undefined}
                isLoading={actionLoading}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

