import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func, desc, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.session import get_db_session, async_session_factory
from backend.db.models import (
    Company,
    Source,
    Job,
    JobSkillEvidence,
    JobExperienceRequirement,
    JobFieldChangeEvent,
    SyncRun,
    CandidateProfile,
    CandidateSkillEvidence,
    LifecycleStatus,
)
from backend.api.schemas import (
    JobsResponse,
    JobListItemSchema,
    JobDetailSchema,
    SkillEvidenceSchema,
    ExperienceRequirementSchema,
    FieldChangeSchema,
    TopSkillsResponse,
    TopSkillItem,
    TelemetryResponse,
    SourceItemSchema,
    SyncRunSchema,
    CandidateProfileUpdate,
)
from backend.services.telemetry import TelemetryEngine
from backend.services.gap_analyzer import GapAnalyzerService
from backend.connectors.manager import ConnectorManager
from backend.services.reconciler import SafeReconciliationEngine

router = APIRouter(prefix="/api")

# In-memory per-source sync locks to protect against concurrent overlapping sync triggers
SOURCE_LOCKS: dict[str, asyncio.Lock] = {}
SYNC_LOCK = asyncio.Lock()

@router.get("/health")
async def get_health(session: AsyncSession = Depends(get_db_session)):
    """Distinguishes internal application health from external ATS source health."""
    sources = (await session.execute(select(Source))).scalars().all()
    degraded_sources = [s.source_id for s in sources if s.health_status != "HEALTHY"]

    return {
        "status": "healthy",
        "database": "connected",
        "external_sources_total": len(sources),
        "degraded_sources_count": len(degraded_sources),
        "degraded_sources": degraded_sources,
    }

from urllib.parse import urlparse

def extract_domain(website_url: Optional[str], company_name: str) -> str:
    if website_url:
        netloc = urlparse(website_url).netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if netloc:
            return netloc
    
    FALLBACK_DOMAINS = {
        "nvidia": "nvidia.com",
        "epic games": "epicgames.com",
        "rockstar games": "rockstargames.com",
        "qualcomm": "qualcomm.com",
        "careem": "careem.com",
        "g42": "g42.ai",
        "apple": "apple.com",
        "amazon": "amazon.com",
        "microsoft": "microsoft.com",
        "roblox": "roblox.com",
        "playstation studios": "playstation.com",
        "sony interactive entertainment": "playstation.com",
        "cerebras": "cerebras.ai",
        "cerebras systems": "cerebras.ai",
        "canonical": "canonical.com",
        "arista": "arista.com",
        "arista networks": "arista.com",
        "weride": "weride.ai",
        "weride uae": "weride.ai",
        "ea": "ea.com",
        "electronic arts": "ea.com",
    }
    cleaned = company_name.lower().strip()
    return FALLBACK_DOMAINS.get(cleaned, f"{cleaned.replace(' ', '')}.com")

