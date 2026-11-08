# ShortlistAI — Production Deployment and Operations Guide

**GitHub Repository:** https://github.com/Khushaligupta01/ShortlistAI  
**Clone URL:** `git clone https://github.com/Khushaligupta01/ShortlistAI.git`  
**Document Version:** 1.0 (Production Release Candidate)  
**Status:** Verified & Tested  

This operational manual documents complete, tested procedures for deploying, maintaining, running, testing, and troubleshooting the ShortlistAI platform across local development, containerized stacks, and production environments.

---

## 1. Prerequisites & Required Software

| Component | Required Version | Verification Command | Purpose |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10.x or 3.11.x (64-bit) | `python --version` | FastAPI backend, parsing & deterministic scoring |
| **Node.js** | 18.x, 20.x, or 22.x LTS | `node --version` | Next.js 15 frontend application |
| **npm** | 9.x or higher | `npm --version` | Frontend package manager |
| **PostgreSQL** | 15.x or 16.x | `psql --version` | Primary relational database |
| **Git** | 2.34+ | `git --version` | Version control & repository tracking |
| **Docker & Compose** *(Optional)* | Docker 24.0+, Compose v2 | `docker compose version` | Containerized single-command execution |

---

## 2. Repository Cloning

```bash
# Clone the authoritative GitHub repository
git clone https://github.com/Khushaligupta01/ShortlistAI.git

# Enter project root directory
cd ShortlistAI
```

---

## 3. Environment Variables Specification

ShortlistAI separates configuration into two distinct files. In accordance with security standards, **only variable names, types, and descriptions are documented below; never hardcode real secrets or private API keys.**

### 3.1 Backend Configuration (`backend/.env`)

| Variable Name | Type / Allowed Values | Required | Description / Example Placeholder |
| :--- | :--- | :---: | :--- |
| `ENVIRONMENT` | `development` \| `test` \| `production` | Yes | Target operating environment. Default: `development`. |
| `DEBUG` | `true` \| `false` | Yes | Controls verbose stack traces. Must be `false` in production. |
| `SECRET_KEY` | 64-character hex string | Yes | Cryptographic HMAC-SHA256 signing key for JWT tokens. Generate with `openssl rand -hex 32`. |
| `ALGORITHM` | `HS256` | Yes | JWT signing algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Integer (e.g. `60`) | Yes | Recruiter and client JWT access token TTL in minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Integer (e.g. `7`) | Yes | Refresh token TTL in days. |
| `DATABASE_URL` | PostgreSQL async connection URI | Yes | Format: `postgresql+asyncpg://<DB_USER>:<DB_PASSWORD>@<DB_HOST>:<DB_PORT>/<DB_NAME>`. |
| `DB_POOL_SIZE` | Integer (e.g. `20`) | No | SQLAlchemy connection pool size. Default: `20`. |
| `DB_MAX_OVERFLOW` | Integer (e.g. `10`) | No | Max pool overflow connections. Default: `10`. |
| `DB_POOL_RECYCLE` | Integer (e.g. `1800`) | No | Connection recycle interval in seconds (30 mins). |
| `ALLOWED_ORIGINS` | JSON list of URL strings | Yes | CORS allowed origins, e.g. `["http://localhost:3000","https://app.shortlistai.com"]`. |
| `STORAGE_DIR` | Directory path string | Yes | Directory for uploaded resume files. Default: `storage`. |
| `MAX_UPLOAD_SIZE_MB` | Integer (e.g. `15`) | Yes | Maximum allowed upload size per file in MB. Default: `15`. |
| `AI_PROVIDER` | `openai` \| `mock` | Yes | AI evidence extraction backend. Use `mock` for offline/tests, `openai` for production. |
| `OPENAI_API_KEY` | String | If `openai` | OpenAI API credential. Format: `sk-proj-<YOUR_API_KEY>`. Leave empty if using `mock`. |
| `OPENAI_MODEL` | String | No | Model name. Default: `gpt-4o-mini`. |
| `MOCK_AI_RESPONSE_TIME` | Float (e.g. `0.2`) | No | Latency simulation in seconds for `mock` provider. |

#### Backend Template File Creation
```bash
# Create backend environment configuration from template
cp backend/.env.example backend/.env
```

### 3.2 Frontend Configuration (`frontend/.env.local`)

