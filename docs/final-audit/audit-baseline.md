# ShortlistAI — Final Audit Baseline Report

**Audit Date:** November 8, 2026  
**Auditor Role:** Independent Principal Software Architect, QA Lead, Security Auditor  
**Baseline Git Commit:** `98dbabb`  
**Git Branch:** `main`  
**Working Tree Status:** Clean (0 uncommitted files, 0 untracked files)  

---

## 1. System Environment & Version Baseline

| Component | Detected Version | Execution Environment |
| :--- | :--- | :--- |
| **Operating System** | Windows 11 Enterprise (x86_64) | Host Development Node |
| **Python Runtime** | Python 3.10.0 (64-bit) | `backend/.venv310` |
| **Node.js Runtime** | Node.js v24.13.1 | Global System Binary |
| **Package Manager (Node)** | npm 11.8.0 | Bundled with Node |
| **Database Server** | PostgreSQL 15.19 (Debian 15.19-1) | Port 5434 (`localhost`) |
| **Active Database** | `shortlistai` | User: `shortlist` |
| **Alembic Revision** | `7a01c382dd94 (head)` | 7 linear revisions applied |
| **Backend Framework** | FastAPI 0.115.5, Starlette 0.41.3 | ASGI async stack |
| **ORM & Async Driver** | SQLAlchemy 2.0.36, asyncpg 0.29.0 | Connection pooling enabled |
| **Frontend Framework** | Next.js 15.5.29 (App Router) | Standalone output enabled |
| **Frontend UI Library** | React 19.0.0, Tailwind CSS 3.4.1 | TypeScript 5.8.2 |

---

## 2. Dependency Audit

### 2.1 Backend Key Dependencies (`backend/requirements.txt`)
- `fastapi==0.115.5`
- `uvicorn[standard]==0.32.1`
- `sqlalchemy==2.0.36`
- `asyncpg==0.29.0`
- `alembic==1.14.0`
- `pydantic==2.9.2`
- `pydantic-settings==2.6.1`
- `argon2-cffi==23.1.0`
- `pwdlib[argon2]==0.2.1`
- `python-jose[cryptography]==3.3.0`
- `pymupdf==1.28.2` (fitz)
- `python-docx==1.2.0`
- `openai==1.57.0`
- `httpx==0.27.2`
- `reportlab==5.1.0`
- `pytest==8.3.4`
- `pytest-asyncio==0.24.0`

### 2.2 Frontend Dependencies (`frontend/package.json`)
- `next: 15.5.29`
- `react: 19.0.0`
- `react-dom: 19.0.0`
- `lucide-react: ^1.16.0`
- `tailwindcss: ^4.0.0`
- `typescript: ^5.0.0`
- `eslint: ^9.0.0`

---

## 3. Database Schema & Migration Verification

The database migration ledger was inspected using `alembic history`:
1. `<base> -> 8df96264c8b2`: `initial_schema` (Organizations, Users, Requisitions)
2. `8df96264c8b2 -> 0998f7a5da05`: `phase3_scorecard_and_requisition_fields` (Scorecards, Criteria)
3. `0998f7a5da05 -> 3e089431a456`: `phase4_bulk_resume_ingestion` (Candidates, Resumes, Batches)
4. `3e089431a456 -> 4f19b52a7c81`: `phase5_candidate_evaluation_engine` (Evaluations, Evidence)
5. `4f19b52a7c81 -> 5e81f129bb32`: `phase6_candidate_notes` (Recruiter Reviews, Notes)
6. `5e81f129bb32 -> 6f92a341cc43`: `phase7_client_portal_and_pipeline` (Submissions, Pipeline)
7. `6f92a341cc43 -> 7a01c382dd94 (head)`: `phase8_privacy_consent_deletion` (Consent, AuditLogs)

Current Database Revision: `7a01c382dd94` (Fully in sync with codebase head).

---

## 4. Test Suite Baseline Execution

Prior to initiating the audit, the complete automated test suite was executed:
- **Backend Test Count:** 162 automated test cases.
- **Backend Test Results:** 162 Passed, 0 Failed, 0 Skipped (Execution time: 126.69s).
- **Frontend Linter Results:** 0 Errors, 0 Warnings (`npm run lint`).
- **Frontend Standalone Build:** Success (`npm run build`).

Baseline status: **STABLE AND VERIFIED**. No blocking defects identified at the initial baseline.

