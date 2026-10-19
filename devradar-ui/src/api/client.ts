import { Job, TopSkillsResponse, FilterState } from '../types';

const API_BASE = '/api';

export async function fetchJobs(filters: FilterState, signal?: AbortSignal): Promise<Job[]> {
  const params = new URLSearchParams();
  if (filters.category) params.set('category', filters.category);
  if (filters.selectedSkill) params.set('skill', filters.selectedSkill);
  if (filters.location && filters.location !== 'Global') params.set('location', filters.location);

  const url = `${API_BASE}/jobs?${params.toString()}`;
  const response = await fetch(url, { credentials: 'omit', signal });

  if (!response.ok) {
    throw new Error(`Failed to fetch jobs: ${response.statusText}`);
  }

  const data = await response.json();
  let jobs: Job[] = data.jobs || [];

  // Local search filter for title or skills
  if (filters.searchQuery.trim()) {
    const q = filters.searchQuery.toLowerCase();
    jobs = jobs.filter(
      (job) =>
        job.title.toLowerCase().includes(q) ||
        job.company.toLowerCase().includes(q) ||
        job.location.toLowerCase().includes(q) ||
        job.required_skills.some((s) => s.toLowerCase().includes(q))
    );
  }

  // Filter by role focus checkboxes if any are selected
  if (filters.roleFocus.length > 0) {
    jobs = jobs.filter((job) => {
      const lowerTitle = job.title.toLowerCase();
      return filters.roleFocus.some((role) => {
        if (role === 'Systems / C++') return lowerTitle.includes('c++') || lowerTitle.includes('system') || job.required_skills.includes('C++');
        if (role === 'AI & GPU / CUDA') return lowerTitle.includes('ai') || lowerTitle.includes('gpu') || lowerTitle.includes('cuda') || job.required_skills.includes('CUDA');
        if (role === 'Game Engine / Graphics') return lowerTitle.includes('game') || lowerTitle.includes('engine') || lowerTitle.includes('graphics') || job.required_skills.includes('Unreal Engine');
        if (role === 'Cloud & DevOps') return lowerTitle.includes('cloud') || lowerTitle.includes('devops') || lowerTitle.includes('sre') || job.required_skills.includes('Docker');
        if (role === 'Embedded / Firmware') return lowerTitle.includes('embedded') || lowerTitle.includes('firmware') || lowerTitle.includes('kernel') || job.required_skills.includes('RTOS');
        return true;
      });
    });
  }

  return jobs;
}

export async function fetchTopSkills(category?: string | null, signal?: AbortSignal): Promise<TopSkillsResponse> {
  const params = new URLSearchParams();
  if (category) params.set('category', category);

  const url = `${API_BASE}/skills/top?${params.toString()}`;
  const response = await fetch(url, { credentials: 'omit', signal });

  if (!response.ok) {
    throw new Error(`Failed to fetch top skills: ${response.statusText}`);
  }

  return response.json();
}

export async function triggerSync(): Promise<{ status: string; total_engineering_jobs: number }> {
  const response = await fetch(`${API_BASE}/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Sync failed: ${response.statusText}`);
  }

  return response.json();
}
