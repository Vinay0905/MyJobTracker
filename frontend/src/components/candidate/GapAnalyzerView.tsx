import React, { useState } from 'react';
import { GapAnalysisResponse, CandidateProfile, RoleGapAnalysis } from '../../types/api';
import { updateCandidateProfile } from '../../api/client';

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
  const [candidateYoe, setCandidateYoe] = useState<number>(profile?.overall_yoe || 3.0);

  if (isLoading) {
    return (
      <div className="p-space-xl flex flex-col items-center justify-center gap-3">
        <span className="material-symbols-outlined text-3xl animate-spin text-primary">psychology</span>
        <span className="font-mono text-xs text-outline">Evaluating candidate skill coverage...</span>
      </div>
    );
  }

  const handleAddSkill = async () => {
    if (!skillInput.trim() || !profile) return;
    const newSkillId = skillInput.trim().toLowerCase().replace(/[^a-z0-9]/g, '_');
    
    const updatedSkills = [
      ...profile.skills,
      {
        skill_id: newSkillId,
        skill_name: skillInput.trim(),
        proficiency: 'intermediate',
        evidence_level: 'production' as const,
      },
    ];

    await updateCandidateProfile({
      name: profile.name,
      overall_yoe: candidateYoe,
      skills: updatedSkills,
    });

    setSkillInput('');
    onRefresh();
  };

  const handleRemoveSkill = async (skillId: string) => {
    if (!profile) return;
    const updatedSkills = profile.skills.filter((s) => s.skill_id !== skillId);
    await updateCandidateProfile({
      name: profile.name,
      overall_yoe: candidateYoe,
      skills: updatedSkills,
    });
    onRefresh();
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
              max="30"
              value={candidateYoe}
              onChange={(e) => setCandidateYoe(parseFloat(e.target.value) || 0)}
              className="w-16 bg-surface-container-lowest border border-outline-variant rounded px-1.5 py-0.5 font-mono text-secondary font-bold text-xs"
            />
            <span>Years • Verified Skills: {profile?.skills.length || 0}</span>
          </p>
        </div>

        {/* Skill Add Input */}
        <div className="flex items-center gap-2 w-full md:w-auto">
          <input
            type="text"
            value={skillInput}
            onChange={(e) => setSkillInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddSkill()}
            placeholder="Add verified skill (e.g. C++, CUDA, PyTorch)..."
            className="bg-surface-container-lowest border border-outline-variant rounded-lg px-3 py-1.5 font-mono text-xs text-on-surface placeholder:text-outline focus:outline-none focus:border-primary"
          />
          <button
            onClick={handleAddSkill}
            className="bg-primary text-on-primary px-3 py-1.5 rounded-lg font-mono text-xs font-semibold hover:bg-white transition-colors"
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
            {gapData.one_skill_away_roles.map((role: RoleGapAnalysis) => (
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
                  <div className="my-3 p-2.5 rounded-lg bg-surface-container border border-primary/40">
                    <div className="flex items-center gap-1.5 font-mono text-xs text-primary font-semibold mb-1">
                      <span className="material-symbols-outlined text-sm">target</span>
                      <span>The 1 Missing Skill: {role.missing_required[0]?.skill_id.toUpperCase()}</span>
                    </div>
                    <p className="font-mono text-[11px] text-on-surface-variant italic bg-surface-container-lowest p-2 rounded">
                      "{role.missing_required[0]?.job_evidence}"
                    </p>
                  </div>

                  {/* Experience Deficit Distinction */}
                  {role.has_experience_gap ? (
                    <div className="p-2 rounded bg-error-container/15 border border-error/30 text-error font-mono text-[11px] flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-sm">warning</span>
                      <span>Experience Gap: Role specifies {role.job_min_yoe}+ YOE (Deficit: {role.yoe_deficit} YOE)</span>
                    </div>
                  ) : (
                    <div className="p-2 rounded bg-secondary/10 border border-secondary/20 text-secondary font-mono text-[11px] flex items-center gap-1.5">
                      <span className="material-symbols-outlined text-sm">check_circle</span>
                      <span>Experience Cleared: Your {role.candidate_yoe} YOE satisfies requirement</span>
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
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
