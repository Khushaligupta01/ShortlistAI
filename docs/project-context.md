# ShortlistAI — Comprehensive Project Context & Technical Knowledge Base

**System Name:** ShortlistAI  
**Document Classification:** Engineering Master Reference  
**Last Updated:** November 2026 (Phase 10 Release Baseline)  
**Target Audience:** Software Engineers, System Architects, DevOps Engineers, and Evaluators  

---

## 1. Project Overview & Problem Statement

### 1.1 Executive Summary
ShortlistAI is an evidence-based, responsible AI resume screening and client shortlist delivery platform engineered for staffing firms, recruitment agencies, and high-volume corporate talent acquisition teams. 

Traditional recruitment workflows suffer from two failure modes:
1. **Keyword-Based ATS Systems:** Reject qualified candidates over superficial phrasing discrepancies and are trivially manipulated by white-font keyword stuffing.
2. **Uncalibrated Generative AI:** Prompting LLMs to assign direct scores (e.g., "Rate this candidate from 1 to 10") produces subjective, hallucinated justifications, high score variance, and systemic demographic bias.

ShortlistAI resolves these vulnerabilities by implementing a strict **Separation of Cognitive Concerns**:
- **Large Language Models (LLMs)** serve strictly as **Evidence Extractors**, locating verbatim text citations in resumes corresponding to specific job criteria.
- A **Deterministic Mathematical Scoring Engine** validates evidence, evaluates hard knockout criteria, and computes normalized percentage match scores.

### 1.2 Target Personas
- **Recruiter (Internal Agency):** Ingests bulk resumes, reviews evidence citations, manages candidates across an interactive Kanban pipeline, and submits curated shortlists to clients.
- **Delivery Head (Agency Management):** Monitors cross-requisition pipeline velocity, reviews audit logs, oversees client satisfaction, and approves GDPR legal holds.
- **Client Hiring Manager (External Client Organization):** Reviews blind-screened candidate submissions in an isolated client portal, provides one-click feedback (Shortlist, Hold, Reject), and submits interview requests.
- **Candidate (Applicant):** Retains sovereignty over their personal data, grants or revokes processing consent via tokenized self-service links, and exercises GDPR Article 17 Right to be Forgotten.

---

## 2. Product Requirements & Core Capabilities

### 2.1 Requisition & Scorecard Management
- Creation of requisitions with job title, client organization mapping, department, and raw job descriptions.
- Automated extraction of structured 4-pillar scorecard rubrics:
  1. **Required Skills (Pillar 1):** Mandatory core technical competencies.
  2. **Preferred Skills (Pillar 2):** Secondary bonus proficiencies.
  3. **Experience & Seniority (Pillar 3):** Quantitative tenure and domain exposure.
  4. **Education & Certifications (Pillar 4):** Formal degrees and credentials.
- Configurable weights normalized to 100%.
- Strict deterministic **Knockout Rules** (e.g., "Must possess at least 5 years backend experience") that immediately flag unqualified candidates.

### 2.2 Resume Ingestion & Parsing
- Multi-format ingestion supporting PDF and DOCX documents up to 15 MB.
- Asynchronous background worker execution to prevent blocking HTTP request threads.
- Candidate deduplication based on email normalization, phone number matching, and full name fuzzy similarity.

### 2.3 Evidence Extraction & Deterministic Evaluation
- For each criterion on an approved scorecard, the AI extracts verbatim quotes, source sentence context, and a confidence rating.
- If a skill is absent, the system records zero evidence without fabricating negative penalties or assuming unstated qualifications.
- Transparent mathematical scoring:
  $$\text{Score} = \left( \sum_{i=1}^{n} w_i \times s_i \right) \times \mathbb{I}_{\text{no knockout}}$$

### 2.4 Recruiter Workspace & Hiring Pipeline
- Live operational dashboard with active requisitions, pipeline metrics, and candidate volume.
- Interactive Kanban pipeline spanning 9 stages: `SUBMITTED`, `CLIENT_SHORTLISTED`, `INTERVIEW_REQUESTED`, `INTERVIEW_SCHEDULED`, `INTERVIEW_COMPLETED`, `OFFER_EXTENDED`, `HIRED`, `CLIENT_REJECTED`, `WITHDRAWN`.
- Internal private recruiter notes and evaluation overrides.

