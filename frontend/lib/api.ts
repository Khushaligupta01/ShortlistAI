import { clearTokens, getAccessToken, getRefreshToken, saveTokens } from "./auth";
import type {
  ApiError,
  CandidateDetail,
  CandidateEvaluationHistoryItem,
  CandidateListResponse,
  CandidateNote,
  CandidateNoteListResponse,
  CriterionEvidenceResponse,
  CurrentUser,
  DashboardActivityResponse,
  EvaluationListResponse,
  EvaluationResponse,
  EvaluationRunResponse,
  JDExtractionResult,
  RecruiterDashboardData,
  RecruiterReviewCreateRequest,
  RecruiterReviewResponse,
  Requisition,
  RequisitionListResponse,
  RequisitionSummary,
  ResumeDetail,
  ResumeFile,
  ResumeReviewRequest,
  ScorecardCreate,
  ScorecardResponse,
  ScorecardUpdate,
  TokenResponse,
  UploadBatch,
  ClientDashboardMetrics,
  ClientRequisitionListItem,
  ClientRequisitionDetail,
  ClientSubmissionListItem,
  MaskedCandidateProfile,
  ClientRequest,
  PipelineRecord,
  RecruiterSubmissionListItem,
  PipelineBoardData,
  ClientOrgOption,
  DeliveryPipelineSummary,
  ConsentRecord,
  ConsentRequestResponse,
  ConsentPublicInfo,
  DataRequest,
  DeletionRequest,
  AuditEvent,
  AuditLogListResponse,
  GovernanceAIMetrics,
  EvaluationQuality,
  PrivacyDashboardStats,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class ApiClient {
  private async request<T>(
    path: string,
    options: RequestInit = {},
    retry = true
  ): Promise<T> {
    const token = getAccessToken();
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...((options.headers as Record<string, string>) ?? {}),
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    // Token expired — attempt refresh once
    if (response.status === 401 && retry) {
      const refreshed = await this.tryRefresh();
      if (refreshed) {
        return this.request<T>(path, options, false);
      }
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Session expired");
    }

    if (!response.ok) {
      let errorData: ApiError;
      try {
        errorData = await response.json();
      } catch {
        throw new Error(`HTTP ${response.status}`);
      }
      throw new Error(
        errorData.message ?? errorData.detail ?? `HTTP ${response.status}`
      );
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }

  private async tryRefresh(): Promise<boolean> {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return false;
    try {
      const resp = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!resp.ok) return false;
      const tokens: TokenResponse = await resp.json();
      saveTokens(tokens);
      return true;
    } catch {
      return false;
    }
  }

  async login(email: string, password: string): Promise<TokenResponse> {
    const resp = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({ message: "Login failed" }));
      throw new Error(err.message ?? err.detail ?? "Login failed");
    }
    return resp.json();
  }

  async logout(refreshToken: string): Promise<void> {
    await fetch(`${API_BASE}/api/v1/auth/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${getAccessToken() ?? ""}`,
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  }

  async getCurrentUser(): Promise<CurrentUser> {
    return this.request<CurrentUser>("/api/v1/auth/me");
  }

  // ── Requisitions ─────────────────────────────────────────────────────────

  async getRequisitions(
    page = 1,
    pageSize = 20,
    status?: string,
    search?: string
  ): Promise<RequisitionListResponse> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (status) params.set("status", status);
    if (search) params.set("search", search);

    return this.request<RequisitionListResponse>(
      `/api/v1/requisitions?${params.toString()}`
    );
  }

  async getRequisition(id: string): Promise<Requisition> {
    return this.request<Requisition>(`/api/v1/requisitions/${id}`);
  }

  async createRequisition(data: {
    title: string;
    job_description: string;
    location?: string;
  }): Promise<Requisition> {
    return this.request<Requisition>("/api/v1/requisitions", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // ── AI Extraction ────────────────────────────────────────────────────────

  async extractRequirements(jobDescription: string): Promise<JDExtractionResult> {
    return this.request<JDExtractionResult>(
      "/api/v1/requisitions/extract-requirements",
      {
        method: "POST",
        body: JSON.stringify({ job_description: jobDescription }),
      }
    );
  }

  // ── Scorecards ───────────────────────────────────────────────────────────

  async getScorecard(requisitionId: string): Promise<ScorecardResponse> {
    return this.request<ScorecardResponse>(
      `/api/v1/requisitions/${requisitionId}/scorecard`
    );
  }

  async createScorecard(
    requisitionId: string,
    data: ScorecardCreate
  ): Promise<ScorecardResponse> {
    return this.request<ScorecardResponse>(
      `/api/v1/requisitions/${requisitionId}/scorecards`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async updateScorecard(
    requisitionId: string,
    data: ScorecardUpdate
  ): Promise<ScorecardResponse> {
    return this.request<ScorecardResponse>(
      `/api/v1/requisitions/${requisitionId}/scorecard`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      }
    );
  }

  async approveScorecard(requisitionId: string): Promise<ScorecardResponse> {
    return this.request<ScorecardResponse>(
      `/api/v1/requisitions/${requisitionId}/scorecard/approve`,
      {
        method: "POST",
      }
    );
  }

  async duplicateScorecard(requisitionId: string): Promise<ScorecardResponse> {
    return this.request<ScorecardResponse>(
      `/api/v1/requisitions/${requisitionId}/scorecard/duplicate`,
      {
        method: "POST",
      }
    );
  }

  // ── Phase 4: Resume Ingestion & Candidate Methods ────────────────────────

  async uploadResumes(
    requisitionId: string,
    files: File[]
  ): Promise<UploadBatch> {
    const token = getAccessToken();
    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });

    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(
      `${API_BASE}/api/v1/requisitions/${requisitionId}/resumes/upload`,
      {
        method: "POST",
        headers,
        body: formData,
      }
    );

    if (!response.ok) {
      const err = await response.json().catch(() => ({ message: "Upload failed" }));
      throw new Error(err.message ?? err.detail ?? `Upload failed (${response.status})`);
    }

    return response.json();
  }

  async getBatchStatus(batchId: string): Promise<UploadBatch> {
    return this.request<UploadBatch>(`/api/v1/resume-batches/${batchId}`);
  }

  async getBatchFiles(batchId: string): Promise<ResumeFile[]> {
    return this.request<ResumeFile[]>(`/api/v1/resume-batches/${batchId}/files`);
  }

  async getResumeDetail(resumeId: string): Promise<ResumeDetail> {
    return this.request<ResumeDetail>(`/api/v1/resumes/${resumeId}`);
  }

  async downloadResumeDocument(
    resumeId: string
  ): Promise<{ blob: Blob; filename: string }> {
    const token = getAccessToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_BASE}/api/v1/resumes/${resumeId}/download`, {
      headers,
    });

    if (!response.ok) {
      throw new Error(`Failed to download document: HTTP ${response.status}`);
    }

    const disposition = response.headers.get("Content-Disposition");
    let filename = "resume_document";
    if (disposition && disposition.includes("filename=")) {
      filename = disposition.split("filename=")[1].replace(/["']/g, "");
    }

    const blob = await response.blob();
    return { blob, filename };
  }

  async retryResume(resumeId: string): Promise<ResumeFile> {
    return this.request<ResumeFile>(`/api/v1/resumes/${resumeId}/retry`, {
      method: "POST",
    });
  }

  async reviewResume(
    resumeId: string,
    data: ResumeReviewRequest
  ): Promise<ResumeFile> {
    return this.request<ResumeFile>(`/api/v1/resumes/${resumeId}/review`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async listCandidates(params?: {
    page?: number;
    pageSize?: number;
    search?: string;
    requisitionId?: string;
    skill?: string;
    location?: string;
    minExperience?: number;
    maxExperience?: number;
    maxNoticeDays?: number;
    evaluationStatus?: string;
    reviewDecision?: string;
    minScore?: number;
    maxScore?: number;
    sortBy?: string;
    sortOrder?: string;
  }): Promise<CandidateListResponse> {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", params.page.toString());
    if (params?.pageSize) query.set("page_size", params.pageSize.toString());
    if (params?.search) query.set("search", params.search);
    if (params?.requisitionId) query.set("requisition_id", params.requisitionId);
    if (params?.skill) query.set("skill", params.skill);
    if (params?.location) query.set("location", params.location);
    if (params?.minExperience !== undefined) query.set("min_experience", params.minExperience.toString());
    if (params?.maxExperience !== undefined) query.set("max_experience", params.maxExperience.toString());
    if (params?.maxNoticeDays !== undefined) query.set("max_notice_days", params.maxNoticeDays.toString());
    if (params?.evaluationStatus) query.set("evaluation_status", params.evaluationStatus);
    if (params?.reviewDecision) query.set("review_decision", params.reviewDecision);
    if (params?.minScore !== undefined) query.set("min_score", params.minScore.toString());
    if (params?.maxScore !== undefined) query.set("max_score", params.maxScore.toString());
    if (params?.sortBy) query.set("sort_by", params.sortBy);
    if (params?.sortOrder) query.set("sort_order", params.sortOrder);

    const qs = query.toString();
    return this.request<CandidateListResponse>(`/api/v1/candidates${qs ? `?${qs}` : ""}`);
  }

  async getCandidateDetail(candidateId: string): Promise<CandidateDetail> {
    return this.request<CandidateDetail>(`/api/v1/candidates/${candidateId}`);
  }

  async getCandidateEvaluationHistory(
    candidateId: string
  ): Promise<CandidateEvaluationHistoryItem[]> {
    return this.request<CandidateEvaluationHistoryItem[]>(
      `/api/v1/candidates/${candidateId}/evaluations`
    );
  }

  async getCandidateNotes(candidateId: string): Promise<CandidateNoteListResponse> {
    return this.request<CandidateNoteListResponse>(
      `/api/v1/candidates/${candidateId}/notes`
    );
  }

  async createCandidateNote(
    candidateId: string,
    content: string,
    requisitionId?: string
  ): Promise<CandidateNote> {
    return this.request<CandidateNote>(`/api/v1/candidates/${candidateId}/notes`, {
      method: "POST",
      body: JSON.stringify({
        content,
        requisition_id: requisitionId || null,
      }),
    });
  }

  async updateCandidateNote(
    noteId: string,
    content: string
  ): Promise<CandidateNote> {
    return this.request<CandidateNote>(`/api/v1/candidates/notes/${noteId}`, {
      method: "PUT",
      body: JSON.stringify({ content }),
    });
  }

  async deleteCandidateNote(noteId: string): Promise<{ ok: boolean }> {
    return this.request<{ ok: boolean }>(`/api/v1/candidates/notes/${noteId}`, {
      method: "DELETE",
    });
  }

  // ── Phase 6: Recruiter Workspace & Dashboard API ──────────────────────────

  async getRecruiterDashboard(): Promise<RecruiterDashboardData> {
    return this.request<RecruiterDashboardData>("/api/v1/recruiter/dashboard");
  }

  async getRecruiterActivity(limit = 20): Promise<DashboardActivityResponse> {
    return this.request<DashboardActivityResponse>(
      `/api/v1/recruiter/activity?limit=${limit}`
    );
  }

  async getRequisitionSummary(requisitionId: string): Promise<RequisitionSummary> {
    return this.request<RequisitionSummary>(
      `/api/v1/requisitions/${requisitionId}/summary`
    );
  }

  async getRequisitionCandidates(
    requisitionId: string,
    params?: {
      page?: number;
      pageSize?: number;
      search?: string;
      skill?: string;
      location?: string;
      minExperience?: number;
      maxExperience?: number;
      maxNoticeDays?: number;
      evaluationStatus?: string;
      reviewDecision?: string;
      minScore?: number;
      maxScore?: number;
      sortBy?: string;
      sortOrder?: string;
    }
  ): Promise<CandidateListResponse> {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", params.page.toString());
    if (params?.pageSize) query.set("page_size", params.pageSize.toString());
    if (params?.search) query.set("search", params.search);
    if (params?.skill) query.set("skill", params.skill);
    if (params?.location) query.set("location", params.location);
    if (params?.minExperience !== undefined) query.set("min_experience", params.minExperience.toString());
    if (params?.maxExperience !== undefined) query.set("max_experience", params.maxExperience.toString());
    if (params?.maxNoticeDays !== undefined) query.set("max_notice_days", params.maxNoticeDays.toString());
    if (params?.evaluationStatus) query.set("evaluation_status", params.evaluationStatus);
    if (params?.reviewDecision) query.set("review_decision", params.reviewDecision);
    if (params?.minScore !== undefined) query.set("min_score", params.minScore.toString());
    if (params?.maxScore !== undefined) query.set("max_score", params.maxScore.toString());
    if (params?.sortBy) query.set("sort_by", params.sortBy);
    if (params?.sortOrder) query.set("sort_order", params.sortOrder);

    const qs = query.toString();
    return this.request<CandidateListResponse>(
      `/api/v1/requisitions/${requisitionId}/candidates${qs ? `?${qs}` : ""}`
    );
  }

  // ── Phase 5: Candidate Evaluation & Deterministic Ranking API ────────────

  async startBatchEvaluation(
    requisitionId: string,
    candidateIds?: string[]
  ): Promise<EvaluationRunResponse> {
    return this.request<EvaluationRunResponse>(
      `/api/v1/requisitions/${requisitionId}/evaluations`,
      {
        method: "POST",
        body: JSON.stringify(candidateIds ? { candidate_ids: candidateIds } : {}),
      }
    );
  }

  async evaluateSingleCandidate(
    requisitionId: string,
    candidateId: string
  ): Promise<EvaluationResponse> {
    return this.request<EvaluationResponse>(
      `/api/v1/requisitions/${requisitionId}/candidates/${candidateId}/evaluate`,
      {
        method: "POST",
      }
    );
  }

  async listEvaluations(
    requisitionId: string,
    params?: {
      page?: number;
      pageSize?: number;
      sortBy?: string;
      scoreMin?: number;
      scoreMax?: number;
      confidenceLevel?: string;
      reviewDecision?: string;
      missingEvidenceOnly?: boolean;
      mustHaveMatchedOnly?: boolean;
      search?: string;
    }
  ): Promise<EvaluationListResponse> {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", params.page.toString());
    if (params?.pageSize) query.set("page_size", params.pageSize.toString());
    if (params?.sortBy) query.set("sort_by", params.sortBy);
    if (params?.scoreMin !== undefined) query.set("score_min", params.scoreMin.toString());
    if (params?.scoreMax !== undefined) query.set("score_max", params.scoreMax.toString());
    if (params?.confidenceLevel) query.set("confidence_level", params.confidenceLevel);
    if (params?.reviewDecision) query.set("review_decision", params.reviewDecision);
    if (params?.missingEvidenceOnly) query.set("missing_evidence_only", "true");
    if (params?.mustHaveMatchedOnly) query.set("must_have_matched_only", "true");
    if (params?.search) query.set("search", params.search);

    const qs = query.toString();
    return this.request<EvaluationListResponse>(
      `/api/v1/requisitions/${requisitionId}/evaluations${qs ? `?${qs}` : ""}`
    );
  }

  async getEvaluation(evaluationId: string): Promise<EvaluationResponse> {
    return this.request<EvaluationResponse>(`/api/v1/evaluations/${evaluationId}`);
  }

  async getEvaluationEvidence(evaluationId: string): Promise<CriterionEvidenceResponse[]> {
    return this.request<CriterionEvidenceResponse[]>(
      `/api/v1/evaluations/${evaluationId}/evidence`
    );
  }

  async getEvaluationRun(
    requisitionId: string,
    runId: string
  ): Promise<EvaluationRunResponse> {
    return this.request<EvaluationRunResponse>(
      `/api/v1/requisitions/${requisitionId}/evaluation-runs/${runId}`
    );
  }

  async submitRecruiterReview(
    evaluationId: string,
    data: RecruiterReviewCreateRequest
  ): Promise<RecruiterReviewResponse> {
    return this.request<RecruiterReviewResponse>(
      `/api/v1/evaluations/${evaluationId}/review`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async recalculateEvaluation(evaluationId: string): Promise<EvaluationResponse> {
    return this.request<EvaluationResponse>(
      `/api/v1/evaluations/${evaluationId}/recalculate`,
      {
        method: "POST",
      }
    );
  }

  // ── Phase 7: Client Portal & Hiring Pipeline Methods ──────────────────────

  async getClientDashboard(): Promise<ClientDashboardMetrics> {
    return this.request<ClientDashboardMetrics>("/api/v1/client/dashboard");
  }

  async getClientRequisitions(): Promise<ClientRequisitionListItem[]> {
    return this.request<ClientRequisitionListItem[]>("/api/v1/client/requisitions");
  }

  async getClientRequisition(id: string): Promise<ClientRequisitionDetail> {
    return this.request<ClientRequisitionDetail>(`/api/v1/client/requisitions/${id}`);
  }

  async getClientSubmissions(params?: {
    requisition_id?: string;
    stage?: string;
  }): Promise<ClientSubmissionListItem[]> {
    const searchParams = new URLSearchParams();
    if (params?.requisition_id) searchParams.set("requisition_id", params.requisition_id);
    if (params?.stage) searchParams.set("stage", params.stage);
    const qs = searchParams.toString();
    return this.request<ClientSubmissionListItem[]>(`/api/v1/client/submissions${qs ? `?${qs}` : ""}`);
  }

  async getClientSubmission(id: string): Promise<MaskedCandidateProfile> {
    return this.request<MaskedCandidateProfile>(`/api/v1/client/submissions/${id}`);
  }

  async submitClientDecision(
    submissionId: string,
    data: {
      decision: string;
      reason_note?: string;
      interview_details?: string;
      info_request_details?: string;
    }
  ): Promise<MaskedCandidateProfile> {
    return this.request<MaskedCandidateProfile>(
      `/api/v1/client/submissions/${submissionId}/decisions`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async submitClientRequest(
    submissionId: string,
    data: {
      request_type: string;
      details: string;
    }
  ): Promise<ClientRequest> {
    return this.request<ClientRequest>(
      `/api/v1/client/submissions/${submissionId}/requests`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async getClientSubmissionHistory(submissionId: string): Promise<PipelineRecord[]> {
    return this.request<PipelineRecord[]>(`/api/v1/client/submissions/${submissionId}/history`);
  }

  async submitCandidateToClient(
    requisitionId: string,
    data: {
      candidate_id: string;
      client_organization_id: string;
      recruiter_notes_for_client?: string;
    }
  ): Promise<{
    submission_id: string;
    candidate_id: string;
    candidate_reference: string;
    requisition_id: string;
    client_organization_id: string;
    current_stage: string;
    submitted_at: string;
    message: string;
  }> {
    return this.request(
      `/api/v1/requisitions/${requisitionId}/submissions`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async getRecruiterSubmissions(params?: {
    requisition_id?: string;
    client_org_id?: string;
    stage?: string;
  }): Promise<RecruiterSubmissionListItem[]> {
    const searchParams = new URLSearchParams();
    if (params?.requisition_id) searchParams.set("requisition_id", params.requisition_id);
    if (params?.client_org_id) searchParams.set("client_org_id", params.client_org_id);
    if (params?.stage) searchParams.set("stage", params.stage);
    const qs = searchParams.toString();
    return this.request<RecruiterSubmissionListItem[]>(`/api/v1/recruiter/submissions${qs ? `?${qs}` : ""}`);
  }

  async getPipelineBoard(params?: {
    requisition_id?: string;
    client_org_id?: string;
  }): Promise<PipelineBoardData> {
    const searchParams = new URLSearchParams();
    if (params?.requisition_id) searchParams.set("requisition_id", params.requisition_id);
    if (params?.client_org_id) searchParams.set("client_org_id", params.client_org_id);
    const qs = searchParams.toString();
    return this.request<PipelineBoardData>(`/api/v1/recruiter/pipeline${qs ? `?${qs}` : ""}`);
  }

  async updatePipelineStage(
    submissionId: string,
    data: {
      stage: string;
      reason_note?: string;
    }
  ): Promise<{ submission_id: string; current_stage: string; message: string }> {
    return this.request(
      `/api/v1/recruiter/submissions/${submissionId}/stage`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      }
    );
  }

  async respondToClientRequest(
    requestId: string,
    data: {
      recruiter_response: string;
      new_stage?: string;
    }
  ): Promise<ClientRequest> {
    return this.request<ClientRequest>(
      `/api/v1/recruiter/requests/${requestId}/response`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async getClientOrganizations(): Promise<ClientOrgOption[]> {
    return this.request<ClientOrgOption[]>("/api/v1/recruiter/clients");
  }

  async getDeliveryPipelineSummary(): Promise<DeliveryPipelineSummary> {
    return this.request<DeliveryPipelineSummary>("/api/v1/delivery/pipeline-summary");
  }

  // ── Phase 8: Candidate Consent, Privacy & AI Governance ─────────────────────

  async createConsentRequest(
    candidateId: string,
    data: { purpose?: string; collection_method?: string; requisition_id?: string }
  ): Promise<ConsentRequestResponse> {
    return this.request<ConsentRequestResponse>(
      `/api/v1/candidates/${candidateId}/consent-requests`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async getCandidateConsent(candidateId: string): Promise<ConsentRecord[]> {
    return this.request<ConsentRecord[]>(`/api/v1/candidates/${candidateId}/consent`);
  }

  async withdrawCandidateConsent(
    candidateId: string,
    data: { reason?: string }
  ): Promise<ConsentRecord> {
    return this.request<ConsentRecord>(
      `/api/v1/candidates/${candidateId}/consent/withdraw`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async listConsentRecords(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ items: ConsentRecord[]; total: number }> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    if (params?.offset) searchParams.set("offset", params.offset.toString());
    const qs = searchParams.toString();
    return this.request(`/api/v1/consent-records${qs ? `?${qs}` : ""}`);
  }

  async getPublicConsentInfo(token: string): Promise<ConsentPublicInfo> {
    return this.request<ConsentPublicInfo>(`/api/v1/public/consent/${token}`);
  }

  async submitPublicConsentDecision(
    token: string,
    data: { decision: "GRANTED" | "DECLINED"; reason?: string }
  ): Promise<ConsentRecord> {
    return this.request<ConsentRecord>(`/api/v1/public/consent/${token}/decision`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async createDataRequest(
    candidateId: string,
    data: { request_type?: string; reason?: string }
  ): Promise<DataRequest> {
    return this.request<DataRequest>(`/api/v1/candidates/${candidateId}/data-requests`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async listDataRequests(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ items: DataRequest[]; total: number }> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    if (params?.offset) searchParams.set("offset", params.offset.toString());
    const qs = searchParams.toString();
    return this.request(`/api/v1/data-requests${qs ? `?${qs}` : ""}`);
  }

  async getDataRequest(requestId: string): Promise<DataRequest> {
    return this.request<DataRequest>(`/api/v1/data-requests/${requestId}`);
  }

  async generateDataExport(requestId: string): Promise<Record<string, unknown>> {
    return this.request(`/api/v1/data-requests/${requestId}/export`, {
      method: "POST",
    });
  }

  async downloadDataExport(requestId: string): Promise<Blob> {
    const token = getAccessToken();
    const res = await fetch(`${API_BASE}/api/v1/data-exports/${requestId}`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) {
      throw new Error(`Download failed with status ${res.status}`);
    }
    return res.blob();
  }

  async createDeletionRequest(
    candidateId: string,
    data: { reason?: string }
  ): Promise<DeletionRequest> {
    return this.request<DeletionRequest>(
      `/api/v1/candidates/${candidateId}/deletion-requests`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async listDeletionRequests(params?: {
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ items: DeletionRequest[]; total: number }> {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set("status", params.status);
    if (params?.limit) searchParams.set("limit", params.limit.toString());
    if (params?.offset) searchParams.set("offset", params.offset.toString());
    const qs = searchParams.toString();
    return this.request(`/api/v1/deletion-requests${qs ? `?${qs}` : ""}`);
  }

  async getDeletionRequest(requestId: string): Promise<DeletionRequest> {
    return this.request<DeletionRequest>(`/api/v1/deletion-requests/${requestId}`);
  }

  async reviewDeletionRequest(
    requestId: string,
    data: {
      decision: "APPROVE" | "REJECT" | "HOLD";
      review_notes?: string;
      retention_policy_notes?: string;
      is_legal_hold?: boolean;
      legal_hold_reason?: string;
    }
  ): Promise<DeletionRequest> {
    return this.request<DeletionRequest>(
      `/api/v1/deletion-requests/${requestId}/review`,
      {
        method: "POST",
        body: JSON.stringify(data),
      }
    );
  }

  async executeDeletion(
    requestId: string
  ): Promise<{ deletion_request_id: string; candidate_id: string; status: string; files_deleted_count: number; message: string }> {
    return this.request(
      `/api/v1/deletion-requests/${requestId}/execute`,
      {
        method: "POST",
      }
    );
  }

  async listAuditEvents(params?: {
    event_type?: string;
    resource_type?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }): Promise<AuditLogListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.event_type) searchParams.set("event_type", params.event_type);
    if (params?.resource_type) searchParams.set("resource_type", params.resource_type);
    if (params?.date_from) searchParams.set("date_from", params.date_from);
    if (params?.date_to) searchParams.set("date_to", params.date_to);
    if (params?.page) searchParams.set("page", params.page.toString());
    if (params?.page_size) searchParams.set("page_size", params.page_size.toString());
    const qs = searchParams.toString();
    return this.request<AuditLogListResponse>(`/api/v1/audit-events${qs ? `?${qs}` : ""}`);
  }

  async getAuditEvent(eventId: string): Promise<AuditEvent> {
    return this.request<AuditEvent>(`/api/v1/audit-events/${eventId}`);
  }

  async getGovernanceAIMetrics(): Promise<GovernanceAIMetrics> {
    return this.request<GovernanceAIMetrics>("/api/v1/governance/ai-metrics");
  }

  async getEvaluationQuality(): Promise<EvaluationQuality> {
    return this.request<EvaluationQuality>("/api/v1/governance/evaluation-quality");
  }

  async getPrivacyDashboardStats(): Promise<PrivacyDashboardStats> {
    return this.request<PrivacyDashboardStats>("/api/v1/privacy/dashboard");
  }
}

export const api = new ApiClient();
