# ShortlistAI - Phase 9 Integration & Defect Register

**Document Version:** 1.0  
**Phase:** Phase 9 — System Integration, E2E Testing, Security Verification & Polish  
**Lead Engineer:** Principal QA & Software Systems Architect  
**Date:** 2026-11-08  
**Defect Resolution Rate:** 100% (8 Defects Identified, Diagnosed, Resolved, and Verified)

---

## Defect Summary Table

| Defect ID | Severity | Component | Summary | Status |
| :--- | :--- | :--- | :--- | :--- |
| **DEF-001** | Medium | Recruiter Dashboard | 404 Not Found on `/api/v1/dashboard/metrics` in E2E tests | **RESOLVED & VERIFIED** |
| **DEF-002** | High | Scorecard Validation | Schema validation 422 on `ScorecardCriterion` instantiation | **RESOLVED & VERIFIED** |
| **DEF-003** | High | Evaluation Service | Pre-condition blocker when requisition lacked approved scorecard | **RESOLVED & VERIFIED** |
| **DEF-004** | Critical | Test Harness / Worker | SQLite `no such table: resume_processing_jobs` in background tests | **RESOLVED & VERIFIED** |
| **DEF-005** | High | Test Configuration | Python namespace shadowing of `app` package over FastAPI instance | **RESOLVED & VERIFIED** |
| **DEF-006** | Medium | Seed Automation | `MultipleResultsFound` crash on repeated seed execution | **RESOLVED & VERIFIED** |
| **DEF-007** | Critical | Candidate Repository | PostgreSQL crash: `could not identify equality operator for type json` | **RESOLVED & VERIFIED** |
| **DEF-008** | High | Seed Model Mapping | Schema mismatch (`department`, `scoring_config_json`, `reviewer_id`) | **RESOLVED & VERIFIED** |

---

## Detailed Defect Reports

### DEF-001: 404 Route Mismatch on Recruiter Dashboard Metrics
- **Component:** `app/api/v1/endpoints/dashboard.py` / `tests/phase9/`
- **Severity:** Medium
- **Symptom:** `test_workflow_a_recruiter_auth.py` and `test_workflow_e_recruiter_workspace.py` received `404 Not Found` calling `/api/v1/dashboard/metrics`.
- **Root Cause:** The dashboard router in `dashboard.py` defines `prefix="/recruiter"`, resulting in the canonical endpoint route `/api/v1/recruiter/metrics`.
- **Resolution:** Updated E2E tests to invoke `/api/v1/recruiter/metrics` and verified metric field names (`active_requisitions`, `total_candidates`).
- **Verification:** Verified via `test_workflow_a` and `test_workflow_e` passing with 200 OK.

---

### DEF-002: Schema Validation 422 on Scorecard Criteria Payloads
- **Component:** `app/schemas/scorecard.py` / `ScorecardCriterion` model
- **Severity:** High
- **Symptom:** POST payloads to `/api/v1/requisitions/{id}/scorecard` returned 422 Unprocessable Entity during criterion creation.
- **Root Cause:** Legacy test payloads passed `category` and `is_required` with float weights. The production Phase 3 schema requires `criterion_type`, `criterion_name`, `label`, `weight: int`, and `is_mandatory: bool`, along with `scoring_config` weights summing to exactly 100.
- **Resolution:** Updated criterion payloads in `test_workflow_b_jd_and_scorecard.py` and `test_workflow_d_ai_evaluation_and_ranking.py` to match `ScorecardCriterion` and `CriterionCreate` specifications.
- **Verification:** Both Workflow B and Workflow D pass with 200 OK and valid criterion persistence.

---

### DEF-003: Evaluation Service Pre-condition Block on Unapproved Scorecard
- **Component:** `app/services/evaluation_service.py`
- **Severity:** High
- **Symptom:** `test_workflow_g_privacy_and_governance.py` threw `ValueError: Requisition does not have an approved scorecard. Evaluation cannot proceed.` when asserting consent blocking.
- **Root Cause:** `evaluation_service.evaluate_candidate()` evaluates prerequisites in strict logical order: it verifies the requisition has an approved scorecard (`scorecard.status == 'approved'`) before querying candidate consent. Because the test had not attached an approved scorecard to the requisition, execution halted before reaching the consent gate.
- **Resolution:** Provisioned an approved `Scorecard` with criteria for the test requisition before triggering the evaluation call.
- **Verification:** Verified `test_workflow_g` cleanly validates consent enforcement and returns processing blocked status.

---

