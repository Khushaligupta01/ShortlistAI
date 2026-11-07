# Functional Requirements — ShortlistAI

This document summarizes the functional requirements derived from the product brief. For precise EARS-format acceptance criteria, see requirements.md.

---

## Authentication and Access Control

**FR-AUTH-01**: The system must support email/password authentication with secure password hashing (bcrypt or Argon2).  
**FR-AUTH-02**: The system must issue JWT access tokens (15-minute expiry) and server-tracked refresh tokens (7-day expiry).  
**FR-AUTH-03**: Authentication failures must return a uniform error message without disclosing which field was incorrect.  
**FR-AUTH-04**: Accounts must lock after 10 failed attempts within 15 minutes; users must be notified.  
**FR-AUTH-05**: The system must enforce RBAC with three roles: Recruiter, Client_Hiring_Manager, Delivery_Head.  
**FR-AUTH-06**: Each API endpoint must verify the authenticated user's role before permitting the operation.  
**FR-AUTH-07**: Logout must immediately revoke the refresh token.  
**FR-AUTH-08**: Password changes must invalidate all existing refresh tokens for that user.

---

## Multi-Tenant Organization Isolation

**FR-ORG-01**: Every data record must be associated with exactly one organization.  
**FR-ORG-02**: All data retrieval queries must filter by the authenticated user's organization.  
**FR-ORG-03**: Cross-organization access attempts must return 404 (not 403) and log the attempt.  
**FR-ORG-04**: The system must support staffing firm organizations and client company organizations.  
**FR-ORG-05**: When a candidate is submitted to a client organization, that org gains scoped read access to that candidate profile.  
**FR-ORG-06**: Submission withdrawal must revoke the client organization's access immediately.

---

## Requisition Management

**FR-REQ-01**: Recruiters must be able to create requisitions with a job title and job description.  
**FR-REQ-02**: Recruiters must be able to update, archive, and search requisitions within their organization.  
**FR-REQ-03**: Archived requisitions must retain all historical data (candidates, evaluations, submissions, pipeline).  
**FR-REQ-04**: Requisitions must support optimistic locking to prevent concurrent edit conflicts.  
**FR-REQ-05**: All requisition changes must produce audit log entries.

---

## JD Intelligence

**FR-JD-01**: The system must extract job title, experience range, location, must-have skills, nice-to-have skills, notice period, and explicit requirements from job descriptions.  
**FR-JD-02**: Each extracted field must have a confidence score (0.0–1.0).  
**FR-JD-03**: Absent fields must return null with confidence 0.0 — never fabricated.  
**FR-JD-04**: Extracted data must pre-populate the scorecard editor for recruiter review and editing.  
**FR-JD-05**: Must-have skills must contain only skills explicitly present in the job description.  
**FR-JD-06**: Raw LLM responses must be stored for audit purposes.

---

## Scorecard Management

**FR-SC-01**: The system must create a scorecard for each requisition with configurable criteria.  
**FR-SC-02**: Default weight distribution: experience 30pts, must-have skills 40pts, notice period 15pts, location 10pts, nice-to-have skills 5pts.  
**FR-SC-03**: Recruiters must be able to add, edit, reorder, and delete criteria before activation.  
**FR-SC-04**: Activation must enforce total weight = exactly 100 points.  
**FR-SC-05**: Active scorecards must be structurally locked; changes require creating a new version.  
**FR-SC-06**: Historical evaluation records must reference the exact scorecard version active at evaluation time.  
**FR-SC-07**: All scorecard changes must produce audit log entries.

---

## Bulk Resume Upload

**FR-UP-01**: The system must support bulk upload of up to 500 PDF/DOCX files per batch.  
**FR-UP-02**: Each file must be validated for format, size (max 10 MB), and malware before processing.  
**FR-UP-03**: File validation failures must not block processing of other files in the batch.  
**FR-UP-04**: Processing must be asynchronous; the UI must reflect progress in real time.  
**FR-UP-05**: Duplicate candidates must be flagged for recruiter resolution, not silently merged.  
**FR-UP-06**: Duplicate resolution must hold the new profile in a pending state until the recruiter decides.  
**FR-UP-07**: Background jobs must retry transient failures up to 3 times with exponential backoff.  
**FR-UP-08**: Upload batch metadata must be recorded in the audit log.

---

## Resume Extraction

**FR-PARSE-01**: The system must extract: name, email, phone, location, total years experience, employment history, education, skills, notice period from resumes.  
**FR-PARSE-02**: Each extracted field must have a confidence score; absent fields return null with 0.0 confidence.  
**FR-PARSE-03**: Resumes producing fewer than 50 words of text must be marked as parsing failures.  
**FR-PARSE-04**: Raw extracted text must be stored separately to enable re-extraction without re-upload.  
**FR-PARSE-05**: Protected attributes must be stripped before passing data to evidence extraction or scoring.

---

## Evidence Extraction

**FR-EV-01**: For each scorecard criterion, the system must produce one of: matched, not_matched, unknown, insufficient_evidence.  
**FR-EV-02**: Evidence statuses must only be returned for triggered evaluations that have completed.  
**FR-EV-03**: Each matched or not_matched criterion must have at least one verified source text excerpt.  
**FR-EV-04**: Source excerpts must be verbatim or near-verbatim from the original resume.  
**FR-EV-05**: Absent information must produce unknown or insufficient_evidence — never not_matched.  
**FR-EV-06**: Protected attributes must be excluded from all LLM-bound data payloads.

