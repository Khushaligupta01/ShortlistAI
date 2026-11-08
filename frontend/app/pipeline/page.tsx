"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { isAuthenticated } from "@/lib/auth";
import Navbar from "@/components/layout/Navbar";
import type {
  ClientOrgOption,
  CurrentUser,
  PipelineBoardData,
  RecruiterSubmissionListItem,
} from "@/lib/types";

export default function PipelinePage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [boardData, setBoardData] = useState<PipelineBoardData | null>(null);
  const [clients, setClients] = useState<ClientOrgOption[]>([]);
  const [selectedClient, setSelectedClient] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Quick stage transition modal
  const [selectedSub, setSelectedSub] = useState<RecruiterSubmissionListItem | null>(null);
  const [targetStage, setTargetStage] = useState<string>("");
  const [stageNote, setStageNote] = useState<string>("");
  const [updating, setUpdating] = useState(false);

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
      return;
    }

    async function loadData() {
      try {
        const currentUser = await api.getCurrentUser();
        if (currentUser.role === "client_hiring_manager") {
          router.replace("/client");
          return;
        }
        setUser(currentUser);

        const [board, clientList] = await Promise.all([
          api.getPipelineBoard({
            client_org_id: selectedClient || undefined,
          }),
          api.getClientOrganizations(),
        ]);
        setBoardData(board);
        setClients(clientList);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load pipeline");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [selectedClient, router]);

  async function handleStageChange() {
    if (!selectedSub || !targetStage) return;
    setUpdating(true);
    try {
      await api.updatePipelineStage(selectedSub.submission_id, {
        stage: targetStage,
        reason_note: stageNote.trim() || undefined,
      });
      const updatedBoard = await api.getPipelineBoard({
        client_org_id: selectedClient || undefined,
      });
      setBoardData(updatedBoard);
      setSelectedSub(null);
      setTargetStage("");
      setStageNote("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to move candidate");
    } finally {
      setUpdating(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Navbar user={user} />

      <main className="max-w-[1600px] mx-auto px-6 py-8 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Hiring Pipeline Workspace</h1>
            <p className="text-sm text-slate-500 mt-1">
              Kanban view of submitted candidates across all client hiring stages.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <select
              value={selectedClient}
              onChange={(e) => setSelectedClient(e.target.value)}
              className="border border-slate-300 rounded-xl px-3 py-2 text-xs text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 shadow-sm bg-white"
            >
              <option value="">All Client Companies</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-xl text-sm">
            {error}
          </div>
        )}

        {/* Pipeline Board Columns */}
        {boardData && (
          <div className="flex gap-4 overflow-x-auto pb-6">
            {boardData.stages.map((col) => {
              const subsInStage = boardData.submissions.filter(
                (s) => s.current_stage === col.stage
              );

              return (
                <div
                  key={col.stage}
                  className="w-72 shrink-0 bg-slate-100 rounded-2xl p-3 flex flex-col max-h-[calc(100vh-220px)] shadow-inner"
                >
                  {/* Column Header */}
                  <div className="flex items-center justify-between px-2 py-2 mb-2">
                    <span className="font-bold text-xs text-slate-800 uppercase tracking-wider">
                      {col.stage_label}
                    </span>
                    <span className="bg-white text-slate-600 font-bold text-xs px-2 py-0.5 rounded-full shadow-sm">
                      {subsInStage.length}
                    </span>
                  </div>

                  {/* Cards List */}
                  <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
                    {subsInStage.length === 0 ? (
                      <div className="p-6 text-center text-slate-400 text-xs italic">
                        No candidates in this stage
                      </div>
                    ) : (
                      subsInStage.map((sub) => (
                        <div
                          key={sub.submission_id}
                          className="bg-white rounded-xl p-3.5 border border-slate-200 shadow-sm hover:shadow transition space-y-2"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div>
                              <Link
                                href={`/candidates/${sub.candidate_id}`}
                                className="font-bold text-xs text-slate-900 hover:text-indigo-600 block"
                              >
                                {sub.candidate_name}
                              </Link>
                              <span className="text-[10px] text-slate-400 font-mono">
                                {sub.candidate_reference}
                              </span>
                            </div>
                            {sub.overall_score !== null && sub.overall_score !== undefined && (
                              <span className="text-[11px] font-bold text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-100 shrink-0">
                                {Math.round(sub.overall_score)}%
                              </span>
                            )}
                          </div>

                          <div className="text-[11px] text-slate-500 space-y-0.5">
                            <p className="font-medium text-slate-700 truncate">
                              🏢 {sub.client_organization_name}
                            </p>
                            <p className="truncate">
                              📋 {sub.requisition_title}
                            </p>
                          </div>

                          {sub.pending_requests_count > 0 && (
                            <span className="inline-block bg-amber-50 text-amber-800 text-[10px] font-bold px-2 py-0.5 rounded border border-amber-200">
                              ⚠️ Action required by client
                            </span>
                          )}

                          <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                            <span className="text-[10px] text-slate-400">
                              {new Date(sub.submitted_at).toLocaleDateString()}
                            </span>
                            <button
                              onClick={() => {
                                setSelectedSub(sub);
                                setTargetStage("");
                                setStageNote("");
                              }}
                              className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800"
                            >
                              Move Stage &rarr;
                            </button>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      {/* Move Stage Modal */}
      {selectedSub && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-slate-900">
              Move Candidate: {selectedSub.candidate_name}
            </h3>
            <p className="text-xs text-slate-500">
              Current stage: <strong>{selectedSub.current_stage}</strong>
            </p>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Select Destination Stage
              </label>
              <select
                value={targetStage}
                onChange={(e) => setTargetStage(e.target.value)}
                className="w-full border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">-- Choose Stage --</option>
                {boardData?.stages.map((st) => (
                  <option key={st.stage} value={st.stage}>
                    {st.stage_label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 block mb-1">
                Reason / Note (Optional)
              </label>
              <textarea
                rows={2}
                value={stageNote}
                onChange={(e) => setStageNote(e.target.value)}
                placeholder="Optional transition note..."
                className="w-full border border-slate-300 rounded-xl p-2.5 text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-100">
              <button
                type="button"
                onClick={() => setSelectedSub(null)}
                className="text-xs font-semibold text-slate-600 hover:text-slate-800 px-4 py-2"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!targetStage || updating}
                onClick={handleStageChange}
                className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white text-xs font-bold px-4 py-2 rounded-xl transition shadow"
              >
                {updating ? "Moving..." : "Move Stage"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