ROLE_FOCUS_MAP = {
    # Granular Focus Tracks
    "ai npcs & game ai": {
        "skills": ["npc_ai", "game_ai", "behavior_trees", "fsm", "goap", "utility_ai", "pathfinding", "crowd_simulation", "reinforcement_learning", "agentic_ai", "eqs", "unreal_engine", "unity", "cpp"],
        "keywords": ["npc", "game ai", "behavior tree", "navmesh", "pathfinding", "agentic", "reinforcement learning", "massentity", "ai character", "gameplay ai", "fsm"]
    },
    "physics & simulation": {
        "skills": ["physics_engine", "collision_detection", "ragdoll_physics", "procedural_animation", "physics_middleware", "simd", "linear_algebra", "simulation_frameworks", "cpp"],
        "keywords": ["physics", "simulation", "rigid body", "collision", "ragdoll", "kinematics", "physx", "havok", "chaos", "mujoco", "isaac sim", "omniverse", "dynamics"]
    },
    "gpu / cuda & silicon": {
        "skills": ["cuda", "rocm", "tensorrt", "triton", "opencl", "gpu_kernels", "parallel_computing", "verilog", "pytorch"],
        "keywords": ["cuda", "gpu", "rocm", "tensorrt", "triton", "kernel", "silicon", "accelerator", "parallel"]
    },
    "edge ai & embedded ece": {
        "skills": ["freertos", "device_drivers", "microcontrollers", "model_quantization", "rtos", "firmware", "arm", "c", "cpp"],
        "keywords": ["edge ai", "embedded", "rtos", "freertos", "zephyr", "qnx", "mcu", "microcontroller", "firmware", "driver", "tinyml", "arm"]
    },
    "ai servers & cloud": {
        "skills": ["distributed_systems", "rdma_networking", "sre", "linux_kernel", "docker", "kubernetes", "terraform", "ci_cd", "aws", "gcp"],
        "keywords": ["cloud", "distributed", "cluster", "rdma", "infiniband", "kubernetes", "docker", "infra", "sre", "networking"]
    },
    # Backwards-compatible aliases
    "systems / c++": {
        "skills": ["cpp", "c", "linux_kernel", "multithreading", "distributed_systems", "os_concepts", "performance"],
        "keywords": ["system", "c++", "kernel", "runtime", "compiler", "performance", "low-level", "low level"]
    },
    "ai & gpu / cuda": {
        "skills": ["cuda", "pytorch", "tensorrt", "triton", "llm", "deep_learning", "machine_learning", "computer_vision", "distributed_training"],
        "keywords": ["ai", "ml", "deep learning", "gpu", "cuda", "vision", "neural", "algorithm", "machine learning"]
    },
    "game engine / graphics": {
        "skills": ["unreal_engine", "unity", "vulkan", "directx", "opengl", "shaders", "rendering", "physics"],
        "keywords": ["graphics", "engine", "rendering", "game", "gameplay", "vulkan", "unreal", "shader", "animation", "audio"]
    },
    "cloud & devops": {
        "skills": ["docker", "kubernetes", "aws", "gcp", "ci_cd", "terraform", "linux", "cloud"],
        "keywords": ["cloud", "devops", "sre", "infrastructure", "platform", "reliability", "deployment", "pipeline"]
    },
    "embedded / firmware": {
        "skills": ["rtos", "firmware", "arm", "c", "verilog", "fpga", "soc"],
        "keywords": ["embedded", "firmware", "rtos", "arm", "soc", "driver", "bsp", "board", "hardware"]
    }
}

