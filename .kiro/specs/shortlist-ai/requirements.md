# Requirements Document

## Introduction

ShortlistAI is an evidence-based AI resume screening and client shortlist platform for staffing and recruitment firms. The platform enables recruiters to create job requisitions, extract structured requirements from job descriptions using AI, bulk-upload candidate resumes, evaluate candidates against configurable scorecards using deterministic scoring, and submit shortlists to client hiring managers — all while maintaining responsible AI principles, multi-tenant data isolation, and full audit traceability.

The system serves three primary roles: **Recruiter** (internal staffing firm staff), **Client Hiring Manager** (external client-side reviewer), and **Delivery Head** (internal management oversight). It comprises a Next.js frontend, a Python/FastAPI backend, PostgreSQL persistence, background job processing for bulk uploads, and a pluggable LLM integration layer.

---

## Glossary

- **System**: The ShortlistAI platform as a whole.
- **Recruiter**: An authenticated internal user belonging to a staffing firm organization who manages requisitions, uploads resumes, reviews evaluations, and submits shortlists.
- **Client_Hiring_Manager**: An authenticated external user belonging to a client organization who reviews submitted candidate profiles, shortlists or rejects candidates, and requests interviews.
- **Delivery_Head**: An authenticated internal user with elevated visibility across all requisitions and pipeline analytics within their organization.
- **Organization**: A tenant entity — either a staffing firm or a client company — whose data is isolated from all other organizations.
- **Requisition**: A job opening record created by a Recruiter, containing a job description and associated scorecard.
- **Job_Description** (JD): The free-text or structured description of a role attached to a Requisition.
- **Scorecard**: A configurable evaluation template linked to a Requisition, containing weighted criteria used to assess candidates.
- **Scorecard_Criteria**: An individual evaluation dimension within a Scorecard (e.g., must-have skill, experience range, location).
- **Candidate**: A person whose resume has been uploaded and parsed within the system; identified by deduplicated profile.
- **Resume**: A raw document (PDF or DOCX) uploaded by a Recruiter, associated with a Candidate.
- **Candidate_Profile**: The structured representation of a Candidate derived from resume parsing: skills, experience, employment history, education, location, notice period, and evidence.
- **JD_Extraction_Service**: The AI sub-service responsible for extracting structured requirements from a Job_Description.
- **Resume_Extraction_Service**: The AI sub-service responsible for parsing a Resume document into a structured Candidate_Profile.
- **Evidence_Extraction_Service**: The AI sub-service responsible for comparing a Candidate_Profile against Scorecard_Criteria and producing matched/not-matched/unknown/insufficient-evidence assessments with source excerpts.
- **Scoring_Engine**: The deterministic backend component that computes a 100-point candidate score from Evidence_Extraction outputs according to fixed, configurable rules — without AI involvement in final score assignment.
- **Evaluation**: The record combining evidence extraction results and a deterministic score for a specific Candidate against a specific Requisition.
- **Submission**: The act of a Recruiter forwarding a Candidate's profile to a client organization for review.
- **Pipeline**: The ordered set of hiring stages a Candidate progresses through after submission (e.g., Submitted, Shortlisted, Interview Requested, Rejected).
- **Audit_Log**: An immutable record of system events for compliance and traceability.
- **Consent_Record**: A record documenting the legal basis under which a Candidate's personal data is stored and processed.
- **Protected_Attribute**: Any data field that must not influence scoring or ranking — including name, gender, age, photo, marital status, and ethnicity.
- **Contact_Masking**: The suppression of a Candidate's personally identifiable contact details (phone, email, address) from Client_Hiring_Manager views.
- **Duplicate_Detection**: The process of identifying whether an uploaded Resume corresponds to a Candidate already present in the system.
- **LLM_Provider**: An external large language model service used by the AI sub-services, accessed through a provider abstraction layer.
- **Background_Job**: An asynchronous task executed outside the HTTP request cycle, used for bulk resume processing.
- **RBAC**: Role-Based Access Control; the mechanism governing which actions each user role may perform.
- **JWT**: JSON Web Token; the mechanism used for stateless authentication session tokens.
- **Multi_Tenant_Isolation**: The guarantee that data belonging to one Organization is inaccessible to users of another Organization.
- **Bias_Monitor**: The periodic process comparing AI-derived rankings against final recruiter decisions to surface potential systematic bias.

---

## Requirements

### Requirement 1: User Authentication

**User Story:** As a user of any role, I want to securely authenticate with the system, so that my identity is verified and I can access only the data and actions appropriate to my role.

#### Acceptance Criteria

1. THE System SHALL store user passwords using a cryptographically strong, salted hashing algorithm (bcrypt or Argon2) and SHALL never persist plaintext passwords.
2. WHEN a user submits valid credentials (email and password), THE System SHALL issue a signed JWT access token with a configurable expiry and a refresh token stored server-side.
3. WHEN a user submits invalid credentials, THE System SHALL return an authentication failure response without revealing whether the email or the password was incorrect.
4. WHEN a JWT access token expires, THE System SHALL require the client to present a valid refresh token to obtain a new access token.
5. WHEN a refresh token is used or revoked, THE System SHALL invalidate it to prevent reuse.
6. IF a user account is disabled or deleted, THEN THE System SHALL reject all authentication attempts for that account immediately.
7. THE System SHALL enforce RBAC such that each API endpoint checks the authenticated user's role before permitting the operation.
8. WHEN a user logs out, THE System SHALL revoke the associated refresh token.
9. THE System SHALL rate-limit authentication attempts to a maximum of 10 failed attempts per account per 15-minute window, after which THE System SHALL temporarily lock the account and notify the user.
10. FOR ALL authentication tokens issued by the System, the token SHALL be cryptographically signed with a secret key not stored in application source code.