### 2.5 Privacy-Preserving Client Portal
- Isolated client portal displaying only candidates submitted to that specific client organization.
- **Server-Side Blind Masking:** Complete redaction of candidate email, phone numbers, and street addresses; generation of synthetic candidate codes (`Candidate CND-XXXXX`).
- Proprietary rubric weight suppression: clients review criteria descriptions and citations, with internal staffing margin constants hidden.

### 2.6 Responsible AI Governance & GDPR Compliance
- **Consent Tracking:** Lifecycle tracking across `GRANTED`, `PENDING`, and `WITHDRAWN`. Single-use cryptographic verification tokens (`/public/consent/[token]`).
- **Processing Gates:** Pre-evaluation guards prevent AI processing or client submission if consent is missing or withdrawn.
- **Right to be Forgotten (GDPR Art. 17):** Controlled erasure workflow with physical disk file unlinking, personal data database scrubbing, and anonymized audit hashing.
- **Append-Only Audit Log:** Centralized event stream with SHA-256 integrity hashes and recursive credential sanitization.

---

## 3. Architecture Decisions & System Design

| ADR ID | Decision | Chosen Alternative | Rationale |
| :--- | :--- | :--- | :--- |
| **ADR-001** | Backend Framework | **FastAPI (Python 3.10+)** | Async concurrency, automatic OpenAPI documentation, Pydantic data validation, native compatibility with NLP/AI libraries. |
| **ADR-002** | Frontend Architecture | **Next.js 15 (App Router)** | React Server Components, server-side data fetching, standalone Docker builds (<120MB), responsive UI with Tailwind CSS. |
| **ADR-003** | Database & Concurrency | **PostgreSQL 16 + SQLAlchemy 2.0 (Asyncpg)** | Relational integrity, foreign key cascades, connection pooling (`DB_POOL_SIZE=20`), versioned Alembic migrations. |
| **ADR-004** | Document Processing | **PyMuPDF (fitz) + python-docx** | 10x faster execution than pure-Python parsers, accurate multi-column text layout preservation. |
| **ADR-005** | AI Provider Abstraction | **Pluggable Multi-Provider (OpenAI / Mock)** | Lean custom protocol isolating prompt contracts; zero heavyweight framework overhead; instant offline mock provider for CI/CD. |
| **ADR-006** | Multi-Tenancy Model | **Shared Database, Logical Tenant Scoping** | All tenant tables include `organization_id`; repository queries enforce tenant isolation at the database layer. |

---

## 4. Technology Stack Summary

### Backend
- **Language:** Python 3.10 / 3.11
- **Web Framework:** FastAPI 0.115+
- **ASGI Server:** Uvicorn 0.32+
- **Database Driver:** Asyncpg 0.29+
- **ORM:** SQLAlchemy 2.0+ (Async IO)
- **Migrations:** Alembic 1.14+
- **Security & Passwords:** Argon2-cffi, Pwdlib, Python-Jose (JWT)
- **Document Processing:** PyMuPDF (fitz), Python-Docx
- **Testing:** Pytest 8.3+, Pytest-AsyncIO 0.24+

### Frontend
- **Framework:** Next.js 15.5+ (App Router, Standalone Mode)
- **Language:** TypeScript 5.x
- **Styling:** Tailwind CSS 3.4+
- **Icons:** Lucide React
- **HTTP Client:** Native Fetch with typed error handling and JWT interceptors

### Database & Storage
- **Database:** PostgreSQL 16
- **Storage:** Local persistent disk volumes (`storage/`) structured by organization UUIDs, abstractable to AWS S3.

---

## 5. Repository Structure

