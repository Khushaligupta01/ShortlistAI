# AI Design — ShortlistAI

## AI Philosophy

AI in ShortlistAI is a **tool for extraction and evidence surfacing**, not a decision-maker. The system is designed around three firm principles:

1. **AI extracts; humans decide.** AI extracts structure from unstructured text and surfaces evidence. Recruiters make every shortlisting and submission decision.
2. **No fabrication, ever.** AI services must never invent information not present in the source document. When information is absent, the system returns `null` with confidence `0.0`.
3. **Transparent scoring.** The final candidate score is produced by a deterministic rule engine — not by AI. Every score point is traceable to a specific rule applied to a specific evidence result.

---

## AI Capabilities Overview

Three distinct AI capabilities are implemented as independent services, each behind the same LLM provider abstraction:

| Service | Input | Output | Notes |
|---------|-------|--------|-------|
| JD Extraction | Job description text | Structured requirements JSON | Only explicitly stated content |
| Resume Extraction | Raw resume text | Structured candidate profile JSON | Protected attrs stripped before scoring |
| Evidence Extraction | Clean profile + scorecard criteria | Per-criterion evidence with excerpts | Never fabricates source text |

---

## LLM Provider Abstraction

### Design

All AI calls are mediated through a `LLMProvider` protocol defined in `backend/app/ai/provider.py`. No service module imports a concrete provider directly.

```python
from typing import Protocol, Any

class LLMProvider(Protocol):
    """
    Abstract interface for all LLM provider implementations.
    Switching providers requires only a configuration change.
    """
    async def extract_jd(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]: ...

    async def extract_resume(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]: ...

    async def extract_evidence(
        self,
        prompt: str,
        output_schema: dict[str, Any],
        max_tokens: int,
    ) -> dict[str, Any]: ...
```

### Provider Loading

```python
# ai/provider_factory.py
def get_llm_provider(config: Config) -> LLMProvider:
    providers: dict[str, type[LLMProvider]] = {
        "openai": OpenAIProvider,
        # Add: "anthropic": AnthropicProvider
        # Add: "gemini": GeminiProvider
    }
    cls = providers.get(config.LLM_PROVIDER)
    if cls is None:
        raise ConfigurationError(f"Unknown LLM provider: {config.LLM_PROVIDER}")
    return cls(config)
```

The provider name comes from the `LLM_PROVIDER` environment variable. No hardcoded import in service modules.

### Initial Provider: OpenAI

Initial implementation uses `gpt-4o` via the OpenAI Python SDK. The concrete implementation in `openai_provider.py`:
- Uses structured output (JSON mode or function calling) to enforce schema compliance
- Logs provider name, model version, input tokens, output tokens after every call
- Raises `LLMExtractionError` on any provider-side failure (not a raw exception)

### Changing Providers

To add a new provider:
1. Create `backend/app/ai/{provider_name}_provider.py` implementing the `LLMProvider` protocol
2. Register it in `provider_factory.py`
3. Set `LLM_PROVIDER={provider_name}` in environment
4. No changes required in `jd_extraction.py`, `resume_extraction.py`, or `evidence_extraction.py`

---

## Retry and Timeout Policy

### Retry Policy

| Error Type | Retry? | Max Attempts | Backoff |
|------------|--------|-------------|---------|
| Network error / timeout | ✅ Yes | 3 total | 1s → 2s → 4s exponential |
| Rate limit (429) | ✅ Yes | 3 total | 1s → 2s → 4s exponential |
| Malformed JSON response | ❌ No | 1 (fail immediately) | — |
| Schema validation failure | ❌ No | 1 (fail immediately) | — |
| Authentication error (401) | ❌ No | 1 (fail immediately) | — |
| Any other provider error | ❌ No | 1 (fail immediately) | — |

### Timeouts

| Service | Request timeout |
|---------|----------------|
| JD Extraction | 30 seconds |
| Resume Extraction | 45 seconds |
| Evidence Extraction | 60 seconds |

After timeout, the error is treated as a network error and retried if attempts remain.

### Token Budgets (configurable per service)

| Service | Max Input Tokens | Max Output Tokens |
|---------|----------------|-------------------|
| JD Extraction | 4,000 | 1,000 |
| Resume Extraction | 8,000 | 2,000 |
| Evidence Extraction | 10,000 | 3,000 |

Calls exceeding the token budget are rejected before dispatch. The extraction is marked as failed and the error reason recorded.

### LLM Call Logging

Every LLM call appends an entry to the audit log containing:
- `provider_name`: e.g., "openai"
- `model_version`: e.g., "gpt-4o"
- `service_name`: "jd_extraction" | "resume_extraction" | "evidence_extraction"
- `input_token_count`
- `output_token_count`
- `latency_ms`
- `success`: true/false
- `error_type` (if failed)

