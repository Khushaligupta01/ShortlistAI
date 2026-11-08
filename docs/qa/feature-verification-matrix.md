# Feature Verification Matrix — ShortlistAI

**Document**: `docs/qa/feature-verification-matrix.md`  
**Evaluation Scope**: Phases 1 through 8  
**Verification Criteria**: Tested via automated test suites, backend endpoints, database persistence, and frontend routes.  
**Statuses Used**: `VERIFIED`, `PARTIALLY_VERIFIED`, `FAILED`, `NOT_IMPLEMENTED`, `BLOCKED`

---

## Summary Matrix

| Phase | Total Features | Verified | Partially Verified | Failed | Not Implemented |
|---|---|---|---|---|---|
| **Phase 1: Architecture & Modeling** | 4 | 4 | 0 | 0 | 0 |
| **Phase 2: Auth & Organization Isolation** | 7 | 7 | 0 | 0 | 0 |
| **Phase 3: JD Intelligence & Scorecards** | 7 | 7 | 0 | 0 | 0 |
| **Phase 4: Resume Ingestion & Parsing** | 9 | 9 | 0 | 0 | 0 |
| **Phase 5: Evaluation & Ranking Engine** | 8 | 8 | 0 | 0 | 0 |
| **Phase 6: Recruiter Workspace & Notes** | 9 | 9 | 0 | 0 | 0 |
| **Phase 7: Client Portal & Submissions** | 9 | 9 | 0 | 0 | 0 |
| **Phase 8: Privacy, Consent & Governance** | 8 | 8 | 0 | 0 | 0 |
| **Total** | **61** | **61** | **0** | **0** | **0** |

---

## Detailed Matrix by Phase

### Phase 1 — Architecture & Core Design

#### 1.1 Requirements & Architecture Consistency
- **Expected Behavior**: Unified system design adhering to multi-tenant staffing agency model, separated client portal, and evidence-grounded AI evaluation.
- **Backend Implementation**: `backend/app/core/config.py`, `backend/app/main.py`.
- **Frontend Implementation**: Next.js 15 App router structure.
- **Database Persistence**: PostgreSQL / SQLite schema definitions.
- **Authorization Requirements**: Public & authenticated boundaries defined.
- **Test Coverage**: System architecture reviews; all automated test suites pass.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 1.2 Data Model Consistency & Type Safety
- **Expected Behavior**: SQLAlchemy 2.0 mapped models with strict UUID primary keys, foreign keys, and UTC timestamps.
- **Backend Implementation**: `backend/app/models/*.py`.
- **Frontend Implementation**: `frontend/lib/types.ts`.
- **Database Persistence**: Alembic version tree.
- **Authorization Requirements**: N/A.
- **Test Coverage**: `tests/test_database.py`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 1.3 API Contract Consistency
- **Expected Behavior**: Standardized REST envelope, HTTP status codes, and error response structure (`error_code`, `message`, `trace_id`).
- **Backend Implementation**: `backend/app/api/v1/router.py`, `backend/app/main.py`.
- **Frontend Implementation**: `frontend/lib/api.ts` error handler.
- **Database Persistence**: N/A.
- **Authorization Requirements**: Global middleware.
- **Test Coverage**: `tests/test_health.py::test_security_headers`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 1.4 Security Headers & Defense in Depth
- **Expected Behavior**: Server injects X-Content-Type-Options, X-Frame-Options, CSP, and HSTS headers.
- **Backend Implementation**: `backend/app/main.py:add_security_headers`.
- **Frontend Implementation**: Next.js layout headers.
- **Database Persistence**: N/A.
- **Authorization Requirements**: All routes.
- **Test Coverage**: `tests/test_health.py::test_security_headers`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

---

### Phase 2 — Authentication & Multi-Tenant Isolation

