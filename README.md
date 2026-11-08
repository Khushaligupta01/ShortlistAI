# ShortlistAI

**Enterprise Evidence-Based AI Resume Screening & Client Shortlist Management Platform**

ShortlistAI transforms high-volume recruitment screening from a subjective, error-prone manual triage into an evidence-grounded, explainable, and privacy-first workflow. 

By decoupling **AI Evidence Extraction** from **Deterministic Mathematical Scoring**, ShortlistAI eliminates generative hallucinations and algorithmic bias. Every score point is backed by verbatim text citations extracted directly from candidate resumes and evaluated against explicit, recruiter-approved job scorecards.

---

## Key System Highlights

- **Dual-Engine Architecture:** LLMs strictly extract verbatim citations matching criteria; an independent mathematical engine calculates transparent, normalized match scores.
- **Explainable Rankings:** Zero black-box scores. Every applicant receives an itemized scorecard breakdown with verbatim quotes and confidence ratings.
- **Hard Knockout Constraints:** Unqualified applicants violating mandatory prerequisites (e.g. minimum experience) are flagged immediately.
- **Multi-Tenant Role Isolation:** Strict tenant separation across recruitment agencies and client organizations.
- **Privacy-Preserving Client Portal:** Blind candidate screening with automatic contact PII redaction and synthetic identifiers to mitigate unconscious bias.
- **GDPR & Responsible AI Compliance:** Full candidate consent tracking, tokenized self-service portals, right to be forgotten (Art. 17) hard erasure, and append-only audit logging.
- **High-Throughput Asynchronous Workers:** Asynchronous PDF/DOCX parsing and OCR processing offloaded from web request threads.

---

## Screenshots & Interface Tour

| Screen | Description | File Link |
| :--- | :--- | :--- |
| **Authentication** | Multi-tenant login with role-based routing | [`01_login.png`](docs/submission/screenshots/01_login.png) |
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
| **CI / Automation** | GitHub Actions (`.github/workflows/ci.yml`) | Automated type checks, linting, tests, and build verification |

---

## Quickstart & Local Setup

### Option 1: Docker Compose (Recommended)

To launch the complete application stack (PostgreSQL, Backend API, Worker, and Frontend) in one command:

```bash
# 1. Clone repository
git clone https://github.com/organization/ShortlistAI.git
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
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

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

## Pre-Configured Demo Credentials

The database seeder (`backend/scripts/seed.py`) populates the system with realistic multi-tenant accounts:

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Recruiter** | `recruiter@techrecruit.com` | `Recruiter@Demo2024!` | Full agency recruiting workspace, candidate ingestion, pipeline |
| **Delivery Head** | `head@techrecruit.com` | `Delivery@Demo2024!` | Agency-wide analytics, client performance, legal hold approvals |
| **Client Hiring Manager (1)** | `client@acme.com` | `Client@Demo2024!` | Acme Corp portal, masked submissions, interview requests |
| **Client Hiring Manager (2)** | `client@starlight.com` | `Client@Demo2024!` | Starlight Health portal, candidate reviews |

---

## Comprehensive Documentation Index

All technical design, operations, and submission deliverables are located in the repository:

- **Technical Design Document (PDF):** [`docs/submission/technical-design-document.pdf`](docs/submission/technical-design-document.pdf)
- **Technical Design Document (Markdown):** [`docs/submission/technical-design-document.md`](docs/submission/technical-design-document.md)
- **Demonstration Walkthrough Script:** [`docs/submission/demo-script.md`](docs/submission/demo-script.md)
- **Production Operations & Deployment Manual:** [`deployment.md`](deployment.md)
- **Automated CI Workflow:** [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
- **Application Screenshots:** [`docs/submission/screenshots/`](docs/submission/screenshots/)

---

## Project Status & Operational Disclaimer

> [!NOTE]
> **Phase 10 Release Candidate Status:** This repository contains the complete production-configured codebase, container definitions, migration history, and submission documentation. A comprehensive, independent end-to-end verification and testing cycle will be conducted separately after Phase 10 prior to commercial general availability.
