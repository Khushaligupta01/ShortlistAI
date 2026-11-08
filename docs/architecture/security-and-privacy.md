# Security and Privacy Design — ShortlistAI

## Security Principles

1. **Defense in depth**: Every security control is layered. Tenant isolation exists at the database query layer AND the service layer AND the audit layer.
2. **Fail secure**: If a security check cannot complete (e.g., malware scanner unavailable), the operation is rejected — not allowed.
3. **Auditability first**: No state-changing operation completes without an audit log entry. If the audit write fails, the operation rolls back.
4. **Minimal privilege**: Application DB user has INSERT-only on audit_logs. Read replicas get SELECT-only access.
5. **Explicit over implicit**: Protected attribute exclusion is enforced at runtime by the Scoring Engine itself, not just at the service layer.

---

## Authentication

### Mechanism
- JWT-based stateless authentication with server-side refresh token tracking
- Access tokens: RS256-signed, 15-minute expiry
- Refresh tokens: opaque token ID stored as bcrypt hash in Redis (TTL 7 days)
- Password hashing: Argon2id (primary) or bcrypt (fallback) — never stored plaintext

### Token Lifecycle

```
Login:
  → Issue access_token (JWT, 15min)
  → Issue refresh_token (opaque ID stored hashed in Redis, 7d TTL)

Access token expired:
  → POST /auth/refresh with refresh_token
  → Revoke old refresh token (single-use)
  → Issue new access_token + new refresh_token

Logout:
  → Revoke refresh token from Redis immediately

Password change:
  → Revoke ALL refresh tokens for that user

Account deactivation:
  → Revoke ALL refresh tokens immediately
```

### Account Lockout
- After 10 failed login attempts in a 15-minute rolling window: account locked
- Lock duration: 15 minutes
- Lockout notification: in-app notification sent to the account's email address
- Lock is per-account, not per-IP (IP-level rate limiting is separate: 10 req/min on login endpoint)

### Error Disclosure Prevention
- Invalid credentials always return the same error message and HTTP 401, regardless of whether the email exists or the password is wrong
- This prevents account enumeration

---

## Authorization (RBAC)

### Roles and Permissions Matrix

| Action | Recruiter | Client_HM | Delivery_Head |
|--------|-----------|-----------|---------------|
| Create/manage requisitions | ✅ | ❌ | ❌ |
| Upload resumes | ✅ | ❌ | ❌ |
| View evaluations | ✅ (own org) | ✅ (submitted only) | ✅ (own org) |
| Shortlist candidates | ✅ | ✅ (submitted only) | ❌ |
| Submit to client | ✅ | ❌ | ❌ |
| View pipeline | ✅ (own org) | ✅ (submitted only) | ✅ (all, analytics) |
| Manage pipeline stages | ✅ | ✅ (submitted only) | ❌ |
| Bias monitoring reports | ❌ | ❌ | ✅ |
| Audit log queries | ❌ | ❌ | ✅ |
| Delete candidate data | ✅ | ❌ | ❌ |
| Deactivate user accounts | ❌ | ❌ | ✅ |

### Enforcement
- Every FastAPI route uses `require_role(*roles)` dependency injected via `Depends`
- Role is embedded in the JWT payload at login time
- Organization membership is verified separately (a user can be a Recruiter in org A and a Client_HM in org B)
- Unauthorized attempts return HTTP 403 and write `UNAUTHORIZED_ACCESS_ATTEMPT` to audit log

---

## Multi-Tenant Data Isolation

### Three-Layer Defense

**Layer 1 — Repository Layer** (innermost)
Every repository function requires `org_id` as a parameter and always includes `WHERE org_id = :org_id` in the query. The SQLAlchemy session is scoped per-request.

**Layer 2 — Service Layer**
`assert_org_member(user_id, org_id)` is called at the start of every service function that touches organizational data. This raises `ForbiddenError` if the user is not a member.

