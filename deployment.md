# ShortlistAI — Production Deployment and Operations Guide

This operational manual documents complete procedures for deploying, maintaining, scaling, and troubleshooting the ShortlistAI platform across local development, containerized stacks, and production cloud environments.

---

## 1. Prerequisites and Minimum System Requirements

### Hardware Requirements
| Resource | Minimum (Development / Staging) | Recommended (Production - 100 concurrent users) | High-Scale Production (1,000+ candidates/day) |
| :--- | :--- | :--- | :--- |
| **CPU Architecture** | x86_64 or ARM64 (2 cores) | x86_64 or ARM64 (4 cores) | x86_64 (8–16 cores) |
| **RAM** | 4 GB | 8 GB | 16–32 GB |
| **Disk Storage** | 20 GB SSD | 50 GB NVMe SSD | 200+ GB NVMe SSD (RAID-10 or Managed EBS) |
| **Network Bandwidth** | 10 Mbps | 100 Mbps symmetric | 1 Gbps symmetric |

### Operating System Compatibility
- **Linux:** Ubuntu 22.04 LTS / 24.04 LTS, Debian 12, RHEL 9, Rocky Linux 9, Amazon Linux 2023.
- **macOS:** macOS Sonoma (14.x) or Sequoia (15.x) on Apple Silicon / Intel.
- **Windows:** Windows 10/11 Pro/Enterprise with WSL2 (Ubuntu 22.04) or native PowerShell 7+.

---

## 2. Software Dependencies

Ensure the following tools are installed on the deployment host:
- **Python:** Version `3.10.x` or `3.11.x` (64-bit).
- **Node.js:** Version `18.x`, `20.x`, or `22.x` LTS.
- **npm:** Version `9.x` or higher (bundled with Node.js).
- **PostgreSQL Server & Client:** Version `15.x` or `16.x`.
- **Docker Engine:** Version `24.0+` or `26.0+` with Docker Compose V2 (`docker compose`).
- **Git:** Version `2.34+`.

---

## 3. Environment Variables Guide

ShortlistAI separates backend configuration (`backend/.env`) from frontend configuration (`frontend/.env.local`).

### Backend Environment Configuration (`backend/.env`)

```env
# ==============================================================================
# ENVIRONMENT & CORE SETTINGS
# ==============================================================================
ENVIRONMENT=production                 # development | test | production
DEBUG=false                            # Set false in production
SECRET_KEY=change-this-to-a-64-character-cryptographically-secure-random-token
ALGORITHM=HS256                        # JWT signing algorithm
ACCESS_TOKEN_EXPIRE_MINUTES=60         # Recruiter/Client session token TTL
REFRESH_TOKEN_EXPIRE_DAYS=7            # Refresh token TTL

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================
DATABASE_URL=postgresql+asyncpg://shortlist_user:SecurePassword123!@localhost:5432/shortlistai_prod
DB_POOL_SIZE=20                        # Base database connection pool size
DB_MAX_OVERFLOW=10                     # Overflow connections above pool size
DB_POOL_RECYCLE=1800                   # Recycle connections every 30 minutes

# ==============================================================================
# CORS & FRONTEND ORIGINS
# ==============================================================================
ALLOWED_ORIGINS=["https://app.shortlistai.com","https://client.shortlistai.com"]

# ==============================================================================
# DOCUMENT STORAGE CONFIGURATION
# ==============================================================================
STORAGE_DIR=storage                    # Relative or absolute path for file uploads
MAX_UPLOAD_SIZE_MB=15                  # Maximum allowable resume file size in MB

# ==============================================================================
# AI PROVIDER SETTINGS
# ==============================================================================
AI_PROVIDER=openai                     # openai | mock | gemini
OPENAI_API_KEY=sk-proj-your-production-openai-api-key-here
OPENAI_MODEL=gpt-4o-mini               # Cost-effective, high-precision extraction
MOCK_AI_RESPONSE_TIME=0.5              # Latency simulation for mock mode only

# ==============================================================================
# DEMO SEED CREDENTIALS (DEVELOPMENT / STAGING ONLY)
# ==============================================================================
SEED_RECRUITER_PASSWORD=Recruiter@Demo2024!
SEED_CLIENT_PASSWORD=Client@Demo2024!
SEED_DELIVERY_PASSWORD=Delivery@Demo2024!
```

