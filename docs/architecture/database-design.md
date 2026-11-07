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
| id | UUID | PK |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| created_by | UUID | NOT NULL, FK → users(id) |
| title | VARCHAR(255) | NOT NULL |
| job_description | TEXT | NOT NULL |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft', CHECK IN ('draft', 'active', 'archived') |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| version | INTEGER | NOT NULL, DEFAULT 1 (optimistic lock) |

**Indexes**: INDEX(organization_id), INDEX(status), INDEX(organization_id, status)

---

### scorecards

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| requisition_id | UUID | NOT NULL, FK → requisitions(id) |
| version_number | INTEGER | NOT NULL |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'draft', CHECK IN ('draft', 'active', 'superseded') |
| total_weight | INTEGER | CHECK total_weight = 100 when status = 'active' |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| activated_at | TIMESTAMPTZ | |
| jd_extraction_json | JSONB | (raw JD extraction result stored for audit) |

**Indexes**: UNIQUE(requisition_id, version_number), INDEX(requisition_id, status)

---

### scorecard_criteria

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| scorecard_id | UUID | NOT NULL, FK → scorecards(id) |
| criterion_type | VARCHAR(30) | NOT NULL, CHECK IN ('experience', 'must_have_skill', 'nice_to_have_skill', 'notice_period', 'location') |
| label | VARCHAR(255) | NOT NULL |
| weight | INTEGER | NOT NULL, CHECK weight BETWEEN 1 AND 97 |
| display_order | INTEGER | NOT NULL, DEFAULT 0 |
| config_json | JSONB | (skill name, experience range, location value, etc.) |

**Indexes**: INDEX(scorecard_id), UNIQUE(scorecard_id, criterion_type, label) — prevents duplicate criteria

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
| parsed_profile_json | JSONB | (full extracted profile including protected attrs; Recruiter display only) |
| is_anonymized | BOOLEAN | NOT NULL, DEFAULT false |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| updated_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(organization_id), INDEX(organization_id, email) — supports duplicate detection

---

### resumes

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| candidate_id | UUID | NOT NULL, FK → candidates(id) |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| file_name | VARCHAR(255) | NOT NULL (original name, for display only) |
| storage_path | VARCHAR(500) | NOT NULL (UUID-based storage key) |
| file_hash | VARCHAR(64) | (SHA-256 of content, for dedup) |
| mime_type | VARCHAR(100) | NOT NULL |
| file_size_bytes | INTEGER | NOT NULL |
| raw_text | TEXT | (extracted text; retained for re-extraction) |
| parse_status | VARCHAR(20) | NOT NULL, DEFAULT 'pending', CHECK IN ('pending', 'processing', 'parsed', 'failed') |
| parse_error | TEXT | |
| upload_batch_id | UUID | FK → upload_batches(id) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(candidate_id), INDEX(upload_batch_id), INDEX(file_hash)

---

### upload_batches

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| organization_id | UUID | NOT NULL, FK → organizations(id) |
| recruiter_id | UUID | NOT NULL, FK → users(id) |
| requisition_id | UUID | NOT NULL, FK → requisitions(id) |
| total_files | INTEGER | NOT NULL |
| processed | INTEGER | NOT NULL, DEFAULT 0 |
| failed | INTEGER | NOT NULL, DEFAULT 0 |
| duplicates | INTEGER | NOT NULL, DEFAULT 0 |
| status | VARCHAR(20) | NOT NULL, DEFAULT 'processing', CHECK IN ('processing', 'completed', 'partially_failed') |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |
| completed_at | TIMESTAMPTZ | |

**Indexes**: INDEX(organization_id), INDEX(recruiter_id)

---

### evaluations

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| candidate_id | UUID | NOT NULL, FK → candidates(id) |
| requisition_id | UUID | NOT NULL, FK → requisitions(id) |
| scorecard_id | UUID | NOT NULL, FK → scorecards(id) (version reference) |
| total_score | NUMERIC(5,2) | NOT NULL, CHECK total_score BETWEEN 0 AND 100 |
| version_number | INTEGER | NOT NULL, DEFAULT 1 |
| is_current | BOOLEAN | NOT NULL, DEFAULT true |
| score_breakdown_json | JSONB | NOT NULL (per-criterion awarded points, flags, status) |
| created_at | TIMESTAMPTZ | NOT NULL, DEFAULT now() |

**Indexes**: INDEX(candidate_id), INDEX(requisition_id), INDEX(candidate_id, requisition_id), INDEX(candidate_id, is_current)

**Note**: When an evidence override triggers a re-score, `is_current = false` is set on the old record and a new record is inserted with `is_current = true`. Old records are never deleted.

---

### evaluation_evidence

| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | PK |
| evaluation_id | UUID | NOT NULL, FK → evaluations(id) |
| scorecard_criterion_id | UUID | NOT NULL, FK → scorecard_criteria(id) |
| evidence_status | VARCHAR(30) | NOT NULL, CHECK IN ('matched', 'not_matched', 'unknown', 'insufficient_evidence') |
| confidence_score | NUMERIC(4,3) | NOT NULL, CHECK BETWEEN 0.0 AND 1.0 |
| source_excerpts_json | JSONB | NOT NULL (array of verified excerpt strings) |
| flags_json | JSONB | NOT NULL ({low_confidence: bool, conflict: bool}) |
| is_overridden | BOOLEAN | NOT NULL, DEFAULT false |
| override_reason | TEXT | |
| overridden_by | UUID | FK → users(id) |
| overridden_at | TIMESTAMPTZ | |

**Indexes**: INDEX(evaluation_id), INDEX(scorecard_criterion_id)

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
candidates ──< evaluations ──< evaluation_evidence
scorecard_criteria ──< evaluation_evidence
candidates ──< submissions ──< pipeline_records
evaluations ──< submissions
organizations ──< upload_batches ──< resumes
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
| resumes | file_hash for content dedup |
| evaluations | (candidate_id, requisition_id), (candidate_id, is_current) |
| submissions | (client_organization_id, status) for client portal |
| audit_logs | (created_at), (event_type), (resource_type, resource_id) |
