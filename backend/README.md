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

API docs: http://localhost:8000/docs

## Running Tests

```bash
pytest tests/ -v
```

All 45 automated tests pass (Phase 1 & 2 auth/RBAC/database + Phase 3 AI extraction and dynamic scorecards).

To run live PostgreSQL end-to-end verification:
```bash
python scripts/verify_phase3.py
```
