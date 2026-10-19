export interface Job {
  job_id: string;
  company: string;
  category: string;
  title: string;
  location: string;
  department: string;
  required_skills: string[];
  min_experience_years: number | null;
  apply_url: string;
  updated_at?: string;
  description_snippet?: string;
}

export interface SkillCount {
  skill: string;
  job_count: number;
}

export interface TopSkillsResponse {
  total_jobs_analyzed: number;
  top_skills: SkillCount[];
}

export interface FilterState {
  searchQuery: string;
  category: string | null;
  roleFocus: string[];
  location: string | null;
  selectedSkill: string | null;
}

export type ViewDensity = 'compact' | 'detailed';
