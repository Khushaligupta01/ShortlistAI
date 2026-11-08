# Database Design — ShortlistAI

## Design Principles

1. **Tenant isolation at query layer**: Every table with user-facing data includes `organization_id`. All queries filter by `org_id`.
2. **Referential integrity**: All relationships enforced with foreign key constraints.
3. **Immutable audit log**: Application DB user has INSERT-only on `audit_logs`.
4. **Versioned records**: Scorecards and Evaluations are versioned; prior versions are never deleted.
5. **Protected attributes stored separately from scoring inputs**: PII and protected attrs stored in `candidates.parsed_profile_json` only; never in `evaluations` or `evaluation_evidence`.
6. **JSONB for flexible schemas**: Extracted profiles, scoring breakdowns, and evidence payloads use JSONB to avoid schema churn as AI output evolves.

---

## Tables

### users

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| email | VARCHAR(255) | NOT NULL, UNIQUE |
| password_hash | VARCHAR(255) | NOT NULL |
| display_name | VARCHAR(100) | |
| is_active | BOOLEAN | NOT NULL, DEFAULT true |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| version | INTEGER | NOT NULL, DEFAULT 1 (optimistic lock) |

**Indexes**: UNIQUE(email)

---

### organizations

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| name | VARCHAR(255) | NOT NULL |
| org_type | VARCHAR(20) | NOT NULL, CHECK IN ('staffing_firm', 'client_company') |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

---

### organization_memberships

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| user_id | UUID | NOT NULL, FK → users(id) |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| role | VARCHAR(30) | NOT NULL, CHECK IN ('recruiter', 'client_hiring_manager', 'delivery_head') |
| is_active | BOOLEAN | NOT NULL, DEFAULT true |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: UNIQUE(user_id, organization_id), INDEX(user_id), INDEX(organization_id)

---

### requisitions

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| created_by | UUID | NOT NULL, FK → users(id) |
| title | VARCHAR(255) | NOT NULL |
| location | VARCHAR(255) | NULL (Phase 3) |
| description | TEXT | NOT NULL |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft', CHECK IN ('draft', 'active', 'paused', 'closed', 'archived') |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| version | INTEGER | NOT NULL, DEFAULT 1 (optimistic lock) |

**Indexes**: INDEX(organization_id), INDEX(status), INDEX(organization_id, status)

---

### scorecards

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| requisition_id | UUID | NOT NULL, FK → requisitions(id) |
| version_number | INTEGER | NOT NULL |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft', CHECK IN ('draft', 'active', 'approved', 'superseded') |
| total_weight | INTEGER | CHECK total_weight = 100 when status = 'active' or 'approved' |
| experience_min | INTEGER | NULL (Phase 3) |
| experience_max | INTEGER | NULL (Phase 3) |
| location | VARCHAR(255) | NULL (Phase 3) |
| max_notice_days | INTEGER | NULL (Phase 3) |
| scoring_config | JSONB | NOT NULL, DEFAULT '{}' (scoring weights: experience, must_have, etc.) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| activated_at | TIMESTAMPTZ | |
| approved_at | TIMESTAMPTZ | NULL (Phase 3) |
| jd_extraction_json | JSONB | (raw JD extraction result stored for audit) |

**Indexes**: UNIQUE(requisition_id, version_number), INDEX(requisition_id, status)

---

### scorecard_criteria

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| scorecard_id | UUID | NOT NULL, FK → scorecards(id) ON DELETE CASCADE |
| criterion_type | VARCHAR(30) | NOT NULL, CHECK IN ('experience', 'must_have_skill', 'nice_to_have_skill', 'notice_period', 'location') |
| label | VARCHAR(255) | NOT NULL |
| criterion_name | VARCHAR(255) | NULL (Phase 3) |
| normalized_name | VARCHAR(255) | NULL (Phase 3) |
| description | TEXT | NULL (Phase 3) |
| weight | INTEGER | NOT NULL, CHECK weight >= 0 |
| is_mandatory | BOOLEAN | NOT NULL, DEFAULT false (Phase 3) |
| evidence_from_jd | TEXT | NULL (Phase 3) |
| display_order | INTEGER | NOT NULL, DEFAULT 0 |
| config_json | JSONB | (skill name, experience range, location value, etc.) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(scorecard_id), INDEX(scorecard_id, criterion_type)

