from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, EvaluationEvidence
from app.models.organization import Organization
from app.models.requisition import Requisition
from app.models.submission import ClientRequest, PipelineRecord, Submission
from app.models.user import User
from app.schemas.auth import CurrentUserResponse
from app.schemas.submission import (
    ClientDashboardMetricsResponse,
    ClientRequisitionDetailResponse,
    ClientRequisitionListItemResponse,
    ClientSubmissionListItemResponse,
    MaskedCandidateProfileResponse,
    PipelineBoardResponse,
    PipelineStageSummaryResponse,
    RecruiterSubmissionListItemResponse,
)
from app.services.candidate_masking_service import CandidateMaskingService

VALID_CLIENT_DECISIONS = {
    "CLIENT_SHORTLISTED",
    "CLIENT_REJECTED",
    "INTERVIEW_REQUESTED",
    "ADDITIONAL_INFO_REQUESTED",
}

ALL_PIPELINE_STAGES = [
    ("SUBMITTED", "Submitted for Review"),
    ("CLIENT_SHORTLISTED", "Client Shortlisted"),
    ("INTERVIEW_REQUESTED", "Interview Requested"),
    ("INTERVIEW_SCHEDULED", "Interview Scheduled"),
    ("ADDITIONAL_INFO_REQUESTED", "Info Requested"),
    ("OFFER_EXTENDED", "Offer Extended"),
    ("HIRED", "Hired"),
    ("CLIENT_REJECTED", "Client Rejected"),
    ("WITHDRAWN", "Withdrawn"),
]


