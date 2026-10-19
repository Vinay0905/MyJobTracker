import React from 'react';
import { CompanyItem } from '../../types/api';
import { CompanyLogo } from '../common/CompanyLogo';

interface SidebarProps {
  selectedCategory: string | null;
  onSelectCategory: (cat: string | null) => void;
  selectedRoleFocus: string[];
  onToggleRoleFocus: (role: string) => void;
  selectedLocation: string | null;
  onSelectLocation: (loc: string | null) => void;
  totalRolesCount: number;
  sectorCounts?: Record<string, number>;
  companies?: CompanyItem[];
  selectedCompany?: string | null;
  onSelectCompany?: (comp: string | null) => void;
}

const SECTORS = [
  { label: 'All Sectors', value: null },
  { label: 'AAA Game Studios', value: 'Game Studio' },
  { label: 'Silicon & AI', value: 'Silicon & AI' },
  { label: 'UAE & Middle East', value: 'UAE & Middle East' },
];

const ROLES = [
  'AI NPCs & Game AI',
  'Physics & Simulation',
  'GPU / CUDA & Silicon',
  'Edge AI & Embedded ECE',
  'AI Servers & Cloud',
  'Systems / C++',
  'Game Engine / Graphics',
];

const LOCATIONS = [
  'Global',
  'UAE / ME',
  'India',
  'US / EU',
  'Remote Only',
];

export const Sidebar: React.FC<SidebarProps> = ({
  selectedCategory,
  onSelectCategory,
  selectedRoleFocus,
  onToggleRoleFocus,
  selectedLocation,
  onSelectLocation,
  totalRolesCount,
  sectorCounts,
  companies = [],
  selectedCompany = null,
  onSelectCompany,
}) => {
  return (
    <aside className="flex flex-col justify-between h-[calc(100vh-57px)] w-64 border-r border-outline-variant p-space-md bg-surface-container-lowest shrink-0 overflow-y-auto">
      <div className="flex flex-col gap-space-lg">
        {/* Rail Header */}
        <div className="flex flex-col">
          <div className="flex items-center justify-between">
            <span className="text-sm font-bold text-on-surface">Sector & Filter Rail</span>
            <span className="font-mono text-[10px] text-secondary flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-secondary" />
              LIVE
            </span>
          </div>
          <span className="font-mono text-[10px] text-outline mt-0.5">Automated Telemetry</span>
        </div>

        {/* Sector Group */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="font-mono text-[10px] text-outline tracking-wider font-semibold uppercase">
              Target Employers
            </label>
            {selectedCategory && (
              <button
                onClick={() => onSelectCategory(null)}
                className="font-mono text-[10px] text-outline hover:text-primary transition-colors"
              >
                Reset
              </button>
            )}
          </div>
          <div className="flex flex-col gap-1">
            {SECTORS.map((sec) => {
              const isSelected = selectedCategory === sec.value;
              const count = sec.value === null
                ? (sectorCounts?.['All Sectors'] ?? totalRolesCount)
                : (sectorCounts?.[sec.value] ?? (isSelected ? totalRolesCount : undefined));

              return (
                <button
                  key={sec.label}
                  onClick={() => onSelectCategory(sec.value)}
                  className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg font-mono text-xs text-left transition-colors ${
                    isSelected
                      ? 'bg-surface-container border border-primary/40 text-primary font-medium'
                      : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                  }`}
                >
                  <span className="truncate">{sec.label}</span>
                  {count !== undefined && (
                    <span
                      className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${
                        isSelected
                          ? 'bg-primary/20 text-primary font-semibold'
                          : 'bg-surface-container-high text-outline'
                      }`}
                    >
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Company Group */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="font-mono text-[10px] text-outline tracking-wider font-semibold uppercase">
              Target Companies
            </label>
            {selectedCompany && (
              <button
                onClick={() => onSelectCompany?.(null)}
                className="font-mono text-[10px] text-outline hover:text-primary transition-colors"
              >
                Reset
              </button>
            )}
          </div>
          <div className="flex flex-col gap-1 max-h-52 overflow-y-auto pr-1">
            {companies && companies.length > 0 ? (
              companies.map((comp) => {
                const isSelected =
                  selectedCompany?.toLowerCase() === comp.name.toLowerCase() ||
                  selectedCompany?.toLowerCase() === comp.company_id.toLowerCase();
                return (
                  <button
                    key={comp.company_id}
                    onClick={() => onSelectCompany?.(isSelected ? null : comp.name)}
                    className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg font-mono text-xs text-left transition-colors ${
                      isSelected
                        ? 'bg-surface-container border border-primary/40 text-primary font-medium'
                        : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate pr-1">
                      <CompanyLogo
                        company={comp.name}
                        domain={comp.website_url}
                        category={comp.canonical_category}
                        size="sm"
                        className="w-4 h-4 !rounded text-[8px] shrink-0"
                      />
                      <span className="truncate">{comp.name}</span>
                    </div>
                    <span
                      className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${
                        isSelected
                          ? 'bg-primary/20 text-primary font-semibold'
                          : 'bg-surface-container-high text-outline'
                      }`}
                    >
                      {comp.active_jobs_count}
                    </span>
                  </button>
                );
              })
            ) : (
              <span className="font-mono text-[11px] text-outline italic px-2 py-1">Loading companies...</span>
            )}
          </div>
        </div>

        {/* Role Focus Checkboxes */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="font-mono text-[10px] text-outline tracking-wider font-semibold uppercase">
              Role Focus
            </label>
            {selectedRoleFocus.length > 0 && (
              <span className="font-mono text-[10px] text-primary font-semibold">
                {selectedRoleFocus.length} active
              </span>
            )}
          </div>
          <div className="flex flex-col gap-1.5 font-mono text-xs">
            {ROLES.map((role) => {
              const isChecked = selectedRoleFocus.includes(role);
              return (
                <label
                  key={role}
                  className={`flex items-center gap-2 cursor-pointer transition-colors ${
                    isChecked ? 'text-primary font-medium' : 'text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => onToggleRoleFocus(role)}
                    className="w-3.5 h-3.5 rounded bg-surface-container-lowest border-outline-variant text-primary focus:ring-0 focus:ring-offset-0 cursor-pointer"
                  />
                  <span>{role}</span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Geographic Scope */}
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <label className="font-mono text-[10px] text-outline tracking-wider font-semibold uppercase">
              Geographic Scope
            </label>
            {selectedLocation && (
              <button
                onClick={() => onSelectLocation(null)}
                className="font-mono text-[10px] text-outline hover:text-primary transition-colors"
              >
                Reset
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-1 font-mono text-[11px]">
            {LOCATIONS.map((loc) => {
              const isSelected = selectedLocation === loc || (!selectedLocation && loc === 'Global');
              return (
                <span
                  key={loc}
                  onClick={() => onSelectLocation(loc === 'Global' ? null : (selectedLocation === loc ? null : loc))}
                  className={`px-2 py-1 rounded cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-surface-container border border-primary/50 text-primary font-medium shadow-sm'
                      : 'bg-surface-container-lowest border border-outline-variant text-on-surface-variant hover:text-on-surface'
                  }`}
                >
                  {loc}
                </span>
              );
            })}
          </div>
        </div>
      </div>

      {/* Rail Footer */}
      <div className="pt-4 border-t border-outline-variant/60 flex flex-col gap-1 font-mono text-xs">
        <div className="text-secondary px-3 py-1.5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-base">sensors</span>
            <span>Crawler: Active</span>
          </div>
          <span className="font-mono text-[10px] text-outline">FastAPI</span>
        </div>
      </div>
    </aside>
  );
};
