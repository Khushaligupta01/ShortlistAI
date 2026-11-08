export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  display_name: string | null;
  role: "recruiter" | "client_hiring_manager" | "delivery_head" | "admin" | "super_admin";
  organization_id: string | null;
  is_active: boolean;
}

export interface ApiError {
  error_code?: string;
  message?: string;
  detail?: string;
  trace_id?: string;
}

export interface Requisition {
  id: string;
  organization_id: string;
  created_by: string;
  title: string;
  job_description: string;
  location?: string | null;
  status: "draft" | "active" | "archived";
  created_at: string;
  updated_at: string;
  version: number;
}

export interface RequisitionListResponse {
  items: Requisition[];
  total: number;
  page: number;
  page_size: number;
}

export interface Organization {
  id: string;
  name: string;
  org_type: "staffing_firm" | "client_company";
  created_at: string;
}

export interface MembershipInfo {
  organization: Organization;
  role: string;
  is_active: boolean;
}

// ── Phase 3: AI & Scorecard Types ──────────────────────────────────────────

export interface ExperienceRequirement {
  minimum_years?: number | null;
  maximum_years?: number | null;
  evidence?: string | null;
  is_explicit: boolean;
}

export interface SkillRequirement {
  name: string;
  normalized_name?: string;
  description?: string | null;
  importance?: string | null;
  evidence?: string | null;
  is_mandatory: boolean;
}

export interface NoticePeriodRequirement {
  maximum_days?: number | null;
  original_wording?: string | null;
  is_explicit: boolean;
}

export interface AdditionalRequirement {
  category: string;
  description: string;
  evidence?: string | null;
  is_mandatory: boolean;
}

export interface ExtractionWarning {
  field: string;
  message: string;
  severity: "info" | "warning" | "error";
}

export interface JDExtractionResult {
  job_title?: string | null;
  department?: string | null;
  seniority_level?: string | null;
  location?: string | null;
  work_arrangement?: string | null;
  employment_type?: string | null;
  summary?: string | null;
  experience?: ExperienceRequirement | null;
  must_have_skills: SkillRequirement[];
  nice_to_have_skills: SkillRequirement[];
  notice_period?: NoticePeriodRequirement | null;
  additional_requirements: AdditionalRequirement[];
  extraction_warnings: ExtractionWarning[];
}

export interface ScoringConfig {
  experience: number;
  must_have_skills: number;
  notice_period: number;
  location: number;
  nice_to_have_skills: number;
}

export interface ScorecardCriterion {
  id?: string;
  scorecard_id?: string;
  criterion_type: string;
  criterion_name: string;
  normalized_name?: string | null;
  label: string;
  description?: string | null;
  weight: number;
  is_mandatory: boolean;
  evidence_from_jd?: string | null;
  display_order: number;
  config_json?: Record<string, unknown> | null;
  created_at?: string;
}

export interface ScorecardResponse {
  id: string;
  requisition_id: string;
  version_number: number;
  version?: number;
  status: "draft" | "approved" | "archived";
  experience_min?: number | null;
  experience_max?: number | null;
  location?: string | null;
  max_notice_days?: number | null;
  scoring_config?: ScoringConfig | null;
  scoring_configuration?: ScoringConfig | null;
  total_weight?: number | null;
  criteria: ScorecardCriterion[];
  jd_extraction_json?: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  approved_at?: string | null;
}

export interface ScorecardCreate {
  experience_min?: number | null;
  experience_max?: number | null;
  location?: string | null;
  max_notice_days?: number | null;
  scoring_config?: ScoringConfig;
  criteria: Omit<ScorecardCriterion, "id" | "scorecard_id" | "created_at">[];
  jd_extraction_json?: Record<string, unknown> | null;
}

export interface ScorecardUpdate {
  experience_min?: number | null;
  experience_max?: number | null;
  location?: string | null;
  max_notice_days?: number | null;
  scoring_config?: ScoringConfig;
  criteria?: Omit<ScorecardCriterion, "id" | "scorecard_id" | "created_at">[];
}


// ── Phase 4: Resume Ingestion & Parsing Types ──────────────────────────────

