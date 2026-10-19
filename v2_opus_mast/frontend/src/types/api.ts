export interface SkillEvidence {
  skill_id: string;
  skill_name?: string;
  category?: string;
  requirement_type: 'required' | 'preferred' | 'mentioned' | 'uncertain';
  evidence_text: string;
  extraction_method: string;
}

export interface ExperienceRequirement {
  min_years?: number | null;
  max_years?: number | null;
  experience_scope: string;
  related_skill?: string | null;
  evidence_text: string;
}

export interface FieldChange {
  timestamp: string;
  field_name: string;
  old_value?: string | null;
  new_value?: string | null;
}

export type Seniority = 'intern' | 'associate' | 'mid' | 'senior' | 'staff' | 'principal' | 'unspecified';
export type PayBand = 'under_100k' | '100_150k' | '150_200k' | '200k_plus' | 'unknown';
export type FeedStatus = 'live' | 'disabled' | 'no_public_feed';

export interface JobListItem {
  job_id: string;
  company: string;
  company_id?: string | null;
  company_domain?: string | null;
  canonical_category: string;
  title: string;
  department?: string | null;
  location: string;
  work_arrangement: string;
  seniority?: Seniority | string;
  apply_url: string;
  requisition_id?: string | null;
  internal_job_id?: string | null;
  is_demo?: boolean;
  first_seen_at: string;
  last_seen_at: string;
  source_created_at?: string | null;
  source_updated_at?: string | null;
  lifecycle_status: string;
  /** null = the posting states no parsable years requirement (shown as "unspecified"). */
  primary_min_yoe?: number | null;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string | null;
  required_skills: string[];
  preferred_skills: string[];
}

export interface JobDetail extends JobListItem {
  source_id: string;
  source_url?: string | null;
  consecutive_missing_syncs: number;
  normalized_description: string;
  description_hash: string;
  snapshots_count?: number;
  latest_snapshot_observed_at?: string | null;
  latest_extraction_signature?: string | null;
  latest_extraction_method?: string;
  latest_pipeline_version?: string;
  skills: SkillEvidence[];
  experience_requirements: ExperienceRequirement[];
  field_changes: FieldChange[];
}

export interface JobsResponse {
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  jobs: JobListItem[];
  sector_counts?: Record<string, number>;
}

export interface SkillDemandBreakdown {
  required: number;
  preferred: number;
  mentioned: number;
}

export interface SkillTelemetryItem {
  skill_id: string;
  skill_name: string;
  category: string;
  job_count: number;
  skill_share_pct: number;
  company_breadth: number;
  demand_breakdown: SkillDemandBreakdown;
  period_over_period_delta_pct?: number | null;
}

export interface TelemetryResponse {
  total_eligible_jobs: number;
  has_prior_window: boolean;
  prior_window_jobs: number;
  data_quality_warnings: string[];
  skills_telemetry: SkillTelemetryItem[];
}

export interface TopSkillItem {
  skill: string;
  job_count: number;
}

export interface TopSkillsResponse {
  total_jobs_analyzed: number;
  top_skills: TopSkillItem[];
}

export interface CompanyItem {
  company_id: string;
  name: string;
  canonical_category: string;
  website_url?: string | null;
  domain?: string | null;
  feed_status: FeedStatus;
  active_jobs_count: number;
}

export interface TaxonomySkill {
  skill_id: string;
  skill_name: string;
  category: string;
}

export interface SyncStatus {
  is_active: boolean;
  current_run_id?: string | null;
  status: 'idle' | 'queued' | 'running' | 'completed' | 'partial' | 'failed' | string;
  current_source?: string | null;
  total_sources: number;
  completed_sources: number;
  started_at?: string | null;
  completed_at?: string | null;
  last_error?: string | null;
  summary: Record<string, any>;
}

export interface SourceItem {
  source_id: string;
  company_id: string;
  company_name: string;
  provider_type: string;
  base_url: string;
  health_status: 'HEALTHY' | 'DEGRADED' | 'OFFLINE';
  enabled: boolean;
  feed_status: FeedStatus;
  last_successful_sync?: string | null;
  last_attempted_sync?: string | null;
  last_error?: string | null;
}

export interface SyncRunItem {
  run_id: string;
  source_id: string;
  started_at: string;
  completed_at?: string | null;
  duration_ms?: number | null;
  run_status: string;
  pagination_complete: boolean;
  jobs_discovered: number;
  jobs_created: number;
  jobs_updated: number;
  jobs_unchanged: number;
  jobs_rejected: number;
  is_reconciliation_safe: boolean;
  error_message?: string | null;
}

export interface CandidateSkill {
  skill_id: string;
  skill_name: string;
  proficiency: string;
  evidence_level: 'claimed' | 'coursework' | 'project' | 'production';
  notes?: string | null;
}

export interface CandidateProfile {
  candidate_id: string;
  name: string;
  overall_yoe: number | null;
  skills: CandidateSkill[];
}

export interface RoleGapAnalysis {
  job_id: string;
  title: string;
  company: string;
  canonical_category: string;
  location: string;
  coverage_score: number;
  satisfied_required: Array<{ skill_id: string; evidence_level: string; job_evidence: string }>;
  missing_required: Array<{ skill_id: string; job_evidence: string }>;
  satisfied_preferred: Array<{ skill_id: string; evidence_level: string; job_evidence: string }>;
  missing_preferred: Array<{ skill_id: string; job_evidence: string }>;
  has_experience_gap: boolean;
  yoe_deficit: number | null;
  yoe_gap_warning?: string | null;
  candidate_yoe: number | null;
  job_min_yoe?: number | null;
  is_one_skill_away: boolean;
  one_skill_gap?: { skill_id: string; job_evidence: string; requirement_type: 'required' | 'preferred' } | null;
  apply_url: string;
}

export interface GapAnalysisResponse {
  candidate_yoe: number | null;
  candidate_skills_count: number;
  total_roles_analyzed: number;
  one_skill_away_count: number;
  one_skill_away_roles: RoleGapAnalysis[];
  top_matched_roles: RoleGapAnalysis[];
}

export type ViewTab = 'radar' | 'constellation' | 'salary' | 'telemetry' | 'gap-analyzer' | 'sources';
