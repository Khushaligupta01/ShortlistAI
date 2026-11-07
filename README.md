# ShortlistAI

An evidence-based AI resume screening and client shortlist platform for staffing and recruitment firms.

## Status

**Phase 3 Complete** — AI Job Description Intelligence and Dynamic Scorecard Engine fully implemented, tested, and integrated.

## What's Built (Phase 3)

### AI Job Description Intelligence
- Provider-independent LLM abstraction (`LLMProvider` protocol in `backend/app/ai/provider.py`).
- Production concrete OpenAI provider (`backend/app/ai/openai_provider.py`) with exponential backoff retry, request timeouts, and quota exhaustion / rate limit detection.
- Protected attribute scanner and bias prevention: detects and warns on age, gender, race, marital status, or photo requirements in JDs without propagating them to criteria.
- Strict Pydantic output schemas (`JDExtractionResult`) validating experience ranges, skills, notice periods, and warnings.
- Rate-limited JD extraction endpoint: `POST /api/v1/requisitions/extract-requirements` (10 req/min per user).

### Dynamic Scorecard Management Engine
- Configurable scoring weights: Experience (30), Must-have skills (40), Notice period (15), Location (10), Nice-to-have skills (5) totaling 100 points.
- Scorecard creation, drafting, and criterion updating with atomic cascade persistence.
- Immutable locking: Approving a scorecard locks it permanently and activates the requisition; modification attempts return `409 Conflict`.
- Explicit version preservation: `POST /api/v1/requisitions/{id}/scorecard/duplicate` clones an approved scorecard into a new draft version.
- Multi-tenant organization isolation (cross-org returns 404) and RBAC (Recruiters only for modifications; Client HM rejected with 403).
- Immutable audit logging for all requisition and scorecard events (`REQUISITION_CREATED`, `SCORECARD_CREATED`, `SCORECARD_UPDATED`, `SCORECARD_APPROVED`, `SCORECARD_DUPLICATED`).

### Frontend User Interface (Next.js 15)
- **Requisitions List** (`/requisitions`): Search by title/location, filter by status (All, Draft, Active, Archived), and pagination.
- **New Requisition & AI Intelligence** (`/requisitions/new`): Enter job title, location, description; trigger AI extraction; review AI findings and warnings; edit scorecard criteria; save draft or approve.
- **Requisition Detail & Scorecard Viewer** (`/requisitions/[id]`): View requisition summary, inspect active scorecard criteria and weights, lock notice for approved scorecards, and one-click "Create New Version" workflow.
- **Interactive Scorecard Editor Component**: Real-time 100-point total counter (turns green on 100, red when unbalanced), add/remove skills, toggle mandatory flags, and set experience/notice bounds.

### Automated Test Suite
- **45 passing automated tests** in `backend/tests/`:
  - 14 AI Extraction tests (`test_jd_extraction.py`): complete JD, missing notice period, missing location, missing experience, multiple skills, nice-to-have skills, contradictory requirements, malformed JSON, invalid ranges, timeouts, provider unavailability, rate limiting, protected attributes scanning, long JDs.
  - 10 Scorecard tests (`test_scorecard.py`): creation, editing, invalid weights, weight sum validation, missing fields, draft status, approval & locking, version preservation via duplicate, RBAC rejection (403), cross-org isolation (404).
  - 21 Phase 1 & 2 tests (auth, authorization, database, health, security headers).
- Live PostgreSQL verification script (`backend/scripts/verify_phase3.py`) passing all 9 end-to-end steps.

## Quick Start

### Prerequisites
- Python 3.10
- Node.js 20+
- PostgreSQL 15 (or Docker)

### With Docker (recommended)

```bash
cp .env.example .env
# Edit .env — set JWT_SECRET_KEY, SEED_* passwords, and AI_API_KEY
docker-compose up -d
```

Apply migrations and seed Section 15 sample data:
```bash
docker-compose exec backend alembic upgrade head
docker-compose exec backend python scripts/seed.py
```

### Without Docker

**Backend:**
```bash
cd backend
py -3.10 -m venv .venv310
.venv310\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env             # edit DATABASE_URL and JWT_SECRET_KEY
alembic upgrade head
python scripts/seed.py
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run build                    # verify production build
npm run dev
```

### Demo Accounts (after seeding)

| Role | Email | Password |
|------|-------|----------|
| Recruiter | `recruiter@techrecruit.com` | set via `SEED_RECRUITER_PASSWORD` |
| Client HM | `client@acme.com` | set via `SEED_CLIENT_PASSWORD` |
| Delivery Head | `head@techrecruit.com` | set via `SEED_DELIVERY_PASSWORD` |

### Running Tests

```bash
cd backend
.venv310\Scripts\pytest tests/ -v
```

**Result: 45 passed in ~12s**

## Architecture

Modular monolith — one FastAPI process, Alembic migrations, PostgreSQL 15, Next.js 15 frontend.

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, Lucide icons |
| Backend | Python 3.10, FastAPI, Pydantic v2, SQLAlchemy 2 (asyncio) |
| AI Integration | Provider-independent `LLMProvider` protocol, OpenAI SDK, Pydantic validation |
| Database | PostgreSQL 15 (Docker container mapped to port 5434:5432) |
| Auth | JWT (HS256), Argon2 passwords, server-side refresh tokens |
| Migrations | Alembic |

## API

Interactive OpenAPI documentation available at `http://localhost:8000/docs`.