export interface UploadBatch {
  id: string;
  requisition_id: string;
  organization_id: string;
  total_files: number;
  accepted_files: number;
  rejected_files: number;
  duplicate_files: number;
  processing_files: number;
  completed_files: number;
  failed_files: number;
  status: "processing" | "completed" | "partial_failure" | "failed";
  created_at: string;
  completed_at?: string | null;
}

export interface ResumeFile {
  id: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  parse_status: "pending" | "processing" | "parsed" | "duplicate" | "needs_review" | "failed";
  extraction_status: "pending" | "extracting" | "extracted" | "failed" | "ocr_required";
  error_code?: string | null;
  error_message_safe?: string | null;
  candidate_id?: string | null;
  candidate_name?: string | null;
  duplicate_of_id?: string | null;
  duplicate_type?: string | null;
  created_at: string;
  processed_at?: string | null;
}

export interface ResumeDetail extends ResumeFile {
  raw_text?: string | null;
  normalized_text?: string | null;
  duplicate_details?: Record<string, unknown> | null;
}

export interface CandidateSkillOut {
  id: string;
  name: string;
  raw_name: string;
  evidence?: string | null;
}

export interface CandidateEmploymentOut {
  id: string;
  company: string;
  job_title: string;
  start_date?: string | null;
  end_date?: string | null;
  is_current: boolean;
  description?: string | null;
  technologies?: string[] | null;
}

export interface CandidateEducationOut {
  id: string;
  institution: string;
  qualification?: string | null;
  field_of_study?: string | null;
  graduation_year?: number | null;
}

export interface CandidateResumeOut {
  id: string;
  file_name: string;
  mime_type: string;
  file_size_bytes: number;
  parse_status: string;
  created_at: string;
}

export interface CandidateListItem {
  id: string;
  organization_id: string;
  full_name?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  notice_period_days?: number | null;
  total_experience_years?: number | null;
  primary_job_title?: string | null;
  primary_company?: string | null;
  evaluation_score?: number | null;
  evaluation_status?: string | null;
  review_decision?: string | null;
  evidence_coverage?: number | null;
  requisition_id?: string | null;
  requisition_title?: string | null;
  skills: CandidateSkillOut[];
  created_at: string;
}

export interface CandidateDetail extends CandidateListItem {
  certifications?: Array<Record<string, unknown>> | null;
  parsed_profile_json?: {
    warnings?: string[];
    missing_fields?: string[];
    [key: string]: unknown;
  } | null;
  employments: CandidateEmploymentOut[];
  educations: CandidateEducationOut[];
  resumes: CandidateResumeOut[];
}