@router.get("/jobs", response_model=JobsResponse)
async def list_jobs(
    company: Optional[str] = Query(None, description="Filter by company ID or name"),
    category: Optional[str] = Query(None, description="Silicon & AI | Game Studio | UAE & Middle East"),
    location: Optional[str] = Query(None, description="City, country, or remote preset"),
    role_focus: Optional[str] = Query(None, description="Comma-separated role focuses e.g. 'AI NPCs & Game AI,Physics & Simulation'"),
    skill: Optional[str] = Query(None, description="Any matching skill name or ID"),
    required_skill: Optional[str] = Query(None, description="Skill strictly required"),
    preferred_skill: Optional[str] = Query(None, description="Skill preferred"),
    max_required_yoe: Optional[int] = Query(None, description="Filter out roles requiring > max_required_yoe (e.g. 6)"),
    min_yoe: Optional[int] = Query(None, description="Alias for max_required_yoe"),
    lifecycle_status: Optional[str] = Query("ACTIVE", description="ACTIVE | MISSING_CANDIDATE | CLOSED | ALL"),
    work_arrangement: Optional[str] = Query(None, description="remote | hybrid | onsite"),
    search: Optional[str] = Query(None, description="Text search title, department, description"),
    include_demo: bool = Query(False, description="Include demo fixtures"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    """Paginated, multi-attribute filtered engineering job list."""
    stmt = select(Job).options(
        selectinload(Job.skills),
        selectinload(Job.experience_requirements),
        selectinload(Job.snapshots),
        selectinload(Job.source).selectinload(Source.company),
    )

    if not include_demo:
        stmt = stmt.where(Job.is_demo == False)

    if lifecycle_status and lifecycle_status.upper() != "ALL":
        stmt = stmt.where(Job.lifecycle_status == lifecycle_status.upper())

    if company:
        stmt = stmt.join(Job.source).join(Source.company).where(
            (Company.name.ilike(f"%{company}%")) | (Company.company_id.ilike(f"%{company}%"))
        )

    if category:
        stmt = stmt.where(Job.canonical_category.ilike(f"%{category}%"))

    if location:
        loc_clean = location.strip().lower()
        if loc_clean in ["remote", "remote only"]:
            stmt = stmt.where(
                or_(
                    Job.work_arrangement == "remote",
                    Job.location.ilike("%remote%")
                )
            )
        elif loc_clean in ["uae / me", "uae", "middle east", "me"]:
            stmt = stmt.where(
                or_(
                    Job.location.ilike("%dubai%"),
                    Job.location.ilike("%abu dhabi%"),
                    Job.location.ilike("%uae%"),
                    Job.location.ilike("%united arab emirates%"),
                    Job.location.ilike("%middle east%"),
                    Job.canonical_category == "UAE & Middle East"
                )
            )
        elif loc_clean in ["us / eu", "us", "eu", "usa", "europe"]:
            stmt = stmt.where(
                or_(
                    Job.location.ilike("%united states%"),
                    Job.location.ilike("%usa%"),
                    Job.location.ilike("%ca%"),
                    Job.location.ilike("%nc%"),
                    Job.location.ilike("%tx%"),
                    Job.location.ilike("%wa%"),
                    Job.location.ilike("%ny%"),
                    Job.location.ilike("%santa clara%"),
                    Job.location.ilike("%austin%"),
                    Job.location.ilike("%cary%"),
                    Job.location.ilike("%seattle%"),
                    Job.location.ilike("%united kingdom%"),
                    Job.location.ilike("%uk%"),
                    Job.location.ilike("%edinburgh%"),
                    Job.location.ilike("%london%"),
                    Job.location.ilike("%dundee%"),
                    Job.location.ilike("%germany%"),
                    Job.location.ilike("%france%"),
                    Job.location.ilike("%serbia%"),
                    Job.location.ilike("%denmark%"),
                    Job.location.ilike("%sweden%"),
                    Job.location.ilike("%poland%"),
                    Job.location.ilike("%netherlands%")
                )
            )
        elif loc_clean == "india":
            stmt = stmt.where(
                or_(
                    Job.location.ilike("%india%"),
                    Job.location.ilike("%bengaluru%"),
                    Job.location.ilike("%bangalore%"),
                    Job.location.ilike("%pune%"),
                    Job.location.ilike("%hyderabad%"),
                    Job.location.ilike("%mumbai%"),
                    Job.location.ilike("%chennai%")
                )
            )
        elif loc_clean in ["global", "all"]:
            pass
        else:
            stmt = stmt.where(Job.location.ilike(f"%{location}%"))

    if work_arrangement:
        stmt = stmt.where(Job.work_arrangement.ilike(f"%{work_arrangement}%"))

    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            (Job.title.ilike(search_term))
            | (Job.department.ilike(search_term))
            | (Job.normalized_description.ilike(search_term))
        )

    # Filter for role focus
    if role_focus:
        selected_roles = [r.strip().lower() for r in role_focus.split(",") if r.strip()]
        role_clauses = []
        for r in selected_roles:
            cfg = ROLE_FOCUS_MAP.get(r)
            if not cfg:
                norm_r = r.replace("&", "and").replace("/", " ")
                for k, v in ROLE_FOCUS_MAP.items():
                    norm_k = k.replace("&", "and").replace("/", " ")
                    if norm_r == norm_k or any(part in norm_k for part in norm_r.split() if len(part) > 2):
                        cfg = v
                        break
            if cfg:
                clause = or_(
                    Job.skills.any(JobSkillEvidence.skill_id.in_(cfg["skills"])),
                    *[Job.title.ilike(f"%{kw}%") for kw in cfg["keywords"]],
                    *[Job.department.ilike(f"%{kw}%") for kw in cfg["keywords"]],
                )
                role_clauses.append(clause)
        if role_clauses:
            stmt = stmt.where(or_(*role_clauses))

    # Subquery filter for skills
    if skill:
        stmt = stmt.where(Job.skills.any(JobSkillEvidence.skill_id.ilike(skill)))
    if required_skill:
        stmt = stmt.where(
            Job.skills.any(
                (JobSkillEvidence.skill_id.ilike(required_skill))
                & (JobSkillEvidence.requirement_type == "required")
            )
        )
    if preferred_skill:
        stmt = stmt.where(
            Job.skills.any(
                (JobSkillEvidence.skill_id.ilike(preferred_skill))
                & (JobSkillEvidence.requirement_type == "preferred")
            )
        )

    # Filter for max required YOE (keeps <= effective_max_yoe and unspecified-YOE roles)
    effective_max_yoe = max_required_yoe if max_required_yoe is not None else min_yoe
    if effective_max_yoe is not None:
        stmt = stmt.where(
            ~Job.experience_requirements.any(JobExperienceRequirement.min_years > effective_max_yoe)
        )

    # Execute total count query
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_count = (await session.execute(count_stmt)).scalar() or 0

    # Sector counts
    sector_stmt = (
        select(Job.canonical_category, func.count(Job.job_id))
        .where(Job.lifecycle_status == "ACTIVE")
    )
    if not include_demo:
        sector_stmt = sector_stmt.where(Job.is_demo == False)
    sector_stmt = sector_stmt.group_by(Job.canonical_category)
    sector_counts_raw = (await session.execute(sector_stmt)).all()
    sector_counts = {row[0]: row[1] for row in sector_counts_raw if row[0]}
    sector_counts["All Sectors"] = sum(sector_counts.values())

    # Paginate
    stmt = stmt.order_by(desc(Job.first_seen_at)).offset((page - 1) * page_size).limit(page_size)
    job_rows = (await session.execute(stmt)).scalars().all()

    items = []
    for j in job_rows:
        comp_name = j.source.company.name if (j.source and j.source.company) else j.source_id
        comp_domain = extract_domain(j.source.company.website_url if (j.source and j.source.company) else None, comp_name)
        active_skills = j.latest_skills
        active_experience = j.latest_experience
        req_skills = [s.skill_id for s in active_skills if s.requirement_type == "required"]
        pref_skills = [s.skill_id for s in active_skills if s.requirement_type == "preferred"]

        exp_years = [r.min_years for r in active_experience if r.min_years is not None]
        min_y = min(exp_years) if exp_years else None

        items.append(JobListItemSchema(
            job_id=j.job_id,
            company=comp_name,
            company_domain=comp_domain,
            canonical_category=j.canonical_category,
            title=j.title,
            department=j.department,
            location=j.location,
            work_arrangement=j.work_arrangement,
            apply_url=j.apply_url,
            requisition_id=j.requisition_id,
            internal_job_id=j.internal_job_id,
            is_demo=j.is_demo,
            first_seen_at=j.first_seen_at,
            last_seen_at=j.last_seen_at,
            lifecycle_status=j.lifecycle_status,
            primary_min_yoe=min_y,
            required_skills=req_skills,
            preferred_skills=pref_skills,
        ))

    return JobsResponse(
        total_count=total_count,
        page=page,
        page_size=page_size,
        jobs=items,
        sector_counts=sector_counts,
    )

@router.get("/jobs/{job_id}", response_model=JobDetailSchema)
async def get_job_detail(job_id: str, session: AsyncSession = Depends(get_db_session)):
    """Full detail attribution for a specific job including cited sentence evidence quotes and snapshot provenance."""
    stmt = select(Job).options(
        selectinload(Job.skills),
        selectinload(Job.experience_requirements),
        selectinload(Job.snapshots),
        selectinload(Job.extraction_runs),
        selectinload(Job.field_changes),
        selectinload(Job.source).selectinload(Source.company),
    ).where(Job.job_id == job_id)

    job = (await session.execute(stmt)).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")

    comp_name = job.source.company.name if (job.source and job.source.company) else job.source_id
    comp_domain = extract_domain(job.source.company.website_url if (job.source and job.source.company) else None, comp_name)
    active_skills = job.latest_skills
    active_experience = job.latest_experience
    snapshots = job.snapshots or []
    extraction_runs = job.extraction_runs or []
    latest_snap = snapshots[-1] if snapshots else None
    latest_extraction = extraction_runs[-1] if extraction_runs else None

    return JobDetailSchema(
        job_id=job.job_id,
        source_id=job.source_id,
        company=comp_name,
        company_domain=comp_domain,
        canonical_category=job.canonical_category,
        title=job.title,
        department=job.department,
        location=job.location,
        work_arrangement=job.work_arrangement,
        apply_url=job.apply_url,
        source_url=job.source_url,
        requisition_id=job.requisition_id,
        internal_job_id=job.internal_job_id,
        is_demo=job.is_demo,
        first_seen_at=job.first_seen_at,
        last_seen_at=job.last_seen_at,
        lifecycle_status=job.lifecycle_status,
        consecutive_missing_syncs=job.consecutive_missing_syncs,
        normalized_description=job.normalized_description,
        description_hash=job.description_hash,
        snapshots_count=len(snapshots) if snapshots else 1,
        latest_snapshot_observed_at=latest_snap.observed_at if latest_snap else job.last_seen_at,
        latest_extraction_signature=latest_extraction.extraction_signature if latest_extraction else job.description_hash,
        latest_extraction_method=latest_extraction.extraction_method if latest_extraction else "deterministic",
        latest_pipeline_version=latest_extraction.pipeline_version if latest_extraction else "1.0",
        skills=[
            SkillEvidenceSchema(
                skill_id=s.skill_id,
                requirement_type=s.requirement_type,
                evidence_text=s.evidence_text,
                extraction_method=s.extraction_method,
            )
            for s in active_skills
        ],
        experience_requirements=[
            ExperienceRequirementSchema(
                min_years=r.min_years,
                max_years=r.max_years,
                experience_scope=r.experience_scope,
                related_skill=r.related_skill,
                evidence_text=r.evidence_text,
            )
            for r in active_experience
        ],
        field_changes=[
            FieldChangeSchema(
                timestamp=c.timestamp,
                field_name=c.field_name,
                old_value=c.old_value,
                new_value=c.new_value,
            )
            for c in job.field_changes
        ],
    )

@router.get("/skills/top", response_model=TopSkillsResponse)
async def get_top_skills(
    category: Optional[str] = Query(None, description="Optional sector filter"),
    include_demo: bool = Query(False, description="Include demo fixtures"),
    session: AsyncSession = Depends(get_db_session),
):
    """Top demanded skills ranking."""
    engine = TelemetryEngine(session)
    telemetry = await engine.get_market_telemetry(category=category, include_demo=include_demo)
    
    top_items = [
        TopSkillItem(skill=item["skill_name"], job_count=item["job_count"])
        for item in telemetry["skills_telemetry"][:20]
    ]

    return TopSkillsResponse(
        total_jobs_analyzed=telemetry["total_eligible_jobs"],
        top_skills=top_items,
    )

@router.get("/telemetry/skills", response_model=TelemetryResponse)
async def get_skills_telemetry(
    category: Optional[str] = Query(None, description="Optional sector filter"),
    include_demo: bool = Query(False, description="Include demo fixtures"),
    session: AsyncSession = Depends(get_db_session),
):
    """Detailed market telemetry including skill share %, company breadth, and 30-day deltas."""
    engine = TelemetryEngine(session)
    return await engine.get_market_telemetry(category=category, include_demo=include_demo)

@router.get("/sources", response_model=List[SourceItemSchema])
async def list_sources(session: AsyncSession = Depends(get_db_session)):
    """Current status and telemetry of all registered ATS connectors."""
    stmt = select(Source).options(selectinload(Source.company))
    sources = (await session.execute(stmt)).scalars().all()

    return [
        SourceItemSchema(
            source_id=s.source_id,
            company_id=s.company_id,
            company_name=s.company.name if s.company else s.company_id,
            provider_type=s.provider_type,
            base_url=s.base_url,
            health_status=s.health_status,
            enabled=s.enabled,
            last_successful_sync=s.last_successful_sync,
            last_attempted_sync=s.last_attempted_sync,
            last_error=s.last_error,
        )
        for s in sources
    ]

@router.get("/sync/runs", response_model=List[SyncRunSchema])
async def list_sync_runs(limit: int = Query(20, ge=1, le=100), session: AsyncSession = Depends(get_db_session)):
    """Audit log of recent ingestion runs and safe reconciliation decisions."""
    stmt = select(SyncRun).order_by(desc(SyncRun.started_at)).limit(limit)
    runs = (await session.execute(stmt)).scalars().all()
    return runs

async def _run_sync_task(target_source_id: Optional[str] = None):
    """Background task executing connectors and safe reconciliation with per-source locking."""
    async with async_session_factory() as session:
        sources_stmt = select(Source).where(Source.enabled == True)
        if target_source_id:
            sources_stmt = sources_stmt.where(Source.source_id == target_source_id)
        sources = (await session.execute(sources_stmt)).scalars().all()

        for source in sources:
            source_lock = SOURCE_LOCKS.setdefault(source.source_id, asyncio.Lock())
            if source_lock.locked():
                continue

            async with source_lock:
                source_cfg = {
                    "source_id": source.source_id,
                    "company_id": source.company_id,
                    "provider_type": source.provider_type,
                    "base_url": source.base_url,
                    "board_token": source.board_token,
                    "endpoint": source.endpoint,
                    "allowed_hosts": source.allowed_hosts,
                    "timeout_seconds": source.timeout_seconds,
                    "concurrency_limit": source.concurrency_limit,
                }

                raw_jobs = []
                pagination_complete = False
                req_count = 0
                error_msg = None

                try:
                    raw_jobs, pagination_complete, req_count = await ConnectorManager.fetch_source_jobs(source_cfg)
                except Exception as e:
                    error_msg = str(e)
                    pagination_complete = False

                reconciler = SafeReconciliationEngine(session)
                await reconciler.execute_sync_run(
                    source=source,
                    raw_postings=raw_jobs,
                    pagination_complete=pagination_complete,
                    requests_count=req_count,
                    error_message=error_msg,
                )

@router.post("/sync")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    source_id: Optional[str] = Query(None, description="Optional specific source ID to sync"),
):
    """Triggers background ingest & safe reconciliation across enabled career portals."""
    if source_id:
        lock = SOURCE_LOCKS.setdefault(source_id, asyncio.Lock())
        if lock.locked():
            return {"status": "in_progress", "message": f"Sync for source '{source_id}' is already in progress."}
    elif SYNC_LOCK.locked():
        return {"status": "in_progress", "message": "A career sync run is already in progress."}

    background_tasks.add_task(_run_sync_task, target_source_id=source_id)
    return {"status": "triggered", "message": f"Background career sync dispatched{f' for {source_id}' if source_id else ''}."}

