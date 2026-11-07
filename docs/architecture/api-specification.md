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

### POST /api/v1/requisitions
**Role**: Recruiter  
**Request**: `{ "title": "Senior Engineer", "job_description": "..." }`  
**Response 201**: Created requisition  
**Errors**: 422 (validation)

### GET /api/v1/requisitions/{id}
**Role**: Recruiter, Delivery_Head  
**Response 200**: Requisition detail  
**Errors**: 404 (not found or cross-org)

### PUT /api/v1/requisitions/{id}
**Role**: Recruiter  
**Request**: `{ "title": "...", "job_description": "...", "version": 3 }`  
**Response 200**: Updated requisition  
**Errors**: 409 (optimistic lock conflict), 404

### DELETE /api/v1/requisitions/{id}
**Role**: Recruiter (archives, does not delete)  
**Response 200**: `{ "status": "archived" }`

---

## JD Extraction

### POST /api/v1/requisitions/{id}/extract-jd
**Role**: Recruiter  
**Request**: `{}` (uses JD from requisition)  
**Response 200**:
```json
{
  "job_title": { "value": "Senior Python Engineer", "confidence": 0.97 },
  "experience_range": { "value": { "min_years": 5, "max_years": 10 }, "confidence": 0.92 },
  "location": { "value": "London, UK", "confidence": 0.88 },
  "must_have_skills": [
    { "value": "Python", "confidence": 0.99 },
    { "value": "FastAPI", "confidence": 0.94 }
  ],
  "nice_to_have_skills": [{ "value": "Kubernetes", "confidence": 0.85 }],
  "notice_period": { "value": "30 days", "confidence": 0.91 },
  "other_requirements": []
}
```
**Errors**: 503 (LLM unavailable after retries)

---

## Scorecard Endpoints

### GET /api/v1/requisitions/{id}/scorecard
**Role**: Recruiter, Delivery_Head  
**Response 200**: Active scorecard with criteria

### POST /api/v1/requisitions/{id}/scorecard
**Role**: Recruiter  
**Request**: `{ "criteria": [{ "criterion_type": "experience", "label": "5+ years", "weight": 30 }] }`  
**Response 201**: Created scorecard

### PUT /api/v1/scorecards/{id}
**Role**: Recruiter  
**Request**: `{ "criteria": [...], "action": "activate" | "save_draft" | "reset_to_draft" }`  
**Response 200**: Updated scorecard  
**Errors**: 400 (weights don't sum to 100 on activate)

---

## Resume Upload Endpoints

### POST /api/v1/requisitions/{id}/upload-batch
**Role**: Recruiter  
**Content-Type**: `multipart/form-data`  
**Body**: Up to 500 files (PDF/DOCX)  
**Response 202**:
```json
{ "batch_id": "uuid", "accepted_count": 498, "rejected_files": [{ "filename": "corrupt.pdf", "reason": "Invalid PDF signature" }] }
```
**Errors**: 413 (batch too large), 422 (no files)

### GET /api/v1/upload-batches/{batch_id}/status
**Role**: Recruiter  
**Response 200**:
```json
{
  "batch_id": "uuid",
  "status": "processing",
  "total": 500,
  "processed": 247,
  "failed": 3,
  "duplicates": 12,
  "files": [
    { "filename": "john_doe.pdf", "status": "parsed", "candidate_id": "uuid" },
    { "filename": "corrupt.docx", "status": "failed", "error": "Could not extract text (< 50 words)" }
  ]
}
```

---

## Candidate Endpoints

### GET /api/v1/requisitions/{id}/candidates
**Role**: Recruiter, Delivery_Head  
**Query**: `?page=1&page_size=25&sort_by=score&sort_dir=desc&score_min=50&score_max=100&skills=Python&pipeline_stage=submitted`  
**Response 200**: Paginated ranked candidate list with scores

### GET /api/v1/candidates/{id}
**Role**: Recruiter (full profile + protected attrs labeled), Client_HM (submitted only, contact masked)  
**Response 200**: Full candidate profile with current evaluation

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