---

## JD Extraction Service

### Purpose
Converts a free-text job description into structured fields used to pre-populate the scorecard editor.

### Input
```
jd_text: str  — the complete job description text
```

### Output Schema
```python
class JDExtractionResult(BaseModel):
    job_title: FieldWithConfidence[str]
    experience_range: FieldWithConfidence[ExperienceRange]  # {min_years, max_years}
    location: FieldWithConfidence[str]
    must_have_skills: list[FieldWithConfidence[str]]
    nice_to_have_skills: list[FieldWithConfidence[str]]
    notice_period: FieldWithConfidence[str]
    other_requirements: list[FieldWithConfidence[str]]  # explicitly stated mandatory requirements
    raw_llm_response_json: str  # stored for audit

class FieldWithConfidence(BaseModel, Generic[T]):
    value: T | None   # null if field not found in JD
    confidence: float  # 0.0 if null; 0.0–1.0 if value present
```

### Critical Constraints

**No fabrication**: If a field cannot be extracted from the JD text, `value = null` and `confidence = 0.0`. The LLM prompt explicitly states: "Only extract fields explicitly stated in the text. Do not infer or add requirements not present in the source."

**Must-have skills are explicit only**: Post-extraction validation checks that each must-have skill appears as a substring (case-insensitive) of the original JD text. Skills failing this check are moved to a review queue for recruiter confirmation.

**Other requirements**: Only requirements explicitly stated as mandatory are included in `other_requirements`. Optional or "nice to have" statements go in `nice_to_have_skills`.

### Failure Handling
On LLM failure (after retries):
- Scorecard editor shows all fields as empty/null
- Error banner displayed to recruiter
- Recruiter can proceed with manual entry
- Raw LLM error is logged in audit log

---

## Resume Extraction Service

### Purpose
Converts raw resume text (pre-extracted by PyMuPDF or python-docx) into a structured candidate profile.

### Input
```
raw_text: str  — text extracted from PDF/DOCX file
                 (must be ≥ 50 words; fewer = parsing failure before reaching this service)
```

### Output Schema (Phase 4 Implementation)
```python
class CandidateSkillItem(BaseModel):
    raw_name: str
    normalized_name: str
    evidence: str | None = None
    related_employment_index: int | None = None

class CandidateEmploymentItem(BaseModel):
    company: str
    job_title: str
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    technologies: list[str] = Field(default_factory=list)
    is_current: bool = False

class CandidateEducationItem(BaseModel):
    institution: str
    qualification: str | None = None
    field_of_study: str | None = None
    graduation_year: int | None = None

class ResumeExtractionResult(BaseModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    total_experience_years: float | None = None
    notice_period_days: int | None = None
    skills: list[CandidateSkillItem] = Field(default_factory=list)
    employments: list[CandidateEmploymentItem] = Field(default_factory=list)
    educations: list[CandidateEducationItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    raw_llm_response_json: str | None = None
```

### Strict Non-Hallucination & Fairness Rules (Phase 4)
1. **Missing information must remain null**: If a resume does not explicitly state notice period, location, phone, or experience duration, that attribute is preserved as `null`. It is NEVER guessed.
2. **Never assume notice period**: If not explicitly written (e.g., "Notice period: 30 days"), leave as `None`.
3. **Never infer age or gender**: Age is never inferred from graduation years; gender is never inferred from names or pronouns.
4. **Never fabricate employment or education**: Only institutions and employers explicitly stated are parsed.
5. **No hallucinated experience calculations**: When total experience is not explicitly stated, overlapping employment dates are never combined without deterministic date interval math.
6. **Rule-Based Fallback**: When the AI provider is unavailable or unconfigured in development, a deterministic zero-hallucination rule-based fallback extracts explicitly matched regex patterns (email, phone, dates) and leaves missing attributes as `null`.

### Protected Attribute Handling

After extraction, the `ProtectedAttributeStripper` creates a `clean_profile` by removing all protected attribute field keys and values before any downstream processing:

```python
PROTECTED_ATTRIBUTE_FIELDS = {
    "full_name", "gender", "age", "date_of_birth",
    "photograph", "marital_status", "ethnicity", "nationality"
}

def strip(profile: dict) -> dict:
    return {k: v for k, v in profile.items()
            if k not in PROTECTED_ATTRIBUTE_FIELDS}
```

The full profile (including protected attributes) is stored in `candidates.parsed_profile_json` for Recruiter display. The clean profile is used for all AI and scoring operations.

### Failure Conditions
| Condition | Outcome |
|-----------|---------|
| Word count < 50 | Mark as `parsing_failure`; notify recruiter with reason; do not call LLM |
| Unsupported file encoding | Mark as `parsing_failure`; record error |
| LLM returns malformed schema | Mark as `parsing_failure`; no retry; record error |
| LLM unavailable (after retries) | Mark as `parsing_failure`; raw text retained for re-extraction |
| Successful parse | No notification sent |