**Layer 3 — Cross-Org Access Logging**
When a request attempts to access a resource belonging to a different organization, the system returns HTTP 404 (not 403 — to avoid revealing resource existence) and writes a `CROSS_ORG_ACCESS_ATTEMPT` audit event.

### Database-Level Isolation
The application database user does NOT have access to data across organizations — the `org_id` filter is applied by the ORM and is not bypassable through the application. Row-level security (RLS) in PostgreSQL can be added in a future hardening pass.

### Cross-Org Data Access (Submissions)
When a Recruiter submits a candidate to a client organization:
- A `Submission` record is created with `target_org_id = client_org_id`
- The client org gains read-only access to that candidate's profile for that requisition
- This access is enforced through the `submissions` table join in the Client portal query
- When a submission is withdrawn, the join no longer matches → access is immediately revoked

---

## File Upload Security

### Five-Step Validation Pipeline

Every uploaded file passes all five checks in sequence. Failure at any step rejects the file immediately.

```
Step 1: Extension check
  Allowed: .pdf, .docx only
  Reject: any other extension → HTTP 415

Step 2: MIME type header
  Allowed: application/pdf, application/vnd.openxmlformats-officedocument.wordprocessingml.document
  Reject: mismatch → HTTP 415

Step 3: Magic bytes (file signature)
  PDF: first bytes must be %PDF-
  DOCX: first bytes must be PK\x03\x04 (ZIP-based format)
  Reject: mismatch → HTTP 400

Step 4: Size check
  Max per file: 10 MB
  Max per batch: 1 GB or 500 files (whichever is reached first)
  Reject: exceeds limit → HTTP 413

Step 5: Malware scan
  Tool: ClamAV via python-clamd
  On detection: quarantine file, reject upload, notify recruiter, write MALWARE_DETECTED audit event
  On scanner unavailable: REJECT the file (fail secure — not fail open)
```

### File Storage & Path Traversal Protection (Phase 4)
- Files stored with UUID-based names (`{organization_id}/{batch_id}/{uuid}.{ext}`). Original filename is preserved in the database for recruiter display and download header only.
- Storage root (`data/resumes`) is located outside web-accessible frontend directories.
- Path traversal protection: `LocalStorageService` resolves absolute paths and strictly verifies `resolved_path.is_relative_to(root.resolve())`, raising `ValueError("Path traversal detected")` if any relative segments (`../`, `..\\`) attempt escape.
- Private document download: `GET /api/v1/resumes/{resume_id}/document` requires JWT authentication, enforces RBAC (Recruiter or Delivery Head only; Client Hiring Managers receive 403), and validates organization ownership (cross-organization requests receive 404). Files are streamed directly with safe `Content-Disposition` attachments.
- Storage backend is abstracted via `StorageService` interface allowing seamless swapping with AWS S3 / private object storage in production environments without changing business logic.

---

## API Security

### Rate Limiting (Redis sliding window)

| Endpoint Group | Limit | Window |
|----------------|-------|--------|
| POST /auth/login | 10 requests/IP | 1 minute |
| Auth failure lockout | 10 failures/account | 15 minutes |
| File upload endpoints | 5 uploads/user | 1 minute |
| All other API endpoints | 100 requests/user | 1 minute |

Response on limit exceeded: HTTP 429 with `Retry-After` header.

### HTTP Security Headers

All five headers are required. Absence of any one is a compliance violation.

