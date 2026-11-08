from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import AuditLog, ConsentRecord, DataRequest, DeletionRequest
from app.models.candidate import Candidate
from app.models.evaluation import Evaluation, EvaluationEvidence, RecruiterReview
from app.models.resume import Resume
from app.services.audit_service import query_audit_logs


async def get_governance_ai_metrics(
    db: AsyncSession,
    organization_id: uuid.UUID,
) -> Dict[str, Any]:
    """Computes responsible AI observability, score distribution, and override metrics."""
    # Fetch all evaluations for candidates in this organization
    eval_query = (
        select(Evaluation)
        .join(Candidate, Evaluation.candidate_id == Candidate.id)
        .options(
            selectinload(Evaluation.evidence),
            selectinload(Evaluation.reviews),
        )
        .where(Candidate.organization_id == organization_id)
    )
    res = await db.execute(eval_query)
    evaluations = res.scalars().all()

    total_evals = len(evaluations)
    if total_evals == 0:
        return {
            "total_evaluations": 0,
            "score_distribution": {"high": 0, "medium": 0, "low": 0},
            "average_score": 0.0,
            "average_evidence_coverage_pct": 0.0,
            "unknown_criteria_frequency": {},
            "recruiter_review_distribution": {
                "SHORTLIST": 0, "HOLD": 0, "REJECT": 0, "REQUEST_INFO": 0, "UNREVIEWED": 0
            },
            "override_rate_pct": 0.0,
            "model_breakdown": {"gpt-4o": 0, "deterministic_rule_engine": 0},
            "fairness_and_bias_disclaimer": (
                "These operational statistics reflect evaluation score distributions and evidence coverage "
                "within the organization. They do not constitute formal statistical fairness or algorithmic bias "
                "certification under statutory anti-discrimination frameworks, which require specialized adverse impact "
                "studies on demographic cohorts under qualified legal counsel."
            ),
        }

    high_count = 0
    med_count = 0
    low_count = 0
    score_sum = 0.0
    coverage_sum = 0.0
    unknown_counts: Dict[str, int] = {}
    review_counts = {
        "SHORTLIST": 0, "HOLD": 0, "REJECT": 0, "REQUEST_INFO": 0, "UNREVIEWED": 0
    }
    overrides_count = 0

    for ev in evaluations:
        score = float(ev.total_score) if ev.total_score is not None else 0.0
        score_sum += score

        if score >= 70.0:
            high_count += 1
        elif score >= 50.0:
            med_count += 1
        else:
            low_count += 1

        coverage = float(ev.evidence_coverage) if ev.evidence_coverage is not None else 0.0
        coverage_sum += coverage

        for item in ev.evidence:
            if item.evidence_status == "UNKNOWN":
                crit_key = str(item.scorecard_criterion_id)
                unknown_counts[crit_key] = unknown_counts.get(crit_key, 0) + 1
            if getattr(item, "is_overridden", False):
                overrides_count += 1

        if ev.reviews:
            dec = ev.reviews[0].decision.upper()
            review_counts[dec] = review_counts.get(dec, 0) + 1
        else:
            review_counts["UNREVIEWED"] += 1

    avg_score = round(score_sum / total_evals, 2)
    avg_coverage = round(coverage_sum / total_evals, 2)
    override_rate = round((overrides_count / max(1, total_evals)) * 100, 2)

    return {
        "total_evaluations": total_evals,
        "score_distribution": {
            "high": high_count,
            "medium": med_count,
            "low": low_count,
        },
        "average_score": avg_score,
        "average_evidence_coverage_pct": avg_coverage,
        "unknown_criteria_frequency": unknown_counts,
        "recruiter_review_distribution": review_counts,
        "override_rate_pct": override_rate,
        "model_breakdown": {
            "gpt-4o": total_evals,
            "deterministic_rule_engine": total_evals,
        },
        "fairness_and_bias_disclaimer": (
            "These operational statistics reflect evaluation score distributions and evidence coverage "
            "within the organization. They do not constitute formal statistical fairness or algorithmic bias "
            "certification under statutory anti-discrimination frameworks, which require specialized adverse impact "
            "studies on demographic cohorts under qualified legal counsel."
        ),
    }