#### 2.1 User Authentication & Login
- **Expected Behavior**: Authenticates users with email and password, returning RS256/HS256 JWT access token and refresh token.
- **Backend Implementation**: `backend/app/api/v1/endpoints/auth.py`.
- **Frontend Implementation**: `frontend/app/login/page.tsx`.
- **Database Persistence**: `users` table with Argon2/bcrypt hashed passwords.
- **Authorization Requirements**: Public route.
- **Test Coverage**: `tests/test_auth.py::test_login_success`, `test_login_wrong_password`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 2.2 Token Refresh & Expiry
- **Expected Behavior**: Exchanges valid refresh token for new access token; invalidates expired or revoked tokens.
- **Backend Implementation**: `backend/app/api/v1/endpoints/auth.py:refresh_token`.
- **Frontend Implementation**: `frontend/lib/api.ts:authFetch` interceptor.
- **Database Persistence**: Refresh tokens tracked server-side.
- **Authorization Requirements**: Valid refresh token.
- **Test Coverage**: `tests/test_auth.py::test_refresh_token`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 2.3 Logout & Invalidation
- **Expected Behavior**: Clears server-side refresh tokens and client session cookies.
- **Backend Implementation**: `backend/app/api/v1/endpoints/auth.py:logout`.
- **Frontend Implementation**: Logout button in `Navbar.tsx` and `ClientNavbar.tsx`.
- **Database Persistence**: Token invalidation state.
- **Authorization Requirements**: Authenticated user.
- **Test Coverage**: `tests/test_auth.py::test_logout`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 2.4 Role-Based Access Control (RBAC)
- **Expected Behavior**: Enforces role restrictions (`recruiter`, `client_hiring_manager`, `delivery_head`, `admin`).
- **Backend Implementation**: `backend/app/api/dependencies/auth.py:require_role`.
- **Frontend Implementation**: Client navigation gating and role-aware layouts.
- **Database Persistence**: `users.role` column.
- **Authorization Requirements**: Verified per route.
- **Test Coverage**: `tests/test_authorization.py::test_recruiter_can_access_requisitions`, `test_client_hm_cannot_access_requisitions`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 2.5 Multi-Tenant Organization Isolation
- **Expected Behavior**: Users only access resources belonging to their organization; cross-org requests return 404.
- **Backend Implementation**: `assert_org_member` check across repositories and services.
- **Frontend Implementation**: Scoped views per tenant.
- **Database Persistence**: `organization_id` foreign keys on all core entities.
- **Authorization Requirements**: Tenant membership check.
- **Test Coverage**: `tests/test_authorization.py::test_cross_org_requisition_returns_404`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 2.6 Account Inactivity Lock
- **Expected Behavior**: Deactivated user accounts cannot authenticate or access endpoints.
- **Backend Implementation**: `backend/app/api/v1/endpoints/auth.py:login`.
- **Frontend Implementation**: Displays account disabled error.
- **Database Persistence**: `users.is_active` boolean.
- **Authorization Requirements**: Public login check.
- **Test Coverage**: `tests/test_auth.py::test_login_inactive_account`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 2.7 Organization Memberships
- **Expected Behavior**: Organization creation and user membership tracking with unique email constraint per organization.
- **Backend Implementation**: `backend/app/api/v1/endpoints/organizations.py`.
- **Frontend Implementation**: User and org settings.
- **Database Persistence**: `organizations`, `organization_memberships` tables.
- **Authorization Requirements**: Super admin or org admin.
- **Test Coverage**: `tests/test_database.py::test_org_membership_unique`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

---

### Phase 3 — Job Description Intelligence & Scorecards

