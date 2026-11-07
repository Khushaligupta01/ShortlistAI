# UX Design Specification — ShortlistAI

## Visual Direction

**Style**: Clean, minimal, modern enterprise SaaS. No decorative elements — every UI component serves a function.

**Typography**: Single typeface (Inter or similar system sans-serif). Strong hierarchy via size and weight. Generous line height for data-dense views.

**Color palette**:
- Primary: Slate/neutral base (gray-50 backgrounds, gray-900 text)
- Accent: Indigo or blue (primary actions, focus states)
- Success: Emerald (matched status, placed stage)
- Warning: Amber (unknown status, low-confidence flags)
- Danger: Red (not_matched, rejected, failures)
- Neutral: Gray-400 (insufficient_evidence, pending)

**Spacing**: 4-point grid (Tailwind defaults). Consistent padding across cards and tables.

**Components**: shadcn/ui exclusively. No custom UI library or third-party component systems.

**Viewport**: Optimized for 1280px+ desktop. Minimum usable at 1024px. Mobile < 768px is out of scope for v1.

---

## Screen Inventory

### 1. Login Screen

**Purpose**: Authenticate users of all roles.

**Components**:
- Centered card layout (max-w-sm)
- Platform logo + "ShortlistAI" wordmark
- Email field
- Password field (show/hide toggle)
- Sign In button (primary, full-width)
- Forgot password link (out of scope for v1 — shows "Contact your administrator")

**States**:
- Default: Empty fields
- Loading: Button shows spinner, fields disabled
- Error: Red error banner below form — "Incorrect email or password" (uniform, no disclosure)
- Locked: "Account temporarily locked. Try again in X minutes."

---

### 2. Recruiter Dashboard

**Purpose**: Overview of all active requisitions and hiring pipeline at a glance.

**Components**:
- Top navigation bar: Logo, nav links (Requisitions, Upload, Pipeline), user avatar dropdown
- Stats row: 4 KPI cards (Active Requisitions, Total Candidates, Submissions Pending, Recent Activity)
- Requisition cards grid (2 or 3 columns): Title, candidate count, top score, pipeline stage summary, "View Candidates" CTA
- Recent activity feed (right panel): Last 10 audit events in plain English

**Actions**: Click requisition card → Requisition detail / candidate list

**Empty state**: "No active requisitions. Create your first requisition to get started." + Create Requisition button

**Loading state**: Skeleton cards matching the grid layout

**Error state**: "Could not load dashboard data. Refresh to try again." with retry button. Stale data shown if available.

---

### 3. Requisition Management

**Purpose**: Create, view, and manage all job requisitions.

**Components**:
- Page header: "Requisitions" + "New Requisition" button
- Search bar + status filter tabs (All / Active / Archived)
- Table: Title, Status badge, Candidate count, Created date, Actions (View, Edit, Archive)
- Create/Edit modal or inline form: Title field, JD textarea, "Save Draft" and "Extract Requirements" buttons

**Actions**: Create, edit, archive requisitions; trigger JD extraction

**Empty state**: "No requisitions yet. Click New Requisition to start."

**Loading state**: Table skeleton (5 rows)

**Error state**: Inline error below affected field on validation failure

---

### 4. JD Scorecard Editor

**Purpose**: Review and edit the AI-generated scorecard before activating.

**Components**:
- Section header showing requisition title
- "AI-generated" banner with explanation of the extraction source
- Criteria table: Type badge (experience / must-have / nice-to-have / location / notice period), Label, Weight input, Confidence indicator, Delete button
- "Add Criterion" button at bottom of table
- Weight summary: Live total display (e.g., "85 / 100 pts") — turns green at 100, red if over or under
- Per-field confidence display: small colored indicator (green ≥ 0.7, amber 0.4–0.69, red < 0.4)
- "Save Draft" and "Activate Scorecard" buttons

**States**:
- AI extraction in progress: Skeleton criteria rows with pulsing animation
- Extraction failed: "AI extraction failed. Fill in criteria manually." banner; form remains editable
- Weight sum ≠ 100 on activation attempt: Validation error, activation blocked

**Constraints**:
- Max 20 criteria per scorecard
- Weight per criterion: 1–97 pts
- Activated scorecard locks structural changes (add/delete blocked; tooltip explains why)

---

### 5. Bulk Resume Upload

**Purpose**: Upload large batches of resumes and monitor processing.

**Components**:
- Drop zone: Large dashed box "Drop PDF and DOCX files here, or click to browse". Visual feedback on hover (blue border + darker background). Inline label shows accepted formats and size limit.
- File status list: Scrollable table showing file name, status badge, actions
- Status badges: pending (gray), uploading (blue spinner), validating (blue), processing (amber spinner), parsed (green), failed (red), duplicate (purple)
- Batch progress bar + summary: "247 / 500 processed — 3 failed — 12 duplicates"
- "Download CSV Report" button (appears after all files complete)
- Duplicate resolution panel: Side-by-side comparison of existing vs. new profile; three action buttons (Update Existing, Keep Both, Discard New); "Pending" badge until resolved

**Hover behavior**: Failed file rows show tooltip with specific failure reason (e.g., "Could not extract text (< 50 words)", "Malware detected")

**Loading state**: Progress bar and counters update every ≤ 2 seconds

**Error state**: Red badge per failed file; batch can complete successfully with some failures

---

### 6. Ranked Candidate List

**Purpose**: Browse, search, and filter candidates for a requisition.

