import enum
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class RunStatus(str, enum.Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    RATE_LIMITED = "RATE_LIMITED"
    ACCESS_DENIED = "ACCESS_DENIED"
    NETWORK_ERROR = "NETWORK_ERROR"
    SCHEMA_ERROR = "SCHEMA_ERROR"


class LifecycleStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    MISSING_CANDIDATE = "MISSING_CANDIDATE"
    CLOSED = "CLOSED"


class HealthStatus(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


class RequirementType(str, enum.Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    MENTIONED = "mentioned"
    UNCERTAIN = "uncertain"


class ExperienceScope(str, enum.Enum):
    OVERALL_PROFESSIONAL = "overall_professional"
    SKILL_SPECIFIC = "skill_specific"
    DOMAIN_SPECIFIC = "domain_specific"
    ENTRY_LEVEL_SIGNAL = "entry_level_signal"
    DEGREE_EQUIVALENT = "degree_equivalent"


class EvidenceLevel(str, enum.Enum):
    CLAIMED = "claimed"
    COURSEWORK = "coursework"
    PROJECT = "project"
    PRODUCTION = "production"


class Company(Base):
    __tablename__ = "companies"

    company_id = Column(String(64), primary_key=True)
    name = Column(String(128), nullable=False)
    canonical_category = Column(String(64), nullable=False)  # Game Studio | Silicon & AI | UAE & Middle East
    website_url = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    sources = relationship("Source", back_populates="company", cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "sources"

    source_id = Column(String(64), primary_key=True)
    company_id = Column(String(64), ForeignKey("companies.company_id"), nullable=False)
    provider_type = Column(String(32), nullable=False)  # greenhouse | workday | eightfold | custom
    base_url = Column(String(256), nullable=False)
    board_token = Column(String(64), nullable=True)
    endpoint = Column(String(256), nullable=True)
    allowed_hosts = Column(Text, nullable=False, default="[]")  # JSON string of whitelisted hostnames
    enabled = Column(Boolean, default=True, nullable=False)
    polling_interval_minutes = Column(Integer, default=60, nullable=False)
    timeout_seconds = Column(Float, default=15.0, nullable=False)
    concurrency_limit = Column(Integer, default=2, nullable=False)
    health_status = Column(String(32), default=HealthStatus.HEALTHY.value, nullable=False)
    last_successful_sync = Column(DateTime, nullable=True)
    last_attempted_sync = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)

    company = relationship("Company", back_populates="sources")
    sync_runs = relationship("SyncRun", back_populates="source", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="source", cascade="all, delete-orphan")


class SyncRun(Base):
    __tablename__ = "sync_runs"

    run_id = Column(String(64), primary_key=True)
    source_id = Column(String(64), ForeignKey("sources.source_id"), nullable=False)
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    run_status = Column(String(32), default=RunStatus.PARTIAL.value, nullable=False)
    pagination_complete = Column(Boolean, default=False, nullable=False)
    requests_count = Column(Integer, default=0, nullable=False)
    jobs_discovered = Column(Integer, default=0, nullable=False)
    jobs_created = Column(Integer, default=0, nullable=False)
    jobs_updated = Column(Integer, default=0, nullable=False)
    jobs_unchanged = Column(Integer, default=0, nullable=False)
    jobs_rejected = Column(Integer, default=0, nullable=False)
    previously_known_observed = Column(Integer, default=0, nullable=False)
    is_reconciliation_safe = Column(Boolean, default=False, nullable=False)
    error_message = Column(Text, nullable=True)

    source = relationship("Source", back_populates="sync_runs")


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint("source_id", "provider_posting_id", name="uq_source_provider_posting"),
        Index("ix_jobs_lifecycle_cat", "lifecycle_status", "canonical_category"),
        Index("ix_jobs_last_seen", "last_seen_at"),
    )

    job_id = Column(String(128), primary_key=True)  # composite: f"{source_id}:{provider_posting_id}"
    source_id = Column(String(64), ForeignKey("sources.source_id"), nullable=False)
    provider_posting_id = Column(String(128), nullable=False)
    requisition_id = Column(String(128), nullable=True)
    internal_job_id = Column(String(128), nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)
    title = Column(String(256), nullable=False)
    canonical_category = Column(String(64), nullable=False)
    department = Column(String(128), nullable=True)
    location = Column(String(256), nullable=False)
    work_arrangement = Column(String(32), default="unknown", nullable=False)  # remote | hybrid | onsite | unknown
    employment_type = Column(String(64), nullable=True)
    country = Column(String(64), nullable=True)
    region = Column(String(64), nullable=True)
    apply_url = Column(Text, nullable=False)
    source_url = Column(Text, nullable=True)
    source_created_at = Column(DateTime, nullable=True)
    source_updated_at = Column(DateTime, nullable=True)
    first_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_successfully_observed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    consecutive_missing_syncs = Column(Integer, default=0, nullable=False)
    lifecycle_status = Column(String(32), default=LifecycleStatus.ACTIVE.value, nullable=False)
    normalized_description = Column(Text, nullable=False, default="")
    description_hash = Column(String(64), nullable=False, default="")
    latest_snapshot_id = Column(Integer, nullable=True)

    source = relationship("Source", back_populates="jobs")
    snapshots = relationship("JobSnapshot", back_populates="job", cascade="all, delete-orphan")
    extraction_runs = relationship("ExtractionRun", back_populates="job", cascade="all, delete-orphan")
    lifecycle_events = relationship("JobLifecycleEvent", back_populates="job", cascade="all, delete-orphan")
    field_changes = relationship("JobFieldChangeEvent", back_populates="job", cascade="all, delete-orphan")
    skills = relationship("JobSkillEvidence", back_populates="job", cascade="all, delete-orphan")
    experience_requirements = relationship("JobExperienceRequirement", back_populates="job", cascade="all, delete-orphan")

    @property
    def latest_skills(self):
        target_snap_id = self.latest_snapshot_id
        if target_snap_id is None:
            from sqlalchemy.orm import attributes
            state = attributes.instance_state(self)
            if "snapshots" in state.dict and self.snapshots:
                target_snap_id = max((s.snapshot_id for s in self.snapshots if s.snapshot_id is not None), default=None)
            elif "skills" in state.dict and self.skills:
                target_snap_id = max((s.snapshot_id for s in self.skills if s.snapshot_id is not None), default=None)

        if target_snap_id is None:
            return list(self.skills) if self.skills else []

        return [s for s in self.skills if s.snapshot_id == target_snap_id]

    @property
    def latest_experience(self):
        target_snap_id = self.latest_snapshot_id
        if target_snap_id is None:
            from sqlalchemy.orm import attributes
            state = attributes.instance_state(self)
            if "snapshots" in state.dict and self.snapshots:
                target_snap_id = max((s.snapshot_id for s in self.snapshots if s.snapshot_id is not None), default=None)
            elif "experience_requirements" in state.dict and self.experience_requirements:
                target_snap_id = max((e.snapshot_id for e in self.experience_requirements if e.snapshot_id is not None), default=None)

        if target_snap_id is None:
            return list(self.experience_requirements) if self.experience_requirements else []

        return [e for e in self.experience_requirements if e.snapshot_id == target_snap_id]


class JobSnapshot(Base):
    __tablename__ = "job_snapshots"

    snapshot_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(128), ForeignKey("jobs.job_id"), nullable=False)
    observed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    raw_payload_json = Column(Text, nullable=False)
    normalized_text = Column(Text, nullable=False)
    description_hash = Column(String(64), nullable=False)

    job = relationship("Job", back_populates="snapshots")
    extraction_runs = relationship("ExtractionRun", back_populates="snapshot", cascade="all, delete-orphan")
    skills = relationship("JobSkillEvidence", back_populates="snapshot", cascade="all, delete-orphan")
    experience_requirements = relationship("JobExperienceRequirement", back_populates="snapshot", cascade="all, delete-orphan")


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    run_id = Column(String(64), primary_key=True)
    job_id = Column(String(128), ForeignKey("jobs.job_id"), nullable=False)
    snapshot_id = Column(Integer, ForeignKey("job_snapshots.snapshot_id"), nullable=False)
    normalization_version = Column(String(32), default="1.0", nullable=False)
    taxonomy_version = Column(String(32), default="1.0", nullable=False)
    pipeline_version = Column(String(32), default="1.0", nullable=False)
    extraction_method = Column(String(32), default="deterministic", nullable=False)
    extraction_signature = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("Job", back_populates="extraction_runs")
    snapshot = relationship("JobSnapshot", back_populates="extraction_runs")
    skills = relationship("JobSkillEvidence", back_populates="extraction_run", cascade="all, delete-orphan")
    experience_requirements = relationship("JobExperienceRequirement", back_populates="extraction_run", cascade="all, delete-orphan")


class JobLifecycleEvent(Base):
    __tablename__ = "job_lifecycle_events"

    event_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(128), ForeignKey("jobs.job_id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    previous_status = Column(String(32), nullable=False)
    new_status = Column(String(32), nullable=False)
    reason = Column(String(256), nullable=False)

    job = relationship("Job", back_populates="lifecycle_events")


class JobFieldChangeEvent(Base):
    __tablename__ = "job_field_change_events"

    change_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(128), ForeignKey("jobs.job_id"), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    field_name = Column(String(64), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

    job = relationship("Job", back_populates="field_changes")


class TaxonomySkill(Base):
    __tablename__ = "taxonomy_skills"

    skill_id = Column(String(64), primary_key=True)
    skill_name = Column(String(64), nullable=False)
    category = Column(String(64), nullable=False)  # Languages | GPU / Silicon | AI / ML | Systems | etc.

    evidence_records = relationship("JobSkillEvidence", back_populates="skill")


class JobSkillEvidence(Base):
    __tablename__ = "job_skill_evidence"
    __table_args__ = (
        Index("ix_skill_evidence_job_skill", "job_id", "skill_id"),
        Index("ix_skill_evidence_snapshot", "snapshot_id"),
    )

    evidence_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(128), ForeignKey("jobs.job_id"), nullable=False)
    snapshot_id = Column(Integer, ForeignKey("job_snapshots.snapshot_id"), nullable=True)
    extraction_run_id = Column(String(64), ForeignKey("extraction_runs.run_id"), nullable=True)
    skill_id = Column(String(64), ForeignKey("taxonomy_skills.skill_id"), nullable=False)
    requirement_type = Column(String(32), default=RequirementType.REQUIRED.value, nullable=False)
    evidence_text = Column(Text, nullable=False)
    extraction_method = Column(String(32), default="deterministic", nullable=False)
    taxonomy_version = Column(String(32), default="1.0", nullable=False)
    pipeline_version = Column(String(32), default="1.0", nullable=False)

    job = relationship("Job", back_populates="skills")
    snapshot = relationship("JobSnapshot", back_populates="skills")
    extraction_run = relationship("ExtractionRun", back_populates="skills")
    skill = relationship("TaxonomySkill", back_populates="evidence_records")


class JobExperienceRequirement(Base):
    __tablename__ = "job_experience_requirements"
    __table_args__ = (
        Index("ix_exp_req_snapshot", "snapshot_id"),
    )

    exp_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(128), ForeignKey("jobs.job_id"), nullable=False)
    snapshot_id = Column(Integer, ForeignKey("job_snapshots.snapshot_id"), nullable=True)
    extraction_run_id = Column(String(64), ForeignKey("extraction_runs.run_id"), nullable=True)
    min_years = Column(Integer, nullable=True)
    max_years = Column(Integer, nullable=True)
    experience_scope = Column(String(32), default=ExperienceScope.OVERALL_PROFESSIONAL.value, nullable=False)
    related_skill = Column(String(64), nullable=True)
    evidence_text = Column(Text, nullable=False)

    job = relationship("Job", back_populates="experience_requirements")
    snapshot = relationship("JobSnapshot", back_populates="experience_requirements")
    extraction_run = relationship("ExtractionRun", back_populates="experience_requirements")


class CandidateProfile(Base):
    __tablename__ = "candidate_profile"

    candidate_id = Column(String(64), primary_key=True, default="default")
    name = Column(String(128), default="Unconfigured Profile", nullable=False)
    overall_yoe = Column(Float, nullable=True, default=None)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    skills = relationship("CandidateSkillEvidence", back_populates="candidate", cascade="all, delete-orphan")


class CandidateSkillEvidence(Base):
    __tablename__ = "candidate_skill_evidence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    candidate_id = Column(String(64), ForeignKey("candidate_profile.candidate_id"), nullable=False)
    skill_id = Column(String(64), ForeignKey("taxonomy_skills.skill_id"), nullable=False)
    proficiency = Column(String(32), default="intermediate", nullable=False)
    evidence_level = Column(String(32), default=EvidenceLevel.PRODUCTION.value, nullable=False)
    notes = Column(Text, nullable=True)

    candidate = relationship("CandidateProfile", back_populates="skills")
    skill = relationship("TaxonomySkill")
