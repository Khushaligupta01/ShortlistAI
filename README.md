# ShortlistAI

**Enterprise Evidence-Based AI Resume Screening & Client Shortlist Management Platform**

**Authoritative GitHub Repository:** https://github.com/Khushaligupta01/ShortlistAI  
**Clone URL:** `git clone https://github.com/Khushaligupta01/ShortlistAI.git`

ShortlistAI transforms high-volume recruitment screening from a subjective, error-prone manual triage into an evidence-grounded, explainable, and privacy-first workflow. 

By decoupling **AI Evidence Extraction** from **Deterministic Mathematical Scoring**, ShortlistAI eliminates generative hallucinations and algorithmic bias. Every score point is backed by verbatim text citations extracted directly from candidate resumes and evaluated against explicit, recruiter-approved job scorecards.

---

## Key System Highlights

- **Dual-Engine Architecture:** LLMs strictly extract verbatim citations matching criteria; an independent mathematical engine calculates transparent, normalized match scores.
- **Explainable Rankings:** Zero black-box scores. Every applicant receives an itemized scorecard breakdown with verbatim quotes and confidence ratings.
- **Hard Knockout Constraints:** Unqualified applicants violating mandatory prerequisites (e.g. minimum experience) are flagged immediately and scored transparently.
- **Multi-Tenant Role Isolation:** Strict tenant separation across recruitment agencies and client organizations.
- **Privacy-Preserving Client Portal:** Blind candidate screening with automatic contact PII redaction and synthetic identifiers to mitigate unconscious bias.
- **GDPR & Responsible AI Compliance:** Full candidate consent tracking, tokenized self-service portals, right to be forgotten (Art. 17) hard erasure, and append-only audit logging.
- **High-Throughput Asynchronous Workers:** Asynchronous PDF/DOCX parsing and OCR processing offloaded from web request threads, tested up to 500 CVs per batch.
- **Premium Warm Neutral Design:** Elegant, accessible UI styled with warm alabaster, soft ivory, muted taupe, and charcoal typography.

---

## Screenshots & Interface Tour

| Screen | Description | File Link |
| :--- | :--- | :--- |
| **Authentication** | Multi-tenant login with role-based routing and demo pre-fills | [`01_login.png`](docs/submission/screenshots/01_login.png) |
| **Recruiter Dashboard** | Live operational metrics, requisitions, pipeline alerts | [`02_recruiter_dashboard.png`](docs/submission/screenshots/02_recruiter_dashboard.png) |
| **Requisitions** | Requisition management and active candidate counts | [`03_requisition_workspace.png`](docs/submission/screenshots/03_requisition_workspace.png) |
| **Scorecard Builder** | 4-pillar rubric editor with weights and knockout toggles | [`04_scorecard_editor.png`](docs/submission/screenshots/04_scorecard_editor.png) |
| **Candidate Leaderboard** | Deterministic ranked candidates with match scores | [`05_ranked_candidates.png`](docs/submission/screenshots/05_ranked_candidates.png) |
| **Hiring Pipeline** | Interactive Kanban pipeline tracking candidate lifecycle | [`06_hiring_pipeline.png`](docs/submission/screenshots/06_hiring_pipeline.png) |
| **Client Portal** | Dedicated executive workspace for client hiring managers | [`07_client_dashboard.png`](docs/submission/screenshots/07_client_dashboard.png) |
| **Client Submissions** | Anonymized, masked candidate profiles for client review | [`08_client_submissions.png`](docs/submission/screenshots/08_client_submissions.png) |
| **Consent & Privacy** | GDPR consent management and Right to be Forgotten requests | [`09_privacy_dashboard.png`](docs/submission/screenshots/09_privacy_dashboard.png) |
| **Audit & Governance** | Immutable compliance logs with SHA-256 hashes | [`10_audit_governance.png`](docs/submission/screenshots/10_audit_governance.png) |

---

## Technology Stack

| Layer | Technologies | Key Responsibilities |
| :--- | :--- | :--- |
| **Backend API** | FastAPI, Python 3.10+, Pydantic v2 | High-concurrency async REST endpoints, validation, RBAC |
| **Database** | PostgreSQL 16, SQLAlchemy 2.0 (asyncpg), Alembic | Relational multi-tenant data layer, transactional migrations |
| **Frontend** | Next.js 15 (App Router), TypeScript, Tailwind CSS | Server-rendered UI, responsive dashboard, client portal |
| **Document Processing** | PyMuPDF (fitz), python-docx | High-fidelity PDF/DOCX text extraction, layout preservation |
| **AI Extraction** | OpenAI GPT-4o-mini / Pluggable Mock AI | Constrained JSON schema verbatim evidence extraction |
| **Containerization** | Docker, Docker Compose, Multi-Stage Builds | Portable standalone production containers (< 120MB) |
| **Testing** | Pytest, AnyIO, ESLint | Automated type checks, linting, unit, and E2E verification |