### Re-Extraction Support
Raw text is stored separately in `resumes.raw_text`. If the LLM provider is later updated or the extraction schema changes, re-extraction can be triggered without re-uploading the original file.

---

## Evidence Extraction Service

### Purpose
Compares a candidate's clean profile against each scorecard criterion and produces evidence assessments with source text excerpts.

### Input
```
clean_profile: dict  — candidate profile with all PA fields stripped
criteria: list[ScorecardCriterion]  — active scorecard criteria
raw_text: str  — original resume text (used for excerpt verification only)
```

### Output Schema
```python
class EvidenceResult(BaseModel):
    criterion_id: UUID
    criterion_label: str
    evidence_status: Literal["matched", "not_matched", "unknown", "insufficient_evidence"]
    confidence: float  # 0.0–1.0
    source_excerpts: list[str]  # verbatim from resume (required for matched/not_matched)
    flags: EvidenceFlags

class EvidenceFlags(BaseModel):
    low_confidence: bool   # True if confidence < 0.5
    conflict: bool         # True if conflicting evidence detected
```

### Evidence Status Semantics

| Status | When Used | Scoring Treatment |
|--------|-----------|------------------|
| `matched` | Criterion clearly satisfied by evidence in resume | Full criterion points |
| `not_matched` | Criterion clearly not satisfied by evidence | Zero points |
| `unknown` | Resume lacks relevant information to assess this criterion | 50% of criterion points |
| `insufficient_evidence` | Some evidence present but too thin to make a determination | 50% of criterion points |

**Critical rule**: `unknown` and `insufficient_evidence` are NOT failures. They represent uncertainty, and the system awards partial credit to avoid penalizing candidates for information not present in their resume.

### Anti-Fabrication Enforcement

After extraction, each `source_excerpt` is validated:
1. The excerpt is searched in `raw_text` using fuzzy string matching (≥ 80% token overlap)
2. If an excerpt cannot be verified as present in the original resume text, it is discarded
3. If discarding excerpts leaves a `matched` or `not_matched` criterion without any verified excerpt, the status is downgraded to `insufficient_evidence`
4. This ensures `source_excerpts` always contains only text actually present in the resume

### Protected Attribute Guard (defense in depth)

Even though `ProtectedAttributeStripper` runs before this service, the Evidence Extraction Service performs its own runtime check:

```python
if any(field in clean_profile for field in PROTECTED_ATTRIBUTE_FIELDS):
    raise ProtectedAttributeViolationError(
        f"Protected attribute fields detected in evidence extraction input: "
        f"{[f for f in PROTECTED_ATTRIBUTE_FIELDS if f in clean_profile]}"
    )
```

This ensures protection holds even if called incorrectly.

### Evidence Only After Evaluation Triggered

The service returns evidence statuses only when called as part of a triggered evaluation. It cannot be called to check evidence status for an evaluation that has not been initiated. This prevents partial or hypothetical evidence responses.

---

## Scoring Engine (Non-AI)

The Scoring Engine is explicitly **not an AI component**. It is a pure deterministic function.

### Inputs
- `evidence: list[EvidenceResult]` — one per scorecard criterion
- `scorecard: ScorecardSchema` — criteria with weights summing to 100

### Algorithm

```
Pre-condition:
  Assert no PA fields in any input dict → raise ProtectedAttributeError if found

For each criterion C:
  
  Step 1 — Base points (by evidence status):
    matched              → base = C.weight
    not_matched          → base = 0.0
    unknown              → base = C.weight × 0.5
    insufficient_evidence → base = C.weight × 0.5

  Step 2 — Confidence penalty:
    IF evidence[C].confidence < 0.5 (strictly less than):
        earned = base × 0.75   (25% penalty)
        low_confidence_flag = True
    ELSE:
        earned = base

  Step 3 — Conflict handling:
    IF evidence[C].flags.conflict == True:
        Use minimum value across all conflicting evidence values
        conflict_flag = True

Must-have skills override (all must_have_skill criteria together):
  matched_must_have_count = count of must_have_skill criteria with status == "matched"
  total_must_have_count = total count of must_have_skill criteria
  must_have_total_weight = sum of weights of all must_have_skill criteria

  must_have_earned = (matched_must_have_count / total_must_have_count) × must_have_total_weight
  
  This formula is the single source of truth for must-have scoring, covering:
    - 0 matched: 0 points
    - Partial match: proportional points
    - All matched: full points
    - Single must-have: 0 or full

Final:
  total_score = sum of earned points across all criteria
  total_score = clamp(total_score, 0.0, 100.0)
```