---

### Requirement 2: Organization and Multi-Tenant Isolation

**User Story:** As a platform operator, I want each organization's data to be strictly isolated, so that staffing firm data and client data are never visible across organizational boundaries.

#### Acceptance Criteria

1. THE System SHALL associate every user, requisition, candidate, resume, evaluation, submission, and audit log record with exactly one Organization.
2. WHEN a user makes any data retrieval request, THE System SHALL filter results to records belonging to the user's Organization, unless an explicit cross-org relationship (e.g., submission) grants access.
3. IF a request attempts to access a resource belonging to a different Organization, THEN THE System SHALL return a not-found or forbidden response and SHALL log the access attempt.
4. THE System SHALL support two Organization types: staffing firm and client company; a user MAY belong to one or more Organizations.
5. WHEN a Submission is created, THE System SHALL grant the target client Organization read access to the submitted Candidate_Profile for that Requisition only.
6. THE System SHALL enforce tenant isolation at the database query layer, not solely at the application layer.

---

### Requirement 3: Role-Based Access Control

**User Story:** As an administrator, I want each role to have clearly defined permissions, so that users can only perform actions appropriate to their role.

#### Acceptance Criteria

1. THE System SHALL define at minimum three roles: Recruiter, Client_Hiring_Manager, and Delivery_Head.
2. THE Recruiter SHALL be permitted to create, read, update, and archive Requisitions within their Organization.
3. THE Recruiter SHALL be permitted to upload Resumes, view Candidate_Profiles, view Evaluations, manage Submissions, and track Pipeline status.
4. THE Client_Hiring_Manager SHALL be permitted to view only Candidate_Profiles that have been explicitly submitted to their Organization, with Contact_Masking applied.
5. THE Client_Hiring_Manager SHALL be permitted to shortlist, reject, or request interviews for submitted Candidates.
6. THE Client_Hiring_Manager SHALL NOT be permitted to view Candidates who have not been submitted to their Organization.
7. THE Delivery_Head SHALL be permitted to view aggregated pipeline analytics and bias monitoring reports across all Requisitions in their Organization.
8. WHERE the Recruiter dashboard already accommodates visibility controls AND no separate screen is required, THE System SHALL grant Delivery_Head access through permission elevation on existing Recruiter views rather than creating additional screens or authentication flows.
9. WHEN a user attempts an action not permitted by their role, THE System SHALL return a forbidden response and record the attempt in the Audit_Log.

---

### Requirement 4: Requisition Management

**User Story:** As a Recruiter, I want to create and manage job requisitions, so that I can track open roles and associate candidates with specific hiring needs.

#### Acceptance Criteria

1. WHEN a Recruiter submits a new Requisition with a job title and Job_Description, THE System SHALL persist the Requisition and assign it a unique identifier.
2. THE System SHALL allow a Recruiter to update the title, Job_Description, status, and metadata of any Requisition belonging to their Organization.
3. THE System SHALL allow a Recruiter to archive a Requisition, after which THE System SHALL prevent new Candidates from being added to the archived Requisition.
4. WHEN a Requisition is archived, THE System SHALL preserve all associated Candidates, Evaluations, Submissions, and Pipeline records for historical reference.
5. THE System SHALL list all active Requisitions for a Recruiter's Organization, ordered by creation date descending, with pagination.
6. WHEN a Recruiter searches Requisitions by keyword, title, or status, THE System SHALL return matching results within the user's Organization only, silently excluding any cross-Organization records that would otherwise match without returning an error.
7. THE System SHALL record a timestamped Audit_Log entry for every Requisition create, update, and archive action.

---

### Requirement 5: JD Intelligence — Structured Extraction

**User Story:** As a Recruiter, I want the system to automatically extract structured requirements from a job description, so that I don't have to manually enter scorecard criteria.

#### Acceptance Criteria

1. WHEN a Recruiter triggers JD extraction on a Requisition, THE JD_Extraction_Service SHALL parse the Job_Description and extract: job title, experience range (minimum and maximum years), location requirements, must-have skills (list), nice-to-have skills (list), notice period constraint, and any other explicitly stated requirements.
2. THE JD_Extraction_Service SHALL return extracted fields as a structured JSON object conforming to a defined schema, with each field annotated with a confidence score between 0.0 and 1.0.
3. IF a required field cannot be extracted from the Job_Description, THEN THE JD_Extraction_Service SHALL return a null value for that field with a confidence score of 0.0, rather than fabricating a value.
4. WHEN extraction completes, THE System SHALL pre-populate the Scorecard editor with the extracted fields, which a Recruiter MAY review and edit before saving.
5. THE System SHALL display the confidence score for each extracted field to the Recruiter in the Scorecard editor.
6. THE JD_Extraction_Service SHALL operate through the LLM_Provider abstraction layer, such that switching LLM providers requires no changes to the extraction interface or the Scorecard data model.
7. THE System SHALL store the raw LLM response alongside the structured extraction result for audit and debugging purposes.
8. FOR ALL JD extractions, the extracted must-have skills list SHALL contain only skills explicitly stated in the Job_Description; THE System SHALL not infer or add skills not present in the source text.

---

### Requirement 6: Scorecard Management

**User Story:** As a Recruiter, I want to review, edit, and save the AI-generated scorecard, so that evaluation criteria accurately reflect what the role requires.

#### Acceptance Criteria

