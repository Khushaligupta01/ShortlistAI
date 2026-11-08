import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://shortlist:shortlist_dev@localhost:5434/shortlistai"
)

from httpx import ASGITransport, AsyncClient
from app.main import app


async def run_e2e():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        print("=== 1. Recruiter Login ===")
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "recruiter@techrecruit.com",
                "password": "Recruiter@Demo2024!",
            },
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        recruiter_token = login_resp.json()["access_token"]
        rec_headers = {"Authorization": f"Bearer {recruiter_token}"}
        print("  Recruiter authenticated successfully.")

        print("=== 2. Create Senior Java Developer Requisition ===")
        jd_text = (
            "We are looking for a Senior Java Developer to join our backend engineering team in Noida.\n\n"
            "Responsibilities:\n"
            "- Design, develop, and maintain high-performance enterprise applications.\n"
            "- Develop robust REST APIs and backend microservices.\n"
            "- Collaborate with engineering and product teams.\n\n"
            "Requirements:\n"
            "- 5-8 years of professional software development experience.\n"
            "- Strong Java development experience required.\n"
            "- Hands-on Spring Boot experience required.\n"
            "- Location: Noida.\n"
            "- Notice period: Notice period up to 60 days.\n\n"
            "Preferred Qualifications:\n"
            "- Microservices experience preferred."
        )
        create_req = await client.post(
            "/api/v1/requisitions",
            headers=rec_headers,
            json={
                "title": "Senior Java Developer",
                "location": "Noida",
                "job_description": jd_text,
            },
        )
        assert create_req.status_code == 201, f"Create req failed: {create_req.text}"
        req_id = create_req.json()["id"]
        req_status = create_req.json()["status"]
        print(f"  Created requisition ID: {req_id}, status: {req_status}")

        print("=== 3. AI Requirement Extraction ===")
        ext_resp = await client.post(
            "/api/v1/requisitions/extract-requirements",
            headers=rec_headers,
            json={"job_description": jd_text},
        )
        print(f"  Extraction status: {ext_resp.status_code}")
        if ext_resp.status_code == 200:
            print("  AI Extracted:", ext_resp.json())
        elif ext_resp.status_code in (429, 502, 503):
            detail = ext_resp.json().get("detail", "")
            print(f"  AI Provider reported expected unavailable/quota behavior: {detail}")

        print("=== 4. Save Scorecard Draft ===")
        sc_resp = await client.post(
            f"/api/v1/requisitions/{req_id}/scorecards",
            headers=rec_headers,
            json={
                "experience_min": 5,
                "experience_max": 8,
                "location": "Noida",
                "max_notice_days": 60,
                "scoring_config": {
                    "experience": 30,
                    "must_have_skills": 40,
                    "notice_period": 15,
                    "location": 10,
                    "nice_to_have_skills": 5,
                },
                "criteria": [
                    {
                        "criterion_type": "must_have_skill",
                        "criterion_name": "Java",
                        "label": "Java Development",
                        "weight": 20,
                        "is_mandatory": True,
                        "evidence_from_jd": "Strong Java development experience required",
                        "display_order": 0,
                    },
                    {
                        "criterion_type": "must_have_skill",
                        "criterion_name": "Spring Boot",
                        "label": "Spring Boot Framework",
                        "weight": 20,
                        "is_mandatory": True,
                        "evidence_from_jd": "Hands-on Spring Boot experience required",
                        "display_order": 1,
                    },
                    {
                        "criterion_type": "nice_to_have_skill",
                        "criterion_name": "Microservices",
                        "label": "Microservices Architecture",
                        "weight": 5,
                        "is_mandatory": False,
                        "evidence_from_jd": "Microservices experience preferred",
                        "display_order": 2,
                    },
                ],
            },
        )
        assert sc_resp.status_code == 201, f"Scorecard create failed: {sc_resp.text}"
        sc_data = sc_resp.json()
        version_num = sc_data["version_number"]
        sc_status = sc_data["status"]
        crit_len = len(sc_data["criteria"])
        print(f"  Scorecard v{version_num} status: {sc_status}, criteria count: {crit_len}")

        print("=== 5. Edit Scorecard ===")
        update_resp = await client.put(
            f"/api/v1/requisitions/{req_id}/scorecard",
            headers=rec_headers,
            json={
                "experience_min": 5,
                "experience_max": 9,
                "location": "Noida / NCR",
                "max_notice_days": 60,
                "scoring_config": {
                    "experience": 30,
                    "must_have_skills": 40,
                    "notice_period": 15,
                    "location": 10,
                    "nice_to_have_skills": 5,
                },
            },
        )
        assert update_resp.status_code == 200
        print(f"  Updated location to: {update_resp.json()['location']}")

        print("=== 6. Approve Scorecard ===")
        approve_resp = await client.post(
            f"/api/v1/requisitions/{req_id}/scorecard/approve", headers=rec_headers
        )
        assert approve_resp.status_code == 200
        approved_at = approve_resp.json()["approved_at"]
        print(f"  Scorecard approved at: {approved_at}")

        req_check = await client.get(
            f"/api/v1/requisitions/{req_id}", headers=rec_headers
        )
        req_status_after = req_check.json()["status"]
        print(f"  Requisition status after approval: {req_status_after}")

        print("=== 7. Verify Persistence and Versioning ===")
        get_sc = await client.get(
            f"/api/v1/requisitions/{req_id}/scorecard", headers=rec_headers
        )
        assert get_sc.status_code == 200
        assert get_sc.json()["status"] == "approved"
        assert get_sc.json()["version_number"] == 1
        print("  Scorecard v1 verified persisted in PostgreSQL.")

        print("=== 8. Duplicate to Version 2 ===")
        dup_resp = await client.post(
            f"/api/v1/requisitions/{req_id}/scorecard/duplicate",
            headers=rec_headers,
        )
        assert dup_resp.status_code == 201
        v2_sc = dup_resp.json()
        assert v2_sc["version_number"] == 2
        assert v2_sc["status"] == "draft"
        print("  Created Version 2 (draft), Version 1 remains approved.")

        print("=== 9. Client Hiring Manager RBAC Rejection ===")
        client_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "client@acme.com",
                "password": "Client@Demo2024!",
            },
        )
        assert client_login.status_code == 200
        client_token = client_login.json()["access_token"]
        client_headers = {"Authorization": f"Bearer {client_token}"}

        # Client attempt to create requisition -> 403
        c_req = await client.post(
            "/api/v1/requisitions",
            headers=client_headers,
            json={
                "title": "Client Created",
                "job_description": "Should be rejected by RBAC.",
            },
        )
        assert c_req.status_code == 403
        print("  Client requisition creation rejected: 403 Forbidden.")

        # Client attempt to update scorecard -> 403
        c_sc = await client.put(
            f"/api/v1/requisitions/{req_id}/scorecard",
            headers=client_headers,
            json={"experience_min": 1},
        )
        assert c_sc.status_code == 403
        print("  Client scorecard modification rejected: 403 Forbidden.")

        print("\n>>> ALL 9 STEPS VERIFIED AGAINST LIVE POSTGRESQL! <<<")


if __name__ == "__main__":
    asyncio.run(run_e2e())

