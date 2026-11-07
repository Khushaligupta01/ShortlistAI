# ShortlistAI — Backend

FastAPI backend for the ShortlistAI evidence-based AI resume screening platform.

## Prerequisites

- Python 3.10+ (3.10 recommended — 3.14 lacks pre-built wheels for key packages)
- PostgreSQL 15 (or Docker)

## Quick Start

### 1. Create virtual environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Unix:
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set your DATABASE_URL and JWT_SECRET_KEY
```

### 4. Run database migrations

```bash
alembic upgrade head
```

### 5. Seed demo data

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

Tests use SQLite in-memory — no PostgreSQL required:

```bash
pytest tests/ -v
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | SQLite dev DB |
| `JWT_SECRET_KEY` | JWT signing secret (min 32 chars) | dev-only default |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token TTL | `15` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token TTL | `7` |
| `CORS_ORIGINS` | Allowed CORS origins (JSON array) | `["http://localhost:3000"]` |
| `APP_ENV` | Environment name | `development` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Architecture

Modular monolith with:
- `app/api/v1/endpoints/` — FastAPI routers (thin layer)
- `app/services/` — Business logic
- `app/repositories/` — Database queries (always org-scoped)
- `app/models/` — SQLAlchemy ORM models
- `app/schemas/` — Pydantic request/response schemas
- `app/core/` — Config, security, exceptions

## Security Notes

- Passwords hashed with Argon2 via `pwdlib`
- JWT tokens signed with HS256 (upgrade to RS256 in Phase 10)
- Refresh tokens stored as SHA-256 hash in DB (single-use)
- All routes RBAC-protected via `require_role` dependency
- Multi-tenant isolation enforced at repository layer
- Security headers applied on every response
