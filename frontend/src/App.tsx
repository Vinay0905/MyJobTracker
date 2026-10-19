import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  JobListItem,
  JobDetail,
  TopSkillItem,
  TelemetryResponse,
  SourceItem,
  SyncRunItem,
  CandidateProfile,
  GapAnalysisResponse,
  CompanyItem,
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
  fetchCompanies,
  fetchSyncStatus,
} from './api/client';
import { TopNavbar } from './components/layout/TopNavbar';
import { Sidebar, PAY_BAND_OPTIONS } from './components/layout/Sidebar';
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

  const [companies, setCompanies] = useState<CompanyItem[]>([]);
  const [selectedCompanies, setSelectedCompanies] = useState<string[]>([]);
  const [selectedSort, setSelectedSort] = useState<string>('newest_discovered');

  // Pagination State (Default 12 per page)
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(12);

  const [yoeMin, setYoeMin] = useState<string>('');
  const [yoeMax, setYoeMax] = useState<string>('');
  const [includeUnspecifiedYoe, setIncludeUnspecifiedYoe] = useState<boolean>(true);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedSearch, setDebouncedSearch] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [selectedRoleFocus, setSelectedRoleFocus] = useState<string[]>([]);
  const [selectedLocation, setSelectedLocation] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);
  const [selectedSeniority, setSelectedSeniority] = useState<string[]>([]);
  const [selectedPayBands, setSelectedPayBands] = useState<string[]>([]);

  // Every filter change returns to page 1 in the same update, so only one request goes out.
  const withPageReset = useCallback(
    <T,>(setter: React.Dispatch<React.SetStateAction<T>>) =>
      (value: React.SetStateAction<T>) => {
        setter(value);
        setCurrentPage(1);
      },
    []
  );
  const toggleIn = (list: string[], value: string) =>
    list.includes(value) ? list.filter((v) => v !== value) : [...list, value];

  const changeCategory = withPageReset(setSelectedCategory);
  const changeLocation = withPageReset(setSelectedLocation);
  const changeSkill = withPageReset(setSelectedSkill);
  const changeSort = withPageReset(setSelectedSort);
  const changeYoeMin = withPageReset(setYoeMin);
  const changeYoeMax = withPageReset(setYoeMax);
  const changeIncludeUnspecifiedYoe = withPageReset(setIncludeUnspecifiedYoe);
  const changeCompanies = withPageReset(setSelectedCompanies);
  const changeSeniority = withPageReset(setSelectedSeniority);
  const changePayBands = withPageReset(setSelectedPayBands);
  const changeRoleFocus = withPageReset(setSelectedRoleFocus);

  // Search waits for typing to pause; the request it triggers aborts any older one.
  useEffect(() => {
    const t = window.setTimeout(() => {
      setDebouncedSearch(searchQuery.trim());
      setCurrentPage(1);
    }, 250);
    return () => window.clearTimeout(t);
  }, [searchQuery]);

  const parseYoeField = (raw: string) => {
    const trimmed = raw.trim();
    if (trimmed === '') return { value: null as number | null, invalid: false };
    const parsed = parseInt(trimmed, 10);
    if (Number.isNaN(parsed)) return { value: null, invalid: true };
    return { value: Math.max(0, parsed), invalid: false };
  };
  const yoeMinParsed = parseYoeField(yoeMin);
  const yoeMaxParsed = parseYoeField(yoeMax);
  const effectiveYoeMin = yoeMinParsed.invalid ? null : yoeMinParsed.value;
  const effectiveYoeMax = yoeMaxParsed.invalid ? null : yoeMaxParsed.value;
  const hasYoeFilter =
    effectiveYoeMin !== null ||
    effectiveYoeMax !== null ||
    !includeUnspecifiedYoe ||
    yoeMinParsed.invalid ||
    yoeMaxParsed.invalid;

  const radarAbortRef = useRef<AbortController | null>(null);

  // Load all jobs and top skills
  const loadRadarData = useCallback(async () => {
    radarAbortRef.current?.abort();
    const controller = new AbortController();
    radarAbortRef.current = controller;
    setIsLoading(true);
    try {
      const [jobsData, skillsData, companiesData] = await Promise.all([
        fetchJobs({
          category: selectedCategory,
          companies: selectedCompanies,
          sort_by: selectedSort,
          location: selectedLocation,
          role_focus: selectedRoleFocus.length > 0 ? selectedRoleFocus : null,
          skill: selectedSkill,
          search: debouncedSearch,
          seniority: selectedSeniority,
          pay_bands: selectedPayBands,
          yoe_min: effectiveYoeMin,
          yoe_max: effectiveYoeMax,
          include_unspecified_yoe: includeUnspecifiedYoe,
          include_demo: includeDemo,
          page: currentPage,
          pageSize: pageSize,
        }, controller.signal),
        fetchTopSkills(selectedCategory, includeDemo, controller.signal),
        fetchCompanies(includeDemo, controller.signal),
      ]);
      if (controller.signal.aborted) return;

      // A filter change can leave the current page past the end; snap back to the last page.
      if (currentPage > jobsData.total_pages) {
        setCurrentPage(jobsData.total_pages);
        return;
      }
      setJobs(jobsData.jobs);
      setTotalJobsCount(jobsData.total_count);
      setSectorCounts(jobsData.sector_counts || {});
      setTopSkills(skillsData.top_skills);
      setCompanies(companiesData);
    } catch (e) {
      if ((e as Error)?.name === 'AbortError') return;
      console.warn('Backend loading warning:', e);
    } finally {
      if (radarAbortRef.current === controller) {
        setIsLoading(false);
      }
    }
  }, [selectedCategory, selectedCompanies, selectedSort, selectedLocation, selectedRoleFocus, selectedSkill, debouncedSearch, selectedSeniority, selectedPayBands, effectiveYoeMin, effectiveYoeMax, includeUnspecifiedYoe, includeDemo, currentPage, pageSize]);

  useEffect(() => () => radarAbortRef.current?.abort(), []);

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

  // Latest loaders/tab for the sync poller, which outlives the render that started it
  const reloadRef = useRef<() => Promise<void>>(async () => {});
  useEffect(() => {
    reloadRef.current = async () => {
      if (currentTab === 'radar') await loadRadarData();
      else if (currentTab === 'sources') await loadSourcesData();
      else if (currentTab === 'telemetry') await loadTelemetryData();
    };
  }, [currentTab, loadRadarData, loadSourcesData, loadTelemetryData]);

  const syncPollRef = useRef<number | null>(null);
  const syncPollInFlightRef = useRef(false);
  const stopSyncPolling = useCallback(() => {
    if (syncPollRef.current !== null) {
      window.clearInterval(syncPollRef.current);
      syncPollRef.current = null;
    }
    syncPollInFlightRef.current = false;
  }, []);
  useEffect(() => stopSyncPolling, [stopSyncPolling]);

  // Trigger sync across all career portals with honest status polling
  const handleSync = async () => {
    if (syncPollRef.current !== null) return;
    setIsSyncing(true);
    setLastSyncedMessage('Initiating sync...');
    try {
      await triggerSync();
      syncPollInFlightRef.current = false;
      syncPollRef.current = window.setInterval(async () => {
        if (syncPollInFlightRef.current) return;
        syncPollInFlightRef.current = true;
        try {
          const status = await fetchSyncStatus();
          if (status.is_active || status.status === 'queued' || status.status === 'running') {
            const currentSource = status.current_source ? ` (${status.current_source})` : '';
            const progress = status.total_sources > 0 ? ` [${status.completed_sources}/${status.total_sources}]` : '';
            setLastSyncedMessage(`Ingesting${currentSource}${progress}...`);
          } else {
            stopSyncPolling();
            setIsSyncing(false);
            if (status.status === 'completed') {
              setLastSyncedMessage('Sync Complete');
              playSyncChime();
            } else if (status.status === 'partial') {
              setLastSyncedMessage('Sync Completed (warnings)');
              playSyncChime();
            } else if (status.status === 'failed') {
              setLastSyncedMessage(`Sync Failed: ${status.last_error || 'Network error'}`);
            } else {
              setLastSyncedMessage('Idle');
            }
            await reloadRef.current();
          }
        } catch (pollErr) {
          console.warn('Sync status poll error:', pollErr);
        } finally {
          syncPollInFlightRef.current = false;
        }
      }, 1000);
    } catch (err) {
      console.error('Sync failed:', err);
      stopSyncPolling();
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

  const handleToggleRoleFocus = (role: string) => changeRoleFocus((prev) => toggleIn(prev, role));

  const companyName = (id: string) => companies.find((c) => c.company_id === id)?.name || id;

  const clearAllFilters = () => {
    setSelectedCategory(null);
    setSelectedCompanies([]);
    setSelectedLocation(null);
    setSelectedRoleFocus([]);
    setSelectedSkill(null);
    setSelectedSeniority([]);
    setSelectedPayBands([]);
    setSearchQuery('');
    setYoeMin('');
    setYoeMax('');
    setIncludeUnspecifiedYoe(true);
    setCurrentPage(1);
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

  const totalPages = Math.max(1, Math.ceil(totalJobsCount / pageSize));

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
        onToggleDemo={() => {
          setIncludeDemo((prev) => !prev);
          setCurrentPage(1);
        }}
        onToggleShortcuts={() => setIsShortcutsOpen((prev) => !prev)}
      />

      {/* Visual Demo Mode Banner */}
      {includeDemo && (
        <div className="bg-amber-500/15 border-b border-amber-500/30 px-space-lg py-2 flex items-center justify-between font-mono text-xs text-amber-300 z-30">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-sm">warning</span>
            <span>
              <strong>DEMO MODE ACTIVE:</strong> Synthetic fixtures (is_demo=True) are mixed in and labeled DEMO. They are not live listings from any employer.
            </span>
          </div>
          <button
            onClick={() => {
              setIncludeDemo(false);
              setCurrentPage(1);
            }}
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
          onSelectCategory={changeCategory}
          selectedRoleFocus={selectedRoleFocus}
          onToggleRoleFocus={handleToggleRoleFocus}
          selectedLocation={selectedLocation}
          onSelectLocation={changeLocation}
          totalRolesCount={totalJobsCount}
          sectorCounts={sectorCounts}
          companies={companies}
          selectedCompanies={selectedCompanies}
          onToggleCompany={(id) => changeCompanies((prev) => toggleIn(prev, id))}
          onClearCompanies={() => changeCompanies([])}
          selectedSeniority={selectedSeniority}
          onToggleSeniority={(lv) => changeSeniority((prev) => toggleIn(prev, lv))}
          selectedPayBands={selectedPayBands}
          onTogglePayBand={(b) => changePayBands((prev) => toggleIn(prev, b))}
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

              {/* Quick Eligibility Controls & Sort Options */}
              <div className="flex flex-wrap items-center justify-between gap-3 px-1">
                {/* Required years range (same years number as the card) */}
                <div className={`flex flex-wrap items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono ${
                  yoeMinParsed.invalid || yoeMaxParsed.invalid
                    ? 'bg-error-container/30 border-error text-on-error-container'
                    : hasYoeFilter
                    ? 'bg-secondary/10 border-secondary/60 text-secondary'
                    : 'bg-surface-container-low border-outline-variant text-on-surface-variant'
                }`}>
                  <span className="material-symbols-outlined text-sm">work_history</span>
                  <label htmlFor="yoe-min" className="text-[11px] uppercase tracking-wider font-semibold">Required YOE</label>
                  <input
                    id="yoe-min"
                    type="number"
                    min={0}
                    max={30}
                    placeholder="min"
                    value={yoeMin}
                    onChange={(e) => changeYoeMin(e.target.value)}
                    aria-invalid={yoeMinParsed.invalid}
                    className={`w-14 bg-surface-container-lowest border rounded px-1.5 py-0.5 text-on-surface ${
                      yoeMinParsed.invalid ? 'border-error' : 'border-outline-variant'
                    }`}
                  />
                  <span>–</span>
                  <input
                    id="yoe-max"
                    aria-label="Maximum required years"
                    type="number"
                    min={0}
                    max={30}
                    placeholder="max"
                    value={yoeMax}
                    onChange={(e) => changeYoeMax(e.target.value)}
                    aria-invalid={yoeMaxParsed.invalid}
                    className={`w-14 bg-surface-container-lowest border rounded px-1.5 py-0.5 text-on-surface ${
                      yoeMaxParsed.invalid ? 'border-error' : 'border-outline-variant'
                    }`}
                  />
                  {(yoeMinParsed.invalid || yoeMaxParsed.invalid) && (
                    <span className="text-[10px] text-error">Enter whole years (0–30)</span>
                  )}
                  <label className="flex items-center gap-1 cursor-pointer text-[11px] text-on-surface-variant">
                    <input
                      type="checkbox"
                      checked={includeUnspecifiedYoe}
                      onChange={(e) => changeIncludeUnspecifiedYoe(e.target.checked)}
                      className="w-3.5 h-3.5 rounded bg-surface-container-lowest border-outline-variant text-primary focus:ring-0"
                    />
                    <span>Keep "YOE unspecified"</span>
                  </label>
                </div>

                {/* Sort By Select */}
                <div className="flex items-center gap-2 font-mono text-xs">
                  <label htmlFor="job-sort-select" className="text-outline text-[11px] uppercase tracking-wider font-semibold">Sort By:</label>
                  <select
                    id="job-sort-select"
                    value={selectedSort}
                    onChange={(e) => {
                      playKeyClick();
                      changeSort(e.target.value);
                    }}
                    className="bg-surface-container-low border border-outline-variant rounded-lg px-2.5 py-1.5 text-xs text-on-surface focus:outline-none focus:border-primary cursor-pointer font-mono"
                  >
                    <option value="newest_discovered">Newest Discovered</option>
                    <option value="recently_posted">Recently Posted</option>
                    <option value="company_asc">Company (A → Z)</option>
                    <option value="company_desc">Company (Z → A)</option>
                    <option value="title_asc">Job Title (A → Z)</option>
                    <option value="title_desc">Job Title (Z → A)</option>
                    <option value="location_asc">Location (A → Z)</option>
                    <option value="recently_updated">Recently Updated</option>
                  </select>
                </div>
              </div>

              {/* Active Filter Chips */}
              {(selectedCategory || selectedCompanies.length > 0 || selectedLocation || selectedRoleFocus.length > 0 || selectedSkill || searchQuery || hasYoeFilter || selectedSeniority.length > 0 || selectedPayBands.length > 0) && (
                <div className="flex flex-wrap items-center gap-2 p-2 rounded-lg bg-surface-container border border-outline-variant font-mono text-xs">
                  <span className="text-outline">Active Filters:</span>
                  {hasYoeFilter && (
                    <span className="px-2 py-0.5 rounded bg-secondary/20 text-secondary flex items-center gap-1">
                      <span>
                        Exp: {effectiveYoeMin ?? 0}–{effectiveYoeMax ?? '∞'} YOE
                        {includeUnspecifiedYoe ? ' + unspecified' : ' (stated only)'}
                      </span>
                      <button
                        onClick={() => {
                          changeYoeMin('');
                          setYoeMax('');
                          setIncludeUnspecifiedYoe(true);
                        }}
                        className="hover:text-white ml-0.5 font-bold"
                      >×</button>
                    </span>
                  )}
                  {selectedCompanies.map((id) => (
                    <span key={id} className="px-2 py-0.5 rounded bg-primary/20 text-primary flex items-center gap-1">
                      <span>Company: {companyName(id)}</span>
                      <button onClick={() => changeCompanies((prev) => prev.filter((c) => c !== id))} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  ))}
                  {selectedSeniority.map((lv) => (
                    <span key={lv} className="px-2 py-0.5 rounded bg-primary/20 text-primary flex items-center gap-1 capitalize">
                      <span>Level: {lv}</span>
                      <button onClick={() => changeSeniority((prev) => prev.filter((v) => v !== lv))} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  ))}
                  {selectedPayBands.map((band) => (
                    <span key={band} className="px-2 py-0.5 rounded bg-secondary/20 text-secondary flex items-center gap-1">
                      <span>Pay: {PAY_BAND_OPTIONS.find((o) => o.value === band)?.label || band}</span>
                      <button onClick={() => changePayBands((prev) => prev.filter((v) => v !== band))} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  ))}
                  {selectedCategory && (
                    <span className="px-2 py-0.5 rounded bg-surface-container-high text-primary flex items-center gap-1">
                      <span>Sector: {selectedCategory}</span>
                      <button onClick={() => changeCategory(null)} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  )}
                  {selectedLocation && (
                    <span className="px-2 py-0.5 rounded bg-surface-container-high text-primary flex items-center gap-1">
                      <span>Location: {selectedLocation}</span>
                      <button onClick={() => changeLocation(null)} className="hover:text-white ml-0.5 font-bold">×</button>
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
                      <button onClick={() => changeSkill(null)} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  )}
                  {searchQuery && (
                    <span className="px-2 py-0.5 rounded bg-surface-container-high text-on-surface flex items-center gap-1">
                      <span>"{searchQuery}"</span>
                      <button onClick={() => setSearchQuery('')} className="hover:text-white ml-0.5 font-bold">×</button>
                    </span>
                  )}
                  <button
                    onClick={clearAllFilters}
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
                <section className="flex flex-col gap-space-md pb-space-xl">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-space-md">
                    {jobs.map((job, idx) => (
                      <JobCard
                        key={job.job_id}
                        job={job}
                        isSelected={selectedJobIndex === idx}
                        onInspect={(id) => {
                          setSelectedJobIndex(idx);
                          handleInspectJob(id);
                        }}
                        onSelectSkill={(s) => changeSkill(s)}
                      />
                    ))}
                  </div>

                  {/* Cyberpunk Pagination Bar */}
                  {totalJobsCount > 0 && (
                    <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-xl bg-surface-container-low border border-outline-variant font-mono text-xs mt-2">
                      <div className="flex items-center gap-3">
                        <span className="text-on-surface-variant">
                          Showing{' '}
                          <strong className="text-on-surface font-semibold">
                            {(currentPage - 1) * pageSize + 1}
                          </strong>{' '}
                          –{' '}
                          <strong className="text-on-surface font-semibold">
                            {Math.min(currentPage * pageSize, totalJobsCount)}
                          </strong>{' '}
                          of{' '}
                          <strong className="text-primary font-bold">{totalJobsCount}</strong> roles
                        </span>

                        <div className="hidden sm:flex items-center gap-1.5 border-l border-outline-variant/60 pl-3">
                          <span className="text-outline text-[11px]">Per page:</span>
                          {[12, 24, 48].map((size) => (
                            <button
                              key={size}
                              onClick={() => {
                                playKeyClick();
                                setPageSize(size);
                                setCurrentPage(1);
                              }}
                              className={`px-2 py-0.5 rounded text-[11px] transition-colors ${
                                pageSize === size
                                  ? 'bg-primary/20 text-primary font-bold border border-primary/40'
                                  : 'text-outline hover:text-on-surface bg-surface-container-highest/40'
                              }`}
                            >
                              {size}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => {
                            playKeyClick();
                            setCurrentPage(1);
                          }}
                          disabled={currentPage === 1}
                          className="px-2.5 py-1 rounded bg-surface-container border border-outline-variant/60 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high transition-colors"
                          title="First Page"
                        >
                          «
                        </button>
                        <button
                          onClick={() => {
                            playKeyClick();
                            setCurrentPage((p) => Math.max(1, p - 1));
                          }}
                          disabled={currentPage === 1}
                          className="px-3 py-1 rounded bg-surface-container border border-outline-variant/60 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high transition-colors flex items-center gap-1"
                        >
                          ‹ Prev
                        </button>

                        {/* Page Numbers */}
                        <div className="flex items-center gap-1 px-1">
                          {Array.from({ length: totalPages }, (_, i) => i + 1)
                            .filter(
                              (p) =>
                                p === 1 ||
                                p === totalPages ||
                                Math.abs(p - currentPage) <= 2
                            )
                            .reduce<(number | string)[]>((acc, p, idx, arr) => {
                              if (idx > 0 && p - (arr[idx - 1] as number) > 1) {
                                acc.push('...');
                              }
                              acc.push(p);
                              return acc;
                            }, [])
                            .map((item, idx) =>
                              item === '...' ? (
                                <span key={`ellipsis-${idx}`} className="px-1 text-outline">
                                  …
                                </span>
                              ) : (
                                <button
                                  key={`page-${item}`}
                                  onClick={() => {
                                    playKeyClick();
                                    setCurrentPage(item as number);
                                  }}
                                  className={`w-7 h-7 rounded flex items-center justify-center text-xs transition-colors ${
                                    currentPage === item
                                      ? 'bg-primary text-on-primary font-bold shadow-sm'
                                      : 'bg-surface-container text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high border border-outline-variant/40'
                                  }`}
                                >
                                  {item}
                                </button>
                              )
                            )}
                        </div>

                        <button
                          onClick={() => {
                            playKeyClick();
                            setCurrentPage((p) => Math.min(totalPages, p + 1));
                          }}
                          disabled={currentPage === totalPages}
                          className="px-3 py-1 rounded bg-surface-container border border-outline-variant/60 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high transition-colors flex items-center gap-1"
                        >
                          Next ›
                        </button>
                        <button
                          onClick={() => {
                            playKeyClick();
                            setCurrentPage(totalPages);
                          }}
                          disabled={currentPage === totalPages}
                          className="px-2.5 py-1 rounded bg-surface-container border border-outline-variant/60 disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high transition-colors"
                          title="Last Page"
                        >
                          »
                        </button>
                      </div>
                    </div>
                  )}
                </section>
              )}
            </>
          )}

          {currentTab === 'constellation' && (
            <SkillConstellationView
              onSelectSkillFilter={(s) => {
                changeSkill(s);
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
