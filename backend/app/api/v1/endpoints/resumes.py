from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import CurrentUserResponse
from app.schemas.resume import (
    ResumeDetailResponse,
    ResumeFileResponse,
    ResumeReviewRequest,
    UploadBatchResponse,
)
from app.services.resume_service import resume_service

router = APIRouter(tags=["resumes"])


async def _get_db_user(current_user: CurrentUserResponse, db: AsyncSession):
    repo = UserRepository(db)
    user = await repo.get_by_id(uuid.UUID(current_user.id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user


@router.post(
    "/requisitions/{requisition_id}/resumes/upload",
    response_model=UploadBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resumes(
    requisition_id: uuid.UUID,
    files: List[UploadFile] = File(...),
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadBatchResponse:
    user = await _get_db_user(current_user, db)
    batch = await resume_service.upload_resumes(
        db=db,
        requisition_id=requisition_id,
        user=user,
        files=files,
    )
    return UploadBatchResponse.model_validate(batch)


@router.get("/resume-batches/{batch_id}", response_model=UploadBatchResponse)
async def get_batch_status(
    batch_id: uuid.UUID,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UploadBatchResponse:
    user = await _get_db_user(current_user, db)
    batch = await resume_service.get_batch(db=db, batch_id=batch_id, user=user)
    return UploadBatchResponse.model_validate(batch)


@router.get("/resume-batches/{batch_id}/files", response_model=List[ResumeFileResponse])
async def get_batch_files(
    batch_id: uuid.UUID,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ResumeFileResponse]:
    user = await _get_db_user(current_user, db)
    files = await resume_service.get_batch_files(db=db, batch_id=batch_id, user=user)
    return [ResumeFileResponse.model_validate(f) for f in files]


@router.get("/resumes/{resume_id}", response_model=ResumeDetailResponse)
async def get_resume_detail(
    resume_id: uuid.UUID,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeDetailResponse:
    user = await _get_db_user(current_user, db)
    resume = await resume_service.get_resume(db=db, resume_id=resume_id, user=user)
    return ResumeDetailResponse.model_validate(resume)


@router.get("/resumes/{resume_id}/download")
async def download_resume_document(
    resume_id: uuid.UUID,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    user = await _get_db_user(current_user, db)
    file_bytes, filename, mime_type = await resume_service.download_resume(
        db=db, resume_id=resume_id, user=user
    )
    # Safe inline or attachment header
    safe_filename = filename.replace('"', '\\"')
    return Response(
        content=file_bytes,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )


@router.post("/resumes/{resume_id}/retry", response_model=ResumeFileResponse)
async def retry_failed_resume(
    resume_id: uuid.UUID,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeFileResponse:
    user = await _get_db_user(current_user, db)
    resume = await resume_service.retry_resume(db=db, resume_id=resume_id, user=user)
    return ResumeFileResponse.model_validate(resume)


@router.post("/resumes/{resume_id}/review", response_model=ResumeFileResponse)
async def review_parsed_resume(
    resume_id: uuid.UUID,
    body: ResumeReviewRequest,
    current_user: CurrentUserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeFileResponse:
    user = await _get_db_user(current_user, db)
    resume = await resume_service.review_resume(
        db=db,
        resume_id=resume_id,
        user=user,
        full_name=body.full_name,
        email=body.email,
        phone=body.phone,
        location=body.location,
        notice_period_days=body.notice_period_days,
        skills=body.skills,
    )
    return ResumeFileResponse.model_validate(resume)