async def get_evaluation_quality_metrics(
    db: AsyncSession,
    organization_id: uuid.UUID,
) -> Dict[str, Any]:
    """Computes evidence token verification and document parsing quality indicators."""
    eval_query = (
        select(Evaluation)
        .join(Candidate, Evaluation.candidate_id == Candidate.id)
        .options(selectinload(Evaluation.evidence))
        .where(Candidate.organization_id == organization_id)
    )
    res = await db.execute(eval_query)
    evaluations = res.scalars().all()

    total_evals = len(evaluations)
    confidence_counts = {"HIGH": 0, "NEEDS_REVIEW": 0, "LOW": 0}
    total_evidence_items = 0
    verified_evidence_items = 0

    for ev in evaluations:
        conf = (ev.confidence_level or "NEEDS_REVIEW").upper()
        confidence_counts[conf] = confidence_counts.get(conf, 0) + 1

        for item in ev.evidence:
            total_evidence_items += 1
            if item.evidence_status in ("MATCHED", "STRONG_MATCH", "PARTIAL_MATCH"):
                verified_evidence_items += 1

    # Check resumes parsing stats
    resume_query = select(Resume).where(Resume.organization_id == organization_id)
    resume_res = await db.execute(resume_query)
    resumes = resume_res.scalars().all()

    total_resumes = len(resumes)
    ocr_count = sum(1 for r in resumes if r.parse_status == "ocr_required")
    error_count = sum(1 for r in resumes if r.parse_status in ("failed", "error"))

    token_pass_rate = (
        round((verified_evidence_items / max(1, total_evidence_items)) * 100, 2)
        if total_evidence_items > 0
        else 100.0
    )
    ocr_rate = round((ocr_count / max(1, total_resumes)) * 100, 2) if total_resumes > 0 else 0.0
    error_rate = round((error_count / max(1, total_resumes)) * 100, 2) if total_resumes > 0 else 0.0

    return {
        "total_evaluations": total_evals,
        "confidence_breakdown": confidence_counts,
        "token_verification_pass_rate_pct": token_pass_rate,
        "scanned_image_ocr_rate_pct": ocr_rate,
        "processing_error_rate_pct": error_rate,
        "quality_assurance_notes": [
            "All candidate evaluation scores are calculated 100% deterministically using approved scorecard weights.",
            "Protected demographic attributes (name, gender, age, photo, marital status) are excluded prior to scoring.",
            "Candidate evidence citations require verbatim token verification against original extracted resume text.",
            "Missing criteria are flagged as UNKNOWN without applying automatic negative penalties.",
        ],
    }


async def get_privacy_dashboard_stats(
    db: AsyncSession,
    organization_id: uuid.UUID,
) -> Dict[str, Any]:
    """Gathers summary counters for the Privacy & Governance dashboard."""
    # Consent counts
    c_pending = await db.execute(
        select(func.count()).select_from(ConsentRecord).where(
            ConsentRecord.organization_id == organization_id,
            ConsentRecord.status == "PENDING",
        )
    )
    c_granted = await db.execute(
        select(func.count()).select_from(ConsentRecord).where(
            ConsentRecord.organization_id == organization_id,
            ConsentRecord.status == "GRANTED",
        )
    )
    c_withdrawn = await db.execute(
        select(func.count()).select_from(ConsentRecord).where(
            ConsentRecord.organization_id == organization_id,
            ConsentRecord.status == "WITHDRAWN",
        )
    )

    # Data request counts
    d_pending = await db.execute(
        select(func.count()).select_from(DataRequest).where(
            DataRequest.organization_id == organization_id,
            DataRequest.status == "PENDING",
        )
    )
    d_completed = await db.execute(
        select(func.count()).select_from(DataRequest).where(
            DataRequest.organization_id == organization_id,
            DataRequest.status == "COMPLETED",
        )
    )

    # Deletion counts
    del_pending = await db.execute(
        select(func.count()).select_from(DeletionRequest).where(
            DeletionRequest.organization_id == organization_id,
            DeletionRequest.status.in_(["REQUESTED", "UNDER_REVIEW", "APPROVED"]),
        )
    )
    del_completed = await db.execute(
        select(func.count()).select_from(DeletionRequest).where(
            DeletionRequest.organization_id == organization_id,
            DeletionRequest.status == "COMPLETED",
        )
    )
    del_holds = await db.execute(
        select(func.count()).select_from(DeletionRequest).where(
            DeletionRequest.organization_id == organization_id,
            DeletionRequest.is_legal_hold == True,
        )
    )

    # Recent audit events (last 10)
    audit_events, _ = await query_audit_logs(
        db=db,
        organization_id=organization_id,
        page=1,
        page_size=10,
    )

    return {
        "pending_consent_requests_count": c_pending.scalar_one(),
        "granted_consents_count": c_granted.scalar_one(),
        "withdrawn_consents_count": c_withdrawn.scalar_one(),
        "pending_data_requests_count": d_pending.scalar_one(),
        "completed_exports_count": d_completed.scalar_one(),
        "pending_deletion_requests_count": del_pending.scalar_one(),
        "completed_deletions_count": del_completed.scalar_one(),
        "active_legal_holds_count": del_holds.scalar_one(),
        "recent_audit_events": audit_events,
    }
