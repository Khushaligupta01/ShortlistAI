# ShortlistAI — Product Demonstration Walkthrough Script

**Duration:** 5–7 minutes  
**Target Audience:** Technical Recruiters, Hiring Managers, AI Governance Auditors, and Engineering Leaders  
**System Version:** Release 1.0 (Phase 10 Production Candidate)  
**Demo Credentials:**
- **Recruiter:** `recruiter@techrecruit.com` / `Recruiter@Demo2024!`
- **Client Hiring Manager:** `client@acme.com` / `Client@Demo2024!`
- **Delivery Head:** `head@techrecruit.com` / `Delivery@Demo2024!`

---

## Demonstration Overview & Narrative

ShortlistAI transforms high-volume resume screening from a subjective, error-prone manual triage into an evidence-grounded, explainable, and privacy-first workflow. 

Unlike traditional ATS solutions that rely on opaque keyword filters or generative LLMs that invent qualifications, ShortlistAI employs a **dual-engine architecture**:
1. An LLM acts strictly as an **Evidence Extractor**, locating exact resume verbatim text matching specific job criteria.
2. A deterministic **Rule & Scoring Engine** computes transparent scores, enforces hard knockout requirements, and calculates normalized rankings.

---

## Minute-by-Minute Walkthrough

### Minute 0:00 – 1:00 | Authentication & Multi-Tenant Recruiter Workspace
- **Action:** Open `http://localhost:3000/login`.
- **Narration:** *"We begin at the login screen. ShortlistAI supports secure multi-tenant role-based access control. Let's log in as Alice Recruiter from TechRecruit Staffing."*
- **Steps:**
  1. Enter `recruiter@techrecruit.com` and `Recruiter@Demo2024!`.
  2. Click **Sign In**.
  3. Lands on `/dashboard`.
- **Key Highlights:**
  - Notice the active requisition overview: Total Requisitions, Active Pipeline Candidates, Pending Consent, and Average Match Score.
  - Organization isolation guarantees that candidate records, client feedback, and scorecards never leak across client boundaries.

---

### Minute 1:00 – 2:00 | Requisition Setup & Automated Scorecard Rubric
- **Action:** Navigate to **Requisitions** (`/requisitions`) and view **Senior Backend Engineer** or click **New Requisition** (`/requisitions/new`).
- **Narration:** *"When opening a new requisition, recruiters upload or paste the job description. ShortlistAI analyzes the requirements and extracts a structured 4-pillar scorecard."*
- **Steps:**
  1. Open the Senior Backend Engineer requisition.
  2. Inspect the **Scorecard Rubric**:
     - **Required Skills (Weight 40%):** Python, FastAPI, PostgreSQL, AsyncIO.
     - **Preferred Skills (Weight 20%):** Docker, Kubernetes, Celery, Redis.
     - **Experience & Seniority (Weight 20%):** Minimum 5 years production experience.
     - **Education & Certifications (Weight 20%):** Degree in Computer Science or equivalent.
  3. Point out the hard knockout constraint: *"Must have at least 5 years of backend engineering experience."*
- **Key Highlights:**
  - Weights are normalized to 100%.
  - Knockout rules ensure unqualified applicants are flagged immediately before recruiter review.

---

### Minute 2:00 – 3:30 | Resume Batch Ingestion & Evidence-Grounded Ranking
- **Action:** Navigate to **Candidates** (`/candidates`) or the candidate table within the active requisition.
- **Narration:** *"Now let's examine candidate evaluation. ShortlistAI ingested sample resumes across PDF and DOCX formats with asynchronous background parsing."*
- **Steps:**
  1. Review the candidate leaderboard:
     - **Marcus Vance:** Match Score **92.5%** — Status: **Shortlisted**
     - **Elena Rostova:** Match Score **89.0%** — Status: **Shortlisted**
     - **Priya Patel:** Match Score **86.5%** — Status: **Shortlisted**
     - **Devon Miller:** Match Score **74.0%** — Status: **Hold**
     - **Samir Roy:** Match Score **44.0%** — Status: **Rejected**
  2. Click on **Marcus Vance** to inspect candidate evidence (`/candidates/[id]`).
