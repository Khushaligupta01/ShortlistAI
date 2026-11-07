# Non-Functional Requirements — ShortlistAI

## Performance

| Requirement | Specification |
|-------------|---------------|
| NFR-P01 | Candidate list with filters returns results in < 3 seconds for up to 500 candidates per requisition |
| NFR-P02 | Candidate profile page renders within 2 seconds of navigation for any number of scorecard criteria |
| NFR-P03 | Dashboard initial page load (SSR) completes within 3 seconds under normal load |
| NFR-P04 | Delivery Head analytics dashboard renders within 5 seconds for organizations with up to 10,000 candidate records |
| NFR-P05 | Upload batch progress state updates within 5 seconds of a background job completing a file |
| NFR-P06 | Bulk upload endpoint returns a batch job ID within 2 seconds of receiving the request, regardless of file count |
| NFR-P07 | API endpoints (non-AI, non-upload) respond within 500ms at the 95th percentile under normal load |

## Scalability

| Requirement | Specification |
|-------------|---------------|
| NFR-S01 | The system SHALL support processing of up to 500 resumes per bulk upload batch |
| NFR-S02 | The background job worker SHALL support at minimum 10 concurrent file processing jobs per deployment instance |
| NFR-S03 | The database schema SHALL support organizations with up to 10,000 candidates without design changes |
| NFR-S04 | The modular architecture SHALL allow independent horizontal scaling of the ARQ worker tier without changes to the API tier |
| NFR-S05 | File storage SHALL be replaceable with S3-compatible cloud storage via a configuration change only (StorageBackend protocol) |

## Reliability

| Requirement | Specification |
|-------------|---------------|
| NFR-R01 | Transient LLM provider failures SHALL be retried up to 3 times with exponential backoff (1s, 2s, 4s) before marking extraction as failed |
| NFR-R02 | Failure of a single file in a bulk upload batch SHALL not affect processing of other files in the same batch |
| NFR-R03 | Background workers SHALL support graceful shutdown, completing in-progress jobs within 60 seconds of receiving SIGTERM |
| NFR-R04 | All multi-step database write operations SHALL execute within a transaction, rolling back fully on any step failure |
| NFR-R05 | If the audit log write fails, the triggering operation SHALL fail and roll back; no state change proceeds without an audit record |
| NFR-R06 | Optimistic locking on Requisition and Scorecard records SHALL prevent lost updates under concurrent edits |

## Security

| Requirement | Specification |
|-------------|---------------|
| NFR-SEC01 | All traffic in production SHALL be served exclusively over HTTPS; HTTP requests SHALL redirect to HTTPS |
| NFR-SEC02 | JWT access tokens SHALL expire after 15 minutes; refresh tokens after 7 days; refresh tokens are single-use |
| NFR-SEC03 | Passwords SHALL be hashed using bcrypt or Argon2; plaintext passwords SHALL never be persisted |
| NFR-SEC04 | All five required security headers SHALL be present on every response: CSP, X-Frame-Options, X-Content-Type-Options, HSTS, Referrer-Policy |
| NFR-SEC05 | File uploads SHALL pass MIME header check, magic bytes check, size check, and malware scan before storage |
| NFR-SEC06 | All secrets SHALL be stored in environment variables or a secrets manager; never in source code or committed config |
| NFR-SEC07 | Authentication endpoints rate-limited to 10 requests/minute/IP; upload endpoints to 5/minute/user; general API to 100/minute/user |
| NFR-SEC08 | Account lockout SHALL trigger after 10 failed authentication attempts in a 15-minute window |
| NFR-SEC09 | Uploaded files SHALL be stored with UUID-based names in non-web-accessible storage |
| NFR-SEC10 | All database queries SHALL use parameterized queries or ORM-level query building; no string-interpolated SQL |

## Privacy

| Requirement | Specification |
|-------------|---------------|
| NFR-PV01 | Protected attributes (name, gender, age, photograph, marital status, ethnicity, nationality, date of birth) SHALL never be inputs to the scoring engine or evidence extraction |
| NFR-PV02 | Contact details (email, phone, address) SHALL be masked in all Client Hiring Manager responses |
| NFR-PV03 | Candidate PII anonymization requests SHALL be fulfilled within 30 days |
| NFR-PV04 | Candidate data sent to external LLM providers SHALL be stripped of PII where provider terms prohibit retention |
| NFR-PV05 | A Consent_Record SHALL be created for every candidate at upload time |
| NFR-PV06 | Anonymized evaluation scores and audit log entries SHALL be retained after PII deletion |

## Auditability

| Requirement | Specification |
|-------------|---------------|
| NFR-A01 | Audit log records SHALL be append-only; no UPDATE or DELETE permissions granted to the application DB user on the audit_logs table |
| NFR-A02 | Audit logs SHALL be retained for a minimum of 7 years |
| NFR-A03 | Every auditable event SHALL produce an audit log entry; if the entry cannot be written, the event SHALL not proceed |
| NFR-A04 | Audit log entries SHALL contain: event type, actor user ID, actor org ID, resource type, resource ID, UTC timestamp, changed fields (old+new for updates) |

## Maintainability

| Requirement | Specification |
|-------------|---------------|
| NFR-M01 | The LLM provider SHALL be replaceable via a configuration change only; no business logic changes required |
| NFR-M02 | The scoring engine SHALL be a pure function with no external dependencies (no I/O, no LLM, no randomness) |
| NFR-M03 | Database schema changes SHALL be managed via Alembic migrations with rollback scripts |
| NFR-M04 | All environment-specific configuration SHALL be loaded from environment variables via Pydantic BaseSettings |
| NFR-M05 | Test coverage SHALL be ≥ 80% line coverage on the Scoring Engine and Evidence Extraction Service modules |
| NFR-M06 | Property-based tests (Hypothesis) SHALL run ≥ 100 iterations per property |

## Usability

| Requirement | Specification |
|-------------|---------------|
| NFR-U01 | The interface SHALL be responsive and usable on viewport widths ≥ 1024px; mobile (< 768px) is out of scope for v1 |
| NFR-U02 | Loading skeleton states SHALL be displayed on all data-heavy screens during API requests |
| NFR-U03 | AI-generated content SHALL be labeled with a visible "AI-generated" label on every affected field |
| NFR-U04 | Color and icons SHALL both be used for status indicators (not color alone) to meet WCAG 1.4.1 |
| NFR-U05 | All interactive components SHALL support keyboard navigation |
| NFR-U06 | The UI component library SHALL be Tailwind CSS + shadcn/ui exclusively |

## Compliance

| Requirement | Specification |
|-------------|---------------|
| NFR-C01 | The system SHALL NOT claim GDPR, SOC 2, or other regulatory compliance without independent verification |
| NFR-C02 | The system SHALL implement privacy-by-design controls: data minimization for AI calls, consent tracking, deletion support |
| NFR-C03 | Bias monitoring reports SHALL aggregate statistics only; no individual candidate identity shall appear in reports |
| NFR-C04 | Bias monitoring data SHALL be retained for a minimum of 24 months for trend analysis |
