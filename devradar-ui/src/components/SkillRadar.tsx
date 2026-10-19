import React from 'react';
import { SkillCount } from '../types';

interface SkillRadarProps {
  topSkills: SkillCount[];
  totalJobs: number;
  selectedSkill: string | null;
  onSelectSkill: (skill: string | null) => void;
}

export const SkillRadar: React.FC<SkillRadarProps> = ({
  topSkills,
  totalJobs,
  selectedSkill,
  onSelectSkill,
}) => {
  const primarySkills = topSkills.slice(0, 4);
  const microSkills = topSkills.slice(4, 10);

  const maxCount = primarySkills.length > 0 ? primarySkills[0].job_count : 1;

  const getBarColor = (index: number) => {
    if (index === 0) return 'bg-tertiary';
    if (index === 1) return 'bg-secondary';
    if (index === 2) return 'bg-primary';
    return 'bg-tertiary';
  };

  return (
    <div className="xl:col-span-3 p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <span className="material-symbols-outlined text-primary text-base">hub</span>
            <span className="font-mono text-[10px] text-on-surface font-semibold tracking-wider uppercase">
              Top Skills Radar
            </span>
          </div>
          <span className="font-mono text-[10px] text-outline">
            {topSkills.length} Indexed
          </span>
        </div>

        {/* Primary Horizontal Bars */}
        <div className="space-y-1.5">
          {primarySkills.map((item, idx) => {
            const isSelected = selectedSkill === item.skill;
            const percentage = Math.min(100, Math.round((item.job_count / maxCount) * 100));

            return (
              <div
                key={item.skill}
                onClick={() => onSelectSkill(isSelected ? null : item.skill)}
                className={`group cursor-pointer p-1 rounded transition-colors ${
                  isSelected ? 'bg-surface-container-high' : 'hover:bg-surface-container'
                }`}
              >
                <div className="flex justify-between font-mono text-[11px] mb-0.5 text-on-surface-variant group-hover:text-on-surface">
                  <span className={`font-medium ${isSelected ? 'text-primary font-bold' : ''}`}>
                    {item.skill}
                  </span>
                  <span className="text-outline font-mono text-[10px]">
                    {item.job_count} jobs
                  </span>
                </div>
                <div className="w-full bg-surface-container-lowest h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`${getBarColor(idx)} h-full rounded-full transition-all duration-500`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Micro Skill Chips */}
      {microSkills.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-2 border-t border-outline-variant/40 mt-2">
          {microSkills.map((item) => {
            const isSelected = selectedSkill === item.skill;
            return (
              <button
                key={item.skill}
                onClick={() => onSelectSkill(isSelected ? null : item.skill)}
                className={`font-mono text-[10px] px-1.5 py-0.5 rounded border transition-colors ${
                  isSelected
                    ? 'bg-primary text-on-primary border-primary'
                    : 'bg-surface-container border-outline-variant/60 text-on-surface-variant hover:text-on-surface'
                }`}
              >
                {item.skill} ({item.job_count})
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
