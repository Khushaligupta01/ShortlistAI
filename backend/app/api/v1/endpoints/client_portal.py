from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_role
from app.db.session import get_db
from app.schemas.auth import CurrentUserResponse
from app.schemas.submission import (
    ClientDashboardMetricsResponse,
    ClientDecisionCreateRequest,
    ClientRequisitionDetailResponse,
    ClientRequisitionListItemResponse,
    ClientRequestCreateRequest,
    ClientRequestResponse,
    ClientSubmissionListItemResponse,
    MaskedCandidateProfileResponse,
    PipelineRecordResponse,
)
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/client", tags=["client-portal"])


def _get_client_org_id(current_user: CurrentUserResponse) -> uuid.UUID:
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No organization context found for user.",
        )
    return uuid.UUID(current_user.organization_id)


@router.get("/dashboard", response_model=ClientDashboardMetricsResponse)
async def get_client_dashboard(
    current_user: CurrentUserResponse = require_role("client_hiring_manager", "client", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> ClientDashboardMetricsResponse:
    org_id = _get_client_org_id(current_user)
    return await SubmissionService.get_client_dashboard_metrics(db=db, client_org_id=org_id)


@router.get("/requisitions", response_model=list[ClientRequisitionListItemResponse])
async def list_client_requisitions(
    current_user: CurrentUserResponse = require_role("client_hiring_manager", "client", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> list[ClientRequisitionListItemResponse]:
    org_id = _get_client_org_id(current_user)
    return await SubmissionService.get_client_requisitions(db=db, client_org_id=org_id)


@router.get("/requisitions/{requisition_id}", response_model=ClientRequisitionDetailResponse)
async def get_client_requisition(
    requisition_id: uuid.UUID,
    current_user: CurrentUserResponse = require_role("client_hiring_manager", "client", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> ClientRequisitionDetailResponse:
    org_id = _get_client_org_id(current_user)
    return await SubmissionService.get_client_requisition_detail(
        db=db, requisition_id=requisition_id, client_org_id=org_id
    )


@router.get("/submissions", response_model=list[ClientSubmissionListItemResponse])
async def list_client_submissions(
    requisition_id: Optional[uuid.UUID] = Query(None),
    stage: Optional[str] = Query(None),
    current_user: CurrentUserResponse = require_role("client_hiring_manager", "client", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> list[ClientSubmissionListItemResponse]:
    org_id = _get_client_org_id(current_user)
    return await SubmissionService.get_client_submissions(
        db=db,
        client_org_id=org_id,
        requisition_id=requisition_id,
        stage=stage,
    )


@router.get("/submissions/{submission_id}", response_model=MaskedCandidateProfileResponse)
async def get_client_submission_profile(
    submission_id: uuid.UUID,
    current_user: CurrentUserResponse = require_role("client_hiring_manager", "client", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> MaskedCandidateProfileResponse:
    org_id = _get_client_org_id(current_user)
    return await SubmissionService.get_client_submission_detail(
        db=db, submission_id=submission_id, client_org_id=org_id
    )


@router.post("/submissions/{submission_id}/decisions", response_model=MaskedCandidateProfileResponse)
async def record_client_decision(
    submission_id: uuid.UUID,
    payload: ClientDecisionCreateRequest,
    current_user: CurrentUserResponse = require_role("client_hiring_manager", "client", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> MaskedCandidateProfileResponse:
    org_id = _get_client_org_id(current_user)
    await SubmissionService.record_client_decision(
        db=db,
        submission_id=submission_id,
        client_user=current_user,
        decision=payload.decision,
        reason_note=payload.reason_note,
        interview_details=payload.interview_details,
        info_request_details=payload.info_request_details,
    )
    return await SubmissionService.get_client_submission_detail(
        db=db, submission_id=submission_id, client_org_id=org_id
    )


@router.post("/submissions/{submission_id}/requests", response_model=ClientRequestResponse)
async def create_client_request(
    submission_id: uuid.UUID,
    payload: ClientRequestCreateRequest,
    current_user: CurrentUserResponse = require_role("client_hiring_manager", "client", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> ClientRequestResponse:
    req = await SubmissionService.create_client_request(
        db=db,
        submission_id=submission_id,
        client_user=current_user,
        request_type=payload.request_type,
        details=payload.details,
    )
    requester_name = current_user.display_name
    return ClientRequestResponse(
        id=req.id,
        submission_id=req.submission_id,
        client_organization_id=req.client_organization_id,
        requested_by=req.requested_by,
        requester_name=requester_name,
        request_type=req.request_type,
        details=req.details,
        status=req.status,
        recruiter_response=req.recruiter_response,
        responded_by=req.responded_by,
        responder_name=None,
        responded_at=req.responded_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
    )


@router.get("/submissions/{submission_id}/history", response_model=list[PipelineRecordResponse])
async def get_client_submission_history(
    submission_id: uuid.UUID,
    current_user: CurrentUserResponse = require_role("client_hiring_manager", "client", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> list[PipelineRecordResponse]:
    org_id = _get_client_org_id(current_user)
    profile = await SubmissionService.get_client_submission_detail(
        db=db, submission_id=submission_id, client_org_id=org_id
    )
    return profile.pipeline_history

