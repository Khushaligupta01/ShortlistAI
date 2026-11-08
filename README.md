# ShortlistAI

An evidence-based AI resume screening and client shortlist platform for staffing and recruitment firms.

## Status

**Phase 4 Complete** — Bulk Resume Ingestion, Document Parsing, and Candidate Data Extraction fully implemented, tested, and integrated.

## What's Built (Phase 4)

### Bulk Resume Ingestion & Storage
- **Multi-format upload**: Support for PDF and DOCX files with configurable batch limits (up to 500 files, 15MB/file, 250MB per batch).
- **Strict document validation**: File signatures (magic bytes `%PDF-`, `PK\x03\x04`), extension, MIME type, empty file, and corruption verification.
- **Private storage abstraction**: `LocalStorageService` with strict directory traversal prevention (`is_relative_to`), UUID-based storage keys, and non-public storage directories.
- **Authorized document downloads**: `GET /api/v1/resumes/{id}/document` with RBAC verification and organization boundary isolation.

### Document Parsing & Text Normalization
- **PDF extraction**: PyMuPDF (`fitz`) multi-page extraction, encrypted document detection, and scanned image OCR detection (`OCR_REQUIRED`) without fabricating text.
- **DOCX extraction**: `python-docx` extraction preserving paragraphs, structured table cells, and document flow.
- **Text normalization**: Unicode NFKC, bullet normalization, excessive whitespace collapsing, while strictly preserving technical terms (`C++`, `.NET`), dates, and employment headers.

### Multi-Level Duplicate Detection
- **Level 1 (Exact file)**: SHA-256 content hashing linking to existing resumes without redundant re-processing.
- **Level 2 (Candidate match)**: Normalized email and E.164 phone number resolution against existing database records.
- **Level 3 (Content similarity)**: Token-based Jaccard similarity (≥ 0.85 threshold) for detecting resume text overlaps.

### Structured Candidate Data Extraction
- **Pydantic schema validation**: Strict schemas for candidate profiles, skills with verbatim resume evidence, employment timelines, educations, and certifications.
- **Strict non-hallucination rules**: Missing attributes remain `null`; notice periods, dates, age, and gender are never inferred or fabricated.
- **Reliable fallback**: Zero-hallucination deterministic regex extractor when external AI services are unconfigured.

### Background Queue Worker Architecture
- **Persistent PostgreSQL job queue**: `ResumeProcessingJob` table with atomic row-level claiming (`SELECT FOR UPDATE SKIP LOCKED`).
- **Worker service**: Bounded concurrency (`WORKER_CONCURRENCY=5`), stale claim timeout reclamation, configurable retries, and batch counter aggregation.
- **CLI worker**: `backend/scripts/run_worker.py` and `backend/app/worker.py` for standalone worker processes.

### Frontend User Interface (Next.js 15)
- **Requisition Candidates Tab**: Switch between "Candidates & Ingestion" and "Scorecard & Requirements" in `/requisitions/[id]`.
- **Drag & Drop Upload Modal**: Real-time client-side validation for file size (15MB), format, and batch limits with upload progress bar.
- **Batch Processing Dashboard**: Real-time status cards (Total, Accepted, Processing, Completed, Duplicates, Failed), per-file status badges, and one-click retry for eligible failures.
- **Candidate Detail & Review Modal**: Full timeline of employment and education, skills badges with verbatim evidence, raw extraction preview, and recruiter review note submission.

### Automated Test Suite
- **82 passing automated tests** in `backend/tests/`:
  - 37 Phase 4 tests (file upload validation, document extraction, text normalization, duplicate detection, AI extraction, background worker, authorization & privacy, end-to-end API, synthetic batch benchmark).
  - 24 Phase 3 AI extraction and scorecard tests.
  - 21 Phase 1 & 2 auth, RBAC, and database tests.
- 14 realistic synthetic test fixtures generated in `backend/tests/fixtures/resumes/`.

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

**Result: 82 passed in ~23s**

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
