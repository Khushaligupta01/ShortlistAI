from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    candidates,
    health,
    organizations,
    requisitions,
    resumes,
    users,
)

router = APIRouter()

router.include_router(health.router)
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(organizations.router)
router.include_router(requisitions.router)
router.include_router(resumes.router)
router.include_router(candidates.router)
