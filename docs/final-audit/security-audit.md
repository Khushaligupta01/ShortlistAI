# ShortlistAI — Application Security & Vulnerability Assessment Report

**Audit Date:** November 8, 2026  
**Auditor Role:** Senior Application Security Auditor & Penetration Tester  
**Classification:** Enterprise Security Audit  
**Scope:** Authentication, RBAC, Multi-Tenant Data Isolation, OWASP Top 10, File Uploads, GDPR Privacy, and Container Hardening  

---

## 1. Security Architecture & Threat Assessment

### 1.1 Authentication & Credential Storage
- **Password Hashing:** Implemented with **Argon2id** (`pwdlib[argon2]`), the winner of the Password Hashing Competition. Plaintext passwords are never persisted to disk or emitted in logs.
- **Session Tokens:** Stateless **JWT (JSON Web Tokens)** signed with `HS256` using an environment-loaded `SECRET_KEY`. Session TTL is configured to 60 minutes.
- **Account Enumeration Defense:** Both invalid password attempts and non-existent email queries return identical response payloads: `{"detail": "Incorrect email or password"}`, preventing user enumeration attacks.

### 1.2 Multi-Tenant Isolation & IDOR Protection
- **Tenant Scoping:** All database entities enforce `organization_id` foreign keys.
- **Query Layer Enforcement:** In `backend/app/core/dependencies.py` and endpoint services, all database queries explicitly filter by `WHERE organization_id = :current_user_org_id`.
- **IDOR Testing:** Simulated attempts by User A (Agency 1) to access Requisitions or Candidates belonging to Agency 2 returned `404 Not Found` or `403 Forbidden`.

### 1.3 Injection & Web Vulnerabilities (OWASP Top 10)
- **SQL Injection:** Zero raw string concatenation. 100% of database interactions utilize SQLAlchemy 2.0 async parameterized queries and ORM models, neutralizing SQL injection vectors.
- **Cross-Site Scripting (XSS):** Next.js 15 App Router automatically escapes rendered variables in JSX. Dangerous raw HTML injection (`dangerouslySetInnerHTML`) is prohibited across all UI components.
- **Cross-Origin Resource Sharing (CORS):** The FastAPI CORS middleware explicitly rejects wildcard `*` origins and strictly validates incoming `Origin` headers against `ALLOWED_ORIGINS`.

### 1.4 File Upload Security & Path Traversal
- **File Validation:** In `backend/app/services/document_validation_service.py`, uploads are inspected for file extension (`.pdf`, `.docx`), declared MIME type, and magic bytes. Executable files (`.exe`, `.sh`, `.bat`) are immediately rejected with HTTP 400.
- **Path Traversal Defense:** Uploaded files are renamed using cryptographic UUID v4 strings (`storage/private/{org_id}/{batch_id}/{uuid}.pdf`). Original client filenames are stored strictly as metadata in the database and never used for disk path construction.
- **Storage Isolation:** The upload directory is located outside the web root and is never served as a static asset. Downloads require authenticated pre-signed streaming endpoints.

---

## 2. Vulnerability Findings & Remediation Register

| Vulnerability ID | Vulnerability Description | Severity | Affected Component | Status | Remediation & Fix Applied | Residual Risk |
| :---: | :--- | :---: | :--- | :---: | :--- | :---: |
| **SEC-001** | Client HM Role Escalation to Requisition Creation | **HIGH** | `api/v1/endpoints/requisitions.py` | **RESOLVED** | Enforced `require_role("recruiter", "delivery_head")` dependency on all mutation endpoints. Verified with HTTP 403 test. | None |
| **SEC-002** | Contact PII Leakage in Client Submission View | **HIGH** | `api/v1/endpoints/client_portal.py` | **RESOLVED** | Implemented `MaskedCandidateProfile` schema. Strips email, phone, and address server-side; generates synthetic candidate codes. | None |
| **SEC-003** | Batch Upload File Exhaustion Denial of Service | **MEDIUM** | `api/v1/endpoints/resumes.py` | **RESOLVED** | Enforced `MAX_BATCH_FILES_COUNT = 500` and `MAX_UPLOAD_SIZE_MB = 15`. Batches with 501+ files rejected with HTTP 400. | None |
| **SEC-004** | Prompt Injection via Malicious Resume Content | **MEDIUM** | `app/services/ai_service.py` | **RESOLVED** | Resume text is treated strictly as an unparsed data payload within delimited user prompts; generative scoring is forbidden. | Low |
| **SEC-005** | Accidental Secret Exposure in Repository | **LOW** | Git Working Tree | **RESOLVED** | Pattern scanned all tracked files. Added explicit exclusion rules to `.gitignore`. Verified zero active credentials in repository. | None |
| **SEC-006** | Container Privilege Escalation | **LOW** | Dockerfiles | **RESOLVED** | Containers configured to run under unprivileged non-root users (`appuser` UID 10001, `nextjs` UID 1001). | None |

---

## 3. Candidate Privacy & GDPR Compliance

1. **Consent Lifecycle:** Candidates must grant consent before evaluation or client submission. Consent status is tracked across `PENDING`, `GRANTED`, and `WITHDRAWN`.
2. **Right to be Forgotten (GDPR Art. 17):**
   - Controlled physical disk unlinking of original resume documents.
   - Database scrubbing: candidate `full_name` is scrubbed to `[DELETED]`, `email` and `phone` are set to `NULL`, and `is_anonymized = True`.
   - Immutable audit logs retain an anonymized SHA-256 cryptographic hash for legal traceability.
3. **Audit Log Integrity:** Every security-sensitive operation is hashed using SHA-256. Passwords, tokens, and raw resume text are recursively sanitized from audit payloads before insertion.

---

## 4. Security Audit Verdict

All identified High and Medium severity security considerations have been remediated and verified. The application satisfies enterprise multi-tenant isolation, OWASP Top 10 defenses, secure credential management, and GDPR Article 17 privacy constraints.

**Security Audit Verdict: PASS (Enterprise Grade Security Posture)**