- **Key Highlights:**
  - Every single score point is backed by **verbatim quotes** extracted directly from Marcus's resume.
  - The AI does *not* assign a score; it only surfaces verbatim citations.
  - The deterministic mathematical engine calculates criteria match: `Weighted Sum = Σ(Criterion Score × Weight)`.
  - Missing skills receive a neutral score (0), not a fabricated negative hallucination.

---

### Minute 3:30 – 4:30 | Recruiter Decision Pipeline & Client Submission
- **Action:** Navigate to **Pipeline** (`/pipeline`).
- **Narration:** *"The pipeline view gives recruiters an interactive Kanban workspace to manage candidate progression through screening stages."*
- **Steps:**
  1. Show candidate columns: `Unreviewed` → `Screening` → `Shortlist` → `Submitted to Client` → `Client Review`.
  2. Demonstrate submitting top candidate Marcus Vance to client **Acme Corp**.
  3. Show the submission confirmation modal with privacy masking options (masking candidate contact details and personal PII).
- **Key Highlights:**
  - Candidates are protected by blind screening options to prevent unconscious recruiter bias.
  - Full audit logging records the state transition.

---

### Minute 4:30 – 5:30 | Client Portal Review & Feedback Loop
- **Action:** Log out and log in as client hiring manager: `client@acme.com` / `Client@Demo2024!`.
- **Narration:** *"Now let's switch perspectives to Bob, Hiring Manager at Acme Corp. Bob logs into the dedicated Client Shortlist Portal."*
- **Steps:**
  1. Open `http://localhost:3000/client` and `/client/submissions`.
  2. Open the submission for Marcus Vance.
  3. View the **Executive Summary**: Match percentage, key strengths, experience summary, and evaluation breakdown.
  4. Note that direct candidate email and phone number are securely redacted based on client engagement agreements.
  5. Click **Request Interview** and enter interview availability notes: *"Strong system architecture background. Request 45-min technical screening."*
- **Key Highlights:**
  - Clients can accept, reject, or request interviews directly in the portal.
  - Recruiter dashboard updates instantly via the unified PostgreSQL data layer.

---

### Minute 5:30 – 6:30 | Responsible AI, GDPR Privacy & Audit Governance
- **Action:** Log back in as `recruiter@techrecruit.com` and open **Privacy** (`/privacy`) and **Governance** (`/governance`).
- **Narration:** *"Finally, let's look at enterprise governance, candidate privacy, and auditability."*
- **Steps:**
  1. Inspect **Consent Tracking**:
     - View consent status: `Granted`, `Pending`, or `Withdrawn`.
     - Show candidate self-service consent confirmation links (`/public/consent/[token]`).
  2. Inspect **Data Deletion / Right to be Forgotten (GDPR Art. 17)**:
     - Demonstrate initiating a candidate deletion request.
     - Show how personal PII, extracted text, and document files in storage are hard-deleted, while historical audit hashes remain anonymized.
  3. Inspect **Governance Audit Log**:
     - Every login, resume upload, evaluation execution, client submission, and consent change is immutably timestamped with user ID and client IP.
- **Key Highlights:**
  - Zero PII leakage.
  - Explainable AI metrics compliant with EU AI Act High-Risk Employment AI requirements.

---

## Q&A and Technical Verification Wrap-Up
- **Backend Architecture:** FastAPI async REST endpoints, SQLAlchemy 2.0 with PostgreSQL, Alembic migrations.
- **Frontend Architecture:** Next.js 15 App Router, TypeScript, Tailwind CSS, Lucide icons.
- **AI Engine:** Dual-mode architecture supporting both live OpenAI/Gemini providers and an offline Mock AI provider for air-gapped unit testing and local development.
- **Deployment:** Fully containerized via multi-stage Dockerfiles and Docker Compose.
