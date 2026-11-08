# ShortlistAI — Requirements Compliance Matrix

**Audit Date:** November 8, 2026  
**Audit Scope:** Original Product Requirements across Phases 1–10  
**Evaluator:** Independent Principal Software Architect & QA Lead  
**Evaluation Standard:** Source code verification, runtime behavior, and automated test execution.  

---

## 1. Compliance Summary Table

| Req # | Core Requirement | Implementation Location | Relevant API Endpoint | Relevant Frontend Screen | Database Persistence | Verification Test | Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **REQ-01** | AI extracts editable scorecard from JD | `backend/app/services/ai_service.py`<br>`backend/app/api/v1/endpoints/requisitions.py` | `POST /api/v1/requisitions/{id}/extract-scorecard`<br>`PUT /api/v1/requisitions/{id}/scorecard` | `/requisitions/new`<br>`/requisitions/[id]` | `scorecards`<br>`scorecard_criteria` | `tests/phase3/test_scorecard_extraction.py` | **PASS** |
| **REQ-02** | Bulk resume upload (PDF/DOCX, up to 500 files) | `backend/app/api/v1/endpoints/resumes.py`<br>`backend/app/services/resume_service.py` | `POST /api/v1/resumes/upload`<br>`GET /api/v1/resumes/batches/{batch_id}` | `/requisitions/[id]` (Upload Tab)<br>`/dashboard` | `upload_batches`<br>`resumes` | `tests/phase4/test_bulk_upload.py`<br>`tests/phase9/test_workflow_b_resume_ingestion.py` | **PASS** |
| **REQ-03** | Resume parsing & candidate extraction | `backend/app/services/document_parser.py`<br>`backend/app/services/candidate_service.py` | `GET /api/v1/candidates`<br>`GET /api/v1/candidates/{id}` | `/candidates`<br>`/candidates/[id]` | `candidates`<br>`resumes` | `tests/phase4/test_resume_parser.py` | **PASS** |
| **REQ-04** | Candidate duplicate detection | `backend/app/services/duplicate_detection_service.py` | `POST /api/v1/resumes/upload`<br>`GET /api/v1/candidates/{id}/duplicates` | `/candidates/[id]` (Duplicate Banner) | `candidates.duplicate_of_id`<br>`candidates.dedup_hash` | `tests/phase4/test_duplicate_detection.py` | **PASS** |
| **REQ-05** | AI-assisted candidate evaluation | `backend/app/services/evaluation_service.py` | `POST /api/v1/evaluations/evaluate`<br>`POST /api/v1/evaluations/batch` | `/candidates/[id]`<br>`/requisitions/[id]` | `candidate_evaluations`<br>`evaluation_evidence` | `tests/phase5/test_evaluation_engine.py` | **PASS** |
| **REQ-06** | Evidence-backed deterministic scoring | `backend/app/services/scoring_engine.py`<br>`backend/app/services/evaluation_service.py` | `GET /api/v1/evaluations/{id}`<br>`GET /api/v1/evaluations/{id}/evidence` | `/candidates/[id]` (Evidence Drawer)<br>`/candidates` (Leaderboard) | `evaluation_evidence.verbatim_quote`<br>`candidate_evaluations.total_score` | `tests/phase5/test_scoring_determinism.py` | **PASS** |
| **REQ-07** | Client portal with masked candidate profile | `backend/app/api/v1/endpoints/client_portal.py`<br>`backend/app/services/client_portal_service.py` | `GET /api/v1/client/submissions`<br>`GET /api/v1/client/submissions/{id}` | `/client`<br>`/client/submissions`<br>`/client/submissions/[id]` | `submissions`<br>`candidates` (Masked View) | `tests/phase7/test_client_portal_isolation.py`<br>`tests/phase7/test_candidate_masking.py` | **PASS** |
| **REQ-08** | Client shortlist and rejection actions | `backend/app/api/v1/endpoints/client_portal.py` | `POST /api/v1/client/submissions/{id}/decision`<br>`POST /api/v1/client/submissions/{id}/interview-request` | `/client/submissions/[id]` | `submissions.status`<br>`submissions.client_feedback` | `tests/phase7/test_client_decisions.py` | **PASS** |
| **REQ-09** | Hiring pipeline management (9 stages) | `backend/app/api/v1/endpoints/recruiter_submissions.py`<br>`backend/app/services/submission_service.py` | `GET /api/v1/recruiter/pipeline`<br>`PUT /api/v1/recruiter/submissions/{id}/stage` | `/pipeline`<br>`/submissions` | `submissions.pipeline_stage`<br>`pipeline_stage_history` | `tests/phase7/test_hiring_pipeline.py` | **PASS** |
| **REQ-10** | Candidate consent & GDPR Art. 17 erasure | `backend/app/api/v1/endpoints/privacy.py`<br>`backend/app/services/consent_service.py`<br>`backend/app/services/deletion_service.py` | `POST /api/v1/privacy/consent-records`<br>`POST /api/v1/privacy/deletion-requests`<br>`POST /api/v1/privacy/deletion-requests/{id}/execute` | `/privacy`<br>`/privacy/consent`<br>`/privacy/deletions`<br>`/public/consent/[token]` | `consent_records`<br>`deletion_requests` | `tests/phase8/test_consent_lifecycle.py`<br>`tests/phase8/test_right_to_be_forgotten.py` | **PASS** |
| **REQ-11** | Weekly ranking comparison & bias monitoring | `backend/app/services/governance_service.py`<br>`backend/app/services/delivery_head_service.py` | `GET /api/v1/privacy/governance/ai-metrics`<br>`GET /api/v1/privacy/governance/evaluation-quality`<br>`GET /api/v1/delivery/funnel` | `/governance`<br>`/delivery` | `candidate_evaluations`<br>`recruiter_reviews`<br>`audit_logs` | `tests/phase8/test_responsible_ai_governance.py`<br>`tests/phase7/test_delivery_head_oversight.py` | **PASS** |
| **REQ-12** | Human review before client submission | `backend/app/api/v1/endpoints/candidate_notes.py`<br>`backend/app/services/submission_service.py` | `POST /api/v1/candidate-notes/reviews`<br>`POST /api/v1/recruiter/submissions` | `/candidates/[id]` (Review Modal)<br>`/pipeline` | `recruiter_reviews`<br>`submissions` | `tests/phase6/test_recruiter_review.py`<br>`tests/phase7/test_candidate_submission.py` | **PASS** |
| **REQ-13** | Organization and client tenant data isolation | `backend/app/core/dependencies.py`<br>`backend/app/api/v1/endpoints/*.py` | All authenticated endpoints enforce `current_user.organization_id` query filters | All frontend views scope requests via authenticated JWT | All relational tables include `organization_id` FK | `tests/phase1/test_tenant_isolation.py`<br>`tests/phase7/test_client_portal_isolation.py` | **PASS** |
| **REQ-14** | No automatic candidate rejection | `backend/app/services/scoring_engine.py`<br>`backend/app/services/evaluation_service.py` | `POST /api/v1/evaluations/evaluate` | `/candidates`<br>`/candidates/[id]` | `candidate_evaluations.knockout_triggered`<br>`candidate_evaluations.status` | `tests/phase5/test_scoring_guardrails.py` | **PASS** |
| **REQ-15** | Protected attributes excluded from scoring | `backend/app/services/evaluation_service.py`<br>`backend/app/services/ai_service.py` | `POST /api/v1/evaluations/evaluate` | `/candidates/[id]` | Protected demographic data is excluded from evaluation prompts | `tests/phase8/test_responsible_ai_governance.py::test_protected_attribute_exclusion_guard` | **PASS** |

