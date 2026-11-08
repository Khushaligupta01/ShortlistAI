from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    candidate_notes,
    candidates,
    client_portal,
    dashboard,
    delivery_head,
    evaluations,
    health,
    organizations,
    privacy,
    recruiter_submissions,
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
router.include_router(candidate_notes.router)
router.include_router(evaluations.router)
router.include_router(dashboard.router)
router.include_router(client_portal.router)
router.include_router(recruiter_submissions.router)
router.include_router(delivery_head.router)
router.include_router(privacy.router)
