# API Specification — ShortlistAI

## Base URL and Versioning

All endpoints are prefixed with `/api/v1/`.  
OpenAPI docs available at `/docs` in non-production environments.

## Standard Conventions

### Response Envelope (Success)
```json
{
  "items": [...],
  "total": 142,
  "page": 1,
  "page_size": 20
}
```
Single-resource responses return the resource directly (no `items` wrapper).

### Response Envelope (Error)
```json
{
  "error_code": "VALIDATION_ERROR",
  "message": "Description of the problem",
  "trace_id": "req-abc123def456",
  "details": [
    { "field": "email", "issue": "Field is required" }
  ]
}
```

### Pagination
`?page=1&page_size=20&sort_by=created_at&sort_dir=desc`

### Timestamps
All timestamps in ISO 8601 UTC format: `2024-01-15T10:30:00Z`

---

## Authentication Endpoints

### POST /api/v1/auth/login
**Role**: Public  
**Request**:
```json
{ "email": "user@example.com", "password": "string" }
```
**Response 200**:
```json
{ "access_token": "eyJ...", "refresh_token": "opaque-token", "token_type": "bearer" }
```
**Errors**: 401 (invalid credentials, uniform message), 429 (rate limit)

---

### POST /api/v1/auth/refresh
**Role**: Public (requires valid refresh token)  
**Request**: `{ "refresh_token": "opaque-token" }`  
**Response 200**: `{ "access_token": "eyJ...", "refresh_token": "new-token" }`  
**Errors**: 401 (invalid/expired token)

---

### POST /api/v1/auth/logout
**Role**: Any authenticated  
**Request**: `{ "refresh_token": "opaque-token" }`  
**Response 204**: No content  

---

## Requisition Endpoints

