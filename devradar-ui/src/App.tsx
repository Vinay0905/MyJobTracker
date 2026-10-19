import React, { useState, useEffect, useCallback } from 'react';
import { Job, SkillCount, FilterState, ViewDensity } from './types';
import { fetchJobs, fetchTopSkills, triggerSync } from './api/client';
import { TopNavBar } from './components/TopNavBar';
import { Sidebar } from './components/Sidebar';
import { AnalyticsStrip } from './components/AnalyticsStrip';
import { FilterBar } from './components/FilterBar';
import { JobGrid } from './components/JobGrid';

// Initial fallback dataset in case the backend hasn't been synced yet
const INITIAL_FALLBACK_JOBS: Job[] = [
  {
    job_id: 'wd_nvidia_001',
    company: 'NVIDIA',
    category: 'Silicon & AI',
    title: 'Principal CUDA Core Architect - Deep Learning',
    location: 'Santa Clara, CA (Hybrid)',
    department: 'Architecture & Silicon',
    required_skills: ['CUDA', 'C++', 'TensorRT', 'PyTorch'],
    min_experience_years: 5,
    apply_url: 'https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite',
    updated_at: '42m ago',
    description_snippet: 'Architecting next-gen tensor core acceleration libraries for Blackwell architecture distributed training clusters and low-precision FP4 GEMM scheduling.',
  },
  {
    job_id: 'gh_epic_002',
    company: 'Epic Games',
    category: 'Game Studio',
    title: 'Senior Engine Programmer - Unreal Engine 5 Core',
    location: 'Cary, NC / Remote',
    department: 'Unreal Engine Systems',
    required_skills: ['C++', 'Unreal Engine', 'Vulkan', 'DirectX'],
    min_experience_years: 4,
    apply_url: 'https://boards-api.greenhouse.io/v1/boards/epicgames/jobs',
    updated_at: '1h ago',
    description_snippet: 'Driving core memory management, asynchronous streaming pipelines, and Nanite geometry virtualization updates inside Unreal Engine 5 source.',
  },
  {
    job_id: 'gh_careem_003',
    company: 'Careem (UAE)',
    category: 'UAE & Middle East',
    title: 'Staff Platform & Kubernetes Infrastructure Engineer',
    location: 'Dubai, UAE',
    department: 'Core Infrastructure',
    required_skills: ['Kubernetes', 'Docker', 'Go', 'AWS', 'Terraform'],
    min_experience_years: 6,
    apply_url: 'https://boards-api.greenhouse.io/v1/boards/careem/jobs',
    updated_at: '2h ago',
    description_snippet: 'Designing scalable multi-region transit and dispatch infrastructure serving millions of daily Super App transactions across GCC and MENA.',
  },
];

const INITIAL_FALLBACK_SKILLS: SkillCount[] = [
  { skill: 'C++', job_count: 42 },
  { skill: 'Python', job_count: 38 },
  { skill: 'CUDA', job_count: 24 },
  { skill: 'Docker', job_count: 21 },
  { skill: 'Unreal Engine', job_count: 18 },
  { skill: 'Kubernetes', job_count: 16 },
  { skill: 'PyTorch', job_count: 15 },
  { skill: 'DirectX', job_count: 12 },
];