```text
ShortlistAI/
├── .github/
│   └── workflows/
│       └── ci.yml                     # Continuous integration workflow
├── backend/
│   ├── alembic/                       # Database migration versions and env.py
│   ├── app/
│   │   ├── api/v1/endpoints/          # REST route handlers (auth, requisitions, candidates, client, privacy)
│   │   ├── core/                      # Configuration (config.py), security, JWT helpers
│   │   ├── db/                        # Database session (session.py) and base model
│   │   ├── models/                    # SQLAlchemy 2.0 async models
│   │   ├── schemas/                   # Pydantic v2 validation models
│   │   ├── services/                  # Business logic (ai, parsing, scoring, privacy, audit)
│   │   └── main.py                    # FastAPI entrypoint, middleware, and router mounts
│   ├── scripts/                       # Seeding, screenshot capture, worker runners, packaging
│   ├── tests/                         # Comprehensive pytest test suite (155 tests)
│   ├── Dockerfile                     # Multi-stage production container
│   ├── pyproject.toml                 # Backend project configuration
│   └── requirements.txt               # Pinned Python dependencies
├── frontend/
│   ├── app/                           # Next.js 15 App Router pages and layouts
│   ├── components/                    # Reusable React components (Navigation, Modals, Tables)
│   ├── lib/                           # API client (api.ts), authentication (auth.ts), types (types.ts)
│   ├── Dockerfile                     # Multi-stage standalone Next.js container
│   ├── next.config.ts                 # Next.js standalone output configuration
│   └── package.json                   # Pinned Node dependencies
├── docs/
│   ├── architecture/                  # Deep-dive architecture specifications and diagrams
│   ├── cleanup/                       # Repository cleanup verification reports
│   ├── qa/                            # Baseline reports, defect registers, test execution logs
│   ├── submission/                    # Final TDD (PDF/MD), demo script, screenshots
│   └── project-context.md             # This document (Master Technical Knowledge Base)
├── deployment.md                      # Comprehensive 19-section operations and deployment manual
├── docker-compose.yml                 # Unified multi-container Docker Compose definition
└── README.md                          # Root project documentation and quickstart
```

---

## 6. Database Schema & Relational Models

The relational schema is implemented in PostgreSQL 16 and managed via Alembic:

1. **`organizations`:** Agency or client tenants (`id`, `name`, `org_type`, `created_at`).
2. **`users`:** User accounts with Argon2id passwords (`id`, `organization_id`, `email`, `hashed_password`, `role`, `is_active`).
3. **`requisitions`:** Job openings (`id`, `organization_id`, `client_organization_id`, `title`, `department`, `job_description`, `status`).
4. **`scorecards`:** Versioned evaluation rubrics (`id`, `requisition_id`, `version`, `status`).
5. **`scorecard_criteria`:** Rubric dimensions (`id`, `scorecard_id`, `category`, `name`, `weight`, `is_knockout`).
6. **`candidates`:** Candidate profiles (`id`, `organization_id`, `requisition_id`, `full_name`, `email`, `phone`, `status`, `is_anonymized`).
7. **`resumes`:** Document metadata (`id`, `candidate_id`, `file_path`, `file_format`, `raw_text`, `parsing_status`).
8. **`candidate_evaluations`:** Deterministic scoring outcomes (`id`, `candidate_id`, `scorecard_id`, `overall_score`, `fit_tier`, `knockout_triggered`).
9. **`evaluation_evidence`:** Verbatim citations (`id`, `evaluation_id`, `criterion_id`, `verbatim_quote`, `match_confidence`).
10. **`submissions`:** Client presentations (`id`, `candidate_id`, `client_organization_id`, `status`, `client_feedback`).
11. **`consent_records`:** GDPR consent state (`id`, `candidate_id`, `status`, `verification_token`, `consent_date`).
12. **`audit_logs`:** Append-only compliance log (`id`, `organization_id`, `user_id`, `action`, `entity_type`, `entity_id`, `sha256_hash`, `timestamp`).

---

## 7. Role-Based Access Control (RBAC) Permissions

