# Implementation Plan: ShortlistAI

## Overview

This plan converts the ShortlistAI design into incremental coding tasks organized by development phase. Each task builds on the previous, ending with all components wired together. The implementation language is **Python 3.11+ (FastAPI/SQLAlchemy)** for the backend and **TypeScript (Next.js 14 App Router)** for the frontend, as specified in the design document.

Tasks marked with `*` are optional (test sub-tasks) and can be skipped for a faster MVP. All other tasks are required.

---

## Tasks

---

### Phase 2: Backend Foundation

- [ ] 1. Set up monorepo structure and Docker development environment
  - Create the root directory layout: `frontend/`, `backend/`, `tests/`, `docs/`, `scripts/`
  - Write `docker-compose.yml` defining services: `postgres` (15), `redis`, `backend` (FastAPI), `worker` (ARQ)
  - Write `backend/pyproject.toml` with all runtime dependencies (fastapi, uvicorn, sqlalchemy[asyncio], alembic, asyncpg, pydantic[email], redis, arq, argon2-cffi, python-jose, PyMuPDF, python-docx, hypothesis)
  - Write `frontend/package.json` bootstrapping Next.js 14 App Router with TypeScript, Tailwind CSS, shadcn/ui
  - Create `.env.example` listing all required environment variables (`DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `OPENAI_API_KEY`, `LLM_PROVIDER`, `OPENAI_MODEL`, `FILE_STORAGE_PATH`, `FRONTEND_URL`)
  - _Requirements: 21.4, 22.1_

- [ ] 2. Implement SQLAlchemy models and initial Alembic migration
  - [ ] 2.1 Define all 14 SQLAlchemy async models in their respective module `models.py` files
    - Implement `BaseModel` in `core/base_model.py` with UUID PK, `created_at`, `updated_at`
    - Implement models: `User`, `Organization`, `OrganizationMembership`, `Requisition`, `Scorecard`, `ScorecardCriterion`, `Candidate`, `Resume`, `UploadBatch`, `Evaluation`, `EvaluationEvidence`, `Submission`, `PipelineRecord`, `AuditLog`, `ConsentRecord`
    - Add all FK constraints, unique constraints, and index definitions per the ER diagram
    - Add `version` (optimistic lock) column to `Requisition` and `Scorecard`
    - _Requirements: 27.1, 27.2, 27.3, 27.5_

  - [ ]* 2.2 Write unit tests for model definitions
    - Assert all FK relationships are declared
    - Assert unique constraints exist on `users.email`, `scorecards` (one active per requisition)
    - _Requirements: 27.1, 27.2_

  - [ ] 2.3 Generate and apply initial Alembic migration
    - Configure `alembic.ini` and `env.py` for async SQLAlchemy
    - Generate `initial_schema` migration from model metadata
    - Verify migration applies cleanly on a fresh PostgreSQL 15 instance via `docker-compose`
    - _Requirements: 27.1, 27.4_

- [ ] 3. Implement FastAPI application skeleton and middleware stack
  - [ ] 3.1 Create `backend/app/main.py` FastAPI application with middleware
    - Register CORS middleware (restrict to `FRONTEND_URL`)
    - Register security headers middleware applying all five required headers: `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`, `Referrer-Policy`
    - Register request `trace_id` injection middleware
    - Mount `/api/v1/` router prefix
    - Implement `GET /health` and `GET /health/ready` endpoints
    - _Requirements: 21.6, 21.7, 22.1, 22.4_

  - [ ] 3.2 Implement core dependency injection in `core/dependencies.py`
    - Implement `get_db()` yielding an async SQLAlchemy session per request
    - Implement `get_current_user(token)` decoding and validating JWT, returning `CurrentUser`
    - Implement `require_role(*roles)` raising `HTTP 403` if the authenticated user's role is not in the allowed set, and writing an `UNAUTHORIZED_ACCESS_ATTEMPT` audit entry
    - _Requirements: 1.7, 3.9_

  - [ ]* 3.3 Write integration tests for middleware and health endpoints
    - Assert all five security headers are present on `/health` response
    - Assert `GET /health/ready` returns 200 when services are up
    - _Requirements: 21.6_

- [ ] 4. Implement authentication module
  - [ ] 4.1 Implement password hashing in `auth/hashing.py`
    - Implement `PasswordHasher` using Argon2 (primary) with bcrypt fallback
    - `hash(plain)` → hashed string; `verify(plain, hashed)` → bool
    - Ensure no plaintext passwords are ever stored
    - _Requirements: 1.1_

  - [ ] 4.2 Implement JWT management in `auth/jwt.py`
    - Implement `JWTManager.issue_access_token(user)` → RS256 signed JWT, 15-minute expiry
    - Implement `JWTManager.issue_refresh_token(user)` → stores hashed token ID in Redis with 7-day TTL
    - Implement `JWTManager.decode_access_token(token)` → `TokenPayload`; raise `HTTP 401` on invalid/expired
    - Implement `JWTManager.revoke_refresh_token(token_id)` → DEL from Redis
    - Token signing key loaded from env variable, never from source code
    - _Requirements: 1.2, 1.4, 1.5, 1.10_

  - [ ] 4.3 Implement Redis-backed rate limiter in `auth/rate_limiter.py`
    - Implement sliding-window `check_and_increment(key, limit, window_seconds)` → `RateLimitResult`
    - Implement `is_locked(account_id)` checking the account lockout key
    - Apply limits: login endpoint 10 req/min/IP; auth failures 10/15 min → lock; uploads 5/min/user; others 100/min/user
    - _Requirements: 1.9, 21.3_

  - [ ] 4.4 Implement auth API endpoints in `api/v1/auth.py`
    - `POST /auth/login` — verify credentials, check lock status, issue access + refresh tokens, audit `USER_LOGIN`
    - `POST /auth/refresh` — validate single-use refresh token from Redis, issue new pair, audit `TOKEN_REFRESH`
    - `POST /auth/logout` — revoke refresh token, audit `USER_LOGOUT`
    - Return the **same** error body for wrong email and wrong password (non-disclosure)
    - _Requirements: 1.2, 1.3, 1.6, 1.8_

  - [ ]* 4.5 Write property test: auth error non-disclosure (Property 10)
    - **Property 10: Authentication Error Non-Disclosure**
    - For any login attempt with a non-existent email and a login attempt with a wrong password, assert both response bodies are identical
    - **Validates: Requirements 1.3**

  - [ ]* 4.6 Write integration tests for auth endpoints
    - Test: valid credentials → 200 with tokens
    - Test: wrong password → 401 with uniform message
    - Test: non-existent email → 401 with uniform message (same body as wrong password)
    - Test: expired access token → 401 on protected endpoint
    - Test: used refresh token rejected (single-use)
    - Test: logout revokes refresh token
    - Test: 10 failed attempts → account locked → 11th attempt rejected even with correct credentials
    - _Requirements: 1.2, 1.3, 1.5, 1.8, 1.9_

- [ ] 5. Implement organization and multi-tenant isolation
  - [ ] 5.1 Implement organization models, schemas, repository, and service
    - Implement `OrganizationRepository` with all queries gated on `org_id`
    - Implement `assert_org_member(user_id, org_id, session)` — raise `HTTP 404` on failure and write `CROSS_ORG_ACCESS_ATTEMPT` audit entry (404 preferred over 403 to avoid existence disclosure)
    - Implement `OrganizationMembership` CRUD
    - _Requirements: 2.1, 2.2, 2.3, 2.6_

  - [ ]* 5.2 Write property test: multi-tenant isolation (Property 8)
    - **Property 8: Multi-Tenant Isolation**
    - For any two orgs A and B, a user from org A's API responses must never contain records owned by org B
    - **Validates: Requirements 2.2, 2.3**

- [ ] 6. Implement RBAC and audit logger
  - [ ] 6.1 Implement RBAC in `auth/rbac.py`
    - Define role constants: `RECRUITER`, `CLIENT_HIRING_MANAGER`, `DELIVERY_HEAD`
    - Wire `require_role` dependency to check `CurrentUser.role` against allowed roles
    - Return `HTTP 403` and emit `UNAUTHORIZED_ACCESS_ATTEMPT` audit entry on violation
    - _Requirements: 3.1, 3.9_

  - [ ] 6.2 Implement `AuditLogger` in `audit/logger.py`
    - Implement `AuditLogger.log(event_type, actor_user_id, actor_org_id, resource_type, resource_id, payload, session)` as an async method
    - The INSERT must use the **same** `AsyncSession` transaction as the caller
    - If the INSERT raises, propagate the exception so the caller's transaction rolls back
    - Grant the application DB user `INSERT`-only on `audit_logs` (document this in migration comments)
    - _Requirements: 18.1, 18.2, 18.3, 18.6_

  - [ ]* 6.3 Write property test: audit log atomicity (Property 11)
    - **Property 11: Audit Log Atomicity**
    - Inject a failure into the audit log write for any auditable operation; assert the operation fails and the resource remains in its pre-operation state
    - **Validates: Requirements 18.6**

  - [ ]* 6.4 Write property test: RBAC enforcement (Property 9)
    - **Property 9: RBAC Enforcement**
    - For any (user_role, restricted_endpoint) pair where the role is disallowed, assert HTTP 403 is always returned and an `UNAUTHORIZED_ACCESS_ATTEMPT` audit entry is always created
    - **Validates: Requirements 3.9**

- [ ] 7. Phase 2 checkpoint — Ensure all tests pass
  - Ensure Docker Compose starts all services cleanly
  - Ensure initial Alembic migration applies on a fresh database
  - Ensure all auth, RBAC, audit, and org isolation tests pass
  - Ask the user if questions arise before proceeding to Phase 3

---

### Phase 3: JD Intelligence and Scorecard

- [ ] 8. Implement LLM provider abstraction
  - [ ] 8.1 Define `LLMProvider` protocol in `ai/provider.py`
    - Define `LLMProvider` as a `typing.Protocol` with methods: `extract_jd`, `extract_resume`, `extract_evidence`
    - Each method accepts `(prompt: str, output_schema: dict, max_tokens: int)` → `dict`
    - _Requirements: 20.1, 20.2_

  - [ ] 8.2 Implement `OpenAIProvider` in `ai/openai_provider.py`
    - Load `OPENAI_API_KEY` and `OPENAI_MODEL` from config; never hardcode
    - Implement retry policy: up to 3 attempts, exponential backoff (1s, 2s, 4s) for `RateLimitError` and `NetworkError`; fail immediately on JSON parse error, Pydantic validation failure, `AuthenticationError`
    - Log provider name, model version, service name, prompt tokens, completion tokens to the audit log on every call
    - Enforce per-service max token budgets from config: JD=4000/1000, Resume=8000/2000, Evidence=10000/3000
    - _Requirements: 20.3, 20.4, 20.5, 20.6_

  - [ ] 8.3 Implement `ProviderFactory` in `ai/provider_factory.py`
    - Load active provider class from `Config.LLM_PROVIDER` string key; raise `ValueError` for unknown keys
    - Ensure service modules import only via the factory, not from `openai_provider` directly
    - _Requirements: 20.3_

  - [ ]* 8.4 Write contract tests for LLMProvider interface
    - Assert `OpenAIProvider` satisfies the `LLMProvider` protocol (duck-type check)
    - Assert all returned confidence values are in [0.0, 1.0]
    - Assert `LLMExtractionError` is raised (not propagated raw) on provider failure
    - _Requirements: 20.1, 28.6_

- [ ] 9. Implement JD Extraction Service
  - [ ] 9.1 Implement `JDExtractionService` in `ai/jd_extraction.py`
    - Define `FieldWithConfidence[T]` and `JDExtractionResult` Pydantic schemas in `ai/schemas.py`
    - Implement `extract(jd_text: str)` → `JDExtractionResult`
    - On field not found: `value = None`, `confidence = 0.0` — never fabricate
    - Post-extraction: validate each must-have skill is a substring of the original `jd_text` (anti-inference check)
    - Store raw LLM response JSON in result for audit
    - _Requirements: 5.1, 5.2, 5.3, 5.7, 5.8_

  - [ ]* 9.2 Write property test: extraction confidence score range (Property 7, JD side)
    - **Property 7: Extraction Confidence Score Range**
    - For any JD extraction result, all confidence scores are in [0.0, 1.0]; any null field has confidence exactly 0.0
    - **Validates: Requirements 5.2, 5.3**

  - [ ]* 9.3 Write unit tests for JD extraction behavior
    - Test: field present in JD → extracted with confidence > 0.0
    - Test: field absent → null value + confidence 0.0
    - Test: skill not in JD text → excluded from must-have list (anti-inference)
    - Test: LLM failure → `LLMExtractionError` raised; pre-populated scorecard editor receives empty result
    - Test: network error retried 3×; schema validation error not retried
    - _Requirements: 5.1, 5.3, 5.8, 20.5_

- [ ] 10. Implement scorecard management
  - [ ] 10.1 Implement scorecard models, schemas, repository, and service
    - Define `Scorecard` and `ScorecardCriterion` SQLAlchemy models (already in Task 2.1)
    - Implement `ScorecardRepository` with org-gated queries and version management
    - Implement `ScorecardService.activate(scorecard_id)` — validates sum of weights == 100; raises `HTTP 400` if not
    - Implement `ScorecardService.reset_to_draft(scorecard_id)` — creates a new draft version, marks prior version as archived (preserves it for historical FK references)
    - Emit audit entries for create, update, activate
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_

  - [ ] 10.2 Implement scorecard API endpoints in `api/v1/scorecards.py`
    - `GET /requisitions/{id}/scorecards` — list scorecard versions (Recruiter)
    - `POST /requisitions/{id}/scorecards` — create new scorecard draft
    - `PUT /scorecards/{id}` — update criteria and weights (draft only)
    - `POST /scorecards/{id}/activate` — validate weights sum to 100, set active
    - `POST /scorecards/{id}/reset` — create new draft from active version
    - _Requirements: 6.1, 6.3, 6.6_

  - [ ] 10.3 Implement JD extraction API endpoint and scorecard pre-population
    - `POST /requisitions/{id}/extract-jd` → call `JDExtractionService`, return `JDExtractionResult`
    - On success: pre-populate scorecard editor with extracted criteria via response payload
    - On LLM failure: return error, scorecard editor receives empty pre-population (no crash)
    - _Requirements: 5.4, 5.5, 5.6_

  - [ ]* 10.4 Write integration tests for scorecard API
    - Test: weight sum < 100 → activation blocked with HTTP 400
    - Test: weight sum = 100 → activation succeeds
    - Test: prior evaluation records still reference old scorecard version after version change
    - Test: structural changes to active scorecard blocked; reset creates new draft
    - _Requirements: 6.3, 6.6, 6.7_

- [ ] 11. Phase 3 checkpoint — Ensure all tests pass
  - Verify JD extraction returns structured result from a sample JD in < 30 seconds
  - Verify LLM provider contract tests pass
  - Verify scorecard versioning tests pass
  - Ask the user if questions arise before proceeding to Phase 4

---

### Phase 4: Resume Ingestion and Parsing

- [ ] 12. Implement file upload validation and storage
  - [ ] 12.1 Implement file validator in `resumes/validator.py`
    - Validate in sequence: extension (`.pdf`/`.docx` only), MIME type header, magic bytes (`%PDF-` for PDF; `PK\x03\x04` for DOCX), size (≤ 10 MB per file), malware scan (ClamAV)
    - Fail-secure on ClamAV unavailability: treat as scan failure, reject the file
    - On malware detection: quarantine file, reject upload, queue recruiter notification, write `MALWARE_DETECTED` audit entry
    - _Requirements: 7.2, 21.1, 21.2, 21.8, 21.9_

  - [ ] 12.2 Implement storage backend in `resumes/storage.py`
    - Define `StorageBackend` protocol with `store(file_bytes, filename) → str` and `retrieve(path) → bytes`
    - Implement `LocalFSBackend`: store files with UUID-based filenames (never original name) in a non-web-accessible directory; construct paths using `pathlib.Path`, not string interpolation
    - _Requirements: 7.9, 21.1_

  - [ ] 12.3 Implement upload batch API and file ingestion in `api/v1/resumes.py`
    - `POST /requisitions/{id}/upload-batch` — accept multipart upload, validate each file, create `UploadBatch` record, enqueue one ARQ job per valid file, return `202 { batch_id }`
    - Enforce max 500 files per batch; enforce 1 GB total batch size
    - Compute SHA-256 hash per file; skip enqueueing if same hash already exists in `resumes` table (idempotency)
    - Write `RESUME_UPLOAD_INITIATED` audit entry per batch
    - Create `ConsentRecord` for each candidate at upload time (legal basis = uploaded_by_recruiter)
    - `GET /upload-batches/{id}/status` — return `{ processed, failed, duplicates, total, status }` per file
    - _Requirements: 7.1, 7.3, 7.4, 7.7, 19.1, 23.2, 23.3, 23.5_

  - [ ]* 12.4 Write integration tests for file upload validation
    - Test: valid PDF → accepted
    - Test: valid DOCX → accepted
    - Test: wrong extension → rejected
    - Test: MIME type mismatch → rejected
    - Test: magic bytes mismatch → rejected
    - Test: file > 10 MB → rejected (413)
    - Test: EICAR test string → quarantined, audit event written
    - Test: same content hash in same batch → single job queued (dedup)
    - _Requirements: 7.2, 21.1, 21.2, 23.5_

- [ ] 13. Implement background job pipeline and document parsing
  - [ ] 13.1 Implement ARQ worker setup in `jobs/worker.py`
    - Define `WorkerSettings` with Redis URL, `max_jobs=10`, job functions list, `on_startup`/`on_shutdown` hooks
    - Implement graceful shutdown: listen for `SIGTERM`, complete in-progress jobs before exit
    - _Requirements: 23.1, 23.6_

  - [ ] 13.2 Implement PDF and DOCX text extraction parsers
    - Implement `PDFParser.extract(file_bytes) → ParsingResult` using PyMuPDF (`fitz`)
    - Implement `DOCXParser.extract(file_bytes) → ParsingResult` using python-docx
    - `ParsingResult` contains `raw_text: str`, `word_count: int`, `success: bool`, `failure_reason: str | None`
    - _Requirements: 8.4_

  - [ ] 13.3 Implement `parse_resume_job` ARQ job in `jobs/resume_jobs.py`
    - Fetch resume file from storage
    - Route to `PDFParser` or `DOCXParser` based on MIME type
    - If `word_count < 50`: mark resume as `parsing_failure`, enqueue recruiter notification, update batch counter
    - If success: proceed to Resume Extraction Service (Phase 5 will fill this step)
    - Implement retry policy: up to 3 attempts with backoff for transient DB/LLM errors; permanent failure for corrupt file, malware, schema errors
    - Update `upload_batches` counters atomically on job completion
    - _Requirements: 7.4, 7.5, 7.8, 8.6, 23.3, 23.4_

  - [ ] 13.4 Implement duplicate detection in `candidates/service.py`
    - After parsing, check `candidates` table for records with matching `(full_name + email)` OR `(full_name + phone)` within the same org
    - On duplicate: flag resume in `pending` state, do not create new candidate record, update batch `duplicates` counter
    - On no duplicate: create/upsert `Candidate` record, update batch `processed` counter
    - _Requirements: 7.6_

  - [ ]* 13.5 Write integration tests for background job processing
    - Test: 10 resumes processed end-to-end without error
    - Test: `word_count < 50` → parsing failure, recruiter notified
    - Test: duplicate name+email → flagged, not auto-merged
    - Test: batch status updates within 5 seconds of job completion
    - Test: graceful shutdown — queued jobs remain in Redis; in-progress jobs complete
    - _Requirements: 7.4, 7.5, 7.6, 8.6, 23.6_

- [ ] 14. Phase 4 checkpoint — Ensure all tests pass
  - Verify 10 resumes upload and process without error
  - Verify invalid files are rejected per spec
  - Verify duplicate detection works correctly
  - Ask the user if questions arise before proceeding to Phase 5

---

### Phase 5: AI Evidence Extraction and Deterministic Scoring

- [ ] 15. Implement Protected Attribute Stripper
  - [ ] 15.1 Implement `ProtectedAttributeStripper` in `ai/protected_attrs.py`
    - Define `PROTECTED_ATTRIBUTE_FIELDS: frozenset` = `{name, gender, age, date_of_birth, photograph, marital_status, ethnicity, nationality}`
    - Implement `strip(profile: dict) → dict` — remove all keys matching the protected set (case-insensitive); leave all other fields unchanged
    - The stripper must produce a `clean_profile` with zero PA field names present
    - _Requirements: 8.5, 16.1, 16.2_

  - [ ]* 15.2 Write property test: PA stripping (Property 6)
    - **Property 6: Protected Attribute Stripping**
    - For any candidate profile dict with any combination of PA fields, `strip()` output contains none of the PA field names, and all non-PA fields are present and unchanged
    - **Validates: Requirements 8.5, 16.2**

- [ ] 16. Implement Resume Extraction Service
  - [ ] 16.1 Implement `ResumeExtractionService` in `ai/resume_extraction.py`
    - Define `CandidateProfileSchema` in `ai/schemas.py` with `FieldWithConfidence` per field, `employment_history`, `education`
    - Implement `extract(raw_text: str)` → `CandidateProfileSchema`; on `word_count < 50` before calling LLM, raise `ParsingFailureError`
    - On field not extractable: `value = None`, `confidence = 0.0` — never fabricate
    - Store raw LLM response and structured profile separately in `resumes` table
    - _Requirements: 8.1, 8.2, 8.3, 8.7, 8.8_

  - [ ]* 16.2 Write property test: extraction confidence score range (Property 7, resume side)
    - **Property 7: Extraction Confidence Score Range**
    - For any resume extraction result, all confidence scores in [0.0, 1.0]; any null field has confidence exactly 0.0
    - **Validates: Requirements 8.2, 8.3**

  - [ ] 16.3 Wire Resume Extraction Service into `parse_resume_job`
    - After successful text extraction, call `ResumeExtractionService.extract(raw_text)`
    - Store resulting `CandidateProfileSchema` in `candidates.parsed_profile_json` (full profile including PAs, for Recruiter display)
    - Mark `resume.status = "parsed"` on success; `"extraction_failed"` on LLM failure
    - _Requirements: 8.1, 8.8_

- [ ] 17. Implement Evidence Extraction Service
  - [ ] 17.1 Implement `EvidenceExtractionService` in `ai/evidence_extraction.py`
    - Define `EvidenceResult` and `EvidenceFlags` Pydantic schemas
    - Implement `extract(clean_profile: dict, criteria: list[ScorecardCriterion], raw_text: str)` → `list[EvidenceResult]`
    - Runtime guard: if `clean_profile` contains any PA field name → raise `ProtectedAttributeError` immediately
    - Post-extraction anti-fabrication: validate each excerpt in `source_excerpts` is present verbatim or ≥ 80% token overlap in `raw_text`; failed excerpts → downgrade criterion to `insufficient_evidence` + set flag
    - Map evidence statuses: `matched`, `not_matched`, `unknown`, `insufficient_evidence` (never default to `not_matched` for absent info)
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.7, 9.8_

  - [ ]* 17.2 Write unit tests for evidence extraction behavior
    - Test: absent information → `unknown` or `insufficient_evidence`, never `not_matched`
    - Test: fabricated excerpt fails 80% overlap check → status downgraded to `insufficient_evidence`
    - Test: PA field in `clean_profile` → `ProtectedAttributeError` raised
    - _Requirements: 9.3, 9.5_

- [ ] 18. Implement Deterministic Scoring Engine
  - [ ] 18.1 Implement `ScoringEngine.compute()` in `scoring/engine.py`
    - Define `ScoringInput`, `ScoringResult`, `CriterionScore` schemas in `scoring/schemas.py`
    - Implement pre-condition PA guard: iterate input field names; if any PA field name found → raise `ProtectedAttributeError` immediately, never return a score
    - Implement base allocation: `matched` → full weight; `not_matched` → 0; `unknown`/`insufficient_evidence` → `weight × 0.5`
    - Implement confidence penalty: `confidence < 0.5` → multiply earned points by `0.75`; set `low_confidence_flag`
    - Implement conflict handling: use lower value for numeric criteria; set `conflict_flag`
    - Implement must-have proportional formula: `(matched_count / total_must_have_count) × must_have_total_weight` — this overrides Step 1 for the must-have category
    - Clamp final total to `[0.0, 100.0]`
    - The function must be pure — no I/O, no LLM, no side effects, no randomness
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9, 10.10, 10.11, 16.3_

  - [ ]* 18.2 Write property test: score invariant (Property 1)
    - **Property 1: Scoring Engine — Score Invariant**
    - For any valid evidence list and scorecard, `total_score` is always in `[0.0, 100.0]`
    - **Validates: Requirements 10.1**

  - [ ]* 18.3 Write property test: scoring determinism (Property 2)
    - **Property 2: Scoring Engine — Determinism**
    - For any valid evidence list and scorecard, computing twice with identical inputs produces bit-for-bit identical `ScoringResult`
    - **Validates: Requirements 10.9**

  - [ ]* 18.4 Write property test: unknown/insufficient partial credit (Property 3)
    - **Property 3: Scoring Engine — Unknown/Insufficient Evidence Partial Credit**
    - For any criterion with `unknown` or `insufficient_evidence` status, awarded points are strictly > 0 and strictly < the criterion's full weight (50% before penalty, 37.5% with confidence penalty)
    - **Validates: Requirements 10.4, 10.5**

  - [ ]* 18.5 Write property test: PA guard (Property 4)
    - **Property 4: Scoring Engine — Protected Attribute Guard**
    - For any scoring input containing any PA field name, `ScoringEngine.compute()` always raises `ProtectedAttributeError` and never returns a score
    - **Validates: Requirements 10.11, 16.3**

  - [ ]* 18.6 Write property test: must-have proportional formula (Property 5)
    - **Property 5: Scoring Engine — Must-Have Proportional Formula**
    - For any scorecard with N must-have skills of total weight W, where M are matched, awarded must-have points equal exactly `(M / N) × W`
    - **Validates: Requirements 10.7**

  - [ ]* 18.7 Write concrete unit tests for scoring engine
    - Test all four evidence status allocations with known inputs
    - Test confidence penalty applied correctly (confidence < 0.5 → 75% of earned points)
    - Test conflict flag sets `conflict_flag = True` and uses minimum value
    - Test score clamped to [0, 100] for extreme inputs
    - _Requirements: 28.1_

- [ ] 19. Implement evaluation orchestration and evidence override
  - [ ] 19.1 Implement evaluation trigger and storage in `candidates/service.py`
    - Implement `trigger_evaluation(candidate_id, requisition_id, session)`:
      1. Fetch candidate profile → strip PAs via `ProtectedAttributeStripper`
      2. Fetch active scorecard
      3. Call `EvidenceExtractionService.extract(clean_profile, criteria, raw_text)`
      4. Call `ScoringEngine.compute(evidence, scorecard)`
      5. In one transaction: INSERT `Evaluation` record + INSERT `EvaluationEvidence` records + INSERT `EVALUATION_COMPLETED` audit entry
    - Store full score breakdown JSON in `evaluations.score_breakdown_json`
    - _Requirements: 9.6, 10.10, 27.4_

  - [ ] 19.2 Implement evaluation API endpoint
    - `POST /candidates/{id}/evaluate` — trigger evaluation job or run inline, return evaluation ID (Recruiter role required)
    - _Requirements: 9.1_

  - [ ] 19.3 Implement evidence override in `candidates/service.py` and `api/v1/candidates.py`
    - `POST /candidates/{id}/override-evidence` — require `reason` field (non-empty); raise `HTTP 400` if absent
    - Create new `Evaluation` version (`version` + 1, `is_current = True`); set `is_current = False` on prior version
    - Set `evaluation_evidence.is_overridden = True` on the affected criterion
    - Recompute total score from updated evidence set using `ScoringEngine.compute()`
    - Write `EVIDENCE_OVERRIDDEN` audit entry
    - _Requirements: 11.6_

  - [ ]* 19.4 Write integration tests for evaluation flow
    - Test: evaluation trigger creates evaluation + evidence records in one transaction
    - Test: override creates new evaluation version, old version retained, is_current updated
    - Test: PA fields absent from all evidence and evaluation records
    - _Requirements: 9.6, 11.6_

- [ ] 20. Phase 5 checkpoint — Ensure all tests pass
  - Verify all 15 Hypothesis property tests pass at ≥ 100 iterations each
  - Verify anti-fabrication excerpt verification works
  - Verify scoring engine ≥ 80% line coverage
  - Ask the user if questions arise before proceeding to Phase 6

---

### Phase 6: Recruiter Dashboard and Candidate Management

- [ ] 21. Set up Next.js frontend scaffold
  - [ ] 21.1 Bootstrap Next.js 14 App Router project with TypeScript and Tailwind CSS
    - Install shadcn/ui and initialize component library
    - Create `frontend/lib/api.ts` typed fetch wrapper: inject `Authorization: Bearer` header; auto-refresh access token on 401 (retry original request once); parse error envelope; export typed response types
    - Create `frontend/lib/auth.ts`: token storage, session state, logout helper
    - Create `frontend/lib/types.ts`: shared TypeScript interfaces mirroring backend Pydantic schemas
    - _Requirements: 24.3_

  - [ ] 21.2 Implement login screen
    - Render at `app/(auth)/login/page.tsx`
    - On submit: call `POST /auth/login`; store tokens; redirect to dashboard
    - Display uniform error message (do not reveal which field was wrong)
    - _Requirements: 1.3_

- [ ] 22. Implement recruiter requisition management screens
  - [ ] 22.1 Implement requisition list and create pages
    - `app/(recruiter)/requisitions/page.tsx` — SSR: fetch active requisitions for org; display paginated list ordered by created_at desc; search by keyword/status
    - `app/(recruiter)/requisitions/new/page.tsx` — form: title + JD text; on submit call `POST /requisitions`; redirect to requisition detail
    - `app/(recruiter)/requisitions/[id]/page.tsx` — requisition detail: show status, JD, action buttons (archive, extract JD, edit scorecard)
    - _Requirements: 4.1, 4.2, 4.3, 4.5, 4.6, 24.1, 24.5_

  - [ ] 22.2 Implement scorecard editor screen
    - `app/(recruiter)/requisitions/[id]/scorecard/page.tsx`
    - Display extracted criteria with confidence badges pre-populated from JD extraction result
    - Allow add/edit/reorder/delete criteria; show running weight total
    - Block activation if weight sum ≠ 100 (client-side validation + server error display)
    - Show AI extraction trigger button; display loading state during extraction
    - _Requirements: 5.4, 5.5, 6.1, 6.2, 6.3, 6.4, 6.5_

- [ ] 23. Implement bulk upload screen
  - [ ] 23.1 Implement `DropZone`, `FileStatusList`, and `BatchProgressBar` components
    - `DropZone` — accept PDF/DOCX; visual indicator for valid/invalid types; on drop call `POST /upload-batch`
    - `FileStatusList` — per-file status badge (pending, uploading, processing, parsed, failed, duplicate); hover on failed → show failure reason tooltip
    - `BatchProgressBar` — show total/success/failed/duplicate counts updating in real time
    - _Requirements: 25.1, 25.2, 25.3, 25.4_

  - [ ] 23.2 Implement upload batch polling and duplicate resolver
    - Implement `useUploadBatchPolling` hook: poll `GET /upload-batches/{id}/status` every 3 seconds; update component state; stop on `status === "completed"`
    - Implement `DuplicateResolver` modal: side-by-side comparison of existing vs new profile; three options: update existing, keep both, discard new; hold in pending state until explicit choice
    - Implement CSV download button: generate CSV of batch results (file name, status, failure reason) after completion
    - _Requirements: 7.6, 25.5, 25.6_

- [ ] 24. Implement candidate list and evaluation screens
  - [ ] 24.1 Implement candidate ranked list screen
    - `app/(recruiter)/requisitions/[id]/candidates/page.tsx` — SSR + client hydration
    - Display candidates ranked by total score descending (default); support sort by individual criterion
    - Implement filters: score range, skill keywords, location, notice period, evidence status, pipeline stage
    - Encode filter state in URL query params so navigating to a profile and back restores filters
    - Return filtered results within 3 seconds for ≤ 500 candidates
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [ ] 24.2 Implement candidate profile and evaluation screen
    - `app/(recruiter)/requisitions/[id]/candidates/[candidateId]/page.tsx` — SSR
    - Display: structured profile fields, total score badge, `ScoreBreakdownChart`, `EvidenceBreakdown` with `CriterionRow` per criterion
    - Each `CriterionRow`: status badge (matched/not_matched/unknown/insufficient_evidence), confidence indicator, low-confidence flag tooltip, conflict flag tooltip, source excerpt expander
    - Display `ResumeViewer` (extracted text or PDF render)
    - Display PA fields labeled "Excluded from scoring"
    - Render within 2 seconds of navigation
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.7, 16.6, 26.1, 26.2, 26.3, 26.4, 26.5, 26.6_

  - [ ] 24.3 Implement evidence override panel and recruiter notes
    - `OverridePanel` component (Recruiter role only): select criterion, enter mandatory reason, submit; disable submit if reason is empty
    - `RecruiterNotesList` + `NoteEditor`: add free-text notes per candidate per requisition; attribute to authoring recruiter; persist via `POST /candidates/{id}/notes`
    - _Requirements: 11.5, 11.6_

- [ ] 25. Implement recruiter dashboard
  - `app/(recruiter)/dashboard/page.tsx` — SSR
  - KPI cards: active requisition count, total candidates, candidates per pipeline stage (aggregated)
  - Recent activity feed
  - Requisition grid with click-through to detail page
  - All data-heavy sections show loading skeleton states during API calls
  - _Requirements: 24.1, 24.2, 24.5, 24.6_

- [ ] 26. Phase 6 checkpoint — Ensure all tests pass
  - Run Playwright E2E: login, create requisition, upload resume, view evaluation
  - Verify candidate list returns within 3 seconds for 500 candidates
  - Verify all screens show loading skeleton states during API calls
  - Ask the user if questions arise before proceeding to Phase 7

---

### Phase 7: Client Portal and Hiring Pipeline

- [ ] 27. Implement shortlisting, submissions, and contact masking
  - [ ] 27.1 Implement `ContactMasker` and `ProfileViewGate` in `submissions/service.py`
    - `ContactMasker.mask(profile)` → sets `email`, `phone`, `address` to `None`; applied at service layer before any client-org response
    - `ProfileViewGate.assert_viewed(recruiter_id, candidate_id, requisition_id, session)` → query audit log for `CANDIDATE_PROFILE_VIEWED` event; raise `HTTP 403 ForbiddenError` if not found
    - Write `CANDIDATE_PROFILE_VIEWED` audit entry when Recruiter fetches `GET /candidates/{id}` (wired in candidates API)
    - _Requirements: 13.2, 13.4_

  - [ ]* 27.2 Write property test: submission requires profile view (Property 15)
    - **Property 15: Submission Requires Profile View**
    - For any candidate with no `CANDIDATE_PROFILE_VIEWED` audit entry for the submitting recruiter in that requisition, submission always rejected
    - **Validates: Requirements 13.2**

  - [ ] 27.3 Implement submission API endpoints in `api/v1/submissions.py`
    - `POST /requisitions/{id}/submissions` — accept `candidate_ids: list[UUID]` (max 50); reject with `HTTP 400` if > 50; call `ProfileViewGate.assert_viewed` per candidate before creating records; apply `ContactMasker`; create `Submission` records; notify client HM; write `SUBMISSION_CREATED` audit entries
    - `DELETE /submissions/{id}` — withdrawal (Recruiter only, before any client action); revoke client access; write `SUBMISSION_WITHDRAWN` audit entry
    - _Requirements: 13.1, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8_

  - [ ]* 27.4 Write property test: bulk submission batch size (Property 12)
    - **Property 12: Bulk Submission Batch Size Invariant**
    - Any submission with > 50 candidate IDs → always rejected with HTTP 400; ≤ 50 → always accepted (given other preconditions met)
    - **Validates: Requirements 13.8**

- [ ] 28. Implement pipeline tracking
  - [ ] 28.1 Implement pipeline models, schemas, repository, and service
    - Define pipeline stages enum: `SUBMITTED → SHORTLISTED_BY_CLIENT → INTERVIEW_REQUESTED → OFFER_EXTENDED → PLACED → REJECTED`
    - Implement `PipelineService.advance_stage(submission_id, new_stage, actor_id, reason_note, session)`
    - Enforce: reversion (moving to an earlier stage) requires non-empty `reason_note` → raise `HTTP 400` if absent
    - Enforce: if `current_stage == PLACED` and not `is_reopened`, block further changes → `HTTP 400`
    - Write `PIPELINE_STAGE_CHANGED` audit entry per transition (previous stage, new stage, actor, timestamp)
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.6_

  - [ ] 28.2 Implement pipeline API endpoints in `api/v1/pipeline.py`
    - `GET /pipeline/{submission_id}/stages` — history of stage transitions
    - `POST /pipeline/{submission_id}/stages` — submit new stage; call `PipelineService.advance_stage`
    - _Requirements: 15.3, 15.4_

  - [ ]* 28.3 Write property test: pipeline reversion requires reason note (Property 13)
    - **Property 13: Pipeline Stage Reversion Requires Reason Note**
    - For any pipeline reversion attempt by any actor, absent or empty `reason_note` → always HTTP 400, no stage change recorded
    - **Validates: Requirements 15.4**

  - [ ]* 28.4 Write integration tests for pipeline transitions
    - Test: `PLACED` stage → advance attempt without `is_reopened` → HTTP 400
    - Test: reversion with reason note → accepted; reversion without reason note → rejected
    - Test: client HM action → pipeline updated, recruiter notified
    - _Requirements: 15.4, 15.6_

- [ ] 29. Implement client portal screens
  - [ ] 29.1 Implement client portal page
    - `app/(client)/portal/page.tsx` — SSR
    - Display only candidates submitted to the user's organization, grouped by requisition
    - Apply `ContactMasker` — email, phone, address fields must be null in all client responses
    - Show per-requisition pipeline stage summary counts
    - _Requirements: 14.1, 14.2, 14.6_

  - [ ] 29.2 Implement client candidate view and action buttons
    - `app/(client)/candidates/[id]/page.tsx`
    - Show: skills, experience, evaluation score, evidence breakdown, recruiter notes (no contact info)
    - Always render all three action buttons — shortlist, reject, request interview — regardless of current stage (never conditionally disabled)
    - Rejection reason / interview note modal with 2000-char limit
    - On action: call pipeline API, trigger in-app notification to recruiter
    - _Requirements: 14.2, 14.3, 14.4, 14.5_

  - [ ] 29.3 Implement in-app notification service
    - Implement `NotificationService.send(user_id, event_type, payload, session)` in `notifications/service.py`
    - Trigger on: new submission (notify client HM), client action (notify recruiter)
    - Deliver in-app; store in `notifications` table; polling or SSE for real-time display
    - _Requirements: 13.6, 14.4_

- [ ] 30. Implement recruiter pipeline dashboard
  - `app/(recruiter)/pipeline/page.tsx`
  - Aggregated stage counts across all active requisitions
  - Click-through to individual candidate submission
  - _Requirements: 15.5_

- [ ] 31. Phase 7 checkpoint — Ensure all tests pass
  - Verify client portal shows only submitted candidates with contact masking
  - Verify pipeline reversion without reason note → HTTP 400
  - Verify notifications delivered within 60 seconds
  - Ask the user if questions arise before proceeding to Phase 8

---

### Phase 8: Privacy, Responsible AI, and Audit

- [ ] 32. Implement data deletion and anonymization
  - [ ] 32.1 Implement anonymization workflow in `privacy/service.py`
    - `PrivacyService.anonymize_candidate(candidate_id, requester_id, session)`:
      - Null or overwrite PII fields: `full_name → "[ANONYMIZED]"`, `email → None`, `phone → None`, `location → None`
      - Null `resumes.raw_text` and `resumes.parsed_profile_json`
      - Set `candidates.is_anonymized = True`
      - Retain all `Evaluation` score records (scores are non-PII)
      - Retain all `AuditLog` records (immutable by design)
      - Write `DATA_DELETION_COMPLETED` audit entry
    - Expose `POST /candidates/{id}/delete-request` (Recruiter/admin)
    - _Requirements: 19.2, 19.3, 19.4_

  - [ ]* 32.2 Write property test: data deletion anonymization invariant (Property 14)
    - **Property 14: Data Deletion Anonymization Invariant**
    - After anonymization: all PII fields are null or `[ANONYMIZED]`; evaluation scores are present and non-null; at least one `DATA_DELETION_COMPLETED` audit entry exists
    - **Validates: Requirements 19.2**

- [ ] 33. Implement bias monitoring
  - [ ] 33.1 Implement `BiasMonitorService` in `bias/service.py`
    - For each requisition with ≥ 20 candidates, compute Spearman rank correlation between AI score ranking and recruiter submission order
    - Alert if correlation < 0.3 or > 0.97 (write `BIAS_ALERT_GENERATED` entry; make visible to Delivery Head)
    - Implement `generate_monthly_report()` → aggregated per-requisition stats; no individual candidate identity in output
    - Store bias data for minimum 24 months
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_

  - [ ] 33.2 Implement bias monitoring API endpoint and UI
    - `GET /analytics/bias` — return bias report (Delivery Head role)
    - `app/(delivery)/bias-monitor/page.tsx` — display per-requisition correlation stats, alerts, plain-language explanations per metric
    - _Requirements: 17.3, 17.4, 17.7_

- [ ] 34. Implement audit log query interface
  - [ ] 34.1 Implement audit log API endpoint
    - `GET /audit-logs` — Delivery Head + admin role required
    - Support filter params: `date_from`, `date_to`, `event_type`, `actor_user_id`, `resource_id`
    - Paginate results
    - _Requirements: 18.5_

  - [ ] 34.2 Implement account settings screen
    - `app/account/page.tsx`
    - Update display name, change password (require current password confirmation)
    - On password change: invalidate all existing refresh tokens for the user
    - View active sessions
    - View recent actions (last 30 days from audit log)
    - Delivery Head / admin: user deactivation button → revoke all sessions immediately
    - _Requirements: 30.1, 30.3, 30.4, 30.5_

- [ ] 35. Implement Delivery Head analytics dashboard
  - `app/(delivery)/analytics/page.tsx` — CSR
  - KPI cards: active requisitions, total candidates, total submissions, submission-to-placement rate, avg upload-to-submission time
  - Filter by recruiter, requisition, date range
  - Average time-in-stage per pipeline stage
  - Charts: funnel (`FunnelChart`), bar (`BarChart`), line (`LineChart`) — all from charting library compatible with Next.js + Tailwind
  - Render within 5 seconds for orgs with up to 10,000 candidate records
  - _Requirements: 29.1, 29.2, 29.3, 29.4, 29.5_

- [ ] 36. Phase 8 checkpoint — Ensure all tests pass
  - Verify data deletion anonymizes PII and retains scores
  - Verify bias monitoring alerts fire at correct thresholds
  - Verify audit log queryable by all filter types
  - Ask the user if questions arise before proceeding to Phase 9

---

### Phase 9: Integration Testing, Security Hardening, and UI Polish

- [ ] 37. Write complete integration test suite
  - [ ] 37.1 Write integration tests for all API endpoint groups
    - Auth: login success/failure, refresh, logout, rate limit, account lockout
    - Requisitions: CRUD, search (org-scoped), archive
    - Upload: batch submission, file validation (all six rejection cases), batch status polling
    - Evaluations: trigger, evidence query, override, score recomputation
    - Submissions: create (with/without profile view), withdraw, contact masking verification
    - Pipeline: stage transitions, reversion validation, placed-stage lock
    - _Requirements: 28.2_

  - [ ] 37.2 Write full Recruiter E2E path tests with Playwright
    - Individual tests for each step: login, create requisition, upload resume, view evaluation, shortlist, submit to client
    - Combined path test: assert successful conjunction of all six steps
    - Candidate profile page renders within 2 seconds (Playwright timing assertion)
    - _Requirements: 28.4_

- [ ] 38. Security hardening verification
  - [ ] 38.1 Verify all five HTTP security headers present on every response
    - Write test asserting each of the five headers is present and correctly valued
    - _Requirements: 21.6_

  - [ ] 38.2 Verify file upload attack surface
    - Test: EICAR malware test string rejected and quarantined
    - Test: path traversal attempt in filename rejected
    - Test: JWT manipulation (invalid signature) → 401
    - Test: rate limit enforcement (> 10 login attempts → lockout)
    - _Requirements: 21.1, 21.3, 21.8_

  - [ ] 38.3 Verify RBAC exhaustive test matrix
    - Test all three roles against all endpoint permission combinations per the design matrix
    - _Requirements: 3.1–3.9_

- [ ] 39. Performance and coverage verification
  - [ ] 39.1 Verify candidate list filter performance
    - Playwright assertion: filtered candidate list for 500 candidates returns within 3 seconds
    - Playwright assertion: candidate profile page renders within 2 seconds
    - _Requirements: 12.2, 26.6_

  - [ ] 39.2 Verify Scoring Engine and Evidence Extraction coverage ≥ 80%
    - Run `pytest --cov=backend/app/scoring --cov=backend/app/ai/evidence_extraction --cov-fail-under=80`
    - _Requirements: 28.5_

- [ ] 40. UI accessibility and polish pass
  - [ ] 40.1 Accessibility review on all interactive screens
    - Verify keyboard navigation works for all interactive elements (upload drop zone, action buttons, override panel)
    - Add ARIA labels to AI-generated content labels, score badges, evidence status badges
    - Verify all status indicators use color + icon (not color alone) per WCAG 1.4.1
    - _Requirements: 24.3_

  - [ ] 40.2 Error state polish
    - Verify error states render on all screens: API failure, LLM unavailable, file validation rejection, network error
    - LLM unavailability: display "AI service temporarily unavailable" banner (not raw error)
    - _Requirements: 22.5_

- [ ] 41. Phase 9 checkpoint — All tests pass
  - All unit, integration, property, E2E, and contract tests pass
  - Coverage ≥ 80% on Scoring Engine and Evidence Extraction modules
  - All five HTTP security headers present
  - No PII visible in client org API responses
  - EICAR test file rejected and quarantined

---

### Phase 10: Deployment and Documentation

- [ ] 42. Production Docker configuration
  - [ ] 42.1 Write production Dockerfiles and Docker Compose
    - `backend/Dockerfile`: multi-stage build, non-root user, pinned base image
    - `frontend/Dockerfile`: Next.js standalone output, non-root user
    - `docker-compose.prod.yml`: all services with health checks, restart policies, volume mounts
    - Verify `docker-compose up` on a clean clone (after `.env` setup) starts all services successfully
    - _Requirements: Phase 10 deliverables_

  - [ ] 42.2 Write database seed script and verify migration
    - `scripts/seed_demo.py`: create demo org, recruiter user, sample requisition, sample candidates
    - Verify Alembic migration applies cleanly on a fresh schema
    - _Requirements: Phase 10 deliverables_

- [ ] 43. Final documentation pass
  - Update root `README.md` with: setup instructions, architecture overview, test run commands, environment variable reference
  - Verify OpenAPI docs accessible at `/docs` in non-production mode
  - Finalize Architecture Decision Records (ADRs)
  - _Requirements: 22.1, Phase 10 deliverables_

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP delivery
- Each task references specific requirements for full traceability
- Checkpoints at the end of each phase ensure incremental validation
- Property tests (Hypothesis) validate universal correctness invariants at ≥ 100 iterations each
- Unit tests validate specific examples and edge cases
- The 15 correctness properties map 1:1 to individual test sub-tasks; each is annotated with its property number
- Phases 3 and 4 (Tasks 8–11 and Tasks 12–14) can be developed in parallel after Phase 2 (Tasks 1–7) is complete
- Phase 5 requires both Phase 3 and Phase 4 to be complete before starting

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["2.1", "3.1"] },
    { "id": 1, "tasks": ["2.2", "2.3", "3.2"] },
    { "id": 2, "tasks": ["3.3", "4.1", "4.2", "4.3"] },
    { "id": 3, "tasks": ["4.4", "5.1", "6.1", "6.2"] },
    { "id": 4, "tasks": ["4.5", "4.6", "5.2", "6.3", "6.4"] },
    { "id": 5, "tasks": ["8.1", "8.2", "12.1", "12.2"] },
    { "id": 6, "tasks": ["8.3", "9.1", "10.1", "12.3", "13.1", "13.2"] },
    { "id": 7, "tasks": ["8.4", "9.2", "9.3", "10.2", "10.3", "12.4", "13.3", "13.4"] },
    { "id": 8, "tasks": ["10.4", "13.5"] },
    { "id": 9, "tasks": ["15.1", "16.1"] },
    { "id": 10, "tasks": ["15.2", "16.2", "17.1"] },
    { "id": 11, "tasks": ["16.3", "17.2", "18.1"] },
    { "id": 12, "tasks": ["18.2", "18.3", "18.4", "18.5", "18.6", "18.7", "19.1"] },
    { "id": 13, "tasks": ["19.2", "19.3", "19.4"] },
    { "id": 14, "tasks": ["21.1"] },
    { "id": 15, "tasks": ["21.2", "22.1"] },
    { "id": 16, "tasks": ["22.2", "23.1"] },
    { "id": 17, "tasks": ["23.2", "24.1"] },
    { "id": 18, "tasks": ["24.2"] },
    { "id": 19, "tasks": ["24.3"] },
    { "id": 20, "tasks": ["27.1", "28.1"] },
    { "id": 21, "tasks": ["27.2", "27.3", "28.2", "29.1", "29.3"] },
    { "id": 22, "tasks": ["27.4", "28.3", "28.4", "29.2"] },
    { "id": 23, "tasks": ["33.1", "34.1"] },
    { "id": 24, "tasks": ["32.1", "33.2", "34.2"] },
    { "id": 25, "tasks": ["32.2"] },
    { "id": 26, "tasks": ["37.1", "37.2", "38.1", "38.2", "38.3"] },
    { "id": 27, "tasks": ["39.1", "39.2", "40.1", "40.2"] },
    { "id": 28, "tasks": ["42.1", "42.2"] }
  ]
}
```
