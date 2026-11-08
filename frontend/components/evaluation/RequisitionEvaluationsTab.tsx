"use client";

import React, { useState, useEffect, useCallback } from "react";
import EvaluationLaunchBanner from "./EvaluationLaunchBanner";
import RankedCandidatesTable from "./RankedCandidatesTable";
import EvaluationProgressModal from "./EvaluationProgressModal";
import CandidateEvaluationModal from "./CandidateEvaluationModal";
import ScoringExplanationModal from "./ScoringExplanationModal";
import { api } from "@/lib/api";
import type {
  CurrentUser,
  EvaluationResponse,
  ScorecardResponse,
} from "@/lib/types";

interface RequisitionEvaluationsTabProps {
  requisitionId: string;
  scorecard: ScorecardResponse | null;
  currentUser: CurrentUser | null;
  onSwitchToScorecardTab: () => void;
}

export default function RequisitionEvaluationsTab({
  requisitionId,
  scorecard,
  currentUser,
  onSwitchToScorecardTab,
}: RequisitionEvaluationsTabProps) {
  const [evaluations, setEvaluations] = useState<EvaluationResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);

  // Filters
  const [sortBy, setSortBy] = useState("score_desc");
  const [search, setSearch] = useState("");
  const [confidenceFilter, setConfidenceFilter] = useState("");
  const [reviewFilter, setReviewFilter] = useState("");
  const [scoreMin, setScoreMin] = useState("");
  const [scoreMax, setScoreMax] = useState("");
  const [missingEvidenceOnly, setMissingEvidenceOnly] = useState(false);
  const [mustHaveMatchedOnly, setMustHaveMatchedOnly] = useState(false);

  // Modals & Active IDs
  const [selectedEvaluationId, setSelectedEvaluationId] = useState<string | null>(null);
  const [isExplanationOpen, setIsExplanationOpen] = useState(false);
  const [isProgressModalOpen, setIsProgressModalOpen] = useState(false);
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  // Evaluating states
  const [isBatchEvaluating, setIsBatchEvaluating] = useState(false);
  const [evaluatingCandidateId, setEvaluatingCandidateId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [totalCandidatesCount, setTotalCandidatesCount] = useState(0);

  const isRecruiter =
    currentUser?.role === "recruiter" || currentUser?.role === "delivery_head";

  // Load evaluations
  const fetchEvaluations = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await api.listEvaluations(requisitionId, {
        page,
        pageSize: 15,
        sortBy,
        search: search.trim() || undefined,
        confidenceLevel: confidenceFilter || undefined,
        reviewDecision: reviewFilter || undefined,
        scoreMin: scoreMin ? Number(scoreMin) : undefined,
        scoreMax: scoreMax ? Number(scoreMax) : undefined,
        missingEvidenceOnly: missingEvidenceOnly || undefined,
        mustHaveMatchedOnly: mustHaveMatchedOnly || undefined,
      });
      setEvaluations(resp.items);
      setTotal(resp.total);
    } catch (err: unknown) {
      console.error("Failed to load evaluations:", err);
      setError(err instanceof Error ? err.message : "Failed to load candidate evaluations");
    } finally {
      setLoading(false);
    }
  }, [
    requisitionId,
    page,
    sortBy,
    search,
    confidenceFilter,
    reviewFilter,
    scoreMin,
    scoreMax,
    missingEvidenceOnly,
    mustHaveMatchedOnly,
  ]);

  // Load candidate count
  const fetchCandidateCount = useCallback(async () => {
    try {
      const cands = await api.listCandidates({ requisitionId, page: 1, pageSize: 1 });
      setTotalCandidatesCount(cands.total);
    } catch {
      // ignore
    }
  }, [requisitionId]);

  useEffect(() => {
    fetchEvaluations();
  }, [fetchEvaluations]);

  useEffect(() => {
    fetchCandidateCount();
  }, [fetchCandidateCount]);

  // Handle batch evaluation trigger
  async function handleEvaluateAll() {
    setIsBatchEvaluating(true);
    setError(null);
    try {
      const run = await api.startBatchEvaluation(requisitionId);
      setActiveRunId(run.id);
      setIsProgressModalOpen(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start batch evaluation");
      setIsBatchEvaluating(false);
    }
  }

  // Handle single candidate evaluation trigger
  async function handleSingleEvaluate(candidateId: string) {
    setEvaluatingCandidateId(candidateId);
    setError(null);
    try {
      const evalResp = await api.evaluateSingleCandidate(requisitionId, candidateId);
      setSelectedEvaluationId(evalResp.id);
      fetchEvaluations();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to evaluate candidate");
    } finally {
      setEvaluatingCandidateId(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Launch Banner & Scorecard Status */}
      <EvaluationLaunchBanner
        scorecard={scorecard}
        totalCandidates={totalCandidatesCount}
        isEvaluating={isBatchEvaluating}
        onEvaluateAll={handleEvaluateAll}
        onOpenProgress={() => setIsProgressModalOpen(true)}
        onOpenExplanation={() => setIsExplanationOpen(true)}
        onSwitchToScorecardTab={onSwitchToScorecardTab}
        activeRunId={activeRunId}
        isRecruiter={isRecruiter}
      />

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-xs p-3 rounded-xl font-medium">
          {error}
        </div>
      )}

      {/* Ranked Table */}
      <RankedCandidatesTable
        evaluations={evaluations}
        total={total}
        page={page}
        pageSize={15}
        loading={loading}
        onPageChange={(p) => setPage(p)}
        sortBy={sortBy}
        onSortByChange={(val) => {
          setSortBy(val);
          setPage(1);
        }}
        search={search}
        onSearchChange={(val) => {
          setSearch(val);
          setPage(1);
        }}
        confidenceFilter={confidenceFilter}
        onConfidenceFilterChange={(val) => {
          setConfidenceFilter(val);
          setPage(1);
        }}
        reviewFilter={reviewFilter}
        onReviewFilterChange={(val) => {
          setReviewFilter(val);
          setPage(1);
        }}
        scoreMin={scoreMin}
        onScoreMinChange={(val) => {
          setScoreMin(val);
          setPage(1);
        }}
        scoreMax={scoreMax}
        onScoreMaxChange={(val) => {
          setScoreMax(val);
          setPage(1);
        }}
        missingEvidenceOnly={missingEvidenceOnly}
        onMissingEvidenceOnlyChange={(val) => {
          setMissingEvidenceOnly(val);
          setPage(1);
        }}
        mustHaveMatchedOnly={mustHaveMatchedOnly}
        onMustHaveMatchedOnlyChange={(val) => {
          setMustHaveMatchedOnly(val);
          setPage(1);
        }}
        onSelectEvaluation={(id) => setSelectedEvaluationId(id)}
        onSingleEvaluate={handleSingleEvaluate}
        isEvaluatingCandidateId={evaluatingCandidateId}
        currentUser={currentUser}
      />

      {/* Modals */}
      {selectedEvaluationId && (
        <CandidateEvaluationModal
          evaluationId={selectedEvaluationId}
          isOpen={Boolean(selectedEvaluationId)}
          onClose={() => setSelectedEvaluationId(null)}
          currentUser={currentUser}
          onEvaluationUpdated={() => fetchEvaluations()}
        />
      )}

      {activeRunId && (
        <EvaluationProgressModal
          requisitionId={requisitionId}
          runId={activeRunId}
          isOpen={isProgressModalOpen}
          onClose={() => setIsProgressModalOpen(false)}
          onRunCompleted={() => {
            setIsBatchEvaluating(false);
            fetchEvaluations();
          }}
        />
      )}

      <ScoringExplanationModal
        isOpen={isExplanationOpen}
        onClose={() => setIsExplanationOpen(false)}
      />
    </div>
  );
}
