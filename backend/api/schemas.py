from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

# Skill & Evidence Schemas
class SkillEvidenceSchema(BaseModel):
    skill_id: str
    skill_name: Optional[str] = None
    category: Optional[str] = None
    requirement_type: str
    evidence_text: str
    extraction_method: str = "deterministic"

class ExperienceRequirementSchema(BaseModel):
    min_years: Optional[int] = None
    max_years: Optional[int] = None
    experience_scope: str
    related_skill: Optional[str] = None
    evidence_text: str

class FieldChangeSchema(BaseModel):
    timestamp: datetime
    field_name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None

class JobDetailSchema(BaseModel):
    job_id: str
    source_id: str
    company: str
    company_domain: Optional[str] = None
    canonical_category: str
    title: str
    department: Optional[str] = None
    location: str
    work_arrangement: str
    apply_url: str
    source_url: Optional[str] = None
    requisition_id: Optional[str] = None
    internal_job_id: Optional[str] = None
    is_demo: bool = False
    first_seen_at: datetime
    last_seen_at: datetime
    lifecycle_status: str
    consecutive_missing_syncs: int
    normalized_description: str
    description_hash: str
    snapshots_count: int = 1
    latest_snapshot_observed_at: Optional[datetime] = None
    latest_extraction_signature: Optional[str] = None
    latest_extraction_method: Optional[str] = "deterministic"
    latest_pipeline_version: Optional[str] = "1.0"
    skills: List[SkillEvidenceSchema]
    experience_requirements: List[ExperienceRequirementSchema]
    field_changes: List[FieldChangeSchema] = []

class JobListItemSchema(BaseModel):
    job_id: str
    company: str
    company_domain: Optional[str] = None
    canonical_category: str
    title: str
    department: Optional[str] = None
    location: str
    work_arrangement: str
    apply_url: str
    requisition_id: Optional[str] = None
    internal_job_id: Optional[str] = None
    is_demo: bool = False
    first_seen_at: datetime
    last_seen_at: datetime
    lifecycle_status: str
    primary_min_yoe: Optional[int] = None
    required_skills: List[str] = []
    preferred_skills: List[str] = []

class JobsResponse(BaseModel):
    total_count: int
    page: int
    page_size: int
    jobs: List[JobListItemSchema]
    sector_counts: Dict[str, int] = Field(default_factory=dict)

# Telemetry Schemas
class SkillDemandBreakdown(BaseModel):
    required: int
    preferred: int
    mentioned: int

class SkillTelemetryItem(BaseModel):
    skill_id: str
    skill_name: str
    category: str
    job_count: int
    skill_share_pct: float
    company_breadth: int
    demand_breakdown: SkillDemandBreakdown
    newly_observed_cohort_count: Optional[int] = 0
    period_over_period_delta_pct: Optional[float] = None

class TelemetryResponse(BaseModel):
    total_eligible_jobs: int
    denominator_count: Optional[int] = None
    source_coverage_count: Optional[int] = 0
    newly_observed_cohort_total: Optional[int] = 0
    data_quality_warnings: List[str]
    skills_telemetry: List[SkillTelemetryItem]

class TopSkillItem(BaseModel):
    skill: str
    job_count: int

class TopSkillsResponse(BaseModel):
    total_jobs_analyzed: int
    top_skills: List[TopSkillItem]

# Candidate & Gap Analysis Schemas
class CandidateSkillInput(BaseModel):
    skill_id: str
    proficiency: str = "intermediate"
    evidence_level: str = "production"
    notes: Optional[str] = None

class CandidateProfileUpdate(BaseModel):
    name: str
    overall_yoe: Optional[float] = None
    skills: List[CandidateSkillInput]

class SourceItemSchema(BaseModel):
    source_id: str
    company_id: str
    company_name: str
    provider_type: str
    base_url: str
    health_status: str
    enabled: bool
    last_successful_sync: Optional[datetime] = None
    last_attempted_sync: Optional[datetime] = None
    last_error: Optional[str] = None

class SyncRunSchema(BaseModel):
    run_id: str
    source_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    run_status: str
    pagination_complete: bool
    jobs_discovered: int
    jobs_created: int
    jobs_updated: int
    jobs_unchanged: int
    jobs_rejected: int
    is_reconciliation_safe: bool
    error_message: Optional[str] = None
