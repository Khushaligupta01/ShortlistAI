# Architecture Decision Records — ShortlistAI

## ADR-001: Modular Monolith over Microservices

**Status**: Accepted

**Context**: The platform requires multiple distinct capabilities (AI extraction, scoring, file processing, client portal). The team is small and the product is early-stage.

**Decision**: Single deployable FastAPI application with clearly bounded internal modules. One ARQ worker process for background jobs. Shared PostgreSQL and Redis.

**Rationale**:
- Transactional integrity is trivial in a monolith (audit log + operation in one DB transaction)
- No inter-service networking, distributed tracing, or service mesh overhead
- Module interfaces are defined cleanly — extraction to microservices is possible later
- Operational burden is appropriate for the team size

**Consequences**:
- All modules share a process and database (acceptable at current scale)
- Future extraction of AI module is possible without business logic rewrite

---

## ADR-002: AI Does Not Assign Final Scores

**Status**: Accepted

**Context**: The brief requires AI assistance for extraction and evidence, but transparency and auditability demand that score assignment be deterministic and explainable.

**Decision**: AI produces evidence assessments (status + excerpts + confidence). A pure-function deterministic scoring engine computes the final score from those inputs using defined rules.

**Rationale**:
- Deterministic scoring means identical inputs always produce identical scores — fully testable
- Every point in the score is traceable to a rule applied to a verifiable evidence item
- Replacing the LLM provider does not change any score (scoring is AI-independent)
- Regulators and clients can be shown exactly why a candidate received their score

**Consequences**:
- Scoring rules are explicit and must be maintained (weight changes create new scorecard versions)
- AI extraction quality directly impacts score quality — evidence extraction must be accurate

---

## ADR-003: LLM Provider Abstraction via Protocol

**Status**: Accepted

**Context**: The brief specifies OpenAI initially but requires the ability to change providers without changing business logic.

**Decision**: Define a `LLMProvider` protocol (Python `typing.Protocol`). All AI services depend on this interface. Concrete provider loaded from `LLM_PROVIDER` environment variable via factory. No hardcoded imports of concrete providers in service modules.

**Rationale**:
- Provider change requires only: new implementation class + config update
- Service unit tests can use a mock provider (no real LLM calls in test suite)
- Prompt engineering improvements are isolated to the concrete provider

**Consequences**:
- Every concrete provider must implement all three interface methods
- Contract tests required for each concrete implementation

---

## ADR-004: Protected Attributes Excluded at Pipeline Level (Not Just UI)

**Status**: Accepted

**Context**: Protected attributes (name, gender, age, etc.) must never influence scores. A UI-level control is insufficient for compliance.

**Decision**: Protected attributes are stripped from the data payload at the `ProtectedAttributeStripper` layer before any LLM call or scoring computation. The Scoring Engine independently validates at runtime that no PA fields are present in its input, raising `ProtectedAttributeError` if any are found.

**Rationale**:
- Defense in depth: two independent enforcement points
- Scoring engine can be tested in isolation to prove PA exclusion (property test)
- Prevents protected attributes from influencing scores even if called incorrectly

**Consequences**:
- Full candidate profile (with PAs) stored in `candidates.parsed_profile_json` for Recruiter display only
- Clean profile used in all AI and scoring operations

---

## ADR-005: ARQ for Background Job Processing

**Status**: Accepted

**Context**: Bulk uploads of up to 500 files must be processed asynchronously without blocking the HTTP request cycle.

**Decision**: Use ARQ (Async Redis Queue) for background job processing. Each file in a batch is an independent job. Redis (already used for rate limiting) serves as the job queue backend.

