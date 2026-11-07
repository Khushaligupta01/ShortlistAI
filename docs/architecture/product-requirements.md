# Product Requirements — ShortlistAI

## Product Vision

ShortlistAI is an evidence-based AI resume screening and client shortlist platform for staffing and recruitment firms. It reduces the manual effort of resume screening by applying AI-assisted extraction and deterministic scoring, while ensuring every hiring decision remains human-reviewed, transparent, and auditable.

The platform is not an autonomous hiring engine. AI assists recruiters by extracting structured information and surfacing evidence. Humans make every shortlisting and submission decision.

---

## Target Users

### Recruiter (Internal — Staffing Firm)
Responsible for managing job requisitions, uploading candidate resumes, reviewing AI-generated evaluations, shortlisting candidates, and submitting them to client hiring managers.

**Key pain points solved:**
- Manual resume reading and scoring across hundreds of applications
- Inconsistent evaluation criteria between different recruiters
- No structured way to present evidence to clients

### Client Hiring Manager (External — Client Organization)
Reviews candidates submitted by the staffing firm, provides feedback, and requests interviews. Has no visibility into candidates not submitted to them.

**Key pain points solved:**
- Receiving unfiltered, unranked CV piles
- No evidence behind why a candidate was recommended
- No structured pipeline to track candidate progress

### Delivery Head (Internal — Staffing Firm Management)
Monitors overall recruitment performance, reviews pipeline analytics, and oversees bias monitoring to ensure AI is being used fairly.

**Key pain points solved:**
- No aggregated view of team performance across requisitions
- No mechanism to detect AI ranking bias over time

---

## Core Product Goals

1. **Evidence-based screening**: Every candidate score is backed by specific resume excerpts, not black-box AI scoring.
2. **Human in the loop**: AI extracts and surfaces — humans decide and submit.
3. **Client trust**: Clients see structured profiles with AI evidence, building confidence in the shortlist.
4. **Operational efficiency**: Bulk upload of 500 resumes processed asynchronously with progress tracking.
5. **Responsible AI**: Protected attributes never influence scores; bias monitoring surfaces systemic patterns.
6. **Full auditability**: Every action logged immutably for compliance and investigation.

---

## Primary Features

### For Recruiters
- Secure authentication with role-based access
- Create and manage job requisitions
- AI-powered job description extraction to pre-populate scorecards
- Review and edit evaluation scorecards before activation
- Bulk upload up to 500 PDF/DOCX resumes per batch
- Real-time upload progress with per-file status tracking
- Duplicate candidate detection with manual resolution
- Structured candidate profiles with AI confidence indicators
- Deterministic 100-point scoring with full breakdown
- Evidence view showing exact resume excerpts per criterion
- Search and filter candidates by score, skills, location, pipeline stage
- Shortlist and submit candidates to clients
- Withdraw submissions before client action
- Track hiring pipeline status across all requisitions

### For Client Hiring Managers
- Secure authentication with organization-scoped access
- View only submitted candidates (contact details masked)
- Review evaluation evidence and AI rationale
- Shortlist, reject, or request interviews
- Add rejection reasons and interview notes
- View pipeline summary by stage

### For Delivery Heads
- Aggregated pipeline analytics across all requisitions
- Bias monitoring reports with rank-correlation statistics
- Time-in-stage analysis to identify bottlenecks
- Alert system for significant divergence between AI rankings and recruiter decisions

---

## Non-Goals (MVP)

- Automated candidate rejection (no such feature will be built)
- Public job posting or candidate self-registration
- Email or SMS notifications (in-app only for MVP)
- Mobile-optimized interface (desktop 1024px+ only for v1)
- Multi-language support
- Video interview integration
- Offer management
- Direct ATS integrations

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Resume bulk upload (500 files) processing time | < 30 minutes |
| Candidate profile page load time | < 2 seconds |
| Candidate list filter response time | < 3 seconds (up to 500 candidates) |
| Score determinism | 100% identical scores for identical inputs |
| Protected attribute influence on scores | 0% (enforced at runtime) |
| Audit log coverage | 100% of defined auditable events |

---

## Assumptions

1. All users have a modern desktop browser (Chrome 120+, Firefox 120+, Safari 17+).
2. The staffing firm operates as a single organization tenant initially.
3. LLM provider (OpenAI) availability is the primary external dependency; fallback is graceful failure, not automatic provider switching.
4. File storage in MVP is local filesystem; cloud storage is a future upgrade.
5. Candidates do not self-register; all candidate data enters via recruiter uploads.
6. Consent for processing candidate data is recorded at upload time by the recruiter on behalf of the firm.

---

## Constraints

- Resume uploads: PDF and DOCX only, max 10 MB per file, max 500 files per batch
- Bulk submission to client: max 50 candidates per submission action
- Scoring: 100-point deterministic model, configurable weights, no AI assignment of final score
- Data retention: Audit logs retained minimum 7 years
- Protected attributes: name, gender, age, photo, marital status, ethnicity, nationality, date of birth — none may influence scoring
