import asyncio
import logging
import math
import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from datetime import datetime, timezone
from sqlalchemy import select, func, desc, asc, or_, and_, literal
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
    TaxonomySkill,
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
    CompanyItemSchema,
    SyncStatusSchema,
    TaxonomySkillSchema,
)
from backend.services.telemetry import TelemetryEngine
from backend.services.gap_analyzer import GapAnalyzerService
from backend.connectors.manager import ConnectorManager
from backend.services.reconciler import SafeReconciliationEngine
from backend.extraction.attributes import SENIORITY_LEVELS, UNSPECIFIED, PAY_BANDS, PAY_UNKNOWN
from backend.extraction.taxonomy import resolve_skill

logger = logging.getLogger("devradar.api")

router = APIRouter(prefix="/api")

# In-memory global sync lifecycle tracker
class GlobalSyncState:
    def __init__(self):
        self.is_active: bool = False
        self.current_run_id: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.status: str = "idle"  # idle | queued | running | completed | partial | failed
        self.current_source: Optional[str] = None
        self.total_sources: int = 0
        self.completed_sources: int = 0
        self.last_error: Optional[str] = None
        self.summary: dict = {}

GLOBAL_SYNC_STATE = GlobalSyncState()

# In-memory per-source sync locks to protect against concurrent overlapping sync triggers
SOURCE_LOCKS: dict[str, asyncio.Lock] = {}
SYNC_LOCK = asyncio.Lock()

@router.get("/health")
async def get_health(session: AsyncSession = Depends(get_db_session)):
    """Distinguishes internal application health from external ATS source health."""
    sources = (await session.execute(select(Source))).scalars().all()
    # Disabled sources (including companies with no public feed) are not live sync failures.
    degraded_sources = [s.source_id for s in sources if s.enabled and s.health_status != "HEALTHY"]

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
        netloc = urlparse(website_url if "//" in website_url else f"https://{website_url}").netloc.lower()
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
        "naughty dog": "naughtydog.com",
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

# Role-focus tracks match on track-specific skills or whole-word title/department keywords.
# General-purpose languages (C++, C) are deliberately absent from the specialized tracks so that
# every C++ posting is not counted as NPC AI, physics, and embedded at once.
ROLE_FOCUS_MAP = {
    # Granular Focus Tracks
    "ai npcs & game ai": {
        "skills": ["npc_ai", "game_ai", "behavior_trees", "fsm", "goap", "utility_ai", "pathfinding", "crowd_simulation", "reinforcement_learning", "agentic_ai", "eqs"],
        "keywords": ["npc", "npcs", "game ai", "gameplay ai", "ai programmer", "ai engineer", "behavior tree", "navmesh", "pathfinding", "agentic", "reinforcement learning", "massentity", "ai character", "ai characters", "fsm"]
    },
    "physics & simulation": {
        "skills": ["physics_engine", "collision_detection", "ragdoll_physics", "procedural_animation", "physics_middleware", "simd", "linear_algebra", "simulation_frameworks"],
        "keywords": ["physics", "simulation", "rigid body", "collision", "ragdoll", "kinematics", "physx", "havok", "chaos", "mujoco", "isaac sim", "omniverse", "dynamics"]
    },
    "gpu / cuda & silicon": {
        "skills": ["cuda", "rocm", "tensorrt", "triton", "opencl", "gpu_kernels", "parallel_computing", "verilog"],
        "keywords": ["cuda", "gpu", "gpus", "rocm", "tensorrt", "triton", "kernel", "kernels", "silicon", "accelerator", "asic", "fpga"]
    },
    "edge ai & embedded ece": {
        "skills": ["freertos", "device_drivers", "microcontrollers", "model_quantization", "rtos", "firmware"],
        "keywords": ["edge ai", "embedded", "rtos", "freertos", "zephyr", "qnx", "mcu", "microcontroller", "firmware", "driver", "drivers", "tinyml", "bsp"]
    },
    "ai servers & cloud": {
        "skills": ["distributed_systems", "rdma_networking", "sre", "linux_kernel", "docker", "kubernetes", "terraform", "ci_cd", "aws", "gcp"],
        "keywords": ["cloud", "distributed", "cluster", "rdma", "infiniband", "kubernetes", "docker", "infrastructure", "infra", "sre", "networking"]
    },
    # Backwards-compatible aliases
    "systems / c++": {
        "skills": ["cpp", "c", "linux_kernel", "multithreading", "distributed_systems", "os_concepts", "performance"],
        "keywords": ["system", "systems", "c++", "kernel", "runtime", "compiler", "performance", "low level"]
    },
    "ai & gpu / cuda": {
        "skills": ["cuda", "pytorch", "tensorrt", "triton", "llm", "deep_learning", "machine_learning", "computer_vision", "distributed_training"],
        "keywords": ["ai", "ml", "deep learning", "gpu", "cuda", "vision", "neural", "machine learning"]
    },
    "game engine / graphics": {
        "skills": ["unreal_engine", "unity", "vulkan", "directx", "opengl", "shaders", "rendering", "physics"],
        "keywords": ["graphics", "engine", "rendering", "game", "games", "gameplay", "vulkan", "unreal", "shader", "shaders", "animation", "audio"]
    },
    "cloud & devops": {
        "skills": ["docker", "kubernetes", "aws", "gcp", "ci_cd", "terraform", "linux", "cloud"],
        "keywords": ["cloud", "devops", "sre", "infrastructure", "platform", "reliability", "deployment", "pipeline"]
    },
    "embedded / firmware": {
        "skills": ["rtos", "firmware", "arm", "verilog", "fpga", "soc"],
        "keywords": ["embedded", "firmware", "rtos", "arm", "soc", "driver", "drivers", "bsp", "board", "hardware"]
    }
}

