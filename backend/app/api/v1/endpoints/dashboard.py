from __future__ import annotations

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_role
from app.db.session import get_db
from app.schemas.auth import CurrentUserResponse
from app.schemas.dashboard import (
    DashboardActivityResponse,
    DashboardMetricsResponse,
    RecruiterDashboardResponse,
)
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/recruiter", tags=["recruiter-dashboard"])

_RECRUITER_OR_INTERNAL = require_role("recruiter", "delivery_head", "admin", "super_admin")


@router.get("/dashboard", response_model=RecruiterDashboardResponse)
async def get_recruiter_dashboard(
    current_user: CurrentUserResponse = _RECRUITER_OR_INTERNAL,
    db: AsyncSession = Depends(get_db),
) -> RecruiterDashboardResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context.")

    org_id = uuid.UUID(current_user.organization_id)
    return await dashboard_service.get_full_dashboard(db, org_id)


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_recruiter_metrics(
    current_user: CurrentUserResponse = _RECRUITER_OR_INTERNAL,
    db: AsyncSession = Depends(get_db),
) -> DashboardMetricsResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context.")

    org_id = uuid.UUID(current_user.organization_id)
    return await dashboard_service.get_dashboard_metrics(db, org_id)


@router.get("/activity", response_model=DashboardActivityResponse)
async def get_recruiter_activity(
    limit: int = Query(20, ge=1, le=100),
    current_user: CurrentUserResponse = _RECRUITER_OR_INTERNAL,
    db: AsyncSession = Depends(get_db),
) -> DashboardActivityResponse:
    if not current_user.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No organization context.")

    org_id = uuid.UUID(current_user.organization_id)
    activities = await dashboard_service.get_recruiter_activity(db, org_id, limit=limit)
    return DashboardActivityResponse(activities=activities)
