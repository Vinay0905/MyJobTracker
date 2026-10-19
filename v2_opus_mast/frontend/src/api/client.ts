import {
  JobsResponse,
  JobDetail,
  TopSkillsResponse,
  TelemetryResponse,
  SourceItem,
  SyncRunItem,
  CandidateProfile,
  CandidateSkill,
  GapAnalysisResponse,
  CompanyItem,
  SyncStatus,
  TaxonomySkill,
} from '../types/api';

const API_BASE = '/api';

export async function fetchJobs(
  filters: {
    category?: string | null;
    /** Exact company_ids */
    companies?: string[];
    sort_by?: string | null;
    location?: string | null;
    role_focus?: string | string[] | null;
    skill?: string | null;
    required_skill?: string | null;
    preferred_skill?: string | null;
    search?: string | null;
    seniority?: string[];
    pay_bands?: string[];
    yoe_min?: number | null;
    yoe_max?: number | null;
    include_unspecified_yoe?: boolean;
    include_demo?: boolean;
    page?: number;
    pageSize?: number;
  },
  signal?: AbortSignal
): Promise<JobsResponse> {
  const params = new URLSearchParams();
  if (filters.category) params.set('category', filters.category);
  if (filters.companies && filters.companies.length > 0) params.set('company', filters.companies.join(','));
  if (filters.sort_by) params.set('sort_by', filters.sort_by);
  if (filters.location && filters.location !== 'Global') params.set('location', filters.location);
  if (filters.role_focus) {
    const roles = Array.isArray(filters.role_focus) ? filters.role_focus.join(',') : filters.role_focus;
    if (roles) params.set('role_focus', roles);
  }
  if (filters.skill) params.set('skill', filters.skill);
  if (filters.required_skill) params.set('required_skill', filters.required_skill);
  if (filters.preferred_skill) params.set('preferred_skill', filters.preferred_skill);
  if (filters.seniority && filters.seniority.length > 0) params.set('seniority', filters.seniority.join(','));
  if (filters.pay_bands && filters.pay_bands.length > 0) params.set('pay_band', filters.pay_bands.join(','));
  if (filters.yoe_min !== undefined && filters.yoe_min !== null) params.set('yoe_min', String(filters.yoe_min));
  if (filters.yoe_max !== undefined && filters.yoe_max !== null) params.set('yoe_max', String(filters.yoe_max));
  if (filters.include_unspecified_yoe === false) params.set('include_unspecified_yoe', 'false');
  if (filters.search) params.set('search', filters.search);
  if (filters.include_demo) params.set('include_demo', 'true');
  if (filters.page) params.set('page', String(filters.page));
  if (filters.pageSize) params.set('page_size', String(filters.pageSize));

  const res = await fetch(`${API_BASE}/jobs?${params.toString()}`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to fetch jobs: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchJobDetail(jobId: string, signal?: AbortSignal): Promise<JobDetail> {
  const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(jobId)}`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to fetch job detail: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTopSkills(category?: string | null, include_demo: boolean = false, signal?: AbortSignal): Promise<TopSkillsResponse> {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (include_demo) params.set('include_demo', 'true');
  const res = await fetch(`${API_BASE}/skills/top?${params.toString()}`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to fetch top skills: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchTelemetry(category?: string | null, include_demo: boolean = false, signal?: AbortSignal): Promise<TelemetryResponse> {
  const params = new URLSearchParams();
  if (category) params.set('category', category);
  if (include_demo) params.set('include_demo', 'true');
  const res = await fetch(`${API_BASE}/telemetry/skills?${params.toString()}`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to fetch telemetry: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSources(signal?: AbortSignal): Promise<SourceItem[]> {
  const res = await fetch(`${API_BASE}/sources`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to fetch sources: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSyncRuns(limit: number = 20, signal?: AbortSignal): Promise<SyncRunItem[]> {
  const res = await fetch(`${API_BASE}/sync/runs?limit=${limit}`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to fetch sync runs: ${res.statusText}`);
  }
  return res.json();
}

export async function triggerSync(sourceId?: string): Promise<{ status: string; message: string }> {
  const url = sourceId ? `${API_BASE}/sync?source_id=${encodeURIComponent(sourceId)}` : `${API_BASE}/sync`;
  const res = await fetch(url, { method: 'POST' });
  if (!res.ok) {
    throw new Error(`Sync trigger failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCandidateProfile(signal?: AbortSignal): Promise<CandidateProfile> {
  const res = await fetch(`${API_BASE}/candidate/profile`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to fetch candidate profile: ${res.statusText}`);
  }
  return res.json();
}

/** Omit `overall_yoe` to keep the stored value; the backend only writes years when the field is sent. */
export async function updateCandidateProfile(profile: {
  name: string;
  overall_yoe?: number | null;
  skills: Array<Pick<CandidateSkill, 'skill_id' | 'proficiency' | 'evidence_level' | 'notes'>>;
}): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/candidate/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(profile),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `Failed to update profile: ${res.statusText}`);
  }
  return res.json();
}

/** Maps typed skill text to a taxonomy id (C++ -> cpp). Returns null for unknown skills. */
export async function resolveSkill(text: string): Promise<TaxonomySkill | null> {
  const res = await fetch(`${API_BASE}/skills/resolve?q=${encodeURIComponent(text)}`);
  if (res.status === 404) return null;
  if (!res.ok) {
    throw new Error(`Failed to resolve skill: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchGapAnalysis(targetCategory?: string | null, include_demo: boolean = false, signal?: AbortSignal): Promise<GapAnalysisResponse> {
  const params = new URLSearchParams();
  if (targetCategory) params.set('target_category', targetCategory);
  if (include_demo) params.set('include_demo', 'true');
  const res = await fetch(`${API_BASE}/candidate/gap-analysis?${params.toString()}`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to fetch gap analysis: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchCompanies(include_demo: boolean = false, signal?: AbortSignal): Promise<CompanyItem[]> {
  const params = new URLSearchParams();
  if (include_demo) params.set('include_demo', 'true');
  const res = await fetch(`${API_BASE}/companies?${params.toString()}`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to fetch companies: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSyncStatus(signal?: AbortSignal): Promise<SyncStatus> {
  const res = await fetch(`${API_BASE}/sync/status`, { signal });
  if (!res.ok) {
    throw new Error(`Failed to fetch sync status: ${res.statusText}`);
  }
  return res.json();
}