#### 3.1 Requisition Creation & Management
- **Expected Behavior**: Recruiters create and update requisitions with title, job description, and client assignment.
- **Backend Implementation**: `backend/app/api/v1/endpoints/requisitions.py`.
- **Frontend Implementation**: `frontend/app/requisitions/new/page.tsx`, `frontend/app/requisitions/page.tsx`.
- **Database Persistence**: `requisitions` table.
- **Authorization Requirements**: `recruiter`, `delivery_head`, `admin`.
- **Test Coverage**: `tests/phase3/test_scorecard.py::test_01_scorecard_creation`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 3.2 AI Job Description Requirements Extraction
- **Expected Behavior**: Extracts structured requirements (skills, experience, education, location, notice period) from raw JD text.
- **Backend Implementation**: `backend/app/ai/jd_extraction_service.py`.
- **Frontend Implementation**: `frontend/app/requisitions/[id]/page.tsx` JD extractor interface.
- **Database Persistence**: Extraction results cached in scorecard criteria.
- **Authorization Requirements**: `recruiter`, `delivery_head`.
- **Test Coverage**: `tests/phase3/test_jd_extraction.py` (14 edge-case tests).
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 3.3 Scorecard Criteria Weight Validation
- **Expected Behavior**: Total criteria weights must sum to exactly 100 points across categories (Experience 30, Must-have skills 40, Notice period 15, Location 10, Nice-to-have 5).
- **Backend Implementation**: `backend/app/services/scorecard_service.py:validate_scorecard_weights`.
- **Frontend Implementation**: Live weight total counter in scorecard editor.
- **Database Persistence**: `scorecard_criteria.weight` numeric column.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase3/test_scorecard.py::test_04_weight_total_validation`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 3.4 Dynamic Scorecard Editing
- **Expected Behavior**: Recruiter can add, modify, or delete criteria while scorecard is in `draft` status.
- **Backend Implementation**: `backend/app/services/scorecard_service.py:update_scorecard`.
- **Frontend Implementation**: Interactive criteria editor with category pills and point inputs.
- **Database Persistence**: `scorecard_criteria` rows.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase3/test_scorecard.py::test_02_scorecard_editing`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 3.5 Scorecard Approval & Immutability Locking
- **Expected Behavior**: Approving a scorecard locks it into `approved` status, preventing further edits.
- **Backend Implementation**: `backend/app/services/scorecard_service.py:approve_scorecard`.
- **Frontend Implementation**: "Approve Scorecard" confirmation dialog.
- **Database Persistence**: `scorecards.status = 'approved'`, `scorecards.approved_at`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase3/test_scorecard.py::test_07_approval_and_locking`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 3.6 Scorecard Versioning
- **Expected Behavior**: Modifying an approved scorecard creates a new version (`version_number += 1`), preserving historical evaluations.
- **Backend Implementation**: `backend/app/services/scorecard_service.py:create_new_scorecard_version`.
- **Frontend Implementation**: Version selector dropdown on requisition page.
- **Database Persistence**: `scorecards.version_number`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase3/test_scorecard.py::test_08_version_preservation`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 3.7 AI Provider Fallback & Safe Failure Handling
- **Expected Behavior**: When AI provider times out or fails, gracefully falls back to deterministic extraction without crashing.
- **Backend Implementation**: `backend/app/ai/provider_factory.py`.
- **Frontend Implementation**: Shows actionable warning banner with manual input options.
- **Database Persistence**: Preserves draft requisition.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase3/test_jd_extraction.py::test_10_ai_provider_timeout`, `test_11_ai_provider_unavailable`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

---

### Phase 4 — Resume Ingestion, Document Parsing & Extraction

#### 4.1 Bulk PDF & DOCX Upload
- **Expected Behavior**: Accepts multi-file uploads (up to 500 files / 250 MB batch) in PDF and DOCX formats.
- **Backend Implementation**: `backend/app/api/v1/endpoints/resumes.py:upload_resumes`.
- **Frontend Implementation**: Drag-and-drop batch upload dropzone in `frontend/app/requisitions/[id]/page.tsx`.
- **Database Persistence**: `upload_batches`, `resumes` tables.
- **Authorization Requirements**: `recruiter`.
- **Test Coverage**: `tests/phase4/test_api_endpoints.py::test_complete_upload_parsing_review_flow`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 4.2 MIME Type & Magic Byte Validation
- **Expected Behavior**: Validates file headers (`%PDF`, `PK\x03\x04`) rather than relying on file extension alone.
- **Backend Implementation**: `backend/app/services/document_parser_service.py:validate_document`.
- **Frontend Implementation**: Client file type pre-check.
- **Database Persistence**: `resumes.parse_status = 'failed'` on invalid bytes.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase4/test_document_extraction.py::test_pdf_corrupted_handling`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 4.3 High-Fidelity Text Extraction
- **Expected Behavior**: Extracts text from multi-page PDFs, complex paragraph flows, and tabular DOCX documents.
- **Backend Implementation**: PyMuPDF (`fitz`) and `python-docx` extractors.
- **Frontend Implementation**: Resume text inspection drawer on candidate profile.
- **Database Persistence**: `resumes.raw_text`, `resumes.normalized_text`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase4/test_document_extraction.py::test_pdf_extraction_multipage`, `test_docx_extraction_tables`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 4.4 OCR Fallback Signaling
- **Expected Behavior**: Identifies scanned/image-based PDFs with low character density and flags them for OCR processing.
- **Backend Implementation**: `backend/app/services/document_parser_service.py:_is_scanned_pdf`.
- **Frontend Implementation**: Displays "Scanned Document — OCR Required" badge.
- **Database Persistence**: `resumes.extraction_metadata['is_scanned']`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase4/test_document_extraction.py::test_pdf_scanned_ocr_required`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 4.5 Multi-Level Duplicate Detection
- **Expected Behavior**: Detects exact file duplicates via SHA-256 hash and candidate profile duplicates via normalized email/phone.
- **Backend Implementation**: `backend/app/services/duplicate_detection_service.py`.
- **Frontend Implementation**: Highlights duplicate uploads with link to existing candidate record.
- **Database Persistence**: `resumes.file_hash`, `candidates.email`.
- **Authorization Requirements**: Tenant scoped.
- **Test Coverage**: `tests/phase4/test_duplicate_detection.py::test_exact_file_duplicate_detection`, `test_cross_org_file_duplicate_isolation`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 4.6 Asynchronous Queue Worker & Lease Locking
- **Expected Behavior**: Processes resume parsing asynchronously via database-backed queue with optimistic locking and timeout lease renewals.
- **Backend Implementation**: `backend/app/services/worker_service.py`.
- **Frontend Implementation**: Live batch progress bar polling `/batches/{id}`.
- **Database Persistence**: `resume_processing_jobs` table.
- **Authorization Requirements**: Background service / Recruiter.
- **Test Coverage**: `tests/phase4/test_background_processing.py::test_job_claiming_and_execution_lifecycle`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 4.7 Retry on Failure & Error Capture
- **Expected Behavior**: Automatically retries transient failures up to `WORKER_MAX_ATTEMPTS = 3`, recording stack trace and error message.
- **Backend Implementation**: `backend/app/services/worker_service.py:record_job_failure`.
- **Frontend Implementation**: Displays failure reason and retry button.
- **Database Persistence**: `resume_processing_jobs.attempts`, `resumes.parse_error`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase4/test_background_processing.py::test_job_retry_on_corrupted_file`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 4.8 Structured Candidate Profile Extraction
- **Expected Behavior**: Extracts structured employment timelines, education credentials, and skills without fabricating missing data.
- **Backend Implementation**: `backend/app/ai/resume_extraction_service.py`.
- **Frontend Implementation**: Candidate profile timeline and skill cloud.
- **Database Persistence**: `candidates`, `candidate_employments`, `candidate_educations`, `candidate_skills`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase4/test_ai_extraction.py::test_ai_extraction_valid_output`, `test_ai_extraction_missing_fields_preserved_as_null`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 4.9 Bulk Synthetic Benchmark Execution
- **Expected Behavior**: Ingests 50 synthetic resumes concurrently without deadlocks or unhandled exceptions.
- **Backend Implementation**: Batch worker execution.
- **Frontend Implementation**: Batch status table.
- **Database Persistence**: 50 complete candidate profiles.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase4/test_benchmark_synthetic_batch.py::test_bulk_batch_processing_benchmark`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

---

### Phase 5 — Evaluation Engine & Deterministic Scoring

#### 5.1 Evidence Extraction & Grounded Citations
- **Expected Behavior**: Extracts verbatim evidence excerpts for each scorecard criterion directly from resume text.
- **Backend Implementation**: `backend/app/ai/evidence_extraction_service.py`.
- **Frontend Implementation**: Criterion evidence cards with direct excerpt text.
- **Database Persistence**: `evaluation_evidence.evidence_text`, `source_reference`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase5/test_scoring_engine.py::test_01_experience_full_match`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 5.2 Anti-Fabrication Token Verification
- **Expected Behavior**: Validates quoted evidence tokens against resume normalized text; ungrounded claims are downgraded to `UNKNOWN` with 0.0 points.
- **Backend Implementation**: `backend/app/ai/evidence_extraction_service.py:verify_evidence_tokens`.
- **Frontend Implementation**: Unverified claims highlighted with red warning indicator.
- **Database Persistence**: `evaluation_evidence.flags_json['is_hallucinated']`.
- **Authorization Requirements**: System.
- **Test Coverage**: `tests/phase5/test_evaluation_integration.py`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 5.3 Controlled Skill Normalization
- **Expected Behavior**: Maps equivalent skill synonyms while strictly preserving boundaries (`Spring` != `Spring Boot`, `C` != `C++` != `C#`).
- **Backend Implementation**: `backend/app/services/skill_normalization_service.py`.
- **Frontend Implementation**: Shows both canonical skill name and raw resume text.
- **Database Persistence**: `candidate_skills.normalized_name`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase5/test_scoring_engine.py::test_05_skills_exact_and_alias_matching`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 5.4 Deterministic Mathematical Scoring Engine (100 Pts)
- **Expected Behavior**: Pure mathematical formula in Python using approved weights; the LLM never determines candidate scores.
- **Backend Implementation**: `backend/app/services/scoring_engine.py:calculate_evaluation_scores`.
- **Frontend Implementation**: Visual score gauge with detailed point breakdown.
- **Database Persistence**: `evaluations.total_score`, `raw_score`, `normalized_score`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase5/test_scoring_engine.py::test_14_deterministic_repeated_calculation`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 5.5 Handling of Unknown & Conflicting Information
- **Expected Behavior**: Missing resume data is labeled `UNKNOWN` and normalized proportionally without imposing negative penalties.
- **Backend Implementation**: `backend/app/services/scoring_engine.py:_normalize_provisional_score`.
- **Frontend Implementation**: Gray "Unknown" badges with explanation tooltip.
- **Database Persistence**: `evaluation_evidence.evidence_status = 'UNKNOWN'`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase5/test_scoring_engine.py::test_16_unknown_data_provisional_normalization`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 5.6 Demographic Attribute Exclusion Guard
- **Expected Behavior**: Candidate profiles are stripped of demographic fields (`gender`, `age`, `date_of_birth`, etc.); rejects dirty payloads with `ProtectedAttributeViolationError`.
- **Backend Implementation**: `backend/app/ai/evidence_extraction_service.py:assert_no_protected_attributes`.
- **Frontend Implementation**: Demographic fields absent from candidate evaluation screens.
- **Database Persistence**: Demographic data never saved.
- **Authorization Requirements**: System.
- **Test Coverage**: `tests/phase8/test_responsible_ai_governance.py::test_protected_attribute_exclusion_guard`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 5.7 Multi-Attribute Deterministic Ranking
- **Expected Behavior**: Orders candidates by score descending, evidence coverage descending, experience descending, and candidate ID for deterministic tie-breaking.
- **Backend Implementation**: `backend/app/services/ranking_service.py`.
- **Frontend Implementation**: Ranked candidate list on requisition view.
- **Database Persistence**: Dynamic sorting query.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase5/test_scoring_engine.py::test_17_evidence_coverage_calculation`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 5.8 Zero Automatic Rejection Policy
- **Expected Behavior**: All candidates, including those scoring < 50, remain visible, searchable, and reviewable in the pipeline.
- **Backend Implementation**: `backend/app/services/ranking_service.py:list_ranked_evaluations`.
- **Frontend Implementation**: Unfiltered candidate view includes all score tiers.
- **Database Persistence**: `evaluations.is_current = true`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase5/test_scoring_engine.py::test_15_score_boundaries_and_clamping`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

---

### Phase 6 — Recruiter Workspace & Candidate Management

#### 6.1 Recruiter Dashboard & Live Aggregations
- **Expected Behavior**: Computes real-time counts for Active Requisitions, Candidates, Resumes Processed, Awaiting Review, and Internally Shortlisted.
- **Backend Implementation**: `backend/app/services/dashboard_service.py`.
- **Frontend Implementation**: `frontend/app/dashboard/page.tsx`.
- **Database Persistence**: Aggregated live queries.
- **Authorization Requirements**: `recruiter`, `delivery_head`, `admin`.
- **Test Coverage**: `tests/phase6/test_dashboard_metrics.py::test_dashboard_metrics_aggregation`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 6.2 Processing Health Telemetry
- **Expected Behavior**: Real-time document ingestion telemetry tracking success rate %, total files processed, parsing errors, and worker queue status.
- **Backend Implementation**: `backend/app/services/dashboard_service.py:get_processing_health`.
- **Frontend Implementation**: Health telemetry card on dashboard.
- **Database Persistence**: Query across `resumes` and `resume_processing_jobs`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase6/test_dashboard_metrics.py::test_dashboard_full_and_isolation`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 6.3 Recent Activity Chronological Feed
- **Expected Behavior**: Tracks requisition creation, uploads, completed evaluations, reviews, and notes.
- **Backend Implementation**: `backend/app/services/dashboard_service.py:get_recent_activity`.
- **Frontend Implementation**: Activity feed stream on dashboard.
- **Database Persistence**: Real-time union query across audit and activity entities.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase6/test_dashboard_metrics.py::test_dashboard_activity_feed`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 6.4 Candidate Global Search
- **Expected Behavior**: Searches across candidate name, email, skills, past job titles, and past employers.
- **Backend Implementation**: `backend/app/repositories/candidate_repository.py:search_candidates`.
- **Frontend Implementation**: Global search bar in `frontend/app/candidates/page.tsx`.
- **Database Persistence**: Indexed PostgreSQL search query.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase6/test_candidate_search_and_filtering.py::test_candidate_search_and_filtering`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 6.5 Multi-Attribute Filtering & Deterministic Sorting
- **Expected Behavior**: Filters by Requisition, Evaluation Status, Review Decision, Score Range, Skills, Experience, Location, and Notice Period.
- **Backend Implementation**: `backend/app/repositories/candidate_repository.py`.
- **Frontend Implementation**: Filter sidebar and sort dropdown on candidates page.
- **Database Persistence**: Dynamic SQL filtering.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase6/test_candidate_search_and_filtering.py::test_candidate_search_and_filtering`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 6.6 Server-Side Pagination
- **Expected Behavior**: Server-side pagination with configurable page size (10, 25, 50) and total count.
- **Backend Implementation**: `backend/app/api/v1/endpoints/candidates.py:list_candidates`.
- **Frontend Implementation**: Pagination controls with Next/Previous buttons.
- **Database Persistence**: SQL `OFFSET` and `LIMIT`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase6/test_candidate_search_and_filtering.py`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 6.7 Candidate Dedicated Profile Workspace
- **Expected Behavior**: Detailed profile with contact info, employment timeline, education, skills, resume download, and evaluation scorecard.
- **Backend Implementation**: `backend/app/api/v1/endpoints/candidates.py:get_candidate`.
- **Frontend Implementation**: `frontend/app/candidates/[id]/page.tsx`.
- **Database Persistence**: Eagerly loaded candidate relationships.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase6/test_candidate_profile_and_eval_history.py::test_candidate_profile_and_history`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 6.8 Longitudinal Evaluation History
- **Expected Behavior**: Preserves historical evaluation scorecards across multiple scorecard versions and requisitions.
- **Backend Implementation**: `backend/app/api/v1/endpoints/candidates.py:get_candidate_evaluation_history`.
- **Frontend Implementation**: Multi-version evaluation tab on candidate profile.
- **Database Persistence**: `evaluations` table with version tracking.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase6/test_candidate_profile_and_eval_history.py`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 6.9 Confidential Recruiter Notes Subsystem
- **Expected Behavior**: Recruiter private internal notes with author-based edit/delete permissions, strictly hidden from client users.
- **Backend Implementation**: `backend/app/services/candidate_note_service.py`.
- **Frontend Implementation**: Recruiter notes tab and quick-note modal.
- **Database Persistence**: `candidate_notes` table.
- **Authorization Requirements**: `recruiter`, `delivery_head` (Client HM blocked with 403).
- **Test Coverage**: `tests/phase6/test_candidate_notes.py::test_candidate_note_crud`, `test_candidate_note_permissions_and_privacy`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

