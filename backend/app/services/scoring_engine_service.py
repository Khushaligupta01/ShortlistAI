from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, List, Optional

from app.ai.schemas import CriterionEvidenceItem
from app.models.candidate import Candidate
from app.models.scorecard import Scorecard, ScorecardCriterion

logger = logging.getLogger("shortlistai.scoring_engine")


@dataclass
class CriterionScoreResult:
    criterion_id: str
    criterion_type: str
    criterion_name: str
    weight: float
    awarded_points: float
    maximum_points: float
    match_status: str
    confidence: float
    evidence_text: Optional[str]
    source_reference: Optional[str]
    explanation: Optional[str]
    flags: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ScoringResult:
    raw_score: float
    normalized_score: float
    maximum_score: float
    evidence_coverage: float
    confidence_level: str  # HIGH, NEEDS_REVIEW, LOW
    average_confidence: float
    criteria_results: List[CriterionScoreResult]
    category_scores: Dict[str, Dict[str, float]]
    breakdown_json: Dict[str, Any]


class ScoringEngine:
    """
    Pure deterministic scoring engine for ShortlistAI.
    Calculates candidate scores strictly from approved scorecard criteria
    and verified evidence items. Contains zero LLM scoring logic.
    """

    def compute_scores(
        self,
        candidate: Candidate,
        scorecard: Scorecard,
        evidence_items: List[CriterionEvidenceItem],
    ) -> ScoringResult:
        criteria = scorecard.criteria or []
        evidence_by_id = {item.criterion_id: item for item in evidence_items}

        total_weight = float(scorecard.total_weight or 100)
        scoring_cfg = scorecard.scoring_config or {
            "experience": 30,
            "must_have_skills": 40,
            "notice_period": 15,
            "location": 10,
            "nice_to_have_skills": 5,
        }

        # Group criteria by type
        must_have_criteria = [c for c in criteria if c.criterion_type == "must_have_skill"]
        nice_to_have_criteria = [c for c in criteria if c.criterion_type == "nice_to_have_skill"]
        exp_criteria = [c for c in criteria if c.criterion_type == "experience"]
        notice_criteria = [c for c in criteria if c.criterion_type == "notice_period"]
        location_criteria = [c for c in criteria if c.criterion_type == "location"]

        criteria_results: List[CriterionScoreResult] = []
        category_scores: Dict[str, Dict[str, float]] = {
            "experience": {"awarded": 0.0, "maximum": float(scoring_cfg.get("experience", 30))},
            "must_have_skills": {"awarded": 0.0, "maximum": float(scoring_cfg.get("must_have_skills", 40))},
            "notice_period": {"awarded": 0.0, "maximum": float(scoring_cfg.get("notice_period", 15))},
            "location": {"awarded": 0.0, "maximum": float(scoring_cfg.get("location", 10))},
            "nice_to_have_skills": {"awarded": 0.0, "maximum": float(scoring_cfg.get("nice_to_have_skills", 5))},
        }

        # -------------------------------------------------------------
        # 1. Experience (Category Weight: default 30)
        # -------------------------------------------------------------
        exp_weight = category_scores["experience"]["maximum"]
        if exp_criteria:
            c = exp_criteria[0]
            ev = evidence_by_id.get(str(c.id))
            res = self._score_experience(candidate, c, ev, exp_weight)
            criteria_results.append(res)
            category_scores["experience"]["awarded"] = res.awarded_points
        else:
            # Scorecard experience from fields directly if no explicit criterion
            res = self._score_experience_direct(candidate, scorecard, exp_weight)
            criteria_results.append(res)
            category_scores["experience"]["awarded"] = res.awarded_points

        # -------------------------------------------------------------
        # 2. Must-Have Skills (Category Weight: default 40)
        # -------------------------------------------------------------
        mh_weight = category_scores["must_have_skills"]["maximum"]
        if must_have_criteria:
            # Distribute category weight across must-have criteria
            per_skill_max = mh_weight / len(must_have_criteria)
            mh_awarded_total = 0.0
            for c in must_have_criteria:
                ev = evidence_by_id.get(str(c.id))
                res = self._score_must_have_skill(c, ev, per_skill_max)
                criteria_results.append(res)
                mh_awarded_total += res.awarded_points
            category_scores["must_have_skills"]["awarded"] = round(mh_awarded_total, 2)
        else:
            category_scores["must_have_skills"]["awarded"] = 0.0

        # -------------------------------------------------------------
        # 3. Notice Period (Category Weight: default 15)
        # -------------------------------------------------------------
        np_weight = category_scores["notice_period"]["maximum"]
        if notice_criteria:
            c = notice_criteria[0]
            ev = evidence_by_id.get(str(c.id))
            res = self._score_notice_period(candidate, c, ev, np_weight)
            criteria_results.append(res)
            category_scores["notice_period"]["awarded"] = res.awarded_points
        else:
            res = self._score_notice_period_direct(candidate, scorecard, np_weight)
            criteria_results.append(res)
            category_scores["notice_period"]["awarded"] = res.awarded_points

        # -------------------------------------------------------------
        # 4. Location (Category Weight: default 10)
        # -------------------------------------------------------------
        loc_weight = category_scores["location"]["maximum"]
        if location_criteria:
            c = location_criteria[0]
            ev = evidence_by_id.get(str(c.id))
            res = self._score_location(candidate, c, ev, loc_weight)
            criteria_results.append(res)
            category_scores["location"]["awarded"] = res.awarded_points
        else:
            res = self._score_location_direct(candidate, scorecard, loc_weight)
            criteria_results.append(res)
            category_scores["location"]["awarded"] = res.awarded_points

        # -------------------------------------------------------------
        # 5. Nice-to-Have Skills (Category Weight: default 5)
        # -------------------------------------------------------------
        nth_weight = category_scores["nice_to_have_skills"]["maximum"]
        if nice_to_have_criteria:
            per_nth_max = nth_weight / len(nice_to_have_criteria)
            nth_awarded_total = 0.0
            for c in nice_to_have_criteria:
                ev = evidence_by_id.get(str(c.id))
                res = self._score_nice_to_have_skill(c, ev, per_nth_max)
                criteria_results.append(res)
                nth_awarded_total += res.awarded_points
            category_scores["nice_to_have_skills"]["awarded"] = round(nth_awarded_total, 2)
        else:
            category_scores["nice_to_have_skills"]["awarded"] = 0.0

        # -------------------------------------------------------------
        # 6. Overall Aggregation & Metrics
        # -------------------------------------------------------------
        raw_score = sum(cat["awarded"] for cat in category_scores.values())
        raw_score = max(0.0, min(100.0, round(raw_score, 2)))
        maximum_score = sum(cat["maximum"] for cat in category_scores.values())

        # Evidence Coverage: percentage of evaluated criteria with definitive evidence
        total_criteria_count = len(criteria_results)
        known_criteria_count = sum(
            1 for r in criteria_results if r.match_status in ("MATCHED", "PARTIAL", "NOT_MATCHED")
        )
        evidence_coverage = (
            round((known_criteria_count / total_criteria_count) * 100.0, 1)
            if total_criteria_count > 0
            else 100.0
        )

        # Normalized Score: provisional 0-100 score normalized by known applicable weights
        known_weights_sum = sum(
            r.maximum_points
            for r in criteria_results
            if r.match_status in ("MATCHED", "PARTIAL", "NOT_MATCHED")
        )
        if known_weights_sum > 0:
            normalized_score = round((raw_score / known_weights_sum) * 100.0, 2)
            normalized_score = max(0.0, min(100.0, normalized_score))
        else:
            normalized_score = raw_score

        # Average Confidence
        confidences = [r.confidence for r in criteria_results if r.confidence is not None]
        avg_confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0.80

        # Confidence Level & Flags
        has_conflicts = any(r.match_status == "CONFLICTING" or r.flags.get("conflict") for r in criteria_results)
        unknown_must_haves = any(
            r.criterion_type == "must_have_skill" and r.match_status == "UNKNOWN"
            for r in criteria_results
        )

        if avg_confidence < 0.50 or evidence_coverage < 50.0:
            confidence_level = "LOW"
        elif has_conflicts or unknown_must_haves or (0.50 <= avg_confidence < 0.80) or (50.0 <= evidence_coverage < 80.0):
            confidence_level = "NEEDS_REVIEW"
        elif avg_confidence >= 0.80 and evidence_coverage >= 80.0 and not has_conflicts:
            confidence_level = "HIGH"
        else:
            confidence_level = "LOW"

        breakdown_json = {
            "raw_score": raw_score,
            "normalized_score": normalized_score,
            "maximum_score": maximum_score,
            "evidence_coverage": evidence_coverage,
            "confidence_level": confidence_level,
            "average_confidence": avg_confidence,
            "category_scores": category_scores,
            "criteria_scores": [
                {
                    "criterion_id": r.criterion_id,
                    "criterion_type": r.criterion_type,
                    "criterion_name": r.criterion_name,
                    "awarded_points": r.awarded_points,
                    "maximum_points": r.maximum_points,
                    "match_status": r.match_status,
                    "confidence": r.confidence,
                    "evidence_text": r.evidence_text,
                    "source_reference": r.source_reference,
                    "explanation": r.explanation,
                }
                for r in criteria_results
            ],
        }

        return ScoringResult(
            raw_score=raw_score,
            normalized_score=normalized_score,
            maximum_score=maximum_score,
            evidence_coverage=evidence_coverage,
            confidence_level=confidence_level,
            average_confidence=avg_confidence,
            criteria_results=criteria_results,
            category_scores=category_scores,
            breakdown_json=breakdown_json,
        )

    # -----------------------------------------------------------------
    # Private Helper Scorers
    # -----------------------------------------------------------------

    def _score_experience(
        self,
        candidate: Candidate,
        criterion: ScorecardCriterion,
        ev: Optional[CriterionEvidenceItem],
        max_points: float,
    ) -> CriterionScoreResult:
        cfg = criterion.config_json or {}
        min_years = float(cfg.get("min_years") or cfg.get("experience_min") or 0.0)
        max_years = float(cfg.get("max_years") or cfg.get("experience_max") or 99.0)

        match_status = ev.match_status if ev else ("UNKNOWN" if candidate.total_experience_years is None else "MATCHED")
        confidence = ev.confidence if ev else 0.80
        evidence_text = ev.evidence_text if ev else None
        source_reference = ev.source_reference if ev else "Employment History"
        explanation = ev.explanation if ev else None

        if candidate.total_experience_years is None:
            return CriterionScoreResult(
                criterion_id=str(criterion.id),
                criterion_type="experience",
                criterion_name=criterion.criterion_name or "Experience",
                weight=max_points,
                awarded_points=0.0,
                maximum_points=max_points,
                match_status="UNKNOWN",
                confidence=0.50,
                evidence_text=None,
                source_reference=None,
                explanation="No verifiable total experience duration stated in resume.",
            )

        cand_years = float(candidate.total_experience_years)

        # Within or above range
        if cand_years >= min_years:
            awarded = max_points
            match_status = "MATCHED"
            explanation = f"Candidate experience of {cand_years:.1f} years meets or exceeds minimum {min_years} years."
        else:
            # Below minimum: deterministic proportional formula
            awarded = round(max_points * (cand_years / min_years), 2) if min_years > 0 else 0.0
            awarded = max(0.0, min(max_points, awarded))
            match_status = "PARTIAL"
            explanation = f"Candidate experience of {cand_years:.1f} years is below required minimum of {min_years} years (proportional points awarded)."

        return CriterionScoreResult(
            criterion_id=str(criterion.id),
            criterion_type="experience",
            criterion_name=criterion.criterion_name or "Experience",
            weight=max_points,
            awarded_points=awarded,
            maximum_points=max_points,
            match_status=match_status,
            confidence=confidence,
            evidence_text=evidence_text or f"Total experience: {cand_years:.1f} years",
            source_reference=source_reference,
            explanation=explanation,
        )

    def _score_experience_direct(
        self,
        candidate: Candidate,
        scorecard: Scorecard,
        max_points: float,
    ) -> CriterionScoreResult:
        min_years = float(scorecard.experience_min or 0.0)
        if candidate.total_experience_years is None:
            return CriterionScoreResult(
                criterion_id="direct_experience",
                criterion_type="experience",
                criterion_name="Total Experience",
                weight=max_points,
                awarded_points=0.0,
                maximum_points=max_points,
                match_status="UNKNOWN",
                confidence=0.50,
                evidence_text=None,
                source_reference=None,
                explanation="No verifiable total experience duration stated in resume.",
            )

        cand_years = float(candidate.total_experience_years)
        if cand_years >= min_years:
            awarded = max_points
            match_status = "MATCHED"
            explanation = f"Candidate experience of {cand_years:.1f} years satisfies requirement of {min_years} years."
        else:
            awarded = round(max_points * (cand_years / min_years), 2) if min_years > 0 else 0.0
            match_status = "PARTIAL"
            explanation = f"Candidate experience of {cand_years:.1f} years is below required minimum of {min_years} years."

        return CriterionScoreResult(
            criterion_id="direct_experience",
            criterion_type="experience",
            criterion_name="Total Experience",
            weight=max_points,
            awarded_points=awarded,
            maximum_points=max_points,
            match_status=match_status,
            confidence=0.90,
            evidence_text=f"Total experience: {cand_years:.1f} years",
            source_reference="Employment History",
            explanation=explanation,
        )

    def _score_must_have_skill(
        self,
        criterion: ScorecardCriterion,
        ev: Optional[CriterionEvidenceItem],
        max_points: float,
    ) -> CriterionScoreResult:
        status = ev.match_status if ev else "NOT_MATCHED"
        confidence = ev.confidence if ev else 0.80

        if status == "MATCHED":
            awarded = round(max_points, 2)
        elif status == "PARTIAL":
            # Documented 50% partial credit rule for must-have skills with partial evidence
            awarded = round(max_points * 0.50, 2)
        elif status == "CONFLICTING":
            awarded = 0.0
        else:  # NOT_MATCHED or UNKNOWN
            awarded = 0.0

        return CriterionScoreResult(
            criterion_id=str(criterion.id),
            criterion_type="must_have_skill",
            criterion_name=criterion.criterion_name or criterion.label,
            weight=max_points,
            awarded_points=awarded,
            maximum_points=max_points,
            match_status=status,
            confidence=confidence,
            evidence_text=ev.evidence_text if ev else None,
            source_reference=ev.source_reference if ev else None,
            explanation=ev.explanation if ev else f"No evidence for {criterion.criterion_name}.",
            flags={"conflict": True} if status == "CONFLICTING" else {},
        )

    def _score_nice_to_have_skill(
        self,
        criterion: ScorecardCriterion,
        ev: Optional[CriterionEvidenceItem],
        max_points: float,
    ) -> CriterionScoreResult:
        status = ev.match_status if ev else "NOT_MATCHED"
        confidence = ev.confidence if ev else 0.80

        if status == "MATCHED":
            awarded = round(max_points, 2)
        elif status == "PARTIAL":
            awarded = round(max_points * 0.50, 2)
        else:
            awarded = 0.0

        return CriterionScoreResult(
            criterion_id=str(criterion.id),
            criterion_type="nice_to_have_skill",
            criterion_name=criterion.criterion_name or criterion.label,
            weight=max_points,
            awarded_points=awarded,
            maximum_points=max_points,
            match_status=status,
            confidence=confidence,
            evidence_text=ev.evidence_text if ev else None,
            source_reference=ev.source_reference if ev else None,
            explanation=ev.explanation if ev else f"Preferred skill {criterion.criterion_name} not found.",
        )

    def _score_notice_period(
        self,
        candidate: Candidate,
        criterion: ScorecardCriterion,
        ev: Optional[CriterionEvidenceItem],
        max_points: float,
    ) -> CriterionScoreResult:
        cfg = criterion.config_json or {}
        max_notice = cfg.get("max_notice_days") or 60

        if candidate.notice_period_days is None:
            return CriterionScoreResult(
                criterion_id=str(criterion.id),
                criterion_type="notice_period",
                criterion_name=criterion.criterion_name or "Notice Period",
                weight=max_points,
                awarded_points=0.0,
                maximum_points=max_points,
                match_status="UNKNOWN",
                confidence=0.50,
                evidence_text=None,
                source_reference=None,
                explanation="Notice period not explicitly stated in resume.",
            )

        cand_notice = candidate.notice_period_days
        if cand_notice <= max_notice:
            awarded = max_points
            match_status = "MATCHED"
            explanation = f"Notice period of {cand_notice} days is within maximum {max_notice} days."
        elif cand_notice <= max_notice * 1.5:
            # Deterministic partial credit if within 1.5x of threshold
            awarded = round(max_points * (max_notice / cand_notice), 2)
            match_status = "PARTIAL"
            explanation = f"Notice period of {cand_notice} days exceeds {max_notice} days (partial credit awarded)."
        else:
            awarded = 0.0
            match_status = "NOT_MATCHED"
            explanation = f"Notice period of {cand_notice} days exceeds maximum permissible limit."

        return CriterionScoreResult(
            criterion_id=str(criterion.id),
            criterion_type="notice_period",
            criterion_name=criterion.criterion_name or "Notice Period",
            weight=max_points,
            awarded_points=awarded,
            maximum_points=max_points,
            match_status=match_status,
            confidence=ev.confidence if ev else 0.90,
            evidence_text=ev.evidence_text if ev else f"Notice period: {cand_notice} days",
            source_reference=ev.source_reference if ev else "Candidate Profile",
            explanation=explanation,
        )

    def _score_notice_period_direct(
        self,
        candidate: Candidate,
        scorecard: Scorecard,
        max_points: float,
    ) -> CriterionScoreResult:
        max_notice = scorecard.max_notice_days or 60
        if candidate.notice_period_days is None:
            return CriterionScoreResult(
                criterion_id="direct_notice",
                criterion_type="notice_period",
                criterion_name="Notice Period",
                weight=max_points,
                awarded_points=0.0,
                maximum_points=max_points,
                match_status="UNKNOWN",
                confidence=0.50,
                evidence_text=None,
                source_reference=None,
                explanation="Notice period not explicitly stated in resume.",
            )

        cand_notice = candidate.notice_period_days
        if cand_notice <= max_notice:
            awarded = max_points
            match_status = "MATCHED"
            explanation = f"Notice period of {cand_notice} days is within maximum {max_notice} days."
        else:
            awarded = round(max_points * (max_notice / cand_notice), 2) if cand_notice <= max_notice * 1.5 else 0.0
            match_status = "PARTIAL" if awarded > 0 else "NOT_MATCHED"
            explanation = f"Notice period of {cand_notice} days exceeds maximum {max_notice} days."

        return CriterionScoreResult(
            criterion_id="direct_notice",
            criterion_type="notice_period",
            criterion_name="Notice Period",
            weight=max_points,
            awarded_points=awarded,
            maximum_points=max_points,
            match_status=match_status,
            confidence=0.90,
            evidence_text=f"Notice period: {cand_notice} days",
            source_reference="Candidate Profile",
            explanation=explanation,
        )

    def _score_location(
        self,
        candidate: Candidate,
        criterion: ScorecardCriterion,
        ev: Optional[CriterionEvidenceItem],
        max_points: float,
    ) -> CriterionScoreResult:
        cfg = criterion.config_json or {}
        req_loc = (cfg.get("location") or criterion.criterion_name or "").strip().lower()

        if not candidate.location:
            return CriterionScoreResult(
                criterion_id=str(criterion.id),
                criterion_type="location",
                criterion_name=criterion.criterion_name or "Location",
                weight=max_points,
                awarded_points=0.0,
                maximum_points=max_points,
                match_status="UNKNOWN",
                confidence=0.50,
                evidence_text=None,
                source_reference=None,
                explanation="Candidate location not stated in resume.",
            )

        cand_loc = candidate.location.strip().lower()
        if req_loc in cand_loc or cand_loc in req_loc or "remote" in cand_loc:
            awarded = max_points
            match_status = "MATCHED"
            explanation = f"Candidate location '{candidate.location}' matches required location."
        else:
            awarded = 0.0
            match_status = "NOT_MATCHED"
            explanation = f"Candidate location '{candidate.location}' does not match required location '{criterion.criterion_name}'."

        return CriterionScoreResult(
            criterion_id=str(criterion.id),
            criterion_type="location",
            criterion_name=criterion.criterion_name or "Location",
            weight=max_points,
            awarded_points=awarded,
            maximum_points=max_points,
            match_status=match_status,
            confidence=ev.confidence if ev else 0.90,
            evidence_text=ev.evidence_text if ev else f"Location: {candidate.location}",
            source_reference=ev.source_reference if ev else "Candidate Profile",
            explanation=explanation,
        )

    def _score_location_direct(
        self,
        candidate: Candidate,
        scorecard: Scorecard,
        max_points: float,
    ) -> CriterionScoreResult:
        req_loc = (scorecard.location or "").strip().lower()
        if not candidate.location:
            return CriterionScoreResult(
                criterion_id="direct_location",
                criterion_type="location",
                criterion_name="Location",
                weight=max_points,
                awarded_points=0.0,
                maximum_points=max_points,
                match_status="UNKNOWN",
                confidence=0.50,
                evidence_text=None,
                source_reference=None,
                explanation="Candidate location not stated in resume.",
            )

        cand_loc = candidate.location.strip().lower()
        if not req_loc or req_loc in cand_loc or cand_loc in req_loc or "remote" in cand_loc:
            awarded = max_points
            match_status = "MATCHED"
            explanation = f"Candidate location '{candidate.location}' matches required location."
        else:
            awarded = 0.0
            match_status = "NOT_MATCHED"
            explanation = f"Candidate location '{candidate.location}' does not match required location '{scorecard.location}'."

        return CriterionScoreResult(
            criterion_id="direct_location",
            criterion_type="location",
            criterion_name="Location",
            weight=max_points,
            awarded_points=awarded,
            maximum_points=max_points,
            match_status=match_status,
            confidence=0.90,
            evidence_text=f"Location: {candidate.location}",
            source_reference="Candidate Profile",
            explanation=explanation,
        )


scoring_engine = ScoringEngine()