1. THE System SHALL create a Scorecard for each Requisition, containing Scorecard_Criteria for: experience range, must-have skills, nice-to-have skills, notice period, and location.
2. THE Recruiter SHALL be able to add, edit, reorder, and delete individual Scorecard_Criteria before any evaluations are run.
3. THE System SHALL enforce that the sum of all criteria weights in a Scorecard equals exactly 100 points before the Scorecard is marked as active.
4. THE System SHALL apply the following default weight distribution: experience 30 pts, must-have skills 40 pts, notice period 15 pts, location 10 pts, nice-to-have skills 5 pts.
5. THE Recruiter SHALL be able to modify the weight of any criterion, provided the total remains 100 points.
6. WHEN a Scorecard is saved as active, THE System SHALL prevent further structural changes (additions or deletions of criteria); WHEN a Recruiter resets an active Scorecard to draft status, THE System SHALL create a new draft Scorecard version and preserve the prior active version unchanged, so that historical Evaluation records continue to reference the version active at evaluation time.
7. THE System SHALL version Scorecards such that re-evaluations triggered after a weight change use the new version and prior Evaluation records reference the version that was active at evaluation time.
8. THE System SHALL record a timestamped Audit_Log entry for every Scorecard create, update, and activation action.

---

### Requirement 7: Bulk Resume Upload

**User Story:** As a Recruiter, I want to upload up to 500 resumes at once, so that I can efficiently process large candidate pools.

#### Acceptance Criteria

1. THE System SHALL accept bulk resume uploads of up to 500 files per batch, supporting PDF and DOCX file formats.
2. WHEN a bulk upload is initiated, THE System SHALL validate each file for: format (PDF or DOCX only), size (maximum 10 MB per file), and absence of malicious content signatures before queuing it for processing.
3. IF a file fails validation, THEN THE System SHALL reject that file with a descriptive error message and SHALL continue processing the remaining valid files in the batch.
4. THE System SHALL process validated files asynchronously via Background_Jobs and SHALL provide the Recruiter with a real-time progress indicator showing: total files, processed count, failed count, and duplicate count.
5. WHEN a Background_Job completes processing for a file, THE System SHALL update the progress state within 5 seconds.
6. THE System SHALL perform Duplicate_Detection for each uploaded Resume by comparing extracted candidate identifiers (name + email, or name + phone) against existing Candidate records; WHEN a duplicate is detected, THE System SHALL flag it for Recruiter review rather than creating a second Candidate record.
7. THE System SHALL retain upload batch metadata (uploader, timestamp, file count, success/failure breakdown) in the Audit_Log.
8. IF a Background_Job fails due to a transient error, THEN THE System SHALL retry the job up to 3 times with exponential backoff before marking the file as permanently failed.
9. THE System SHALL store uploaded resume files in secure, access-controlled file storage with validation that file contents match the declared MIME type.

---

### Requirement 8: Document Parsing — Resume Extraction

**User Story:** As a Recruiter, I want the system to automatically extract structured information from uploaded resumes, so that I can compare candidates against scorecard criteria without manual data entry.

#### Acceptance Criteria

1. WHEN a Resume file is processed, THE Resume_Extraction_Service SHALL extract: full name, email, phone number, location, total years of experience, employment history (employer, title, dates, responsibilities), education (institution, degree, field, graduation year), skills (explicit list), notice period (if stated), and any other explicitly stated relevant information.
2. THE Resume_Extraction_Service SHALL return extracted data as a structured JSON object conforming to a defined Candidate_Profile schema, with a confidence score per field between 0.0 and 1.0.
3. IF a field cannot be determined from the Resume, THEN THE Resume_Extraction_Service SHALL return a null value with a confidence score of 0.0 and SHALL not fabricate or infer values.
4. THE System SHALL use PyMuPDF for PDF text extraction and python-docx for DOCX text extraction prior to passing content to the Resume_Extraction_Service.
5. THE System SHALL strip Protected_Attributes (name, gender, age inferred from dates, photo, marital status) from the data passed to the Scoring_Engine, while retaining them in the Candidate_Profile for Recruiter display only.
6. WHEN resume text extraction produces an empty or near-empty result (fewer than 50 words extracted), THE System SHALL mark the file as a parsing failure, notify the Recruiter with the specific failure reason, and SHALL NOT send a notification for resumes that parse successfully.
7. FOR ALL resumes processed by the system, the Resume_Extraction_Service SHALL operate through the LLM_Provider abstraction layer such that provider changes require no schema changes.
8. THE System SHALL store the raw extracted text and the structured Candidate_Profile separately to support re-extraction without re-uploading the original file.

---

### Requirement 9: Evidence Extraction

**User Story:** As a Recruiter, I want the system to compare each candidate's profile against the scorecard criteria and show me the specific evidence from their resume, so that I can understand why a candidate received a particular score.

#### Acceptance Criteria

1. WHEN an Evaluation is triggered for a Candidate against a Requisition and the criterion comparison has been performed, THE Evidence_Extraction_Service SHALL compare each Scorecard_Criterion against the Candidate_Profile and produce one of four evidence statuses: matched, not_matched, unknown, or insufficient_evidence; IF an Evaluation has not been triggered or the criterion comparison has not been completed, THEN THE Evidence_Extraction_Service SHALL refuse to return any evidence status including not_matched.
2. FOR EACH Scorecard_Criterion assessed as matched or not_matched, THE Evidence_Extraction_Service SHALL provide at least one source text excerpt from the Resume that supports the assessment.
3. THE Evidence_Extraction_Service SHALL NEVER fabricate source text excerpts; all excerpts SHALL be verbatim or near-verbatim text present in the original Resume.
4. THE Evidence_Extraction_Service SHALL record a confidence score between 0.0 and 1.0 for each criterion assessment.
5. IF a Scorecard_Criterion cannot be assessed due to absence of relevant information in the Resume, THEN THE Evidence_Extraction_Service SHALL return a status of unknown or insufficient_evidence, not not_matched.
6. THE System SHALL store each criterion's evidence status, source excerpts, and confidence scores in the Evaluation_Evidence table linked to the Evaluation record.
7. THE Evidence_Extraction_Service SHALL operate through the LLM_Provider abstraction layer; THE System SHALL not expose provider-specific response formats to the Evidence_Extraction_Service interface.
8. FOR ALL evidence extractions, Protected_Attributes SHALL be excluded from the data sent to the LLM_Provider.