| Variable Name | Type / Allowed Values | Required | Description / Example Placeholder |
| :--- | :--- | :---: | :--- |
| `NEXT_PUBLIC_API_URL` | URL string | Yes | Publicly reachable base URL of the FastAPI backend. Local default: `http://localhost:8000/api/v1`. Production: `https://api.yourdomain.com/api/v1`. |
| `NODE_ENV` | `development` \| `production` | Yes | Node execution environment. |

#### Frontend Template File Creation
```bash
# Create frontend environment configuration
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1" > frontend/.env.local
echo "NODE_ENV=development" >> frontend/.env.local
```

---

## 4. Database Setup & Initialization (PostgreSQL)

### 4.1 Provision Database & Role
Open `psql` as administrator:
```bash
# On Linux / macOS:
sudo -u postgres psql

# On Windows (PowerShell):
psql -U postgres
```

Execute SQL provisioning commands:
```sql
-- Create application user
CREATE USER shortlist WITH PASSWORD '<CHOOSE_STRONG_PASSWORD>';

-- Create development database
CREATE DATABASE shortlistai_dev OWNER shortlist;

-- Grant schema privileges
GRANT ALL PRIVILEGES ON DATABASE shortlistai_dev TO shortlist;
\c shortlistai_dev
GRANT ALL ON SCHEMA public TO shortlist;
\q
```

---

## 5. Backend Setup, Migration & Seeding

### 5.1 Python Virtual Environment
```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Linux / macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# On Windows (CMD):
.\.venv\Scripts\activate.bat

# Upgrade pip and install all dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

### 5.2 Execute Database Migrations (Alembic)
```bash
# Verify current migration status
alembic current

# Run all pending migrations up to head
alembic upgrade head
```

### 5.3 Seed Demo Accounts & Benchmark Data
Populate the database with verified multi-tenant demo organizations, scorecards, sample candidates, and audit logs:
```bash
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
    - Compliance:    compliance@shortlist.ai    / ShortlistAI@2026!
[+] Created sample requisition: Senior Backend Engineer
[+] Seeded benchmark candidates across High, Medium, and Low criteria match.
[+] Generated initial consent and audit governance logs.
==================================================
```

---

## 6. Verified Demo Login Credentials

The following credentials have been seeded into the PostgreSQL database and tested against `/api/v1/auth/login`:

| Role | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- |
| **Recruiter** | `recruiter@techrecruit.com` | `Recruiter@Demo2024!` | Full agency recruiting workspace, requisition creation, candidate ingestion, Kanban pipeline |
| **Client Hiring Manager** | `client@acme.com` | `Client@Demo2024!` | Acme Corp client portal, masked candidate submissions, interview requests |
| **Delivery Head** | `head@techrecruit.com` | `Delivery@Demo2024!` | Agency-wide analytics, cross-client pipeline velocity, audit oversight |
| **Super Admin / Privacy** | `compliance@shortlist.ai` | `ShortlistAI@2026!` | GDPR consent lifecycle, Article 17 deletion requests, audit trails |

*(Alternative alias credentials with password `ShortlistAI@2026!` are also seeded for `recruiter@shortlist.ai`, `client@acmecorp.com`, and `delivery@shortlist.ai`.)*

---

## 7. Starting the Application (Local Development)

### 7.1 Start Backend API Server
In a dedicated terminal:
```bash
cd backend
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Interactive API documentation:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health check: `http://127.0.0.1:8000/api/v1/health`

### 7.2 Start Background Ingestion Worker (Optional for Local Asynchronous Processing)
In a dedicated terminal:
```bash
cd backend
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1
python scripts/run_worker.py
```

### 7.3 Start Frontend Development Server
In another dedicated terminal:
```bash
cd frontend

# Install Node dependencies
npm ci

# Start Next.js development server
npm run dev -- -p 3000
```
Open your browser to: `http://localhost:3000`

---

## 8. Executing Tests & Verification Commands

### 8.1 Backend Test Suite (Pytest — 162 Tests)
```bash
cd backend
python -m pytest tests -v
```
All 162 tests verify authentication, RBAC, scorecard criteria normalization, PDF/DOCX extraction, deterministic scoring, knockout enforcement, client portal isolation, and GDPR deletion.

### 8.2 Real End-to-End HTTP Audit
Executes real HTTP requests across 8 critical workflows against the live backend:
```bash
cd backend
python scripts/audit_e2e_runner.py
```

### 8.3 500-Resume Batch Capacity & Limit Check
Validates 500-resume boundary enforcement and rejection of 501+ uploads:
```bash
cd backend
python scripts/test_500_resumes.py
```

### 8.4 Frontend Linting & Production Build
```bash
cd frontend

# Run ESLint validation
npm run lint

# Run Next.js production compilation
npm run build
```

