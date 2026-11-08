from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_role
from app.db.session import get_db
from app.models.organization import Organization
from app.models.requisition import Requisition
from app.models.submission import Submission
from app.schemas.auth import CurrentUserResponse
from app.services.submission_service import ALL_PIPELINE_STAGES

router = APIRouter(prefix="/delivery", tags=["delivery-head"])


class ClientPipelineSummary(BaseModel):
    client_organization_id: uuid.UUID
    client_organization_name: str
    active_requisitions_count: int
    total_submissions: int
    shortlisted_count: int
    interview_count: int
    hired_count: int


class DeliveryPipelineSummaryResponse(BaseModel):
    total_submissions: int
    stage_breakdown: dict[str, int]
    clients: list[ClientPipelineSummary]
    conversion_shortlist_rate: float
    conversion_interview_rate: float
    conversion_hire_rate: float


@router.get("/pipeline-summary", response_model=DeliveryPipelineSummaryResponse)
async def get_delivery_pipeline_summary(
    current_user: CurrentUserResponse = require_role("delivery_head", "admin", "super_admin"),
    db: AsyncSession = Depends(get_db),
) -> DeliveryPipelineSummaryResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context.")

    source_org_id = uuid.UUID(current_user.organization_id)

    # 1. Total submissions and stage breakdown for this staffing firm
    stage_query = await db.execute(
        select(Submission.current_stage, func.count(Submission.id))
        .where(
            Submission.source_organization_id == source_org_id,
            Submission.status == "active",
        )
        .group_by(Submission.current_stage)
    )
    stage_breakdown: dict[str, int] = {s[0]: 0 for s in ALL_PIPELINE_STAGES}
    for row in stage_query.fetchall():
        stage_breakdown[row[0]] = row[1]

    total_submissions = sum(stage_breakdown.values())

    # 2. Per-client breakdown
    client_subs_query = await db.execute(
        select(
            Submission.client_organization_id,
            Organization.name,
            func.count(Submission.id).label("total_subs"),
            func.count(Submission.id).filter(
                Submission.current_stage.in_(["CLIENT_SHORTLISTED", "INTERVIEW_SCHEDULED", "OFFER_EXTENDED", "HIRED"])
            ).label("shortlisted"),
            func.count(Submission.id).filter(
                Submission.current_stage.in_(["INTERVIEW_REQUESTED", "INTERVIEW_SCHEDULED"])
            ).label("interviews"),
            func.count(Submission.id).filter(
                Submission.current_stage == "HIRED"
            ).label("hired"),
        )
        .join(Organization, Submission.client_organization_id == Organization.id)
        .where(
            Submission.source_organization_id == source_org_id,
            Submission.status == "active",
        )
        .group_by(Submission.client_organization_id, Organization.name)
    )

    clients_list: list[ClientPipelineSummary] = []
    for row in client_subs_query.fetchall():
        client_org_id = row[0]
        client_name = row[1]
        t_subs = row[2]
        s_count = row[3]
        i_count = row[4]
        h_count = row[5]

        # Count active requisitions for this client
        req_count_res = await db.execute(
            select(func.count(Requisition.id)).where(
                Requisition.organization_id == source_org_id,
                Requisition.client_organization_id == client_org_id,
            )
        )
        active_reqs = req_count_res.scalar() or 0

        clients_list.append(
            ClientPipelineSummary(
                client_organization_id=client_org_id,
                client_organization_name=client_name,
                active_requisitions_count=active_reqs,
                total_submissions=t_subs,
                shortlisted_count=s_count,
                interview_count=i_count,
                hired_count=h_count,
            )
        )

    # Calculate conversion metrics
    total_shortlisted = sum(c.shortlisted_count for c in clients_list)
    total_interviews = sum(c.interview_count for c in clients_list)
    total_hired = sum(c.hired_count for c in clients_list)

    shortlist_rate = round((total_shortlisted / total_submissions * 100), 1) if total_submissions > 0 else 0.0
    interview_rate = round((total_interviews / total_submissions * 100), 1) if total_submissions > 0 else 0.0
    hire_rate = round((total_hired / total_submissions * 100), 1) if total_submissions > 0 else 0.0

    return DeliveryPipelineSummaryResponse(
        total_submissions=total_submissions,
        stage_breakdown=stage_breakdown,
        clients=clients_list,
        conversion_shortlist_rate=shortlist_rate,
        conversion_interview_rate=interview_rate,
        conversion_hire_rate=hire_rate,
    )