### Frontend Environment Configuration (`frontend/.env.local` or `.env.production`)

```env
# Backend API Base URL reachable by browser client
NEXT_PUBLIC_API_URL=https://api.shortlistai.com/api/v1

# Node execution environment
NODE_ENV=production
```

---

## 4. Database Setup and Initialization

### Step 1: Install and Initialize PostgreSQL
On Ubuntu / Debian:
```bash
sudo apt update && sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable --now postgresql
```

### Step 2: Create User and Database
Open the PostgreSQL prompt:
```bash
sudo -u postgres psql
```
Execute the provisioning script:
```sql
CREATE USER shortlist_user WITH PASSWORD 'SecurePassword123!';
CREATE DATABASE shortlistai_prod OWNER shortlist_user;
GRANT ALL PRIVILEGES ON DATABASE shortlistai_prod TO shortlist_user;
\c shortlistai_prod
GRANT ALL ON SCHEMA public TO shortlist_user;
\q
```

---

## 5. Database Migration Execution (Alembic)

All schema changes are tracked with versioned Alembic migrations.

```bash
cd backend
source .venv/bin/activate  # Or .venv\Scripts\Activate.ps1 on Windows

# Check current migration revision
alembic current

# Run all pending migrations up to latest head
alembic upgrade head
```

To rollback a migration if needed:
```bash
# Rollback one migration step
alembic downgrade -1
```

---

## 6. Database Seeding Instructions

To populate the database with standardized demo roles, organizations, requisitions, scorecards, sample candidates, and audit records:

```bash
cd backend
python scripts/seed.py
```

Expected Output:
```text
==================================================
   ShortlistAI Database Seeder
==================================================
[*] Connected to database.
[+] Created / verified organizations: TechRecruit Staffing, Acme Corp, Starlight Health.
[+] Created / verified demo users:
    - Recruiter:     recruiter@techrecruit.com  / Recruiter@Demo2024!
    - Delivery Head: head@techrecruit.com       / Delivery@Demo2024!
    - Client HM:     client@acme.com            / Client@Demo2024!
[+] Created sample requisition: Senior Backend Engineer (REQ-2024-001)
[+] Seeded 10 benchmark candidates across High, Medium, and Low criteria match.
[+] Generated initial consent and audit governance logs.
==================================================
```

---

## 7. Backend Local Development Startup

```bash
cd backend

# 1. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start development server with auto-reload
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API Documentation will be available at:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## 8. Frontend Local Development Startup

```bash
cd frontend

# 1. Install dependencies
npm ci

# 2. Start Next.js development server
npm run dev -- -p 3000
```
Open `http://localhost:3000` in your web browser.

---

## 9. Background Worker Execution

ShortlistAI offloads resume text extraction, OCR, and AI evidence evaluation to asynchronous background workers to ensure zero latency impact on HTTP request threads.

```bash
cd backend
python scripts/run_worker.py
```
In a production deployment, the background worker should run as an isolated systemd daemon or containerized service with independent auto-restart policies.

---

## 10. Docker Compose Deployment (Single-Command Setup)

For containerized staging and production deployments, run the entire stack with Docker Compose:

```bash
# 1. Clone repository and verify environment files
cp backend/.env.production.example backend/.env
cp frontend/.env.production.example frontend/.env.local

# 2. Build and launch all services in detached mode
docker compose up -d --build

# 3. Verify container status
docker compose ps

# 4. View real-time aggregated logs
docker compose logs -f
```

