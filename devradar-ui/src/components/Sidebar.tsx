import React from 'react';

interface SidebarProps {
  selectedCategory: string | null;
  onSelectCategory: (category: string | null) => void;
  selectedRoleFocus: string[];
  onToggleRoleFocus: (role: string) => void;
  selectedLocation: string | null;
  onSelectLocation: (loc: string | null) => void;
  totalRolesCount: number;
}

const SECTORS = [
  { label: 'All Sectors', value: null },
  { label: 'AAA Game Studios', value: 'Game Studio' },
  { label: 'Silicon & AI', value: 'Silicon & AI' },
  { label: 'UAE & Middle East', value: 'UAE & Middle East' },
];

const ROLES = [
  'Systems / C++',
  'AI & GPU / CUDA',
  'Game Engine / Graphics',
  'Cloud & DevOps',
  'Embedded / Firmware',
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
}) => {
  return (
    <aside className="flex flex-col justify-between h-[calc(100vh-53px)] w-64 border-r border-outline-variant p-space-md bg-surface-container-lowest shrink-0 overflow-y-auto">
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
          <span className="font-mono text-[10px] text-outline mt-0.5">Telemetry Active</span>
        </div>

        {/* Global Navigation Section */}
        <nav className="flex flex-col gap-1 font-mono text-xs">
          <a
            href="#"
            className="text-primary bg-surface-container border-l-2 border-primary px-3 py-2 rounded-r flex items-center gap-2"
          >
            <span className="material-symbols-outlined text-base">radar</span>
            <span>Live Stream</span>
          </a>
          <a
            href="#"
            className="text-on-surface-variant hover:bg-surface-container hover:text-on-surface px-3 py-2 rounded flex items-center gap-2 transition-colors"
          >
            <span className="material-symbols-outlined text-base">query_stats</span>
            <span>Telemetry</span>
          </a>
          <a
            href="#"
            className="text-on-surface-variant hover:bg-surface-container hover:text-on-surface px-3 py-2 rounded flex items-center gap-2 transition-colors"
          >
            <span className="material-symbols-outlined text-base">bookmark</span>
            <span>Saved Roles</span>
          </a>
        </nav>

        <div className="h-px bg-outline-variant/60" />

        {/* Sector Group */}
        <div className="flex flex-col gap-2">
          <label className="font-mono text-[10px] text-outline tracking-wider font-semibold uppercase">
            Sectors
          </label>
          <div className="flex flex-col gap-1">
            {SECTORS.map((sec) => {
              const isSelected = selectedCategory === sec.value;
              return (
                <button
                  key={sec.label}
                  onClick={() => onSelectCategory(sec.value)}
                  className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg font-mono text-xs text-left transition-colors ${
                    isSelected
                      ? 'bg-surface-container border border-primary/40 text-primary'
                      : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                  }`}
                >
                  <span className="truncate">{sec.label}</span>
                  {isSelected && (
                    <span className="font-mono text-[10px] bg-surface-container-high text-primary px-1.5 py-0.5 rounded">
                      {totalRolesCount}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Role Focus Checkboxes */}
        <div className="flex flex-col gap-2">
          <label className="font-mono text-[10px] text-outline tracking-wider font-semibold uppercase">
            Role Focus
          </label>
          <div className="flex flex-col gap-1.5 font-mono text-xs">
            {ROLES.map((role) => {
              const isChecked = selectedRoleFocus.includes(role);
              return (
                <label
                  key={role}
                  className="flex items-center gap-2 cursor-pointer text-on-surface-variant hover:text-on-surface"
                >
                  <input
                    type="checkbox"
                    checked={isChecked}
                    onChange={() => onToggleRoleFocus(role)}
                    className="w-3.5 h-3.5 rounded bg-surface-container-lowest border-outline-variant text-primary focus:ring-0 focus:ring-offset-0"
                  />
                  <span>{role}</span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Geographic Scope */}
        <div className="flex flex-col gap-2">
          <label className="font-mono text-[10px] text-outline tracking-wider font-semibold uppercase">
            Geographic Scope
          </label>
          <div className="flex flex-wrap gap-1 font-mono text-[11px]">
            {LOCATIONS.map((loc) => {
              const isSelected = selectedLocation === loc || (!selectedLocation && loc === 'Global');
              return (
                <span
                  key={loc}
                  onClick={() => onSelectLocation(loc === 'Global' ? null : loc)}
                  className={`px-2 py-1 rounded cursor-pointer transition-colors ${
                    isSelected
                      ? 'bg-surface-container border border-primary/50 text-primary font-medium'
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
            <span>Crawler: Online</span>
          </div>
          <span className="font-mono text-[10px] text-outline">FastAPI</span>
        </div>
      </div>
    </aside>
  );
};
