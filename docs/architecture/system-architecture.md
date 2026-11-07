# System Architecture — ShortlistAI

## Architecture Decision: Modular Monolith

ShortlistAI is structured as a **modular monolith**: a single deployable Python process whose internal structure is organized into clearly bounded modules with explicit interfaces.

### Rationale

| Factor | Modular Monolith | Microservices |
|--------|-----------------|---------------|
| Operational complexity | Low (1 API process, 1 worker) | High (service mesh, distributed tracing) |
| Transactional integrity | Native (single DB transaction) | Requires distributed sagas |
| Team scale | Appropriate (small team) | Overhead at small scale |
| Future extraction | Possible (interfaces already defined) | Default |
| Development velocity | High | Lower initially |

The modular design means each bounded context (`ai/`, `scoring/`, `submissions/`, etc.) has explicit interfaces. If a module needs independent scaling in the future, extraction is straightforward.

---

## Deployment Topology

```
┌─────────────────────────────────────────────────────────┐
│                     Client Layer                         │
│              Browser (Next.js 14 App Router)             │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────┐
│                   Application Layer                       │
│  ┌──────────────────┐    ┌───────────────────────────┐  │
│  │  Next.js Frontend │    │   FastAPI Backend          │  │
│  │  (Port 3000)      │───▶│   (Uvicorn, Port 8000)    │  │
│  │  SSR + Client     │    │   /api/v1/ prefix         │  │
│  └──────────────────┘    └─────────────┬─────────────┘  │
│                                         │                 │
│                           ┌─────────────▼─────────────┐  │
│                           │   ARQ Worker Process       │  │
│                           │   (10 concurrent jobs)     │  │
│                           │   Resume processing        │  │
│                           └─────────────┬─────────────┘  │
└─────────────────────────────────────────┼────────────────┘
                                          │
┌─────────────────────────────────────────▼────────────────┐
│                      Data Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐ │
│  │ PostgreSQL 15│  │   Redis      │  │  File Storage  │ │
│  │ Port 5432    │  │   Port 6379  │  │  (Local FS /   │ │
│  │ Primary store│  │  Job queue   │  │  S3 future)    │ │
│  │              │  │  Rate limits │  │                │ │
│  │              │  │  Token cache │  │                │ │
│  └──────────────┘  └──────────────┘  └────────────────┘ │
└──────────────────────────────────────────────────────────┘
                                          │
┌─────────────────────────────────────────▼────────────────┐
│                   External Services                        │
│  ┌──────────────────────┐    ┌──────────────────────────┐│
│  │  OpenAI API          │    │  ClamAV                  ││
│  │  (via LLMProvider    │    │  Malware scanning        ││
│  │   abstraction)       │    │                          ││
│  └──────────────────────┘    └──────────────────────────┘│
└──────────────────────────────────────────────────────────┘
```

---

## Backend Module Map

```
backend/app/
├── api/v1/                    ← FastAPI routers (thin — delegate to services)
│   ├── auth.py
│   ├── requisitions.py
│   ├── scorecards.py
│   ├── resumes.py
│   ├── candidates.py
│   ├── submissions.py
│   ├── pipeline.py
│   ├── analytics.py
│   ├── audit.py
│   └── account.py
│
├── core/                      ← Shared infrastructure
│   ├── config.py              ← Pydantic BaseSettings (all env vars)
│   ├── database.py            ← Async SQLAlchemy engine + session factory
│   └── dependencies.py        ← get_db, get_current_user, require_role
│
├── auth/                      ← Token lifecycle, password hashing, RBAC
│   ├── hashing.py
│   ├── jwt.py
│   ├── refresh_tokens.py
│   ├── rbac.py
│   └── rate_limiter.py
│
├── organizations/             ← Org CRUD, membership management
├── requisitions/              ← Requisition CRUD, versioning, search
├── scorecards/                ← Scorecard + criteria, versioning
│
├── resumes/                   ← File upload, storage, validation, dedup
│   ├── storage.py             ← StorageBackend protocol
│   └── validator.py           ← MIME + magic bytes + malware scan
│
├── parsing/                   ← Pure text extraction (no AI)
│   ├── pdf_parser.py          ← PyMuPDF
│   └── docx_parser.py         ← python-docx
│
├── ai/                        ← LLM abstraction + three extraction services
│   ├── provider.py            ← LLMProvider protocol (typing.Protocol)
│   ├── provider_factory.py    ← Dynamic loading from config
│   ├── openai_provider.py     ← Concrete OpenAI implementation
│   ├── jd_extraction.py       ← JDExtractionService
│   ├── resume_extraction.py   ← ResumeExtractionService
│   ├── evidence_extraction.py ← EvidenceExtractionService
│   └── protected_attrs.py     ← ProtectedAttributeStripper
│
├── scoring/                   ← Deterministic scoring engine (pure function)
│   ├── engine.py              ← ScoringEngine.compute()
│   └── rules.py               ← Constants and weight configuration
│
├── candidates/                ← Candidate profile, evaluation orchestration
├── submissions/               ← Shortlisting, submission, contact masking
├── pipeline/                  ← Stage tracking, transition validation
├── audit/                     ← Append-only audit log (AuditLogger)
├── privacy/                   ← Consent records, PII anonymization
├── bias/                      ← Rank correlation, monitoring, alerts
├── notifications/             ← In-app notification service
│
└── jobs/                      ← ARQ background jobs
    ├── worker.py
    └── resume_jobs.py
```