The stack runs 4 primary services:
1. `postgres`: PostgreSQL 16 Alpine database with health checks and persistent volume `postgres_data`.
2. `backend-api`: FastAPI REST API on port `8000`.
3. `backend-worker`: Dedicated asynchronous worker process sharing storage volume `storage_data`.
4. `frontend`: Next.js 15 standalone server on port `3000`.

---

## 11. Production Deployment Considerations

### Reverse Proxy & SSL/TLS Configuration (Nginx)

Place an Nginx reverse proxy in front of the services to terminate SSL/TLS and route traffic:

```nginx
# /etc/nginx/sites-available/shortlistai.conf

server {
    listen 80;
    server_name app.shortlistai.com api.shortlistai.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name app.shortlistai.com;

    ssl_certificate /etc/letsencrypt/live/app.shortlistai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.shortlistai.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Next.js standalone frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name api.shortlistai.com;

    ssl_certificate /etc/letsencrypt/live/api.shortlistai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.shortlistai.com/privkey.pem;

    client_max_body_size 20M;

    # FastAPI backend API
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Systemd Process Manager (Bare-Metal Deployments)

Create `/etc/systemd/system/shortlistai-backend.service`:
```ini
[Unit]
Description=ShortlistAI FastAPI Backend
After=network.target postgresql.service

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/opt/shortlistai/backend
EnvironmentFile=/opt/shortlistai/backend/.env
ExecStart=/opt/shortlistai/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now shortlistai-backend
```

---

## 12. Database Backup and Restore Procedures

### Automated Daily Backup Script (`backup_db.sh`)
```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/shortlistai"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/shortlistai_backup_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"

# Run pg_dump in custom compressed format (-Fc)
PGPASSWORD="${DB_PASSWORD}" pg_dump -h localhost -U shortlist_user -d shortlistai_prod -Fc -f "${BACKUP_FILE}"

# Retain backups for 30 days
find "${BACKUP_DIR}" -type f -name "*.dump" -mtime +30 -delete

echo "[+] Database backup completed successfully: ${BACKUP_FILE}"
```

### Database Restoration Procedure
```bash
# 1. Stop backend services to disconnect active clients
sudo systemctl stop shortlistai-backend

# 2. Restore database from dump file
PGPASSWORD="${DB_PASSWORD}" pg_restore -h localhost -U shortlist_user -d shortlistai_prod --clean --if-exists /var/backups/shortlistai/shortlistai_backup_20261108_120000.dump

