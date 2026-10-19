import os
import json
import logging
from typing import AsyncGenerator
from sqlalchemy import text, select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.db.models import Base, Company, Source, Job, TaxonomySkill, CandidateProfile
from backend.extraction.attributes import parse_seniority, parse_work_arrangement, parse_salary
from backend.extraction.experience import governing_min_years

logger = logging.getLogger("devradar.db")

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./devradar.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()

# Default Seed Registry (Tier-1 Target Employers)
DEFAULT_COMPANIES = [
    {
        "company_id": "nvidia",
        "name": "NVIDIA",
        "canonical_category": "Silicon & AI",
        "website_url": "https://www.nvidia.com",
        "source": {
            "source_id": "nvidia_workday",
            "provider_type": "workday",
            "base_url": "https://nvidia.wd5.myworkdayjobs.com",
            "endpoint": "/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs",
            "allowed_hosts": json.dumps(["nvidia.wd5.myworkdayjobs.com"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 20.0,
            "concurrency_limit": 2,
        }
    },
    {
        "company_id": "epicgames",
        "name": "Epic Games",
        "canonical_category": "Game Studio",
        "website_url": "https://www.epicgames.com",
        "source": {
            "source_id": "epic_greenhouse",
            "provider_type": "greenhouse",
            "base_url": "https://boards-api.greenhouse.io",
            "board_token": "epicgames",
            "allowed_hosts": json.dumps(["boards-api.greenhouse.io", "boards.greenhouse.io"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 3,
        }
    },
    {
        "company_id": "rockstar",
        "name": "Rockstar Games",
        "canonical_category": "Game Studio",
        "website_url": "https://www.rockstargames.com",
        "source": {
            "source_id": "rockstar_greenhouse",
            "provider_type": "greenhouse",
            "base_url": "https://boards-api.greenhouse.io",
            "board_token": "rockstargames",
            "allowed_hosts": json.dumps(["boards-api.greenhouse.io", "boards.greenhouse.io"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 3,
        }
    },
    {
        "company_id": "ea",
        "name": "Electronic Arts",
        "canonical_category": "Game Studio",
        "website_url": "https://www.ea.com",
        "source": {
            # EA's careers site is GR8 People. An unauthenticated GET to ea.gr8people.com/jobs
            # returns CloudFront 403 ("Request forbidden by administrative rules"), so there is no public feed.
            "source_id": "ea_gr8people",
            "provider_type": "gr8people",
            "base_url": "https://ea.gr8people.com",
            "allowed_hosts": json.dumps(["ea.gr8people.com"]),
            "enabled": False,
            "polling_interval_minutes": 120,
            "timeout_seconds": 15.0,
            "concurrency_limit": 1,
        }
    },
    {
        "company_id": "careem",
        "name": "Careem",
        "canonical_category": "UAE & Middle East",
        "website_url": "https://www.careem.com",
        "source": {
            "source_id": "careem_greenhouse",
            "provider_type": "greenhouse",
            "base_url": "https://boards-api.greenhouse.io",
            "board_token": "careem",
            "allowed_hosts": json.dumps(["boards-api.greenhouse.io", "boards.greenhouse.io"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 3,
        }
    },
    {
        "company_id": "roblox",
        "name": "Roblox",
        "canonical_category": "Game Studio",
        "website_url": "https://www.roblox.com",
        "source": {
            "source_id": "roblox_greenhouse",
            "provider_type": "greenhouse",
            "base_url": "https://boards-api.greenhouse.io",
            "board_token": "roblox",
            "allowed_hosts": json.dumps(["boards-api.greenhouse.io", "boards.greenhouse.io"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 3,
        }
    },
    {
        "company_id": "playstation",
        "name": "PlayStation Studios",
        "canonical_category": "Game Studio",
        "website_url": "https://www.playstation.com",
        "source": {
            "source_id": "playstation_greenhouse",
            "provider_type": "greenhouse",
            "base_url": "https://boards-api.greenhouse.io",
            "board_token": "sonyinteractiveentertainmentglobal",
            "allowed_hosts": json.dumps(["boards-api.greenhouse.io", "boards.greenhouse.io"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 3,
        }
    },
    {
        "company_id": "naughtydog",
        "name": "Naughty Dog",
        "canonical_category": "Game Studio",
        "website_url": "https://www.naughtydog.com",
        "source": {
            "source_id": "naughtydog_greenhouse",
            "provider_type": "greenhouse",
            "base_url": "https://boards-api.greenhouse.io",
            "board_token": "naughtydog",
            "allowed_hosts": json.dumps(["boards-api.greenhouse.io", "boards.greenhouse.io"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 3,
        }
    },
    {
        "company_id": "cerebras",
        "name": "Cerebras Systems",
        "canonical_category": "Silicon & AI",
        "website_url": "https://www.cerebras.net",
        "source": {
            "source_id": "cerebras_ashby",
            "provider_type": "ashby",
            "base_url": "https://api.ashbyhq.com",
            "board_token": "cerebras",
            "allowed_hosts": json.dumps(["api.ashbyhq.com", "jobs.ashbyhq.com"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 2,
        }
    },
    {
        "company_id": "canonical",
        "name": "Canonical / Ubuntu",
        "canonical_category": "Silicon & AI",
        "website_url": "https://canonical.com",
        "source": {
            "source_id": "canonical_greenhouse",
            "provider_type": "greenhouse",
            "base_url": "https://boards-api.greenhouse.io",
            "board_token": "canonical",
            "allowed_hosts": json.dumps(["boards-api.greenhouse.io", "boards.greenhouse.io"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 3,
        }
    },
    {
        "company_id": "arista",
        "name": "Arista Networks",
        "canonical_category": "Silicon & AI",
        "website_url": "https://www.arista.com",
        "source": {
            "source_id": "arista_smartrecruiters",
            "provider_type": "smartrecruiters",
            "base_url": "https://api.smartrecruiters.com",
            "board_token": "AristaNetworks",
            "allowed_hosts": json.dumps(["api.smartrecruiters.com", "jobs.smartrecruiters.com"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 2,
        }
    },
    {
        "company_id": "weride",
        "name": "WeRide UAE",
        "canonical_category": "UAE & Middle East",
        "website_url": "https://www.weride.ai",
        "source": {
            "source_id": "weride_lever",
            "provider_type": "lever",
            "base_url": "https://api.lever.co",
            "board_token": "weride",
            "allowed_hosts": json.dumps(["api.lever.co", "jobs.lever.co"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 2,
        }
    },
    {
        "company_id": "qualcomm",
        "name": "Qualcomm",
        "canonical_category": "Silicon & AI",
        "website_url": "https://www.qualcomm.com",
        "source": {
            "source_id": "qualcomm_eightfold",
            "provider_type": "eightfold",
            "base_url": "https://careers.qualcomm.com",
            "allowed_hosts": json.dumps(["careers.qualcomm.com"]),
            "enabled": False,
            "polling_interval_minutes": 120,
            "timeout_seconds": 15.0,
            "concurrency_limit": 1,
        }
    },
    {
        "company_id": "g42",
        "name": "G42",
        "canonical_category": "UAE & Middle East",
        "website_url": "https://www.g42.ai",
        "source": {
            "source_id": "g42_phenom",
            "provider_type": "phenom",
            "base_url": "https://careers.g42.ai",
            "allowed_hosts": json.dumps(["careers.g42.ai"]),
            "enabled": False,
            "polling_interval_minutes": 120,
            "timeout_seconds": 15.0,
            "concurrency_limit": 1,
        }
    }
]

# Standard Taxonomy Skills Seed List
DEFAULT_TAXONOMY_SKILLS = [
    # Languages
    ("cpp", "C++", "Languages"),
    ("c", "C", "Languages"),
    ("python", "Python", "Languages"),
    ("rust", "Rust", "Languages"),
    ("go", "Go", "Languages"),
    ("csharp", "C#", "Languages"),
    ("typescript", "TypeScript", "Languages"),
    ("sql", "SQL", "Languages"),
    
    # GPU / Silicon / Embedded
    ("cuda", "CUDA", "GPU / Silicon"),
    ("tensorrt", "TensorRT", "GPU / Silicon"),
    ("triton", "Triton", "GPU / Silicon"),
    ("rtos", "RTOS", "Embedded & Systems"),
    ("firmware", "Firmware", "Embedded & Systems"),
    ("linux_kernel", "Linux Kernel", "Embedded & Systems"),
    ("arm", "ARM Architecture", "Embedded & Systems"),
    ("verilog", "Verilog/VHDL", "GPU / Silicon"),
    
    # Graphics & Game Engines
    ("unreal_engine", "Unreal Engine", "Graphics & Games"),
    ("unity", "Unity", "Graphics & Games"),
    ("vulkan", "Vulkan", "Graphics & Games"),
    ("directx", "DirectX / D3D12", "Graphics & Games"),
    ("opengl", "OpenGL", "Graphics & Games"),
    ("shaders", "HLSL / GLSL Shaders", "Graphics & Games"),
    
    # AI / ML
    ("pytorch", "PyTorch", "AI / ML"),
    ("tensorflow", "TensorFlow", "AI / ML"),
    ("jax", "JAX", "AI / ML"),
    ("llm", "LLMs / Transformers", "AI / ML"),
    ("distributed_training", "Distributed Training", "AI / ML"),
    
    # Cloud & DevOps / Infra
    ("docker", "Docker", "Deployment & Cloud"),
    ("kubernetes", "Kubernetes", "Deployment & Cloud"),
    ("aws", "AWS", "Deployment & Cloud"),
    ("gcp", "Google Cloud", "Deployment & Cloud"),
    ("ci_cd", "CI/CD", "Deployment & Cloud"),
    ("terraform", "Terraform", "Deployment & Cloud"),
    
    # AI NPC & Game AI
    ("npc_ai", "NPC AI / Game AI", "AI & Game AI"),
    ("behavior_trees", "Behavior Trees", "AI & Game AI"),
    ("fsm", "Finite State Machines (FSM)", "AI & Game AI"),
    ("goap", "GOAP", "AI & Game AI"),
    ("utility_ai", "Utility AI", "AI & Game AI"),
    ("pathfinding", "Pathfinding / NavMesh", "AI & Game AI"),
    ("crowd_simulation", "Crowd Simulation", "AI & Game AI"),
    ("reinforcement_learning", "Reinforcement Learning (RL)", "AI & Game AI"),
    ("agentic_ai", "Agentic AI / SLMs", "AI & Game AI"),
    ("eqs", "Environment Query System (EQS)", "AI & Game AI"),

    # Physics & Simulation
    ("physics_engine", "Physics Engine & Dynamics", "Physics & Simulation"),
    ("collision_detection", "Collision Detection", "Physics & Simulation"),
    ("ragdoll_physics", "Ragdoll & IK", "Physics & Simulation"),
    ("procedural_animation", "Procedural Animation", "Physics & Simulation"),
    ("physics_middleware", "Havok / PhysX / Chaos", "Physics & Simulation"),
    ("simd", "SIMD / Vector Math", "Physics & Simulation"),
    ("linear_algebra", "Linear Algebra & 3D Math", "Physics & Simulation"),
    ("simulation_frameworks", "MuJoCo / Isaac Sim / Omniverse", "Physics & Simulation"),

    # GPU / Accelerators / Silicon
    ("rocm", "ROCm / HIP", "GPU / Silicon"),
    ("opencl", "OpenCL", "GPU / Silicon"),
    ("gpu_kernels", "GPU Kernels & Optimization", "GPU / Silicon"),
    ("parallel_computing", "Parallel Computing", "GPU / Silicon"),

    # Edge AI & Embedded ECE
    ("freertos", "FreeRTOS / Zephyr / QNX", "Embedded & Systems"),
    ("device_drivers", "Device Drivers & BSP", "Embedded & Systems"),
    ("microcontrollers", "Microcontrollers & Protocols", "Embedded & Systems"),
    ("model_quantization", "Model Quantization & ONNX", "Embedded & Systems"),

    # AI Servers & Cloud Infra
    ("distributed_systems", "Distributed Systems", "Deployment & Cloud"),
    ("rdma_networking", "RDMA & High-Speed Networking", "Deployment & Cloud"),
    ("sre", "SRE & Reliability", "Deployment & Cloud"),
]

# Source ids that were replaced by a differently-named source for the same company.
RETIRED_SOURCE_IDS = {"ea_greenhouse"}

DERIVED_JOB_COLUMNS = {
    "seniority": "VARCHAR(32) DEFAULT 'unspecified' NOT NULL",
    "required_yoe": "INTEGER",
    "salary_min": "FLOAT",
    "salary_max": "FLOAT",
    "salary_currency": "VARCHAR(8)",
}

async def _migrate_sqlite_schema(conn) -> bool:
    """
    Safely adds missing columns to existing SQLite database tables.
    Returns True when derived job columns were just added and need a backfill.
    """
    needs_backfill = False
    try:
        # 1. Check jobs table
        res = await conn.execute(text("PRAGMA table_info(jobs)"))
        job_cols = [row[1] for row in res.fetchall()]
        if job_cols:
            if "internal_job_id" not in job_cols:
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN internal_job_id VARCHAR(128)"))
            if "is_demo" not in job_cols:
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN is_demo BOOLEAN DEFAULT 0 NOT NULL"))
            if "latest_snapshot_id" not in job_cols:
                await conn.execute(text("ALTER TABLE jobs ADD COLUMN latest_snapshot_id INTEGER"))
            for col_name, col_ddl in DERIVED_JOB_COLUMNS.items():
                if col_name not in job_cols:
                    await conn.execute(text(f"ALTER TABLE jobs ADD COLUMN {col_name} {col_ddl}"))
                    needs_backfill = True

        # 2. Check job_skill_evidence table
        res = await conn.execute(text("PRAGMA table_info(job_skill_evidence)"))
        skill_cols = [row[1] for row in res.fetchall()]
        if skill_cols:
            if "snapshot_id" not in skill_cols:
                await conn.execute(text("ALTER TABLE job_skill_evidence ADD COLUMN snapshot_id INTEGER"))
            if "extraction_run_id" not in skill_cols:
                await conn.execute(text("ALTER TABLE job_skill_evidence ADD COLUMN extraction_run_id VARCHAR(64)"))

        # 3. Check job_experience_requirements table
        res = await conn.execute(text("PRAGMA table_info(job_experience_requirements)"))
        exp_cols = [row[1] for row in res.fetchall()]
        if exp_cols:
            if "snapshot_id" not in exp_cols:
                await conn.execute(text("ALTER TABLE job_experience_requirements ADD COLUMN snapshot_id INTEGER"))
            if "extraction_run_id" not in exp_cols:
                await conn.execute(text("ALTER TABLE job_experience_requirements ADD COLUMN extraction_run_id VARCHAR(64)"))

        # 4. Check candidate_profile table (migrate overall_yoe from NOT NULL to NULL)
        res = await conn.execute(text("PRAGMA table_info(candidate_profile)"))
        cand_cols = res.fetchall()
        yoe_col = [row for row in cand_cols if row[1] == "overall_yoe"]
        if yoe_col and yoe_col[0][3] == 1:  # notnull is set to 1 in old schema
            await conn.execute(text("ALTER TABLE candidate_profile RENAME TO _candidate_profile_old"))
            await conn.execute(text("""
                CREATE TABLE candidate_profile (
                    candidate_id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(128) NOT NULL,
                    overall_yoe FLOAT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
            """))
            await conn.execute(text("""
                INSERT INTO candidate_profile (candidate_id, name, overall_yoe, created_at, updated_at)
                SELECT candidate_id, name, overall_yoe, created_at, updated_at FROM _candidate_profile_old
            """))
            await conn.execute(text("DROP TABLE _candidate_profile_old"))
    except Exception:
        # Ignore if tables do not exist yet
        pass
    return needs_backfill

async def _backfill_derived_job_fields(session: AsyncSession) -> None:
    """Fills seniority, years, arrangement, and pay for jobs ingested before those columns existed."""
    jobs = (await session.execute(
        select(Job).options(selectinload(Job.experience_requirements), selectinload(Job.snapshots))
    )).scalars().all()
    for job in jobs:
        job.seniority = parse_seniority(job.title)
        job.required_yoe = governing_min_years(job.latest_experience)
        if job.is_demo:
            if not job.work_arrangement or job.work_arrangement == "unknown":
                job.work_arrangement = parse_work_arrangement(None, job.location)
            continue
        # Live jobs used to be stored with a hardcoded "hybrid".
        job.work_arrangement = parse_work_arrangement(None, job.location)
        salary = parse_salary(job.normalized_description)
        job.salary_min = salary["salary_min"]
        job.salary_max = salary["salary_max"]
        job.salary_currency = salary["salary_currency"]
    logger.info(f"Backfilled derived fields for {len(jobs)} jobs")

async def _retire_sources(session: AsyncSession) -> None:
    for source_id in RETIRED_SOURCE_IDS:
        retired = await session.get(Source, source_id)
        if retired is None:
            continue
        legacy_demo = (await session.execute(
            select(Job).where(Job.source_id == source_id, Job.is_demo == True)
        )).scalars().all()
        for job in legacy_demo:
            await session.delete(job)

        live_jobs = (await session.execute(
            select(func.count(Job.job_id)).where(Job.source_id == source_id, Job.is_demo == False)
        )).scalar() or 0
        if live_jobs:
            retired.enabled = False
        else:
            await session.delete(retired)

async def init_db(custom_engine=None):
    """Initializes tables and seeds default registries."""
    eng = custom_engine or engine
    needs_backfill = False
    async with eng.begin() as conn:
        if conn.dialect.name == "sqlite":
            needs_backfill = await _migrate_sqlite_schema(conn)
        await conn.run_sync(Base.metadata.create_all)

    # Seed default data
    session_factory = async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # 1. Seed Skills
        for skill_id, skill_name, category in DEFAULT_TAXONOMY_SKILLS:
            existing = await session.get(TaxonomySkill, skill_id)
            if not existing:
                session.add(TaxonomySkill(skill_id=skill_id, skill_name=skill_name, category=category))

        # 2. Seed and Synchronize Companies & Sources
        for item in DEFAULT_COMPANIES:
            existing_company = await session.get(Company, item["company_id"])
            if not existing_company:
                comp = Company(
                    company_id=item["company_id"],
                    name=item["name"],
                    canonical_category=item["canonical_category"],
                    website_url=item.get("website_url"),
                )
                session.add(comp)
                await session.flush()
            else:
                # Update configuration-managed fields
                existing_company.name = item["name"]
                existing_company.canonical_category = item["canonical_category"]
                if item.get("website_url"):
                    existing_company.website_url = item.get("website_url")

            source_cfg = item["source"]
            existing_source = await session.get(Source, source_cfg["source_id"])
            if not existing_source:
                src = Source(
                    source_id=source_cfg["source_id"],
                    company_id=item["company_id"],
                    provider_type=source_cfg["provider_type"],
                    base_url=source_cfg["base_url"],
                    board_token=source_cfg.get("board_token"),
                    endpoint=source_cfg.get("endpoint"),
                    allowed_hosts=source_cfg.get("allowed_hosts", "[]"),
                    enabled=source_cfg.get("enabled", True),
                    polling_interval_minutes=source_cfg.get("polling_interval_minutes", 60),
                    timeout_seconds=source_cfg.get("timeout_seconds", 15.0),
                    concurrency_limit=source_cfg.get("concurrency_limit", 2),
                )
                session.add(src)
            else:
                # Synchronize configuration-managed fields while preserving runtime telemetry
                configured_identity = (
                    source_cfg["provider_type"], source_cfg["base_url"],
                    source_cfg.get("board_token"), source_cfg.get("endpoint"),
                )
                stored_identity = (
                    existing_source.provider_type, existing_source.base_url,
                    existing_source.board_token, existing_source.endpoint,
                )
                if configured_identity != stored_identity:
                    logger.warning(
                        f"Source {existing_source.source_id} now points at {configured_identity} "
                        f"(was {stored_identity}); postings from the old board close through normal reconciliation"
                    )
                existing_source.provider_type = source_cfg["provider_type"]
                existing_source.base_url = source_cfg["base_url"]
                existing_source.board_token = source_cfg.get("board_token")
                existing_source.endpoint = source_cfg.get("endpoint")
                existing_source.allowed_hosts = source_cfg.get("allowed_hosts", "[]")
                # Never re-enable a source the user turned off; config can only switch off feeds that do not exist.
                if not source_cfg.get("enabled", True):
                    existing_source.enabled = False
                existing_source.polling_interval_minutes = source_cfg.get("polling_interval_minutes", 60)
                existing_source.timeout_seconds = source_cfg.get("timeout_seconds", 15.0)
                existing_source.concurrency_limit = source_cfg.get("concurrency_limit", 2)
                # Note: enabled, health_status, last_successful_sync, last_attempted_sync, last_error are preserved!

        await _retire_sources(session)

        if needs_backfill:
            await _backfill_derived_job_fields(session)

        # 3. Seed Candidate Profile
        existing_candidate = await session.get(CandidateProfile, "default")
        if not existing_candidate:
            cand = CandidateProfile(candidate_id="default", name="Unconfigured Profile", overall_yoe=None)
            session.add(cand)

        await session.commit()