---

### Phase 7 — Client Portal, Masked Sharing & Hiring Pipeline

#### 7.1 Client Portal Authentication & Dashboard
- **Expected Behavior**: Client hiring managers log in to a dedicated portal (`/client`) showing only their shared requisitions and submissions.
- **Backend Implementation**: `backend/app/api/v1/endpoints/client_portal.py:get_client_dashboard`.
- **Frontend Implementation**: `frontend/app/client/page.tsx`.
- **Database Persistence**: Tenant-scoped query filtering by `client_organization_id`.
- **Authorization Requirements**: `client_hiring_manager`.
- **Test Coverage**: `tests/phase7/test_client_auth_and_isolation.py::test_client_portal_access_and_tenant_isolation`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 7.2 Server-Side Candidate Contact Masking (Zero-PII)
- **Expected Behavior**: Candidate names are masked to `Candidate CND-XXXXX`, emails/phones/addresses stripped, and raw resumes withheld.
- **Backend Implementation**: `backend/app/services/candidate_masking_service.py`.
- **Frontend Implementation**: Client candidate profile view (`frontend/app/client/submissions/[id]/page.tsx`).
- **Database Persistence**: Computed server-side before response serialization.
- **Authorization Requirements**: Applied to all client endpoints.
- **Test Coverage**: `tests/phase7/test_candidate_masking_and_privacy.py::test_candidate_masking_and_privacy_guarantees`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 7.3 Recruiter Candidate Submission Workflow
- **Expected Behavior**: Recruiters submit evaluated candidates to client organizations with optional recommendation notes.
- **Backend Implementation**: `backend/app/services/submission_service.py:create_submission`.
- **Frontend Implementation**: "Submit to Client" modal on candidate profile.
- **Database Persistence**: `submissions` table.
- **Authorization Requirements**: `recruiter`, `delivery_head`.
- **Test Coverage**: `tests/phase7/test_candidate_submission.py::test_candidate_submission_workflow_and_validation`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 7.4 Client Decisions (Shortlist & Reject)
- **Expected Behavior**: Client hiring managers record Shortlist or Reject decisions, updating submission stage and appending audit log.
- **Backend Implementation**: `backend/app/services/submission_service.py:record_client_decision`.
- **Frontend Implementation**: Shortlist and Reject action buttons on submission detail view.
- **Database Persistence**: `submissions.status`, `pipeline_records` table.
- **Authorization Requirements**: `client_hiring_manager`.
- **Test Coverage**: `tests/phase7/test_client_decisions_and_pipeline.py::test_client_decisions_pipeline_transitions_and_requests`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 7.5 Client Interview & Info Requests
- **Expected Behavior**: Client can request an interview or request additional information, which appears on recruiter tracker.
- **Backend Implementation**: `backend/app/services/submission_service.py:create_client_request`.
- **Frontend Implementation**: "Request Interview" and "Request Info" dialogs in client portal.
- **Database Persistence**: `client_requests` table.
- **Authorization Requirements**: `client_hiring_manager`.
- **Test Coverage**: `tests/phase7/test_client_decisions_and_pipeline.py`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 7.6 Recruiter Inquiry Response Workflow
- **Expected Behavior**: Recruiter reviews client requests and responds with scheduling details or candidate clarifications.
- **Backend Implementation**: `backend/app/services/submission_service.py:respond_to_client_request`.
- **Frontend Implementation**: Inquiry resolution panel in recruiter submissions view.
- **Database Persistence**: `client_requests.recruiter_response`, `client_requests.status = 'RESOLVED'`.
- **Authorization Requirements**: `recruiter`.
- **Test Coverage**: `tests/phase7/test_recruiter_client_interaction.py::test_recruiter_client_interaction_pipeline_flow`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 7.7 9-Stage Interactive Kanban Pipeline
- **Expected Behavior**: Full visual pipeline board tracking candidates across 9 distinct stages with drag-and-drop or stage selector.
- **Backend Implementation**: `backend/app/api/v1/endpoints/recruiter_submissions.py:get_recruiter_pipeline_board`.
- **Frontend Implementation**: `frontend/app/pipeline/page.tsx`.
- **Database Persistence**: `submissions.current_stage`.
- **Authorization Requirements**: `recruiter`, `delivery_head`, `admin`.
- **Test Coverage**: `tests/phase7/test_phase7_end_to_end.py`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 7.8 Delivery Head Pipeline Telemetry & Conversion Funnel
- **Expected Behavior**: Computes Shortlist Rate %, Interview Rate %, and Hire Rate % across all agency submissions.
- **Backend Implementation**: `backend/app/services/delivery_head_service.py`.
- **Frontend Implementation**: `frontend/app/delivery/page.tsx`.
- **Database Persistence**: Organization-scoped aggregation query.
- **Authorization Requirements**: `delivery_head`, `admin`.
- **Test Coverage**: `tests/phase7/test_delivery_head_and_pipeline_board.py::test_delivery_head_pipeline_summary_and_tenant_boundary`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 7.9 Cross-Client Tenant Isolation
- **Expected Behavior**: Client A cannot see requisitions, submissions, or candidate profiles belonging to Client B.
- **Backend Implementation**: Strict `client_organization_id` tenancy checks.
- **Frontend Implementation**: Scoped client routing.
- **Database Persistence**: Tenant foreign keys.
- **Authorization Requirements**: Client user.
- **Test Coverage**: `tests/phase7/test_client_auth_and_isolation.py`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

