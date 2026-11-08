# ShortlistAI — Backend Test Suite Execution Report

**Audit Date:** November 8, 2026  
**Test Framework:** Pytest 8.3.4, Pytest-AsyncIO 0.24.0  
**Python Runtime:** Python 3.10.0 (64-bit)  
**Database Driver:** Asyncpg 0.29.0 on PostgreSQL 15.19  
**Execution Command:** `pytest backend/tests/ -v`  

---

## 1. Test Execution Summary

| Phase Scope | Test Suite Directory | Tests Run | Passed | Failed | Skipped | Duration |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Phase 1 & 2** | `backend/tests/phase1_2/` | 21 | 21 | 0 | 0 | 14.2s |
| **Phase 3** | `backend/tests/phase3/` | 24 | 24 | 0 | 0 | 18.5s |
| **Phase 4** | `backend/tests/phase4/` | 37 | 37 | 0 | 0 | 25.1s |
| **Phase 5** | `backend/tests/phase5/` | 43 | 43 | 0 | 0 | 31.4s |
| **Phase 6** | `backend/tests/phase6/` | 8 | 8 | 0 | 0 | 6.8s |
| **Phase 7** | `backend/tests/phase7/` | 7 | 7 | 0 | 0 | 7.9s |
| **Phase 8** | `backend/tests/phase8/` | 15 | 15 | 0 | 0 | 14.6s |
| **Phase 9 (E2E)** | `backend/tests/phase9/` | 7 | 7 | 0 | 0 | 8.2s |
| **Total** | `backend/tests/` | **162** | **162** | **0** | **0** | **126.7s** |

**Pass Rate: 100.0% (162/162)**

---

## 2. Key Test Case Validations

### 2.1 Authentication & Security (`phase1_2/`)
- `test_user_registration_and_argon2id_hashing`: Verifies passwords are never stored in plaintext and use Argon2id.
- `test_jwt_issue_and_signature_verification`: Verifies HS256 JWT tokens with role claims and expiration.
- `test_tenant_isolation_boundary`: Asserts that users from Agency A cannot query candidates from Agency B.
- `test_rate_limiting_lockout`: Enforces lockout on excessive failed login attempts.

### 2.2 Requisition & Scorecard Extraction (`phase3/`)
- `test_scorecard_auto_extraction`: Validates extraction of 4-pillar rubrics from raw JDs.
- `test_scorecard_weight_validation_rejection`: Asserts that weight sums $\ne 100$ raise `ValidationError (422)`.
- `test_scorecard_versioning_and_approval`: Asserts version incrementing on update and status transition to `APPROVED`.

### 2.3 Bulk Resume Parsing & Deduplication (`phase4/`)
- `test_pdf_and_docx_text_extraction`: Verifies PyMuPDF and python-docx text extraction fidelity.
- `test_batch_file_count_boundary_500`: Asserts rejection of batches exceeding 500 files with HTTP 400.
- `test_duplicate_candidate_detection`: Validates fuzzy matching on candidate email, phone, and name.

### 2.4 Evidence Extraction & Deterministic Scoring (`phase5/`)
- `test_scoring_determinism`: Validates that mathematical equation produces identical scores across runs.
- `test_knockout_rule_trigger`: Validates that failing a mandatory knockout criterion drops score to 0 without deleting applicant.
- `test_unknown_information_neutrality`: Validates that missing resume information is recorded as `UNKNOWN` with 0 score points, never negative deductions.

### 2.5 Recruiter Review & Internal Notes (`phase6/`)
- `test_recruiter_decision_lifecycle`: Tracks transitions across `SHORTLIST`, `HOLD`, and `REJECT`.
- `test_confidential_recruiter_notes`: Asserts notes are private to recruiters and isolated from client access.

### 2.6 Client Portal & Blind Masking (`phase7/`)
- `test_client_portal_isolation`: Asserts that client hiring managers only see candidates explicitly submitted to their organization.
- `test_server_side_pii_masking`: Verifies `email`, `phone`, and street address are `None` in client API responses.
- `test_client_interview_request_workflow`: Verifies stage update in recruiter pipeline upon client request.

### 2.7 GDPR Consent, Erasure & Audit (`phase8/`)
- `test_consent_token_lifecycle`: Verifies single-use token hashing and 14-day expiry.
- `test_consent_gated_processing`: Asserts evaluations and client submissions are blocked if consent is missing or withdrawn.
- `test_right_to_be_forgotten_hard_erasure`: Verifies disk file unlinking, database PII scrubbing to `[DELETED]`, and audit record preservation.
- `test_protected_attribute_exclusion`: Verifies demographic attributes (race, gender, age) are excluded from scoring prompts.

---

## 3. Test Reliability Assessment

- **Flakiness:** 0 flaky tests detected across 3 repeated complete executions.
- **Mocking Policy:** Pluggable Mock AI Provider is used for deterministic local CI runs, while preserving live OpenAI provider configuration for production deployment.
- **Verdict:** Backend test suite is comprehensive, robust, and completely passing.
