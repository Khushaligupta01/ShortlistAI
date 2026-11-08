from __future__ import annotations

import re
import uuid
from typing import Any, Optional

from app.models.candidate import Candidate
from app.models.evaluation import Evaluation
from app.models.submission import Submission, PipelineRecord, ClientRequest
from app.schemas.submission import (
    MaskedCandidateProfileResponse,
    MaskedCriterionEvidence,
    MaskedEducation,
    MaskedEmployment,
    PipelineRecordResponse,
    ClientRequestResponse,
    ClientSubmissionListItemResponse,
)


class CandidateMaskingService:
    @staticmethod
    def generate_candidate_reference(candidate_id: uuid.UUID) -> str:
        """
        Generate a unique, professional candidate reference code.
        Format: Candidate CND-XXXXX
        """
        hex_suffix = str(candidate_id).replace("-", "")[:5].upper()
        return f"Candidate CND-{hex_suffix}"

    @staticmethod
    def mask_location(location: Optional[str]) -> Optional[str]:
        """
        Sanitize location to broad city, state/country level.
        Strips street addresses, unit numbers, and specific zip codes.
        """
        if not location:
            return None
        loc = location.strip()
        # Remove postal/zip codes (e.g. 78701 or 78701-1234)
        loc = re.sub(r"\b\d{5}(-\d{4})?\b", "", loc).strip()
        # Remove street patterns if comma separated
        parts = [p.strip() for p in loc.split(",") if p.strip()]
        if len(parts) > 2:
            # Drop the leading street address part (e.g., "123 Main St, Austin, TX" -> "Austin, TX")
            return ", ".join(parts[-2:])
        return loc if loc else None

    @classmethod
    def mask_profile_for_client(
        cls,
        submission: Submission,
        candidate: Candidate,
        requisition_title: str,
        evaluation: Optional[Evaluation] = None,
        pipeline_records: Optional[list[PipelineRecord]] = None,
        client_requests: Optional[list[ClientRequest]] = None,
    ) -> MaskedCandidateProfileResponse:
        """
        Builds a strictly privacy-safe masked candidate profile for client users.
        Zero PII (no name, email, phone, street address, private recruiter notes, or resume files).
        """
        ref = submission.custom_candidate_reference or cls.generate_candidate_reference(candidate.id)

        # Masked employments
        masked_employments: list[MaskedEmployment] = []
        if candidate.employments:
            for emp in sorted(
                candidate.employments,
                key=lambda x: str(x.start_date) if x.start_date else "",
                reverse=True,
            ):
                masked_employments.append(
                    MaskedEmployment(
                        title=getattr(emp, "job_title", getattr(emp, "title", None)),
                        company=emp.company,
                        start_date=str(emp.start_date) if emp.start_date else None,
                        end_date=str(emp.end_date) if emp.end_date else None,
                        is_current=bool(emp.is_current),
                        description=emp.description,
                    )
                )

        # Masked educations
        masked_educations: list[MaskedEducation] = []
        if candidate.educations:
            for edu in candidate.educations:
                masked_educations.append(
                    MaskedEducation(
                        degree=getattr(edu, "qualification", getattr(edu, "degree", None)),
                        institution=edu.institution,
                        field_of_study=edu.field_of_study,
                        graduation_year=edu.graduation_year,
                    )
                )

        # Skills
        skills = [s.name for s in candidate.skills] if candidate.skills else []

        # Certifications
        certs: list[str] = []
        if candidate.certifications:
            if isinstance(candidate.certifications, list):
                certs = [str(c) for c in candidate.certifications]
            elif isinstance(candidate.certifications, str):
                certs = [candidate.certifications]

        # Evaluation criteria evidence
        criterion_evidences: list[MaskedCriterionEvidence] = []
        overall_score: Optional[float] = None
        eval_summary: Optional[str] = None

        if evaluation:
            score_val = getattr(evaluation, "total_score", getattr(evaluation, "overall_score", None))
            overall_score = float(score_val) if score_val is not None else None
            eval_summary = getattr(evaluation, "summary", getattr(evaluation, "executive_summary", None))

            evidence_list = getattr(evaluation, "evidence", getattr(evaluation, "evidence_items", []))
            if evidence_list:
                for ev in evidence_list:
                    crit_name = "Criterion"
                    crit_cat = "General"
                    if hasattr(ev, "criterion") and ev.criterion:
                        crit_name = getattr(ev.criterion, "criterion_name", getattr(ev.criterion, "name", getattr(ev.criterion, "label", "Criterion")))
                        crit_cat = getattr(ev.criterion, "criterion_type", getattr(ev.criterion, "category", "General"))

                    crit_id = getattr(ev, "scorecard_criterion_id", getattr(ev, "criterion_id", uuid.uuid4()))
                    status_val = getattr(ev, "evidence_status", getattr(ev, "status", "UNKNOWN"))
                    reasoning_val = getattr(ev, "explanation", getattr(ev, "reasoning", None))

                    criterion_evidences.append(
                        MaskedCriterionEvidence(
                            criterion_id=crit_id,
                            criterion_name=crit_name,
                            category=crit_cat,
                            status=status_val,
                            evidence_excerpt=ev.evidence_text,
                            reasoning=reasoning_val,
                        )
                    )

        # Pipeline history
        history_resp: list[PipelineRecordResponse] = []
        if pipeline_records:
            for pr in sorted(pipeline_records, key=lambda x: x.changed_at, reverse=True):
                actor_name = None
                if hasattr(pr, "changer") and pr.changer:
                    actor_name = getattr(pr.changer, "display_name", getattr(pr.changer, "email", "User"))
                history_resp.append(
                    PipelineRecordResponse(
                        id=pr.id,
                        submission_id=pr.submission_id,
                        current_stage=pr.current_stage,
                        previous_stage=pr.previous_stage,
                        changed_by=pr.changed_by,
                        actor_name=actor_name,
                        reason_note=pr.reason_note,
                        changed_at=pr.changed_at,
                        is_reopened=pr.is_reopened,
                    )
                )

        # Requests
        requests_resp: list[ClientRequestResponse] = []
        if client_requests:
            for req in sorted(client_requests, key=lambda x: x.created_at, reverse=True):
                req_name = getattr(req.requester, "display_name", getattr(req.requester, "email", None)) if hasattr(req, "requester") and req.requester else None
                resp_name = getattr(req.responder, "display_name", getattr(req.responder, "email", None)) if hasattr(req, "responder") and req.responder else None
                requests_resp.append(
                    ClientRequestResponse(
                        id=req.id,
                        submission_id=req.submission_id,
                        client_organization_id=req.client_organization_id,
                        requested_by=req.requested_by,
                        requester_name=req_name,
                        request_type=req.request_type,
                        details=req.details,
                        status=req.status,
                        recruiter_response=req.recruiter_response,
                        responded_by=req.responded_by,
                        responder_name=resp_name,
                        responded_at=req.responded_at,
                        created_at=req.created_at,
                        updated_at=req.updated_at,
                    )
                )

        latest_decision = None
        if history_resp:
            for h in history_resp:
                if h.current_stage in {"CLIENT_SHORTLISTED", "CLIENT_REJECTED", "INTERVIEW_REQUESTED", "ADDITIONAL_INFO_REQUESTED"}:
                    latest_decision = h.current_stage
                    break

        return MaskedCandidateProfileResponse(
            submission_id=submission.id,
            candidate_id=candidate.id,
            candidate_reference=ref,
            requisition_id=submission.requisition_id,
            requisition_title=requisition_title,
            current_stage=submission.current_stage,
            submitted_at=submission.submitted_at,
            recruiter_notes_for_client=submission.recruiter_notes_for_client,
            location=cls.mask_location(candidate.location),
            total_experience_years=float(candidate.total_experience_years) if candidate.total_experience_years is not None else None,
            notice_period_days=candidate.notice_period_days,
            overall_score=overall_score,
            evaluation_summary=eval_summary,
            skills=skills,
            employments=masked_employments,
            educations=masked_educations,
            certifications=certs,
            criterion_evaluations=criterion_evidences,
            latest_decision=latest_decision,
            pipeline_history=history_resp,
            requests=requests_resp,
        )

    @classmethod
    def mask_submission_list_item(
        cls,
        submission: Submission,
        candidate: Candidate,
        requisition_title: str,
        overall_score: Optional[float] = None,
    ) -> ClientSubmissionListItemResponse:
        ref = submission.custom_candidate_reference or cls.generate_candidate_reference(candidate.id)
        skills = [s.name for s in candidate.skills] if candidate.skills else []

        pending_action = None
        if submission.current_stage in {"SUBMITTED", "CLIENT_REVIEW_PENDING"}:
            pending_action = "Review Required"
        elif submission.current_stage == "ADDITIONAL_INFO_REQUESTED":
            pending_action = "Awaiting Recruiter Info"
        elif submission.current_stage == "INTERVIEW_REQUESTED":
            pending_action = "Interview Pending Scheduling"

        return ClientSubmissionListItemResponse(
            submission_id=submission.id,
            candidate_id=candidate.id,
            candidate_reference=ref,
            requisition_id=submission.requisition_id,
            requisition_title=requisition_title,
            location=cls.mask_location(candidate.location),
            total_experience_years=float(candidate.total_experience_years) if candidate.total_experience_years is not None else None,
            overall_score=overall_score,
            skills=skills,
            current_stage=submission.current_stage,
            submitted_at=submission.submitted_at,
            pending_action=pending_action,
        )