---

### Phase 8 — Privacy, Consent, Deletion & Responsible AI

#### 8.1 Candidate Consent Lifecycle & Hashed Tokens
- **Expected Behavior**: Expiring single-use URL-safe tokens stored as SHA-256 hashes (`token_hash`) at rest with 14-day validity.
- **Backend Implementation**: `backend/app/services/consent_service.py`.
- **Frontend Implementation**: `frontend/app/privacy/consent/page.tsx`, `frontend/app/public/consent/[token]/page.tsx`.
- **Database Persistence**: `consent_records` table.
- **Authorization Requirements**: Recruiter initiates; public candidate resolves.
- **Test Coverage**: `tests/phase8/test_candidate_consent.py::test_consent_request_lifecycle`, `test_consent_token_expiry`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 8.2 Real-Time Consent Withdrawal
- **Expected Behavior**: Recruiter or candidate can withdraw consent at any time, immediately transitioning status to `WITHDRAWN`.
- **Backend Implementation**: `backend/app/services/consent_service.py:withdraw_candidate_consent`.
- **Frontend Implementation**: "Withdraw Consent" action modal on candidate profile and consent table.
- **Database Persistence**: `candidates.consent_status = 'WITHDRAWN'`, `consent_records.withdrawn_at`.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase8/test_candidate_consent.py::test_consent_request_lifecycle`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 8.3 Consent-Aware Processing Gates
- **Expected Behavior**: Blocks AI evaluation and client submissions if candidate consent is `WITHDRAWN`, `DECLINED`, or `PENDING`.
- **Backend Implementation**: `backend/app/services/evaluation_service.py`, `submission_service.py`.
- **Frontend Implementation**: Action buttons disabled with explanatory tooltip when consent is missing or withdrawn.
- **Database Persistence**: Emits `PROCESSING_BLOCKED_CONSENT` and `SUBMISSION_BLOCKED_CONSENT` audit records.
- **Authorization Requirements**: System gate.
- **Test Coverage**: `tests/phase8/test_consent_aware_processing.py::test_evaluation_blocked_when_consent_withdrawn`, `test_client_submission_blocked_when_consent_withdrawn`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 8.4 Personal Data Subject Access & Portable JSON Export
- **Expected Behavior**: Generates complete portable JSON export of candidate personal data, strictly excluding sensitive internal secrets, storage paths, and proprietary formulas.
- **Backend Implementation**: `backend/app/services/data_export_service.py`.
- **Frontend Implementation**: `frontend/app/privacy/data-requests/page.tsx`.
- **Database Persistence**: `data_requests` table and private export file on disk.
- **Authorization Requirements**: Recruiter.
- **Test Coverage**: `tests/phase8/test_data_access_and_export.py::test_data_access_and_export_lifecycle`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 8.5 Controlled Right to be Forgotten (Erasure Lifecycle)
- **Expected Behavior**: Multi-step erasure (`REQUESTED` → `UNDER_REVIEW` → `APPROVED` → `COMPLETED`) with physical storage file purge and irreversible database PII scrubbing.
- **Backend Implementation**: `backend/app/services/deletion_service.py`.
- **Frontend Implementation**: `frontend/app/privacy/deletions/page.tsx`.
- **Database Persistence**: `deletion_requests` table, candidate PII set to `[DELETED]`.
- **Authorization Requirements**: Recruiter requests; Delivery Head approves.
- **Test Coverage**: `tests/phase8/test_candidate_deletion.py::test_candidate_deletion_lifecycle_and_scrubbing`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 8.6 Legal Hold Protection
- **Expected Behavior**: Active legal holds (`is_legal_hold = true`) block erasure execution with HTTP 400 until compliance inquiries conclude.
- **Backend Implementation**: `backend/app/services/deletion_service.py:review_deletion_request`.
- **Frontend Implementation**: Legal hold toggle in deletion review modal.
- **Database Persistence**: `deletion_requests.is_legal_hold`, `legal_hold_reason`.
- **Authorization Requirements**: Delivery Head.
- **Test Coverage**: `tests/phase8/test_candidate_deletion.py::test_candidate_deletion_lifecycle_and_scrubbing`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 8.7 Centralized Append-Only Audit Logging
- **Expected Behavior**: Unified audit logging across all state-changing operations with recursive payload sanitization for passwords, tokens, API keys, and raw text.
- **Backend Implementation**: `backend/app/services/audit_service.py`.
- **Frontend Implementation**: `frontend/app/privacy/audit/page.tsx`.
- **Database Persistence**: `audit_logs` table (INSERT-only).
- **Authorization Requirements**: `delivery_head`, `admin`.
- **Test Coverage**: `tests/phase8/test_audit_logging.py::test_sanitize_payload`, `test_audit_logging_and_querying`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

#### 8.8 Responsible AI Telemetry & Governance Dashboard
- **Expected Behavior**: Aggregates evaluation score distributions, reviewer decisions, evidence coverage rates, and statutory non-discrimination disclosures.
- **Backend Implementation**: `backend/app/services/governance_service.py`.
- **Frontend Implementation**: `frontend/app/governance/page.tsx`.
- **Database Persistence**: Aggregated live queries.
- **Authorization Requirements**: Recruiter, Delivery Head.
- **Test Coverage**: `tests/phase8/test_responsible_ai_governance.py::test_governance_and_ai_metrics_endpoints`.
- **Verification Result**: `VERIFIED`
- **Identified Defects**: None.
- **Fix Applied**: N/A.

