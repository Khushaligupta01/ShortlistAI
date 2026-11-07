from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.provider import LLMExtractionError, LLMProviderUnavailableError
from app.ai.jd_extraction_service import JDExtractionService
from app.ai.provider_factory import get_provider
from app.ai.schemas import (
    DEFAULT_SCORING_CONFIG,
    JDExtractionResult,
    ScoringConfig,
)
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.audit import AuditLog
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.repositories.requisition_repository import RequisitionRepository
from app.repositories.scorecard_repository import ScorecardRepository
from app.schemas.requisition import (
    CriterionCreate,
    ScorecardCreate,
    ScorecardResponse,
    ScorecardUpdate,
)


class ScorecardService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sc_repo = ScorecardRepository(db)
        self.req_repo = RequisitionRepository(db)

    # ──────────────────────────────────────────────────────────────────────
    # AI Extraction
    # ──────────────────────────────────────────────────────────────────────

    async def extract_requirements(
        self,
        jd_text: str,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> JDExtractionResult:
        """
        Call the AI provider to extract structured requirements from a JD.
        Raises LLMExtractionError if provider fails.
        Does NOT save anything — returns extraction result for frontend review.
        """
        provider = get_provider()
        service = JDExtractionService(provider)

        try:
            result = await service.extract(jd_text)
        except (LLMExtractionError, LLMProviderUnavailableError):
            raise  # Let API layer handle with appropriate HTTP status

        # Audit the AI call (best-effort)
        try:
            self.db.add(AuditLog(
                organization_id=org_id,
                actor_user_id=user_id,
                event_type="JD_EXTRACTION_COMPLETED",
                resource_type="jd_text",
                payload_json={
                    "skills_extracted": len(result.must_have_skills),
                    "warnings": len(result.extraction_warnings),
                },
            ))
            await self.db.commit()
        except Exception:
            pass  # audit failure must not fail extraction

        return result

    # ──────────────────────────────────────────────────────────────────────
    # Scorecard CRUD
    # ──────────────────────────────────────────────────────────────────────

    async def create(
        self,
        requisition_id: uuid.UUID,
        data: ScorecardCreate,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Scorecard:
        # Verify requisition exists and belongs to org
        req = await self.req_repo.get_by_id_and_org(requisition_id, org_id)
        if not req:
            raise NotFoundError("Requisition not found")

        # Block creation if an active (non-superseded) scorecard already exists
        existing = await self.sc_repo.get_active_for_requisition(requisition_id)
        if existing and existing.status == "approved":
            raise ConflictError(
                "Requisition already has an approved scorecard. "
                "Use duplicate to create a new version."
            )

        version = await self.sc_repo.get_latest_version_number(requisition_id) + 1

        scoring_cfg = (
            data.scoring_config.model_dump() if data.scoring_config else DEFAULT_SCORING_CONFIG
        )
        _validate_scoring_config(scoring_cfg)

        total_weight = _compute_total_weight(data.criteria)

        scorecard = Scorecard(
            requisition_id=requisition_id,
            version_number=version,
            status="draft",
            experience_min=data.experience_min,
            experience_max=data.experience_max,
            location=data.location,
            max_notice_days=data.max_notice_days,
            scoring_config=scoring_cfg,
            total_weight=total_weight,
            jd_extraction_json=data.jd_extraction_json,
        )
        await self.sc_repo.create(scorecard)

        for i, c in enumerate(data.criteria):
            criterion = _build_criterion(scorecard.id, c, i)
            self.db.add(criterion)

        self.db.add(AuditLog(
            organization_id=org_id,
            actor_user_id=user_id,
            event_type="SCORECARD_CREATED",
            resource_type="scorecard",
            resource_id=scorecard.id,
            payload_json={"version": version, "requisition_id": str(requisition_id)},
        ))
        await self.db.commit()
        return await self.sc_repo.get_by_id(scorecard.id)

    async def get(
        self, requisition_id: uuid.UUID, org_id: uuid.UUID
    ) -> Scorecard:
        req = await self.req_repo.get_by_id_and_org(requisition_id, org_id)
        if not req:
            raise NotFoundError("Requisition not found")

        scorecard = await self.sc_repo.get_active_for_requisition(requisition_id)
        if not scorecard:
            raise NotFoundError("No scorecard found for this requisition")
        return scorecard

    async def update(
        self,
        requisition_id: uuid.UUID,
        data: ScorecardUpdate,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Scorecard:
        req = await self.req_repo.get_by_id_and_org(requisition_id, org_id)
        if not req:
            raise NotFoundError("Requisition not found")

        scorecard = await self.sc_repo.get_active_for_requisition(requisition_id)
        if not scorecard:
            raise NotFoundError("No scorecard found for this requisition")

        if scorecard.status == "approved":
            raise ConflictError(
                "Cannot edit an approved scorecard. Use duplicate to create a new version."
            )

        # Apply updates
        if data.experience_min is not None:
            scorecard.experience_min = data.experience_min
        if data.experience_max is not None:
            scorecard.experience_max = data.experience_max
        if data.location is not None:
            scorecard.location = data.location
        if data.max_notice_days is not None:
            scorecard.max_notice_days = data.max_notice_days
        if data.scoring_config is not None:
            scoring_cfg = data.scoring_config.model_dump()
            _validate_scoring_config(scoring_cfg)
            scorecard.scoring_config = scoring_cfg
        if data.criteria is not None:
            total_weight = _compute_total_weight(data.criteria)
            scorecard.total_weight = total_weight
            scorecard.criteria = [
                _build_criterion(scorecard.id, c, i)
                for i, c in enumerate(data.criteria)
            ]

        self.db.add(AuditLog(
            organization_id=org_id,
            actor_user_id=user_id,
            event_type="SCORECARD_UPDATED",
            resource_type="scorecard",
            resource_id=scorecard.id,
            payload_json={"requisition_id": str(requisition_id)},
        ))
        await self.db.commit()
        return await self.sc_repo.get_by_id(scorecard.id)

    async def approve(
        self,
        requisition_id: uuid.UUID,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Scorecard:
        req = await self.req_repo.get_by_id_and_org(requisition_id, org_id)
        if not req:
            raise NotFoundError("Requisition not found")

        scorecard = await self.sc_repo.get_active_for_requisition(requisition_id)
        if not scorecard:
            raise NotFoundError("No scorecard found for this requisition")

        if scorecard.status == "approved":
            raise ConflictError("Scorecard is already approved")

        if not scorecard.criteria:
            raise ValidationError("Cannot approve a scorecard with no criteria")

        # Validate scoring configuration total and bounds
        if not scorecard.scoring_config:
            raise ValidationError("Scorecard must have a valid scoring configuration to approve")
        _validate_scoring_config(scorecard.scoring_config)

        # Validate criteria weights
        for c in scorecard.criteria:
            if c.weight < 0:
                raise ValidationError(f"Criterion '{c.label}' cannot have a negative weight")

        scorecard.status = "approved"
        scorecard.approved_at = datetime.now(timezone.utc)

        # Also activate the requisition
        req.status = "active"

        self.db.add(AuditLog(
            organization_id=org_id,
            actor_user_id=user_id,
            event_type="SCORECARD_APPROVED",
            resource_type="scorecard",
            resource_id=scorecard.id,
            payload_json={
                "version": scorecard.version_number,
                "requisition_id": str(requisition_id),
            },
        ))
        await self.db.commit()
        return await self.sc_repo.get_by_id(scorecard.id)

    async def duplicate(
        self,
        requisition_id: uuid.UUID,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Scorecard:
        """Create a new draft version from the current approved scorecard."""
        req = await self.req_repo.get_by_id_and_org(requisition_id, org_id)
        if not req:
            raise NotFoundError("Requisition not found")

        existing = await self.sc_repo.get_active_for_requisition(requisition_id)
        if not existing:
            raise NotFoundError("No scorecard found to duplicate")

        version = await self.sc_repo.get_latest_version_number(requisition_id) + 1
        new_scorecard = Scorecard(
            requisition_id=requisition_id,
            version_number=version,
            status="draft",
            experience_min=existing.experience_min,
            experience_max=existing.experience_max,
            location=existing.location,
            max_notice_days=existing.max_notice_days,
            scoring_config=existing.scoring_config,
            total_weight=existing.total_weight,
            jd_extraction_json=existing.jd_extraction_json,
        )
        self.db.add(new_scorecard)
        await self.db.flush()

        for i, c in enumerate(existing.criteria):
            crit = ScorecardCriterion(
                scorecard_id=new_scorecard.id,
                criterion_type=c.criterion_type,
                criterion_name=c.criterion_name,
                normalized_name=c.normalized_name,
                label=c.label,
                description=c.description,
                weight=c.weight,
                is_mandatory=c.is_mandatory,
                evidence_from_jd=c.evidence_from_jd,
                display_order=i,
                config_json=c.config_json,
            )
            self.db.add(crit)

        self.db.add(AuditLog(
            organization_id=org_id,
            actor_user_id=user_id,
            event_type="SCORECARD_DUPLICATED",
            resource_type="scorecard",
            resource_id=new_scorecard.id,
            payload_json={
                "version": version,
                "source_version": existing.version_number,
            },
        ))
        await self.db.commit()
        return await self.sc_repo.get_by_id(new_scorecard.id)


# ──────────────────────────────────────────────────────────────────────────
# Private helpers
# ──────────────────────────────────────────────────────────────────────────

def _validate_scoring_config(cfg: dict) -> None:
    try:
        ScoringConfig(**cfg)
    except Exception as e:
        raise ValidationError(f"Invalid scoring configuration: {e}")


def _compute_total_weight(criteria: list[CriterionCreate]) -> int:
    return sum(c.weight for c in criteria)


def _build_criterion(
    scorecard_id: uuid.UUID, c: CriterionCreate, order: int
) -> ScorecardCriterion:
    return ScorecardCriterion(
        scorecard_id=scorecard_id,
        criterion_type=c.criterion_type,
        criterion_name=c.criterion_name,
        normalized_name=c.normalized_name or c.criterion_name.lower().replace(" ", "_"),
        label=c.label,
        description=c.description,
        weight=c.weight,
        is_mandatory=c.is_mandatory,
        evidence_from_jd=c.evidence_from_jd,
        display_order=order,
        config_json=getattr(c, "config_json", None),
    )
