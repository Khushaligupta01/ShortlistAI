from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_role
from app.db.session import get_db
from app.models.organization import Organization
from app.schemas.auth import CurrentUserResponse
from app.schemas.submission import (
    ClientRequestResponse,
    PipelineBoardResponse,
    RecruiterResponseRequest,
    RecruiterStageUpdateRequest,
    RecruiterSubmissionListItemResponse,
    SubmissionCreateRequest,
)
from app.services.submission_service import SubmissionService

router = APIRouter(tags=["recruiter-submissions"])


class ClientOrgOption(BaseModel):
    id: uuid.UUID
    name: str
    org_type: str


def _get_source_org_id(current_user: CurrentUserResponse) -> uuid.UUID:
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organization context found for user.",
        )
    return uuid.UUID(current_user.organization_id)


@router.post("/requisitions/{requisition_id}/submissions", status_code=status.HTTP_201_CREATED)
async def submit_candidate_to_client(
    requisition_id: uuid.UUID,
    payload: SubmissionCreateRequest,
    current_user: CurrentUserResponse = require_role("recruiter", "delivery_head", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
):
    submission = await SubmissionService.create_submission(
        db=db,
        requisition_id=requisition_id,
        candidate_id=payload.candidate_id,
        client_organization_id=payload.client_organization_id,
        current_user=current_user,
        recruiter_notes_for_client=payload.recruiter_notes_for_client,
    )
    return {
        "submission_id": submission.id,
        "candidate_id": submission.candidate_id,
        "candidate_reference": submission.custom_candidate_reference,
        "requisition_id": submission.requisition_id,
        "client_organization_id": submission.client_organization_id,
        "current_stage": submission.current_stage,
        "submitted_at": submission.submitted_at,
        "message": "Candidate submitted to client successfully.",
    }


@router.get("/recruiter/submissions", response_model=list[RecruiterSubmissionListItemResponse])
async def list_recruiter_submissions(
    requisition_id: Optional[uuid.UUID] = Query(None),
    client_org_id: Optional[uuid.UUID] = Query(None),
    stage: Optional[str] = Query(None),
    current_user: CurrentUserResponse = require_role("recruiter", "delivery_head", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> list[RecruiterSubmissionListItemResponse]:
    source_org_id = _get_source_org_id(current_user)
    return await SubmissionService.get_recruiter_submissions(
        db=db,
        source_org_id=source_org_id,
        requisition_id=requisition_id,
        client_org_id=client_org_id,
        stage=stage,
    )


@router.get("/recruiter/pipeline", response_model=PipelineBoardResponse)
async def get_pipeline_board(
    requisition_id: Optional[uuid.UUID] = Query(None),
    client_org_id: Optional[uuid.UUID] = Query(None),
    current_user: CurrentUserResponse = require_role("recruiter", "delivery_head", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> PipelineBoardResponse:
    source_org_id = _get_source_org_id(current_user)
    return await SubmissionService.get_pipeline_board(
        db=db,
        source_org_id=source_org_id,
        requisition_id=requisition_id,
        client_org_id=client_org_id,
    )


@router.patch("/recruiter/submissions/{submission_id}/stage")
async def update_pipeline_stage(
    submission_id: uuid.UUID,
    payload: RecruiterStageUpdateRequest,
    current_user: CurrentUserResponse = require_role("recruiter", "delivery_head", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
):
    submission = await SubmissionService.update_pipeline_stage(
        db=db,
        submission_id=submission_id,
        recruiter_user=current_user,
        stage=payload.stage,
        reason_note=payload.reason_note,
    )
    return {
        "submission_id": submission.id,
        "current_stage": submission.current_stage,
        "message": f"Pipeline stage updated to {submission.current_stage}.",
    }


@router.post("/recruiter/requests/{request_id}/response", response_model=ClientRequestResponse)
async def respond_to_client_request(
    request_id: uuid.UUID,
    payload: RecruiterResponseRequest,
    current_user: CurrentUserResponse = require_role("recruiter", "delivery_head", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> ClientRequestResponse:
    client_req = await SubmissionService.respond_to_client_request(
        db=db,
        request_id=request_id,
        recruiter_user=current_user,
        response_text=payload.recruiter_response,
        new_stage=payload.new_stage,
    )
    return ClientRequestResponse(
        id=client_req.id,
        submission_id=client_req.submission_id,
        client_organization_id=client_req.client_organization_id,
        requested_by=client_req.requested_by,
        requester_name=None,
        request_type=client_req.request_type,
        details=client_req.details,
        status=client_req.status,
        recruiter_response=client_req.recruiter_response,
        responded_by=client_req.responded_by,
        responder_name=current_user.display_name,
        responded_at=client_req.responded_at,
        created_at=client_req.created_at,
        updated_at=client_req.updated_at,
    )


@router.get("/recruiter/clients", response_model=list[ClientOrgOption])
async def list_available_client_organizations(
    current_user: CurrentUserResponse = require_role("recruiter", "delivery_head", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> list[ClientOrgOption]:
    # List client companies that can be submitted to
    res = await db.execute(
        select(Organization).where(Organization.org_type == "client_company").order_by(Organization.name)
    )
    clients = res.scalars().all()
    if not clients:
        # Also return all organizations other than the user's staffing firm if org_type wasn't set to client_company
        res_all = await db.execute(
            select(Organization)
            .where(Organization.id != uuid.UUID(current_user.organization_id))
            .order_by(Organization.name)
        )
        clients = res_all.scalars().all()

    return [
        ClientOrgOption(id=c.id, name=c.name, org_type=c.org_type)
        for c in clients
    ]

