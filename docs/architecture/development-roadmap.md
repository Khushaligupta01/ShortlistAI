# Development Roadmap — ShortlistAI

## Overview

10-phase implementation roadmap. Each phase has defined dependencies, deliverables, and acceptance criteria. No phase begins until its dependencies are met.

---

## Phase 1: Requirements and Architecture ✅

**Goal**: Complete product analysis and architecture design before any implementation.

**Deliverables**:
- All architecture documents in docs/architecture/
- ER diagram and system architecture diagrams
- API specification
- Root README

**Acceptance Criteria**:
- All 13 architecture documents exist and are internally consistent
- ER diagram covers all 14 tables
- API spec covers all endpoint groups
- No critical unresolved architectural decisions

**Status**: Complete (this document is the final Phase 1 deliverable)

---

## Phase 2: Backend Foundation — Database, Auth, and Core Infrastructure

**Dependencies**: Phase 1

**Goal**: Working backend with database, migrations, authentication, and multi-tenant isolation.

**Deliverables**:
- Monorepo structure: `frontend/`, `backend/`, `tests/`, `docs/`
- Docker Compose for local development (PostgreSQL 15, Redis, backend)
- All 14 SQLAlchemy models with FK constraints, indexes, unique constraints
- Alembic migration for initial schema
- FastAPI application skeleton with middleware stack (auth, rate limit, CORS, security headers)
- JWT authentication: login, refresh, logout endpoints
- Argon2/bcrypt password hashing
- RBAC dependency (`require_role`)
- Organization membership model and tenant isolation guard
- Audit logger (`AuditLogger`) with transaction-bound writes
- Health endpoints (`/health`, `/health/ready`)

**Test Requirements**:
- Auth integration tests: login success, login failure (uniform message), refresh, logout, account lockout
- RBAC tests: all three roles against at least 5 endpoint permission combinations
- Org isolation test: user A cannot access user B's requisition
- Audit log atomicity test: audit write failure → operation rollback
- Property test: auth error non-disclosure (Property 10)

**Acceptance Criteria**:
- All auth endpoints return correct HTTP codes
- Cross-org access returns 404 and writes audit event
- RBAC returns 403 for disallowed roles
- Audit log fails the operation on write failure
- Docker Compose starts all services successfully

---

## Phase 3: JD Intelligence and Scorecard

**Dependencies**: Phase 2

**Goal**: LLM provider abstraction, JD extraction, and full scorecard management.

**Deliverables**:
- LLM Provider protocol (`LLMProvider`) and factory (config-driven)
- OpenAI provider implementation with retry/timeout policy
- JD Extraction Service with confidence scoring and null handling
- Scorecard API: create, read, update, activate, version
- Scorecard weight validation (sum = 100 on activation)
- Scorecard versioning (new draft on reset from active)
- JD extraction pre-populates scorecard editor via API
- LLM call audit logging (provider, model, tokens, latency)

**Test Requirements**:
- JD extraction: fields present in JD → extracted with confidence; absent fields → null + 0.0
- Must-have skills: only skills in JD text (anti-inference test)
- LLM failure: extraction service returns error, scorecard editor receives empty pre-population
- Retry policy: network error retried 3x; schema validation error not retried
- Scorecard: weight sum < 100 blocks activation; weight sum = 100 allows activation
- Contract test: OpenAI provider satisfies LLMProvider interface

**Acceptance Criteria**:
- JD extraction returns structured result from a sample JD in < 30 seconds
- Scorecard activation blocked if total weight ≠ 100
- Prior evaluation records reference the correct scorecard version after a version change

---

## Phase 4: Resume Ingestion and Parsing

**Dependencies**: Phase 2

**Goal**: Bulk upload, background processing, document parsing, and duplicate detection.

**Deliverables**:
- File upload API: multipart, MIME validation, magic bytes check, size limits
- ClamAV integration for malware scanning (fail-secure on scanner unavailable)
- UUID-based file storage (local FS for MVP)
- ARQ worker setup with Redis connection
- Background job pipeline: file → extract text (PyMuPDF / python-docx) → detect duplicates → queue extraction
- Upload batch record with per-file status tracking
- Batch status polling endpoint
- Duplicate detection (name+email or name+phone) with pending state
- Consent record creation at upload