export interface CandidateListResponse {
  items: CandidateListItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ResumeReviewRequest {
  full_name?: string | null;
  email?: string | null;
  phone?: string | null;
  location?: string | null;
  notice_period_days?: number | null;
  skills?: string[] | null;
}

// ── Phase 5: Candidate Evaluation & Deterministic Ranking Types ──────────

export type EvaluationMatchStatus = "MATCHED" | "PARTIAL" | "NOT_MATCHED" | "UNKNOWN" | "CONFLICTING";
export type EvaluationConfidenceLevel = "HIGH" | "NEEDS_REVIEW" | "LOW";
export type RecruiterReviewDecision = "UNREVIEWED" | "SHORTLIST" | "REJECT" | "HOLD" | "REQUEST_INFO";

export interface CriterionEvidenceResponse {
  id: string;
  scorecard_criterion_id: string;
  criterion_name?: string | null;
  criterion_type?: string | null;
  evidence_status: EvaluationMatchStatus;
  confidence_score: number;
  awarded_points: number;
  maximum_points: number;
  evidence_text?: string | null;
  source_reference?: string | null;
  explanation?: string | null;
  is_overridden: boolean;
  override_reason?: string | null;
  created_at?: string | null;
}

export interface RecruiterReviewResponse {
  id: string;
  evaluation_id: string;
  recruiter_id: string;
  decision: RecruiterReviewDecision;
  notes?: string | null;
  reviewed_at: string;
}

export interface ScoreBreakdownCategory {
  awarded: number;
  max: number;
  provisional_max?: number;
  coverage?: number;
  notes?: string;
  [key: string]: unknown;
}

export interface ScoreBreakdown {
  experience?: ScoreBreakdownCategory;
  must_have_skills?: ScoreBreakdownCategory;
  notice_period?: ScoreBreakdownCategory;
  location?: ScoreBreakdownCategory;
  nice_to_have_skills?: ScoreBreakdownCategory;
  [key: string]: unknown;
}

export interface EvaluationResponse {
  id: string;
  candidate_id: string;
  candidate_name?: string | null;
  candidate_email?: string | null;
  candidate_location?: string | null;
  candidate_experience_years?: number | null;
  candidate_notice_days?: number | null;
  candidate_skills: string[];
  requisition_id: string;
  scorecard_id: string;
  scorecard_version: number;
  version_number: number;
  total_score: number;
  raw_score: number;
  normalized_score: number;
  evidence_coverage: number;
  confidence_level: EvaluationConfidenceLevel;
  evaluation_status: "COMPLETED" | "FAILED" | "PENDING";
  is_current: boolean;
  score_breakdown: ScoreBreakdown;
  evidence?: CriterionEvidenceResponse[] | null;
  reviews?: RecruiterReviewResponse[] | null;
  latest_review_decision?: RecruiterReviewDecision;
  model_provider?: string | null;
  model_name?: string | null;
  evaluated_at?: string | null;
  created_at: string;
}

export interface EvaluationListResponse {
  items: EvaluationResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface EvaluationRunResponse {
  id: string;
  requisition_id: string;
  total_candidates: number;
  completed_count: number;
  failed_count: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "PARTIALLY_FAILED" | "FAILED";
  started_at: string;
  completed_at?: string | null;
  error_summary?: {
    errors?: Array<{ candidate_id: string; error: string }>;
  } | null;
}

export interface RecruiterReviewCreateRequest {
  decision: "SHORTLIST" | "REJECT" | "HOLD" | "REQUEST_INFO";
  notes?: string | null;
}

export interface BatchEvaluationRequest {
  candidate_ids?: string[] | null;
}

// ── Phase 6: Recruiter Dashboard & Candidate Management Workspace ──────────

export interface DashboardMetrics {
  active_requisitions: number;
  total_candidates: number;
  resumes_processed: number;
  resumes_pending: number;
  failed_jobs: number;
  candidates_awaiting_review: number;
  candidates_shortlisted: number;
  completed_evaluations: number;
}

export interface RequisitionOverviewItem {
  id: string;
  title: string;
  department?: string | null;
  location?: string | null;
  status: string;
  target_hire_date?: string | null;
  candidate_count: number;
  evaluated_count: number;
  pending_reviews_count: number;
  shortlisted_count: number;
  average_score?: number | null;
  top_score?: number | null;
  created_at?: string | null;
}

export interface ProcessingOverview {
  total_uploaded: number;
  total_processed: number;
  total_pending: number;
  total_failed: number;
  success_rate_percent: number;
}

export interface DashboardActivityItem {
  id: string;
  type: string;
  title: string;
  description: string;
  timestamp: string;
  actor_name?: string | null;
  entity_id?: string | null;
  entity_type?: string | null;
}

export interface DashboardActivityResponse {
  activities: DashboardActivityItem[];
}

export interface RecruiterDashboardData {
  metrics: DashboardMetrics;
  requisitions: RequisitionOverviewItem[];
  processing: ProcessingOverview;
  recent_activity: DashboardActivityItem[];
}

export interface CandidateNote {
  id: string;
  candidate_id: string;
  requisition_id?: string | null;
  requisition_title?: string | null;
  author_id: string;
  author_name?: string | null;
  author_email?: string | null;
  organization_id: string;
  content: string;
  created_at: string;
  updated_at: string;
  is_author: boolean;
}

export interface CandidateNoteListResponse {
  notes: CandidateNote[];
  total: number;
}

export interface CandidateEvaluationHistoryItem {
  id: string;
  requisition_id: string;
  requisition_title?: string | null;
  scorecard_id: string;
  scorecard_version?: number | null;
  overall_score: number;
  confidence_score: number;
  evidence_coverage: number;
  evaluation_status: string;
  is_current: boolean;
  summary?: string | null;
  strengths: string[];
  gaps: string[];
  risks: string[];
  review_decision?: string | null;
  review_notes?: string | null;
  reviewed_at?: string | null;
  created_at: string;
}

export interface RequisitionSummary {
  id: string;
  title: string;
  status: string;
  location?: string | null;
  created_at: string;
  candidate_count: number;
  evaluated_count: number;
  pending_reviews_count: number;
  shortlisted_count: number;
  rejected_count: number;
  hold_count: number;
  average_score?: number | null;
  top_score?: number | null;
  approved_scorecard_id?: string | null;
  scorecard_version?: number | null;
}



// ── Phase 7: Client Shortlist Portal & Hiring Pipeline Types ─────────────

export interface ClientDashboardMetrics {
  active_requisitions_count: number;
  total_submissions_count: number;
  awaiting_review_count: number;
  shortlisted_count: number;
  rejected_count: number;
  interview_requested_count: number;
  additional_info_requested_count: number;
}

export interface ClientRequisitionListItem {
  id: string;
  title: string;
  location?: string | null;
  status: string;
  created_at: string;
  submissions_count: number;
  awaiting_review_count: number;
}

export interface ClientRequisitionDetail {
  id: string;
  title: string;
  job_description: string;
  location?: string | null;
  status: string;
  created_at: string;
  submissions_count: number;
}

export interface ClientSubmissionListItem {
  submission_id: string;
  candidate_id: string;
  candidate_reference: string;
  requisition_id: string;
  requisition_title: string;
  location?: string | null;
  total_experience_years?: number | null;
  overall_score?: number | null;
  skills: string[];
  current_stage: string;
  submitted_at: string;
  pending_action?: string | null;
}

export interface MaskedEmployment {
  title?: string | null;
  company?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  is_current: boolean;
  description?: string | null;
}

export interface MaskedEducation {
  degree?: string | null;
  institution?: string | null;
  field_of_study?: string | null;
  graduation_year?: number | null;
}

export interface MaskedCriterionEvidence {
  criterion_id: string;
  criterion_name: string;
  category: string;
  status: string;
  evidence_excerpt?: string | null;
  reasoning?: string | null;
}

export interface PipelineRecord {
  id: string;
  submission_id: string;
  current_stage: string;
  previous_stage?: string | null;
  changed_by: string;
  actor_name?: string | null;
  reason_note?: string | null;
  changed_at: string;
  is_reopened: boolean;
}

export interface ClientRequest {
  id: string;
  submission_id: string;
  client_organization_id: string;
  requested_by: string;
  requester_name?: string | null;
  request_type: string;
  details: string;
  status: string;
  recruiter_response?: string | null;
  responded_by?: string | null;
  responder_name?: string | null;
  responded_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MaskedCandidateProfile {
  submission_id: string;
  candidate_id: string;
  candidate_reference: string;
  requisition_id: string;
  requisition_title: string;
  current_stage: string;
  submitted_at: string;
  recruiter_notes_for_client?: string | null;
  location?: string | null;
  total_experience_years?: number | null;
  notice_period_days?: number | null;
  overall_score?: number | null;
  evaluation_summary?: string | null;
  skills: string[];
  employments: MaskedEmployment[];
  educations: MaskedEducation[];
  certifications: string[];
  criterion_evaluations: MaskedCriterionEvidence[];
  latest_decision?: string | null;
  pipeline_history: PipelineRecord[];
  requests: ClientRequest[];
}

export interface RecruiterSubmissionListItem {
  submission_id: string;
  candidate_id: string;
  candidate_name: string;
  candidate_email: string;
  candidate_reference: string;
  requisition_id: string;
  requisition_title: string;
  client_organization_id: string;
  client_organization_name: string;
  current_stage: string;
  overall_score?: number | null;
  submitted_at: string;
  last_activity_at: string;
  pending_requests_count: number;
}

export interface PipelineStageSummary {
  stage: string;
  stage_label: string;
  count: number;
}

export interface PipelineBoardData {
  stages: PipelineStageSummary[];
  submissions: RecruiterSubmissionListItem[];
}

export interface ClientOrgOption {
  id: string;
  name: string;
  org_type: string;
}

export interface DeliveryPipelineSummary {
  total_submissions: number;
  stage_breakdown: Record<string, number>;
  clients: {
    client_organization_id: string;
    client_organization_name: string;
    active_requisitions_count: number;
    total_submissions: number;
    shortlisted_count: number;
    interview_count: number;
    hired_count: number;
  }[];
  conversion_shortlist_rate: number;
  conversion_interview_rate: number;
  conversion_hire_rate: number;
}