**Components**:
- Requisition context header: Title, active scorecard version, candidate count
- Filter bar: Score range slider, skill keyword input, location filter, notice period range, pipeline stage select, evidence status on criterion
- Sort controls: Default "Score ↓"; options include individual criterion scores
- Candidate table: Rank, Name, Total score badge (color-coded: ≥ 70 green, 40–69 amber, < 40 red), Top 3 criterion scores, Pipeline stage badge, "View Profile" button
- Shortlist checkbox: Inline on each row for batch shortlisting

**States**:
- All candidates displayed, regardless of score (no minimum threshold)
- Empty state after filtering: "No candidates match these filters." + Clear Filters link
- Loading state: 10-row table skeleton

**Filter persistence**: Filter state encoded in URL query string — survives navigation and tab refresh.

---

### 7. Candidate Evaluation and Evidence

**Purpose**: Deep-dive into one candidate's evaluation with full evidence transparency.

**Components**:
- Profile header: Name (with "Excluded from scoring" label on PA fields), total score badge, AI label
- Score breakdown chart: Horizontal bar chart per criterion category (awarded vs. max points)
- Evidence section — one row per criterion:
  - Criterion label
  - Status badge (matched / not_matched / unknown / insufficient_evidence)
  - Confidence score (e.g., 0.87 — with color indicator; placeholder shown if unavailable)
  - Awarded points / Max points
  - Source excerpt (truncated — click to expand full excerpt in context)
  - ⚠ low-confidence indicator (if confidence < 50%) with tooltip
  - ⚡ conflict indicator with tooltip
  - "AI-generated" label on each AI-extracted field
  - Override button (Recruiter only): opens modal with status select + mandatory reason field
- Resume panel: Original PDF text or extracted text in a scrollable panel alongside the structured profile
- Recruiter Notes section: Add/edit/view notes (max 500 chars each)
- Shortlist / Submit buttons in sticky footer

**Loading state**: Skeleton for each criterion row; profile header placeholder

**Error state**: If resume rendering fails — "Resume preview unavailable. View extracted text instead." with fallback

**Performance**: Page must render within 2 seconds of navigation

---

### 8. Client Shortlist Portal

**Purpose**: Client Hiring Manager reviews submitted candidates and takes action.

**Components**:
- Requisitions list (left panel or top tabs): Each requisition with submitted candidate count + pipeline summary
- Candidate cards: Name (masked contact), score, top evidence summary, current stage badge
- Action buttons per candidate: Shortlist (green), Request Interview (blue), Reject (red) — all three always visible
- Note modal (on reject or interview): Free text field, max 2000 chars, attribution shown
- Pipeline summary bar: Counts per stage for the selected requisition

**Contact masking**: Email, phone, and address fields display "—" (never null/blank, not missing)

**States**:
- Empty state: "No candidates have been submitted to your organization yet."
- Withdrawn candidate: Immediately removed from view (within 5 seconds of withdrawal)

---

### 9. Hiring Pipeline

**Purpose**: Recruiter view of all candidates in motion across all active requisitions.

**Components**:
- Pipeline board: Swimlane columns for each stage, with candidate cards
- Candidate card: Name, requisition title, days in current stage
- Stage transition controls: Click card to view detail; "Advance Stage" and "Revert Stage" buttons
- Reason note modal: Required for all reversions (mandatory text field)
- Placed stage: Locked indicator; "Re-open Placement" link

**Delivery Head view**: Same board, with additional analytics overlay — average time in each stage, conversion rate between stages

---

### 10. Delivery Head Analytics

**Purpose**: Aggregated performance and bias monitoring for the Delivery Head.

**Components**:
- Date range picker (default: last 90 days)
- KPI row: Active Requisitions, Candidates Uploaded, Total Submissions, Placement Rate, Avg Upload-to-Submission Days
- Filters: Recruiter, Requisition
- Pipeline funnel chart (bar chart fallback)
- Time-in-stage bar chart with above-average highlight
- Bias monitoring section: Per-requisition rank correlation table + alert badges for out-of-range correlations
- Each metric: value + plain-language explanation tooltip (≤ 50 words)

**Empty state**: "No data available for the selected period."

**Loading state**: Skeleton charts

---

### 11. Account and Privacy Controls

**Purpose**: User account management and data subject rights.

**Components**:
- Profile section: Display name field (edit inline), email (read-only), role badge
- Change password section: Current password, New password, Confirm fields
- Active sessions list: Device/browser, last seen, Revoke button
- Recent activity log: Last 30 days of actions by this user
- Privacy controls (Recruiter only): "Request Candidate Data Deletion" button → opens candidate search modal
- Admin controls (Delivery Head only): User list with Deactivate button per user

**States**:
- Password change confirmation: Green inline success message
- Session revocation: Immediate removal from list
- Deletion request submitted: "Request submitted. Anonymization will complete within 30 days."

---

## Accessibility Standards

All components use shadcn/ui primitives which include:
- ARIA roles on all interactive elements
- Keyboard navigation (Tab, Enter, Escape, Arrow keys)
- Focus ring visibility

Additional:
- Status badges use color + icon (not color alone) — WCAG 1.4.1
- AI-generated labels use `aria-label` for screen reader context
- Error messages are associated with their input via `aria-describedby`
- Minimum contrast ratio of 4.5:1 for normal text — WCAG 1.4.3

*Note: Full WCAG compliance requires manual testing with assistive technologies.*
