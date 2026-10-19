import json
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from backend.db.models import (
    Source,
    Company,
    Job,
    JobSnapshot,
    ExtractionRun,
    JobLifecycleEvent,
    JobFieldChangeEvent,
    JobSkillEvidence,
    JobExperienceRequirement,
    SyncRun,
    RunStatus,
    LifecycleStatus,
)
from backend.extraction.pipeline import process_job_description
from backend.extraction.experience import governing_min_years
from backend.extraction.attributes import (
    parse_seniority,
    parse_work_arrangement,
    parse_provider_timestamp,
    parse_salary,
)

logger = logging.getLogger("devradar.reconciler")

LOCATION_NOT_LISTED = "Location not listed"

# Posting metadata refreshed on every sighting. Seniority is derived from the title.
OBSERVED_FIELDS = ("title", "department", "location", "work_arrangement", "apply_url", "source_url", "requisition_id")
AUDITED_FIELDS = {"title", "department", "location", "work_arrangement", "apply_url"}


def posting_attributes(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalizes connector output into the Job columns that mirror the live posting."""
    title = (raw.get("title") or "").strip()
    location = (raw.get("location") or "").strip() or LOCATION_NOT_LISTED
    return {
        "title": title,
        "department": raw.get("department") or None,
        "location": location,
        "work_arrangement": parse_work_arrangement(raw.get("work_arrangement"), location),
        "apply_url": raw.get("apply_url") or "",
        "source_url": raw.get("source_url"),
        "requisition_id": raw.get("requisition_id"),
        "seniority": parse_seniority(title),
        "source_created_at": parse_provider_timestamp(raw.get("source_created_at")),
        "source_updated_at": parse_provider_timestamp(raw.get("source_updated_at")),
    }


class SafeReconciliationEngine:
    """
    Executes atomic, idempotent sync runs with safe job closure state machine
    (ACTIVE -> MISSING_CANDIDATE -> CLOSED).
    """
    def __init__(self, session: AsyncSession, consecutive_missing_threshold: int = 2):
        self.session = session
        self.consecutive_missing_threshold = consecutive_missing_threshold

    async def execute_sync_run(
        self,
        source: Source,
        raw_postings: List[Dict[str, Any]],
        pagination_complete: bool,
        requests_count: int,
        error_message: Optional[str] = None,
    ) -> SyncRun:
        run_id = str(uuid.uuid4())
        started_at = datetime.now(timezone.utc)

        # Volume drop guard compares against live inventory only; demo fixtures are never observed by a sync.
        prior_active_stmt = select(Job).where(
            Job.source_id == source.source_id,
            Job.lifecycle_status == LifecycleStatus.ACTIVE.value,
            Job.is_demo == False,
        )
        prior_active_jobs = (await self.session.execute(prior_active_stmt)).scalars().all()
        prior_active_count = len(prior_active_jobs)

        is_suspicious_drop = False
        if prior_active_count >= 10 and len(raw_postings) < (prior_active_count * 0.5):
            is_suspicious_drop = True
            drop_msg = f"Suspicious volume drop: observed {len(raw_postings)} postings, expected ~{prior_active_count}"
            error_message = f"{error_message} | {drop_msg}" if error_message else drop_msg
            logger.warning(f"Reconciliation safety triggered: {drop_msg}")

        # 1. Evaluate Reconciliation Safety Guard
        # Safe ONLY if: no error AND pagination complete AND not suspicious drop
        run_status = RunStatus.COMPLETE.value if (not error_message and pagination_complete and not is_suspicious_drop) else (
            RunStatus.PARTIAL.value if pagination_complete else RunStatus.NETWORK_ERROR.value
        )
        if error_message and "429" in error_message:
            run_status = RunStatus.RATE_LIMITED.value

        is_reconciliation_safe = (run_status == RunStatus.COMPLETE.value) and pagination_complete and not is_suspicious_drop

        sync_run = SyncRun(
            run_id=run_id,
            source_id=source.source_id,
            started_at=started_at,
            run_status=run_status,
            pagination_complete=pagination_complete,
            requests_count=requests_count,
            jobs_discovered=len(raw_postings),
            is_reconciliation_safe=is_reconciliation_safe,
            error_message=error_message,
        )
        self.session.add(sync_run)
        await self.session.flush()

        now = datetime.now(timezone.utc)
        observed_posting_ids = set()
        jobs_created = 0
        jobs_updated = 0
        jobs_unchanged = 0
        jobs_rejected = 0

        # Query existing company for canonical_category
        company = await self.session.get(Company, source.company_id)
        canonical_category = company.canonical_category if company else "Engineering"

        # 2. Process discovered job postings
        for raw in raw_postings:
            posting_id = str(raw["provider_posting_id"])
            observed_posting_ids.add(posting_id)
            job_composite_id = f"{source.source_id}:{posting_id}"
            attrs = posting_attributes(raw)

            # Connectors that fetch descriptions separately flag failed detail fetches.
            # Postings without the flag carry their description inline.
            description_available = raw.get("description_status", "available") == "available"

            existing_job = await self.session.get(Job, job_composite_id)

            processed = None
            if existing_job is None or description_available:
                processed = process_job_description(
                    title=attrs["title"],
                    department=attrs["department"] or "",
                    raw_html_or_text=raw.get("raw_html", ""),
                )
                if not processed["is_engineering"]:
                    jobs_rejected += 1
                    continue

            if existing_job is None:
                salary = parse_salary(processed["normalized_description"], raw.get("salary"))
                new_job = Job(
                    job_id=job_composite_id,
                    source_id=source.source_id,
                    provider_posting_id=posting_id,
                    requisition_id=attrs["requisition_id"],
                    internal_job_id=raw.get("internal_job_id"),
                    is_demo=bool(raw.get("is_demo", False)),
                    title=attrs["title"],
                    canonical_category=canonical_category,
                    department=attrs["department"],
                    location=attrs["location"],
                    work_arrangement=attrs["work_arrangement"],
                    seniority=attrs["seniority"],
                    required_yoe=processed["primary_min_yoe"],
                    salary_min=salary["salary_min"],
                    salary_max=salary["salary_max"],
                    salary_currency=salary["salary_currency"],
                    apply_url=attrs["apply_url"],
                    source_url=attrs["source_url"],
                    source_created_at=attrs["source_created_at"],
                    source_updated_at=attrs["source_updated_at"],
                    first_seen_at=now,
                    last_seen_at=now,
                    last_successfully_observed_at=now,
                    consecutive_missing_syncs=0,
                    lifecycle_status=LifecycleStatus.ACTIVE.value,
                    normalized_description=processed["normalized_description"],
                    description_hash=processed["description_hash"],
                )
                self.session.add(new_job)
                await self.session.flush()

                await self._record_snapshot(new_job, raw, processed, now)

                self.session.add(JobLifecycleEvent(
                    job_id=new_job.job_id,
                    timestamp=now,
                    previous_status="NONE",
                    new_status=LifecycleStatus.ACTIVE.value,
                    reason="Initial discovery during sync",
                ))

                jobs_created += 1
                continue

            # EXISTING JOB OBSERVATION
            existing_job.last_seen_at = now
            existing_job.last_successfully_observed_at = now
            existing_job.consecutive_missing_syncs = 0

            # Resurrect if it was missing or closed
            if existing_job.lifecycle_status != LifecycleStatus.ACTIVE.value:
                prev_st = existing_job.lifecycle_status
                existing_job.lifecycle_status = LifecycleStatus.ACTIVE.value
                self.session.add(JobLifecycleEvent(
                    job_id=existing_job.job_id,
                    timestamp=now,
                    previous_status=prev_st,
                    new_status=LifecycleStatus.ACTIVE.value,
                    reason="Re-observed active in career portal (resurrected)",
                ))

            metadata_changed = self._apply_observed_fields(existing_job, attrs, now)

            if processed is None:
                # Detail fetch failed: keep the stored description, skills, and latest snapshot.
                if metadata_changed:
                    jobs_updated += 1
                else:
                    jobs_unchanged += 1
                continue

            salary = parse_salary(processed["normalized_description"], raw.get("salary"))
            existing_job.salary_min = salary["salary_min"]
            existing_job.salary_max = salary["salary_max"]
            existing_job.salary_currency = salary["salary_currency"]

            if existing_job.description_hash != processed["description_hash"]:
                self.session.add(JobFieldChangeEvent(
                    job_id=existing_job.job_id,
                    timestamp=now,
                    field_name="description",
                    old_value=existing_job.normalized_description[:200],
                    new_value=processed["normalized_description"][:200],
                ))
                existing_job.normalized_description = processed["normalized_description"]
                existing_job.description_hash = processed["description_hash"]
                existing_job.required_yoe = processed["primary_min_yoe"]

                # New snapshot + extraction run; historical snapshot skills are preserved.
                await self._record_snapshot(existing_job, raw, processed, now)
                jobs_updated += 1
            elif metadata_changed:
                jobs_updated += 1
            else:
                jobs_unchanged += 1

        # 3. Safe Reconciliation of Missing Jobs (ONLY if is_reconciliation_safe == True)
        if is_reconciliation_safe:
            # Demo fixtures are never part of a live feed, so they are never closed by one.
            active_jobs_stmt = select(Job).where(
                Job.source_id == source.source_id,
                Job.lifecycle_status != LifecycleStatus.CLOSED.value,
                Job.is_demo == False,
            )
            source_jobs = (await self.session.execute(active_jobs_stmt)).scalars().all()

            for job in source_jobs:
                if job.provider_posting_id not in observed_posting_ids:
                    job.consecutive_missing_syncs += 1

                    if job.lifecycle_status == LifecycleStatus.ACTIVE.value:
                        job.lifecycle_status = LifecycleStatus.MISSING_CANDIDATE.value
                        self.session.add(JobLifecycleEvent(
                            job_id=job.job_id,
                            timestamp=now,
                            previous_status=LifecycleStatus.ACTIVE.value,
                            new_status=LifecycleStatus.MISSING_CANDIDATE.value,
                            reason="Omitted in verified complete career sync",
                        ))
                    elif job.lifecycle_status == LifecycleStatus.MISSING_CANDIDATE.value:
                        if job.consecutive_missing_syncs >= self.consecutive_missing_threshold:
                            job.lifecycle_status = LifecycleStatus.CLOSED.value
                            self.session.add(JobLifecycleEvent(
                                job_id=job.job_id,
                                timestamp=now,
                                previous_status=LifecycleStatus.MISSING_CANDIDATE.value,
                                new_status=LifecycleStatus.CLOSED.value,
                                reason=f"Omitted across {job.consecutive_missing_syncs} consecutive complete syncs",
                            ))
        else:
            logger.warning(
                f"Sync run for source {source.source_id} was NOT reconciliation-safe. "
                "Skipping closure checks to prevent data loss."
            )

        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        sync_run.completed_at = completed_at
        sync_run.duration_ms = duration_ms
        sync_run.jobs_created = jobs_created
        sync_run.jobs_updated = jobs_updated
        sync_run.jobs_unchanged = jobs_unchanged
        sync_run.jobs_rejected = jobs_rejected
        sync_run.previously_known_observed = len(observed_posting_ids) - jobs_created

        # Update source telemetry
        source.last_attempted_sync = completed_at
        if run_status == RunStatus.COMPLETE.value:
            source.last_successful_sync = completed_at
            source.health_status = "HEALTHY"
            source.last_error = None
        else:
            source.health_status = "DEGRADED"
            source.last_error = error_message

        await self.session.commit()
        return sync_run

    def _apply_observed_fields(self, job: Job, attrs: Dict[str, Any], now: datetime) -> bool:
        """Copies the posting's current metadata onto the job. Returns True when anything changed."""
        changed = False
        title_changed = False
        for field in OBSERVED_FIELDS:
            new_value = attrs[field]
            # Empty provider values never blank out a stored URL, title, or requisition id.
            if new_value in (None, "") and field != "department":
                continue
            old_value = getattr(job, field)
            if old_value == new_value:
                continue
            if field in AUDITED_FIELDS:
                self.session.add(JobFieldChangeEvent(
                    job_id=job.job_id,
                    timestamp=now,
                    field_name=field,
                    old_value=None if old_value is None else str(old_value)[:200],
                    new_value=None if new_value is None else str(new_value)[:200],
                ))
            setattr(job, field, new_value)
            changed = True
            if field == "title":
                title_changed = True

        prior_seniority = job.seniority
        job.seniority = parse_seniority(job.title)
        if title_changed or job.seniority != prior_seniority:
            state = attributes.instance_state(job)
            if "experience_requirements" in state.dict:
                job.required_yoe = governing_min_years(job.latest_experience)
        for ts_field in ("source_created_at", "source_updated_at"):
            if attrs[ts_field] is not None:
                setattr(job, ts_field, attrs[ts_field])
        return changed

    async def _record_snapshot(self, job: Job, raw: Dict[str, Any], processed: Dict[str, Any], now: datetime) -> None:
        snapshot = JobSnapshot(
            job_id=job.job_id,
            observed_at=now,
            raw_payload_json=json.dumps(raw, default=str),
            normalized_text=processed["normalized_description"],
            description_hash=processed["description_hash"],
        )
        self.session.add(snapshot)
        await self.session.flush()
        job.latest_snapshot_id = snapshot.snapshot_id

        extraction_sig = hashlib.sha256(
            (processed["normalized_description"] + "1.0:1.0:1.0:deterministic").encode()
        ).hexdigest()
        extraction_run = ExtractionRun(
            run_id=str(uuid.uuid4()),
            job_id=job.job_id,
            snapshot_id=snapshot.snapshot_id,
            normalization_version="1.0",
            taxonomy_version="1.0",
            pipeline_version="1.0",
            extraction_method="deterministic",
            extraction_signature=extraction_sig,
            created_at=now,
        )
        self.session.add(extraction_run)
        await self.session.flush()

        for s in processed["skills"]:
            self.session.add(JobSkillEvidence(
                job_id=job.job_id,
                snapshot_id=snapshot.snapshot_id,
                extraction_run_id=extraction_run.run_id,
                skill_id=s["skill_id"],
                requirement_type=s["requirement_type"],
                evidence_text=s["evidence_text"],
                extraction_method=s["extraction_method"],
            ))

        for exp in processed["experience"]:
            self.session.add(JobExperienceRequirement(
                job_id=job.job_id,
                snapshot_id=snapshot.snapshot_id,
                extraction_run_id=extraction_run.run_id,
                min_years=exp["min_years"],
                max_years=exp["max_years"],
                experience_scope=exp["experience_scope"],
                related_skill=exp["related_skill"],
                evidence_text=exp["evidence_text"],
            ))