export const App: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>(INITIAL_FALLBACK_JOBS);
  const [topSkills, setTopSkills] = useState<SkillCount[]>(INITIAL_FALLBACK_SKILLS);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [lastSynced, setLastSynced] = useState<string | null>('2 mins ago');
  const [viewDensity, setViewDensity] = useState<ViewDensity>('detailed');

  const [filters, setFilters] = useState<FilterState>({
    searchQuery: '',
    category: null,
    roleFocus: [],
    location: null,
    selectedSkill: null,
  });

  // Load jobs from API with fallback
  const loadData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [fetchedJobs, fetchedSkills] = await Promise.all([
        fetchJobs(filters),
        fetchTopSkills(filters.category),
      ]);

      if (fetchedJobs && fetchedJobs.length > 0) {
        setJobs(fetchedJobs);
      }
      if (fetchedSkills && fetchedSkills.top_skills && fetchedSkills.top_skills.length > 0) {
        setTopSkills(fetchedSkills.top_skills);
      }
    } catch {
      // Backend not yet reachable or empty database: filter initial fallback jobs client-side
      let filtered = [...INITIAL_FALLBACK_JOBS];
      if (filters.category) {
        filtered = filtered.filter((j) => j.category.toLowerCase().includes(filters.category!.toLowerCase()));
      }
      if (filters.selectedSkill) {
        filtered = filtered.filter((j) => j.required_skills.includes(filters.selectedSkill!));
      }
      if (filters.searchQuery) {
        const q = filters.searchQuery.toLowerCase();
        filtered = filtered.filter(
          (j) => j.title.toLowerCase().includes(q) || j.company.toLowerCase().includes(q)
        );
      }
      setJobs(filtered);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Sync career pages handler
  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const result = await triggerSync();
      setLastSynced('Just now');
      await loadData();
      console.log(`Synced ${result.total_engineering_jobs} jobs successfully.`);
    } catch (err) {
      console.warn('Sync failed (API server might be offline):', err);
      setLastSynced('Offline Demo Mode');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleToggleRoleFocus = (role: string) => {
    setFilters((prev) => ({
      ...prev,
      roleFocus: prev.roleFocus.includes(role)
        ? prev.roleFocus.filter((r) => r !== role)
        : [...prev.roleFocus, role],
    }));
  };

  const handleResetFilters = () => {
    setFilters({
      searchQuery: '',
      category: null,
      roleFocus: [],
      location: null,
      selectedSkill: null,
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-surface text-on-surface">
      {/* Top Navigation */}
      <TopNavBar
        searchQuery={filters.searchQuery}
        onSearchChange={(q) => setFilters((prev) => ({ ...prev, searchQuery: q }))}
        onSync={handleSync}
        isSyncing={isSyncing}
        lastSynced={lastSynced}
      />

      {/* Main Shell Frame (Sidebar + Main Dashboard) */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Filter Sidebar */}
        <Sidebar
          selectedCategory={filters.category}
          onSelectCategory={(cat) => setFilters((prev) => ({ ...prev, category: cat }))}
          selectedRoleFocus={filters.roleFocus}
          onToggleRoleFocus={handleToggleRoleFocus}
          selectedLocation={filters.location}
          onSelectLocation={(loc) => setFilters((prev) => ({ ...prev, location: loc }))}
          totalRolesCount={jobs.length}
        />

        {/* Analytical Canvas */}
        <main className="flex-1 overflow-y-auto p-space-lg lg:p-6 flex flex-col gap-space-lg bg-surface">
          {/* Top Analytics Strip & Skills Radar */}
          <AnalyticsStrip
            totalJobs={jobs.length}
            topSkills={topSkills}
            selectedSkill={filters.selectedSkill}
            onSelectSkill={(skill) => setFilters((prev) => ({ ...prev, selectedSkill: skill }))}
          />

          {/* Active Filter Chips & View Density */}
          <FilterBar
            totalCount={jobs.length}
            filters={filters}
            onClearCategory={() => setFilters((prev) => ({ ...prev, category: null }))}
            onClearSkill={() => setFilters((prev) => ({ ...prev, selectedSkill: null }))}
            onClearSearch={() => setFilters((prev) => ({ ...prev, searchQuery: '' }))}
            viewDensity={viewDensity}
            onChangeDensity={setViewDensity}
          />

          {/* Live Job Feed Grid */}
          <JobGrid
            jobs={jobs}
            isLoading={isLoading}
            viewDensity={viewDensity}
            selectedSkill={filters.selectedSkill}
            onSelectSkill={(skill) => setFilters((prev) => ({ ...prev, selectedSkill: skill }))}
            onResetFilters={handleResetFilters}
          />
        </main>
      </div>
    </div>
  );
};

export default App;