---

## Quickstart & Local Setup

### Option 1: Docker Compose (Single-Command Setup)

To launch the complete application stack (PostgreSQL, Backend API, Worker, and Frontend) in one command:

```bash
# 1. Clone repository
git clone https://github.com/Khushaligupta01/ShortlistAI.git
cd ShortlistAI

# 2. Configure environment templates
cp backend/.env.production.example backend/.env
cp frontend/.env.production.example frontend/.env.local

# 3. Launch stack
docker compose up -d --build
```
Access the services:
- **Frontend Workspace:** `http://localhost:3000`
- **Backend API & Swagger Docs:** `http://localhost:8000/docs`

---

### Option 2: Native Local Development

#### 1. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run migrations and seed demo data
alembic upgrade head
python scripts/seed.py

# Start FastAPI development server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

#### 2. Frontend Setup
```bash
cd frontend

# Install Node dependencies
npm ci

# Start Next.js development server
npm run dev -- -p 3000
```

---

## Verified Demo Login Credentials

The database seeder (`backend/scripts/seed.py`) populates the system with realistic multi-tenant accounts:

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Recruiter** | `recruiter@techrecruit.com` | `Recruiter@Demo2024!` | Full agency recruiting workspace, candidate ingestion, pipeline |
| **Client Hiring Manager** | `client@acme.com` | `Client@Demo2024!` | Acme Corp portal, masked submissions, interview requests |
| **Delivery Head** | `head@techrecruit.com` | `Delivery@Demo2024!` | Agency-wide analytics, client performance, legal hold approvals |
| **Super Admin / Privacy** | `compliance@shortlist.ai` | `ShortlistAI@2026!` | GDPR consent lifecycle, deletion requests, audit logs |

*(Alternative alias credentials with password `ShortlistAI@2026!` are also active for `recruiter@shortlist.ai`, `client@acmecorp.com`, and `delivery@shortlist.ai`.)*

---

## Running the Automated Test Suite

### 1. Backend Tests (162 Pytest Cases)
```bash
cd backend
python -m pytest tests -v
```
Verified: **162 passed in ~142 seconds** (covering auth, scorecard normalization, evidence extraction, deterministic scoring, knockout enforcement, client isolation, and GDPR deletion).

### 2. Real HTTP End-to-End Audit (8 Critical Stages)
```bash
cd backend
python scripts/audit_e2e_runner.py
```
Verified: **8/8 stages passed** with zero mock shortcuts.

### 3. 500-Resume Batch Limits & Capacity Test
```bash
cd backend
python scripts/test_500_resumes.py
```
Verified: Correct HTTP 400 rejection on 501 files; valid batches processed successfully.

### 4. Frontend Linting & Production Build
```bash
cd frontend
npm run lint
npm run build
```
Verified: ESLint passed with 0 errors; Next.js 15 production build compiled all 23 routes cleanly.

---

## Known Limitations & Assumptions

1. **Text-Based Documents:** Resumes are assumed to be text-based PDF or DOCX files. Scanned images require OCR preprocessing.
2. **Batch Boundary:** Batches are hard-capped at 500 CVs per upload to safeguard server memory and worker process queues.
3. **English Language Focus:** Natural language processing is optimized for English resumes.
4. **Vector Search Excluded:** Cross-requisition semantic vector search is deliberately excluded from this release to ensure strict tenant data segregation.

---

## Submission Documentation & Deliverables

- **Final Submission Archive:** [`dist/ShortlistAI-Submission.zip`](dist/ShortlistAI-Submission.zip) (under 25 MB, containing `technical-design-document.pdf` and `deployment.md`)
- **Technical Design Document (PDF):** [`docs/submission/technical-design-document.pdf`](docs/submission/technical-design-document.pdf)
- **Technical Design Document (Markdown):** [`docs/submission/technical-design-document.md`](docs/submission/technical-design-document.md)
- **Production Operations & Deployment Manual:** [`deployment.md`](deployment.md)
- **Product Demonstration Script:** [`docs/submission/demo-script.md`](docs/submission/demo-script.md)