**Test Requirements**:
- File validation: valid PDF parsed, valid DOCX parsed, wrong extension rejected, MIME mismatch rejected, magic bytes mismatch rejected, oversized file rejected, malware (EICAR) quarantined
- Word count < 50 → parsing failure, recruiter notification
- Duplicate detection: same name+email → flagged, not auto-merged
- Batch status updates within 5 seconds of job completion
- Graceful shutdown: in-progress jobs complete, queue jobs remain
- Content hash dedup: same file content in same batch → single job queued

**Acceptance Criteria**:
- 10 resumes upload and process without error in test environment
- Invalid files rejected per specification
- Malware detection quarantines file and logs audit event
- Duplicate candidate flagged in batch status response

---

## Phase 5: AI Evidence Extraction and Deterministic Scoring

**Dependencies**: Phases 3 and 4

**Goal**: Resume extraction service, evidence extraction, protected attribute pipeline, and scoring engine.

**Deliverables**:
- Resume Extraction Service (LLM-backed) with per-field confidence
- Protected Attribute Stripper (removes PA field keys and values)
- Evidence Extraction Service with 4-status model and source excerpts
- Anti-fabrication excerpt verification (≥ 80% token overlap)
- Deterministic Scoring Engine (pure function)
- Evidence override endpoint (with mandatory reason + re-scoring)
- Evaluation record creation with full breakdown JSON

**Test Requirements**:
- Scoring Engine property tests (Properties 1–5, 7, 11):
  - Score always in [0, 100]
  - Determinism: same input → same output
  - Unknown → strictly between 0 and full criterion weight
  - PA fields in input → ProtectedAttributeError
  - Must-have proportional formula
- PA stripping property test (Property 6): no PA fields in clean_profile
- Extraction confidence property test (Property 7): all confidence values in [0.0, 1.0]
- Evidence extraction: absent information → unknown/insufficient_evidence (never not_matched)
- Anti-fabrication: fabricated excerpt fails verification → status downgraded
- Override: new evaluation version created, old version retained

**Acceptance Criteria**:
- Scoring engine passes all 15 property tests (min 100 iterations each)
- Evidence extraction returns verified source excerpts only
- Score breakdown stored in evaluation record with full criterion detail
- Evidence override creates new evaluation version and re-computes total score

---

## Phase 6: Recruiter Dashboard and Candidate Management

**Dependencies**: Phase 5

**Goal**: Complete recruiter-facing frontend with dashboard, candidate list, and evaluation screen.

**Deliverables**:
- Next.js app scaffold with App Router, TypeScript, Tailwind, shadcn/ui
- Typed API client (`lib/api.ts`) with token refresh on 401
- Login screen
- Recruiter dashboard (SSR): KPI cards, requisition grid, activity feed
- Requisition management screen: list, create, edit, archive
- JD scorecard editor: AI extraction trigger, criteria management, weight validation
- Candidate ranked list: filters, sorting, pagination, URL-encoded filter state
- Candidate profile + evaluation screen: score breakdown chart, evidence rows, source excerpts, override panel, notes
- Bulk upload screen: drop zone, file status list, progress bar, duplicate resolver, CSV download
- Loading skeleton states on all data-heavy screens

**Test Requirements**:
- E2E recruiter path — individual tests for each step: login, create requisition, upload resume, view evaluation, shortlist, submit to client
- E2E combined path test: all steps in conjunction
- Candidate profile page renders within 2 seconds (Lighthouse or Playwright timing assertion)
- Candidate list with 500 candidates returns filtered results within 3 seconds
- Filter state persists after navigating to profile and back

**Acceptance Criteria**:
- Recruiter can complete full workflow end-to-end in the test environment
- All six E2E individual path tests pass
- Combined path test passes
- All screens display loading skeleton states during API calls

---

## Phase 7: Client Portal and Hiring Pipeline

**Dependencies**: Phase 6

**Goal**: Client Hiring Manager portal, contact masking, pipeline tracking, and in-app notifications.

**Deliverables**:
- Client portal screen: submitted candidates only, contact masked
- Client action buttons: shortlist, reject, request interview — always all three available
- Rejection reason / interview note modal with 2000-char limit
- Pipeline stage tracking and history
- Stage transition validation (reason required for reversion; placed stage lock)
- In-app notification service (client receives on submission; recruiter receives on client action)
- Delivery Head pipeline view with analytics
- Recruiter pipeline dashboard: aggregated stage counts