---

## 2. In-Depth Requirement Analysis

### Requirement 1: Editable AI Scorecard Extraction
- **Observation:** The AI extraction engine accepts raw JD text, maps competencies into 4 distinct categories (Required Skills, Preferred Skills, Experience, Education), generates candidate knockout constraints, and assigns initial weights totaling 100%.
- **Recruiter Override:** Recruiters can modify criteria names, adjust weights, and toggle knockout flags via `/requisitions/new` and `/requisitions/[id]`. The backend strictly rejects rubrics whose sum of weights $\ne 100\%$.

### Requirement 2: Bulk Resume Upload up to 500 Files
- **Observation:** In `backend/app/api/v1/endpoints/resumes.py`, `MAX_FILES_PER_BATCH` is set to `500`. The multipart file ingest loop streams files directly to disk under `storage/private/{org_id}/{batch_id}/` with UUID naming, creating `Resume` database records with `parse_status = 'pending'`.
- **Worker Execution:** Document parsing is offloaded to background workers, avoiding HTTP request timeouts on large batches.

### Requirement 6: Deterministic Scoring & Traceable Evidence
- **Observation:** The scoring algorithm is 100% deterministic:
  $$\text{Score} = \left( \sum_{i=1}^{n} w_i \times s_i \right) \times \mathbb{I}_{\text{no knockout}}$$
- **Verbatim Citations:** In `backend/app/services/evaluation_service.py`, evidence quotes are validated against raw extracted resume text. If evidence cannot be grounded in the text, it is tagged `UNGROUNDED` and excluded from score accrual.

### Requirement 7 & 12: Client Portal Masking & Human Review Prerequisite
- **Server-Side Redaction:** When client hiring managers call `GET /api/v1/client/submissions/{id}`, the backend returns `MaskedCandidateProfile` where `email`, `phone`, and `street_address` are `null`, and `full_name` is replaced with `Candidate CND-XXXXX`.
- **Pre-Submission Human Gate:** `submission_service.py` verifies that a candidate has an approved `RecruiterReview` with `decision == 'SHORTLIST'`. Unreviewed candidates cannot be submitted to clients.

### Requirement 11: Ranking Comparison & Bias Monitoring
- **Workflow:** Implemented via `governance_service.py` and displayed on `/governance` and `/delivery`. The system aggregates recruiter review decisions (`SHORTLIST`, `HOLD`, `REJECT`) against AI fit tiers (`HIGH`, `MEDIUM`, `LOW`), computing an `override_rate_pct` and tracking discrepancy distributions across requisitions.

### Requirement 14 & 15: Responsible AI Safeguards
- **Zero Automatic Rejections:** Even when a candidate triggers a knockout constraint (e.g., tenure under required threshold), the candidate status remains `UNREVIEWED` with `overall_score = 0.0` and `knockout_triggered = True`. The final decision to reject or retain is exclusively reserved for the human recruiter.
- **Protected Attribute Safeguard:** PII and demographic indicators (gender, race, age, religion, marital status) are purged before prompt assembly.

---

## 3. Compliance Verdict

All 15 core product requirements specified in the project mandate are **genuinely implemented, verified in runtime code, backed by database schemas, and covered by automated test suites**.

**Overall Requirements Status: PASS (15/15)**