---

### candidates

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| full_name | VARCHAR(255) | (display only — not used in scoring) |
| email | VARCHAR(255) | |
| phone | VARCHAR(50) | |
| location | VARCHAR(255) | |
| notice_period_days | INTEGER | |
| total_experience_years | NUMERIC(4,1) | NULL (Phase 4 — parsed total experience) |
| certifications | JSONB | NOT NULL, DEFAULT '[]' (Phase 4) |
| parsed_profile_json | JSONB | (full extracted profile including protected attrs; Recruiter display only) |
| is_anonymized | BOOLEAN | NOT NULL, DEFAULT false |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(organization_id), INDEX(organization_id, email) — supports duplicate detection

---

### candidate_employments (Phase 4)

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| candidate_id | UUID | NOT NULL, FK → candidates(id) ON DELETE CASCADE |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| company | VARCHAR(255) | NOT NULL |
| job_title | VARCHAR(255) | NOT NULL |
| start_date | VARCHAR(50) | NULL |
| end_date | VARCHAR(50) | NULL |
| description | TEXT | NULL |
| technologies | JSONB | NOT NULL, DEFAULT '[]' |
| is_current | BOOLEAN | NOT NULL, DEFAULT false |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(candidate_id), INDEX(organization_id)

---

### candidate_educations (Phase 4)

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| candidate_id | UUID | NOT NULL, FK → candidates(id) ON DELETE CASCADE |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| institution | VARCHAR(255) | NOT NULL |
| qualification | VARCHAR(255) | NULL |
| field_of_study | VARCHAR(255) | NULL |
| graduation_year | INTEGER | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(candidate_id), INDEX(organization_id)

---

### candidate_skills (Phase 4)

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| candidate_id | UUID | NOT NULL, FK → candidates(id) ON DELETE CASCADE |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| raw_name | VARCHAR(255) | NOT NULL |
| normalized_name | VARCHAR(255) | NOT NULL |
| evidence | TEXT | NULL |
| related_employment_id | UUID | FK → candidate_employments(id) ON DELETE SET NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(candidate_id), INDEX(organization_id), INDEX(normalized_name)

---

### resumes

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| candidate_id | UUID | NULL (Phase 4), FK → candidates(id) |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| requisition_id | UUID | NULL (Phase 4), FK → requisitions(id) |
| file_name | VARCHAR(255) | NOT NULL (original name, for display only) |
| storage_path | VARCHAR(500) | NOT NULL (UUID-based storage key) |
| file_hash | VARCHAR(64) | (SHA-256 of content, for dedup) |
| mime_type | VARCHAR(100) | NOT NULL |
| file_size_bytes | INTEGER | NOT NULL |
| raw_text | TEXT | (extracted text; retained for re-extraction) |
| extracted_text | TEXT | (Phase 4 extracted text) |
| normalized_text | TEXT | (Phase 4 normalized text) |
| parse_status | VARCHAR(20) | NOT NULL, DEFAULT 'pending', CHECK IN ('pending', 'processing', 'parsed', 'failed') |
| extraction_status | VARCHAR(50) | NOT NULL, DEFAULT 'PENDING' (Phase 4) |
| error_code | VARCHAR(100) | NULL (Phase 4) |
| error_message_safe | TEXT | NULL (Phase 4 safe sanitized message) |
| parse_error | TEXT | |
| upload_batch_id | UUID | FK → upload_batches(id) |
| duplicate_of_id | UUID | FK → resumes(id) NULL (Phase 4) |
| recruiter_notes | TEXT | NULL (Phase 4) |
| uploaded_by | UUID | NULL (Phase 4), FK → users(id) |
| uploaded_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| processed_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(candidate_id), INDEX(upload_batch_id), INDEX(file_hash), INDEX(organization_id)