_WORD_SEPARATORS = [",", "/", "-", "(", ")", "|", ";", ":", ".", "&", "\n"]

def _normalize_term(term: str) -> str:
    out = term.lower()
    for ch in _WORD_SEPARATORS:
        out = out.replace(ch, " ")
    return " ".join(out.split())

def _word_match(column, term: str):
    """Case-insensitive whole-word match: 'ca' matches 'Santa Clara, CA' but not 'Canada'."""
    expr = func.lower(column)
    for ch in _WORD_SEPARATORS:
        expr = func.replace(expr, ch, " ")
    padded = literal(" ").concat(expr).concat(" ")
    return padded.like(f"% {_normalize_term(term)} %")

# Region presets list whole words; two-letter tokens are only state/country codes that are not English words.
LOCATION_PRESETS = {
    "uae": ["dubai", "abu dhabi", "uae", "united arab emirates", "middle east", "sharjah"],
    "us_eu": [
        "united states", "usa", "us", "america",
        "ca", "wa", "tx", "ny", "nc", "ma", "co", "il", "ga", "fl", "pa", "va", "ut", "az", "mn", "mi", "nj", "md", "dc",
        "california", "washington", "texas", "new york", "north carolina", "massachusetts",
        "santa clara", "austin", "cary", "seattle", "san francisco", "san mateo", "sunnyvale", "los angeles", "san diego", "santa monica",
        "united kingdom", "uk", "england", "scotland", "edinburgh", "london", "dundee", "lincoln", "leeds",
        "europe", "eu", "emea", "germany", "france", "serbia", "denmark", "sweden", "poland", "netherlands",
        "ireland", "spain", "italy", "finland", "norway", "switzerland", "austria", "belgium", "portugal",
        "czech republic", "czechia", "romania", "berlin", "munich", "paris", "stockholm", "copenhagen", "warsaw", "amsterdam",
    ],
    "india": ["india", "bengaluru", "bangalore", "pune", "hyderabad", "mumbai", "chennai", "noida", "gurgaon", "gurugram"],
}
LOCATION_PRESET_ALIASES = {
    "uae / me": "uae", "uae": "uae", "middle east": "uae", "me": "uae",
    "us / eu": "us_eu", "us": "us_eu", "eu": "us_eu", "usa": "us_eu", "europe": "us_eu",
    "india": "india",
}

def _csv(value: Optional[str]) -> List[str]:
    return [v.strip() for v in (value or "").split(",") if v.strip()]