---

## 9. Containerized Single-Command Deployment (Docker Compose)

For instant staging or production execution with zero manual host configuration:

```bash
# 1. Prepare environment configuration from production templates
cp backend/.env.production.example backend/.env
cp frontend/.env.production.example frontend/.env.local

# 2. Build and launch all 4 containers in detached mode
docker compose up -d --build

# 3. Check container status
docker compose ps

# 4. View aggregated service logs
docker compose logs -f
```

The Docker stack deploys:
1. `postgres`: PostgreSQL 16 Alpine on port `5432` with health checks.
2. `backend-api`: FastAPI REST API on port `8000`.
3. `backend-worker`: Asynchronous background worker process.
4. `frontend`: Next.js 15 standalone server on port `3000`.

To stop the containers:
```bash
docker compose down
```

---

## 10. Production Deployment & Reverse Proxy Architecture

### 10.1 Nginx Reverse Proxy Configuration
Place Nginx in front of the application to terminate SSL/TLS (HTTPS) on port 443 and proxy traffic:

```nginx
# /etc/nginx/sites-available/shortlistai.conf

server {
    listen 80;
    server_name app.shortlistai.com api.shortlistai.com;
    return 301 https://$host$request_uri;
}

# Frontend Application
server {
    listen 443 ssl http2;
    server_name app.shortlistai.com;

    ssl_certificate /etc/letsencrypt/live/app.shortlistai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/app.shortlistai.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

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

# Backend REST API
server {
    listen 443 ssl http2;
    server_name api.shortlistai.com;

    ssl_certificate /etc/letsencrypt/live/api.shortlistai.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.shortlistai.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    client_max_body_size 25M;

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

### 10.2 Systemd Daemon Management (Bare Metal Linux)
Create `/etc/systemd/system/shortlistai-backend.service`:
```ini
[Unit]
Description=ShortlistAI FastAPI Application Server
After=network.target postgresql.service

[Service]
Type=simple
User=appuser
Group=appuser
WorkingDirectory=/opt/shortlistai/backend
EnvironmentFile=/opt/shortlistai/backend/.env
ExecStart=/opt/shortlistai/backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
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

## 11. Database Backup & Disaster Recovery

### 11.1 Automated Backup Script (`backup_db.sh`)
```bash
#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/shortlistai"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/shortlistai_${TIMESTAMP}.dump"

mkdir -p "${BACKUP_DIR}"
PGPASSWORD="${DB_PASSWORD}" pg_dump -h localhost -U shortlist -d shortlistai_dev -Fc -f "${BACKUP_FILE}"

# Retain backups for 30 days
find "${BACKUP_DIR}" -type f -name "*.dump" -mtime +30 -delete
echo "[+] Backup created: ${BACKUP_FILE}"
```

### 11.2 Restore Procedure
```bash
# Stop backend to prevent active connection conflicts
sudo systemctl stop shortlistai-backend

# Restore database from backup archive
PGPASSWORD="${DB_PASSWORD}" pg_restore -h localhost -U shortlist -d shortlistai_dev --clean --if-exists /var/backups/shortlistai/shortlistai_backup.dump

# Restart backend
sudo systemctl start shortlistai-backend
```

---

## 12. Troubleshooting Guide

| Issue | Root Cause | Resolution |
| :--- | :--- | :--- |
| **Port Conflict (8000 / 3000)** | Another process is occupying the port | Check process: `lsof -i :8000` (Unix) or `netstat -ano \| findstr 8000` (Win). Stop process or adjust port. |
| **Database Connection Refused** | PostgreSQL service stopped or credentials incorrect | Verify service: `sudo systemctl status postgresql`. Test connection with `psql -U shortlist -d shortlistai_dev`. |
| **Alembic Version Drift** | Database out of sync with migration scripts | Run `alembic current`, inspect migration heads with `alembic heads`, and apply with `alembic upgrade head`. |
| **Upload Rejected (HTTP 413)** | File exceeds upload ceiling | Ensure file is under 15 MB. In Nginx, set `client_max_body_size 25M;`. In backend, check `MAX_UPLOAD_SIZE_MB`. |
| **CORS Block in Browser** | Frontend origin missing from whitelist | Add your frontend origin (e.g. `http://localhost:3000`) to `ALLOWED_ORIGINS` in `backend/.env`. |

---

*Manual verified for ShortlistAI Release Candidate. Authoritative repository: https://github.com/Khushaligupta01/ShortlistAI*
