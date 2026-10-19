import React, { useRef, useEffect, useState } from 'react';
import { ViewTab } from '../../types/api';
import { playKeyClick, isSoundEnabled, toggleSound } from '../../utils/audio';

interface TopNavbarProps {
  currentTab: ViewTab;
  onSelectTab: (tab: ViewTab) => void;
  searchQuery: string;
  onSearchChange: (q: string) => void;
  onSync: () => void;
  isSyncing: boolean;
  lastSyncedMessage: string;
  includeDemo: boolean;
  onToggleDemo: () => void;
  onToggleShortcuts?: () => void;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({
  currentTab,
  onSelectTab,
  searchQuery,
  onSearchChange,
  onSync,
  isSyncing,
  lastSyncedMessage,
  includeDemo,
  onToggleDemo,
  onToggleShortcuts,
}) => {
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [soundActive, setSoundActive] = useState<boolean>(isSoundEnabled());

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

  const handleSoundToggle = () => {
    const state = toggleSound();
    setSoundActive(state);
    if (state) playKeyClick();
  };

  const tabs: Array<{ id: ViewTab; label: string; icon: string }> = [
    { id: 'radar', label: 'Job Radar', icon: 'radar' },
    { id: 'constellation', label: 'Constellation', icon: 'hub' },
    { id: 'salary', label: 'Stack Salary & UAE', icon: 'payments' },
    { id: 'telemetry', label: 'Market Telemetry', icon: 'query_stats' },
    { id: 'gap-analyzer', label: '1-Skill Away', icon: 'psychology' },
    { id: 'sources', label: 'Source Health', icon: 'dns' },
  ];

  return (
    <header className="bg-surface-container-low flex flex-wrap justify-between items-center w-full px-space-lg py-2.5 border-b border-outline-variant sticky top-0 z-40 gap-3">
      {/* Brand & Ingestion Tag */}
      <div className="flex items-center gap-space-md">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-surface-container-highest border border-outline-variant flex items-center justify-center relative">
            <span className="material-symbols-outlined text-primary text-base">radar</span>
            <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-secondary beacon-pulse" />
          </div>
          <span className="text-lg font-bold tracking-tight text-on-surface">DevRadar</span>
        </div>

        {/* Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-surface-container-lowest p-1 rounded-lg border border-outline-variant font-mono text-xs">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => {
                playKeyClick();
                onSelectTab(t.id);
              }}
              className={`flex items-center gap-1.5 px-3 py-1 rounded-md transition-colors ${
                currentTab === t.id
                  ? 'bg-surface-container-high text-primary font-semibold shadow-sm'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              <span className="material-symbols-outlined text-sm">{t.icon}</span>
              <span>{t.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Terminal Search Prompt */}
      {currentTab === 'radar' && (
        <div className="flex-1 max-w-md mx-2">
          <div className="relative flex items-center">
            <span className="absolute left-3 text-outline font-mono text-xs select-none">&gt;</span>
            <input
              ref={searchInputRef}
              type="text"
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="Search title, C++, CUDA, Unreal, Dubai..."
              className="w-full bg-surface-container-lowest border border-outline-variant rounded-lg pl-7 pr-12 py-1.5 text-on-surface placeholder:text-outline font-mono text-xs focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
            />
            <kbd className="absolute right-2 px-1.5 py-0.5 rounded bg-surface-container border border-outline-variant text-outline font-mono text-[10px]">
              ⌘K
            </kbd>
          </div>
        </div>
      )}

      {/* Trailing Controls & Sync */}
      <div className="flex items-center gap-space-md">
        <div className="hidden lg:flex items-center gap-2 px-2.5 py-1 rounded bg-surface-container-lowest border border-outline-variant">
          <span className="w-1.5 h-1.5 rounded-full bg-secondary beacon-pulse" />
          <span className="text-on-surface-variant font-mono text-[11px]">{lastSyncedMessage}</span>
        </div>

        <button
          onClick={onToggleDemo}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg font-mono text-xs font-semibold border transition-colors ${
            includeDemo
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-sm'
              : 'bg-surface-container-lowest text-outline hover:text-on-surface border-outline-variant'
          }`}
          title="Toggle synthetic baseline fixtures (is_demo=True)"
        >
          <span className={`w-2 h-2 rounded-full ${includeDemo ? 'bg-amber-400 animate-pulse' : 'bg-outline'}`} />
          <span>Demo: {includeDemo ? 'ON' : 'OFF'}</span>
        </button>

        <button
          onClick={onSync}
          disabled={isSyncing}
          className="flex items-center gap-1.5 bg-primary-container text-on-primary-container px-3 py-1.5 rounded-lg font-mono text-xs font-semibold hover:bg-primary transition-colors shadow-sm disabled:opacity-50"
        >
          <span className={`material-symbols-outlined text-sm ${isSyncing ? 'animate-spin' : ''}`}>
            sync
          </span>
          <span>{isSyncing ? 'Ingesting...' : 'Sync Career Pages'}</span>
        </button>

        {/* Synthesized Terminal Audio Toggle */}
        <button
          onClick={handleSoundToggle}
          className={`p-1.5 rounded-lg border font-mono text-xs transition-colors flex items-center justify-center ${
            soundActive
              ? 'bg-secondary/20 text-secondary border-secondary/40 shadow-sm'
              : 'bg-surface-container-lowest text-outline hover:text-on-surface border-outline-variant'
          }`}
          title={soundActive ? 'Mute terminal audio (M)' : 'Enable terminal audio (M)'}
        >
          <span className="material-symbols-outlined text-base">
            {soundActive ? 'volume_up' : 'volume_off'}
          </span>
        </button>

        {/* Keyboard Shortcuts Cheatsheet Trigger */}
        {onToggleShortcuts && (
          <button
            onClick={() => {
              playKeyClick();
              onToggleShortcuts();
            }}
            className="p-1.5 rounded-lg border bg-surface-container-lowest border-outline-variant text-outline hover:text-on-surface hover:border-outline transition-colors flex items-center justify-center"
            title="Vim & Terminal Shortcuts (?)"
          >
            <span className="material-symbols-outlined text-base">keyboard</span>
          </button>
        )}

        <div className="w-7 h-7 rounded-lg border border-outline-variant bg-surface-container-high flex items-center justify-center font-mono text-xs font-bold text-primary">
          OP
        </div>
      </div>
    </header>
  );
};