---

### Requirement 10: Deterministic Scoring Engine

**User Story:** As a Recruiter, I want each candidate to receive a transparent, reproducible score based on defined rules, so that I can trust and explain the ranking to clients.

#### Acceptance Criteria

1. THE Scoring_Engine SHALL compute a total candidate score between 0 and 100 using only the evidence statuses and confidence scores produced by the Evidence_Extraction_Service; THE Scoring_Engine SHALL NOT call any LLM or AI service.
2. THE Scoring_Engine SHALL apply the following base allocation rules per criterion category (using the active Scorecard weights): experience match earns full experience weight; must-have skills earn full must-have weight divided equally across all must-have skills listed; notice period match earns full notice period weight; location match earns full location weight; nice-to-have skills earn full nice-to-have weight divided equally across all nice-to-have skills listed.
3. WHEN a criterion status is matched, THE Scoring_Engine SHALL award the full points allocated to that criterion.
4. WHEN a criterion status is not_matched, THE Scoring_Engine SHALL award zero points for that criterion.
5. WHEN a criterion status is unknown or insufficient_evidence, THE Scoring_Engine SHALL award a partial score equal to 50% of the criterion's allocated points, and SHALL flag the criterion for Recruiter review; THE Scoring_Engine SHALL NEVER treat unknown as a failure.
6. WHEN a criterion has a confidence score below 0.5, THE Scoring_Engine SHALL apply a penalty of 25% to the points that would otherwise be awarded for that criterion, and SHALL surface the low-confidence flag in the Evaluation display.
7. WHEN multiple must-have skills are present, THE Scoring_Engine SHALL award proportional points using the formula: (matched_count / total_must_have_count) × must_have_weight; this formula applies for all values of matched_count including zero, which correctly yields zero points, making the proportional formula the single source of truth for must-have skill scoring regardless of match count.
8. WHEN conflicting information exists for a single criterion (e.g., two employment records imply different experience totals), THE Scoring_Engine SHALL use the lower of the two values and SHALL flag the conflict in the Evaluation record.
9. THE Scoring_Engine SHALL produce identical scores for identical inputs on every execution; the scoring function SHALL be deterministic and side-effect-free.
10. THE System SHALL record the complete scoring breakdown — points per criterion, evidence status, confidence, flags — in the Evaluation record for full traceability.
11. FOR ALL scoring computations, Protected_Attribute values SHALL not be inputs to any scoring formula.

---

### Requirement 11: Candidate Profile View

**User Story:** As a Recruiter, I want to view a structured candidate profile alongside their evaluation results, so that I can make an informed decision about who to shortlist.

#### Acceptance Criteria

1. THE System SHALL display a Candidate_Profile page showing: structured extracted fields (skills, experience, employment history, education, location, notice period), the Evaluation score and breakdown, and per-criterion evidence with source excerpts.
2. THE System SHALL display the evidence status (matched / not_matched / unknown / insufficient_evidence) and confidence score for each Scorecard_Criterion on the Candidate_Profile page.
3. THE System SHALL surface low-confidence flags and conflict flags on the relevant criteria in the Candidate_Profile view.
4. THE System SHALL display the original resume (PDF/DOCX rendering or extracted text) alongside the structured profile to allow manual verification.
5. THE Recruiter SHALL be able to add free-text notes to a Candidate_Profile within the context of a specific Requisition; notes SHALL be stored and attributed to the authoring Recruiter.
6. THE System SHALL allow a Recruiter to override an evidence status for a criterion, with a mandatory reason field; overrides SHALL be recorded in the Audit_Log; WHEN an override is saved, THE System SHALL create a new Evaluation version that automatically recomputes the overall score and breakdown to reflect the overridden criterion, while the prior Evaluation version remains intact for historical reference.
7. THE System SHALL display Protected_Attributes on the Recruiter's Candidate_Profile view for reference but SHALL label them clearly as excluded from scoring.

---

### Requirement 12: Candidate Search and Filtering

**User Story:** As a Recruiter, I want to search and filter candidates across a requisition, so that I can quickly find candidates matching specific criteria without scrolling through hundreds of profiles.

#### Acceptance Criteria

1. THE System SHALL provide a search interface within each Requisition that allows filtering candidates by: score range, skill keywords, location, notice period range, evidence status on a specific criterion, and pipeline stage.
2. WHEN a Recruiter applies filters, THE System SHALL return matching candidates within the Requisition in under 3 seconds for datasets of up to 500 candidates.
3. THE System SHALL always display candidates in a ranked list ordered by total score descending by default, with the option to sort by individual criterion scores; the ranked list view is unconditional and not contingent on other display states.
4. THE System SHALL allow a Recruiter to search for low-scoring candidates (score 0–40) and SHALL present them with the same interface as high-scoring candidates; low scores SHALL NOT prevent profile access.
5. WHEN a Recruiter performs a full-text search within a Requisition, THE System SHALL search across extracted skills, job titles, and employer names in the Candidate_Profile.
6. THE System SHALL persist filter state within a session so that navigating to a Candidate_Profile and returning restores the previous filter configuration.

