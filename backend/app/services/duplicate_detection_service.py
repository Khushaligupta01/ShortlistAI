from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate import Candidate
from app.models.resume import Resume


@dataclass
class DuplicateMatchResult:
    is_duplicate: bool
    duplicate_type: str | None  # "exact_file", "confirmed_candidate", "potential_candidate", "similar_content"
    existing_resume_id: uuid.UUID | None
    existing_candidate_id: uuid.UUID | None
    detection_method: str | None
    confidence: float
    details: Dict[str, Any]


class DuplicateDetectionService:
    """Multi-level duplicate detection for resumes and candidates."""

    @staticmethod
    def normalize_email(email: str | None) -> str | None:
        if not email:
            return None
        cleaned = email.strip().lower()
        return cleaned if "@" in cleaned else None

    @staticmethod
    def normalize_phone(phone: str | None) -> str | None:
        if not phone:
            return None
        # Extract digits
        digits = re.sub(r"\D", "", phone)
        if len(digits) < 7:
            return None
        # Normalize North American 11-digit numbers starting with 1
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        return digits

    async def check_exact_file_duplicate(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        file_hash: str,
        exclude_resume_id: Optional[uuid.UUID] = None,
    ) -> DuplicateMatchResult:
        """Level 1: Exact SHA-256 file duplicate check."""
        query = select(Resume).where(
            Resume.organization_id == organization_id,
            Resume.file_hash == file_hash,
        )
        if exclude_resume_id:
            query = query.where(Resume.id != exclude_resume_id)

        result = await db.execute(query.limit(1))
        existing_resume = result.scalars().first()

        if existing_resume:
            return DuplicateMatchResult(
                is_duplicate=True,
                duplicate_type="exact_file",
                existing_resume_id=existing_resume.id,
                existing_candidate_id=existing_resume.candidate_id,
                detection_method="sha256_hash",
                confidence=1.0,
                details={
                    "file_hash": file_hash,
                    "original_file_name": existing_resume.file_name,
                    "existing_resume_id": str(existing_resume.id),
                    "detected_at": datetime.now(timezone.utc).isoformat(),
                },
            )

        return DuplicateMatchResult(
            is_duplicate=False,
            duplicate_type=None,
            existing_resume_id=None,
            existing_candidate_id=None,
            detection_method=None,
            confidence=0.0,
            details={},
        )

    async def check_candidate_match(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        email: str | None,
        phone: str | None,
    ) -> DuplicateMatchResult:
        """Level 2: Potential candidate duplicate check using email and phone."""
        norm_email = self.normalize_email(email)
        norm_phone = self.normalize_phone(phone)

        if not norm_email and not norm_phone:
            return DuplicateMatchResult(
                is_duplicate=False,
                duplicate_type=None,
                existing_resume_id=None,
                existing_candidate_id=None,
                detection_method=None,
                confidence=0.0,
                details={},
            )

        # 1. Exact email match in organization -> Confirmed candidate match
        if norm_email:
            q_email = select(Candidate).where(
                Candidate.organization_id == organization_id,
                Candidate.email.ilike(norm_email),
            ).limit(1)
            res_email = await db.execute(q_email)
            cand_by_email = res_email.scalars().first()
            if cand_by_email:
                return DuplicateMatchResult(
                    is_duplicate=True,
                    duplicate_type="confirmed_candidate",
                    existing_resume_id=None,
                    existing_candidate_id=cand_by_email.id,
                    detection_method="normalized_email",
                    confidence=0.98,
                    details={
                        "matched_email": norm_email,
                        "candidate_id": str(cand_by_email.id),
                        "candidate_name": cand_by_email.full_name,
                        "detected_at": datetime.now(timezone.utc).isoformat(),
                    },
                )

        # 2. Exact phone match in organization -> Potential candidate duplicate
        if norm_phone:
            # Query candidates in the org whose phone matches when cleaned
            q_candidates = select(Candidate).where(
                Candidate.organization_id == organization_id,
                Candidate.phone.is_not(None),
            )
            res_cands = await db.execute(q_candidates)
            for c in res_cands.scalars().all():
                if self.normalize_phone(c.phone) == norm_phone:
                    return DuplicateMatchResult(
                        is_duplicate=True,
                        duplicate_type="potential_candidate",
                        existing_resume_id=None,
                        existing_candidate_id=c.id,
                        detection_method="normalized_phone",
                        confidence=0.80,
                        details={
                            "matched_phone": norm_phone,
                            "candidate_id": str(c.id),
                            "candidate_name": c.full_name,
                            "detected_at": datetime.now(timezone.utc).isoformat(),
                            "action_recommended": "recruiter_review",
                        },
                    )

        return DuplicateMatchResult(
            is_duplicate=False,
            duplicate_type=None,
            existing_resume_id=None,
            existing_candidate_id=None,
            detection_method=None,
            confidence=0.0,
            details={},
        )

    def calculate_text_similarity(self, text_a: str, text_b: str) -> float:
        """Calculate Jaccard word-ngram similarity between two normalized texts."""
        words_a = set(re.findall(r"\b[a-zA-Z0-9+#.]{3,}\b", text_a.lower()))
        words_b = set(re.findall(r"\b[a-zA-Z0-9+#.]{3,}\b", text_b.lower()))

        if not words_a or not words_b:
            return 0.0

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union if union > 0 else 0.0

    async def check_content_similarity(
        self,
        db: AsyncSession,
        organization_id: uuid.UUID,
        normalized_text: str,
        threshold: float = 0.88,
        exclude_resume_id: Optional[uuid.UUID] = None,
    ) -> DuplicateMatchResult:
        """Level 3: Resume text content similarity check."""
        if not normalized_text or len(normalized_text) < 100:
            return DuplicateMatchResult(
                is_duplicate=False,
                duplicate_type=None,
                existing_resume_id=None,
                existing_candidate_id=None,
                detection_method=None,
                confidence=0.0,
                details={},
            )

        # Retrieve recent parsed resumes from same organization
        q = select(Resume).where(
            Resume.organization_id == organization_id,
            Resume.normalized_text.is_not(None),
        )
        if exclude_resume_id:
            q = q.where(Resume.id != exclude_resume_id)

        res = await db.execute(q.limit(100))
        for existing in res.scalars().all():
            if existing.normalized_text:
                score = self.calculate_text_similarity(normalized_text, existing.normalized_text)
                if score >= threshold:
                    return DuplicateMatchResult(
                        is_duplicate=True,
                        duplicate_type="similar_content",
                        existing_resume_id=existing.id,
                        existing_candidate_id=existing.candidate_id,
                        detection_method="jaccard_text_similarity",
                        confidence=round(score, 3),
                        details={
                            "similarity_score": round(score, 3),
                            "existing_resume_id": str(existing.id),
                            "existing_candidate_id": str(existing.candidate_id) if existing.candidate_id else None,
                            "detected_at": datetime.now(timezone.utc).isoformat(),
                        },
                    )

        return DuplicateMatchResult(
            is_duplicate=False,
            duplicate_type=None,
            existing_resume_id=None,
            existing_candidate_id=None,
            detection_method=None,
            confidence=0.0,
            details={},
        )


duplicate_detector = DuplicateDetectionService()
