import React from 'react';
import { SourceItem, SyncRunItem } from '../../types/api';

interface SourceHealthViewProps {
  sources: SourceItem[];
  syncRuns: SyncRunItem[];
  isLoading: boolean;
  onTriggerSync: () => void;
  isSyncing: boolean;
}

export const SourceHealthView: React.FC<SourceHealthViewProps> = ({
  sources,
  syncRuns,
  isLoading,
  onTriggerSync,
  isSyncing,
}) => {
  if (isLoading) {
    return (
      <div className="p-space-xl flex flex-col items-center justify-center gap-3">
        <span className="material-symbols-outlined text-3xl animate-spin text-primary">sync</span>
        <span className="font-mono text-xs text-outline">Loading source telemetry and sync logs...</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-space-lg">
      {/* Header Action */}
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-base font-bold text-on-surface">Registered ATS Connectors</h3>
          <p className="font-mono text-xs text-on-surface-variant">
            Direct public API endpoints for Tier-1 Game Studios, Silicon, and UAE Tech Hubs
          </p>
        </div>
        <button
          onClick={onTriggerSync}
          disabled={isSyncing}
          className="flex items-center gap-1.5 bg-primary-container text-on-primary-container px-3 py-1.5 rounded-lg font-mono text-xs font-semibold hover:bg-primary transition-colors disabled:opacity-50"
        >
          <span className={`material-symbols-outlined text-sm ${isSyncing ? 'animate-spin' : ''}`}>
            sync
          </span>
          <span>{isSyncing ? 'Ingesting...' : 'Trigger Full Sync'}</span>
        </button>
      </div>

      {/* Sources Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
        {sources.map((src) => {
          const isHealthy = src.health_status === 'HEALTHY';
          return (
            <div
              key={src.source_id}
              className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between"
            >
              <div>
                <div className="flex justify-between items-start">
                  <span className="font-mono text-xs text-outline uppercase font-semibold">
                    {src.provider_type}
                  </span>
                  <span
                    className={`font-mono text-[10px] px-1.5 py-0.5 rounded font-bold ${
                      isHealthy
                        ? 'bg-secondary/15 text-secondary border border-secondary/30'
                        : 'bg-error-container/20 text-error border border-error/30'
                    }`}
                  >
                    {src.health_status}
                  </span>
                </div>
                <h4 className="text-base font-bold text-on-surface mt-1">{src.company_name}</h4>
                <p className="font-mono text-[11px] text-on-surface-variant truncate mt-0.5">
                  {src.base_url}
                </p>
                {src.last_error && (
                  <p className="font-mono text-[10px] text-error bg-error-container/10 border border-error/20 p-1.5 rounded mt-2">
                    {src.last_error}
                  </p>
                )}
              </div>

              <div className="pt-3 mt-3 border-t border-outline-variant/60 font-mono text-[10px] text-outline flex justify-between items-center">
                <span>
                  Last Success:{' '}
                  {src.last_successful_sync
                    ? new Date(src.last_successful_sync).toLocaleTimeString()
                    : 'Pending'}
                </span>
                <span className="text-secondary font-medium">Auto-poll: 60m</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Sync Runs Audit Table */}
      <div className="rounded-xl bg-surface-container-low border border-outline-variant overflow-hidden">
        <div className="p-space-md border-b border-outline-variant flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-base">receipt_long</span>
            <span className="text-sm font-bold text-on-surface">Ingestion & Reconciliation Audit Log</span>
          </div>
          <span className="font-mono text-xs text-outline">{syncRuns.length} Runs Recorded</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-surface-container-lowest text-outline border-b border-outline-variant">
              <tr>
                <th className="p-3">Source ID</th>
                <th className="p-3">Status</th>
                <th className="p-3">Pagination</th>
                <th className="p-3">Jobs Discovered</th>
                <th className="p-3">Created / Updated</th>
                <th className="p-3">Safe Guard</th>
                <th className="p-3 text-right">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/40">
              {syncRuns.map((run) => (
                <tr key={run.run_id} className="hover:bg-surface-container transition-colors">
                  <td className="p-3 font-semibold text-on-surface">{run.source_id}</td>
                  <td className="p-3">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                        run.run_status === 'COMPLETE'
                          ? 'bg-secondary/15 text-secondary'
                          : 'bg-error-container/20 text-error'
                      }`}
                    >
                      {run.run_status}
                    </span>
                  </td>
                  <td className="p-3 text-on-surface-variant">
                    {run.pagination_complete ? 'Complete' : 'Partial'}
                  </td>
                  <td className="p-3 text-on-surface">{run.jobs_discovered}</td>
                  <td className="p-3 text-secondary">
                    +{run.jobs_created} / ~{run.jobs_updated}
                  </td>
                  <td className="p-3">
                    <span
                      className={`text-[10px] font-semibold ${
                        run.is_reconciliation_safe ? 'text-secondary' : 'text-outline'
                      }`}
                    >
                      {run.is_reconciliation_safe ? 'Safe' : 'Bypassed'}
                    </span>
                  </td>
                  <td className="p-3 text-right text-outline">
                    {new Date(run.started_at).toLocaleTimeString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
