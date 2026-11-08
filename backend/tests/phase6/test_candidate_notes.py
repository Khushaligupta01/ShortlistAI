from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.requisition import Requisition
from tests.conftest import auth_headers, create_membership, create_test_user, seed_user_with_org


@pytest.mark.asyncio
async def test_candidate_note_crud(client: AsyncClient, db_session: AsyncSession):
    recruiter, org = await seed_user_with_org(
        db_session, email="notes_recruiter@example.com", password="Password123!", role="recruiter"
    )
    headers = auth_headers(recruiter.id, "recruiter", org.id)

    cand = Candidate(
        id=uuid.uuid4(),
        organization_id=org.id,
        full_name="Candidate Under Evaluation",
        email="eval@example.com",
    )
    req = Requisition(
        id=uuid.uuid4(),
        organization_id=org.id,
        created_by=recruiter.id,
        title="Role for Note",
        job_description="JD text",
        status="active",
    )
    db_session.add_all([cand, req])
    await db_session.commit()

    # 1. Create note
    payload = {
        "content": "Candidate has excellent domain knowledge but demands high compensation.",
        "requisition_id": str(req.id),
    }
    create_res = await client.post(
        f"/api/v1/candidates/{cand.id}/notes",
        json=payload,
        headers=headers,
    )
    assert create_res.status_code == 201
    created_note = create_res.json()
    assert created_note["candidate_id"] == str(cand.id)
    assert created_note["content"] == payload["content"]
    assert created_note["requisition_id"] == str(req.id)
    assert created_note["requisition_title"] == "Role for Note"
    assert created_note["is_author"] is True
    note_id = created_note["id"]

    # 2. List notes
    list_res = await client.get(f"/api/v1/candidates/{cand.id}/notes", headers=headers)
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] == 1
    assert list_data["notes"][0]["id"] == note_id

    # 3. Update note
    update_res = await client.put(
        f"/api/v1/candidates/notes/{note_id}",
        json={"content": "Updated: Candidate agreed to standard compensation band."},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert "agreed to standard compensation" in update_res.json()["content"]

    # 4. Delete note
    del_res = await client.delete(f"/api/v1/candidates/notes/{note_id}", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["ok"] is True

    # Confirm deletion
    list_res2 = await client.get(f"/api/v1/candidates/{cand.id}/notes", headers=headers)
    assert list_res2.status_code == 200
    assert list_res2.json()["total"] == 0


@pytest.mark.asyncio
async def test_candidate_note_permissions_and_privacy(client: AsyncClient, db_session: AsyncSession):
    # Recruiter 1 & Org
    recruiter1, org = await seed_user_with_org(
        db_session, email="rec1@firm.com", password="Password123!", role="recruiter", org_name="Staffing Firm"
    )
    # Recruiter 2 in same org
    recruiter2 = await create_test_user(db_session, email="rec2@firm.com", password="Password123!")
    await create_membership(db_session, recruiter2.id, org.id, role="recruiter")
    # Delivery head in same org
    delivery_head = await create_test_user(db_session, email="head@firm.com", password="Password123!")
    await create_membership(db_session, delivery_head.id, org.id, role="delivery_head")
    # Client hiring manager in same org
    client_user = await create_test_user(db_session, email="client@firm.com", password="Password123!")
    await create_membership(db_session, client_user.id, org.id, role="client_hiring_manager")
    await db_session.commit()

    cand = Candidate(id=uuid.uuid4(), organization_id=org.id, full_name="Candidate Sec", email="sec@example.com")
    db_session.add(cand)
    await db_session.commit()

    headers_rec1 = auth_headers(recruiter1.id, "recruiter", org.id)
    headers_rec2 = auth_headers(recruiter2.id, "recruiter", org.id)
    headers_head = auth_headers(delivery_head.id, "delivery_head", org.id)
    headers_client = auth_headers(client_user.id, "client_hiring_manager", org.id)

    # Recruiter 1 creates note
    res = await client.post(
        f"/api/v1/candidates/{cand.id}/notes",
        json={"content": "Confidential screening note by recruiter 1"},
        headers=headers_rec1,
    )
    assert res.status_code == 201
    note_id = res.json()["id"]

    # Recruiter 2 attempts to edit Recruiter 1's note -> 403 Forbidden
    res_rec2_edit = await client.put(
        f"/api/v1/candidates/notes/{note_id}",
        json={"content": "Attempted unauthorized edit"},
        headers=headers_rec2,
    )
    assert res_rec2_edit.status_code == 403

    # Recruiter 2 attempts to delete Recruiter 1's note -> 403 Forbidden
    res_rec2_del = await client.delete(f"/api/v1/candidates/notes/{note_id}", headers=headers_rec2)
    assert res_rec2_del.status_code == 403

    # Client user attempts to access candidate notes -> 403 Forbidden
    res_client_get = await client.get(f"/api/v1/candidates/{cand.id}/notes", headers=headers_client)
    assert res_client_get.status_code == 403

    # Delivery head (privileged) CAN edit note
    res_head_edit = await client.put(
        f"/api/v1/candidates/notes/{note_id}",
        json={"content": "Delivery head approval and notes added"},
        headers=headers_head,
    )
    assert res_head_edit.status_code == 200

    # Delivery head CAN delete note
    res_head_del = await client.delete(f"/api/v1/candidates/notes/{note_id}", headers=headers_head)
    assert res_head_del.status_code == 200