### GET /api/v1/requisitions
**Role**: Recruiter, Delivery_Head  
**Query**: `?page=1&page_size=20&status=active&search=software+engineer`  
**Response 200**: Paginated list of requisitions
```json
{
  "items": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "title": "Senior Java Developer",
      "description": "...",
      "location": "Noida",
      "status": "draft",
      "created_by": "uuid",
      "created_at": "2026-11-08T00:00:00Z",
      "updated_at": "2026-11-08T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### POST /api/v1/requisitions
**Role**: Recruiter  
**Request**:
```json
{
  "title": "Senior Java Developer",
  "location": "Noida",
  "description": "5-8 years experience in Java..."
}
```
**Response 201**: Created requisition object  
**Errors**: 422 (validation error)

### GET /api/v1/requisitions/{id}
**Role**: Recruiter, Delivery_Head  
**Response 200**: Requisition detail  
**Errors**: 404 (not found or cross-org access)

### PUT /api/v1/requisitions/{id}
**Role**: Recruiter  
**Request**:
```json
{
  "title": "Senior Java Developer (Updated)",
  "location": "Noida / Remote",
  "description": "..."
}
```
**Response 200**: Updated requisition object  
**Errors**: 404 (not found)

---

## JD Extraction Endpoints

### POST /api/v1/requisitions/extract-requirements
**Role**: Recruiter  
**Rate Limit**: 10 requests / minute  
**Request**:
```json
{
  "job_description": "We are seeking a Senior Java Developer in Noida with 5-8 years of experience. Must have hands-on Java and Spring Boot. Microservices is preferred. Max notice period 60 days."
}
```
**Response 200**:
```json
{
  "job_title": "Senior Java Developer",
  "department": null,
  "seniority_level": "Senior",
  "location": "Noida",
  "work_arrangement": null,
  "employment_type": "Full-time",
  "summary": "Seeking Senior Java Developer with Spring Boot experience.",
  "experience": {
    "minimum_years": 5,
    "maximum_years": 8,
    "evidence": "5-8 years of experience",
    "is_inferred": false
  },
  "must_have_skills": [
    {
      "name": "Java",
      "normalized_name": "java",
      "description": "Java backend development",
      "importance": "high",
      "evidence": "hands-on Java",
      "is_mandatory": true
    },
    {
      "name": "Spring Boot",
      "normalized_name": "spring_boot",
      "description": "Spring Boot framework",
      "importance": "high",
      "evidence": "Spring Boot",
      "is_mandatory": true
    }
  ],
  "nice_to_have_skills": [
    {
      "name": "Microservices",
      "normalized_name": "microservices",
      "description": "Microservices architecture",
      "importance": "medium",
      "evidence": "Microservices is preferred",
      "is_mandatory": false
    }
  ],
  "notice_period": {
    "maximum_days": 60,
    "original_wording": "Max notice period 60 days",
    "is_inferred": false
  },
  "additional_requirements": [],
  "extraction_warnings": [],
  "suggested_weights": {
    "experience": 30,
    "must_have_skills": 40,
    "notice_period": 15,
    "location": 10,
    "nice_to_have_skills": 5
  }
}
```
**Errors**:
- 422: Job description too short (< 20 characters) or malformed.
- 429: AI provider rate limited or quota exhausted (with user instructions to manually fill scorecard).
- 502/503: AI provider service unavailable or timeout after retries.

---

## Scorecard Endpoints

### GET /api/v1/requisitions/{id}/scorecard
**Role**: Recruiter, Delivery_Head  
**Response 200**: Active or latest scorecard for requisition  
**Errors**: 404 (no scorecard or cross-org)

### POST /api/v1/requisitions/{id}/scorecards
**Role**: Recruiter  
**Request**:
```json
{
  "experience_min": 5,
  "experience_max": 8,
  "location": "Noida",
  "max_notice_days": 60,
  "scoring_configuration": {
    "experience": 30,
    "must_have_skills": 40,
    "notice_period": 15,
    "location": 10,
    "nice_to_have_skills": 5
  },
  "criteria": [
    {
      "criterion_type": "must_have_skill",
      "criterion_name": "Java",
      "normalized_name": "java",
      "description": "Core Java",
      "weight": 20,
      "is_mandatory": true,
      "evidence_from_jd": "hands-on Java"
    }
  ]
}
```
**Response 201**: Created scorecard in `draft` status.  
**Errors**: 400 (scoring weights do not sum to 100 or negative).

### PUT /api/v1/requisitions/{id}/scorecard
**Role**: Recruiter  
**Request**: Updated scorecard fields and criteria list.  
**Response 200**: Updated draft scorecard.  
**Errors**:
- 400: Weights do not sum to 100.
- 409: Scorecard is already approved (immutable lock).

### POST /api/v1/requisitions/{id}/scorecard/approve
**Role**: Recruiter  
**Request**: `{}`  
**Response 200**:
```json
{
  "id": "uuid",
  "status": "approved",
  "version": 1,
  "approved_at": "2026-11-08T00:00:00Z"
}
```
**Behavior**: Sets scorecard status to `approved`, stamps `approved_at`, activates requisition status to `active`, and logs `SCORECARD_APPROVED` audit event.

### POST /api/v1/requisitions/{id}/scorecard/duplicate
**Role**: Recruiter  
**Request**: `{}`  
**Response 201**: Clones latest approved scorecard into a new draft scorecard with incremented version (`version: 2`), allowing revisions while preserving historical approved scorecard.

---

## Resume Upload & Ingestion Endpoints (Phase 4)

### POST /api/v1/requisitions/{id}/resumes/upload
**Role**: Recruiter  
**Content-Type**: `multipart/form-data`  
**Body**: Form `files` array (PDF/DOCX, up to 500 files per batch, 15MB/file, 250MB total)  
**Response 202**:
```json
{
  "id": "uuid",
  "requisition_id": "uuid",
  "status": "processing",
  "total_files": 14,
  "accepted_files": 13,
  "rejected_files": 1,
  "duplicate_files": 1,
  "processing_files": 12,
  "completed_files": 0,
  "failed_files": 0,
  "error_summary": {
    "rejected": [{ "filename": "invalid.exe", "reason": "Unsupported format" }]
  },
  "created_at": "2026-11-08T00:00:00Z"
}
```
**Errors**: 400 (no files or batch limits exceeded), 404 (requisition not found)

### GET /api/v1/resumes/batches/{batch_id}
**Role**: Recruiter, Delivery_Head  
**Response 200**: Real-time batch counter summary:
```json
{
  "id": "uuid",
  "requisition_id": "uuid",
  "status": "processing",
  "total_files": 14,
  "accepted_files": 13,
  "rejected_files": 1,
  "duplicate_files": 1,
  "processing_files": 2,
  "completed_files": 10,
  "failed_files": 1,
  "created_at": "2026-11-08T00:00:00Z",
  "completed_at": null
}
```

### GET /api/v1/resumes/batches/{batch_id}/files
**Role**: Recruiter, Delivery_Head  
**Response 200**: List of all files tracked within the upload batch:
```json
[
  {
    "id": "uuid",
    "file_name": "01_strong_java_senior.pdf",
    "mime_type": "application/pdf",
    "file_size_bytes": 125000,
    "parse_status": "parsed",
    "extraction_status": "COMPLETED",
    "candidate_id": "uuid",
    "candidate_name": "Alex Mercer",
    "candidate_email": "alex.mercer@example.com",
    "error_code": null,
    "error_message_safe": null,
    "duplicate_of_id": null,
    "uploaded_at": "2026-11-08T00:00:00Z"
  }
]
```

### GET /api/v1/resumes/{resume_id}
**Role**: Recruiter, Delivery_Head  
**Response 200**: Detailed resume metadata, extraction results, recruiter notes, and links.  
**Errors**: 404 (not found or cross-org access)

### GET /api/v1/resumes/{resume_id}/document
**Role**: Recruiter, Delivery_Head  
**Response 200**: Streaming binary file response (`application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document`) with `Content-Disposition: attachment; filename="..."`.  
**Errors**: 403 (unauthorized role), 404 (not found / cross-org), 410 (file missing from storage)

### POST /api/v1/resumes/{resume_id}/retry
**Role**: Recruiter  
**Response 200**:
```json
{ "status": "RETRY_SCHEDULED", "message": "Resume processing job re-enqueued" }
```
**Errors**: 400 (resume not in failed status), 404 (not found)

### PUT /api/v1/resumes/{resume_id}/review
**Role**: Recruiter  
**Request**:
```json
{
  "notes": "Verified candidate skills against certifications.",
  "status_override": "COMPLETED"
}
```
**Response 200**: Updated resume record with recruiter notes and status override.

---

## Candidate Endpoints (Phase 4)

### GET /api/v1/candidates
**Role**: Recruiter, Delivery_Head, Client_Hiring_Manager  
**Query**: `?page=1&page_size=20&search=Alex&requisition_id=uuid`  
**Response 200**:
```json
{
  "items": [
    {
      "id": "uuid",
      "full_name": "Alex Mercer",
      "email": "alex.mercer@example.com",
      "phone": "+1-555-010-9988",
      "location": "San Francisco, CA",
      "total_experience_years": 8.5,
      "notice_period_days": 30,
      "skills_count": 12,
      "created_at": "2026-11-08T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```
*Note*: For Client Hiring Managers, PII is masked (`a***@***.com`, `***-***-9988`).

### GET /api/v1/candidates/{id}
**Role**: Recruiter (full profile), Client_HM (masked contact details)  
**Response 200**:
```json
{
  "id": "uuid",
  "full_name": "Alex Mercer",
  "email": "alex.mercer@example.com",
  "phone": "+1-555-010-9988",
  "location": "San Francisco, CA",
  "total_experience_years": 8.5,
  "notice_period_days": 30,
  "certifications": ["AWS Certified Solutions Architect"],
  "skills": [
    {
      "id": "uuid",
      "raw_name": "Java",
      "normalized_name": "java",
      "evidence": "8 years developing high-throughput microservices in Java/Spring Boot",
      "related_employment_id": "uuid"
    }
  ],
  "employments": [
    {
      "id": "uuid",
      "company": "Tech Corp",
      "job_title": "Lead Software Engineer",
      "start_date": "2020-01",
      "end_date": "Present",
      "description": "Architected distributed streaming services",
      "technologies": ["Java", "Kafka", "Docker"],
      "is_current": true
    }
  ],
  "educations": [
    {
      "id": "uuid",
      "institution": "University of California, Berkeley",
      "qualification": "Bachelor of Science",
      "field_of_study": "Computer Science",
      "graduation_year": 2016
    }
  ],
  "resumes": [
    {
      "id": "uuid",
      "file_name": "01_strong_java_senior.pdf",
      "mime_type": "application/pdf",
      "file_size_bytes": 125000,
      "parse_status": "parsed",
      "extraction_status": "COMPLETED",
      "uploaded_at": "2026-11-08T00:00:00Z"
    }
  ]
}
```

---

## Evaluation Endpoints

### POST /api/v1/candidates/{id}/evaluate
**Role**: Recruiter  
**Request**: `{ "requisition_id": "uuid" }`  
**Response 202**: `{ "evaluation_id": "uuid", "status": "processing" }`  
(Evaluation runs asynchronously; client polls GET /candidates/{id}/evaluation)

### GET /api/v1/candidates/{id}/evaluation
**Role**: Recruiter  
**Query**: `?requisition_id=uuid`  
**Response 200**:
```json
{
  "evaluation_id": "uuid",
  "total_score": 72.5,
  "scorecard_version": 2,
  "criterion_scores": [
    {
      "criterion_id": "uuid",
      "criterion_label": "5+ years Python experience",
      "evidence_status": "matched",
      "confidence": 0.91,
      "awarded_points": 30.0,
      "max_points": 30.0,
      "source_excerpts": ["Led Python development team for 6 years at Acme Corp"],
      "flags": { "low_confidence": false, "conflict": false }
    }
  ]
}
```

### POST /api/v1/evaluation-evidence/{evidence_id}/override
**Role**: Recruiter  
**Request**: `{ "new_status": "matched", "reason": "Verified by manual review of portfolio link" }`  
**Response 200**: Updated evidence with new evaluation version  
**Errors**: 400 (reason missing)

---

## Submission Endpoints

### POST /api/v1/requisitions/{id}/submissions
**Role**: Recruiter  
**Request**: `{ "candidate_ids": ["uuid", "uuid"], "client_organization_id": "uuid" }`  
**Response 201**: `{ "submission_ids": [...], "count": 2 }`  
**Errors**: 400 (> 50 candidates, candidate not shortlisted, profile not viewed), 404 (candidate or org not found)

### DELETE /api/v1/submissions/{id}
**Role**: Recruiter (withdraw before client action)  
**Response 204**  
**Errors**: 409 (client has already taken action)

---

## Client Portal Endpoints

### GET /api/v1/client/submissions
**Role**: Client_Hiring_Manager  
**Query**: `?page=1&page_size=20&requisition_id=uuid&stage=submitted`  
**Response 200**: Paginated submitted candidates (contact masked)

### POST /api/v1/client/submissions/{id}/action
**Role**: Client_Hiring_Manager  
**Request**: `{ "action": "shortlist" | "reject" | "request_interview", "note": "optional text (max 2000 chars)" }`  
**Response 200**: Updated submission with new pipeline stage  

---

## Pipeline Endpoints

### GET /api/v1/pipeline/{submission_id}/stages
**Role**: Recruiter, Client_HM, Delivery_Head  
**Response 200**: Full stage history with actor and timestamps

### POST /api/v1/pipeline/{submission_id}/stages
**Role**: Recruiter  
**Request**: `{ "new_stage": "offer_extended", "reason_note": "required if reverting" }`  
**Response 200**: Updated stage  
**Errors**: 400 (reason note missing for reversion, placed stage locked)

---

## Analytics Endpoints

### GET /api/v1/analytics/pipeline
**Role**: Delivery_Head  
**Query**: `?date_from=2024-01-01&date_to=2024-12-31&recruiter_id=uuid&requisition_id=uuid`  
**Response 200**: Aggregated pipeline metrics, time-in-stage, conversion rates

### GET /api/v1/analytics/bias-monitor
**Role**: Delivery_Head  
**Query**: `?months=3`  
**Response 200**: Per-requisition rank correlation statistics, alerts, monthly summary

---

## Audit Endpoints

### GET /api/v1/audit-logs
**Role**: Delivery_Head  
**Query**: `?date_from=...&date_to=...&event_type=SUBMISSION_CREATED&actor_id=uuid&resource_id=uuid&page=1`  
**Response 200**: Paginated audit log entries

---

## Account Endpoints

### GET /api/v1/account/me
**Role**: Any authenticated  
**Response 200**: User profile (display_name, email, role, org)

### PUT /api/v1/account/me
**Role**: Any authenticated  
**Request**: `{ "display_name": "Jane Smith" }`  
**Response 200**: Updated profile

### POST /api/v1/account/change-password
**Role**: Any authenticated  
**Request**: `{ "current_password": "...", "new_password": "..." }`  
**Response 204**  
**Errors**: 400 (current password incorrect)

### GET /api/v1/account/activity
**Role**: Any authenticated  
**Response 200**: Last 30 days of activity log entries

### POST /api/v1/candidates/{id}/delete-request
**Role**: Recruiter  
**Request**: `{ "reason": "Candidate withdrawal request" }`  
**Response 202**: `{ "deletion_request_id": "uuid", "expected_completion_days": 30 }`

---

## Candidate Evaluation and Deterministic Ranking Endpoints (Phase 5)

### POST /api/v1/requisitions/{requisition_id}/evaluations
Starts asynchronous batch candidate evaluation across all eligible candidates (or selected candidates) for a requisition. Requires an approved scorecard.
- **Role**: `recruiter`
- **Request Body**: `{"candidate_ids": ["uuid", ...]}` (optional, defaults to all candidates in requisition)
- **Response**: `202 Accepted` with `EvaluationRunResponse`

### POST /api/v1/requisitions/{requisition_id}/candidates/{candidate_id}/evaluate
Synchronously evaluates a single candidate against the active approved scorecard.
- **Role**: `recruiter`
- **Response**: `200 OK` with `EvaluationResponse`

### GET /api/v1/requisitions/{requisition_id}/evaluations
Lists paginated, ranked candidate evaluations with multi-attribute filtering and sorting.
- **Roles**: `recruiter`, `client_hiring_manager` (PII masked for client)
- **Query Parameters**:
  - `page` (default 1), `page_size` (default 20)
  - `sort_by` (`score_desc`, `score_asc`, `experience_desc`, `notice_asc`, `evaluated_desc`)
  - `score_min`, `score_max`
  - `confidence_level` (`HIGH`, `NEEDS_REVIEW`, `LOW`)
  - `review_decision` (`UNREVIEWED`, `SHORTLIST`, `REJECT`, `HOLD`, `REQUEST_INFO`)
  - `missing_evidence_only` (`true`/`false`)
  - `must_have_matched_only` (`true`/`false`)
  - `search` (candidate name/email)
- **Response**: `200 OK` with `EvaluationListResponse`

### GET /api/v1/evaluations/{evaluation_id}
Fetches full evaluation record including score breakdown, confidence, and audit provenance.
- **Roles**: `recruiter`, `client_hiring_manager` (PII masked for client)
- **Response**: `200 OK` with `EvaluationResponse`

### GET /api/v1/evaluations/{evaluation_id}/evidence
Fetches criterion-level evidence citations, match statuses, and verbatim resume excerpts.
- **Roles**: `recruiter`, `client_hiring_manager`
- **Response**: `200 OK` with array of `CriterionEvidenceResponse`

### GET /api/v1/requisitions/{requisition_id}/evaluation-runs/{run_id}
Fetches real-time status and progress counts of a batch evaluation run.
- **Roles**: `recruiter`, `client_hiring_manager`
- **Response**: `200 OK` with `EvaluationRunResponse`

### POST /api/v1/evaluations/{evaluation_id}/review
Records an immutable recruiter review decision (Shortlist, Reject, Hold, Request Info) with notes.
- **Role**: `recruiter` (403 Forbidden for client hiring managers)
- **Request Body**: `{"decision": "SHORTLIST", "notes": "..."}`
- **Response**: `200 OK` with `RecruiterReviewResponse`

### POST /api/v1/evaluations/{evaluation_id}/recalculate
Deterministically recalculates candidate scores using the exact same approved scorecard and stored validated evidence without re-calling the AI provider.
- **Role**: `recruiter`
- **Response**: `200 OK` with `EvaluationResponse`

---

## Phase 6: Recruiter Dashboard & Candidate Management Endpoints

### GET /api/v1/recruiter/dashboard
Composite recruiter workspace telemetry: aggregated KPI metrics, requisition performance cards, document processing health, and real-time activity timeline.
- **Roles**: `recruiter`, `delivery_head`, `admin` (403 Forbidden for client hiring managers)
- **Response**: `200 OK` with `RecruiterDashboardResponse`

### GET /api/v1/recruiter/metrics
Aggregated real database metrics across the organization:
- `active_requisitions`
- `total_candidates`
- `resumes_processed`
- `resumes_pending`
- `failed_jobs`
- `candidates_awaiting_review`
- `candidates_shortlisted`
- `completed_evaluations`
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `DashboardMetricsResponse`

### GET /api/v1/recruiter/activity
Live activity timeline across requisition creation, resume batch ingestion, completed candidate evaluations, recruiter review decisions, and internal recruiter notes.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Query Parameters**: `limit` (default 20, max 100)
- **Response**: `200 OK` with `DashboardActivityResponse`

### GET /api/v1/candidates
Global searchable and filterable candidate directory.
- **Roles**: `recruiter`, `delivery_head`, `admin` (PII masked for client roles)
- **Query Parameters**:
  - `page`, `page_size`
  - `search` (name, email, skills, job title, company)
  - `requisition_id`
  - `skill`
  - `location`
  - `min_experience`, `max_experience`
  - `max_notice_days`
  - `evaluation_status` (`evaluated`, `unreviewed`, `pending`)
  - `review_decision` (`SHORTLIST`, `HOLD`, `REJECT`, `REQUEST_INFO`, `UNREVIEWED`)
  - `min_score`, `max_score`
  - `sort_by` (`created_at`, `score`, `experience`, `name`)
  - `sort_order` (`asc`, `desc`)
- **Response**: `200 OK` with `CandidateListResponse`

### GET /api/v1/candidates/{candidate_id}/evaluations
Retrieves multi-version evaluation trail for a candidate across approved scorecards and requisitions.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with array of `CandidateEvaluationHistoryItemResponse`

### GET /api/v1/candidates/{candidate_id}/notes
Lists confidential internal notes on a candidate, ordered chronologically newest first.
- **Roles**: `recruiter`, `delivery_head`, `admin` (403 Forbidden for client users)
- **Response**: `200 OK` with `CandidateNoteListResponse`

### POST /api/v1/candidates/{candidate_id}/notes
Creates a confidential recruiter note for a candidate, optionally referencing a requisition.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Request Body**: `{"content": "string", "requisition_id": "uuid | null"}`
- **Response**: `201 Created` with `CandidateNoteResponse`

### PUT /api/v1/candidates/notes/{note_id}
Updates an existing confidential recruiter note.
- **Roles**: Author of the note, or org `admin` / `delivery_head`
- **Request Body**: `{"content": "string"}`
- **Response**: `200 OK` with `CandidateNoteResponse`

### DELETE /api/v1/candidates/notes/{note_id}
Deletes a confidential recruiter note.
- **Roles**: Author of the note, or org `admin` / `delivery_head`
- **Response**: `200 OK` with `{"ok": true, "message": "Note deleted successfully"}`

### GET /api/v1/requisitions/{requisition_id}/summary
Returns recruiter summary of requisition performance (candidate count, evaluated count, pending reviews, shortlisted, rejected, hold, average score, top score, approved scorecard version).
- **Roles**: `recruiter`, `delivery_head`
- **Response**: `200 OK` with `RequisitionSummaryResponse`

### GET /api/v1/requisitions/{requisition_id}/candidates
Returns candidates associated with this requisition with search, filter, and deterministic sorting support.
- **Roles**: `recruiter`, `delivery_head`
- **Response**: `200 OK` with `CandidateListResponse`

---

## Phase 7: Client Shortlist Portal & Hiring Pipeline Endpoints

### GET /api/v1/client/dashboard
Returns operational metrics for the authenticated client organization (active shared requisitions, total submissions, awaiting review, shortlisted, rejected, interview requests, info inquiries).
- **Roles**: `client_hiring_manager`, `client`, `admin`
- **Response**: `200 OK` with `ClientDashboardMetricsResponse`

### GET /api/v1/client/requisitions
Lists all active job requisitions shared with the authenticated client organization.
- **Roles**: `client_hiring_manager`, `client`, `admin`
- **Response**: `200 OK` with `list[ClientRequisitionListItemResponse]`

### GET /api/v1/client/requisitions/{id}
Retrieves detailed job description and submission counts for a shared requisition.
- **Roles**: `client_hiring_manager`, `client`, `admin`
- **Response**: `200 OK` with `ClientRequisitionDetailResponse`

### GET /api/v1/client/submissions
Lists candidates submitted to the client organization with strict PII masking (Candidate CND-XXXXX, sanitized location, match scores).
- **Query Parameters**: `requisition_id` (optional), `stage` (optional)
- **Roles**: `client_hiring_manager`, `client`, `admin`
- **Response**: `200 OK` with `list[ClientSubmissionListItemResponse]`

### GET /api/v1/client/submissions/{id}
Retrieves complete sanitized candidate profile for client review:
- Masked reference code (`Candidate CND-XXXXX`), broad location, experience years, notice period.
- Criterion-level match breakdown with evidence grounding excerpts (proprietary scorecard weights withheld).
- Relevant employment history, education, and verified skills.
- Explicit recruiter recommendation notes.
- Complete pipeline history trail and past inquiries.
- **Roles**: `client_hiring_manager`, `client`, `admin`
- **Response**: `200 OK` with `MaskedCandidateProfileResponse`

### POST /api/v1/client/submissions/{id}/decisions
Records client hiring manager decision (`CLIENT_SHORTLISTED`, `CLIENT_REJECTED`, `INTERVIEW_REQUESTED`, `ADDITIONAL_INFO_REQUESTED`).
- Updates `Submission.current_stage` and appends immutable `PipelineRecord`.
- Creates `ClientRequest` if interview details or information requests are specified.
- **Roles**: `client_hiring_manager`, `client`, `admin`
- **Request Body**: `ClientDecisionCreateRequest`
- **Response**: `200 OK` with updated `MaskedCandidateProfileResponse`

### POST /api/v1/client/submissions/{id}/requests
Submits standalone interview scheduling request or candidate clarification inquiry.
- **Roles**: `client_hiring_manager`, `client`, `admin`
- **Request Body**: `ClientRequestCreateRequest`
- **Response**: `200 OK` with `ClientRequestResponse`

### GET /api/v1/client/submissions/{id}/history
Returns audit history timeline of stage transitions and decisions for a candidate submission.
- **Roles**: `client_hiring_manager`, `client`, `admin`
- **Response**: `200 OK` with `list[PipelineRecordResponse]`

### POST /api/v1/requisitions/{requisition_id}/submissions
Submits an evaluated candidate to a client organization for review.
- Verifies requisition and candidate belong to recruiter's organization.
- Validates candidate has completed scorecard evaluation.
- Prevents duplicate active submission to same client.
- Generates reproducible masked candidate reference (`Candidate CND-XXXXX`).
- Initializes `PipelineRecord` at `SUBMITTED` stage.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Request Body**: `SubmissionCreateRequest`
- **Response**: `201 Created`

### GET /api/v1/recruiter/submissions
Lists all client submissions from the staffing firm across client companies, showing real candidate contact details alongside masked candidate reference.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `list[RecruiterSubmissionListItemResponse]`

### GET /api/v1/recruiter/pipeline
Returns visual Kanban pipeline board data grouped across all 9 hiring stages.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `PipelineBoardResponse`

### PATCH /api/v1/recruiter/submissions/{id}/stage
Updates candidate pipeline stage (`INTERVIEW_SCHEDULED`, `OFFER_EXTENDED`, `HIRED`, `WITHDRAWN`, etc.) and appends audit log.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Request Body**: `RecruiterStageUpdateRequest`
- **Response**: `200 OK`

### POST /api/v1/recruiter/requests/{request_id}/response
Recruiter responds to client interview scheduling request or clarification question.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Request Body**: `RecruiterResponseRequest`
- **Response**: `200 OK` with `ClientRequestResponse`

### GET /api/v1/recruiter/clients
Lists available client organizations for candidate submission.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `list[ClientOrgOption]`

### GET /api/v1/delivery/pipeline-summary
Returns organization-wide pipeline summary and client conversion ratios (shortlist rate, interview rate, hire rate) respecting strict staffing firm tenant isolation.
- **Roles**: `delivery_head`, `admin`, `super_admin`
- **Response**: `200 OK` with `DeliveryPipelineSummaryResponse`

---

## Phase 8 Privacy, Consent, Deletion, Audit & Governance Endpoints

### Candidate Consent Endpoints

#### POST /api/v1/candidates/{id}/consent-requests
Initiates a single-use expiring tokenized consent request for a candidate.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Request Body**: `ConsentRequestCreate` (`purpose`, `collection_method`, `requisition_id`)
- **Response**: `201 Created` with `ConsentRecordResponse` containing `token` and `consent_url`

#### GET /api/v1/public/consent/{token}
Retrieves safe public information for a candidate consent decision link (no authentication required).
- **Response**: `200 OK` with `PublicConsentInfoResponse` (`candidate_reference`, `organization_name`, `purpose`, `is_valid`)

#### POST /api/v1/public/consent/{token}/decision
Records candidate's consent decision (`GRANTED` or `DECLINED`). Marks token as used (single-use enforcement).
- **Request Body**: `ConsentDecisionSubmit` (`decision`, `reason`)
- **Response**: `200 OK` with `ConsentRecordResponse`

#### POST /api/v1/candidates/{id}/consent/withdraw
Records immediate candidate consent withdrawal. Transitions candidate status to `WITHDRAWN` and blocks future processing.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Request Body**: `ConsentWithdrawRequest` (`reason`)
- **Response**: `200 OK` with `ConsentRecordResponse`

#### GET /api/v1/candidates/{id}/consent
Retrieves complete historical consent audit records for a candidate.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `list[ConsentRecordResponse]`

#### GET /api/v1/consent-records
Lists organization consent records with pagination and status filtering.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Query Params**: `status`, `page`, `page_size`
- **Response**: `200 OK` with `ConsentRecordListResponse`

### Data Subject Access & Export Endpoints

#### POST /api/v1/candidates/{id}/data-requests
Creates a candidate personal data access or export request.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Request Body**: `DataRequestCreate` (`request_type`, `reason`)
- **Response**: `201 Created` with `DataRequestResponse`

#### GET /api/v1/data-requests
Lists candidate personal data requests for the organization.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `DataRequestListResponse`

#### POST /api/v1/data-requests/{request_id}/export
Generates complete portable JSON export of candidate personal data, strictly excluding sensitive internal secrets, storage paths, and proprietary formulas.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `CandidateDataExportResponse`

#### GET /api/v1/data-exports/{request_id}
Downloads the generated portable candidate export JSON file before expiration.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `application/json` file stream

### Controlled Deletion (Right to be Forgotten) Endpoints

#### POST /api/v1/candidates/{id}/deletion-requests
Submits a candidate erasure request.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Request Body**: `DeletionRequestCreate` (`reason`, `scheduled_for`)
- **Response**: `201 Created` with `DeletionRequestResponse`

#### GET /api/v1/deletion-requests
Lists candidate deletion requests for the organization with status filtering.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `DeletionRequestListResponse`

#### POST /api/v1/deletion-requests/{request_id}/review
Delivery head reviews deletion request: approves, rejects, or applies legal hold.
- **Roles**: `delivery_head`, `admin`, `super_admin`
- **Request Body**: `DeletionReviewSubmit` (`decision`, `is_legal_hold`, `legal_hold_reason`, `retention_policy_notes`)
- **Response**: `200 OK` with `DeletionRequestResponse`

#### POST /api/v1/deletion-requests/{request_id}/execute
Executes controlled permanent erasure: unlinks physical resume files from disk, cancels pending processing jobs, and scrubs database PII to `[DELETED]`.
- **Roles**: `delivery_head`, `admin`, `super_admin`
- **Response**: `200 OK` with `DeletionExecutionResponse`

### Audit Trail Endpoints

#### GET /api/v1/audit-events
Queries organization audit trail events with pagination and filtering. Sensitive payload values are recursively sanitized.
- **Roles**: `delivery_head`, `admin`, `super_admin`
- **Query Params**: `event_type`, `resource_type`, `actor_user_id`, `limit`, `offset`
- **Response**: `200 OK` with `AuditEventListResponse`

#### GET /api/v1/audit-events/{event_id}
Retrieves single audit event detail.
- **Roles**: `delivery_head`, `admin`, `super_admin`
- **Response**: `200 OK` with `AuditEventResponse`

### Responsible AI Governance Endpoints

#### GET /api/v1/governance/ai-metrics
Aggregates score distributions, reviewer decision rates, evidence coverage metrics, and statutory fairness disclosures.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `GovernanceAIMetricsResponse`

#### GET /api/v1/governance/evaluation-quality
Telemetry on evaluation confidence distribution and quality assurance metrics.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `EvaluationQualityResponse`

#### GET /api/v1/privacy/dashboard
Privacy dashboard KPIs including pending consent counts, granted consent ratio, active legal holds, and completed deletions.
- **Roles**: `recruiter`, `delivery_head`, `admin`
- **Response**: `200 OK` with `PrivacyDashboardStatsResponse`

---

## HTTP Status Codes Reference

| Code | Meaning |
|------|---------|
| 200 | Success (read or update) |
| 201 | Resource created |
| 202 | Async operation accepted |
| 204 | Success, no content (delete/logout) |
| 400 | Business rule violation |
| 401 | Missing or invalid authentication |
| 403 | Authenticated but insufficient permissions |
| 404 | Not found (also cross-org access) |
| 409 | Optimistic lock conflict |
| 413 | Payload too large |
| 415 | Unsupported media type (file upload) |
| 422 | Schema validation failure |
| 429 | Rate limit exceeded |
| 503 | External service unavailable (LLM after retries) |