# 3. Restart backend service
sudo systemctl start shortlistai-backend
```

---

## 13. Health Check Endpoints and Monitoring

### Endpoints
- **Liveness Probe:** `GET /api/v1/health`
  - Returns `{"status": "ok", "app": "ShortlistAI", "version": "1.0.0"}` with HTTP 200.
  - Used by Kubernetes, AWS ALB, and Docker Compose to verify process vitality.
- **Readiness Probe:** `GET /api/v1/health/ready`
  - Verifies live connectivity to PostgreSQL database and file storage write permissions.

### Monitoring Integration
- Integrates with Prometheus, Grafana, Datadog, or AWS CloudWatch via standard HTTP health probing and structured JSON logging.

---

## 14. Log Management and Log Rotation

### Backend Logging Standard
- Structured logs output to `stdout`/`stderr` adhering to 12-factor application standards.
- Every HTTP request logs method, path, response status, duration (ms), client IP, and authenticated user ID.
- Candidate PII (phone, email, SSN) is strictly redacted from all log streams.

### Logrotate Configuration (`/etc/logrotate.d/shortlistai`)
```text
/var/log/shortlistai/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 appuser appuser
    sharedscripts
    postrotate
        systemctl reload shortlistai-backend > /dev/null 2>&1 || true
    endscript
}
```

---

## 15. Storage Management & Cleanup Policies

- **Resume Uploads Directory:** All candidate documents are stored in `storage/` structured by UUID hashes (`storage/resumes/{org_id}/{candidate_id}.pdf`).
- **File Access Security:** Files are never exposed via public static URLs. File downloads require authenticated pre-signed streaming through `/api/v1/resumes/{id}/download`.
- **GDPR Deletion Policy:** When a candidate exercises their Right to be Forgotten, the backend deletes the physical file from disk using secure unlinking, clears parsed text columns, and anonymizes audit references.

---

## 16. AI Provider Configuration

### Supported Providers
1. **OpenAI (`AI_PROVIDER=openai`):**
   - Requires valid `OPENAI_API_KEY`.
   - Default model: `gpt-4o-mini` (configurable via `OPENAI_MODEL`).
   - Built-in retry handler with exponential backoff for handling `HTTP 429 (Rate Limit)` responses.
2. **Mock AI Provider (`AI_PROVIDER=mock`):**
   - Zero external network calls required.
   - Ideal for CI/CD test runners, development, and air-gapped demo environments.
   - Extracts evidence based on deterministic text scanning.

---

## 17. Troubleshooting Guide

| Issue | Symptoms | Probable Cause | Resolution |
| :--- | :--- | :--- | :--- |
| **Port Conflict (8000 / 3000)** | `bind: address already in use` | Another service is using port 8000 or 3000 | Find process: `lsof -i :8000` (Unix) or `netstat -ano \| findstr 8000` (Win). Terminate process or change port in `.env`. |
| **Database Connection Refused** | `ConnectionRefusedError: [Errno 111]` | PostgreSQL service stopped or invalid port | Check status: `systemctl status postgresql`. Verify port in `DATABASE_URL` matches PostgreSQL `postgresql.conf`. |
| **Alembic Migration Failure** | `Target database is not up to date` | Out-of-sync migration revisions | Run `alembic heads`, check current state via `alembic current`, and resolve merge heads with `alembic stamp head`. |
| **Resume Upload 413 Error** | `HTTP 413 Request Entity Too Large` | Nginx or FastAPI upload limit exceeded | Increase `client_max_body_size 20M;` in Nginx config and `MAX_UPLOAD_SIZE_MB=15` in `backend/.env`. |
| **CORS Policy Rejection** | `Cross-Origin Request Blocked` | Frontend origin missing in `ALLOWED_ORIGINS` | Add frontend domain (e.g., `https://app.shortlistai.com`) to `ALLOWED_ORIGINS` array in `backend/.env`. |

---

## 18. Security Checklist for Production

- [x] **Disable Debug Mode:** Verify `DEBUG=false` in `backend/.env`.
- [x] **Cryptographic Secret Rotation:** Generate a 64-character random key using `openssl rand -hex 32` for `SECRET_KEY`.
- [x] **CORS Origins:** Restrict `ALLOWED_ORIGINS` strictly to authorized customer domains (no wildcard `*`).
- [x] **Non-Root Execution:** Docker containers run as unprivileged `appuser` (backend) and `nextjs` (frontend).
- [x] **Database Isolation:** Database port `5432` bound only to `127.0.0.1` or internal Docker bridge network; never exposed to public internet.
- [x] **Secure HTTPS:** Enforce TLS 1.2+ with HSTS enabled on reverse proxy.
- [x] **Secure Cookies:** Session tokens configured with `Secure`, `HttpOnly`, and `SameSite=Lax`.

---

## 19. Scaling Considerations

### Horizontal Backend Scaling
The FastAPI backend is completely stateless. Additional backend API instances can be deployed behind a load balancer (AWS ALB, Nginx, or HAProxy) with zero session stickiness required.

### Database Connection Pooling
SQLAlchemy 2.0 connection pool is configured via `DB_POOL_SIZE` (default 20) and `DB_MAX_OVERFLOW` (default 10). For deployments exceeding 500 concurrent connections, place **PgBouncer** between the backend workers and PostgreSQL.

### Frontend CDN Caching
Next.js static assets (`/_next/static/*`) are built with immutable hashes and can be cached aggressively at Cloudflare / AWS CloudFront edge locations with `Cache-Control: public, max-age=31536000, immutable`.