---

## Deterministic Scoring

**FR-SCORE-01**: Scores must be computed by the backend scoring engine, not by AI.  
**FR-SCORE-02**: Scores must be between 0 and 100, deterministic for identical inputs.  
**FR-SCORE-03**: matched = full points; not_matched = zero points; unknown/insufficient_evidence = 50% of criterion points.  
**FR-SCORE-04**: Confidence < 0.5 applies a 25% penalty to criterion points.  
**FR-SCORE-05**: Must-have skills use the proportional formula: (matched_count / total_count) × total_must_have_weight.  
**FR-SCORE-06**: Conflicting evidence uses the minimum value and sets a conflict flag.  
**FR-SCORE-07**: The engine must raise an error if protected attribute fields are detected in input.  
**FR-SCORE-08**: The complete scoring breakdown must be stored for traceability.

---

## Candidate Management

**FR-CAND-01**: Candidate profiles must show structured data, evaluation scores, and per-criterion evidence with source excerpts.  
**FR-CAND-02**: Protected attributes must be visible to recruiters but labeled as excluded from scoring.  
**FR-CAND-03**: Recruiters must be able to add requisition-scoped notes to candidate profiles.  
**FR-CAND-04**: Evidence status overrides must require a mandatory reason and trigger re-scoring.  
**FR-CAND-05**: Candidates must be searchable and filterable by score range, skills, location, notice period, pipeline stage.  
**FR-CAND-06**: Low-scoring candidates must remain searchable; minimum score filters must not delete records.  
**FR-CAND-07**: Filter state must persist across navigation within a session.

---

## Shortlisting and Submission

**FR-SUB-01**: Any candidate may be shortlisted regardless of score.  
**FR-SUB-02**: A recruiter must have viewed a candidate profile before submitting that candidate to a client.  
**FR-SUB-03**: Submissions must create a record linking candidate, requisition, recruiter, and client organization.  
**FR-SUB-04**: Contact details must be masked in all client-visible candidate profiles.  
**FR-SUB-05**: Submissions may be withdrawn before the client takes any action.  
**FR-SUB-06**: Bulk submissions are limited to 50 candidates per action; exceeding this rejects the whole batch.  
**FR-SUB-07**: Non-shortlisted candidates cannot be submitted.  
**FR-SUB-08**: Clients must receive in-app notifications when candidates are submitted.

---

## Client Hiring Manager Portal

**FR-CLIENT-01**: Clients see only candidates explicitly submitted to their organization.  
**FR-CLIENT-02**: Clients can shortlist, reject, or request interviews — all three actions always available.  
**FR-CLIENT-03**: Client actions update the pipeline stage and notify the submitting recruiter.  
**FR-CLIENT-04**: Clients can add rejection reasons and interview notes.  
**FR-CLIENT-05**: Evidence breakdown and source excerpts must be visible to clients.  
**FR-CLIENT-06**: Withdrawn submissions must disappear from client view within 5 seconds.

---

## Pipeline Tracking

**FR-PIPE-01**: The system must track pipeline stages: Submitted → Shortlisted_by_Client → Interview_Requested → Offer_Extended → Placed → Rejected.  
**FR-PIPE-02**: All stage changes must be recorded with actor and timestamp in the audit log.  
**FR-PIPE-03**: Stage reversions must require a mandatory reason note, regardless of actor role.  
**FR-PIPE-04**: Placed stage is locked; re-opening requires explicit recruiter action.  
**FR-PIPE-05**: The recruiter dashboard must show aggregated pipeline counts across all active requisitions.

---

## Responsible AI

**FR-RAI-01**: Protected attributes must never appear in evidence extraction or scoring inputs.  
**FR-RAI-02**: The scoring engine must validate at runtime that no protected attributes are present in its input.  
**FR-RAI-03**: No candidate may be automatically rejected; human review is required for all submissions.  
**FR-RAI-04**: All AI-generated content must be labeled "AI-generated" in the UI.  
**FR-RAI-05**: Bias monitoring must compute rank-order correlation between AI rankings and recruiter submission decisions.  
**FR-RAI-06**: Significant divergence alerts must be visible to the Delivery Head.  
**FR-RAI-07**: Monthly bias reports must aggregate statistics only, with no individual candidate identity.

---

## Audit and Privacy

**FR-AUDIT-01**: All defined system events must produce append-only audit log entries.  
**FR-AUDIT-02**: Audit log entries must contain event type, actor, org, resource, timestamp, and changed fields.  
**FR-AUDIT-03**: Audit logs must be retained for a minimum of 7 years.  
**FR-AUDIT-04**: A consent record must be created for each candidate at upload time.  
**FR-AUDIT-05**: Data deletion requests must anonymize all PII within 30 days.  
**FR-AUDIT-06**: Anonymized evaluation scores and audit entries must be retained after deletion.

---

## Background Processing

**FR-BG-01**: Bulk uploads must be processed asynchronously; the UI must not block.  
**FR-BG-02**: The system must return a batch job ID within 2 seconds of accepting an upload.  
**FR-BG-03**: Job status must be pollable; per-file status must be included in the response.  
**FR-BG-04**: Non-retryable errors must mark the file as permanently failed without affecting other files.  
**FR-BG-05**: Workers must support graceful shutdown, completing in-progress jobs within 60 seconds.
