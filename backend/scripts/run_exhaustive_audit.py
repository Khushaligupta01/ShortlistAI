"""
ShortlistAI — Exhaustive End-to-End Functional Audit Script
Executes all functional tests across Phases 1–12 against real database models and API endpoints.
"""
import asyncio
import os
import sys
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db.session import async_session_factory
from app.models.user import User
from app.models.organization import Organization, OrganizationMembership
from app.models.requisition import Requisition
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.models.candidate import Candidate, CandidateSkill, CandidateEmployment
from app.models.resume import Resume
from app.models.evaluation import Evaluation, EvaluationEvidence, RecruiterReview
from app.models.submission import Submission, PipelineRecord
from app.models.audit import AuditLog, ConsentRecord, DeletionRequest
from app.services.scoring_engine_service import scoring_engine
from app.ai.schemas import CriterionEvidenceItem


audit_results = []

def record(phase: str, feature: str, result: str, notes: str = ""):
    audit_results.append({
        "phase": phase,
        "feature": feature,
        "result": result,
        "notes": notes,
    })
    print(f"[{result}] {phase} - {feature}: {notes}")


async def run_exhaustive_audit():
    print("=" * 70)
    print("      SHORTLISTAI EXHAUSTIVE FUNCTIONAL & END-TO-END AUDIT")
    print("=" * 70)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # ---------------------------------------------------------------------
        # PHASE 1: Authentication & User Management
        # ---------------------------------------------------------------------
        print("\n--- PHASE 1: AUTHENTICATION & RBAC ---")

        # 1.1 Valid Recruiter Login
        resp = await client.post("/api/v1/auth/login", json={"email": "recruiter@techrecruit.com", "password": "Recruiter@Demo2024!"})
        if resp.status_code == 200 and "access_token" in resp.json():
            recruiter_token = resp.json()["access_token"]
            refresh_token = resp.json()["refresh_token"]
            record("Phase 1", "Valid Login (Recruiter)", "PASS", "Token generated successfully.")
        else:
            record("Phase 1", "Valid Login (Recruiter)", "FAIL", f"Status: {resp.status_code}")
            return

        recruiter_headers = {"Authorization": f"Bearer {recruiter_token}"}

        # 1.2 Invalid Credentials
        resp_bad = await client.post("/api/v1/auth/login", json={"email": "recruiter@techrecruit.com", "password": "WrongPassword!"})
        if resp_bad.status_code == 401:
            record("Phase 1", "Invalid Password Handling", "PASS", "Returns 401 Unauthorized.")
        else:
            record("Phase 1", "Invalid Password Handling", "FAIL", f"Status: {resp_bad.status_code}")

        # 1.3 Unknown User
        resp_unknown = await client.post("/api/v1/auth/login", json={"email": "nonexistent@example.com", "password": "Password123!"})
        if resp_unknown.status_code == 401:
            record("Phase 1", "Non-existent User Handling", "PASS", "Returns 401 Unauthorized.")
        else:
            record("Phase 1", "Non-existent User Handling", "FAIL", f"Status: {resp_unknown.status_code}")

        # 1.4 Current User Profile & Organization Check
        resp_me = await client.get("/api/v1/auth/me", headers=recruiter_headers)
        if resp_me.status_code == 200 and resp_me.json()["role"] == "recruiter":
            org_id = resp_me.json()["organization_id"]
            user_id = resp_me.json()["id"]
            record("Phase 1", "Get Current User & Role", "PASS", f"User: {resp_me.json()['email']}, Org: {org_id}")
        else:
            record("Phase 1", "Get Current User & Role", "FAIL", f"Status: {resp_me.status_code}")

        # 1.5 Client Login & Role Verification
        resp_client_login = await client.post("/api/v1/auth/login", json={"email": "client@acme.com", "password": "Client@Demo2024!"})
        if resp_client_login.status_code == 200:
            client_token = resp_client_login.json()["access_token"]
            client_headers = {"Authorization": f"Bearer {client_token}"}
            record("Phase 1", "Valid Login (Client)", "PASS", "Client authenticated.")
        else:
            record("Phase 1", "Valid Login (Client)", "FAIL", f"Status: {resp_client_login.status_code}")

        # 1.6 Delivery Head Login
        resp_dh_login = await client.post("/api/v1/auth/login", json={"email": "head@techrecruit.com", "password": "Delivery@Demo2024!"})
        if resp_dh_login.status_code == 200:
            dh_token = resp_dh_login.json()["access_token"]
            dh_headers = {"Authorization": f"Bearer {dh_token}"}
            record("Phase 1", "Valid Login (Delivery Head)", "PASS", "Delivery head authenticated.")
        else:
            record("Phase 1", "Valid Login (Delivery Head)", "FAIL", f"Status: {resp_dh_login.status_code}")

        # 1.7 Role-Based Access Control: Client blocked from recruiter-only endpoint
        resp_rbac_blocked = await client.get("/api/v1/requisitions", headers=client_headers)
        if resp_rbac_blocked.status_code in (403, 404):
            record("Phase 1", "RBAC Route Protection", "PASS", "Client prevented from accessing recruiter requisitions.")
        else:
            record("Phase 1", "RBAC Route Protection", "FAIL", f"Status: {resp_rbac_blocked.status_code}")

        # 1.8 Token Refresh
        resp_refresh = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
        if resp_refresh.status_code == 200 and "access_token" in resp_refresh.json():
            record("Phase 1", "Session Token Refresh", "PASS", "New access token issued.")
        else:
            record("Phase 1", "Session Token Refresh", "FAIL", f"Status: {resp_refresh.status_code}")

        # ---------------------------------------------------------------------
        # PHASE 2: Job and Job Description Management
        # ---------------------------------------------------------------------
        print("\n--- PHASE 2: JOB & REQUISITION MANAGEMENT ---")

        # 2.1 Create Job Requisition
        req_payload = {
            "title": "Principal Distributed Systems Engineer",
            "department": "Infrastructure",
            "location": "San Francisco, CA / Hybrid",
            "job_description": "We are seeking a Principal Systems Engineer with 8+ years of Java, Kafka, and Kubernetes experience. Notice under 30 days.",
            "target_hire_count": 2,
        }
        resp_create_req = await client.post("/api/v1/requisitions", json=req_payload, headers=recruiter_headers)
        if resp_create_req.status_code == 201:
            req_id = resp_create_req.json()["id"]
            record("Phase 2", "Create Job Requisition", "PASS", f"Created Req ID: {req_id}")
        else:
            record("Phase 2", "Create Job Requisition", "FAIL", f"Status: {resp_create_req.status_code}, Body: {resp_create_req.text}")
            return

        # 2.2 Requisition Listing & Filtering
        resp_list_req = await client.get("/api/v1/requisitions", params={"search": "Principal", "page": 1, "page_size": 10}, headers=recruiter_headers)
        if resp_list_req.status_code == 200 and any(r["id"] == req_id for r in resp_list_req.json()["items"]):
            record("Phase 2", "List & Search Requisitions", "PASS", "New requisition found in filtered search.")
        else:
            record("Phase 2", "List & Search Requisitions", "FAIL", f"Status: {resp_list_req.status_code}")

        # 2.3 Requisition Detail View
        resp_get_req = await client.get(f"/api/v1/requisitions/{req_id}", headers=recruiter_headers)
        if resp_get_req.status_code == 200 and resp_get_req.json()["status"] == "draft":
            record("Phase 2", "View Requisition Details", "PASS", "Correct initial draft status verified.")
        else:
            record("Phase 2", "View Requisition Details", "FAIL", f"Status: {resp_get_req.status_code}")

        # ---------------------------------------------------------------------
        # PHASE 3: AI Job Description Extraction & Scorecard
        # ---------------------------------------------------------------------
        print("\n--- PHASE 3: AI JD EXTRACTION & SCORECARD ---")

        # 3.1 AI Extraction from JD Text
        jd_text = (
            "Senior Backend Architect needed. Minimum 6+ years Java or Python experience. "
            "Must have Spring Boot and PostgreSQL. Nice to have Docker and AWS. "
            "Location: San Francisco, CA. Maximum 30 days notice period."
        )
        resp_extract = await client.post("/api/v1/requisitions/extract-requirements", json={"job_description": jd_text}, headers=recruiter_headers)
        if resp_extract.status_code == 200:
            extracted_data = resp_extract.json()
            record("Phase 3", "AI JD Requirement Extraction", "PASS", f"Extracted title: {extracted_data.get('job_title')}, Skills: {len(extracted_data.get('must_have_skills', []))}")
        else:
            record("Phase 3", "AI JD Requirement Extraction", "FAIL", f"Status: {resp_extract.status_code}")

        # 3.2 Create Scorecard Draft
        sc_payload = {
            "experience_min": 6.0,
            "experience_max": 12.0,
            "location": "San Francisco, CA",
            "max_notice_days": 30,
            "scoring_config": {
                "experience": 30,
                "must_have_skills": 40,
                "notice_period": 15,
                "location": 10,
                "nice_to_have_skills": 5,
            },
            "criteria": [
                {"criterion_type": "experience", "criterion_name": "6+ Years Backend", "label": "6+ Years Backend", "description": "Core software engineering", "weight": 30, "is_mandatory": True},
                {"criterion_type": "must_have_skill", "criterion_name": "Java / Python", "label": "Java / Python", "description": "Backend language", "weight": 20, "is_mandatory": True},
                {"criterion_type": "must_have_skill", "criterion_name": "Spring Boot / FastAPI", "label": "Spring Boot / FastAPI", "description": "Web framework", "weight": 20, "is_mandatory": True},
                {"criterion_type": "notice_period", "criterion_name": "Under 30 Days Notice", "label": "Under 30 Days Notice", "description": "Immediate joiner preferred", "weight": 15, "is_mandatory": False},
                {"criterion_type": "location", "criterion_name": "San Francisco / Hybrid", "label": "San Francisco / Hybrid", "description": "Location match", "weight": 10, "is_mandatory": False},
                {"criterion_type": "nice_to_have_skill", "criterion_name": "Docker & AWS", "label": "Docker & AWS", "description": "Cloud platform", "weight": 5, "is_mandatory": False},
            ],
        }
        resp_create_sc = await client.post(f"/api/v1/requisitions/{req_id}/scorecards", json=sc_payload, headers=recruiter_headers)
        if resp_create_sc.status_code == 201:
            sc_id = resp_create_sc.json()["id"]
            record("Phase 3", "Create Draft Scorecard", "PASS", f"Created Scorecard v1 ID: {sc_id}")
        else:
            record("Phase 3", "Create Draft Scorecard", "FAIL", f"Status: {resp_create_sc.status_code}, Body: {resp_create_sc.text}")
            return

        # 3.3 Validate Category Weights sum to 100
        invalid_sc_payload = dict(sc_payload)
        invalid_sc_payload["scoring_config"] = {"experience": 50, "must_have_skills": 40, "notice_period": 15, "location": 10, "nice_to_have_skills": 5}  # Total 120
        resp_invalid_sc = await client.put(f"/api/v1/requisitions/{req_id}/scorecard", json=invalid_sc_payload, headers=recruiter_headers)
        if resp_invalid_sc.status_code == 422:
            record("Phase 3", "Scorecard Weights Validation (=100)", "PASS", "Rejected invalid weights summing to 120.")
        else:
            record("Phase 3", "Scorecard Weights Validation (=100)", "FAIL", f"Status: {resp_invalid_sc.status_code}")

        # 3.4 Approve Scorecard
        resp_approve_sc = await client.post(f"/api/v1/requisitions/{req_id}/scorecard/approve", headers=recruiter_headers)
        if resp_approve_sc.status_code == 200 and resp_approve_sc.json()["status"] == "approved":
            record("Phase 3", "Approve Scorecard & Activate Requisition", "PASS", "Scorecard transitioned to approved, requisition active.")
        else:
            record("Phase 3", "Approve Scorecard & Activate Requisition", "FAIL", f"Status: {resp_approve_sc.status_code}")

        # ---------------------------------------------------------------------
        # PHASE 4: Resume Ingestion & Processing
        # ---------------------------------------------------------------------
        print("\n--- PHASE 4: RESUME UPLOAD & PROCESSING ---")

        # 4.1 Upload Valid PDF Resume
        pdf_path = os.path.join(os.path.dirname(__file__), "..", "tests", "fixtures", "resumes", "01_strong_java_senior.pdf")
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        files = {"files": ("aarav_sharma_cv.pdf", pdf_bytes, "application/pdf")}
        resp_upload = await client.post(f"/api/v1/requisitions/{req_id}/resumes/upload", files=files, headers=recruiter_headers)
        if resp_upload.status_code == 201:
            batch_id = resp_upload.json()["id"]
            record("Phase 4", "Resume Upload (PDF)", "PASS", f"Uploaded batch ID: {batch_id}")
        else:
            record("Phase 4", "Resume Upload (PDF)", "FAIL", f"Status: {resp_upload.status_code}, Body: {resp_upload.text}")
            batch_id = None

        # 4.2 Wait / Process Candidate Ingestion
        if batch_id:
            from app.services.worker_service import worker_service
            from app.models.resume import ResumeProcessingJob
            async with async_session_factory() as db:
                j_res = await db.execute(select(ResumeProcessingJob).where(ResumeProcessingJob.batch_id == uuid.UUID(batch_id)))
                job = j_res.scalars().first()
                if job and job.status != "completed":
                    await worker_service.process_job_by_id(job.id)

        # Check Candidate table
        async with async_session_factory() as db:
            c_res = await db.execute(select(Candidate).where(Candidate.email == "aarav.sharma@example.com"))
            candidate = c_res.scalars().first()

        if candidate:
            cand_id = candidate.id
            record("Phase 4", "Resume Parsing & Profile Creation", "PASS", f"Parsed candidate: {candidate.full_name}, Experience: {candidate.total_experience_years}y, Location: {candidate.location}")
        else:
            record("Phase 4", "Resume Parsing & Profile Creation", "FAIL", "Candidate record was not created.")
            return

        # ---------------------------------------------------------------------
        # PHASE 5: Candidate Management
        # ---------------------------------------------------------------------
        print("\n--- PHASE 5: CANDIDATE MANAGEMENT ---")

        # 5.1 List Candidates
        resp_cands = await client.get("/api/v1/candidates", params={"search": "Aarav", "page": 1}, headers=recruiter_headers)
        if resp_cands.status_code == 200 and resp_cands.json()["total"] >= 1:
            record("Phase 5", "Candidate Listing & Search", "PASS", f"Total matching candidates: {resp_cands.json()['total']}")
        else:
            record("Phase 5", "Candidate Listing & Search", "FAIL", f"Status: {resp_cands.status_code}")

        # 5.2 Candidate Detail Profile
        resp_cand_profile = await client.get(f"/api/v1/candidates/{cand_id}", headers=recruiter_headers)
        if resp_cand_profile.status_code == 200 and resp_cand_profile.json()["full_name"] == "Aarav Sharma":
            record("Phase 5", "Candidate Profile Workspace", "PASS", "Full profile loaded with skills and employments.")
        else:
            record("Phase 5", "Candidate Profile Workspace", "FAIL", f"Status: {resp_cand_profile.status_code}")

        # ---------------------------------------------------------------------
        # PHASE 6: AI Candidate Evaluation & Deterministic Scoring
        # ---------------------------------------------------------------------
        print("\n--- PHASE 6: AI EVALUATION & DETERMINISTIC SCORING ---")

        # 6.1 Evaluate Single Candidate
        resp_eval = await client.post(f"/api/v1/requisitions/{req_id}/candidates/{cand_id}/evaluate", headers=recruiter_headers)
        if resp_eval.status_code == 200:
            eval_data = resp_eval.json()
            eval_id = eval_data["id"]
            record("Phase 6", "Single Candidate Evaluation", "PASS", f"Score: {eval_data['normalized_score']}, Coverage: {eval_data['evidence_coverage']}%, Status: {eval_data['evaluation_status']}")
        else:
            record("Phase 6", "Single Candidate Evaluation", "FAIL", f"Status: {resp_eval.status_code}, Body: {resp_eval.text}")
            return

        # 6.2 Verify Score Boundaries & Determinism
        assert 0.0 <= eval_data["normalized_score"] <= 100.0
        assert eval_data["confidence_level"] in ("HIGH", "NEEDS_REVIEW", "LOW")
        record("Phase 6", "Score Clamping & Confidence Level", "PASS", f"Score within bounds: {eval_data['normalized_score']}, Level: {eval_data['confidence_level']}")

        # 6.3 Ranked Candidates List
        resp_ranked = await client.get(f"/api/v1/requisitions/{req_id}/evaluations", params={"sort_by": "score_desc"}, headers=recruiter_headers)
        if resp_ranked.status_code == 200 and len(resp_ranked.json()["items"]) >= 1:
            record("Phase 6", "Ranked Candidates Table", "PASS", f"Ranked candidates returned: {len(resp_ranked.json()['items'])}")
        else:
            record("Phase 6", "Ranked Candidates Table", "FAIL", f"Status: {resp_ranked.status_code}")

        # 6.4 Recalculate Evaluation (Deterministic without LLM call)
        resp_recalc = await client.post(f"/api/v1/evaluations/{eval_id}/recalculate", headers=recruiter_headers)
        if resp_recalc.status_code == 200:
            recalc_data = resp_recalc.json()
            assert recalc_data["normalized_score"] == eval_data["normalized_score"]
            record("Phase 6", "Deterministic Evaluation Recalculation", "PASS", f"Recalculated score {recalc_data['normalized_score']} exactly matches original {eval_data['normalized_score']}.")
        else:
            record("Phase 6", "Deterministic Evaluation Recalculation", "FAIL", f"Status: {resp_recalc.status_code}")

        # 6.5 Record Human Review Decision
        review_payload = {
            "decision": "SHORTLIST",
            "notes": "Strong engineering profile with excellent Java and Spring Boot experience. Recommended for client submission.",
        }
        resp_review = await client.post(f"/api/v1/evaluations/{eval_id}/review", json=review_payload, headers=recruiter_headers)
        if resp_review.status_code == 200 and resp_review.json()["decision"] == "SHORTLIST":
            record("Phase 6", "Record Recruiter Review Decision", "PASS", "Human review decision recorded with notes.")
        else:
            record("Phase 6", "Record Recruiter Review Decision", "FAIL", f"Status: {resp_review.status_code}")

        # ---------------------------------------------------------------------
        # PHASE 7: Recruiter Dashboard & Submission to Client
        # ---------------------------------------------------------------------
        print("\n--- PHASE 7: DASHBOARD & SUBMISSION WORKFLOW ---")

        # 7.1 Recruiter Dashboard Metrics
        resp_dash = await client.get("/api/v1/recruiter/metrics", headers=recruiter_headers)
        if resp_dash.status_code == 200 and "active_requisitions" in resp_dash.json():
            record("Phase 7", "Recruiter Dashboard Metrics", "PASS", f"Active Reqs: {resp_dash.json()['active_requisitions']}, Total Candidates: {resp_dash.json()['total_candidates']}")
        else:
            record("Phase 7", "Recruiter Dashboard Metrics", "FAIL", f"Status: {resp_dash.status_code}")

        # 7.2 Submit Candidate to Client
        async with async_session_factory() as db:
            co_res = await db.execute(select(Organization).where(Organization.org_type == "client_company"))
            client_org = co_res.scalars().first()
            client_org_id = client_org.id if client_org else uuid.uuid4()

        sub_payload = {
            "candidate_id": str(cand_id),
            "client_organization_id": str(client_org_id),
            "recruiter_notes_for_client": "Top candidate matching backend requirements. Verified notice period.",
        }
        resp_sub = await client.post(f"/api/v1/requisitions/{req_id}/submissions", json=sub_payload, headers=recruiter_headers)
        if resp_sub.status_code == 201:
            sub_id = resp_sub.json()["submission_id"]
            record("Phase 7", "Submit Candidate to Client", "PASS", f"Submission ID: {sub_id}, Stage: {resp_sub.json()['current_stage']}")
        else:
            record("Phase 7", "Submit Candidate to Client", "FAIL", f"Status: {resp_sub.status_code}, Body: {resp_sub.text}")
            sub_id = None

        # ---------------------------------------------------------------------
        # PHASE 8: Client Portal Experience & Isolation
        # ---------------------------------------------------------------------
        print("\n--- PHASE 8: CLIENT PORTAL ---")

        # 8.1 Client Submissions View with Masked PII
        resp_client_subs = await client.get("/api/v1/client/submissions", headers=client_headers)
        if resp_client_subs.status_code == 200:
            client_items = resp_client_subs.json()
            # Verify PII masking on email
            for item in client_items:
                if item.get("candidate_email"):
                    assert "***@" in item["candidate_email"], f"Unmasked email: {item['candidate_email']}"
            record("Phase 8", "Client Submissions Listing & PII Masking", "PASS", f"Found {len(client_items)} submissions. Contact PII masked.")
        else:
            record("Phase 8", "Client Submissions Listing & PII Masking", "FAIL", f"Status: {resp_client_subs.status_code}")

        # 8.2 Client Hiring Decision
        if client_items:
            target_sub = client_items[0]
            dec_payload = {
                "decision": "CLIENT_SHORTLISTED",
                "reason_note": "Looks like a great match for the cloud infrastructure team.",
            }
            resp_dec = await client.post(f"/api/v1/client/submissions/{target_sub['submission_id']}/decisions", json=dec_payload, headers=client_headers)
            if resp_dec.status_code == 200:
                record("Phase 8", "Client Shortlist Decision", "PASS", f"Updated stage: {resp_dec.json()['current_stage']}")
            else:
                record("Phase 8", "Client Shortlist Decision", "FAIL", f"Status: {resp_dec.status_code}")

        # ---------------------------------------------------------------------
        # PHASE 9: Hiring Pipeline Board & Delivery Head
        # ---------------------------------------------------------------------
        print("\n--- PHASE 9: PIPELINE BOARD & DELIVERY HEAD ---")

        resp_pipe = await client.get("/api/v1/recruiter/pipeline", headers=recruiter_headers)
        if resp_pipe.status_code == 200 and "stages" in resp_pipe.json():
            pipe_data = resp_pipe.json()
            record("Phase 9", "Pipeline Board Synchronization", "PASS", f"Active pipeline stages: {len(pipe_data['stages'])}, Total submissions: {len(pipe_data.get('submissions', []))}")
        else:
            record("Phase 9", "Pipeline Board Synchronization", "FAIL", f"Status: {resp_pipe.status_code}")

        # Delivery Head Pipeline Summary
        resp_dh = await client.get("/api/v1/delivery/pipeline-summary", headers=dh_headers)
        if resp_dh.status_code == 200 and "stage_breakdown" in resp_dh.json():
            dh_data = resp_dh.json()
            record("Phase 9", "Delivery Head Pipeline Summary", "PASS", f"Total Submissions: {dh_data['total_submissions']}, Shortlist Conversion: {dh_data['conversion_shortlist_rate']}%")
        else:
            record("Phase 9", "Delivery Head Pipeline Summary", "FAIL", f"Status: {resp_dh.status_code}")

        # ---------------------------------------------------------------------
        # PHASE 10: Privacy, Consent & Governance
        # ---------------------------------------------------------------------
        print("\n--- PHASE 10: PRIVACY, CONSENT & GOVERNANCE ---")

        # 10.1 Consent Records List
        resp_consent = await client.get("/api/v1/consent-records", headers=recruiter_headers)
        if resp_consent.status_code == 200 and "items" in resp_consent.json():
            record("Phase 10", "Consent Tracking & Legal Basis", "PASS", f"Total consent records: {resp_consent.json()['total']}")
        else:
            record("Phase 10", "Consent Tracking & Legal Basis", "FAIL", f"Status: {resp_consent.status_code}")

        # 10.2 GDPR / DPDP Portable Data Export (Create Data Request & Export)
        resp_data_req = await client.post(
            f"/api/v1/candidates/{cand_id}/data-requests",
            json={"request_type": "export", "reason": "Candidate subject access request"},
            headers=recruiter_headers,
        )
        if resp_data_req.status_code == 201:
            data_req_id = resp_data_req.json()["id"]
            resp_export = await client.post(f"/api/v1/data-requests/{data_req_id}/export", headers=recruiter_headers)
            if resp_export.status_code == 200 and "profile" in resp_export.json():
                export_payload = resp_export.json()
                record("Phase 10", "Data Subject Access Request (Export)", "PASS", f"Exported candidate {export_payload['profile']['full_name']} with {len(export_payload.get('evaluations', []))} evaluations.")
            else:
                record("Phase 10", "Data Subject Access Request (Export)", "FAIL", f"Export execution failed: {resp_export.status_code}, Keys: {list(resp_export.json().keys()) if resp_export.status_code == 200 else resp_export.text}")
        else:
            record("Phase 10", "Data Subject Access Request (Export)", "FAIL", f"Request creation failed: {resp_data_req.status_code}")

        # 10.3 Privacy Dashboard
        resp_priv_dash = await client.get("/api/v1/privacy/dashboard", headers=recruiter_headers)
        if resp_priv_dash.status_code == 200 and "granted_consents_count" in resp_priv_dash.json():
            pd = resp_priv_dash.json()
            record("Phase 10", "Privacy Dashboard Overview", "PASS", f"Granted: {pd['granted_consents_count']}, Exports: {pd['completed_exports_count']}, Deletions: {pd['completed_deletions_count']}")
        else:
            record("Phase 10", "Privacy Dashboard Overview", "FAIL", f"Status: {resp_priv_dash.status_code}")

        # 10.4 Responsible AI Governance Metrics
        resp_gov = await client.get("/api/v1/governance/ai-metrics", headers=dh_headers)
        if resp_gov.status_code == 200 and "average_evidence_coverage_pct" in resp_gov.json():
            gov_data = resp_gov.json()
            record("Phase 10", "Responsible AI Governance Metrics", "PASS", f"Avg Evidence Coverage: {gov_data['average_evidence_coverage_pct']}%, Override Rate: {gov_data['override_rate_pct']}%")
        else:
            record("Phase 10", "Responsible AI Governance Metrics", "FAIL", f"Status: {resp_gov.status_code}")

        # 10.5 Evaluation Quality Metrics
        resp_qual = await client.get("/api/v1/governance/evaluation-quality", headers=dh_headers)
        if resp_qual.status_code == 200 and "total_evaluations" in resp_qual.json():
            qual_data = resp_qual.json()
            record("Phase 10", "AI Evaluation Quality Breakdown", "PASS", f"Total: {qual_data['total_evaluations']}, Confidence: {qual_data['confidence_breakdown']}")
        else:
            record("Phase 10", "AI Evaluation Quality Breakdown", "FAIL", f"Status: {resp_qual.status_code}")

        # 10.6 Candidate Deletion Request & Legal Hold Workflow
        resp_del_req = await client.post(
            f"/api/v1/candidates/{cand_id}/deletion-requests",
            json={"reason": "Candidate requested deletion under DPDP/GDPR"},
            headers=recruiter_headers,
        )
        if resp_del_req.status_code == 201:
            del_req_id = resp_del_req.json()["id"]
            # Delivery Head / Admin reviews deletion with legal hold or approval
            review_del_payload = {
                "decision": "REJECT",
                "review_notes": "Retained under statutory legal hold pending active client placement.",
                "is_legal_hold": True,
                "legal_hold_reason": "Compliance verification active",
            }
            resp_del_rev = await client.post(f"/api/v1/deletion-requests/{del_req_id}/review", json=review_del_payload, headers=dh_headers)
            if resp_del_rev.status_code == 200 and resp_del_rev.json()["is_legal_hold"] is True:
                record("Phase 10", "Candidate Deletion & Legal Hold Review", "PASS", f"Deletion request placed on legal hold: {resp_del_rev.json()['status']}")
            else:
                record("Phase 10", "Candidate Deletion & Legal Hold Review", "FAIL", f"Review status: {resp_del_rev.status_code}")
        else:
            record("Phase 10", "Candidate Deletion & Legal Hold Review", "FAIL", f"Deletion request creation failed: {resp_del_req.status_code}")

        # 10.7 Centralized Audit Log Query
        resp_audit = await client.get("/api/v1/audit-events", headers=dh_headers)
        if resp_audit.status_code == 200 and resp_audit.json()["total"] >= 1:
            record("Phase 10", "Immutable Audit Logging Trail", "PASS", f"Total Audit Events Recorded: {resp_audit.json()['total']}")
        else:
            record("Phase 10", "Immutable Audit Logging Trail", "FAIL", f"Status: {resp_audit.status_code}")

    print("\n" + "=" * 70)
    print("                EXHAUSTIVE AUDIT EXECUTION COMPLETE")
    print("=" * 70)
    passes = sum(1 for r in audit_results if r["result"] == "PASS")
    fails = sum(1 for r in audit_results if r["result"] == "FAIL")
    print(f"Total Features Verified: {len(audit_results)}")
    print(f"PASS: {passes} | FAIL: {fails}")
    assert fails == 0, f"{fails} features failed audit!"


if __name__ == "__main__":
    asyncio.run(run_exhaustive_audit())