class SubmissionService:
    @classmethod
    async def create_submission(
        cls,
        db: AsyncSession,
        requisition_id: uuid.UUID,
        candidate_id: uuid.UUID,
        client_organization_id: uuid.UUID,
        current_user: CurrentUserResponse,
        recruiter_notes_for_client: Optional[str] = None,
    ) -> Submission:
        # 1. Verify requisition
        req_res = await db.execute(
            select(Requisition).where(
                Requisition.id == requisition_id,
                Requisition.organization_id == current_user.organization_id,
            )
        )
        requisition = req_res.scalar_one_or_none()
        if not requisition:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requisition not found or access denied.",
            )

        # 2. Verify candidate
        cand_res = await db.execute(
            select(Candidate).where(
                Candidate.id == candidate_id,
                Candidate.organization_id == current_user.organization_id,
            )
        )
        candidate = cand_res.scalar_one_or_none()
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found or access denied.",
            )

        # Check candidate consent and deletion status
        from app.services.consent_service import is_processing_allowed
        allowed, reason = is_processing_allowed(candidate)
        if not allowed:
            from app.services.audit_service import log_event
            await log_event(
                db=db,
                organization_id=current_user.organization_id,
                actor_user_id=current_user.id,
                event_type="SUBMISSION_BLOCKED_CONSENT",
                resource_type="candidate",
                resource_id=candidate.id,
                payload={"reason": reason, "requisition_id": str(requisition_id)},
                commit=True,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Client submission blocked: {reason}",
            )

        # 3. Verify client organization
        client_org_res = await db.execute(
            select(Organization).where(Organization.id == client_organization_id)
        )
        client_org = client_org_res.scalar_one_or_none()
        if not client_org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client organization not found.",
            )

        # 4. Check that requisition is shared with client org or associate it
        if requisition.client_organization_id is None:
            requisition.client_organization_id = client_organization_id

        # 5. Check candidate evaluation
        eval_res = await db.execute(
            select(Evaluation)
            .where(
                Evaluation.candidate_id == candidate_id,
                Evaluation.requisition_id == requisition_id,
            )
            .order_by(Evaluation.created_at.desc())
        )
        evaluation = eval_res.scalars().first()
        if not evaluation:
            # Fall back to candidate's latest evaluation overall if requisition evaluation hasn't been created separately
            eval_fallback = await db.execute(
                select(Evaluation)
                .where(Evaluation.candidate_id == candidate_id)
                .order_by(Evaluation.created_at.desc())
            )
            evaluation = eval_fallback.scalars().first()

        if not evaluation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Candidate must be evaluated against a scorecard before submission to a client.",
            )

        # 6. Prevent active duplicate submission
        dup_res = await db.execute(
            select(Submission).where(
                Submission.candidate_id == candidate_id,
                Submission.requisition_id == requisition_id,
                Submission.client_organization_id == client_organization_id,
                Submission.status == "active",
                Submission.current_stage.notin_(["CLIENT_REJECTED", "WITHDRAWN"]),
            )
        )
        existing_sub = dup_res.scalar_one_or_none()
        if existing_sub:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate has already been submitted to this client for this requisition (Current Stage: {existing_sub.current_stage}).",
            )

        # 7. Generate reference code
        custom_ref = CandidateMaskingService.generate_candidate_reference(candidate.id)

        # 8. Create submission
        user_uuid = uuid.UUID(str(current_user.id))
        source_org_uuid = uuid.UUID(str(current_user.organization_id))

        submission = Submission(
            candidate_id=candidate.id,
            requisition_id=requisition.id,
            evaluation_id=evaluation.id,
            submitted_by=user_uuid,
            source_organization_id=source_org_uuid,
            client_organization_id=client_organization_id,
            status="active",
            current_stage="SUBMITTED",
            recruiter_notes_for_client=recruiter_notes_for_client,
            custom_candidate_reference=custom_ref,
        )
        db.add(submission)
        await db.flush()

        # 9. Create initial pipeline record
        pipeline_rec = PipelineRecord(
            submission_id=submission.id,
            current_stage="SUBMITTED",
            previous_stage=None,
            changed_by=user_uuid,
            reason_note="Candidate submitted to client by recruiter.",
            is_reopened=False,
        )
        db.add(pipeline_rec)
        await db.commit()
        await db.refresh(submission)
        return submission

    @classmethod
    async def record_client_decision(
        cls,
        db: AsyncSession,
        submission_id: uuid.UUID,
        client_user: CurrentUserResponse,
        decision: str,
        reason_note: Optional[str] = None,
        interview_details: Optional[str] = None,
        info_request_details: Optional[str] = None,
    ) -> Submission:
        if decision not in VALID_CLIENT_DECISIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid client decision: {decision}. Allowed: {sorted(list(VALID_CLIENT_DECISIONS))}",
            )

        client_org_uuid = uuid.UUID(str(client_user.organization_id))
        client_user_uuid = uuid.UUID(str(client_user.id))

        sub_res = await db.execute(
            select(Submission)
            .where(
                Submission.id == submission_id,
                Submission.client_organization_id == client_org_uuid,
            )
        )
        submission = sub_res.scalar_one_or_none()
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found or access denied.",
            )

        previous_stage = submission.current_stage
        submission.current_stage = decision

        # If interview requested with details, create ClientRequest
        if decision == "INTERVIEW_REQUESTED" and interview_details:
            client_req = ClientRequest(
                submission_id=submission.id,
                client_organization_id=client_org_uuid,
                requested_by=client_user_uuid,
                request_type="INTERVIEW",
                details=interview_details,
                status="PENDING",
            )
            db.add(client_req)

        # If additional info requested with details, create ClientRequest
        if decision == "ADDITIONAL_INFO_REQUESTED" and info_request_details:
            client_req = ClientRequest(
                submission_id=submission.id,
                client_organization_id=client_org_uuid,
                requested_by=client_user_uuid,
                request_type="ADDITIONAL_INFO",
                details=info_request_details,
                status="PENDING",
            )
            db.add(client_req)

        # Append Pipeline Record
        is_reopened = previous_stage in ["CLIENT_REJECTED", "WITHDRAWN"]
        pipeline_rec = PipelineRecord(
            submission_id=submission.id,
            current_stage=decision,
            previous_stage=previous_stage,
            changed_by=client_user_uuid,
            reason_note=reason_note or f"Client decision recorded: {decision}",
            is_reopened=is_reopened,
        )
        db.add(pipeline_rec)
        await db.commit()
        await db.refresh(submission)
        return submission

    @classmethod
    async def create_client_request(
        cls,
        db: AsyncSession,
        submission_id: uuid.UUID,
        client_user: CurrentUserResponse,
        request_type: str,
        details: str,
    ) -> ClientRequest:
        client_org_uuid = uuid.UUID(str(client_user.organization_id))
        client_user_uuid = uuid.UUID(str(client_user.id))

        sub_res = await db.execute(
            select(Submission).where(
                Submission.id == submission_id,
                Submission.client_organization_id == client_org_uuid,
            )
        )
        submission = sub_res.scalar_one_or_none()
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found or access denied.",
            )

        client_req = ClientRequest(
            submission_id=submission.id,
            client_organization_id=client_org_uuid,
            requested_by=client_user_uuid,
            request_type=request_type,
            details=details,
            status="PENDING",
        )
        db.add(client_req)

        # Update stage if appropriate
        previous_stage = submission.current_stage
        target_stage = "INTERVIEW_REQUESTED" if request_type == "INTERVIEW" else "ADDITIONAL_INFO_REQUESTED"
        if submission.current_stage != target_stage:
            submission.current_stage = target_stage
            pipeline_rec = PipelineRecord(
                submission_id=submission.id,
                current_stage=target_stage,
                previous_stage=previous_stage,
                changed_by=client_user_uuid,
                reason_note=f"Client request submitted: {request_type}",
                is_reopened=False,
            )
            db.add(pipeline_rec)

        await db.commit()
        await db.refresh(client_req)
        return client_req

    @classmethod
    async def respond_to_client_request(
        cls,
        db: AsyncSession,
        request_id: uuid.UUID,
        recruiter_user: CurrentUserResponse,
        response_text: str,
        new_stage: Optional[str] = None,
    ) -> ClientRequest:
        req_res = await db.execute(
            select(ClientRequest)
            .options(selectinload(ClientRequest.submission))
            .where(ClientRequest.id == request_id)
        )
        client_req = req_res.scalar_one_or_none()
        if not client_req or not client_req.submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client request not found.",
            )

        # Check organization isolation for recruiter
        if str(client_req.submission.source_organization_id) != str(recruiter_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this request.",
            )

        recruiter_user_uuid = uuid.UUID(str(recruiter_user.id))
        client_req.recruiter_response = response_text
        client_req.status = "RESPONDED"
        client_req.responded_by = recruiter_user_uuid
        client_req.responded_at = datetime.now(timezone.utc)

        if new_stage:
            previous_stage = client_req.submission.current_stage
            client_req.submission.current_stage = new_stage
            pipeline_rec = PipelineRecord(
                submission_id=client_req.submission.id,
                current_stage=new_stage,
                previous_stage=previous_stage,
                changed_by=recruiter_user_uuid,
                reason_note=f"Recruiter updated stage to {new_stage} upon responding to request.",
                is_reopened=False,
            )
            db.add(pipeline_rec)

        await db.commit()
        await db.refresh(client_req)
        return client_req

    @classmethod
    async def update_pipeline_stage(
        cls,
        db: AsyncSession,
        submission_id: uuid.UUID,
        recruiter_user: CurrentUserResponse,
        stage: str,
        reason_note: Optional[str] = None,
    ) -> Submission:
        recruiter_org_uuid = uuid.UUID(str(recruiter_user.organization_id))
        recruiter_user_uuid = uuid.UUID(str(recruiter_user.id))

        sub_res = await db.execute(
            select(Submission).where(
                Submission.id == submission_id,
                Submission.source_organization_id == recruiter_org_uuid,
            )
        )
        submission = sub_res.scalar_one_or_none()
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found or access denied.",
            )

        previous_stage = submission.current_stage
        submission.current_stage = stage
        if stage == "WITHDRAWN":
            submission.withdrawn_at = datetime.now(timezone.utc)

        pipeline_rec = PipelineRecord(
            submission_id=submission.id,
            current_stage=stage,
            previous_stage=previous_stage,
            changed_by=recruiter_user_uuid,
            reason_note=reason_note or f"Stage updated to {stage} by recruiter.",
            is_reopened=(previous_stage in ["CLIENT_REJECTED", "WITHDRAWN"]),
        )
        db.add(pipeline_rec)
        await db.commit()
        await db.refresh(submission)
        return submission

    @classmethod
    async def get_client_dashboard_metrics(
        cls,
        db: AsyncSession,
        client_org_id: uuid.UUID,
    ) -> ClientDashboardMetricsResponse:
        # Requisitions count
        req_count_res = await db.execute(
            select(func.count(Requisition.id)).where(
                Requisition.client_organization_id == client_org_id
            )
        )
        active_reqs = req_count_res.scalar() or 0

        # Submissions counts grouped by stage
        subs_res = await db.execute(
            select(Submission.current_stage, func.count(Submission.id))
            .where(
                Submission.client_organization_id == client_org_id,
                Submission.status == "active",
            )
            .group_by(Submission.current_stage)
        )
        stage_counts = dict(subs_res.fetchall())

        total = sum(stage_counts.values())
        awaiting_review = stage_counts.get("SUBMITTED", 0) + stage_counts.get("CLIENT_REVIEW_PENDING", 0)
        shortlisted = (
            stage_counts.get("CLIENT_SHORTLISTED", 0)
            + stage_counts.get("INTERVIEW_SCHEDULED", 0)
            + stage_counts.get("OFFER_EXTENDED", 0)
            + stage_counts.get("HIRED", 0)
        )
        rejected = stage_counts.get("CLIENT_REJECTED", 0)
        interview_requested = stage_counts.get("INTERVIEW_REQUESTED", 0)
        additional_info = stage_counts.get("ADDITIONAL_INFO_REQUESTED", 0)

        return ClientDashboardMetricsResponse(
            active_requisitions_count=active_reqs,
            total_submissions_count=total,
            awaiting_review_count=awaiting_review,
            shortlisted_count=shortlisted,
            rejected_count=rejected,
            interview_requested_count=interview_requested,
            additional_info_requested_count=additional_info,
        )

    @classmethod
    async def get_client_requisitions(
        cls,
        db: AsyncSession,
        client_org_id: uuid.UUID,
    ) -> list[ClientRequisitionListItemResponse]:
        query = (
            select(Requisition)
            .where(Requisition.client_organization_id == client_org_id)
            .order_by(Requisition.created_at.desc())
        )
        res = await db.execute(query)
        reqs = res.scalars().all()

        results: list[ClientRequisitionListItemResponse] = []
        for req in reqs:
            # Count submissions
            count_res = await db.execute(
                select(
                    func.count(Submission.id),
                    func.count(Submission.id).filter(
                        Submission.current_stage.in_(["SUBMITTED", "CLIENT_REVIEW_PENDING"])
                    ),
                ).where(
                    Submission.requisition_id == req.id,
                    Submission.client_organization_id == client_org_id,
                    Submission.status == "active",
                )
            )
            total_sub, awaiting_sub = count_res.one()

            results.append(
                ClientRequisitionListItemResponse(
                    id=req.id,
                    title=req.title,
                    location=req.location,
                    status=req.status,
                    created_at=req.created_at,
                    submissions_count=total_sub or 0,
                    awaiting_review_count=awaiting_sub or 0,
                )
            )
        return results

    @classmethod
    async def get_client_requisition_detail(
        cls,
        db: AsyncSession,
        requisition_id: uuid.UUID,
        client_org_id: uuid.UUID,
    ) -> ClientRequisitionDetailResponse:
        res = await db.execute(
            select(Requisition).where(
                Requisition.id == requisition_id,
                Requisition.client_organization_id == client_org_id,
            )
        )
        req = res.scalar_one_or_none()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requisition not found or access denied.",
            )

        count_res = await db.execute(
            select(func.count(Submission.id)).where(
                Submission.requisition_id == req.id,
                Submission.client_organization_id == client_org_id,
                Submission.status == "active",
            )
        )
        total_sub = count_res.scalar() or 0

        return ClientRequisitionDetailResponse(
            id=req.id,
            title=req.title,
            job_description=req.job_description,
            location=req.location,
            status=req.status,
            created_at=req.created_at,
            submissions_count=total_sub,
        )

    @classmethod
    async def get_client_submissions(
        cls,
        db: AsyncSession,
        client_org_id: uuid.UUID,
        requisition_id: Optional[uuid.UUID] = None,
        stage: Optional[str] = None,
    ) -> list[ClientSubmissionListItemResponse]:
        query = (
            select(Submission)
            .options(
                selectinload(Submission.candidate).selectinload(Candidate.skills),
                selectinload(Submission.requisition),
                selectinload(Submission.evaluation),
            )
            .where(
                Submission.client_organization_id == client_org_id,
                Submission.status == "active",
            )
        )
        if requisition_id:
            query = query.where(Submission.requisition_id == requisition_id)
        if stage:
            query = query.where(Submission.current_stage == stage)

        query = query.order_by(Submission.submitted_at.desc())
        res = await db.execute(query)
        submissions = res.scalars().all()

        results: list[ClientSubmissionListItemResponse] = []
        for s in submissions:
            score = (
                float(getattr(s.evaluation, "total_score", getattr(s.evaluation, "overall_score", None)))
                if s.evaluation and getattr(s.evaluation, "total_score", getattr(s.evaluation, "overall_score", None)) is not None
                else None
            )
            results.append(
                CandidateMaskingService.mask_submission_list_item(
                    submission=s,
                    candidate=s.candidate,
                    requisition_title=s.requisition.title if s.requisition else "Requisition",
                    overall_score=score,
                )
            )
        return results

    @classmethod
    async def get_client_submission_detail(
        cls,
        db: AsyncSession,
        submission_id: uuid.UUID,
        client_org_id: uuid.UUID,
    ) -> MaskedCandidateProfileResponse:
        query = (
            select(Submission)
            .options(
                selectinload(Submission.candidate).selectinload(Candidate.skills),
                selectinload(Submission.candidate).selectinload(Candidate.employments),
                selectinload(Submission.candidate).selectinload(Candidate.educations),
                selectinload(Submission.requisition),
                selectinload(Submission.evaluation).selectinload(Evaluation.evidence).selectinload(EvaluationEvidence.criterion),
                selectinload(Submission.pipeline_records).selectinload(PipelineRecord.changer),
                selectinload(Submission.requests).selectinload(ClientRequest.requester),
                selectinload(Submission.requests).selectinload(ClientRequest.responder),
            )
            .where(
                Submission.id == submission_id,
                Submission.client_organization_id == client_org_id,
            )
        )
        res = await db.execute(query)
        submission = res.scalar_one_or_none()
        if not submission:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found or access denied.",
            )

        return CandidateMaskingService.mask_profile_for_client(
            submission=submission,
            candidate=submission.candidate,
            requisition_title=submission.requisition.title if submission.requisition else "Requisition",
            evaluation=submission.evaluation,
            pipeline_records=submission.pipeline_records,
            client_requests=submission.requests,
        )

    @classmethod
    async def get_recruiter_submissions(
        cls,
        db: AsyncSession,
        source_org_id: uuid.UUID,
        requisition_id: Optional[uuid.UUID] = None,
        client_org_id: Optional[uuid.UUID] = None,
        stage: Optional[str] = None,
    ) -> list[RecruiterSubmissionListItemResponse]:
        query = (
            select(Submission)
            .options(
                selectinload(Submission.candidate),
                selectinload(Submission.requisition),
                selectinload(Submission.evaluation),
                selectinload(Submission.client_organization),
                selectinload(Submission.pipeline_records),
                selectinload(Submission.requests),
            )
            .where(
                Submission.source_organization_id == source_org_id,
                Submission.status == "active",
            )
        )
        if requisition_id:
            query = query.where(Submission.requisition_id == requisition_id)
        if client_org_id:
            query = query.where(Submission.client_organization_id == client_org_id)
        if stage:
            query = query.where(Submission.current_stage == stage)

        query = query.order_by(Submission.submitted_at.desc())
        res = await db.execute(query)
        submissions = res.scalars().all()

        results: list[RecruiterSubmissionListItemResponse] = []
        for s in submissions:
            score = (
                float(getattr(s.evaluation, "total_score", getattr(s.evaluation, "overall_score", None)))
                if s.evaluation and getattr(s.evaluation, "total_score", getattr(s.evaluation, "overall_score", None)) is not None
                else None
            )
            # Find latest activity
            last_activity = s.submitted_at
            if s.pipeline_records:
                latest_p = max(p.changed_at for p in s.pipeline_records)
                if latest_p > last_activity:
                    last_activity = latest_p

            pending_reqs = sum(1 for r in s.requests if r.status == "PENDING")

            results.append(
                RecruiterSubmissionListItemResponse(
                    submission_id=s.id,
                    candidate_id=s.candidate_id,
                    candidate_name=s.candidate.full_name,
                    candidate_email=s.candidate.email,
                    candidate_reference=s.custom_candidate_reference or f"Candidate CND-{str(s.candidate_id)[:5].upper()}",
                    requisition_id=s.requisition_id,
                    requisition_title=s.requisition.title if s.requisition else "Requisition",
                    client_organization_id=s.client_organization_id,
                    client_organization_name=s.client_organization.name if s.client_organization else "Client",
                    current_stage=s.current_stage,
                    overall_score=score,
                    submitted_at=s.submitted_at,
                    last_activity_at=last_activity,
                    pending_requests_count=pending_reqs,
                )
            )
        return results

    @classmethod
    async def get_pipeline_board(
        cls,
        db: AsyncSession,
        source_org_id: uuid.UUID,
        requisition_id: Optional[uuid.UUID] = None,
        client_org_id: Optional[uuid.UUID] = None,
    ) -> PipelineBoardResponse:
        submissions = await cls.get_recruiter_submissions(
            db=db,
            source_org_id=source_org_id,
            requisition_id=requisition_id,
            client_org_id=client_org_id,
        )

        stage_counts: dict[str, int] = {code: 0 for code, _ in ALL_PIPELINE_STAGES}
        for sub in submissions:
            if sub.current_stage in stage_counts:
                stage_counts[sub.current_stage] += 1
            else:
                stage_counts[sub.current_stage] = 1

        summaries = [
            PipelineStageSummaryResponse(
                stage=code,
                stage_label=label,
                count=stage_counts.get(code, 0),
            )
            for code, label in ALL_PIPELINE_STAGES
        ]

        return PipelineBoardResponse(stages=summaries, submissions=submissions)
