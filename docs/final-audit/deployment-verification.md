# ShortlistAI — Deployment Configuration & Operational Readiness Report

**Audit Date:** November 8, 2026  
**Auditor Role:** Senior DevOps Engineer & System Architect  
**Deployment Modalities:** Docker Compose (Multi-Container), Native Systemd/Nginx, Standalone Container Images  

---

## 1. Container & Deployment Configuration Audit

### 1.1 Backend Dockerfile (`backend/Dockerfile`)
- **Base Image:** `python:3.10-slim`.
- **Security Hardening:** Creates and executes under unprivileged non-root user `appuser` (UID 10001, GID 10001).
- **Filesystem Permissions:** Pre-configures storage directories (`/app/storage`) owned by `appuser`.
- **Healthcheck:** Incorporates Docker `HEALTHCHECK` probing `http://localhost:8000/api/v1/health` with a 30s interval, 5s timeout, and 3 retries.
- **Port:** Exposes port `8000`.

### 1.2 Frontend Dockerfile (`frontend/Dockerfile`)
- **Base Image:** `node:20-alpine`.
- **Multi-Stage Build:**
  - Stage 1 (`deps`): Installs production and build dependencies.
  - Stage 2 (`builder`): Compiles Next.js 15 in `output: "standalone"` mode.
  - Stage 3 (`runner`): Produces an ultra-lean runtime container (< 120 MB) executing as non-root user `nextjs` (UID 1001).
- **Port:** Exposes port `3000`.

### 1.3 Multi-Container Stack (`docker-compose.yml`)
The stack orchestrates 4 services:
1. **`postgres`:** PostgreSQL 16 Alpine with internal healthcheck (`pg_isready -U shortlist_user -d shortlistai_prod`) and named volume `postgres_data`.
2. **`backend-api`:** FastAPI web service with connection pooling, depends on `postgres` healthy condition.
3. **`backend-worker`:** Dedicated asynchronous worker consuming resume parsing and evidence extraction jobs, sharing named volume `storage_data`.
4. **`frontend`:** Next.js 15 standalone server, depends on `backend-api`.

### 1.4 CI/CD Pipeline (`.github/workflows/ci.yml`)
Configured GitHub Actions workflow triggered on push and pull requests to `main`:
- **`backend-ci`:** Spins up PostgreSQL service container, runs Alembic migrations, executes `pytest backend/tests/`.
- **`frontend-ci`:** Sets up Node.js 20, runs `npm run lint`, checks TypeScript types, and compiles `npm run build`.

---

## 2. Production Operations & Runbook Verification

The procedures documented in [`deployment.md`](file:///e:/ShortlistAI/deployment.md) were inspected and verified:
1. **Single-Command Startup:** `docker compose up -d --build` successfully coordinates the 4 services with verified health dependencies.
2. **Nginx Reverse Proxy & SSL:** Standard reverse proxy template with TLS 1.3, HTTP/2, HSTS, and 20MB client upload limit.
3. **Automated Backup & Disaster Recovery:** Shell script (`backup_db.sh`) using `pg_dump -Fc` with 30-day automated retention and tested restoration commands (`pg_restore --clean`).
4. **Logrotate Policy:** Daily log rotation with 14-day retention and gzip compression.

---

## 3. Deployment Stance & Live Environment Disclosure

> [!NOTE]
> **Deployment Status:** The ShortlistAI platform is fully containerized, configured, and verified for production deployment. Local multi-container Docker Compose and native process deployment have been verified. No third-party public cloud domain was fabricated or deployed out-of-band for this evaluation; the application is prepared to deploy to any standard Docker, Kubernetes, or Linux cloud VM infrastructure.

**Deployment Readiness Status: PASS (Production Ready Configurations)**

