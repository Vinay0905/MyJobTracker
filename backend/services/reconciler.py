import json
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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

logger = logging.getLogger("devradar.reconciler")

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
        
        # Check prior known active inventory for volume drop guard
        prior_active_stmt = select(Job).where(
            Job.source_id == source.source_id,
            Job.lifecycle_status == LifecycleStatus.ACTIVE.value,
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

            # Run normalization and extraction pipeline
            processed = process_job_description(
                title=raw.get("title", ""),
                department=raw.get("department", ""),
                raw_html_or_text=raw.get("raw_html", ""),
            )

            if not processed["is_engineering"]:
                jobs_rejected += 1
                continue

            existing_job = await self.session.get(Job, job_composite_id)

            if existing_job is None:
                # NEW JOB CREATION
                new_job = Job(
                    job_id=job_composite_id,
                    source_id=source.source_id,
                    provider_posting_id=posting_id,
                    requisition_id=raw.get("requisition_id"),
                    internal_job_id=raw.get("internal_job_id"),
                    is_demo=bool(raw.get("is_demo", False)),
                    title=raw.get("title", ""),
                    canonical_category=canonical_category,
                    department=raw.get("department"),
                    location=raw.get("location", "Global"),
                    work_arrangement="hybrid",
                    apply_url=raw.get("apply_url", ""),
                    source_url=raw.get("source_url"),
                    source_updated_at=raw.get("source_updated_at") if isinstance(raw.get("source_updated_at"), datetime) else None,
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

                # Snapshot
                snapshot = JobSnapshot(
                    job_id=new_job.job_id,
                    observed_at=now,
                    raw_payload_json=json.dumps(raw),
                    normalized_text=processed["normalized_description"],
                    description_hash=processed["description_hash"],
                )
                self.session.add(snapshot)
                await self.session.flush()
                new_job.latest_snapshot_id = snapshot.snapshot_id

                # Extraction run provenance
                extraction_sig = hashlib.sha256(
                    (processed["normalized_description"] + "1.0:1.0:1.0:deterministic").encode()
                ).hexdigest()
                extraction_run = ExtractionRun(
                    run_id=str(uuid.uuid4()),
                    job_id=new_job.job_id,
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

                # Lifecycle event
                event = JobLifecycleEvent(
                    job_id=new_job.job_id,
                    timestamp=now,
                    previous_status="NONE",
                    new_status=LifecycleStatus.ACTIVE.value,
                    reason="Initial discovery during sync",
                )
                self.session.add(event)

                # Persist extracted skills linked to snapshot and extraction run
                for s in processed["skills"]:
                    self.session.add(JobSkillEvidence(
                        job_id=new_job.job_id,
                        snapshot_id=snapshot.snapshot_id,
                        extraction_run_id=extraction_run.run_id,
                        skill_id=s["skill_id"],
                        requirement_type=s["requirement_type"],
                        evidence_text=s["evidence_text"],
                        extraction_method=s["extraction_method"],
                    ))

                # Persist extracted experience requirements linked to snapshot and extraction run
                for exp in processed["experience"]:
                    self.session.add(JobExperienceRequirement(
                        job_id=new_job.job_id,
                        snapshot_id=snapshot.snapshot_id,
                        extraction_run_id=extraction_run.run_id,
                        min_years=exp["min_years"],
                        max_years=exp["max_years"],
                        experience_scope=exp["experience_scope"],
                        related_skill=exp["related_skill"],
                        evidence_text=exp["evidence_text"],
                    ))

                jobs_created += 1

            else:
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

                # Check if description content changed
                if existing_job.description_hash != processed["description_hash"]:
                    # Log field change
                    self.session.add(JobFieldChangeEvent(
                        job_id=existing_job.job_id,
                        timestamp=now,
                        field_name="description",
                        old_value=existing_job.normalized_description[:200],
                        new_value=processed["normalized_description"][:200],
                    ))
                    existing_job.normalized_description = processed["normalized_description"]
                    existing_job.description_hash = processed["description_hash"]

                    # Add new snapshot
                    new_snapshot = JobSnapshot(
                        job_id=existing_job.job_id,
                        observed_at=now,
                        raw_payload_json=json.dumps(raw),
                        normalized_text=processed["normalized_description"],
                        description_hash=processed["description_hash"],
                    )
                    self.session.add(new_snapshot)
                    await self.session.flush()
                    existing_job.latest_snapshot_id = new_snapshot.snapshot_id

                    # Add new extraction run for this snapshot
                    extraction_sig = hashlib.sha256(
                        (processed["normalized_description"] + "1.0:1.0:1.0:deterministic").encode()
                    ).hexdigest()
                    new_extraction_run = ExtractionRun(
                        run_id=str(uuid.uuid4()),
                        job_id=existing_job.job_id,
                        snapshot_id=new_snapshot.snapshot_id,
                        normalization_version="1.0",
                        taxonomy_version="1.0",
                        pipeline_version="1.0",
                        extraction_method="deterministic",
                        extraction_signature=extraction_sig,
                        created_at=now,
                    )
                    self.session.add(new_extraction_run)
                    await self.session.flush()

                    # Append new skills tied to this new snapshot (preserves historical snapshot skills)
                    for s in processed["skills"]:
                        self.session.add(JobSkillEvidence(
                            job_id=existing_job.job_id,
                            snapshot_id=new_snapshot.snapshot_id,
                            extraction_run_id=new_extraction_run.run_id,
                            skill_id=s["skill_id"],
                            requirement_type=s["requirement_type"],
                            evidence_text=s["evidence_text"],
                            extraction_method=s["extraction_method"],
                        ))

                    for exp in processed["experience"]:
                        self.session.add(JobExperienceRequirement(
                            job_id=existing_job.job_id,
                            snapshot_id=new_snapshot.snapshot_id,
                            extraction_run_id=new_extraction_run.run_id,
                            min_years=exp["min_years"],
                            max_years=exp["max_years"],
                            experience_scope=exp["experience_scope"],
                            related_skill=exp["related_skill"],
                            evidence_text=exp["evidence_text"],
                        ))

                    jobs_updated += 1
                else:
                    jobs_unchanged += 1

        # 3. Safe Reconciliation of Missing Jobs (ONLY if is_reconciliation_safe == True)
        if is_reconciliation_safe:
            # Query all non-closed jobs for this source
            active_jobs_stmt = select(Job).where(
                Job.source_id == source.source_id,
                Job.lifecycle_status != LifecycleStatus.CLOSED.value,
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
