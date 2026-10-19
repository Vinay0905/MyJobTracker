import React from 'react';
import { Job, ViewDensity } from '../types';

interface JobCardProps {
  job: Job;
  viewDensity: ViewDensity;
  selectedSkill: string | null;
  onSelectSkill: (skill: string) => void;
}

export const JobCard: React.FC<JobCardProps> = ({
  job,
  viewDensity,
  selectedSkill,
  onSelectSkill,
}) => {
  const isGameStudio = job.category.toLowerCase().includes('game');
  const isSilicon = job.category.toLowerCase().includes('silicon') || job.category.toLowerCase().includes('ai');

  const borderAccentColor = isSilicon
    ? 'bg-secondary'
    : isGameStudio
    ? 'bg-tertiary'
    : 'bg-primary';

  const badgeTextColor = isSilicon
    ? 'text-secondary'
    : isGameStudio
    ? 'text-tertiary'
    : 'text-primary';

  // Get 2-letter initials
  const initials = job.company
    .split(' ')
    .map((word) => word[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  return (
    <article className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant hover:border-outline hover:bg-surface-container transition-all flex flex-col justify-between relative group">
      {/* Category indicator line */}
      <div className={`absolute left-0 top-3 bottom-3 w-1 ${borderAccentColor} rounded-r`} />

      <div>
        {/* Card Header: Org Badge + Delta */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <div
              className={`w-8 h-8 rounded bg-surface-container-highest border border-outline-variant flex items-center justify-center font-bold ${badgeTextColor} font-mono text-xs`}
            >
              {initials}
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-semibold text-on-surface">{job.company}</span>
                <span className="text-outline text-xs">•</span>
                <span className={`font-mono text-[10px] ${badgeTextColor} font-medium`}>
                  {job.category}
                </span>
              </div>
              <h3 className="text-sm font-bold text-on-surface group-hover:text-primary transition-colors mt-0.5">
                {job.title}
              </h3>
            </div>
          </div>

          <span className="font-mono text-[10px] text-outline px-1.5 py-0.5 rounded bg-surface-container-lowest border border-outline-variant/60 shrink-0">
            {job.updated_at || 'Recent'}
          </span>
        </div>

        {/* Metadata Strip */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 my-2.5 font-mono text-[11px] text-on-surface-variant">
          <span className="flex items-center gap-1">
            <span className="material-symbols-outlined text-xs text-outline">location_on</span>
            {job.location}
          </span>
          {job.min_experience_years && (
            <>
              <span>•</span>
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-xs text-outline">work_history</span>
                {job.min_experience_years}+ YOE
              </span>
            </>
          )}
          {job.department && (
            <>
              <span>•</span>
              <span className="text-outline truncate max-w-[140px]">{job.department}</span>
            </>
          )}
        </div>

        {/* Required Skill Chips */}
        {job.required_skills && job.required_skills.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {job.required_skills.map((skill) => {
              const isSelected = selectedSkill === skill;
              return (
                <button
                  key={skill}
                  onClick={() => onSelectSkill(skill)}
                  className={`font-mono text-[10px] px-2 py-0.5 rounded transition-colors ${
                    isSelected
                      ? 'bg-primary text-on-primary font-bold'
                      : 'bg-surface-container-high border border-outline-variant text-on-surface hover:border-primary/50'
                  }`}
                >
                  {skill}
                </button>
              );
            })}
          </div>
        )}

        {/* Detailed description if selected */}
        {viewDensity === 'detailed' && job.description_snippet && (
          <p className="text-xs text-on-surface-variant leading-relaxed line-clamp-2 mt-2">
            {job.description_snippet}
          </p>
        )}
      </div>

      {/* Card Footer CTA & Scrape Origin */}
      <div className="pt-3 mt-3 border-t border-outline-variant/60 flex items-center justify-between font-mono text-[10px]">
        <span className="text-outline truncate max-w-[200px]">ID: {job.job_id}</span>
        <a
          href={job.apply_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-primary hover:text-white font-semibold transition-colors"
        >
          <span>Direct Career Page</span>
          <span className="material-symbols-outlined text-[12px]">arrow_outward</span>
        </a>
      </div>
    </article>
  );
};
