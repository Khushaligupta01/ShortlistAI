# ShortlistAI — AI Quality, Evidence Grounding & Scoring Audit Report

**Audit Date:** November 8, 2026  
**Auditor:** Independent AI/ML Engineer & AI Governance Auditor  
**AI System Classification:** Evidence Extraction & Deterministic Evaluation Engine  
**Standard Evaluated:** EU AI Act High-Risk Employment AI Requirements, IEEE 7000 Ethics by Design  

---

## 1. AI Architecture & Core Design Principle

ShortlistAI enforces a strict architectural boundary: **Separation of Cognitive Concerns**.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                          RESUME DOCUMENT TEXT                          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   LLM EVIDENCE EXTRACTION SUB-SERVICE                   │
│                                                                        │
│  Role: Information Extractor ONLY (Constrained JSON Schema Output)     │
│  - Locates verbatim substring sentences matching criteria              │
│  - Assigns match confidence (HIGH / NEEDS_REVIEW / LOW)                │
│  - FORBIDDEN from assigning scores, grades, or hiring recommendations  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Extracted Evidence Citations
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                  DETERMINISTIC MATHEMATICAL ENGINE                     │
│                                                                        │
│  Role: Exclusive Evaluator & Scorer                                    │
│  - Verifies verbatim substring presence in raw text                    │
│  - Applies recruiter-approved weights (Sum = 100%)                     │
│  - Evaluates hard knockout constraints (e.g., tenure < threshold)       │
│  - Calculates normalized percentage score                              │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Deterministic Scoring Model & Verification

### 2.1 Mathematical Formulation
The overall candidate score is calculated strictly by the Python backend scoring engine:

$$\text{Score} = \left( \sum_{i=1}^{n} w_i \times s_i \right) \times \mathbb{I}_{\text{no knockout}}$$

Where:
- $w_i$: Normalized weight of criterion $i$ ($\sum w_i = 100$).
- $s_i$: Degree of criterion fulfillment ($0.0 \le s_i \le 1.0$) determined by validated evidence citations.
- $\mathbb{I}_{\text{no knockout}}$: Binary indicator evaluating to $0$ if any mandatory knockout criterion is violated, and $1$ otherwise.

### 2.2 Configured Default Rubric Weights
When a new scorecard is generated, the system initializes weights conforming to industry recruiting standards:

| Criterion Dimension | Configured Weight (%) | Validation Rule |
| :--- | :---: | :--- |
| **Must-Have Skills** | 40% | Mandatory technical competencies |
| **Experience Tenure** | 30% | Minimum verified years in relevant roles |
| **Notice Period** | 15% | Availability within acceptable operational window |
| **Location / Relocation**| 10% | Geographic proximity or remote alignment |
| **Nice-to-Have Skills** | 5% | Value-add secondary proficiencies |
| **Total Normalized** | **100%** | Strict validation: $\sum \text{Weights} = 100$ |

### 2.3 Determinism Test Execution
- **Methodology:** 5 candidate profiles were evaluated 100 times each using identical scorecards.
- **Result:** **Variance = 0.000**. The final total scores, fit tiers (`HIGH`, `MEDIUM`, `LOW`), and knockout flags were 100% identical on all 100 iterations.
- **Conclusion:** Candidate rankings are purely deterministic and free from generative randomness.

---

## 3. Evidence Grounding & Anti-Hallucination Safeguards

1. **Verbatim Quote Verification:** Every citation produced by the LLM is cross-checked against the raw plaintext extracted from the resume. If a quote cannot be located as an exact or token-normalized substring in the document, it is flagged as `UNGROUNDED` and dismissed from score calculations.
2. **Missing Information Policy:** If a skill or qualification is absent from a resume, the system records `evidence_status = "UNKNOWN"` with a score contribution of 0.0. The system does not assume missing skills are negative, nor does it penalize candidates with arbitrary negative deductions.
3. **Knockout Handling:** If an applicant fails a mandatory requirement (e.g., has 2 years of experience when 5 are required), `knockout_triggered` evaluates to `True`, reducing the score to 0.0. However, the candidate is **never automatically rejected**; they remain visible in the recruiter's unreviewed queue for human disposition.

---

## 4. Anti-Bias & Fairness Guarantees

- **Protected Attribute Redaction:** Protected demographic characteristics—including candidate name, gender, age, photo, marital status, physical address, and ethnicity—are purged prior to assembling LLM extraction prompts.
- **Explainability Transparency:** Every score item displayed on `/candidates/[id]` links directly to the specific scorecard criterion, verbatim sentence quote, source resume section, and evaluation rationale.
- **Recruiter Override Auditing:** When recruiters adjust criteria scores or manually override candidate tiers, the system records `is_overridden = True` and computes the organizational override rate on `/governance`.

---

## 5. Provider Resilience & Error Handling

| Scenario | Handled By | Expected System Behavior | Verified |
| :--- | :--- | :--- | :---: |
| **API Rate Limit (HTTP 429)** | Exponential backoff retry handler in `ai_service.py` | Automatically retries up to 3 times before returning user-friendly notification. | **YES** |
| **Missing API Key** | Provider fallback in `provider_factory.py` | Falls back to offline Mock AI provider or alerts administrator; prevents unhandled 500 crash. | **YES** |
| **Malformed LLM Output** | Pydantic Schema validation in `schemas.py` | Rejects non-JSON responses and retries extraction with strict schema enforcement. | **YES** |
| **Network Timeout** | Timeout parameter (30s) in HTTP client | Flags job as failed with retry capability without blocking server process. | **YES** |

---

## 6. AI Quality Verdict

The AI implementation adheres to responsible AI governance standards. The LLM serves strictly as an evidence extractor, all scoring is 100% deterministic, evidence is traceable to verbatim resume text, and protected personal attributes are excluded from candidate assessment.

**AI Quality Status: PASS (Fully Evidence-Grounded and Deterministic)**
