import React from 'react';
import { JobDetail } from '../../types/api';
import { CompanyLogo } from '../common/CompanyLogo';

interface JobDetailDrawerProps {
  job: JobDetail | null;
  isOpen: boolean;
  onClose: () => void;
}

export const JobDetailDrawer: React.FC<JobDetailDrawerProps> = ({ job, isOpen, onClose }) => {
  if (!isOpen || !job) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end">
      <div className="w-full max-w-2xl bg-surface-container-low border-l border-outline-variant h-full overflow-y-auto flex flex-col shadow-2xl">
        {/* Header */}
        <div className="p-space-lg border-b border-outline-variant flex items-start justify-between bg-surface-container-lowest sticky top-0 z-10">
          <div className="flex items-start gap-3.5">
            <CompanyLogo
              company={job.company}
              domain={job.company_domain}
              category={job.canonical_category}
              size="lg"
              className="mt-0.5"
            />
            <div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs font-semibold text-primary">{job.company}</span>
              <span className="text-outline text-xs">•</span>
              <span className="font-mono text-xs text-on-surface-variant">{job.canonical_category}</span>
            </div>
            <h2 className="text-xl font-bold text-on-surface mt-1">{job.title}</h2>
            <div className="flex items-center gap-3 mt-2 font-mono text-xs text-outline">
              <span className="flex items-center gap-1">
                <span className="material-symbols-outlined text-sm">location_on</span>
                {job.location}
              </span>
              <span>•</span>
              <span className="capitalize">{job.work_arrangement}</span>
              <span>•</span>
              <span className="text-secondary font-semibold">{job.lifecycle_status}</span>
            </div>
          </div>
        </div>

        <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-surface-container text-outline hover:text-on-surface transition-colors"
          >
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        {/* Content Body */}
        <div className="p-space-lg flex flex-col gap-space-lg flex-1">
          {/* Section 0: Snapshot Provenance & Identity Card */}
          <div className="p-3.5 rounded-lg bg-surface-container border border-primary/25 flex flex-col gap-2 font-mono text-xs">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 font-bold text-primary">
                <span className="material-symbols-outlined text-sm">history_edu</span>
                Snapshot Provenance: #{job.snapshots_count || 1}
              </span>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-surface-container-highest text-on-surface-variant border border-outline-variant/60">
                Pipeline v{job.latest_pipeline_version || '1.0'} ({job.latest_extraction_method || 'deterministic'})
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px] text-outline pt-1">
              <div>
                <span className="text-on-surface-variant font-medium">Requisition ID: </span>
                <span>{job.requisition_id || 'None'}</span>
              </div>
              <div>
                <span className="text-on-surface-variant font-medium">Internal ID: </span>
                <span>{job.internal_job_id || 'None'}</span>
              </div>
              <div>
                <span className="text-on-surface-variant font-medium">Captured: </span>
                <span>{new Date(job.latest_snapshot_observed_at || job.last_seen_at).toLocaleDateString()}</span>
              </div>
              <div>
                <span className="text-on-surface-variant font-medium">Data Integrity: </span>
                <span className={job.is_demo ? 'text-amber-400 font-semibold' : 'text-secondary font-semibold'}>
                  {job.is_demo ? 'Demo Fixture (is_demo=True)' : 'Live ATS Observation'}
                </span>
              </div>
            </div>
            {job.latest_extraction_signature && (
              <div className="text-[10px] text-outline/80 border-t border-outline-variant/40 pt-1 flex items-center justify-between">
                <span>Signature: {job.latest_extraction_signature.slice(0, 24)}...</span>
                <span>Idempotent SHA-256</span>
              </div>
            )}
          </div>

          {/* Section 1: Extracted Skills with Sentence Evidence */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between border-b border-outline-variant/60 pb-1.5">
              <span className="font-mono text-xs text-outline uppercase tracking-wider font-semibold">
                Extracted Skills & Sentence Evidence ({job.skills.length})
              </span>
              <span className="font-mono text-[10px] text-secondary">Deterministic Regex + Scope</span>
            </div>

            <div className="space-y-2.5">
              {job.skills.map((s, idx) => {
                const isReq = s.requirement_type === 'required';
                return (
                  <div
                    key={idx}
                    className="p-3 rounded-lg bg-surface-container border border-outline-variant flex flex-col gap-1.5"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold text-on-surface">
                          {s.skill_id.toUpperCase()}
                        </span>
                        <span
                          className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${
                            isReq
                              ? 'bg-secondary/15 text-secondary border border-secondary/30'
                              : 'bg-primary/15 text-primary border border-primary/30'
                          }`}
                        >
                          {s.requirement_type.toUpperCase()}
                        </span>
                      </div>
                      <span className="font-mono text-[10px] text-outline">
                        {s.extraction_method}
                      </span>
                    </div>

                    <p className="font-mono text-xs text-on-surface-variant bg-surface-container-lowest p-2 rounded border border-outline-variant/40 italic">
                      "{s.evidence_text}"
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Section 2: Experience Requirements */}
          <div className="flex flex-col gap-3">
            <span className="font-mono text-xs text-outline uppercase tracking-wider font-semibold border-b border-outline-variant/60 pb-1.5">
              Experience Requirements ({job.experience_requirements.length})
            </span>

            <div className="space-y-2">
              {job.experience_requirements.map((exp, idx) => (
                <div
                  key={idx}
                  className="p-3 rounded-lg bg-surface-container border border-outline-variant flex flex-col gap-1"
                >
                  <div className="flex items-center justify-between font-mono text-xs">
                    <span className="text-secondary font-semibold">
                      {exp.min_years ? `${exp.min_years}+ Years` : 'Signal'}
                    </span>
                    <span className="text-outline uppercase text-[10px]">
                      Scope: {exp.experience_scope}
                    </span>
                  </div>
                  <p className="font-mono text-xs text-on-surface-variant italic">
                    "{exp.evidence_text}"
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Section 3: Field Change Audit Trail */}
          {job.field_changes.length > 0 && (
            <div className="flex flex-col gap-3">
              <span className="font-mono text-xs text-outline uppercase tracking-wider font-semibold border-b border-outline-variant/60 pb-1.5">
                Audit Trail & Field Changes ({job.field_changes.length})
              </span>
              <div className="space-y-2">
                {job.field_changes.map((c, idx) => (
                  <div
                    key={idx}
                    className="p-2.5 rounded bg-surface-container border border-outline-variant font-mono text-xs"
                  >
                    <div className="flex justify-between text-outline text-[10px] mb-1">
                      <span>Field: {c.field_name}</span>
                      <span>{new Date(c.timestamp).toLocaleString()}</span>
                    </div>
                    <div className="text-error line-through text-[11px]">- {c.old_value}</div>
                    <div className="text-secondary text-[11px]">+ {c.new_value}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section 4: Normalized Description */}
          <div className="flex flex-col gap-2">
            <span className="font-mono text-xs text-outline uppercase tracking-wider font-semibold border-b border-outline-variant/60 pb-1.5">
              Full Normalized Posting Text
            </span>
            <div className="bg-surface-container-lowest p-3 rounded-lg border border-outline-variant font-mono text-xs text-on-surface-variant whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
              {job.normalized_description}
            </div>
          </div>
        </div>

        {/* Footer CTA */}
        <div className="p-space-md border-t border-outline-variant bg-surface-container-lowest flex items-center justify-between sticky bottom-0">
          <span className="font-mono text-[10px] text-outline">
            Hash: {job.description_hash.slice(0, 16)}...
          </span>
          <a
            href={
              job.apply_url && job.apply_url.trim().startsWith('http')
                ? job.apply_url
                : `https://www.google.com/search?q=${encodeURIComponent(job.company + ' careers ' + job.title)}`
            }
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 bg-primary-container text-on-primary-container px-4 py-2 rounded-lg font-mono text-xs font-semibold hover:bg-primary transition-colors shadow-sm"
            title={job.apply_url && job.apply_url.startsWith('http') ? 'Apply on employer career portal' : 'Search job on Google'}
          >
            <span>Apply at Employer Site</span>
            <span className="material-symbols-outlined text-sm">arrow_outward</span>
          </a>
        </div>
      </div>
    </div>
  );
};