---

## Request Lifecycle

```
Browser Request
      │
      ▼
FastAPI Router (api/v1/)
      │
      ├── JWT Validation Middleware
      │      └── Decode token, load current_user
      │
      ├── Rate Limit Middleware
      │      └── Check Redis sliding window counter
      │
      ├── Role Check (require_role dependency)
      │      └── Raises 403 if role not permitted
      │
      ├── Org Membership Check (service layer)
      │      └── assert_org_member(user_id, org_id)
      │
      ├── Business Logic (service layer)
      │      ├── Repository calls (always with org_id filter)
      │      ├── AI service calls (if applicable)
      │      ├── Scoring Engine call (if applicable)
      │      └── Audit log write (same DB transaction)
      │
      └── Pydantic Response Schema serialization
             └── Contact masking applied if client role
```

---

## Key Component Interactions

### Evaluation Flow (Critical Path)

```
Recruiter triggers evaluation
         │
         ▼
CandidateService.trigger_evaluation(candidate_id, requisition_id)
         │
         ├─── fetch candidate profile from DB
         ├─── fetch active scorecard from DB
         │
         ▼
ProtectedAttributeStripper.strip(full_profile)
         │  Removes: name, gender, age, photo, marital_status, ethnicity, nationality, dob
         │
         ▼
EvidenceExtractionService.extract(clean_profile, criteria, raw_text)
         │  [LLM call via LLMProvider abstraction]
         │  Returns: list[EvidenceResult] with status + excerpts + confidence
         │
         ▼
Excerpt Verification (anti-fabrication)
         │  Each excerpt verified against raw_text (≥80% token overlap)
         │
         ▼
ScoringEngine.compute(evidence, scorecard)
         │  [Pure function — no I/O]
         │  PA guard: raises ProtectedAttributeError if PA fields found in input
         │  Returns: ScoringResult (total_score, criterion_scores)
         │
         ▼
BEGIN TRANSACTION
         ├─── INSERT evaluation record
         ├─── INSERT evaluation_evidence records (one per criterion)
         └─── INSERT audit_log entry (EVALUATION_COMPLETED)
COMMIT
```

### Bulk Upload Flow

```
POST /upload-batch (up to 500 files)
         │
         ├── File validation (MIME, magic bytes, size, malware) — per file
         ├── Store valid files with UUID names
         ├── Create upload_batch record in DB
         ├── Enqueue one ARQ job per valid file
         └── Return 202 { batch_id } immediately (< 2 seconds)

[Background — ARQ Worker, up to 10 concurrent]
         │
         For each file job:
         ├── Extract raw text (PyMuPDF or python-docx)
         ├── Check word count (< 50 → parsing failure)
         ├── Call ResumeExtractionService (LLM)
         ├── Check for duplicates (name+email or name+phone)
         │      ├── Duplicate → flag for Recruiter review (pending state)
         │      └── New → create Candidate record + Consent record
         └── Update upload_batch counters atomically

GET /upload-batches/{batch_id}/status (polled every 3s)
         └── Returns: { total, processed, failed, duplicates, per_file_status[] }
```