### Determinism Guarantee
The function has no external dependencies, no I/O, no randomness, no mutable shared state. For identical inputs it always produces identical outputs. This is verified by property-based tests.

### Worked Example

Scorecard: experience (30), Python (20), FastAPI (20), notice period (15), location (10), Kubernetes (5)

| Criterion | Status | Confidence | Base | After Penalty | Notes |
|-----------|--------|-----------|------|---------------|-------|
| Experience | matched | 0.88 | 30.0 | 30.0 | — |
| Python | matched | 0.94 | — (must-have) | — | Proportional formula |
| FastAPI | unknown | 0.42 | — (must-have) | — | Proportional formula |
| Notice period | matched | 0.85 | 15.0 | 15.0 | — |
| Location | not_matched | 0.91 | 0.0 | 0.0 | — |
| Kubernetes | matched | 0.76 | 5.0 | 5.0 | — |

Must-have: 1 matched / 2 total × 40 weight = **20.0 pts**

Total = 30 + 20 + 15 + 0 + 5 = **70.0 / 100**

---

## Responsible AI Design

### What AI Must Not Do
- Assign or influence the final candidate score
- Fabricate information not present in source documents
- Consider protected attributes in any extraction or evidence assessment
- Automatically reject any candidate
- Access candidate data across organization boundaries

### Bias Monitoring
- For each requisition with ≥ 20 candidates, the Bias Monitor computes Spearman rank-order correlation between AI score ranking and Recruiter submission order
- Correlation < 0.3 or > 0.97 over a rolling 90-day window (min 5 requisitions) triggers an alert to the Delivery Head
- Monthly reports aggregate per-requisition statistics; no individual candidate identity surfaced
- Bias monitoring data retained for 24 months
- Each metric displayed with a plain-language explanation (≤ 50 words)

### AI Label in UI
Every AI-generated field in the user interface displays a visible "AI-generated" label. This is unconditional — not configurable. The label communicates to users that the content requires human review.

### Human Review Gate
Before a recruiter can submit a candidate to a client, the system verifies that the recruiter has viewed the candidate profile (a `CANDIDATE_PROFILE_VIEWED` audit event must exist). This enforces the human-in-the-loop principle at the system level.

---

## Phase 5 Implementation: Evidence Extraction & Controlled Normalization

### Controlled Skill Normalization Architecture
Implemented in `backend/app/services/skill_normalization_service.py`:
- Canonical alias mappings for common variations (e.g. `react.js`, `reactjs` -> `react`; `postgresql`, `postgres` -> `postgresql`; `golang` -> `go`).
- Strict boundary preservation rules:
  - `Spring` does NOT match `Spring Boot`.
  - `Java` does NOT match `JavaScript`.
  - `C` does NOT match `C++` or `C#`.
  - `TypeScript` does NOT match `JavaScript`.
- Token-level boundaries prevent partial substring confusion.

### Evidence Extraction & Anti-Fabrication Engine
Implemented in `backend/app/ai/evidence_extraction_service.py`:
- Protected Demographic Stripping: Strips gender, age, ethnicity, marital status, nationality, and graduation dates before prompt creation. Raises `ProtectedAttributeViolationError` if prohibited fields are detected.
- Resume Token Overlap Verification: Any extracted evidence quotation claiming `MATCHED` or `PARTIAL` status is checked against the raw resume text. If the resume does not contain the quoted tokens (overlap < 40%), the evidence status is safely downgraded to `UNKNOWN` or `NOT_MATCHED` with confidence reduced to 0.0.
- Deterministic Fallback: When the AI provider is unavailable, times out, or fails schema validation, the engine automatically falls back to an offline rule-based extraction that evaluates normalized candidate skills, experience years, notice days, and locations directly against criteria without fabricating text.

### Deterministic Scoring Formulas
Implemented in `backend/app/services/scoring_engine_service.py`:
- Category Weights: Experience (30), Must-Have Skills (40), Notice Period (15), Location (10), Nice-To-Have Skills (5) = 100 points.
- Raw Score: Direct sum of awarded points across all categories.
- Normalized Provisional Score: $\frac{\text{Raw Score}}{\text{Maximum Available Points}} \times 100$, where criteria with status `UNKNOWN` are excluded from the denominator so candidates are not penalized for missing resume metadata.
- Evidence Coverage: $\frac{\text{Count of Evaluated Criteria with Explicit Evidence}}{\text{Total Criteria}} \times 100$.
- Confidence Levels:
  - `HIGH`: Evidence coverage $\ge 80\%$, average confidence $\ge 0.75$, no critical missing information.
  - `NEEDS_REVIEW`: Moderate evidence coverage or partial/uncertain evidence.
  - `LOW`: Evidence coverage $< 50\%$ or average confidence $< 0.50$.