| Role | Permitted Actions | Restricted Boundaries |
| :--- | :--- | :--- |
| **`RECRUITER`** | Manage requisitions, upload resumes, review candidate profiles, edit scorecards, move pipeline stages, submit candidates to clients, manage consent and erasure requests. | Cannot view data of other staffing agencies; cannot modify client feedback directly. |
| **`DELIVERY_HEAD`** | All Recruiter capabilities, plus cross-requisition funnel analytics, client account performance comparisons, and GDPR legal hold approvals. | Restricted to their own agency organization. |
| **`CLIENT_HIRING_MANAGER`** | Access dedicated client portal (`/client`), view blind-masked submissions, approve/reject candidates, submit interview requests. | Strictly barred from unsubmitted candidates, direct candidate contact PII, raw resume downloads, and internal agency recruiter notes. |

---

## 8. Development, Testing & Operational Commands

### Backend Local Commands
```bash
cd backend
source .venv/bin/activate  # Or .venv\Scripts\Activate.ps1 on Windows

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed demo data
python scripts/seed.py

# Start development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Execute automated tests
pytest tests/ -v
```

### Frontend Local Commands
```bash
cd frontend

# Install dependencies
npm ci

# Start Next.js development server
npm run dev -- -p 3000

# Type-check and build standalone production bundle
npm run build
```

### Docker Compose Stack
```bash
# Build and run all services in detached mode
docker compose up -d --build

# View container logs
docker compose logs -f

# Teardown stack and preserve volumes
docker compose down
```

---

## 9. Environment Variable Documentation

### Backend (`backend/.env`)
- `ENVIRONMENT`: `development` | `test` | `production`
- `DEBUG`: `true` in local development; `false` in production.
- `SECRET_KEY`: Cryptographically secure 64-character hex string for JWT signing.
- `ALGORITHM`: Token signing algorithm (`HS256`).
- `ACCESS_TOKEN_EXPIRE_MINUTES`: Recruiter/Client session token TTL (default: `60`).
- `DATABASE_URL`: Async PostgreSQL connection string (`postgresql+asyncpg://user:pass@host:5432/dbname`).
- `DB_POOL_SIZE`: Database connection pool base size (default: `20`).
- `DB_MAX_OVERFLOW`: Overflow connections allowed above pool size (default: `10`).
- `DB_POOL_RECYCLE`: Connection recycle interval in seconds (default: `1800`).
- `ALLOWED_ORIGINS`: JSON array of allowed frontend CORS domains.
- `STORAGE_DIR`: Path for resume uploads (default: `storage`).
- `MAX_UPLOAD_SIZE_MB`: Maximum resume upload file size in MB (default: `15`).
- `AI_PROVIDER`: `openai` | `mock`
- `OPENAI_API_KEY`: API key for OpenAI model access.
- `OPENAI_MODEL`: Model name (default: `gpt-4o-mini`).

### Frontend (`frontend/.env.local` or `.env.production`)
- `NEXT_PUBLIC_API_URL`: Backend API base URL reachable by browser client (e.g., `http://localhost:8000/api/v1`).
- `NODE_ENV`: Execution environment (`development` | `production`).

---

## 10. Pre-Configured Demo Credentials

The database seeder (`backend/scripts/seed.py`) provisions the following accounts:

| Role | Email | Password | Scope |
| :--- | :--- | :--- | :--- |
| **Recruiter** | `recruiter@techrecruit.com` | `Recruiter@Demo2024!` | Agency recruiting workspace |
| **Delivery Head** | `head@techrecruit.com` | `Delivery@Demo2024!` | Agency executive oversight |
| **Client Hiring Manager (1)** | `client@acme.com` | `Client@Demo2024!` | Acme Corp client portal |
| **Client Hiring Manager (2)** | `client@starlight.com` | `Client@Demo2024!` | Starlight Health portal |

---

## 11. Known Limitations & Future Improvements

1. **OCR on Low-Resolution Scans:** Degraded physical image scans may produce lower text fidelity; production environments should integrate cloud OCR services (e.g. AWS Textract) for degraded documents.
2. **Third-Party LLM Quotas:** Bulk processing of 500+ resumes concurrently requires managing external LLM API rate limits using queuing with exponential backoff.
3. **Cross-Requisition Talent Pooling:** Future roadmap includes pgvector embedding indexing to enable semantic searching across past candidate submissions.

