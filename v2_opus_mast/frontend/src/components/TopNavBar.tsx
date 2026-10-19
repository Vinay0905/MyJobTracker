import React, { useRef, useEffect } from 'react';

interface TopNavBarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  onSync: () => void;
  isSyncing: boolean;
  lastSynced: string | null;
}

export const TopNavBar: React.FC<TopNavBarProps> = ({
  searchQuery,
  onSearchChange,
  onSync,
  isSyncing,
  lastSynced,
}) => {
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Command+K shortcut to focus search input
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        searchInputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <header className="bg-surface-container-low flex justify-between items-center w-full px-space-lg py-space-sm border-b border-outline-variant sticky top-0 z-50">
      {/* Brand & Telemetry Indicator */}
      <div className="flex items-center gap-space-md">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-surface-container-highest border border-outline-variant flex items-center justify-center relative">
            <span className="material-symbols-outlined text-primary text-base">radar</span>
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-secondary beacon-pulse" />
          </div>
          <span className="text-lg font-bold tracking-tight text-on-surface">DevRadar</span>
        </div>
        <span className="hidden sm:inline-flex items-center px-1.5 py-0.5 rounded border border-outline-variant bg-surface-container-lowest text-outline font-mono text-[10px]">
          v2.4 Live Ingestion
        </span>
      </div>

      {/* Terminal Search Prompt */}
      <div className="flex-1 max-w-xl mx-space-lg">
        <div className="relative flex items-center">
          <span className="absolute left-3 text-outline font-mono text-sm select-none">&gt;</span>
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search role title, C++, CUDA, Unreal, Dubai..."
            className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg pl-7 pr-12 py-1.5 text-on-surface placeholder:text-outline font-mono text-xs focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
          />
          <kbd className="absolute right-2 px-1.5 py-0.5 rounded bg-surface-container border border-outline-variant text-outline font-mono text-[10px]">
            ⌘K
          </kbd>
        </div>
      </div>

      {/* Actions & Live Controls */}
      <div className="flex items-center gap-space-md">
        <div className="hidden lg:flex items-center gap-2 px-2 py-1 rounded bg-surface-container-lowest border border-outline-variant">
          <span className="w-1.5 h-1.5 rounded-full bg-secondary beacon-pulse" />
          <span className="text-on-surface-variant font-mono text-[11px]">
            {lastSynced ? `Last Synced: ${lastSynced}` : 'Status: Ready'}
          </span>
        </div>

        <button
          onClick={onSync}
          disabled={isSyncing}
          className="flex items-center gap-1.5 bg-primary-container text-on-primary-container px-3 py-1.5 rounded-lg font-mono text-xs font-semibold hover:bg-primary transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className={`material-symbols-outlined text-sm ${isSyncing ? 'animate-spin' : ''}`}>
            sync
          </span>
          <span>{isSyncing ? 'Ingesting...' : 'Sync Career Pages'}</span>
        </button>

        <div className="h-4 w-px bg-outline-variant hidden sm:block" />

        <button
          title="Terminal Logs"
          className="p-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-container rounded transition-colors hidden sm:block"
        >
          <span className="material-symbols-outlined text-base">terminal</span>
        </button>

        <div className="w-7 h-7 rounded-lg border border-outline-variant bg-surface-container-high flex items-center justify-center font-mono text-xs font-bold text-primary">
          OP
        </div>
      </div>
    </header>
  );
};