---

### Requirement 13: Shortlisting and Client Submission

**User Story:** As a Recruiter, I want to shortlist candidates and submit them to the client, so that clients can review only the candidates I have approved.

#### Acceptance Criteria

1. THE Recruiter SHALL be able to mark any Candidate within a Requisition as shortlisted; a Candidate MAY be shortlisted regardless of their score.
2. THE System SHALL prevent a Recruiter from submitting a Candidate to a client Organization unless the Recruiter has explicitly reviewed the Candidate_Profile (recorded as a profile view event in the Audit_Log).
3. WHEN a Recruiter submits a shortlisted Candidate to a client Organization, THE System SHALL create a Submission record linking the Candidate, Requisition, submitting Recruiter, target Organization, and submission timestamp.
4. WHEN a Submission is created, THE System SHALL apply Contact_Masking to the Candidate_Profile visible to the Client_Hiring_Manager, hiding email, phone, and home address.
5. THE Recruiter SHALL be able to withdraw a Submission before the Client_Hiring_Manager takes any action; WHEN withdrawn, THE System SHALL revoke the Client_Hiring_Manager's access to that Candidate_Profile.
6. THE System SHALL notify the relevant Client_Hiring_Manager (via in-app notification) when new Candidates are submitted to their Organization.
7. THE System SHALL record a timestamped Audit_Log entry for every Submission created, withdrawn, or modified.
8. THE System SHALL allow bulk submission of up to 50 shortlisted Candidates in a single action; IF a Recruiter attempts to submit more than 50 Candidates at once, THEN THE System SHALL reject the entire submission batch and require the Recruiter to resubmit with 50 or fewer Candidates.

---

### Requirement 14: Client Hiring Manager Portal

**User Story:** As a Client Hiring Manager, I want to review submitted candidates and take action on them, so that I can provide timely feedback to the staffing firm.

#### Acceptance Criteria

1. WHEN a Client_Hiring_Manager authenticates and navigates to their portal, THE System SHALL display only Candidates submitted to their Organization, grouped by Requisition.
2. THE System SHALL display each submitted Candidate_Profile with Contact_Masking applied; skills, experience, evaluation score, evidence breakdown, and recruiter notes SHALL be visible.
3. THE Client_Hiring_Manager SHALL always be able to take all three actions on any submitted Candidate — shortlist, reject, or request interview — regardless of the Candidate's current pipeline state; none of the three actions SHALL be conditionally disabled based on Candidate state.
4. WHEN a Client_Hiring_Manager takes an action on a Candidate, THE System SHALL update the Pipeline stage for that Candidate and notify the submitting Recruiter via in-app notification.
5. THE Client_Hiring_Manager SHALL be able to add a free-text rejection reason or interview note; reasons SHALL be stored and attributed to the authoring Client_Hiring_Manager.
6. THE System SHALL display a pipeline summary view for each Requisition, showing counts per stage: Submitted, Shortlisted, Interview Requested, Rejected.
7. IF a Submission is withdrawn by the Recruiter, THEN THE System SHALL remove the Candidate from the Client_Hiring_Manager's view immediately.
8. THE System SHALL present the evidence breakdown and source excerpts to the Client_Hiring_Manager so they can assess the AI's rationale.

---

### Requirement 15: Hiring Pipeline Tracking

**User Story:** As a Recruiter, I want to track the hiring pipeline status for every candidate in a requisition, so that I can manage client relationships and report on placement progress.

#### Acceptance Criteria

1. THE System SHALL maintain a Pipeline record for each Candidate–Requisition pair that has been submitted, tracking the current pipeline stage.
2. THE System SHALL support the following pipeline stages in order: Submitted → Shortlisted_by_Client → Interview_Requested → Offer_Extended → Placed → Rejected.
3. WHEN a pipeline stage changes, THE System SHALL record the previous stage, new stage, actor (who made the change), and timestamp in the Audit_Log.
4. THE System SHALL allow a Recruiter to manually advance or revert a pipeline stage; WHEN any actor reverts a pipeline stage, THE System SHALL require a mandatory reason note regardless of the actor's role before the reversion is accepted.
5. THE Recruiter dashboard SHALL display an aggregated pipeline view across all active Requisitions, showing candidate counts per stage.
6. WHEN a Candidate reaches the Placed stage, THE System SHALL prevent further stage changes unless the Recruiter explicitly re-opens the placement.
7. THE System SHALL allow a Delivery_Head to view pipeline analytics across all Requisitions in the Organization, including average time-in-stage and conversion rates.

---

### Requirement 16: Responsible AI — Protected Attribute Exclusion

**User Story:** As a compliance officer, I want the system to ensure that protected attributes never influence candidate scores, so that the platform does not facilitate discriminatory hiring decisions.

#### Acceptance Criteria

1. THE System SHALL identify and tag the following fields as Protected_Attributes: name, gender, age, photograph, marital status, ethnicity, nationality, and date of birth.
2. WHEN the Resume_Extraction_Service extracts a Candidate_Profile, THE System SHALL strip all Protected_Attribute values from the data payload before passing it to the Evidence_Extraction_Service or Scoring_Engine.
3. THE Scoring_Engine SHALL verify at runtime that its input data contains no Protected_Attribute fields; IF a Protected_Attribute field is detected in the scoring input, THEN THE Scoring_Engine SHALL abort the scoring computation and raise an error.
4. THE System SHALL never automatically reject a Candidate; THE System SHALL require a human Recruiter to review each Candidate_Profile before any submission action.
5. THE System SHALL retain low-scoring Candidates in the searchable candidate pool; filtering by minimum score SHALL be available but SHALL NOT automatically exclude Candidates from the database.
6. THE System SHALL label AI-generated content clearly in all user-facing screens, identifying it as AI-assisted and subject to human review.

