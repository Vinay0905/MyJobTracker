import React, { useState, useEffect, useCallback } from 'react';
import {
  JobListItem,
  JobDetail,
  TopSkillItem,
  TelemetryResponse,
  SourceItem,
  SyncRunItem,
  CandidateProfile,
  GapAnalysisResponse,
  ViewTab,
} from './types/api';
import {
  fetchJobs,
  fetchJobDetail,
  fetchTopSkills,
  fetchTelemetry,
  fetchSources,
  fetchSyncRuns,
  triggerSync,
  fetchCandidateProfile,
  fetchGapAnalysis,
} from './api/client';
import { TopNavbar } from './components/layout/TopNavbar';
import { Sidebar } from './components/layout/Sidebar';
import { JobCard } from './components/jobs/JobCard';
import { JobDetailDrawer } from './components/jobs/JobDetailDrawer';
import { SkillTelemetryView } from './components/telemetry/SkillTelemetryView';
import { GapAnalyzerView } from './components/candidate/GapAnalyzerView';
import { SourceHealthView } from './components/sources/SourceHealthView';
import { SkillConstellationView } from './components/constellation/SkillConstellationView';
import { SalaryCalculatorView } from './components/salary/SalaryCalculatorView';
import { KeyboardShortcutsModal } from './components/common/KeyboardShortcutsModal';
import { playKeyClick, playInspectChirp, playSyncChime, toggleSound } from './utils/audio';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState<ViewTab>('radar');
  
  // Data State
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [totalJobsCount, setTotalJobsCount] = useState<number>(0);
  const [topSkills, setTopSkills] = useState<TopSkillItem[]>([]);
  const [telemetry, setTelemetry] = useState<TelemetryResponse | null>(null);
  const [sources, setSources] = useState<SourceItem[]>([]);
  const [syncRuns, setSyncRuns] = useState<SyncRunItem[]>([]);
  const [candidateProfile, setCandidateProfile] = useState<CandidateProfile | null>(null);
  const [gapData, setGapData] = useState<GapAnalysisResponse | null>(null);
  const [sectorCounts, setSectorCounts] = useState<Record<string, number>>({});

  // Drawer & Inspection State
  const [inspectingJob, setInspectingJob] = useState<JobDetail | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [selectedJobIndex, setSelectedJobIndex] = useState<number>(-1);
  const [isShortcutsOpen, setIsShortcutsOpen] = useState<boolean>(false);

  // Status & Filter State
  const [includeDemo, setIncludeDemo] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [lastSyncedMessage, setLastSyncedMessage] = useState<string>('Live Ingestion');

  const [filter0to6Yoe, setFilter0to6Yoe] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedRoleFocus, setSelectedRoleFocus] = useState<string[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);

  // Load all jobs and top skills
  const loadRadarData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [jobsData, skillsData] = await Promise.all([
        fetchJobs({
          category: selectedCategory,
          location: selectedLocation,
          role_focus: selectedRoleFocus.length > 0 ? selectedRoleFocus : null,
          skill: selectedSkill,
          search: searchQuery,
          include_demo: includeDemo,
          max_required_yoe: filter0to6Yoe ? 6 : null,
        }),
        fetchTopSkills(selectedCategory, includeDemo),
      ]);

      setJobs(jobsData.jobs);
      setTotalJobsCount(jobsData.total_count);
      if (jobsData.sector_counts) {
        setSectorCounts(jobsData.sector_counts);
      }
      setTopSkills(skillsData.top_skills);
    } catch (e) {
      console.warn('Backend loading warning:', e);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, selectedLocation, selectedRoleFocus, selectedSkill, searchQuery, includeDemo, filter0to6Yoe]);

  // Load telemetry
  const loadTelemetryData = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await fetchTelemetry(selectedCategory, includeDemo);
      setTelemetry(data);
    } catch (e) {
      console.warn('Telemetry loading warning:', e);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, includeDemo]);

  // Load gap analysis & candidate profile
  const loadGapData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [profileData, gapRes] = await Promise.all([
        fetchCandidateProfile(),
        fetchGapAnalysis(selectedCategory, includeDemo),
      ]);
      setCandidateProfile(profileData);
      setGapData(gapRes);
    } catch (e) {
      console.warn('Gap analysis loading warning:', e);
    } finally {
      setIsLoading(false);
    }
  }, [selectedCategory, includeDemo]);

  // Load sources & sync runs
  const loadSourcesData = useCallback(async () => {
    setIsLoading(true);
    try {
      const [srcData, runsData] = await Promise.all([
        fetchSources(),
        fetchSyncRuns(),
      ]);
      setSources(srcData);
      setSyncRuns(runsData);
    } catch (e) {
      console.warn('Sources loading warning:', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Fetch when tab or filters change
  useEffect(() => {
    if (currentTab === 'radar') loadRadarData();
    else if (currentTab === 'telemetry') loadTelemetryData();
    else if (currentTab === 'gap-analyzer') loadGapData();
    else if (currentTab === 'sources') loadSourcesData();
  }, [currentTab, loadRadarData, loadTelemetryData, loadGapData, loadSourcesData]);

  // Trigger sync across all career portals
  const handleSync = async () => {
    setIsSyncing(true);
    setLastSyncedMessage('Ingesting...');
    try {
      await triggerSync();
      // Actively poll every 1.5s until jobs populate
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts += 1;
        if (currentTab === 'radar') await loadRadarData();
        else if (currentTab === 'sources') await loadSourcesData();
        else if (currentTab === 'telemetry') await loadTelemetryData();

        if (attempts >= 6) {
          clearInterval(interval);
          setIsSyncing(false);
          setLastSyncedMessage('Just now');
          playSyncChime();
        }
      }, 1500);
    } catch (err) {
      console.error('Sync failed:', err);
      setLastSyncedMessage('Sync Failed');
      setIsSyncing(false);
    }
  };

  const handleInspectJob = async (jobId: string) => {
    playInspectChirp();
    try {
      const detail = await fetchJobDetail(jobId);
      setInspectingJob(detail);
      setIsDrawerOpen(true);
    } catch (e) {
      console.error('Failed to load job detail:', e);
    }
  };

  const handleToggleRoleFocus = (role: string) => {
    setSelectedRoleFocus((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
    );
  };

  // Cyberpunk Terminal & Vim Keyboard Navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        if (e.key === 'Escape') target.blur();
        return;
      }

      // 1-6 quick tab navigation
      if (['1', '2', '3', '4', '5', '6'].includes(e.key)) {
        playKeyClick();
        const tabMap: Record<string, ViewTab> = {
          '1': 'radar',
          '2': 'constellation',
          '3': 'salary',
          '4': 'telemetry',
          '5': 'gap-analyzer',
          '6': 'sources',
        };
        if (tabMap[e.key]) setCurrentTab(tabMap[e.key]);
        return;
      }

      // Vim keys for radar job feed
      if (currentTab === 'radar' && jobs.length > 0) {
        if (e.key === 'j' || e.key === 'ArrowDown') {
          e.preventDefault();
          playKeyClick();
          setSelectedJobIndex((prev) => (prev + 1 < jobs.length ? prev + 1 : 0));
          return;
        }
        if (e.key === 'k' || e.key === 'ArrowUp') {
          e.preventDefault();
          playKeyClick();
          setSelectedJobIndex((prev) => (prev - 1 >= 0 ? prev - 1 : jobs.length - 1));
          return;
        }
        if (e.key === 'Enter' || e.key === ' ' || e.key === 'o') {
          if (selectedJobIndex >= 0 && selectedJobIndex < jobs.length) {
            e.preventDefault();
            handleInspectJob(jobs[selectedJobIndex].job_id);
            return;
          }
        }
      }

      // Escape to close drawers/modals
      if (e.key === 'Escape') {
        if (isDrawerOpen) {
          setIsDrawerOpen(false);
          return;
        }
        if (isShortcutsOpen) {
          setIsShortcutsOpen(false);
          return;
        }
      }

      // Shortcuts modal toggle
      if (e.key === '?') {
        e.preventDefault();
        playKeyClick();
        setIsShortcutsOpen((prev) => !prev);
        return;
      }

      // Toggle terminal audio
      if (e.key === 'm' || e.key === 'M') {
        toggleSound();
        return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentTab, jobs, selectedJobIndex, isDrawerOpen, isShortcutsOpen]);

  return (
    <div className="min-h-screen flex flex-col bg-surface text-on-surface">
      {/* Top Navigation */}
      <TopNavbar
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        onSync={handleSync}
        isSyncing={isSyncing}
        lastSyncedMessage={lastSyncedMessage}
        includeDemo={includeDemo}
        onToggleDemo={() => setIncludeDemo((prev) => !prev)}
        onToggleShortcuts={() => setIsShortcutsOpen((prev) => !prev)}
      />

      {/* Visual Demo Mode Banner */}
      {includeDemo && (
        <div className="bg-amber-500/15 border-b border-amber-500/30 px-space-lg py-2 flex items-center justify-between font-mono text-xs text-amber-300 z-30">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-sm">warning</span>
            <span>
              <strong>DEMO MODE ACTIVE:</strong> Including synthetic baseline fixtures (is_demo=True) for Qualcomm, G42, Careem, NVIDIA, Epic, and Rockstar.
            </span>
          </div>
          <button
            onClick={() => setIncludeDemo(false)}
            className="underline hover:text-white text-[11px] font-semibold"
          >
            Dismiss / Switch to Live Only
          </button>
        </div>
      )}

      {/* Main Container */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Filter Sidebar */}
        <Sidebar
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
          selectedRoleFocus={selectedRoleFocus}
          onToggleRoleFocus={handleToggleRoleFocus}
          selectedLocation={selectedLocation}
          onSelectLocation={setSelectedLocation}
          totalRolesCount={totalJobsCount}
          sectorCounts={sectorCounts}
        />

        {/* Dynamic View Canvas */}
        <main className="flex-1 overflow-y-auto p-space-lg lg:p-6 flex flex-col gap-space-lg bg-surface">
          {currentTab === 'radar' && (
            <>
              {/* Radar Feed Analytics Strip */}
              <section className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
                <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between">
                  <span className="font-mono text-[10px] text-outline uppercase tracking-wider font-semibold">
                    Live Engineering Openings
                  </span>
                  <span className="text-3xl font-bold text-on-surface my-1">
                    {totalJobsCount}
                  </span>
                  <span className="font-mono text-[10px] text-secondary">
                    Active Verified Roles
                  </span>
                </div>

                <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between">
                  <span className="font-mono text-[10px] text-outline uppercase tracking-wider font-semibold">
                    Top In-Demand Skill
                  </span>
                  <span className="text-xl font-bold text-on-surface my-1 truncate">
                    {topSkills[0]?.skill || 'C++ & Python'}
                  </span>
                  <span className="font-mono text-[10px] text-primary">
                    Most Frequently Required
                  </span>
                </div>

                <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between">
                  <span className="font-mono text-[10px] text-outline uppercase tracking-wider font-semibold">
                    Reconciliation Guard
                  </span>
                  <span className="text-3xl font-bold text-secondary my-1">Active</span>
                  <span className="font-mono text-[10px] text-outline">
                    Safe Closure State Machine
                  </span>
                </div>
              </section>

              {/* Quick Eligibility Controls & Filter Header */}
              <div className="flex flex-wrap items-center justify-between gap-2 px-1">
                <button
                  onClick={() => setFilter0to6Yoe((prev) => !prev)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono transition-all ${
                    filter0to6Yoe
                      ? 'bg-secondary/20 border-secondary text-secondary font-semibold shadow-sm shadow-secondary/10'
                      : 'bg-surface-container-low border-outline-variant text-on-surface-variant hover:text-on-surface hover:border-outline'
                  }`}
                >
                  <span className="material-symbols-outlined text-sm">
                    {filter0to6Yoe ? 'check_circle' : 'radio_button_unchecked'}
                  </span>
                  <span>0–6 YOE Eligible (Exclude 7+ YOE Staff/Principal)</span>
                </button>
                <span className="text-[11px] font-mono text-outline">
                  {filter0to6Yoe ? 'Filtering: ≤6 YOE or unspecified' : 'Showing all seniority levels'}
                </span>
              </div>

              {/* Active Filter Chips */}
              {(selectedCategory || selectedLocation || selectedRoleFocus.length > 0 || selectedSkill || searchQuery || filter0to6Yoe) && (
                <div className="flex flex-wrap items-center gap-2 p-2 rounded-lg bg-surface-container border border-outline-variant font-mono text-xs">
                  <span className="text-outline">Active Filters:</span>
                  {filter0to6Yoe && (
                    <span className="px-2 py-0.5 rounded bg-secondary/20 text-secondary flex items-center gap-1">
                      <span>Exp: ≤6 YOE</span>
                      <button onClick={() => setFilter0to6Yoe(false)} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  )}
                  {selectedCategory && (
                    <span className="px-2 py-0.5 rounded bg-surface-container-high text-primary flex items-center gap-1">
                      <span>Sector: {selectedCategory}</span>
                      <button onClick={() => setSelectedCategory(null)} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  )}
                  {selectedLocation && (
                    <span className="px-2 py-0.5 rounded bg-surface-container-high text-primary flex items-center gap-1">
                      <span>Location: {selectedLocation}</span>
                      <button onClick={() => setSelectedLocation(null)} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  )}
                  {selectedRoleFocus.map((role) => (
                    <span key={role} className="px-2 py-0.5 rounded bg-primary/20 text-primary flex items-center gap-1">
                      <span>{role}</span>
                      <button onClick={() => handleToggleRoleFocus(role)} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  ))}
                  {selectedSkill && (
                    <span className="px-2 py-0.5 rounded bg-secondary/20 text-secondary flex items-center gap-1">
                      <span>Skill: {selectedSkill}</span>
                      <button onClick={() => setSelectedSkill(null)} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  )}
                  {searchQuery && (
                    <span className="px-2 py-0.5 rounded bg-surface-container-high text-on-surface flex items-center gap-1">
                      <span>"{searchQuery}"</span>
                      <button onClick={() => setSearchQuery('')} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  )}
                  <button
                    onClick={() => {
                      setSelectedCategory(null);
                      setSelectedLocation(null);
                      setSelectedRoleFocus([]);
                      setSelectedSkill(null);
                      setSearchQuery('');
                      setFilter0to6Yoe(false);
                    }}
                    className="ml-auto text-[11px] text-outline hover:text-primary transition-colors underline"
                  >
                    Clear All
                  </button>
                </div>
              )}

              {/* Job Grid Feed */}
              {isLoading ? (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-space-md">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant animate-pulse h-48"
                    />
                  ))}
                </div>
              ) : jobs.length === 0 ? (
                <div className="p-12 text-center rounded-xl bg-surface-container-low border border-outline-variant flex flex-col items-center justify-center gap-2">
                  <span className="material-symbols-outlined text-4xl text-outline">search_off</span>
                  <h4 className="text-base font-bold text-on-surface">No Engineering Roles Found</h4>
                  <p className="text-xs text-on-surface-variant max-w-sm">
                    No active positions match your current sector or search filters. Trigger a fresh crawl to sync career pages.
                  </p>
                  <button
                    onClick={handleSync}
                    className="mt-2 px-3 py-1.5 rounded-lg bg-primary-container text-on-primary-container font-mono text-xs font-semibold"
                  >
                    Sync Career Pages Now
                  </button>
                </div>
              ) : (
                <section className="grid grid-cols-1 lg:grid-cols-2 gap-space-md pb-space-xl">
                  {jobs.map((job, idx) => (
                    <JobCard
                      key={job.job_id}
                      job={job}
                      isSelected={selectedJobIndex === idx}
                      onInspect={(id) => {
                        setSelectedJobIndex(idx);
                        handleInspectJob(id);
                      }}
                      onSelectSkill={(s) => setSelectedSkill(s)}
                    />
                  ))}
                </section>
              )}
            </>
          )}

          {currentTab === 'constellation' && (
            <SkillConstellationView
              onSelectSkillFilter={(s) => {
                setSelectedSkill(s);
                setCurrentTab('radar');
              }}
            />
          )}

          {currentTab === 'salary' && (
            <SalaryCalculatorView />
          )}

          {currentTab === 'telemetry' && (
            <SkillTelemetryView
              telemetry={telemetry}
              isLoading={isLoading}
              onRefresh={loadTelemetryData}
            />
          )}

          {currentTab === 'gap-analyzer' && (
            <GapAnalyzerView
              gapData={gapData}
              profile={candidateProfile}
              isLoading={isLoading}
              onRefresh={loadGapData}
            />
          )}

          {currentTab === 'sources' && (
            <SourceHealthView
              sources={sources}
              syncRuns={syncRuns}
              isLoading={isLoading}
              onTriggerSync={handleSync}
              isSyncing={isSyncing}
            />
          )}
        </main>
      </div>

      {/* Slide-Over Job Detail Drawer */}
      <JobDetailDrawer
        job={inspectingJob}
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
      />

      {/* Vim & Keyboard Shortcuts Cheat Sheet Modal */}
      <KeyboardShortcutsModal
        isOpen={isShortcutsOpen}
        onClose={() => setIsShortcutsOpen(false)}
      />
    </div>
  );
};

export default App;
