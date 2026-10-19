import React from 'react';
import { Job, ViewDensity } from '../types';
import { JobCard } from './JobCard';

interface JobGridProps {
  jobs: Job[];
  isLoading: boolean;
  viewDensity: ViewDensity;
  selectedSkill: string | null;
  onSelectSkill: (skill: string) => void;
  onResetFilters: () => void;
}

export const JobGrid: React.FC<JobGridProps> = ({
  jobs,
  isLoading,
  viewDensity,
  selectedSkill,
  onSelectSkill,
  onResetFilters,
}) => {
  if (isLoading) {
    return (
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-space-md pb-space-xl">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant animate-pulse h-48 flex flex-col justify-between"
          >
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded bg-surface-container-high" />
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-surface-container-high rounded w-1/3" />
                <div className="h-5 bg-surface-container-highest rounded w-3/4" />
              </div>
            </div>
            <div className="flex gap-2">
              <div className="h-5 w-16 bg-surface-container-high rounded" />
              <div className="h-5 w-16 bg-surface-container-high rounded" />
              <div className="h-5 w-16 bg-surface-container-high rounded" />
            </div>
            <div className="h-4 bg-surface-container-high rounded w-1/4" />
          </div>
        ))}
      </section>
    );
  }

  if (jobs.length === 0) {
    return (
      <section className="p-12 text-center rounded-xl bg-surface-container-low border border-outline-variant flex flex-col items-center justify-center gap-3">
        <span className="material-symbols-outlined text-4xl text-outline">search_off</span>
        <h4 className="text-base font-semibold text-on-surface">No Engineering Roles Found</h4>
        <p className="text-xs text-on-surface-variant max-w-sm">
          No open roles match your current sector, role focus, or skill criteria. Try relaxing your filters or triggering a fresh career page crawl.
        </p>
        <button
          onClick={onResetFilters}
          className="mt-2 px-3 py-1.5 rounded-lg bg-surface-container-high border border-outline-variant text-primary font-mono text-xs hover:bg-surface-container"
        >
          Reset All Filters
        </button>
      </section>
    );
  }

  return (
    <section className="grid grid-cols-1 lg:grid-cols-2 gap-space-md pb-space-xl">
      {jobs.map((job) => (
        <JobCard
          key={job.job_id}
          job={job}
          viewDensity={viewDensity}
          selectedSkill={selectedSkill}
          onSelectSkill={onSelectSkill}
        />
      ))}
    </section>
  );
};
