import React from 'react';
import { SkillCount } from '../types';
import { SkillRadar } from './SkillRadar';

interface AnalyticsStripProps {
  totalJobs: number;
  topSkills: SkillCount[];
  selectedSkill: string | null;
  onSelectSkill: (skill: string | null) => void;
}

export const AnalyticsStrip: React.FC<AnalyticsStripProps> = ({
  totalJobs,
  topSkills,
  selectedSkill,
  onSelectSkill,
}) => {
  const topSkillName = topSkills.length > 0 ? topSkills[0].skill : 'C++ & Python';
  const topSkillPercentage = totalJobs > 0 && topSkills.length > 0
    ? Math.round((topSkills[0].job_count / totalJobs) * 100)
    : 64;

  return (
    <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-12 gap-space-md">
      {/* Metric 1: Total Live Openings */}
      <div className="xl:col-span-3 p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between relative overflow-hidden">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] text-outline uppercase tracking-wider font-semibold">
            Total Live Openings
          </span>
          <span className="material-symbols-outlined text-primary text-lg">travel_explore</span>
        </div>
        <div className="flex items-baseline gap-3 my-2">
          <span className="text-3xl font-bold tracking-tight text-on-surface">{totalJobs}</span>
          <span className="inline-flex items-center font-mono text-[11px] text-secondary font-semibold bg-secondary/10 px-1.5 py-0.5 rounded border border-secondary/20">
            Live Stream
          </span>
        </div>
        <div className="flex items-center justify-between font-mono text-[10px] text-outline">
          <span>Real-time crawler match</span>
          <span className="text-on-surface-variant font-medium">FastAPI Engine</span>
        </div>
      </div>

      {/* Metric 2: New Positions (24h) */}
      <div className="xl:col-span-3 p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between relative overflow-hidden">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] text-outline uppercase tracking-wider font-semibold">
            Active Workspaces
          </span>
          <span className="material-symbols-outlined text-secondary text-lg">bolt</span>
        </div>
        <div className="flex items-baseline gap-3 my-2">
          <span className="text-3xl font-bold tracking-tight text-on-surface">3 Tier-1 Hubs</span>
          <span className="inline-flex items-center font-mono text-[11px] text-secondary font-semibold bg-secondary/10 px-1.5 py-0.5 rounded border border-secondary/20">
            Active
          </span>
        </div>
        <div className="flex items-center justify-between font-mono text-[10px] text-outline">
          <span>Workday & Greenhouse APIs</span>
          <span className="text-secondary font-medium">Async httpx</span>
        </div>
      </div>

      {/* Metric 3: Most Requested Skill */}
      <div className="xl:col-span-3 p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between relative overflow-hidden">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[10px] text-outline uppercase tracking-wider font-semibold">
            Most Demanded Tech
          </span>
          <span className="material-symbols-outlined text-tertiary text-lg">memory</span>
        </div>
        <div className="flex flex-col my-1">
          <span className="text-xl font-bold text-on-surface truncate">{topSkillName}</span>
          <span className="font-mono text-[11px] text-primary font-medium mt-0.5">
            Present in ~{topSkillPercentage}% of engineering specs
          </span>
        </div>
        <div className="flex items-center justify-between font-mono text-[10px] text-outline">
          <span>Automated Regex Taxonomy</span>
          <span className="text-on-surface-variant">0ms Overhead</span>
        </div>
      </div>

      {/* Metric 4: Top Skills Radar */}
      <SkillRadar
        topSkills={topSkills}
        totalJobs={totalJobs}
        selectedSkill={selectedSkill}
        onSelectSkill={onSelectSkill}
      />
    </section>
  );
};