**Test Requirements**:
- Contact masking tests: client API response contains null for email, phone, address fields
- RBAC isolation: client cannot access non-submitted candidates (Property 9)
- Multi-tenant isolation: client org user cannot access other org's submissions (Property 8)
- Stage reversion without reason → 400 error (Property 13)
- Placed stage locked — advance attempt → 400 error
- Submission withdrawal → candidate disappears from client view within 5 seconds

**Acceptance Criteria**:
- Client portal shows only submitted candidates
- Contact masking applied consistently in all client responses
- Pipeline stage reversion without reason note rejected
- Notifications delivered within 60 seconds of triggering event

---

## Phase 8: Privacy, Responsible AI, and Audit

**Dependencies**: Phase 7

**Goal**: Full privacy controls, bias monitoring, audit query interface, and account management.

**Deliverables**:
- Consent record creation and display during bulk upload (privacy notice gate)
- Candidate data deletion / anonymization workflow
- Account settings screen: display name, password change, active sessions
- Audit log query endpoint (Delivery Head + admin)
- Bias Monitor: rank-order correlation computation, alert generation
- Monthly bias report generation
- Delivery Head analytics dashboard with charts
- Protected attribute runtime guard in scoring engine (already in Phase 5 — verify here)
- Delivery Head user deactivation

**Test Requirements**:
- Data deletion property test (Property 14): PII anonymized, scores retained, audit entry present
- Submission requires profile view property test (Property 15)
- Bulk submission batch size property test (Property 12)
- Bias monitoring: alert triggers below 0.3 or above 0.97 correlation
- Monthly report: no candidate identity in output
- Deactivating a user revokes all active sessions

**Acceptance Criteria**:
- Data deletion request processes within the required timeframe
- Bias monitoring correctly identifies divergent requisitions
- Audit logs queryable by date range, event type, actor, resource
- Account deactivation revokes all sessions immediately

---

## Phase 9: Integration Testing, Security Hardening, and UI Polish

**Dependencies**: Phase 8

**Goal**: Full test suite pass, security review, performance validation, and UI refinement.

**Deliverables**:
- Complete integration test suite (all API endpoints: auth, requisitions, upload, evaluations, submissions, pipeline)
- All 15 property-based tests verified at 100 iterations
- LLM provider contract tests
- Security testing: file upload attacks, JWT manipulation, EICAR malware test, rate limit verification, RBAC exhaustive tests
- Performance tests: candidate list filter < 3s, profile page < 2s, analytics < 5s
- 80%+ line coverage on Scoring Engine and Evidence Extraction Service
- UI accessibility pass: keyboard navigation, ARIA labels, color + icon status indicators
- Error state polish on all screens
- CSV export from upload screen
- Comprehensive README and setup instructions

**Acceptance Criteria**:
- All tests pass (unit, integration, property, E2E, contract)
- Coverage ≥ 80% on specified modules
- All five HTTP security headers present on every response
- No PII visible in client org API responses
- EICAR test file rejected and quarantined

---

## Phase 10: Deployment and Documentation

**Dependencies**: Phase 9

**Goal**: Production-ready deployment configuration and complete documentation.

**Deliverables**:
- Production Docker Compose / Dockerfile for all services
- Environment variable documentation (.env.example with all required keys)
- Alembic migration run verified on clean schema
- Database seed script for demo/review data
- OpenAPI documentation verified at /docs (non-production)
- Final README with setup instructions, architecture overview, and test run instructions
- Architecture decision records (ADRs) finalized

**Acceptance Criteria**:
- Application starts from a clean clone with `docker-compose up` after .env setup
- All migrations apply without error
- OpenAPI docs accessible at /docs
- Demo data loads and all features demonstrable

---

## Phase Dependencies Summary

```
Phase 1 (Architecture)
    └── Phase 2 (Backend Foundation)
            ├── Phase 3 (JD + Scorecard)
            └── Phase 4 (Upload + Parsing)
                    └── Phase 5 (AI Extraction + Scoring)
                            └── Phase 6 (Recruiter Frontend)
                                    └── Phase 7 (Client Portal + Pipeline)
                                            └── Phase 8 (Privacy + Bias + Audit)
                                                    └── Phase 9 (Testing + Polish)
                                                            └── Phase 10 (Deployment)
```

Note: Phases 3 and 4 can proceed in parallel after Phase 2. Phase 5 requires both 3 and 4.
