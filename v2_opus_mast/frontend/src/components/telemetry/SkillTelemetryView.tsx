import React from 'react';
import { TelemetryResponse } from '../../types/api';

interface SkillTelemetryViewProps {
  telemetry: TelemetryResponse | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export const SkillTelemetryView: React.FC<SkillTelemetryViewProps> = ({
  telemetry,
  isLoading,
  onRefresh,
}) => {
  if (isLoading) {
    return (
      <div className="p-space-xl flex flex-col items-center justify-center gap-3">
        <span className="material-symbols-outlined text-3xl animate-spin text-primary">sync</span>
        <span className="font-mono text-xs text-outline">Computing market telemetry...</span>
      </div>
    );
  }

  if (!telemetry || telemetry.skills_telemetry.length === 0) {
    return (
      <div className="p-12 text-center rounded-xl bg-surface-container-low border border-outline-variant flex flex-col items-center justify-center gap-3">
        <span className="material-symbols-outlined text-4xl text-outline">analytics</span>
        <h3 className="text-base font-semibold text-on-surface">No Telemetry Observations</h3>
        <p className="text-xs text-on-surface-variant max-w-md">
          Run a career sync to aggregate skill share percentages and company breadth across active openings.
        </p>
        <button
          onClick={onRefresh}
          className="mt-2 px-3 py-1.5 rounded-lg bg-surface-container-high border border-outline-variant text-primary font-mono text-xs"
        >
          Refresh Telemetry
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-space-lg">
      {/* Degraded Source Warning Banner */}
      {telemetry.data_quality_warnings && telemetry.data_quality_warnings.length > 0 && (
        <div className="p-3 rounded-lg bg-error-container/20 border border-error/30 flex items-start gap-2.5">
          <span className="material-symbols-outlined text-error text-lg mt-0.5">warning</span>
          <div className="flex-1">
            <h4 className="text-xs font-bold text-error">Data Quality Safeguard Active</h4>
            <div className="mt-1 space-y-1">
              {telemetry.data_quality_warnings.map((w, idx) => (
                <p key={idx} className="font-mono text-[11px] text-error/90">
                  {w}
                </p>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Header Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
        <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between">
          <span className="font-mono text-[10px] text-outline uppercase tracking-wider font-semibold">
            Eligible Technical Postings
          </span>
          <span className="text-3xl font-bold text-on-surface my-1">
            {telemetry.total_eligible_jobs}
          </span>
          <span className="font-mono text-[10px] text-outline">Evaluated via Strict Filter</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between">
          <span className="font-mono text-[10px] text-outline uppercase tracking-wider font-semibold">
            Indexed Technical Skills
          </span>
          <span className="text-3xl font-bold text-secondary my-1">
            {telemetry.skills_telemetry.length}
          </span>
          <span className="font-mono text-[10px] text-outline">Automated Multi-Scope Extraction</span>
        </div>

        <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between">
          <span className="font-mono text-[10px] text-outline uppercase tracking-wider font-semibold">
            Telemetry Window
          </span>
          <span className="text-3xl font-bold text-primary my-1">30-Day Delta</span>
          <span className="font-mono text-[10px] text-outline">
            {telemetry.has_prior_window
              ? `Live jobs now vs ${telemetry.prior_window_jobs} live jobs 30–60 days ago`
              : 'Not enough history yet (needs a prior 30-day window)'}
          </span>
        </div>
      </div>

      {/* Ranked Telemetry Table */}
      <div className="rounded-xl bg-surface-container-low border border-outline-variant overflow-hidden">
        <div className="p-space-md border-b border-outline-variant flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-base">query_stats</span>
            <span className="text-sm font-bold text-on-surface">Market Skill Share & Trend Table</span>
          </div>
          <span className="font-mono text-xs text-outline">
            {telemetry.skills_telemetry.length} Tracked Technologies
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-xs">
            <thead className="bg-surface-container-lowest text-outline border-b border-outline-variant">
              <tr>
                <th className="p-3">Skill / Technology</th>
                <th className="p-3">Category</th>
                <th className="p-3">Live Roles</th>
                <th className="p-3">Skill Share %</th>
                <th className="p-3">Company Breadth</th>
                <th className="p-3">Demand Breakdown</th>
                <th className="p-3 text-right">30d Trend</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/40">
              {telemetry.skills_telemetry.map((item) => {
                const delta = item.period_over_period_delta_pct;
                const noDelta = delta === null || delta === undefined;
                const isPositive = !noDelta && delta >= 0;
                return (
                  <tr key={item.skill_id} className="hover:bg-surface-container transition-colors">
                    <td className="p-3 font-bold text-on-surface flex items-center gap-2">
                      <span>{item.skill_name}</span>
                    </td>
                    <td className="p-3 text-outline">{item.category}</td>
                    <td className="p-3 text-on-surface">{item.job_count}</td>
                    <td className="p-3 text-secondary font-semibold">{item.skill_share_pct}%</td>
                    <td className="p-3 text-on-surface-variant">{item.company_breadth} orgs</td>
                    <td className="p-3">
                      <div className="flex items-center gap-1.5 text-[10px]">
                        <span className="px-1.5 py-0.5 rounded bg-secondary/15 text-secondary">
                          Req: {item.demand_breakdown.required}
                        </span>
                        <span className="px-1.5 py-0.5 rounded bg-surface-container-high text-outline">
                          Pref: {item.demand_breakdown.preferred}
                        </span>
                      </div>
                    </td>
                    <td className="p-3 text-right font-semibold">
                      {noDelta ? (
                        <span
                          className="text-outline font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface-container-high border border-outline-variant"
                          title="No prior 30-day window of live jobs to compare against"
                        >
                          Not enough history
                        </span>
                      ) : (
                        <span className={isPositive ? 'text-secondary' : 'text-error'}>
                          {isPositive ? '+' : ''}
                          {delta}%
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
