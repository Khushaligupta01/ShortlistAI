"""
Performance & Reliability Benchmark Suite for ShortlistAI (Phase 9 Verification).

Measures:
1. Dashboard KPI Aggregation Response Time (Target: < 300ms)
2. Candidate Multi-Attribute Search & Filter Response Time (Target: < 500ms)
3. Deterministic Candidate Scoring Execution Time (Target: < 50ms)

Usage:
    python scripts/benchmark_performance.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.ai.schemas import CriterionEvidenceItem
from app.core.config import settings
from app.db.base import Base
from app.main import app
from app.models.candidate import Candidate
from app.models.scorecard import Scorecard, ScorecardCriterion
from app.services.scoring_engine_service import ScoringEngine


engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def calculate_stats(latencies_ms: List[float]) -> dict:
    if not latencies_ms:
        return {}
    sorted_l = sorted(latencies_ms)
    n = len(sorted_l)
    return {
        "count": n,
        "mean_ms": round(sum(sorted_l) / n, 2),
        "min_ms": round(sorted_l[0], 2),
        "max_ms": round(sorted_l[-1], 2),
        "p50_ms": round(sorted_l[int(n * 0.50)], 2),
        "p95_ms": round(sorted_l[min(int(n * 0.95), n - 1)], 2),
        "p99_ms": round(sorted_l[min(int(n * 0.99), n - 1)], 2),
    }


async def benchmark() -> None:
    print("================================================================")
    print("       ShortlistAI Performance & Reliability Benchmark          ")
    print("================================================================\n")

    # 1. Login to obtain demo recruiter JWT
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://benchmark") as client:
        login_res = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "recruiter@techrecruit.com",
                "password": settings.SEED_RECRUITER_PASSWORD,
            },
        )
        if login_res.status_code != 200:
            print(f"[-] Authentication failed: {login_res.status_code} {login_res.text}")
            print("[-] Please ensure `python scripts/seed.py` has been executed first.")
            return

        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("[+] Authenticated as Alice Recruiter (recruiter@techrecruit.com)")

        # -------------------------------------------------------------
        # Benchmark 1: Dashboard KPI Aggregation (Target: < 300ms)
        # -------------------------------------------------------------
        print("\n[Benchmark 1/3] Dashboard KPI Aggregation (GET /api/v1/recruiter/metrics)")
        kpi_latencies = []
        # Warmup
        await client.get("/api/v1/recruiter/metrics", headers=headers)

        for _ in range(30):
            t0 = time.perf_counter()
            res = await client.get("/api/v1/recruiter/metrics", headers=headers)
            elapsed = (time.perf_counter() - t0) * 1000.0
            assert res.status_code == 200
            kpi_latencies.append(elapsed)

        kpi_stats = calculate_stats(kpi_latencies)
        print(f"  Iterations: 30")
        print(f"  Mean Latency: {kpi_stats['mean_ms']} ms")
        print(f"  P50 Latency:  {kpi_stats['p50_ms']} ms")
        print(f"  P95 Latency:  {kpi_stats['p95_ms']} ms")
        print(f"  Target:       < 300.0 ms")
        passed_kpi = kpi_stats["p95_ms"] < 300.0
        print(f"  Status:       {'[PASS]' if passed_kpi else '[FAIL]'}")

        # -------------------------------------------------------------
        # Benchmark 2: Candidate Multi-Attribute Search & Filter (Target: < 500ms)
        # -------------------------------------------------------------
        print("\n[Benchmark 2/3] Candidate Multi-Attribute Search & Filter (GET /api/v1/candidates)")
        filter_latencies = []
        # Warmup
        await client.get(
            "/api/v1/candidates",
            headers=headers,
            params={"search": "Elena", "min_experience": 5.0, "sort_by": "experience", "sort_order": "desc"},
        )

        for _ in range(30):
            t0 = time.perf_counter()
            res = await client.get(
                "/api/v1/candidates",
                headers=headers,
                params={"search": "Elena", "min_experience": 5.0, "sort_by": "experience", "sort_order": "desc"},
            )
            elapsed = (time.perf_counter() - t0) * 1000.0
            assert res.status_code == 200
            filter_latencies.append(elapsed)

        filter_stats = calculate_stats(filter_latencies)
        print(f"  Iterations: 30")
        print(f"  Mean Latency: {filter_stats['mean_ms']} ms")
        print(f"  P50 Latency:  {filter_stats['p50_ms']} ms")
        print(f"  P95 Latency:  {filter_stats['p95_ms']} ms")
        print(f"  Target:       < 500.0 ms")
        passed_filter = filter_stats["p95_ms"] < 500.0
        print(f"  Status:       {'[PASS]' if passed_filter else '[FAIL]'}")

        # -------------------------------------------------------------
        # Benchmark 3: Deterministic Candidate Scoring Execution (Target: < 50ms)
        # -------------------------------------------------------------
        print("\n[Benchmark 3/3] Deterministic Candidate Scoring Execution")
        scorer = ScoringEngine()

        bench_cand = Candidate(
            full_name="Bench Candidate",
            total_experience_years=8.0,
            location="San Francisco, CA",
            notice_period_days=30,
        )
        bench_sc = Scorecard(
            version_number=1,
            total_weight=100,
            scoring_config={
                "experience": 30,
                "must_have_skills": 40,
                "nice_to_have_skills": 15,
                "location": 10,
                "notice_period": 5,
            },
        )
        c1_id = "c1000000-0000-0000-0000-000000000001"
        c2_id = "c2000000-0000-0000-0000-000000000002"
        c3_id = "c3000000-0000-0000-0000-000000000003"
        c4_id = "c4000000-0000-0000-0000-000000000004"
        c5_id = "c5000000-0000-0000-0000-000000000005"

        crit1 = ScorecardCriterion(id=c1_id, criterion_type="experience", criterion_name="8+ yrs Experience", label="Experience", weight=30, is_mandatory=True)
        crit2 = ScorecardCriterion(id=c2_id, criterion_type="must_have_skills", criterion_name="Java & Spring Boot", label="Skills", weight=40, is_mandatory=True)
        crit3 = ScorecardCriterion(id=c3_id, criterion_type="nice_to_have_skills", criterion_name="Kafka streaming", label="Kafka", weight=15, is_mandatory=False)
        crit4 = ScorecardCriterion(id=c4_id, criterion_type="location", criterion_name="San Francisco", label="Location", weight=10, is_mandatory=False)
        crit5 = ScorecardCriterion(id=c5_id, criterion_type="notice_period", criterion_name="30 days", label="Notice", weight=5, is_mandatory=False)
        bench_sc.criteria = [crit1, crit2, crit3, crit4, crit5]

        sample_evidence = [
            CriterionEvidenceItem(criterion_id=c1_id, criterion_name="8+ yrs Experience", match_status="MATCHED", evidence_text="8.5 years of experience", confidence=0.95),
            CriterionEvidenceItem(criterion_id=c2_id, criterion_name="Java & Spring Boot", match_status="MATCHED", evidence_text="Senior Java developer building Spring Boot APIs", confidence=0.9),
            CriterionEvidenceItem(criterion_id=c3_id, criterion_name="Kafka streaming", match_status="PARTIAL", evidence_text="Kafka producer experience", confidence=0.75),
            CriterionEvidenceItem(criterion_id=c4_id, criterion_name="San Francisco", match_status="MATCHED", evidence_text="Based in San Francisco, CA", confidence=0.99),
            CriterionEvidenceItem(criterion_id=c5_id, criterion_name="30 days", match_status="MATCHED", evidence_text="30 days notice", confidence=0.9),
        ]

        scoring_latencies = []
        for _ in range(500):
            t0 = time.perf_counter()
            score_out = scorer.compute_scores(bench_cand, bench_sc, sample_evidence)
            elapsed = (time.perf_counter() - t0) * 1000.0
            scoring_latencies.append(elapsed)

        scoring_stats = calculate_stats(scoring_latencies)
        print(f"  Iterations: 500")
        print(f"  Mean Latency: {scoring_stats['mean_ms']} ms")
        print(f"  P50 Latency:  {scoring_stats['p50_ms']} ms")
        print(f"  P95 Latency:  {scoring_stats['p95_ms']} ms")
        print(f"  Target:       < 50.0 ms")
        passed_scoring = scoring_stats["p95_ms"] < 50.0
        print(f"  Status:       {'[PASS]' if passed_scoring else '[FAIL]'}")

        # Summary
        print("\n================================================================")
        print("                      Benchmark Summary                         ")
        print("================================================================")
        all_passed = passed_kpi and passed_filter and passed_scoring
        print(f"  Dashboard KPI Aggregation:         {kpi_stats['p95_ms']} ms (Target: < 300ms) -> {'PASSED' if passed_kpi else 'FAILED'}")
        print(f"  Candidate Multi-Attribute Search:  {filter_stats['p95_ms']} ms (Target: < 500ms) -> {'PASSED' if passed_filter else 'FAILED'}")
        print(f"  Deterministic Scoring Engine:      {scoring_stats['p95_ms']} ms (Target: < 50ms)  -> {'PASSED' if passed_scoring else 'FAILED'}")
        print(f"  Overall Verification Gate:         {'ALL GATES PASSED' if all_passed else 'GATE FAILED'}")
        print("================================================================\n")


if __name__ == "__main__":
    asyncio.run(benchmark())