---

### upload_batches

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| recruiter_id | UUID | NOT NULL, FK → users(id) |
| requisition_id | UUID | NOT NULL, FK → requisitions(id) |
| total_files | INTEGER | NOT NULL |
| accepted_files | INTEGER | NOT NULL, DEFAULT 0 (Phase 4) |
| rejected_files | INTEGER | NOT NULL, DEFAULT 0 (Phase 4) |
| duplicate_files | INTEGER | NOT NULL, DEFAULT 0 (Phase 4) |
| processing_files | INTEGER | NOT NULL, DEFAULT 0 (Phase 4) |
| completed_files | INTEGER | NOT NULL, DEFAULT 0 (Phase 4) |
| failed_files | INTEGER | NOT NULL, DEFAULT 0 (Phase 4) |
| processed | INTEGER | NOT NULL, DEFAULT 0 |
| failed | INTEGER | NOT NULL, DEFAULT 0 |
| duplicates | INTEGER | NOT NULL, DEFAULT 0 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'processing', CHECK IN ('processing', 'completed', 'partially_failed') |
| error_summary | JSONB | NULL (Phase 4) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| completed_at | TIMESTAMPTZ | |

**Indexes**: INDEX(organization_id), INDEX(recruiter_id), INDEX(requisition_id)

---

### resume_processing_jobs (Phase 4)

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK, DEFAULT gen_random_uuid() |
| resume_id | UUID | NOT NULL, FK → resumes(id) ON DELETE CASCADE |
| batch_id | UUID | NOT NULL, FK → upload_batches(id) ON DELETE CASCADE |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| status | VARCHAR(50) | NOT NULL, DEFAULT 'PENDING', CHECK IN ('PENDING', 'CLAIMED', 'PROCESSING', 'COMPLETED', 'FAILED', 'RETRY_SCHEDULED') |
| attempt_count | INTEGER | NOT NULL, DEFAULT 0 |
| max_attempts | INTEGER | NOT NULL, DEFAULT 3 |
| worker_id | VARCHAR(255) | NULL (worker instance claiming job) |
| last_error_code | VARCHAR(100) | NULL |
| last_error_message | TEXT | NULL |
| claimed_at | TIMESTAMPTZ | NULL |
| started_at | TIMESTAMPTZ | NULL |
| completed_at | TIMESTAMPTZ | NULL |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(status), INDEX(batch_id), INDEX(resume_id), INDEX(claimed_at)

---

### evaluations

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| candidate_id | UUID | NOT NULL, FK → candidates(id) |
| requisition_id | UUID | NOT NULL, FK → requisitions(id) |
| scorecard_id | UUID | NOT NULL, FK → scorecards(id) (version reference) |
| organization_id | UUID | NULLABLE, FK → organizations(id) |
| total_score | NUMERIC(5,2) | NOT NULL, CHECK total_score BETWEEN 0 AND 100 |
| raw_score | NUMERIC(5,2) | NOT NULL, DEFAULT 0.0 |
| normalized_score | NUMERIC(5,2) | NOT NULL, DEFAULT 0.0 |
| evidence_coverage | NUMERIC(5,2) | NOT NULL, DEFAULT 0.0 |
| confidence_level | VARCHAR(20) | NOT NULL, DEFAULT 'HIGH' |
| evaluation_status | VARCHAR(20) | NOT NULL, DEFAULT 'COMPLETED' |
| version_number | INTEGER | NOT NULL, DEFAULT 1 |
| scorecard_version | INTEGER | NOT NULL, DEFAULT 1 |
| is_current | BOOLEAN | NOT NULL, DEFAULT true |
| evaluation_run_id | UUID | NULLABLE, FK → evaluation_runs(id) |
| score_breakdown_json | JSONB | NOT NULL (per-criterion awarded points, flags, status) |
| model_provider | VARCHAR(50) | NULLABLE |
| model_name | VARCHAR(100) | NULLABLE |
| evaluated_at | TIMESTAMPTZ | NULLABLE |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(candidate_id), INDEX(requisition_id), INDEX(organization_id), INDEX(candidate_id, requisition_id), INDEX(candidate_id, is_current), INDEX(normalized_score), INDEX(confidence_level)