| Header | Value |
|--------|-------|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:` |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (HTTPS only) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |

### CORS
- Allowed origins restricted to the configured `FRONTEND_URL` environment variable
- Credentials allowed (for cookie-based auth if needed in future)
- Requests from non-configured origins receive HTTP 403

### Input Validation
- All request bodies validated by Pydantic models → HTTP 422 on failure with field-level errors
- Query parameters validated via FastAPI's type annotations
- All database queries via SQLAlchemy ORM — no raw string-interpolated SQL
- File names sanitized; storage paths use UUID keys

---

## Secret Management

### Rules
- Database credentials, JWT signing keys, LLM API keys stored ONLY in environment variables or a secrets manager
- Never embedded in source code or committed configuration files
- `.env` files are gitignored; `.env.example` provides keys without values
- In production, inject via AWS Secrets Manager, HashiCorp Vault, or equivalent at container startup
- Secrets never logged (Pydantic `BaseSettings` fields marked `exclude=True` in `model_config`)

---

## Protected Attribute Exclusion

### Definition
The following fields are classified as Protected Attributes and must never influence scores:

`name`, `gender`, `age`, `photograph`, `marital_status`, `ethnicity`, `nationality`, `date_of_birth`

### Enforcement Pipeline

```
1. Resume Extraction Service extracts full profile (including PAs) → stored in candidates.parsed_profile_json for Recruiter display

2. ProtectedAttributeStripper.strip() creates a clean_profile dict with all PA field names AND values removed

3. Evidence Extraction Service receives ONLY clean_profile

4. Scoring Engine receives ONLY clean_profile
   - At runtime: iterates input field names
   - IF any PA field name found → raises ProtectedAttributeError immediately
   - Score computation aborts
   - Error returned to caller
   - No partial score is ever returned when PA fields are detected
```

### Recruiter Display
- PA fields (name, contact details) are shown on the Recruiter's candidate profile view for reference
- Every PA field is labeled "Excluded from scoring" in the UI
- Client Hiring Managers never see PA fields

---

## Contact Masking

Applied at the service layer (not just serialization) for all Client Hiring Manager responses:

```python
MASKED_FIELDS = {"email", "phone", "address", "home_address"}

# Applied in submission_service.py before any client-org response
def mask_for_client(profile: dict) -> dict:
    return {k: None if k in MASKED_FIELDS else v for k, v in profile.items()}