@router.get("/candidate/profile")
async def get_candidate_profile(session: AsyncSession = Depends(get_db_session)):
    """Retrieves current candidate profile and verified skills."""
    stmt = select(CandidateProfile).options(
        selectinload(CandidateProfile.skills).selectinload(CandidateSkillEvidence.skill)
    ).where(CandidateProfile.candidate_id == "default")

    cand = (await session.execute(stmt)).scalar_one_or_none()
    if not cand:
        cand = CandidateProfile(candidate_id="default", name="Unconfigured Profile", overall_yoe=None)
        session.add(cand)
        await session.commit()

    return {
        "candidate_id": cand.candidate_id,
        "name": cand.name,
        "overall_yoe": cand.overall_yoe,
        "skills": [
            {
                "skill_id": s.skill_id,
                "skill_name": s.skill.skill_name if s.skill else s.skill_id,
                "proficiency": s.proficiency,
                "evidence_level": s.evidence_level,
                "notes": s.notes,
            }
            for s in cand.skills
        ],
    }

@router.put("/candidate/profile")
async def update_candidate_profile(
    update_data: CandidateProfileUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """Updates candidate skills, evidence levels, and overall YOE."""
    cand = await session.get(CandidateProfile, "default", options=[selectinload(CandidateProfile.skills)])
    if not cand:
        cand = CandidateProfile(candidate_id="default")
        session.add(cand)

    cand.name = update_data.name
    cand.overall_yoe = update_data.overall_yoe

    # Clear existing skills and replace
    for old_s in cand.skills:
        await session.delete(old_s)

    for new_s in update_data.skills:
        cand.skills.append(CandidateSkillEvidence(
            candidate_id="default",
            skill_id=new_s.skill_id,
            proficiency=new_s.proficiency,
            evidence_level=new_s.evidence_level,
            notes=new_s.notes,
        ))

    await session.commit()
    return {"status": "updated", "candidate_id": "default"}

@router.get("/candidate/gap-analysis")
async def get_gap_analysis(
    target_category: Optional[str] = Query(None, description="Optional sector filter"),
    include_demo: bool = Query(False, description="Include demo fixtures"),
    session: AsyncSession = Depends(get_db_session),
):
    """Calculates coverage, prioritized missing technical skills, and 1-Skill Away opportunities."""
    analyzer = GapAnalyzerService(session)
    return await analyzer.analyze_candidate_gap(
        candidate_id="default",
        target_category=target_category,
        include_demo=include_demo,
    )
