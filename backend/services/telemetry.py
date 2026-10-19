from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models import Job, JobSkillEvidence, Source, TaxonomySkill, LifecycleStatus

class TelemetryEngine:
    """
    Computes market telemetry, skill share percentages, company breadth,
    and 30-day period-over-period trend analysis with data quality safeguards.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_market_telemetry(self, category: Optional[str] = None, include_demo: bool = False) -> Dict[str, Any]:
        # 1. Inspect source health for data quality warnings
        sources_stmt = select(Source)
        sources = (await self.session.execute(sources_stmt)).scalars().all()
        
        data_quality_warnings = []
        for src in sources:
            if src.health_status == "DEGRADED":
                data_quality_warnings.append(
                    f"Source '{src.source_id}' is degraded ({src.last_error or 'Network anomaly'}). Telemetry counts may undercount live openings."
                )

        # 2. Query active jobs with snapshots and source
        jobs_stmt = select(Job).options(
            selectinload(Job.skills),
            selectinload(Job.snapshots),
            selectinload(Job.source),
        ).where(Job.lifecycle_status == LifecycleStatus.ACTIVE.value)

        if not include_demo:
            jobs_stmt = jobs_stmt.where(Job.is_demo == False)

        if category:
            jobs_stmt = jobs_stmt.where(Job.canonical_category.ilike(f"%{category}%"))

        jobs = (await self.session.execute(jobs_stmt)).scalars().all()
        total_eligible_jobs = len(jobs)
        distinct_sources = {j.source_id for j in jobs if j.source_id}

        if total_eligible_jobs == 0:
            return {
                "total_eligible_jobs": 0,
                "denominator_count": 0,
                "source_coverage_count": len(distinct_sources),
                "newly_observed_cohort_total": 0,
                "data_quality_warnings": data_quality_warnings,
                "skills_telemetry": [],
            }

        # 3. Aggregate skill frequencies, requirement levels, company breadth, and discovery cohorts
        now = datetime.now(timezone.utc)
        thirty_days_ago = now - timedelta(days=30)
        sixty_days_ago = now - timedelta(days=60)

        skill_jobs_map = defaultdict(set)
        skill_companies_map = defaultdict(set)
        skill_req_counts = defaultdict(lambda: {"required": 0, "preferred": 0, "mentioned": 0})
        
        # Newly observed cohort in last 30 days (first_seen_at)
        skill_newly_observed_cohort = defaultdict(set)
        newly_observed_jobs = set()

        for job in jobs:
            company_id = job.source.company_id if job.source else "tech"
            first_seen = job.first_seen_at.replace(tzinfo=timezone.utc) if job.first_seen_at.tzinfo is None else job.first_seen_at

            is_newly_observed = first_seen >= thirty_days_ago
            if is_newly_observed:
                newly_observed_jobs.add(job.job_id)

            for s in job.latest_skills:
                skill_id = s.skill_id
                skill_jobs_map[skill_id].add(job.job_id)
                skill_companies_map[skill_id].add(company_id)
                skill_req_counts[skill_id][s.requirement_type] += 1

                if is_newly_observed:
                    skill_newly_observed_cohort[skill_id].add(job.job_id)

        # 4. Check historical snapshot baseline (Window B: 30-60 days ago) for genuine market trend
        from backend.db.models import JobSnapshot, JobSkillEvidence
        prior_snapshots_stmt = select(JobSnapshot).where(
            JobSnapshot.observed_at >= sixty_days_ago,
            JobSnapshot.observed_at < thirty_days_ago,
        )
        prior_snapshots = (await self.session.execute(prior_snapshots_stmt)).scalars().all()
        has_prior_baseline = len(prior_snapshots) >= 10

        prior_skill_shares: Dict[str, float] = {}
        if has_prior_baseline:
            prior_snapshot_ids = [s.snapshot_id for s in prior_snapshots]
            prior_jobs_count = len({s.job_id for s in prior_snapshots})
            if prior_jobs_count > 0:
                prior_evidence_stmt = select(JobSkillEvidence.skill_id, JobSkillEvidence.job_id).where(
                    JobSkillEvidence.snapshot_id.in_(prior_snapshot_ids)
                )
                prior_evidence = (await self.session.execute(prior_evidence_stmt)).all()
                prior_skill_jobs = defaultdict(set)
                for s_id, j_id in prior_evidence:
                    prior_skill_jobs[s_id].add(j_id)
                for s_id, j_ids in prior_skill_jobs.items():
                    prior_skill_shares[s_id] = (len(j_ids) / prior_jobs_count) * 100.0
        else:
            data_quality_warnings.append(
                "Historical 30-day market demand shift requires complete snapshots across prior 30d window (>=60d total history). Exposing newly observed discovery cohort instead."
            )

        # Load skill metadata names
        tax_skills = (await self.session.execute(select(TaxonomySkill))).scalars().all()
        skill_meta = {s.skill_id: (s.skill_name, s.category) for s in tax_skills}

        telemetry_records = []
        for skill_id, job_ids in skill_jobs_map.items():
            count = len(job_ids)
            skill_name, cat = skill_meta.get(skill_id, (skill_id.upper(), "Technical"))
            skill_share = round((count / total_eligible_jobs) * 100, 1)
            breadth = len(skill_companies_map[skill_id])
            cohort_count = len(skill_newly_observed_cohort[skill_id])

            # Period delta is only computed if genuine historical snapshots exist in prior window
            period_delta = None
            if has_prior_baseline:
                if skill_id in prior_skill_shares:
                    period_delta = round(skill_share - prior_skill_shares[skill_id], 1)
                else:
                    period_delta = round(skill_share, 1)

            telemetry_records.append({
                "skill_id": skill_id,
                "skill_name": skill_name,
                "category": cat,
                "job_count": count,
                "skill_share_pct": skill_share,
                "company_breadth": breadth,
                "demand_breakdown": skill_req_counts[skill_id],
                "newly_observed_cohort_count": cohort_count,
                "period_over_period_delta_pct": period_delta,
            })

        # Sort by total job count descending
        telemetry_records.sort(key=lambda x: x["job_count"], reverse=True)

        return {
            "total_eligible_jobs": total_eligible_jobs,
            "denominator_count": total_eligible_jobs,
            "source_coverage_count": len(distinct_sources),
            "newly_observed_cohort_total": len(newly_observed_jobs),
            "data_quality_warnings": data_quality_warnings,
            "skills_telemetry": telemetry_records,
        }
