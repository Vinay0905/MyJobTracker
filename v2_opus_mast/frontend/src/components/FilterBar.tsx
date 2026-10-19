import React from 'react';
import { FilterState, ViewDensity } from '../types';

interface FilterBarProps {
  totalCount: number;
  filters: FilterState;
  onClearCategory: () => void;
  onClearSkill: () => void;
  onClearSearch: () => void;
  viewDensity: ViewDensity;
  onChangeDensity: (density: ViewDensity) => void;
}

export const FilterBar: React.FC<FilterBarProps> = ({
  totalCount,
  filters,
  onClearCategory,
  onClearSkill,
  onClearSearch,
  viewDensity,
  onChangeDensity,
}) => {
  return (
    <section className="flex flex-wrap items-center justify-between gap-space-md py-2 border-y border-outline-variant/60">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-sm text-on-surface font-semibold">
          Displaying {totalCount} Live Roles
        </span>

        {/* Active Pill Tags */}
        <div className="flex flex-wrap items-center gap-1.5 ml-2 font-mono text-[11px]">
          {filters.category && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container border border-outline-variant text-on-surface-variant">
              <span>Sector: {filters.category}</span>
              <button onClick={onClearCategory} className="hover:text-on-surface">
                <span className="material-symbols-outlined text-[12px] leading-none">close</span>
              </button>
            </span>
          )}

          {filters.selectedSkill && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-primary/10 border border-primary/30 text-primary">
              <span>Skill: {filters.selectedSkill}</span>
              <button onClick={onClearSkill} className="hover:text-white">
                <span className="material-symbols-outlined text-[12px] leading-none">close</span>
              </button>
            </span>
          )}

          {filters.searchQuery && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-container border border-outline-variant text-on-surface-variant">
              <span>Search: "{filters.searchQuery}"</span>
              <button onClick={onClearSearch} className="hover:text-on-surface">
                <span className="material-symbols-outlined text-[12px] leading-none">close</span>
              </button>
            </span>
          )}
        </div>
      </div>

      {/* View Density Switchers */}
      <div className="flex items-center gap-2">
        <div className="flex items-center p-0.5 rounded-lg bg-surface-container-lowest border border-outline-variant font-mono text-[11px]">
          <button
            onClick={() => onChangeDensity('compact')}
            className={`px-2.5 py-1 rounded flex items-center gap-1 transition-colors ${
              viewDensity === 'compact'
                ? 'bg-surface-container border border-outline-variant text-primary font-medium'
                : 'text-outline hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-sm">density_small</span>
            <span>Compact</span>
          </button>
          <button
            onClick={() => onChangeDensity('detailed')}
            className={`px-2.5 py-1 rounded flex items-center gap-1 transition-colors ${
              viewDensity === 'detailed'
                ? 'bg-surface-container border border-outline-variant text-primary font-medium'
                : 'text-outline hover:text-on-surface'
            }`}
          >
            <span className="material-symbols-outlined text-sm">density_medium</span>
            <span>Detailed</span>
          </button>
        </div>
      </div>
    </section>
  );
};