---

## Error Handling Strategy

| Error Type | HTTP Code | Backend Action | Frontend Action |
|------------|-----------|----------------|-----------------|
| Pydantic validation | 422 | Auto response with field errors | Field-level error display |
| Auth failure | 401 | Uniform message | Redirect to login |
| RBAC denial | 403 | Log attempt in audit | Permission error screen |
| Cross-org access | 404 | Log attempt in audit | Standard 404 |
| Optimistic lock conflict | 409 | Return version info | Reload and retry prompt |
| LLM unavailable | 503 | After 3 retries | "AI temporarily unavailable" banner |
| File validation | 400/413/415 | Per-file error message | Inline in upload list |
| Malware detected | 400 | Quarantine + audit | Security alert |
| Audit log write fail | 500 | Rollback entire transaction | Generic error; no change applied |

---

## Observability

- **Structured logging**: JSON format on all backend processes; includes `trace_id` on every log line
- **Request tracing**: Every API response includes `X-Trace-Id` header and error envelopes include `trace_id`
- **LLM call logging**: Provider, model, tokens (in + out), latency, success — logged in audit
- **Background job logging**: Job ID, file name, processing time, outcome per job
- **Health endpoints**:
  - `GET /health` — process alive, DB pool healthy, Redis reachable
  - `GET /health/ready` — all of the above + ARQ worker queue reachable
- **Error tracking**: All unhandled exceptions emit structured error logs with full request context

---

## Technology Choices

| Component | Technology | Why |
|-----------|-----------|-----|
| Frontend framework | Next.js 14 (App Router) | SSR for first-paint performance; TypeScript-native; large ecosystem |
| UI components | shadcn/ui + Tailwind CSS | Accessible components; utility-first styling; consistent design system |
| Backend framework | FastAPI (Python 3.11+) | Async-native; OpenAPI auto-generated; Pydantic integration; type hints throughout |
| ORM | SQLAlchemy 2.0 (async) | Mature; type-safe; parameterized queries prevent SQL injection; Alembic migrations |
| Database | PostgreSQL 15 | Reliable; JSONB for flexible profile storage; FK constraints; partial indexes |
| Job queue | ARQ (Redis-backed) | Lightweight; Python-native; async; Redis already used for rate limiting |
| Cache / rate limiting | Redis | Multi-purpose: rate limits + job queue + refresh token cache |
| PDF parsing | PyMuPDF (fitz) | Fast; reliable text extraction; maintained |
| DOCX parsing | python-docx | Standard library for DOCX; pure Python |
| LLM (initial) | OpenAI (gpt-4o) | Structured output support; reliability; JSON mode |
| File scanning | ClamAV via python-clamd | Open-source; widely deployed; signature database |
| Property-based testing | Hypothesis | Essential for scoring engine invariant verification |
| E2E testing | Playwright | Reliable cross-browser; strong async support |
| Schema migrations | Alembic | Standard SQLAlchemy migration tool |

---

## Monorepo Layout

```
shortlistai/                    ← Repository root
├── frontend/                   ← Next.js 14 app
│   ├── app/                    ← App Router pages
│   ├── components/             ← React components
│   ├── lib/                    ← API client, auth, types
│   ├── hooks/                  ← Custom React hooks
│   ├── public/
│   ├── package.json
│   └── tsconfig.json
│
├── backend/                    ← FastAPI app
│   ├── app/                    ← Application code
│   ├── alembic/                ← DB migrations
│   ├── requirements.txt
│   └── pyproject.toml
│
├── tests/                      ← Cross-cutting test suite
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── contracts/
│   └── fixtures/
│
├── docs/                       ← Documentation
│   └── architecture/           ← Phase 1 deliverables
│
├── scripts/                    ← Dev tooling
│   ├── setup_dev.sh
│   └── seed_data.py
│
├── docker-compose.yml          ← Local dev environment
├── .env.example                ← Environment variable template
└── README.md                   ← Project overview
```