def _resolve_role_focus(role: str) -> Optional[Dict[str, List[str]]]:
    cfg = ROLE_FOCUS_MAP.get(role)
    if cfg:
        return cfg
    norm_r = role.replace("&", "and").replace("/", " ")
    for k, v in ROLE_FOCUS_MAP.items():
        norm_k = k.replace("&", "and").replace("/", " ")
        if norm_r == norm_k or any(part in norm_k for part in norm_r.split() if len(part) > 2):
            return v
    return None

def _snapshot_bound_skill(*conditions):
    snapshot_match = or_(
        and_(Job.latest_snapshot_id.is_(None), JobSkillEvidence.snapshot_id.is_(None)),
        JobSkillEvidence.snapshot_id == Job.latest_snapshot_id,
    )
    return Job.skills.any(and_(snapshot_match, *conditions))

def build_job_filters(
    *,
    company: Optional[str] = None,
    location: Optional[str] = None,
    role_focus: Optional[str] = None,
    skill: Optional[str] = None,
    required_skill: Optional[str] = None,
    preferred_skill: Optional[str] = None,
    seniority: Optional[str] = None,
    pay_band: Optional[str] = None,
    yoe_min: Optional[int] = None,
    yoe_max: Optional[int] = None,
    include_unspecified_yoe: bool = True,
    lifecycle_status: Optional[str] = "ACTIVE",
    work_arrangement: Optional[str] = None,
    search: Optional[str] = None,
    include_demo: bool = False,
) -> list:
    """WHERE clauses shared by the job list, its count, and the sector counts (everything except sector)."""
    clauses = []

    if not include_demo:
        clauses.append(Job.is_demo == False)

    if lifecycle_status and lifecycle_status.upper() != "ALL":
        clauses.append(Job.lifecycle_status == lifecycle_status.upper())

    company_ids = _csv(company)
    if company_ids:
        clauses.append(Job.source_id.in_(select(Source.source_id).where(Source.company_id.in_(company_ids))))

    if location:
        loc_clean = location.strip().lower()
        preset = LOCATION_PRESET_ALIASES.get(loc_clean)
        if loc_clean in ("remote", "remote only"):
            clauses.append(or_(Job.work_arrangement == "remote", _word_match(Job.location, "remote")))
        elif preset:
            preset_clauses = [_word_match(Job.location, term) for term in LOCATION_PRESETS[preset]]
            if preset == "uae":
                preset_clauses.append(Job.canonical_category == "UAE & Middle East")
            clauses.append(or_(*preset_clauses))
        elif loc_clean not in ("global", "all"):
            clauses.append(Job.location.ilike(f"%{location.strip()}%"))

    if work_arrangement:
        clauses.append(Job.work_arrangement == work_arrangement.strip().lower())

    if search:
        search_term = f"%{search}%"
        clauses.append(
            (Job.title.ilike(search_term))
            | (Job.department.ilike(search_term))
            | (Job.normalized_description.ilike(search_term))
        )

    if role_focus:
        role_clauses = []
        for r in [x.lower() for x in _csv(role_focus)]:
            cfg = _resolve_role_focus(r)
            if not cfg:
                continue
            role_clauses.append(or_(
                _snapshot_bound_skill(JobSkillEvidence.skill_id.in_(cfg["skills"])),
                *[_word_match(Job.title, kw) for kw in cfg["keywords"]],
                *[_word_match(Job.department, kw) for kw in cfg["keywords"]],
            ))
        if role_clauses:
            clauses.append(or_(*role_clauses))

    # Skill filters bind strictly to current snapshot evidence
    if skill:
        clauses.append(_snapshot_bound_skill(JobSkillEvidence.skill_id.ilike(skill)))
    if required_skill:
        clauses.append(_snapshot_bound_skill(
            JobSkillEvidence.skill_id.ilike(required_skill),
            JobSkillEvidence.requirement_type == "required",
        ))
    if preferred_skill:
        clauses.append(_snapshot_bound_skill(
            JobSkillEvidence.skill_id.ilike(preferred_skill),
            JobSkillEvidence.requirement_type == "preferred",
        ))

    levels = [lv.lower() for lv in _csv(seniority)]
    if levels:
        unknown_levels = [lv for lv in levels if lv not in SENIORITY_LEVELS and lv != UNSPECIFIED]
        if unknown_levels:
            raise HTTPException(status_code=400, detail=f"Unknown seniority {unknown_levels}. Supported: {SENIORITY_LEVELS + [UNSPECIFIED]}")
        clauses.append(Job.seniority.in_(levels))

    bands = [b.lower() for b in _csv(pay_band)]
    if bands:
        band_clauses = []
        top_of_range = func.coalesce(Job.salary_max, Job.salary_min)
        for band in bands:
            if band == PAY_UNKNOWN:
                band_clauses.append(Job.salary_min.is_(None))
                continue
            if band not in PAY_BANDS:
                raise HTTPException(status_code=400, detail=f"Unknown pay_band '{band}'. Supported: {list(PAY_BANDS) + [PAY_UNKNOWN]}")
            lo, hi = PAY_BANDS[band]
            conds = [Job.salary_min.isnot(None)]
            if hi is not None:
                conds.append(Job.salary_min < hi)
            if lo is not None:
                conds.append(top_of_range >= lo)
            band_clauses.append(and_(*conds))
        clauses.append(or_(*band_clauses))

    # Years range uses the stored governing_min_years(); unspecified roles stay unless excluded.
    if yoe_min is not None or yoe_max is not None:
        in_range = [Job.required_yoe.isnot(None)]
        if yoe_min is not None:
            in_range.append(Job.required_yoe >= yoe_min)
        if yoe_max is not None:
            in_range.append(Job.required_yoe <= yoe_max)
        range_clause = and_(*in_range)
        clauses.append(or_(range_clause, Job.required_yoe.is_(None)) if include_unspecified_yoe else range_clause)
    elif not include_unspecified_yoe:
        clauses.append(Job.required_yoe.isnot(None))

    return clauses