---

### Requirement 17: Bias Monitoring

**User Story:** As a Delivery Head, I want periodic bias monitoring reports, so that I can detect and address systematic patterns between AI rankings and recruiter decisions.

#### Acceptance Criteria

1. THE System SHALL record, for each Requisition, the AI-generated score ranking order and the final Recruiter submission order (the set of Candidates submitted to clients).
2. THE Bias_Monitor SHALL compute, for each Requisition with at least 20 Candidates, a rank-order correlation coefficient between AI ranking and Recruiter submission decisions.
3. WHEN the Bias_Monitor detects a statistically significant divergence (correlation below 0.3 or above 0.97) between AI rankings and Recruiter decisions over a rolling 90-day period, THE System SHALL generate an alert visible to the Delivery_Head.
4. THE Bias_Monitor SHALL produce a monthly summary report available to the Delivery_Head, showing per-Requisition correlation statistics, top divergence cases, and any flagged anomalies.
5. THE System SHALL store bias monitoring data for a minimum of 24 months for trend analysis.
6. THE Bias_Monitor SHALL NOT surface individual Candidate identity in reports; reports SHALL aggregate statistics only.
7. WHEN a Delivery_Head views the bias monitoring report, THE System SHALL display a plain-language explanation of each metric alongside the statistical value.

---

### Requirement 18: Audit Logging

**User Story:** As a compliance officer, I want all significant system actions to be recorded in an immutable audit log, so that I can investigate incidents and demonstrate regulatory compliance.

#### Acceptance Criteria

1. THE System SHALL record an Audit_Log entry for every one of the following events: user login and logout, failed authentication attempts, Requisition create/update/archive, Scorecard create/update/activate, Resume upload initiation and completion, Candidate_Profile view, Evaluation triggered and completed, Submission create/withdraw, Pipeline stage change, Recruiter note add/edit, evidence status override, bias monitoring report generation, and data deletion request.
2. EACH Audit_Log entry SHALL contain: event type, actor user ID, actor organization ID, target resource type and ID, timestamp (UTC), and a JSON payload of changed fields (old and new values for update events).
3. THE System SHALL prevent modification or deletion of Audit_Log records through the application API; Audit_Log records SHALL be append-only.
4. THE System SHALL retain Audit_Log records for a minimum of 7 years.
5. THE Delivery_Head and system administrators SHALL be able to query Audit_Logs filtered by date range, event type, actor, and resource.
6. IF an Audit_Log write fails, THEN THE System SHALL reject the triggering operation and return an error rather than proceeding without a log record.

---

### Requirement 19: Consent and Data Privacy

**User Story:** As a data protection officer, I want the system to track consent and support data deletion, so that we comply with data privacy regulations.

#### Acceptance Criteria

1. THE System SHALL create a Consent_Record for each Candidate at the time of resume upload, recording: the legal basis for processing, the uploading Recruiter's identity, the Organization, and the timestamp.
2. THE System SHALL provide a mechanism for a Recruiter or administrator to submit a data deletion request for a Candidate, which SHALL remove or anonymize all Personally Identifiable Information (PII) fields from Candidate_Profile, Resume text, and Consent_Records while retaining anonymized Evaluation scores and Audit_Log entries.
3. WHEN a data deletion request is fulfilled, THE System SHALL complete anonymization within 30 days.
4. THE System SHALL record the data deletion request and its completion in the Audit_Log.
5. THE System SHALL not transfer Candidate PII to LLM_Provider APIs if the LLM_Provider's terms of service prohibit data retention; THE System SHALL use PII-stripped payloads where required.
6. THE System SHALL display a privacy notice to Recruiters during bulk upload that describes the legal basis for processing Candidate data.

---

### Requirement 20: LLM Provider Abstraction

**User Story:** As a platform engineer, I want all AI calls to go through a provider abstraction layer, so that we can switch LLM providers without changing business logic.

#### Acceptance Criteria

1. THE System SHALL define a single LLM_Provider interface (abstract class or protocol) with at minimum these methods: extract_jd(prompt, schema) → structured JSON, extract_resume(prompt, schema) → structured JSON, extract_evidence(prompt, schema) → structured JSON.
2. WHEN a concrete LLM_Provider implementation is replaced, THE JD_Extraction_Service, Resume_Extraction_Service, and Evidence_Extraction_Service SHALL require no code changes beyond the provider configuration.
3. THE System SHALL load the active LLM_Provider implementation from configuration, not from hardcoded imports in service modules.
4. THE System SHALL log the provider name, model version, and token usage for every LLM call in a structured format accessible to the Audit_Log.
5. IF an LLM_Provider call fails due to a network error or rate limit, THEN THE System SHALL retry up to 3 times with exponential backoff before marking the extraction as failed; IF an LLM_Provider call fails for any other reason (malformed response, schema validation failure, provider-side error), THEN THE System SHALL mark the extraction as failed immediately without retrying.
6. THE System SHALL enforce a maximum token budget per LLM call, configurable per service (JD extraction, resume extraction, evidence extraction), to control costs.

---

### Requirement 21: Security Controls

**User Story:** As a security engineer, I want the system to apply security controls throughout, so that the platform is protected against common web application vulnerabilities and data breaches.

#### Acceptance Criteria

