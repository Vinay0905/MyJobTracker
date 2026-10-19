from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models import Job, JobSkillEvidence, Source, TaxonomySkill, LifecycleStatus

def _as_utc(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

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
            if src.enabled and src.health_status == "DEGRADED":
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
                "has_prior_window": False,
                "prior_window_jobs": 0,
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

        # 4. 30-day delta: both windows use live (non-demo) jobs in the same sector.
        # Current window = jobs active now (latest snapshot skills).
        # Prior window = jobs already listed 30 days ago and still seen during days 30-60,
        # using the snapshot that was current 30 days ago.
        live_current_jobs = [j for j in jobs if not j.is_demo]
        current_skill_jobs = defaultdict(set)
        for job in live_current_jobs:
            for s in job.latest_skills:
                current_skill_jobs[s.skill_id].add(job.job_id)

        prior_stmt = select(Job).options(
            selectinload(Job.skills),
            selectinload(Job.snapshots),
        ).where(
            Job.is_demo == False,
            Job.first_seen_at < thirty_days_ago,
            Job.last_seen_at >= sixty_days_ago,
        )
        if category:
            prior_stmt = prior_stmt.where(Job.canonical_category.ilike(f"%{category}%"))
        prior_jobs = (await self.session.execute(prior_stmt)).scalars().all()

        prior_skill_jobs = defaultdict(set)
        prior_jobs_count = 0
        for job in prior_jobs:
            snaps_then = [s for s in job.snapshots if _as_utc(s.observed_at) < thirty_days_ago]
            if not snaps_then:
                continue
            snapshot_then = max(snaps_then, key=lambda s: _as_utc(s.observed_at)).snapshot_id
            prior_jobs_count += 1
            for s in job.skills:
                if s.snapshot_id == snapshot_then:
                    prior_skill_jobs[s.skill_id].add(job.job_id)

        has_prior_baseline = prior_jobs_count >= 10 and len(live_current_jobs) > 0
        prior_skill_shares: Dict[str, float] = {}
        if has_prior_baseline:
            for s_id, j_ids in prior_skill_jobs.items():
                prior_skill_shares[s_id] = (len(j_ids) / prior_jobs_count) * 100.0
        else:
            data_quality_warnings.append(
                "Not enough history for a 30-day trend: the prior window (30-60 days ago) needs at least 10 live jobs in this sector. Showing the newly observed cohort instead."
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

            period_delta = None
            if has_prior_baseline:
                live_share = (len(current_skill_jobs[skill_id]) / len(live_current_jobs)) * 100.0
                period_delta = round(live_share - prior_skill_shares.get(skill_id, 0.0), 1)

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
            "has_prior_window": has_prior_baseline,
            "prior_window_jobs": prior_jobs_count,
            "data_quality_warnings": data_quality_warnings,
            "skills_telemetry": telemetry_records,
        }