**Rationale**:
- ARQ is Python-native and async-first — fits the FastAPI async codebase
- Each file as an independent job provides fault isolation (one failure doesn't block others)
- Redis is already in the stack — no additional infrastructure
- Simpler than Celery for an MVP; can be replaced with Celery + RabbitMQ if scale demands

**Alternatives considered**:
- Celery + RabbitMQ: More complex, additional service, overkill for MVP
- FastAPI BackgroundTasks: No retry support, no cross-process persistence
- Threading pool: Not appropriate for I/O-bound async workloads

---

## ADR-006: Audit Log as Transaction Guard

**Status**: Accepted

**Context**: Compliance requires that every state-changing operation be audited. The risk is that an operation succeeds but the audit log fails to write.

**Decision**: Audit log writes occur in the same database transaction as the triggering operation. If the audit write fails, the entire transaction rolls back — the operation does not proceed.

**Rationale**:
- Guarantees there is never an unlogged state change
- Eliminates the "audit as side effect" anti-pattern
- Auditability is a hard invariant, not best-effort

**Consequences**:
- Operations are slower by the cost of an audit INSERT in the same transaction
- Application DB user has INSERT-only on `audit_logs` (enforced at DB permission level)

---

## ADR-007: Scorecard and Evaluation Versioning

**Status**: Accepted

**Context**: Recruiters may need to adjust scorecard weights after evaluations have been run. Historical evaluation records must remain traceable.

**Decision**:
- Scorecards are versioned. Resetting an active scorecard creates a new draft version; the prior active version is preserved with status `superseded`.
- `evaluations.scorecard_id` is a foreign key to the exact scorecard version used.
- Evaluations are also versioned. Evidence overrides create a new evaluation version; prior versions are retained with `is_current = false`.

**Consequences**:
- Queries for "current" evaluation always filter `WHERE is_current = true`
- Storage grows with each scorecard version and evaluation override — acceptable at current scale

---

## ADR-008: Contact Masking at Service Layer

**Status**: Accepted

**Context**: Client Hiring Managers must not see candidate contact details. Masking only at the API serialization layer is fragile — a new code path could inadvertently expose PII.

**Decision**: Contact masking is applied in the `submission_service.py` layer before any response is returned for client org requests. The API serializer applies masking as a second layer for defense in depth.

**Consequences**:
- Client org users never receive unmasked contact details regardless of which API endpoint is called
- Recruiter views and client views are handled by separate code paths

---

## ADR-009: PostgreSQL with JSONB for Flexible Profiles

**Status**: Accepted

**Context**: AI-extracted candidate profiles and scoring breakdowns have evolving schemas. Normalizing every field into columns would require frequent migrations as AI output improves.

**Decision**: Store full extracted profiles in `JSONB` columns (`candidates.parsed_profile_json`, `evaluations.score_breakdown_json`). Fixed, queryable fields (email, location, notice_period_days) have dedicated typed columns.

**Rationale**:
- JSONB is indexed and queryable in PostgreSQL — supports filtering without full JSON scans
- Schema evolution (new extracted fields) requires no migration
- Dedicated columns exist for the fields that need indexing or FK constraints

---

## ADR-010: File Storage Abstraction for Future S3 Migration

**Status**: Accepted

**Context**: MVP uses local filesystem storage. Production will require cloud object storage.

**Decision**: Define a `StorageBackend` protocol with `save(key, content)` and `read(key)` methods. MVP implements `LocalFSBackend`. Migrating to S3 requires implementing `S3Backend` and updating the config.

**Consequences**:
- No application code changes required for storage migration
- File paths in the database are storage keys, not filesystem paths

---

## ADR-011: Strict AI Provider Protocol, Quota Exhaustion & Rate-Limit Handling

**Status**: Accepted

**Context**: In Phase 3, job description intelligence relies on external LLMs (such as OpenAI gpt-4o-mini). Provider credentials may lack quota, rate limits may be hit, or services may experience downtime. The application must never fabricate AI responses as production behavior.

**Decision**:
1. Implement `LLMProvider` protocol with typed schemas (`JDExtractionResult`).
2. Implement bounded exponential backoff retry for transient network errors (HTTP 500, 502, 503, 504).
3. Detect permanent quota exhaustion (`insufficient_quota`, `credit_balance_exhausted`) and fail fast without burning retries, returning HTTP 429 with clear instructions.
4. Expose clear provider unavailable / rate-limited error responses to the frontend, permitting recruiters to proceed with manual scorecard creation without blocking the hiring workflow.
5. In-memory sliding window rate limiting on `/extract-requirements` (10 requests/minute per user).
6. Protected attribute detection in JD extraction: any mention of age, gender, race, marital status, or photograph triggers extraction warnings and flags criteria for recruiter review.

**Consequences**:
- System is completely resilient to provider outages or lack of credits.
- Zero fake responses in production; testing is verified with mocked providers in pytest.
- Strict Pydantic schema validation ensures no unvalidated AI objects enter the database.

---

## ADR-012: Scorecard Immutability upon Approval and Explicit Versioning

**Status**: Accepted

**Context**: Requisitions require objective scoring models that cannot be silently modified after candidates begin being evaluated or after approval. However, recruiters may need to revise criteria as hiring needs evolve.

**Decision**:
1. Scorecards start with status `DRAFT`. While in draft, criteria and weights (must sum to 100) are fully editable with atomic cascade replacement (`cascade="all, delete-orphan"`).
2. Approving a scorecard locks it permanently: status changes to `APPROVED`, `approved_at` is timestamped, and the parent requisition transitions to `ACTIVE`.
3. Any attempt to modify an approved scorecard returns `409 Conflict`.
4. To modify an approved scorecard, recruiters must use `POST /api/v1/requisitions/{id}/scorecard/duplicate`, which clones criteria and weights into a new draft scorecard with incremented `version` (e.g., version 2).
5. All revisions, approvals, and duplications produce immutable audit log entries (`SCORECARD_CREATED`, `SCORECARD_UPDATED`, `SCORECARD_APPROVED`, `SCORECARD_DUPLICATED`).

**Consequences**:
- Complete auditability and reproducibility of historical evaluations.
- Recruiter workflows are smooth with explicit versioning.
- Prevents race conditions or unintended criteria modifications during active candidate scoring.

---

## Unresolved Decisions

| Decision | Options | Blocking? |
|----------|---------|-----------|
| Exact LLM prompts for extraction | Engineering iteration required | No (Phase 3) |
| ClamAV deployment in Docker | clamd daemon vs. subprocess | No (Phase 4) |
| In-app notification delivery mechanism | Polling vs. WebSocket vs. SSE | No (Phase 7) |
| Analytics charting library | Recharts vs. Victory vs. Chart.js | No (Phase 6) |
| Production secrets management | AWS Secrets Manager vs. Vault | No (Phase 10) |
| PostgreSQL Row Level Security | Can be added as Phase 10 hardening | No |
