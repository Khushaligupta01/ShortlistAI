# ShortlistAI — Backend

FastAPI backend for the ShortlistAI evidence-based AI resume screening and scorecard engine platform.

## Prerequisites

- Python 3.10+ (3.10 recommended)
- PostgreSQL 15 (Docker or local instance)

## Quick Start

### 1. Create virtual environment

```bash
python -m venv .venv310
# Windows:
.venv310\Scripts\activate
# Unix:
source .venv310/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and configure DATABASE_URL, JWT_SECRET_KEY, and AI_* keys
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Seed demo data (including Section 15 Senior Java Developer sample)

```bash
python scripts/seed.py
```

Demo accounts created:
- **Recruiter**: `recruiter@techrecruit.com` / (set in SEED_RECRUITER_PASSWORD)
- **Client HM**: `client@acme.com` / (set in SEED_CLIENT_PASSWORD)
- **Delivery Head**: `head@techrecruit.com` / (set in SEED_DELIVERY_PASSWORD)

### 6. Start the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Start the background worker (Phase 4 & 5)

In a separate terminal:
```bash
python scripts/run_worker.py
```

API docs: http://localhost:8000/docs

## Running Tests

```bash
pytest tests/ -v
```

All 140 automated tests pass across:
- **Phase 1 & 2**: Auth, organization multi-tenancy, RBAC, and database models.
- **Phase 3**: AI JD extraction, dynamic scorecard versioning, and approval workflows.
- **Phase 4**: Bulk resume upload, document parsing (PyMuPDF & python-docx), text normalization, multi-level duplicate detection, AI profile extraction, and background queue workers.
- **Phase 5**: Grounded AI evidence extraction, anti-fabrication token verification, controlled skill normalization, pure deterministic mathematical scoring engine (100 pts), multi-attribute candidate ranking, client PII masking, and recruiter reviews.
- **Phase 6**: Recruiter dashboard metrics aggregation, processing health telemetry, multi-attribute candidate search and deterministic sorting, candidate profile & multi-version evaluation history, and confidential recruiter notes with author permissions.
- **Phase 7**: Secure client shortlist portal, server-side candidate PII masking (`Candidate CND-XXXXX`), recruiter client submissions, 9-stage Kanban pipeline, client decisions (Shortlist, Reject, Interview, Info), inquiry resolution workflows, and delivery head conversion funnel metrics.

To run live PostgreSQL end-to-end verification:
```bash
python scripts/verify_phase3.py
```
