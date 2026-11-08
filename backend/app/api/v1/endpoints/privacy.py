from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.auth import get_current_user
from app.db.session import get_db
from app.schemas.auth import CurrentUserResponse
from app.schemas.privacy import (
    AuditEventResponse,
    AuditLogListResponse,
    CandidateExportData,
    ConsentDecisionRequest,
    ConsentPublicInfoResponse,
    ConsentRecordResponse,
    ConsentRequestCreate,
    ConsentRequestResponse,
    ConsentWithdrawRequest,
    DataRequestCreate,
    DataRequestResponse,
    DeletionExecuteResponse,
    DeletionRequestCreate,
    DeletionRequestResponse,
    DeletionReviewRequest,
    EvaluationQualityResponse,
    GovernanceAIMetricsResponse,
    PrivacyDashboardResponse,
)
from app.services import (
    audit_service,
    consent_service,
    data_export_service,
    deletion_service,
    governance_service,
)

router = APIRouter(tags=["privacy-and-governance"])

PRIVILEGED_ROLES = {"delivery_head", "admin", "super_admin"}
RECRUITER_ROLES = {"recruiter", "delivery_head", "admin", "super_admin"}


def verify_role(current_user: CurrentUserResponse, allowed_roles: set[str]) -> None:
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Forbidden: role '{current_user.role}' lacks permission for this operation.",
        )


# ============================================================================
# Candidate Consent Endpoints
# ============================================================================

