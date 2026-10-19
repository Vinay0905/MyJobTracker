import json
from typing import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.db.models import Base, Company, Source, TaxonomySkill, CandidateProfile

DATABASE_URL = "sqlite+aiosqlite:///./devradar.db"

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
            "source_id": "ea_greenhouse",
            "provider_type": "greenhouse",
            "base_url": "https://boards-api.greenhouse.io",
            "board_token": "ea",
            "allowed_hosts": json.dumps(["boards-api.greenhouse.io", "boards.greenhouse.io", "ea.com", "jobs.ea.com"]),
            "enabled": True,
            "polling_interval_minutes": 60,
            "timeout_seconds": 15.0,
            "concurrency_limit": 3,
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
        "name": "Sony PlayStation Studios",
        "canonical_category": "Game Studio",
        "website_url": "https://www.playstation.com",
        "source": {
            "source_id": "playstation_greenhouse",
            "provider_type": "greenhouse",
            "base_url": "https://boards-api.greenhouse.io",
            "board_token": "playstationglobal",
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

async def _migrate_sqlite_schema(conn):
    """Safely adds missing columns to existing SQLite database tables."""
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

async def init_db(custom_engine=None):
    """Initializes tables and seeds default registries."""
    eng = custom_engine or engine
    async with eng.begin() as conn:
        await _migrate_sqlite_schema(conn)
        await conn.run_sync(Base.metadata.create_all)

    # Seed default data
    session_factory = async_sessionmaker(bind=eng, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        # 1. Seed Skills
        for skill_id, skill_name, category in DEFAULT_TAXONOMY_SKILLS:
            existing = await session.get(TaxonomySkill, skill_id)
            if not existing:
                session.add(TaxonomySkill(skill_id=skill_id, skill_name=skill_name, category=category))

        # 2. Seed Companies & Sources
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

        # 3. Seed Candidate Profile
        existing_candidate = await session.get(CandidateProfile, "default")
        if not existing_candidate:
            cand = CandidateProfile(candidate_id="default", name="Unconfigured Profile", overall_yoe=None)
            session.add(cand)

        await session.commit()