@router.get("/companies", response_model=List[CompanyItemSchema])
async def list_companies(
    include_demo: bool = Query(False, description="Include demo company job counts"),
    session: AsyncSession = Depends(get_db_session)
):
    """Returns dynamic registry of known companies with live active job counts."""
    companies_stmt = select(Company).options(selectinload(Company.sources)).order_by(Company.name.asc())
    companies = (await session.execute(companies_stmt)).scalars().all()

    job_counts_stmt = (
        select(Source.company_id, func.count(Job.job_id))
        .join(Job, Job.source_id == Source.source_id)
        .where(Job.lifecycle_status == LifecycleStatus.ACTIVE.value)
    )
    if not include_demo:
        job_counts_stmt = job_counts_stmt.where(Job.is_demo == False)
    job_counts_stmt = job_counts_stmt.group_by(Source.company_id)

    counts_res = (await session.execute(job_counts_stmt)).all()
    counts_map = {row[0]: row[1] for row in counts_res}

    def company_feed_status(c: Company) -> str:
        statuses = {ConnectorManager.feed_status(s.provider_type, s.enabled) for s in c.sources}
        for status in ("live", "no_public_feed", "disabled"):
            if status in statuses:
                return status
        return "disabled"

    results = [
        CompanyItemSchema(
            company_id=c.company_id,
            name=c.name,
            canonical_category=c.canonical_category,
            website_url=c.website_url,
            domain=extract_domain(c.website_url, c.name),
            feed_status=company_feed_status(c),
            active_jobs_count=counts_map.get(c.company_id, 0),
        )
        for c in companies
    ]
    results.sort(key=lambda x: (-x.active_jobs_count, x.name))
    return results

SUPPORTED_SORT_OPTIONS = {
    "newest_discovered",
    "recently_posted",
    "company_asc",
    "company_desc",
    "title_asc",
    "title_desc",
    "location_asc",
    "recently_updated",
}

