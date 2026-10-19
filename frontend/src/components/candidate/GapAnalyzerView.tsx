import React, { useEffect, useState } from 'react';
import { GapAnalysisResponse, CandidateProfile, CandidateSkill, RoleGapAnalysis } from '../../types/api';
import { resolveSkill, updateCandidateProfile } from '../../api/client';

interface GapAnalyzerViewProps {
  gapData: GapAnalysisResponse | null;
  profile: CandidateProfile | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export const GapAnalyzerView: React.FC<GapAnalyzerViewProps> = ({
  gapData,
  profile,
  isLoading,
  onRefresh,
}) => {
  const [skillInput, setSkillInput] = useState('');
  // Empty until the profile loads; only sent to the backend once the user edits it.
  const [yoeInput, setYoeInput] = useState<string>('');
  const [yoeDirty, setYoeDirty] = useState<boolean>(false);
  const [message, setMessage] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);

  useEffect(() => {
    if (!profile || yoeDirty) return;
    setYoeInput(profile.overall_yoe === null || profile.overall_yoe === undefined ? '' : String(profile.overall_yoe));
  }, [profile, yoeDirty]);

  if (isLoading) {
    return (
      <div className="p-space-xl flex flex-col items-center justify-center gap-3">
        <span className="material-symbols-outlined text-3xl animate-spin text-primary">psychology</span>
        <span className="font-mono text-xs text-outline">Evaluating candidate skill coverage...</span>
      </div>
    );
  }