1. THE System SHALL validate all uploaded files by checking both MIME type headers and magic bytes, rejecting files whose content does not match a PDF or DOCX signature.
2. THE System SHALL enforce a maximum upload size of 10 MB per file and 1 GB per batch (or 500 files, whichever is smaller).
3. THE System SHALL apply rate limiting to all public API endpoints: authentication endpoints at 10 requests per minute per IP, file upload endpoints at 5 uploads per minute per user, and other API endpoints at 100 requests per minute per user.
4. THE System SHALL store all secrets (database credentials, JWT signing keys, LLM API keys) in environment variables or a secrets management service and SHALL never embed them in source code or configuration files committed to version control.
5. THE System SHALL apply parameterized queries or ORM-level query building for all database interactions; THE System SHALL enforce SQL injection protection independently as a verifiable constraint; BOTH parameterized_queries_used AND sql_injection_protection SHALL hold as independent requirements.
6. THE System SHALL set all five of the following HTTP security headers on every response, and the security_headers_applied status SHALL be considered compliant only when ALL five are present: Content-Security-Policy, X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security (HTTPS only), and Referrer-Policy; absence of any single header SHALL constitute a requirement violation.
7. THE System SHALL serve all traffic exclusively over HTTPS in production; HTTP requests SHALL be redirected to HTTPS.
8. THE System SHALL scan uploaded file contents for known malware signatures using a file scanning library before storage.
9. IF a security scan flags a file as potentially malicious, THEN THE System SHALL quarantine the file, reject the upload, notify the uploading Recruiter, and log the event in the Audit_Log.

---

### Requirement 22: API Design and Integration

**User Story:** As a frontend developer, I want a well-defined REST API, so that I can build the Next.js frontend without ambiguity about endpoints, request formats, or error responses.

#### Acceptance Criteria

1. THE System SHALL expose a RESTful HTTP API using FastAPI with OpenAPI documentation auto-generated and accessible at /docs in non-production environments.
2. THE System SHALL use Pydantic models for all request and response bodies, enforcing schema validation on every endpoint.
3. WHEN a request body fails schema validation, THE System SHALL return a 422 Unprocessable Entity response with a structured error payload identifying each invalid field.
4. THE System SHALL version the API using a URL prefix (e.g., /api/v1/) to allow future breaking changes without disrupting existing clients.
5. THE System SHALL return consistent error response envelopes across all endpoints, containing: error code, human-readable message, and request trace ID.
6. THE System SHALL implement CORS configuration that restricts allowed origins to the configured frontend domain(s).
7. THE System SHALL use ISO 8601 UTC timestamps in all API request and response payloads.

---

### Requirement 23: Background Job Processing

**User Story:** As a Recruiter, I want large resume batches to be processed in the background without blocking the UI, so that I can continue working while uploads are processed.

#### Acceptance Criteria

1. THE System SHALL implement a lightweight background job queue for resume parsing tasks, supporting at minimum concurrent processing of 10 files simultaneously per deployment instance.
2. WHEN a bulk upload is accepted, THE System SHALL immediately return a batch job ID to the Recruiter and begin background processing asynchronously.
3. THE System SHALL expose a job status endpoint that returns the current state of a batch job: queued, processing, completed, or failed, with per-file status details.
4. WHEN a Background_Job encounters a non-retryable error (e.g., corrupt file, unsupported encoding), THE System SHALL mark that file as permanently failed, record the error reason, and continue processing remaining files.
5. THE System SHALL prevent duplicate Background_Jobs for the same file within the same batch by deduplicating on a content hash before queuing.
6. THE System SHALL support graceful shutdown of background workers, completing in-progress jobs before terminating.

---

### Requirement 24: Frontend — Recruiter Dashboard

**User Story:** As a Recruiter, I want a clear dashboard showing my active requisitions and pipeline summary, so that I can manage my workload at a glance.

#### Acceptance Criteria

1. THE System SHALL display a Recruiter dashboard as the default authenticated view, showing: active Requisition count, total Candidates across active Requisitions, candidates per pipeline stage aggregated across all Requisitions, and recent activity feed.
2. THE System SHALL render the dashboard using Next.js with server-side rendering for initial page load and client-side updates for live data.
3. THE System SHALL use Tailwind CSS and shadcn/ui components exclusively for all UI elements on all screens.
4. THE System SHALL be responsive and usable on viewport widths from 1024px and above; mobile viewports below 768px are out of scope for v1.
5. WHEN a Recruiter clicks a Requisition card on the dashboard, THE System SHALL navigate to the Requisition detail page showing the candidate ranked list.
6. THE System SHALL display loading skeleton states while API requests are in progress on all data-heavy screens.

---

### Requirement 25: Frontend — Bulk Upload Screen

**User Story:** As a Recruiter, I want a dedicated upload screen with real-time feedback, so that I can monitor the progress of large resume batches.

#### Acceptance Criteria

1. THE System SHALL provide a drag-and-drop file upload interface that accepts PDF and DOCX files, with a visual indicator for valid/invalid file types.
2. THE System SHALL display per-file upload status (pending, uploading, validating, processing, parsed, failed, duplicate) in a list view as files are processed.
3. THE System SHALL show a progress bar and summary statistics (total / success / failed / duplicate) that update in real time as Background_Jobs complete.
4. WHEN the Recruiter hovers over a failed file entry, THE System SHALL display the specific failure reason.
5. THE System SHALL allow the Recruiter to download a CSV report of the batch results (file name, status, failure reason) after processing completes.
6. WHEN duplicate Candidates are detected, THE System SHALL display a side-by-side comparison of the existing and new profiles and prompt the Recruiter to choose: update existing, keep both, or discard new; WHILE the Recruiter has not made an explicit choice, THE System SHALL hold the new profile in a pending state and SHALL NOT create or modify any Candidate record.

---

### Requirement 26: Frontend — Candidate Evaluation Screen