**Note**: When an evidence override triggers a re-score, `is_current = false` is set on the old record and a new record is inserted with `is_current = true`. Old records are never deleted.

---

### evaluation_evidence

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| evaluation_id | UUID | NOT NULL, FK → evaluations(id) |
| scorecard_criterion_id | UUID | NOT NULL, FK → scorecard_criteria(id) |
| evidence_status | VARCHAR(30) | NOT NULL, CHECK IN ('MATCHED', 'PARTIAL', 'NOT_MATCHED', 'UNKNOWN', 'CONFLICTING') |
| confidence_score | NUMERIC(4,3) | NOT NULL, CHECK BETWEEN 0.0 AND 1.0 |
| awarded_points | NUMERIC(5,2) | NOT NULL, DEFAULT 0.0 |
| maximum_points | NUMERIC(5,2) | NOT NULL, DEFAULT 0.0 |
| evidence_text | TEXT | NULLABLE (verbatim quote from resume) |
| source_reference | VARCHAR(255) | NULLABLE (page/section in resume) |
| explanation | TEXT | NULLABLE (explanation of uncertainty) |
| source_excerpts_json | JSONB | NOT NULL (array of verified excerpt strings) |
| flags_json | JSONB | NOT NULL ({low_confidence: bool, conflict: bool}) |
| is_overridden | BOOLEAN | NOT NULL, DEFAULT false |
| override_reason | TEXT | |
| overridden_by | UUID | FK → users(id) |
| overridden_at | TIMESTAMPTZ | |

**Indexes**: INDEX(evaluation_id), INDEX(scorecard_criterion_id), INDEX(evidence_status)

---

### evaluation_runs

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| requisition_id | UUID | NOT NULL, FK → requisitions(id) |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| initiated_by | UUID | NOT NULL, FK → users(id) |
| total_candidates | INTEGER | NOT NULL, DEFAULT 0 |
| completed_count | INTEGER | NOT NULL, DEFAULT 0 |
| failed_count | INTEGER | NOT NULL, DEFAULT 0 |
| status | VARCHAR(30) | NOT NULL, DEFAULT 'PENDING' ('PENDING', 'PROCESSING', 'COMPLETED', 'PARTIALLY_FAILED', 'FAILED') |
| started_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| completed_at | TIMESTAMPTZ | NULLABLE |
| error_summary | JSONB | NULLABLE |

**Indexes**: INDEX(requisition_id), INDEX(organization_id), INDEX(status)

---

### recruiter_reviews

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| evaluation_id | UUID | NOT NULL, FK → evaluations(id) |
| recruiter_id | UUID | NOT NULL, FK → users(id) |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| decision | VARCHAR(30) | NOT NULL ('SHORTLIST', 'REJECT', 'HOLD', 'REQUEST_INFO') |
| notes | TEXT | NULLABLE |
| reviewed_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(evaluation_id), INDEX(recruiter_id), INDEX(decision)

---

### submissions

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| candidate_id | UUID | NOT NULL, FK → candidates(id) |
| requisition_id | UUID | NOT NULL, FK → requisitions(id) |
| evaluation_id | UUID | NOT NULL, FK → evaluations(id) |
| submitted_by | UUID | NOT NULL, FK → users(id) |
| source_organization_id | UUID | NOT NULL, FK → organizations(id) (staffing firm org) |
| client_organization_id | UUID | NOT NULL, FK → organizations(id) (client org) |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'active', CHECK IN ('active', 'withdrawn') |
| submitted_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| withdrawn_at | TIMESTAMPTZ | |

