# ShortlistAI

An evidence-based AI resume screening and client shortlist platform for staffing and recruitment firms.

## Status

**Phase 2 Complete** — Backend foundation, database, authentication, and frontend shells are implemented.

## What's Built (Phase 2)

### Backend (FastAPI + PostgreSQL)
- 14 database models with full FK constraints, indexes, and unique constraints
- JWT authentication with Argon2 password hashing and server-side refresh tokens
- Role-based access control: Recruiter, Client Hiring Manager, Delivery Head
- Multi-tenant organization isolation enforced at the repository layer
- Security headers (CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- Alembic migrations (initial schema, upgrade + downgrade)
- 21 automated tests — all passing

### Frontend (Next.js 15 + Tailwind CSS)
- Login page connecting to real backend
- Recruiter dashboard (authenticated, org-scoped requisition list)
- Client Hiring Manager portal (role-gated)
- JWT token management with auto-refresh

## Quick Start

### Prerequisites
- Python 3.10
- Node.js 20+
- PostgreSQL 15 (or Docker)

### With Docker (recommended)

```bash
cp backend/.env.example backend/.env
# Edit backend/.env — set JWT_SECRET_KEY and SEED_* passwords
docker-compose up
```

Then seed demo data:
```bash
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
# Create .env.local with: NEXT_PUBLIC_API_URL=http://localhost:8000
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

**Result: 21 passed**

## Architecture

Modular monolith — one FastAPI process, Alembic migrations, PostgreSQL.

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Backend | Python 3.10, FastAPI, Pydantic v2, SQLAlchemy 2 |
| Database | PostgreSQL 15 |
| Auth | JWT (HS256), Argon2 passwords, server-side refresh tokens |
| Migrations | Alembic |

## API

Docs available at `http://localhost:8000/docs` (non-production).

Key endpoints:
- `POST /api/v1/auth/login` — authenticate
- `POST /api/v1/auth/refresh` — refresh tokens
- `POST /api/v1/auth/logout` — revoke session
- `GET /api/v1/auth/me` — current user
- `GET /api/v1/requisitions` — list requisitions (Recruiter/Delivery Head)
- `GET /api/v1/health` — health check
- `GET /api/v1/health/ready` — readiness with DB check

## Next Phase

**Phase 3** — JD intelligence (LLM extraction), scorecard management, full requisition CRUD.

See [`docs/architecture/development-roadmap.md`](docs/architecture/development-roadmap.md) for the full 10-phase plan.