@router.get("/jobs", response_model=JobsResponse)
async def list_jobs(
    company: Optional[str] = Query(None, description="Comma-separated exact company_ids, e.g. 'nvidia,epicgames'"),
    sort_by: str = Query("newest_discovered", description="Sort order: newest_discovered | recently_posted | company_asc | company_desc | title_asc | title_desc | location_asc | recently_updated"),
    category: Optional[str] = Query(None, description="Silicon & AI | Game Studio | UAE & Middle East"),
    location: Optional[str] = Query(None, description="City, country, or region preset (UAE / ME, US / EU, India, Remote Only)"),
    role_focus: Optional[str] = Query(None, description="Comma-separated role focuses e.g. 'AI NPCs & Game AI,Physics & Simulation'"),
    skill: Optional[str] = Query(None, description="Any matching skill name or ID"),
    required_skill: Optional[str] = Query(None, description="Skill strictly required"),
    preferred_skill: Optional[str] = Query(None, description="Skill preferred"),
    seniority: Optional[str] = Query(None, description="Comma-separated: intern, associate, mid, senior, staff, principal, unspecified"),
    pay_band: Optional[str] = Query(None, description="Comma-separated: under_100k, 100_150k, 150_200k, 200k_plus, unknown"),
    yoe_min: Optional[int] = Query(None, ge=0, description="Roles whose required years are >= yoe_min"),
    yoe_max: Optional[int] = Query(None, ge=0, description="Roles whose required years are <= yoe_max"),
    include_unspecified_yoe: bool = Query(True, description="Keep roles with no stated years requirement when a years range is set"),
    max_required_yoe: Optional[int] = Query(None, description="Deprecated alias for yoe_max"),
    min_yoe: Optional[int] = Query(None, description="Deprecated alias for yoe_max"),
    lifecycle_status: Optional[str] = Query("ACTIVE", description="ACTIVE | MISSING_CANDIDATE | CLOSED | ALL"),
    work_arrangement: Optional[str] = Query(None, description="remote | hybrid | onsite | unknown"),
    search: Optional[str] = Query(None, description="Text search title, department, description"),
    include_demo: bool = Query(False, description="Include demo fixtures"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
):
    """Paginated, multi-attribute filtered engineering job list with backend-driven sorting."""
    if sort_by not in SUPPORTED_SORT_OPTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid sort_by '{sort_by}'. Supported options: {sorted(list(SUPPORTED_SORT_OPTIONS))}"
        )

    effective_yoe_max = yoe_max if yoe_max is not None else (max_required_yoe if max_required_yoe is not None else min_yoe)
    shared_clauses = build_job_filters(
        company=company,
        location=location,
        role_focus=role_focus,
        skill=skill,
        required_skill=required_skill,
        preferred_skill=preferred_skill,
        seniority=seniority,
        pay_band=pay_band,
        yoe_min=yoe_min,
        yoe_max=effective_yoe_max,
        include_unspecified_yoe=include_unspecified_yoe,
        lifecycle_status=lifecycle_status,
        work_arrangement=work_arrangement,
        search=search,
        include_demo=include_demo,
    )
    list_clauses = list(shared_clauses)
    if category:
        list_clauses.append(Job.canonical_category.ilike(f"%{category}%"))

    total_count = (await session.execute(
        select(func.count(Job.job_id)).where(*list_clauses)
    )).scalar() or 0
    total_pages = max(1, math.ceil(total_count / page_size))

    # Sector counts apply every filter except the sector itself
    sector_stmt = (
        select(Job.canonical_category, func.count(Job.job_id))
        .where(*shared_clauses)
        .group_by(Job.canonical_category)
    )
    sector_counts_raw = (await session.execute(sector_stmt)).all()
    sector_counts = {row[0]: row[1] for row in sector_counts_raw if row[0]}
    sector_counts["All Sectors"] = sum(sector_counts.values())

    stmt = select(Job).options(
        selectinload(Job.skills),
        selectinload(Job.source).selectinload(Source.company),
    ).where(*list_clauses)

    if sort_by in ("company_asc", "company_desc"):
        stmt = stmt.outerjoin(Job.source).outerjoin(Source.company)

    if sort_by == "newest_discovered":
        stmt = stmt.order_by(desc(Job.first_seen_at), desc(Job.job_id))
    elif sort_by == "recently_posted":
        stmt = stmt.order_by(Job.source_created_at.desc().nullslast(), desc(Job.first_seen_at), desc(Job.job_id))
    elif sort_by == "company_asc":
        stmt = stmt.order_by(asc(Company.name), desc(Job.first_seen_at), desc(Job.job_id))
    elif sort_by == "company_desc":
        stmt = stmt.order_by(desc(Company.name), desc(Job.first_seen_at), desc(Job.job_id))
    elif sort_by == "title_asc":
        stmt = stmt.order_by(asc(Job.title), desc(Job.job_id))
    elif sort_by == "title_desc":
        stmt = stmt.order_by(desc(Job.title), desc(Job.job_id))
    elif sort_by == "location_asc":
        stmt = stmt.order_by(asc(Job.location), desc(Job.job_id))
    elif sort_by == "recently_updated":
        stmt = stmt.order_by(
            Job.source_updated_at.desc().nullslast(),
            Job.source_created_at.desc().nullslast(),
            desc(Job.job_id),
        )

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    job_rows = (await session.execute(stmt)).scalars().all()

    items = []
    for j in job_rows:
        company_obj = j.source.company if j.source else None
        comp_name = company_obj.name if company_obj else j.source_id
        comp_domain = extract_domain(company_obj.website_url if company_obj else None, comp_name)
        active_skills = j.latest_skills
        req_skills = [s.skill_id for s in active_skills if s.requirement_type == "required"]
        pref_skills = [s.skill_id for s in active_skills if s.requirement_type == "preferred"]

        items.append(JobListItemSchema(
            job_id=j.job_id,
            company=comp_name,
            company_id=j.source.company_id if j.source else None,
            company_domain=comp_domain,
            canonical_category=j.canonical_category,
            title=j.title,
            department=j.department,
            location=j.location,
            work_arrangement=j.work_arrangement,
            seniority=j.seniority or UNSPECIFIED,
            apply_url=j.apply_url,
            requisition_id=j.requisition_id,
            internal_job_id=j.internal_job_id,
            is_demo=j.is_demo,
            first_seen_at=j.first_seen_at,
            last_seen_at=j.last_seen_at,
            source_created_at=j.source_created_at,
            source_updated_at=j.source_updated_at,
            lifecycle_status=j.lifecycle_status,
            primary_min_yoe=j.required_yoe,
            salary_min=j.salary_min,
            salary_max=j.salary_max,
            salary_currency=j.salary_currency,
            required_skills=req_skills,
            preferred_skills=pref_skills,
        ))

    return JobsResponse(
        total_count=total_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
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
        seniority=job.seniority or UNSPECIFIED,
        apply_url=job.apply_url,
        source_url=job.source_url,
        requisition_id=job.requisition_id,
        internal_job_id=job.internal_job_id,
        is_demo=job.is_demo,
        first_seen_at=job.first_seen_at,
        last_seen_at=job.last_seen_at,
        source_created_at=job.source_created_at,
        source_updated_at=job.source_updated_at,
        lifecycle_status=job.lifecycle_status,
        primary_min_yoe=job.required_yoe,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
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

@router.get("/skills/taxonomy", response_model=List[TaxonomySkillSchema])
async def list_taxonomy_skills(session: AsyncSession = Depends(get_db_session)):
    """Every skill id the extractor and the candidate profile understand."""
    skills = (await session.execute(select(TaxonomySkill).order_by(TaxonomySkill.skill_name))).scalars().all()
    return [TaxonomySkillSchema(skill_id=s.skill_id, skill_name=s.skill_name, category=s.category) for s in skills]

@router.get("/skills/resolve", response_model=TaxonomySkillSchema)
async def resolve_skill_text(
    q: str = Query(..., min_length=1, description="Free-typed skill, e.g. 'C++' or 'c#'"),
    session: AsyncSession = Depends(get_db_session),
):
    """Maps typed skill text to a taxonomy id (C++ -> cpp, C# -> csharp). 404 for unknown skills."""
    spec = resolve_skill(q)
    row = await session.get(TaxonomySkill, spec["skill_id"]) if spec else None
    if row is None:
        raise HTTPException(status_code=404, detail=f"'{q}' is not a known skill in the taxonomy")
    return TaxonomySkillSchema(skill_id=row.skill_id, skill_name=row.skill_name, category=row.category)

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
            feed_status=ConnectorManager.feed_status(s.provider_type, s.enabled),
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

@router.get("/sync/status", response_model=SyncStatusSchema)
async def get_sync_status():
    """Real-time observability into ongoing career synchronization lifecycle."""
    return SyncStatusSchema(
        is_active=GLOBAL_SYNC_STATE.is_active,
        current_run_id=GLOBAL_SYNC_STATE.current_run_id,
        status=GLOBAL_SYNC_STATE.status,
        current_source=GLOBAL_SYNC_STATE.current_source,
        total_sources=GLOBAL_SYNC_STATE.total_sources,
        completed_sources=GLOBAL_SYNC_STATE.completed_sources,
        started_at=GLOBAL_SYNC_STATE.started_at,
        completed_at=GLOBAL_SYNC_STATE.completed_at,
        last_error=GLOBAL_SYNC_STATE.last_error,
        summary=GLOBAL_SYNC_STATE.summary,
    )

def _owns_sync_state(run_id: str) -> bool:
    """A run only reports into the shared state while it is the most recently dispatched run."""
    return GLOBAL_SYNC_STATE.current_run_id == run_id

async def _sync_source(session: AsyncSession, source_id: str, run_id: str, summary_stats: dict) -> bool:
    """Fetches and reconciles one source. Returns False when the connector or reconciliation failed."""
    source = await session.get(Source, source_id)
    if source is None:
        return False
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

    raw_jobs: list = []
    pagination_complete = False
    req_count = 0
    error_msg = None
    try:
        raw_jobs, pagination_complete, req_count = await ConnectorManager.fetch_source_jobs(source_cfg)
    except Exception as e:
        error_msg = str(e) or e.__class__.__name__
        pagination_complete = False

    try:
        reconciler = SafeReconciliationEngine(session)
        sync_run = await reconciler.execute_sync_run(
            source=source,
            raw_postings=raw_jobs,
            pagination_complete=pagination_complete,
            requests_count=req_count,
            error_message=error_msg,
        )
    except Exception as e:
        await session.rollback()
        logger.exception(f"Reconciliation failed for {source_id}")
        error_msg = f"Reconciliation failed for {source_id}: {e}"
        sync_run = None

    if error_msg and _owns_sync_state(run_id):
        GLOBAL_SYNC_STATE.last_error = error_msg
    if sync_run is not None:
        summary_stats["jobs_discovered"] += sync_run.jobs_discovered
        summary_stats["jobs_created"] += sync_run.jobs_created
        summary_stats["jobs_updated"] += sync_run.jobs_updated
        summary_stats["jobs_rejected"] += sync_run.jobs_rejected
    return error_msg is None

async def _run_sync_task(run_id: str, target_source_id: Optional[str] = None, held_lock: Optional[asyncio.Lock] = None):
    """
    Background task executing connectors and safe reconciliation.
    `held_lock` was acquired by the request handler (SYNC_LOCK for a full sync, the source lock
    for a single-source sync) and is always released here, whatever fails.
    """
    has_errors = False
    summary_stats = {"jobs_discovered": 0, "jobs_created": 0, "jobs_updated": 0, "jobs_rejected": 0}
    try:
        if _owns_sync_state(run_id):
            GLOBAL_SYNC_STATE.is_active = True
            GLOBAL_SYNC_STATE.status = "running"

        async with async_session_factory() as session:
            sources_stmt = select(Source.source_id).where(Source.enabled == True)
            if target_source_id:
                sources_stmt = sources_stmt.where(Source.source_id == target_source_id)
            source_ids = list((await session.execute(sources_stmt)).scalars().all())
            if _owns_sync_state(run_id):
                GLOBAL_SYNC_STATE.total_sources = len(source_ids)

            for source_id in source_ids:
                if _owns_sync_state(run_id):
                    GLOBAL_SYNC_STATE.current_source = source_id
                if target_source_id:
                    ok = await _sync_source(session, source_id, run_id, summary_stats)
                else:
                    # Waits for any single-source sync of the same board to finish first.
                    async with SOURCE_LOCKS.setdefault(source_id, asyncio.Lock()):
                        ok = await _sync_source(session, source_id, run_id, summary_stats)
                has_errors = has_errors or not ok
                if _owns_sync_state(run_id):
                    GLOBAL_SYNC_STATE.completed_sources += 1

        if _owns_sync_state(run_id):
            GLOBAL_SYNC_STATE.status = "partial" if has_errors else "completed"
            GLOBAL_SYNC_STATE.summary = summary_stats
    except Exception as e:
        logger.exception(f"Sync run {run_id} failed")
        if _owns_sync_state(run_id):
            GLOBAL_SYNC_STATE.status = "failed"
            GLOBAL_SYNC_STATE.last_error = str(e) or e.__class__.__name__
    finally:
        if _owns_sync_state(run_id):
            GLOBAL_SYNC_STATE.is_active = False
            GLOBAL_SYNC_STATE.current_source = None
            GLOBAL_SYNC_STATE.completed_at = datetime.now(timezone.utc)
        if held_lock is not None and held_lock.locked():
            held_lock.release()

@router.post("/sync")
async def trigger_sync(
    background_tasks: BackgroundTasks,
    source_id: Optional[str] = Query(None, description="Optional specific source ID to sync"),
    session: AsyncSession = Depends(get_db_session),
):
    """Triggers background ingest & safe reconciliation across enabled career portals."""
    if source_id:
        source = await session.get(Source, source_id)
        if source is None:
            raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
        if not source.enabled:
            feed = ConnectorManager.feed_status(source.provider_type, source.enabled)
            reason = "has no public job feed" if feed == "no_public_feed" else "is disabled"
            return {"status": "skipped", "run_id": None, "message": f"Source '{source_id}' {reason}."}
        if SYNC_LOCK.locked():
            return {"status": "in_progress", "run_id": GLOBAL_SYNC_STATE.current_run_id, "message": "A full career sync is already in progress and includes this source."}
        held_lock = SOURCE_LOCKS.setdefault(source_id, asyncio.Lock())
        if held_lock.locked():
            return {"status": "in_progress", "run_id": GLOBAL_SYNC_STATE.current_run_id, "message": f"Sync for source '{source_id}' is already in progress."}
    else:
        held_lock = SYNC_LOCK
        if held_lock.locked():
            return {"status": "in_progress", "run_id": GLOBAL_SYNC_STATE.current_run_id, "message": "A career sync run is already in progress."}

    await held_lock.acquire()
    try:
        run_id = str(uuid.uuid4())
        GLOBAL_SYNC_STATE.is_active = True
        GLOBAL_SYNC_STATE.current_run_id = run_id
        GLOBAL_SYNC_STATE.status = "queued"
        GLOBAL_SYNC_STATE.started_at = datetime.now(timezone.utc)
        GLOBAL_SYNC_STATE.completed_at = None
        GLOBAL_SYNC_STATE.current_source = None
        GLOBAL_SYNC_STATE.total_sources = 0
        GLOBAL_SYNC_STATE.completed_sources = 0
        GLOBAL_SYNC_STATE.last_error = None
        GLOBAL_SYNC_STATE.summary = {}
        background_tasks.add_task(_run_sync_task, run_id=run_id, target_source_id=source_id, held_lock=held_lock)
    except Exception:
        held_lock.release()
        raise
    return {
        "status": "triggered",
        "run_id": run_id,
        "message": f"Background career sync dispatched{f' for {source_id}' if source_id else ''}."
    }

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
    """Updates candidate skills, evidence levels, and (only when sent) overall YOE."""
    known_skill_ids = set((await session.execute(select(TaxonomySkill.skill_id))).scalars().all())
    unknown = sorted({s.skill_id for s in update_data.skills if s.skill_id not in known_skill_ids})
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown skill ids (not in taxonomy): {unknown}")

    cand = await session.get(CandidateProfile, "default", options=[selectinload(CandidateProfile.skills)])
    if not cand:
        cand = CandidateProfile(candidate_id="default")
        session.add(cand)

    cand.name = update_data.name
    if "overall_yoe" in update_data.model_fields_set:
        cand.overall_yoe = update_data.overall_yoe

    # Clear existing skills and replace
    for old_s in cand.skills:
        await session.delete(old_s)

    seen_ids = set()
    for new_s in update_data.skills:
        if new_s.skill_id in seen_ids:
            continue
        seen_ids.add(new_s.skill_id)
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