**Indexes**: INDEX(candidate_id), INDEX(client_organization_id), INDEX(requisition_id), INDEX(client_organization_id, status)

---

### pipeline_records

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| submission_id | UUID | NOT NULL, FK → submissions(id) |
| current_stage | VARCHAR(30) | NOT NULL |
| previous_stage | VARCHAR(30) | |
| changed_by | UUID | NOT NULL, FK → users(id) |
| reason_note | TEXT | NOT NULL when previous_stage IS NOT NULL (required for all reversions) |
| changed_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| is_reopened | BOOLEAN | NOT NULL, DEFAULT false |

**Valid stages**: `submitted`, `shortlisted_by_client`, `interview_requested`, `offer_extended`, `placed`, `rejected`

**Indexes**: INDEX(submission_id), INDEX(changed_at)

---

### audit_logs

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| organization_id | UUID | FK → organizations(id) |
| actor_user_id | UUID | FK → users(id) |
| event_type | VARCHAR(100) | NOT NULL |
| resource_type | VARCHAR(100) | |
| resource_id | UUID | |
| payload_json | JSONB | (old+new values for update events; operation details for others) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(organization_id), INDEX(actor_user_id), INDEX(created_at), INDEX(event_type), INDEX(resource_type, resource_id)

**DB Permissions**: Application DB user granted INSERT only on this table. No UPDATE or DELETE.

---

### consent_records

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| candidate_id | UUID | NOT NULL, FK → candidates(id) |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| uploaded_by | UUID | NOT NULL, FK → users(id) |
| legal_basis | VARCHAR(100) | NOT NULL |
| privacy_notice_acknowledged | BOOLEAN | NOT NULL, DEFAULT false |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| deleted_at | TIMESTAMPTZ | (set during anonymization) |

---

## Key Relationships Summary

```
users ──< organization_memberships >── organizations
organizations ──< requisitions ──< scorecards ──< scorecard_criteria
organizations ──< candidates ──< resumes
candidates ──< candidate_employments
candidates ──< candidate_educations
candidates ──< candidate_skills
candidates ──< evaluations ──< evaluation_evidence
scorecard_criteria ──< evaluation_evidence
candidates ──< submissions ──< pipeline_records
evaluations ──< submissions
organizations ──< upload_batches ──< resumes ──< resume_processing_jobs
candidates ──< consent_records
```

---

## Migration Strategy

- Alembic manages all schema changes
- Every migration has a corresponding `downgrade()` function
- Migrations are applied before the application process starts in deployment
- Schema version tracked in `alembic_version` table
- Breaking migrations (column drops, type changes) require two-phase deployment:
  1. Deploy code that handles both old and new schema
  2. Apply migration
  3. Deploy code that uses only new schema

---

## Performance Indexes (Summary)

All tenant-scoped tables have INDEX on `organization_id`.

| Table | Additional Indexes |
|-------|-------------------|
| requisitions | (organization_id, status) composite |
| candidates | (organization_id, email) for dedup |
| candidate_employments | (candidate_id) |
| candidate_educations | (candidate_id) |
| candidate_skills | (candidate_id), (normalized_name) |
| resumes | file_hash for content dedup, (upload_batch_id) |
| resume_processing_jobs | (status), (batch_id), (resume_id), (claimed_at) |
| evaluations | (candidate_id, requisition_id), (candidate_id, is_current) |
| submissions | (client_organization_id, status) for client portal |
| audit_logs | (created_at), (event_type), (resource_type, resource_id) |
| candidates | (organization_id, email) for dedup |
| resumes | file_hash for content dedup |
| evaluations | (candidate_id, requisition_id), (candidate_id, is_current) |
| submissions | (client_organization_id, status) for client portal |
| audit_logs | (created_at), (event_type), (resource_type, resource_id) |