  const saveProfile = async (skills: CandidateSkill[]): Promise<boolean> => {
    if (!profile) return false;
    let yoePayload: { overall_yoe?: number | null } = {};
    if (yoeDirty) {
      const trimmed = yoeInput.trim();
      const parsed = trimmed === '' ? null : Number(trimmed);
      if (parsed !== null && (Number.isNaN(parsed) || parsed < 0 || parsed > 50)) {
        setMessage('Years of experience must be a number between 0 and 50.');
        return false;
      }
      yoePayload = { overall_yoe: parsed };
    }
    setIsSaving(true);
    try {
      await updateCandidateProfile({
        name: profile.name,
        skills: skills.map(({ skill_id, proficiency, evidence_level, notes }) => ({ skill_id, proficiency, evidence_level, notes })),
        ...yoePayload,
      });
      if (yoeDirty) setYoeDirty(false);
      onRefresh();
      return true;
    } catch (e) {
      setMessage((e as Error).message || 'Failed to save profile');
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddSkill = async () => {
    const typed = skillInput.trim();
    if (!typed || !profile) return;
    setMessage(null);

    const match = await resolveSkill(typed).catch(() => null);
    if (!match) {
      setMessage(`"${typed}" is not a skill DevRadar tracks. Try a taxonomy skill such as C++, C#, CUDA, or PyTorch.`);
      return;
    }
    if (profile.skills.some((s) => s.skill_id === match.skill_id)) {
      setMessage(`${match.skill_name} is already on your profile.`);
      setSkillInput('');
      return;
    }

    const saved = await saveProfile([
      ...profile.skills,
      {
        skill_id: match.skill_id,
        skill_name: match.skill_name,
        proficiency: 'intermediate',
        evidence_level: 'production',
      },
    ]);
    if (saved) setSkillInput('');
  };

  const handleRemoveSkill = async (skillId: string) => {
    if (!profile) return;
    setMessage(null);
    await saveProfile(profile.skills.filter((s) => s.skill_id !== skillId));
  };

  return (
    <div className="flex flex-col gap-space-lg">
      {/* Candidate Profile Strip */}
      <div className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-primary text-base">person</span>
            <span className="text-sm font-bold text-on-surface">Candidate Profile</span>
          </div>
          <p className="font-mono text-xs text-on-surface-variant mt-0.5 flex items-center gap-2">
            <span>Overall Experience:</span>
            <input
              type="number"
              step="0.5"
              min="0"
              max="50"
              value={yoeInput}
              disabled={!profile}
              placeholder={profile ? 'not set' : '…'}
              onChange={(e) => {
                setYoeInput(e.target.value);
                setYoeDirty(true);
              }}
              className="w-16 bg-surface-container-lowest border border-outline-variant rounded px-1.5 py-0.5 font-mono text-secondary font-bold text-xs disabled:opacity-50"
            />
            <span>Years • Verified Skills: {profile?.skills.length || 0}</span>
            {yoeDirty && profile && (
              <button
                onClick={() => saveProfile(profile.skills)}
                disabled={isSaving}
                className="px-2 py-0.5 rounded bg-secondary/20 text-secondary border border-secondary/40 font-semibold disabled:opacity-50"
              >
                Save years
              </button>
            )}
          </p>
          {message && (
            <p className="font-mono text-[11px] text-error mt-1">{message}</p>
          )}
        </div>

        {/* Skill Add Input */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <input
            type="text"
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddSkill()}
            placeholder="Add verified skill (e.g. C++, CUDA, PyTorch)..."
            disabled={!profile}
            className="bg-surface-container-lowest border border-outline-variant rounded-lg px-3 py-1.5 font-mono text-xs text-on-surface placeholder:text-outline focus:outline-none focus:border-primary disabled:opacity-50"
          />
          <button
            onClick={handleAddSkill}
            disabled={!profile || isSaving}
            className="bg-primary text-on-primary px-3 py-1.5 rounded-lg font-mono text-xs font-semibold hover:bg-white transition-colors disabled:opacity-50"
          >
            Add
          </button>
        </div>
      </div>

      {/* Candidate Active Skills Chips */}
      {profile && profile.skills.length > 0 && (
        <div className="flex flex-wrap gap-1.5 p-3 rounded-lg bg-surface-container border border-outline-variant">
          {profile.skills.map((s) => (
            <span
              key={s.skill_id}
              className="inline-flex items-center gap-1 font-mono text-xs px-2 py-1 rounded bg-surface-container-high border border-outline-variant text-on-surface"
            >
              <span className="font-semibold text-primary">{s.skill_name || s.skill_id}</span>
              <span className="text-[10px] text-outline uppercase">({s.evidence_level})</span>
              <button
                onClick={() => handleRemoveSkill(s.skill_id)}
                className="hover:text-error transition-colors ml-1"
              >
                <span className="material-symbols-outlined text-xs leading-none">close</span>
              </button>
            </span>
          ))}
        </div>
      )}

      {/* "1-Skill Away" High Leverage Opportunities */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between border-b border-outline-variant/60 pb-2">
          <div className="flex items-center gap-2">
            <span className="material-symbols-outlined text-secondary text-lg">bolt</span>
            <span className="text-sm font-bold text-on-surface">
              High-Leverage "1-Skill Away" Roles ({gapData?.one_skill_away_count || 0})
            </span>
          </div>
          <span className="font-mono text-xs text-outline">
            Decoupled Technical Gap vs Experience Deficit
          </span>
        </div>

        {(!gapData || gapData.one_skill_away_roles.length === 0) ? (
          <div className="p-8 text-center rounded-xl bg-surface-container-low border border-outline-variant text-outline font-mono text-xs">
            No exact 1-skill-away openings identified. Add more of your skills above to uncover target roles.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            {gapData.one_skill_away_roles.map((role: RoleGapAnalysis) => {
              const gap =
                role.one_skill_gap ||
                (role.missing_required[0]
                  ? { ...role.missing_required[0], requirement_type: 'required' as const }
                  : role.missing_preferred[0]
                  ? { ...role.missing_preferred[0], requirement_type: 'preferred' as const }
                  : null);
              return (
              <div
                key={role.job_id}
                className="p-space-md rounded-xl bg-surface-container-low border border-outline-variant flex flex-col justify-between"
              >
                <div>
                  <div className="flex justify-between items-start gap-2">
                    <div>
                      <span className="font-mono text-xs text-secondary font-semibold">
                        {role.company} • {role.canonical_category}
                      </span>
                      <h4 className="text-sm font-bold text-on-surface mt-0.5">{role.title}</h4>
                      <span className="font-mono text-[11px] text-outline">{role.location}</span>
                    </div>
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-secondary/15 text-secondary border border-secondary/30">
                      {role.coverage_score}% Match
                    </span>
                  </div>

                  {/* Missing #1 Technical Skill Highlight */}
                  {gap && (
                    <div className="my-3 p-2.5 rounded-lg bg-surface-container border border-primary/40">
                      <div className="flex items-center gap-1.5 font-mono text-xs text-primary font-semibold mb-1">
                        <span className="material-symbols-outlined text-sm">target</span>
                        <span>The 1 Missing Skill: {gap.skill_id.toUpperCase()}</span>
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-container-high text-outline uppercase">
                          {gap.requirement_type}
                        </span>
                      </div>
                      <p className="font-mono text-[11px] text-on-surface-variant italic bg-surface-container-lowest p-2 rounded">
                        "{gap.job_evidence}"
                      </p>
                    </div>
                  )}

                  {/* Experience Deficit Distinction */}
                  {role.has_experience_gap ? (
                    <div className="p-2 rounded bg-error-container/15 border border-error/30 text-error font-mono text-[11px] flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-sm">warning</span>
                      <span>Experience Gap: Role specifies {role.job_min_yoe}+ YOE (Deficit: {role.yoe_deficit} YOE)</span>
                    </div>
                  ) : role.candidate_yoe === null || role.candidate_yoe === undefined ? (
                    <div className="p-2 rounded bg-surface-container border border-outline-variant text-outline font-mono text-[11px] flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-sm">help</span>
                      <span>Set your years of experience above to check this role's requirement</span>
                    </div>
                  ) : role.job_min_yoe === null || role.job_min_yoe === undefined ? (
                    <div className="p-2 rounded bg-surface-container border border-outline-variant text-outline font-mono text-[11px] flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-sm">help</span>
                      <span>Role states no years requirement (YOE unspecified)</span>
                    </div>
                  ) : (
                    <div className="p-2 rounded bg-secondary/10 border border-secondary/20 text-secondary font-mono text-[11px] flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-sm">check_circle</span>
                      <span>Experience Cleared: Your {role.candidate_yoe} YOE meets the {role.job_min_yoe}+ YOE requirement</span>
                    </div>
                  )}
                </div>

                <div className="pt-3 mt-3 border-t border-outline-variant/60 flex items-center justify-between font-mono text-xs">
                  <span className="text-outline">{role.satisfied_required.length} Skills Satisfied</span>
                  <a
                    href={role.apply_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-primary hover:text-white font-semibold transition-colors"
                  >
                    <span>View Opening</span>
                    <span className="material-symbols-outlined text-xs">arrow_outward</span>
                  </a>
                </div>
              </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