@router.post(
    "/candidates/{candidate_id}/consent-requests",
    response_model=ConsentRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_consent_request(
    candidate_id: uuid.UUID,
    payload: ConsentRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    try:
        record, raw_token = await consent_service.create_consent_request(
            db=db,
            candidate_id=candidate_id,
            organization_id=uuid.UUID(str(current_user.organization_id)),
            recruiter_id=uuid.UUID(str(current_user.id)),
            purpose=payload.purpose,
            collection_method=payload.collection_method,
            requisition_id=payload.requisition_id,
        )
        return ConsentRequestResponse(
            id=record.id,
            candidate_id=record.candidate_id,
            status=record.status,
            purpose=record.purpose,
            version=record.version,
            collection_method=record.collection_method,
            token=raw_token,
            consent_url=f"/public/consent/{raw_token}",
            token_expires_at=record.token_expires_at,
            created_at=record.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/candidates/{candidate_id}/consent",
    response_model=List[ConsentRecordResponse],
)
async def get_candidate_consent(
    candidate_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    records = await consent_service.get_candidate_consent_records(
        db=db,
        candidate_id=candidate_id,
        organization_id=uuid.UUID(str(current_user.organization_id)),
    )
    return [
        ConsentRecordResponse(
            id=r.id,
            candidate_id=r.candidate_id,
            organization_id=r.organization_id,
            uploaded_by=r.uploaded_by,
            legal_basis=r.legal_basis,
            status=r.status,
            purpose=r.purpose,
            version=r.version,
            collection_method=r.collection_method,
            requisition_id=r.requisition_id,
            privacy_notice_acknowledged=r.privacy_notice_acknowledged,
            withdrawn_at=r.withdrawn_at,
            withdrawal_reason=r.withdrawal_reason,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in records
    ]


@router.post(
    "/candidates/{candidate_id}/consent/withdraw",
    response_model=ConsentRecordResponse,
)
async def withdraw_candidate_consent(
    candidate_id: uuid.UUID,
    payload: ConsentWithdrawRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    try:
        record = await consent_service.withdraw_candidate_consent(
            db=db,
            candidate_id=candidate_id,
            organization_id=uuid.UUID(str(current_user.organization_id)),
            actor_id=uuid.UUID(str(current_user.id)),
            reason=payload.reason,
        )
        return ConsentRecordResponse(
            id=record.id,
            candidate_id=record.candidate_id,
            organization_id=record.organization_id,
            uploaded_by=record.uploaded_by,
            legal_basis=record.legal_basis,
            status=record.status,
            purpose=record.purpose,
            version=record.version,
            collection_method=record.collection_method,
            requisition_id=record.requisition_id,
            privacy_notice_acknowledged=record.privacy_notice_acknowledged,
            withdrawn_at=record.withdrawn_at,
            withdrawal_reason=record.withdrawal_reason,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/consent-records",
    response_model=Dict[str, Any],
)
async def list_consent_records(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    records, total = await consent_service.list_consent_records(
        db=db,
        organization_id=uuid.UUID(str(current_user.organization_id)),
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            ConsentRecordResponse(
                id=r.id,
                candidate_id=r.candidate_id,
                organization_id=r.organization_id,
                uploaded_by=r.uploaded_by,
                legal_basis=r.legal_basis,
                status=r.status,
                purpose=r.purpose,
                version=r.version,
                collection_method=r.collection_method,
                requisition_id=r.requisition_id,
                privacy_notice_acknowledged=r.privacy_notice_acknowledged,
                withdrawn_at=r.withdrawn_at,
                withdrawal_reason=r.withdrawal_reason,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in records
        ],
        "total": total,
    }


# Public candidate consent response endpoints (No JWT required)
@router.get(
    "/public/consent/{token}",
    response_model=ConsentPublicInfoResponse,
)
async def get_public_consent_info(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    try:
        info = await consent_service.get_public_consent_info(db=db, raw_token=token)
        return ConsentPublicInfoResponse(**info)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/public/consent/{token}/decision",
    response_model=ConsentRecordResponse,
)
async def submit_public_consent_decision(
    token: str,
    payload: ConsentDecisionRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    try:
        record = await consent_service.record_candidate_consent_decision(
            db=db,
            raw_token=token,
            decision=payload.decision,
            reason=payload.reason,
            ip_address=client_ip,
            user_agent=user_agent,
        )
        return ConsentRecordResponse(
            id=record.id,
            candidate_id=record.candidate_id,
            organization_id=record.organization_id,
            uploaded_by=record.uploaded_by,
            legal_basis=record.legal_basis,
            status=record.status,
            purpose=record.purpose,
            version=record.version,
            collection_method=record.collection_method,
            requisition_id=record.requisition_id,
            privacy_notice_acknowledged=record.privacy_notice_acknowledged,
            withdrawn_at=record.withdrawn_at,
            withdrawal_reason=record.withdrawal_reason,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Candidate Data Access & Export Endpoints
# ============================================================================

@router.post(
    "/candidates/{candidate_id}/data-requests",
    response_model=DataRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_data_request(
    candidate_id: uuid.UUID,
    payload: DataRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    try:
        req = await data_export_service.create_data_request(
            db=db,
            candidate_id=candidate_id,
            organization_id=uuid.UUID(str(current_user.organization_id)),
            requested_by=uuid.UUID(str(current_user.id)),
            request_type=payload.request_type,
            reason=payload.reason,
        )
        return DataRequestResponse(
            id=req.id,
            candidate_id=req.candidate_id,
            organization_id=req.organization_id,
            requested_by=req.requested_by,
            request_type=req.request_type,
            status=req.status,
            export_file_path=req.export_file_path,
            export_metadata=req.export_metadata,
            expires_at=req.expires_at,
            created_at=req.created_at,
            completed_at=req.completed_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/data-requests",
    response_model=Dict[str, Any],
)
async def list_data_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    records, total = await data_export_service.list_data_requests(
        db=db,
        organization_id=uuid.UUID(str(current_user.organization_id)),
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            DataRequestResponse(
                id=r.id,
                candidate_id=r.candidate_id,
                organization_id=r.organization_id,
                requested_by=r.requested_by,
                request_type=r.request_type,
                status=r.status,
                export_file_path=r.export_file_path,
                export_metadata=r.export_metadata,
                expires_at=r.expires_at,
                created_at=r.created_at,
                completed_at=r.completed_at,
            )
            for r in records
        ],
        "total": total,
    }


@router.get(
    "/data-requests/{request_id}",
    response_model=DataRequestResponse,
)
async def get_data_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    req = await data_export_service.get_data_request(
        db=db,
        request_id=request_id,
        organization_id=uuid.UUID(str(current_user.organization_id)),
    )
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data request not found.")
    return DataRequestResponse(
        id=req.id,
        candidate_id=req.candidate_id,
        organization_id=req.organization_id,
        requested_by=req.requested_by,
        request_type=req.request_type,
        status=req.status,
        export_file_path=req.export_file_path,
        export_metadata=req.export_metadata,
        expires_at=req.expires_at,
        created_at=req.created_at,
        completed_at=req.completed_at,
    )


@router.post(
    "/data-requests/{request_id}/export",
    response_model=CandidateExportData,
)
async def generate_export(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    try:
        data = await data_export_service.generate_candidate_export(
            db=db,
            request_id=request_id,
            organization_id=uuid.UUID(str(current_user.organization_id)),
        )
        return CandidateExportData(**data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/data-exports/{request_id}",
)
async def download_data_export(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    try:
        content, filename = await data_export_service.download_data_export(
            db=db,
            request_id=request_id,
            organization_id=uuid.UUID(str(current_user.organization_id)),
            actor_id=uuid.UUID(str(current_user.id)),
        )
        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ============================================================================
# Candidate Deletion Endpoints
# ============================================================================

@router.post(
    "/candidates/{candidate_id}/deletion-requests",
    response_model=DeletionRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_deletion_request(
    candidate_id: uuid.UUID,
    payload: DeletionRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    try:
        req = await deletion_service.create_deletion_request(
            db=db,
            candidate_id=candidate_id,
            organization_id=uuid.UUID(str(current_user.organization_id)),
            requested_by=uuid.UUID(str(current_user.id)),
            reason=payload.reason,
        )
        return DeletionRequestResponse(
            id=req.id,
            candidate_id=req.candidate_id,
            organization_id=req.organization_id,
            requested_by=req.requested_by,
            reviewer_id=req.reviewer_id,
            reason=req.reason,
            status=req.status,
            review_decision=req.review_decision,
            review_notes=req.review_notes,
            retention_policy_notes=req.retention_policy_notes,
            files_deleted_count=req.files_deleted_count,
            is_legal_hold=req.is_legal_hold,
            legal_hold_reason=req.legal_hold_reason,
            created_at=req.created_at,
            updated_at=req.updated_at,
            completed_at=req.completed_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/deletion-requests",
    response_model=Dict[str, Any],
)
async def list_deletion_requests(
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    records, total = await deletion_service.list_deletion_requests(
        db=db,
        organization_id=uuid.UUID(str(current_user.organization_id)),
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [
            DeletionRequestResponse(
                id=r.id,
                candidate_id=r.candidate_id,
                organization_id=r.organization_id,
                requested_by=r.requested_by,
                reviewer_id=r.reviewer_id,
                reason=r.reason,
                status=r.status,
                review_decision=r.review_decision,
                review_notes=r.review_notes,
                retention_policy_notes=r.retention_policy_notes,
                files_deleted_count=r.files_deleted_count,
                is_legal_hold=r.is_legal_hold,
                legal_hold_reason=r.legal_hold_reason,
                created_at=r.created_at,
                updated_at=r.updated_at,
                completed_at=r.completed_at,
            )
            for r in records
        ],
        "total": total,
    }


@router.get(
    "/deletion-requests/{request_id}",
    response_model=DeletionRequestResponse,
)
async def get_deletion_request(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    req = await deletion_service.get_deletion_request(
        db=db,
        request_id=request_id,
        organization_id=uuid.UUID(str(current_user.organization_id)),
    )
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deletion request not found.")
    return DeletionRequestResponse(
        id=req.id,
        candidate_id=req.candidate_id,
        organization_id=req.organization_id,
        requested_by=req.requested_by,
        reviewer_id=req.reviewer_id,
        reason=req.reason,
        status=req.status,
        review_decision=req.review_decision,
        review_notes=req.review_notes,
        retention_policy_notes=req.retention_policy_notes,
        files_deleted_count=req.files_deleted_count,
        is_legal_hold=req.is_legal_hold,
        legal_hold_reason=req.legal_hold_reason,
        created_at=req.created_at,
        updated_at=req.updated_at,
        completed_at=req.completed_at,
    )


@router.post(
    "/deletion-requests/{request_id}/review",
    response_model=DeletionRequestResponse,
)
async def review_deletion_request(
    request_id: uuid.UUID,
    payload: DeletionReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, PRIVILEGED_ROLES)
    try:
        req = await deletion_service.review_deletion_request(
            db=db,
            request_id=request_id,
            organization_id=uuid.UUID(str(current_user.organization_id)),
            reviewer_id=uuid.UUID(str(current_user.id)),
            decision=payload.decision,
            review_notes=payload.review_notes,
            retention_policy_notes=payload.retention_policy_notes,
            is_legal_hold=payload.is_legal_hold,
            legal_hold_reason=payload.legal_hold_reason,
        )
        return DeletionRequestResponse(
            id=req.id,
            candidate_id=req.candidate_id,
            organization_id=req.organization_id,
            requested_by=req.requested_by,
            reviewer_id=req.reviewer_id,
            reason=req.reason,
            status=req.status,
            review_decision=req.review_decision,
            review_notes=req.review_notes,
            retention_policy_notes=req.retention_policy_notes,
            files_deleted_count=req.files_deleted_count,
            is_legal_hold=req.is_legal_hold,
            legal_hold_reason=req.legal_hold_reason,
            created_at=req.created_at,
            updated_at=req.updated_at,
            completed_at=req.completed_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/deletion-requests/{request_id}/execute",
    response_model=DeletionExecuteResponse,
)
async def execute_deletion(
    request_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, PRIVILEGED_ROLES)
    try:
        result = await deletion_service.execute_deletion(
            db=db,
            request_id=request_id,
            organization_id=uuid.UUID(str(current_user.organization_id)),
            actor_id=uuid.UUID(str(current_user.id)),
        )
        return DeletionExecuteResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ============================================================================
# Centralized Audit Log Endpoints
# ============================================================================

@router.get(
    "/audit-events",
    response_model=AuditLogListResponse,
)
async def list_audit_events(
    event_type: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    records, total = await audit_service.query_audit_logs(
        db=db,
        organization_id=uuid.UUID(str(current_user.organization_id)),
        event_type=event_type,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return AuditLogListResponse(
        items=[AuditEventResponse(**r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/audit-events/{event_id}",
    response_model=AuditEventResponse,
)
async def get_audit_event(
    event_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    event = await audit_service.get_audit_log_by_id(
        db=db,
        organization_id=uuid.UUID(str(current_user.organization_id)),
        event_id=event_id,
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit event not found.")
    return AuditEventResponse(**event)


# ============================================================================
# Responsible AI Governance & Quality Metrics
# ============================================================================

@router.get(
    "/governance/ai-metrics",
    response_model=GovernanceAIMetricsResponse,
)
async def get_ai_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    metrics = await governance_service.get_governance_ai_metrics(
        db=db,
        organization_id=uuid.UUID(str(current_user.organization_id)),
    )
    return GovernanceAIMetricsResponse(**metrics)


@router.get(
    "/governance/evaluation-quality",
    response_model=EvaluationQualityResponse,
)
async def get_evaluation_quality(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    metrics = await governance_service.get_evaluation_quality_metrics(
        db=db,
        organization_id=uuid.UUID(str(current_user.organization_id)),
    )
    return EvaluationQualityResponse(**metrics)


@router.get(
    "/privacy/dashboard",
    response_model=PrivacyDashboardResponse,
)
async def get_privacy_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUserResponse = Depends(get_current_user),
):
    verify_role(current_user, RECRUITER_ROLES)
    stats = await governance_service.get_privacy_dashboard_stats(
        db=db,
        organization_id=uuid.UUID(str(current_user.organization_id)),
    )
    return PrivacyDashboardResponse(
        pending_consent_requests_count=stats["pending_consent_requests_count"],
        granted_consents_count=stats["granted_consents_count"],
        withdrawn_consents_count=stats["withdrawn_consents_count"],
        pending_data_requests_count=stats["pending_data_requests_count"],
        completed_exports_count=stats["completed_exports_count"],
        pending_deletion_requests_count=stats["pending_deletion_requests_count"],
        completed_deletions_count=stats["completed_deletions_count"],
        active_legal_holds_count=stats["active_legal_holds_count"],
        recent_audit_events=[AuditEventResponse(**e) for e in stats["recent_audit_events"]],
    )