```

Fields masked: email, phone number, home address.
Fields visible to clients: skills, experience, employment history, education, location (city/region only), notice period, evaluation score, evidence breakdown, recruiter notes.

---

## Consent and Data Privacy

### Consent Records
A `consent_records` entry is created for every candidate at resume upload time, recording:
- Legal basis for processing
- Uploading recruiter's identity and organization
- Timestamp
- Whether the recruiter acknowledged the privacy notice

The privacy notice is displayed to recruiters during the bulk upload flow before they can proceed. Acknowledgment is required.

### Data Deletion / Anonymization
When a deletion request is submitted:
1. Request recorded in audit log immediately
2. Within 30 days: anonymization workflow runs
3. PII fields zeroed/replaced: `full_name → [ANONYMIZED]`, `email → null`, `phone → null`, `address → null`
4. Resume raw text deleted from storage
5. `is_anonymized = true` set on candidate record
6. Evaluation scores and audit log entries retained (anonymized)
7. Completion recorded in audit log

### Data Sent to LLM Providers
The following controls apply to data sent to external LLM providers:
- Protected attributes are stripped BEFORE sending to any LLM service
- When `LLM_STRIP_PII_FOR_PROVIDER = true` (configurable per provider), full PII (name, email, phone) is also stripped from resume text before submission
- Raw resume text + extracted profile are stored locally; only processed payloads are sent to the LLM
- LLM API keys are stored in secrets manager, never in code
- All LLM API calls are made over HTTPS

### What Is Sent to OpenAI
| Data type | Sent to OpenAI? | Notes |
|-----------|----------------|-------|
| Job description text | Yes | No personal data typically |
| Resume raw text | Yes (configurable) | PII stripped when provider policy requires |
| Protected attributes | Never | Stripped before all LLM calls |
| Evaluation scores | Never | Computed locally by Scoring Engine |
| Organization or recruiter names | No | Not included in prompts |

---

## Audit Logging

### Immutability Enforcement
- Application DB user has `INSERT` permission only on `audit_logs` — no UPDATE or DELETE
- No application-layer endpoint exists to modify or delete audit records
- Audit log is write-only from the application's perspective

### Retention
- Minimum 7-year retention
- Records are never purged as part of normal operations
- Anonymization replaces PII in the payload_json field but does not delete the audit record

### Covered Events
See Requirement 18 for the full list of audited events. Key ones:
- All authentication events (login, logout, failure, lockout)
- All data-changing operations (requisition CRUD, scorecard changes, evaluations, submissions)
- All privacy events (consent creation, deletion request, anonymization completion)
- All security events (cross-org access attempts, unauthorized role attempts, malware detection)
- All AI events (LLM call made, extraction failed, evidence override)

---

## Vulnerability Considerations

### OWASP Top 10 Mitigations

| Risk | Mitigation |
|------|-----------|
| A01 Broken Access Control | RBAC on every endpoint; org-id filter at DB layer; audit of all violations |
| A02 Cryptographic Failures | Argon2/bcrypt passwords; RS256 JWT; HTTPS only; secrets in env vars |
| A03 Injection | SQLAlchemy ORM (parameterized); Pydantic input validation; no raw SQL |
| A04 Insecure Design | Threat-modeled per feature; audit-first design; PA exclusion enforced at engine |
| A05 Security Misconfiguration | Security headers enforced; CORS restricted; no secrets in code |
| A06 Vulnerable Components | Pin dependencies; regular `pip audit` / `npm audit` in CI |
| A07 Authentication Failures | Rate limiting; account lockout; single-use refresh tokens; uniform error messages |
| A08 Software Integrity | No arbitrary deserialization; Pydantic schema validation on all LLM responses |
| A09 Logging Failures | Audit log is a transaction guard; operation fails if log write fails |
| A10 Server-Side Request Forgery | No user-supplied URLs fetched by the server; LLM provider URL is config-only |

---

## Security Testing Requirements

- Authentication bypass tests: every role combination
- RBAC enforcement: every endpoint × every disallowed role
- Cross-org access tests: attempt resource access across org boundaries
- File upload attack tests: MIME mismatch, magic bytes manipulation, oversized files, malicious filenames, malware samples (EICAR test file)
- JWT manipulation tests: expired token, modified payload, wrong signature
- Rate limit tests: confirm 429 responses at correct thresholds
- Contact masking tests: confirm no unmasked fields in client org responses
- Protected attribute tests: inject PA fields into scoring input → confirm ProtectedAttributeError

---

## Phase 5 Evaluation Security & Responsible AI Controls

### 1. Demographic Attribute Exclusion Guard
Implemented in `backend/app/ai/evidence_extraction_service.py`:
- Before constructing prompts or passing candidate data to AI evidence extractors, candidate profiles are sanitized to remove all non-job-relevant demographic attributes:
  `gender`, `sex`, `age`, `date_of_birth`, `ethnicity`, `race`, `nationality`, `marital_status`, `religion`, `photo`, and `graduation_year`.
- If an input payload directly contains any prohibited protected attribute, the service raises `ProtectedAttributeViolationError` and aborts evaluation immediately.

### 2. Client Role PII Masking
Implemented in `backend/app/api/v1/endpoints/evaluations.py`:
- In the evaluation API responses, if `current_user.role == "client_hiring_manager"`, candidate email addresses are automatically masked (e.g. `j***@example.com`).
- Direct contact details and raw resumes are gated from unauthorized client-side harvesting.

### 3. Review Authority & RBAC Guard
- Only users with the `recruiter` or `delivery_head` role in the owning organization can record review decisions (`SHORTLIST`, `REJECT`, `HOLD`, `REQUEST_INFO`) or trigger deterministic score recalculations.
- Client hiring managers attempting to submit reviews receive `403 Forbidden`.

### 4. Zero Automatic Rejection Policy
- ShortlistAI explicitly forbids automatic candidate rejections or hidden thresholds based on AI scores.
- Candidates with scores below 50 remain completely visible, filterable, and reviewable in the requisition candidate pipeline.