**User Story:** As a Recruiter, I want a detailed evaluation view per candidate that shows the score breakdown and evidence, so that I can explain my shortlisting decisions.

#### Acceptance Criteria

1. THE System SHALL display the total score prominently at the top of the Candidate_Profile page, alongside a visual score breakdown chart per criterion category.
2. THE System SHALL display each Scorecard_Criterion with its awarded points, maximum points, evidence status, confidence score, and supporting source text excerpt.
3. WHEN a criterion has a low-confidence or conflict flag, THE System SHALL visually highlight the criterion and display an explanation tooltip.
4. THE System SHALL allow a Recruiter to expand each criterion to view the full source text excerpt within the context of the original resume text.
5. THE System SHALL display the AI label on all AI-generated content on the Candidate_Profile page, clearly indicating which fields were extracted by AI.
6. THE System SHALL render the Candidate_Profile page within 2 seconds of navigation for profiles with any number of scorecard criteria; for profiles with more than 20 criteria, the 2-second bound SHALL still apply or the render time SHALL scale predictably and remain within a documented SLA.

---

### Requirement 27: Data Model Integrity

**User Story:** As a database engineer, I want the data model to enforce referential integrity and prevent orphaned records, so that the system remains consistent under concurrent operations.

#### Acceptance Criteria

1. THE System SHALL define foreign key constraints in the PostgreSQL schema for all relationships between: users↔organization_memberships, organizations↔requisitions, requisitions↔scorecards, scorecards↔scorecard_criteria, candidates↔resumes, candidates↔evaluations, evaluations↔evaluation_evidence, candidates↔submissions, submissions↔pipeline records, and users↔audit_logs.
2. THE System SHALL use database-level unique constraints to prevent: duplicate user emails within the system, duplicate Scorecard_Criteria types within a single Scorecard, and duplicate active Scorecards per Requisition.
3. THE System SHALL use optimistic locking (version column) on Requisition and Scorecard records to prevent lost updates under concurrent edits.
4. THE System SHALL run all multi-step write operations (e.g., create Evaluation + store Evidence records) within a database transaction, rolling back on any step failure.
5. THE System SHALL define appropriate indexes on high-query columns: organization_id on all tenant-scoped tables, requisition_id on candidates and evaluations, candidate_id on evaluations and submissions, and created_at on audit_logs.

---

### Requirement 28: Testing and Quality Assurance

**User Story:** As a software engineer, I want a comprehensive test suite, so that regressions are caught automatically before deployment.

#### Acceptance Criteria

1. THE System SHALL include Pytest-based unit tests for the Scoring_Engine covering: all four evidence status types, partial skill matching, unknown handling at 50% allocation, low-confidence penalty, conflict flag logic, and Protected_Attribute exclusion verification.
2. THE System SHALL include Pytest-based API integration tests for all critical endpoints: authentication, requisition CRUD, resume upload, evaluation trigger, submission creation, and pipeline stage transitions.
3. THE System SHALL include property-based tests (using Hypothesis) for the Scoring_Engine verifying: score always falls within [0, 100], identical inputs always produce identical scores (determinism), unknown statuses always yield a score strictly greater than 0 and less than the criterion's full allocation, and Protected_Attribute fields in input always trigger an error (never a score).
4. THE System SHALL include end-to-end tests for the critical Recruiter path where ALL of the following steps must each have an individual test AND a combined path test that asserts their successful conjunction: login, create requisition, upload resume, view evaluation, shortlist, and submit to client.
5. THE System SHALL achieve a minimum of 80% line coverage on the Scoring_Engine and Evidence_Extraction_Service modules.
6. THE System SHALL include contract tests verifying that each concrete LLM_Provider implementation satisfies the LLM_Provider interface schema.

---

### Requirement 29: Delivery Head Analytics

**User Story:** As a Delivery Head, I want consolidated pipeline analytics across all requisitions, so that I can assess team performance and identify bottlenecks.

#### Acceptance Criteria

1. THE Delivery_Head dashboard SHALL display, for the selected date range: total active Requisitions, total Candidates uploaded, total Submissions made, Submission-to-Placement conversion rate, and average time from upload to submission.
2. THE System SHALL allow a Delivery_Head to filter analytics by Recruiter, Requisition, and date range.
3. THE System SHALL display average time-in-stage metrics for each pipeline stage across all Requisitions, identifying stages with above-average dwell times.
4. WHEN a Delivery_Head views the analytics dashboard, THE System SHALL render the page within 5 seconds for organizations with up to 10,000 Candidate records.
5. THE System SHALL present pipeline analytics using visual charts (bar, funnel, or line charts) rendered using a charting library compatible with Next.js and Tailwind CSS; the charting library SHALL natively support all three chart types (bar, funnel, and line), and chart_type_supported AND chart_library_compatible SHALL both hold as independent verifiable requirements.

---

### Requirement 30: Account and Privacy Controls Screen

**User Story:** As any authenticated user, I want account management and privacy controls, so that I can manage my profile and exercise data subject rights.

#### Acceptance Criteria

1. THE System SHALL provide an account settings screen where any authenticated user can: update their display name, change their password (requiring current password confirmation), and view their active sessions.
2. THE System SHALL allow a Recruiter or administrator to initiate a Candidate data deletion request from the Candidate_Profile page, which SHALL trigger the anonymization workflow defined in Requirement 19.
3. THE System SHALL display a log of recent actions performed by the authenticated user (last 30 days) on the account settings screen.
4. WHEN a user changes their password, THE System SHALL invalidate all existing refresh tokens for that user.
5. THE System SHALL allow a Delivery_Head or administrator to deactivate a user account, which SHALL immediately revoke all active sessions for that user.

