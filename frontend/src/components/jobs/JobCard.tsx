import React from 'react';
import { JobListItem } from '../../types/api';
import { CompanyLogo } from '../common/CompanyLogo';

interface JobCardProps {
  job: JobListItem;
  onInspect: (jobId: string) => void;
  onSelectSkill?: (skillId: string) => void;
  isSelected?: boolean;
}

const formatAmount = (value: number): string =>
  value >= 1000 ? `${Math.round(value / 1000)}k` : String(Math.round(value));

/** Formats a stated annual salary in its own currency; returns null when the posting states none. */
export const formatPay = (min?: number | null, max?: number | null, currency?: string | null): string | null => {
  if (min === null || min === undefined || !currency) return null;
  const top = max ?? min;
  return top !== min ? `${currency} ${formatAmount(min)}–${formatAmount(top)}` : `${currency} ${formatAmount(min)}`;
};

export const JobCard: React.FC<JobCardProps> = ({ job, onInspect, onSelectSkill, isSelected = false }) => {
  const isGameStudio = job.canonical_category.toLowerCase().includes('game');
  const isSilicon =
    job.canonical_category.toLowerCase().includes('silicon') ||
    job.canonical_category.toLowerCase().includes('ai');

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

  const postedDate = job.source_created_at ? new Date(job.source_created_at) : null;
  const seniority = job.seniority && job.seniority !== 'unspecified' ? job.seniority : null;
  const payLabel = formatPay(job.salary_min, job.salary_max, job.salary_currency);

  return (
    <article
      className={`p-space-md rounded-xl transition-all flex flex-col justify-between relative group ${
        isSelected
          ? 'bg-surface-container border-2 border-primary ring-2 ring-primary/30 shadow-lg shadow-primary/10'
          : 'bg-surface-container-low border border-outline-variant hover:border-outline hover:bg-surface-container'
      }`}
    >
      <div className={`absolute left-0 top-3 bottom-3 w-1 ${borderAccentColor} rounded-r`} />

      <div>
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2.5">
            <CompanyLogo
              company={job.company}
              domain={job.company_domain}
              category={job.canonical_category}
              size="md"
            />
            <div>
              <div className="flex items-center gap-1.5">
                <span className="text-sm font-semibold text-on-surface">{job.company}</span>
                <span className="text-outline text-xs">•</span>
                <span className={`font-mono text-[10px] ${badgeTextColor} font-medium`}>
                  {job.canonical_category}
                </span>
                {job.is_demo && (
                  <span
                    className="font-mono text-[9px] px-1.5 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/40 font-bold uppercase"
                    title="Synthetic demo fixture, not a live listing from this employer"
                  >
                    Demo
                  </span>
                )}
              </div>
              <h3
                onClick={() => onInspect(job.job_id)}
                className="text-sm font-bold text-on-surface group-hover:text-primary transition-colors mt-0.5 cursor-pointer"
              >
                {job.title}
              </h3>
            </div>
          </div>

          <span
            className="font-mono text-[10px] text-outline px-1.5 py-0.5 rounded bg-surface-container-lowest border border-outline-variant/60 shrink-0"
            title={postedDate ? 'Posted date reported by the employer' : 'Employer did not report a posted date; first seen by DevRadar'}
          >
            {postedDate
              ? `Posted ${postedDate.toLocaleDateString()}`
              : `Seen ${new Date(job.first_seen_at).toLocaleDateString()}`}
          </span>
        </div>

        {/* Metadata */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 my-2.5 font-mono text-[11px] text-on-surface-variant">
          <span className="flex items-center gap-1">
            <span className="material-symbols-outlined text-xs text-outline">location_on</span>
            {job.location}
          </span>
          <span>•</span>
          <span className="flex items-center gap-1" title="Minimum years from the posting's requirement lines">
            <span className="material-symbols-outlined text-xs text-outline">work_history</span>
            {job.primary_min_yoe !== null && job.primary_min_yoe !== undefined
              ? `${job.primary_min_yoe}+ YOE`
              : <span className="text-outline italic">YOE unspecified</span>}
          </span>
          {seniority && (
            <>
              <span>•</span>
              <span className="capitalize text-primary">{seniority}</span>
            </>
          )}
          {job.work_arrangement && job.work_arrangement !== 'unknown' && (
            <>
              <span>•</span>
              <span className="capitalize text-outline">{job.work_arrangement}</span>
            </>
          )}
          {payLabel && (
            <>
              <span>•</span>
              <span className="flex items-center gap-1 text-secondary" title="Annual salary stated in the posting">
                <span className="material-symbols-outlined text-xs">payments</span>
                {payLabel}
              </span>
            </>
          )}
        </div>

        {/* Required Skills Chips */}
        {job.required_skills && job.required_skills.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {job.required_skills.map((s) => (
              <span
                key={s}
                onClick={() => onSelectSkill && onSelectSkill(s)}
                className="font-mono text-[10px] px-2 py-0.5 rounded bg-secondary/10 border border-secondary/25 text-secondary font-medium cursor-pointer hover:bg-secondary/20 transition-colors"
              >
                {s.toUpperCase()}
              </span>
            ))}
            {job.preferred_skills &&
              job.preferred_skills.map((s) => (
                <span
                  key={s}
                  onClick={() => onSelectSkill && onSelectSkill(s)}
                  className="font-mono text-[10px] px-2 py-0.5 rounded bg-surface-container-high border border-outline-variant text-on-surface-variant cursor-pointer hover:border-primary/40 transition-colors"
                >
                  +{s.toUpperCase()}
                </span>
              ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="pt-3 mt-3 border-t border-outline-variant/60 flex items-center justify-between font-mono text-[11px]">
        <button
          onClick={() => onInspect(job.job_id)}
          className="inline-flex items-center gap-1 text-primary hover:text-white transition-colors"
        >
          <span className="material-symbols-outlined text-sm">visibility</span>
          <span>Inspect Evidence</span>
        </button>

        <a
          href={
            job.apply_url && job.apply_url.trim().startsWith('http')
              ? job.apply_url
              : `https://www.google.com/search?q=${encodeURIComponent(job.company + ' careers ' + job.title)}`
          }
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-on-surface-variant hover:text-white font-semibold transition-colors"
          title={job.apply_url && job.apply_url.startsWith('http') ? 'Apply on employer career portal' : 'Search job on Google'}
        >
          <span>Direct Career Page</span>
          <span className="material-symbols-outlined text-xs">arrow_outward</span>
        </a>
      </div>
    </article>
  );
};
