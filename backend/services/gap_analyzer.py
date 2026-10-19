from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models import Job, JobSkillEvidence, JobExperienceRequirement, CandidateProfile, CandidateSkillEvidence, LifecycleStatus

class GapAnalyzerService:
    """
    Evaluates candidate skills against active job requirements.
    Calculates coverage scores, prioritizes missing technical skills,
    and decouples learnable skill gaps from experience gaps.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def analyze_candidate_gap(
        self,
        candidate_id: str = "default",
        target_category: Optional[str] = None,
        include_demo: bool = False,
    ) -> Dict[str, Any]:
        # 1. Load candidate profile and verified skills
        stmt_cand = select(CandidateProfile).options(
            selectinload(CandidateProfile.skills)
        ).where(CandidateProfile.candidate_id == candidate_id)
        candidate = (await self.session.execute(stmt_cand)).scalar_one_or_none()
        if not candidate:
            candidate_skills: Dict[str, str] = {}
            candidate_yoe: Optional[float] = None
        else:
            candidate_skills = {s.skill_id: s.evidence_level for s in candidate.skills}
            candidate_yoe = candidate.overall_yoe

        # 2. Query active engineering jobs
        stmt = select(Job).options(
            selectinload(Job.skills),
            selectinload(Job.experience_requirements),
            selectinload(Job.snapshots),
            selectinload(Job.source),
        ).where(Job.lifecycle_status == LifecycleStatus.ACTIVE.value)

        if not include_demo:
            stmt = stmt.where(Job.is_demo == False)

        if target_category:
            stmt = stmt.where(Job.canonical_category.ilike(f"%{target_category}%"))

        jobs = (await self.session.execute(stmt)).scalars().all()

        analyzed_roles: List[Dict[str, Any]] = []
        one_skill_away_roles: List[Dict[str, Any]] = []

        for job in jobs:
            active_skills = job.latest_skills
            active_experience = job.latest_experience

            required_skills = [s for s in active_skills if s.requirement_type == "required"]
            preferred_skills = [s for s in active_skills if s.requirement_type == "preferred"]

            satisfied_required = []
            missing_required = []
            satisfied_preferred = []
            missing_preferred = []

            for s in required_skills:
                if s.skill_id in candidate_skills:
                    satisfied_required.append({
                        "skill_id": s.skill_id,
                        "evidence_level": candidate_skills[s.skill_id],
                        "job_evidence": s.evidence_text,
                    })
                else:
                    missing_required.append({
                        "skill_id": s.skill_id,
                        "job_evidence": s.evidence_text,
                    })

            for s in preferred_skills:
                if s.skill_id in candidate_skills:
                    satisfied_preferred.append({
                        "skill_id": s.skill_id,
                        "evidence_level": candidate_skills[s.skill_id],
                        "job_evidence": s.evidence_text,
                    })
                else:
                    missing_preferred.append({
                        "skill_id": s.skill_id,
                        "job_evidence": s.evidence_text,
                    })

            # Calculate weighted coverage score
            req_weight = 1.0
            pref_weight = 0.3
            total_points = (len(required_skills) * req_weight) + (len(preferred_skills) * pref_weight)
            earned_points = (len(satisfied_required) * req_weight) + (len(satisfied_preferred) * pref_weight)
            coverage_score = round((earned_points / total_points * 100), 1) if total_points > 0 else 100.0

            # Experience gap evaluation
            job_min_yoe = None
            yoe_reqs = [r for r in active_experience if r.min_years is not None]
            if yoe_reqs:
                job_min_yoe = min(r.min_years for r in yoe_reqs)

            has_experience_gap = False
            yoe_deficit = None
            yoe_gap_warning = None
            if candidate_yoe is None:
                has_experience_gap = False
                yoe_deficit = None
                yoe_gap_warning = "Candidate experience not configured"
            elif job_min_yoe is not None and candidate_yoe < job_min_yoe:
                has_experience_gap = True
                yoe_deficit = round(job_min_yoe - candidate_yoe, 1)
                yoe_gap_warning = f"Candidate has {candidate_yoe} YOE, but role specifies a minimum of {job_min_yoe} YOE."

            # Strict 1-Skill Away logic: missing exactly 1 required, or 0 required and 1 preferred
            is_one_skill_away = (len(missing_required) == 1) or (len(missing_required) == 0 and len(missing_preferred) == 1)

            analysis = {
                "job_id": job.job_id,
                "title": job.title,
                "company": job.source.company_id if job.source else "Tech",
                "canonical_category": job.canonical_category,
                "location": job.location,
                "coverage_score": coverage_score,
                "satisfied_required": satisfied_required,
                "missing_required": missing_required,
                "satisfied_preferred": satisfied_preferred,
                "missing_preferred": missing_preferred,
                "has_experience_gap": has_experience_gap,
                "yoe_deficit": yoe_deficit,
                "yoe_gap_warning": yoe_gap_warning,
                "candidate_yoe": candidate_yoe,
                "job_min_yoe": job_min_yoe,
                "is_one_skill_away": is_one_skill_away,
                "apply_url": job.apply_url,
            }
            analyzed_roles.append(analysis)

            if is_one_skill_away:
                one_skill_away_roles.append(analysis)

        # Sort analyzed roles by coverage score descending
        analyzed_roles.sort(key=lambda x: x["coverage_score"], reverse=True)
        one_skill_away_roles.sort(key=lambda x: x["coverage_score"], reverse=True)

        is_profile_configured = (candidate is not None and candidate_yoe is not None and len(candidate_skills) > 0)

        return {
            "candidate_yoe": candidate_yoe,
            "candidate_skills_count": len(candidate_skills),
            "total_roles_analyzed": len(analyzed_roles),
            "one_skill_away_count": len(one_skill_away_roles),
            "one_skill_away_roles": one_skill_away_roles[:10],
            "top_matched_roles": analyzed_roles[:10],
            "experience_alignment": "evaluated" if candidate_yoe is not None else "unknown_candidate_yoe",
            "analysis_complete": is_profile_configured,
            "status_message": "Full alignment evaluated" if is_profile_configured else "Configure your profile & YOE to calculate full alignment",
        }
