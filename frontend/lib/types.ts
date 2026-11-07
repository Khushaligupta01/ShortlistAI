export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  display_name: string | null;
  role: "recruiter" | "client_hiring_manager" | "delivery_head";
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