### DEF-004: In-Memory SQLite Missing `resume_processing_jobs` Table
- **Component:** `tests/conftest.py` / `ResumeWorkerService`
- **Severity:** Critical
- **Symptom:** Worker background task crashed with `sqlite3.OperationalError: no such table: resume_processing_jobs`.
- **Root Cause:** In `tests/conftest.py`, `conn.run_sync(Base.metadata.create_all)` was executed before ORM model modules were imported. In SQLAlchemy, declarative models are only registered with `Base.metadata` when their defining modules are imported. Because `ResumeProcessingJob` was not yet imported, its table was omitted from `create_all`.
- **Resolution:** Added `import app.models as _all_models` at the module level in `conftest.py` prior to `test_engine` and fixture definitions, ensuring all models in `app.models.__all__` are registered before schema generation.
- **Verification:** Re-ran worker tests in `test_workflow_c_bulk_resume_ingestion.py`; background batch jobs process and complete with 0 database errors.

---

### DEF-005: Python Module Namespace Shadowing of FastAPI App
- **Component:** `tests/conftest.py`
- **Severity:** High
- **Symptom:** Pytest setup crashed with `AttributeError: module 'app' has no attribute 'dependency_overrides'`.
- **Root Cause:** In Python, writing `from app.main import app` followed by `import app.models` overwrites the local variable `app` (which was bound to the FastAPI instance) with the top-level package module `app`.
- **Resolution:** Re-aliased model registration to `import app.models as _all_models` and imported `from app.main import app` cleanly.
- **Verification:** Pytest client fixture overrides `app.dependency_overrides[get_db]` without error across all test suites.

---

### DEF-006: MultipleResultsFound Error in Seed Script Idempotency
- **Component:** `backend/scripts/seed.py`
- **Severity:** Medium
- **Symptom:** Running `python scripts/seed.py` a second time crashed with `sqlalchemy.exc.MultipleResultsFound: Multiple rows were found when one or none was required`.
- **Root Cause:** Requisition lookup queried `select(Requisition).where(Requisition.title == ...)` using `.scalar_one_or_none()`. Because earlier test runs had created multiple requisitions with matching titles, `scalar_one_or_none()` raised an exception.
- **Resolution:** Replaced `.scalar_one_or_none()` with `.scalars().first()` and scoped queries by `organization_id`, ensuring completely idempotent execution.
- **Verification:** Executed `python scripts/seed.py` repeatedly; all runs finished with Exit Code 0.

---

### DEF-007: PostgreSQL Equality Failure on JSON Type During Candidate Queries
- **Component:** `backend/app/repositories/candidate_repository.py`
- **Severity:** Critical
- **Symptom:** Benchmark test against live PostgreSQL crashed with `UndefinedFunctionError: could not identify an equality operator for type json` on `SELECT DISTINCT candidates...`.
- **Root Cause:** `candidate_repository.py` had `stmt = stmt.distinct()` before sorting. In PostgreSQL, standard `JSON` data types (unlike `JSONB` or scalar types) do not have an equality operator (`=`), so invoking `SELECT DISTINCT` across all columns of a table containing `JSON` columns (`certifications`, `parsed_profile_json`) raises a fatal query failure in PostgreSQL.
- **Resolution:** Removed the redundant `stmt = stmt.distinct()` statement. Candidate searches already filter via subqueries (`id.in_(...)`), and evaluations are 1:1 via `is_current == True`, so `DISTINCT` across entire rows was both unnecessary and incompatible with PostgreSQL `JSON`.
- **Verification:** Ran `python scripts/benchmark_performance.py` against live PostgreSQL; all 30 candidate search iterations passed with HTTP 200 and ~65ms response time.

---

### DEF-008: Schema Column Keyword Mismatch in Demo Seed Script
- **Component:** `backend/scripts/seed.py`
- **Severity:** High
- **Symptom:** Seed script failed with `TypeError` when instantiating `Requisition`, `Scorecard`, `Candidate`, and `RecruiterReview`.
- **Root Cause:** `seed.py` used tentative field names (`department` on `Requisition`, `scoring_config_json` on `Scorecard`, `raw_extracted_json` on `Candidate`, `reviewer_id` on `RecruiterReview`, `organization_id` on `Submission`).
- **Resolution:** Aligned all model instantiations with the exact SQLAlchemy ORM models:
  - Removed `department` from `Requisition`.
  - Changed `scoring_config_json` to `scoring_config` on `Scorecard`.
  - Changed `raw_extracted_json` to `parsed_profile_json` on `Candidate`.
  - Changed `reviewer_id` to `recruiter_id` and `reason_note` to `notes` on `RecruiterReview`.
  - Changed `organization_id` to `source_organization_id` and added `evaluation_id` on `Submission`.
  - Aligned `ConsentRecord` and `AuditLog` fields with their respective models.
- **Verification:** `scripts/seed.py` executes end-to-end, seeding all 7 phases with zero errors.

---

## Defect Closure Sign-Off
All 8 detected issues have been root-cause analyzed, fixed in code, and verified through both automated unit/integration suites and live PostgreSQL benchmarks. Zero defects remain open.
