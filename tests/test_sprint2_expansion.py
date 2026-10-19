import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.main import app
from backend.db.session import init_db, get_db_session
from backend.db.models import Job, JobExperienceRequirement, LifecycleStatus
from backend.connectors.ashby import AshbyConnector
from backend.connectors.lever import LeverConnector
from backend.connectors.smartrecruiters import SmartRecruitersConnector
from backend.api.routes import ROLE_FOCUS_MAP

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def expansion_session():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    await init_db(custom_engine=test_engine)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        # Job 1: Early-career / mid role (2 YOE required)
        j1 = Job(
            job_id="test:early",
            source_id="roblox_ashby",
            provider_posting_id="101",
            title="Software Engineer - AI NPCs",
            canonical_category="Game Studio",
            location="San Mateo, CA",
            work_arrangement="hybrid",
            apply_url="https://jobs.ashbyhq.com/roblox/101",
            lifecycle_status=LifecycleStatus.ACTIVE.value,
            normalized_description="Develop game AI, behavior trees, and NPC logic in C++.",
            description_hash="hash101",
            required_yoe=2,
        )
        session.add(j1)
        await session.flush()
        req1 = JobExperienceRequirement(
            job_id=j1.job_id,
            min_years=2,
            max_years=4,
            experience_scope="overall_professional",
            evidence_text="2+ years experience in C++ and game AI",
        )
        session.add(req1)

        # Job 2: Senior/Principal role (8 YOE required)
        j2 = Job(
            job_id="test:staff",
            source_id="cerebras_lever",
            provider_posting_id="102",
            title="Principal Physics & Simulation Architect",
            canonical_category="Silicon & AI",
            location="Sunnyvale, CA",
            work_arrangement="onsite",
            apply_url="https://jobs.lever.co/cerebras/102",
            lifecycle_status=LifecycleStatus.ACTIVE.value,
            normalized_description="Design large scale distributed physics simulation and rigid body solvers.",
            description_hash="hash102",
            required_yoe=8,
        )
        session.add(j2)
        await session.flush()
        req2 = JobExperienceRequirement(
            job_id=j2.job_id,
            min_years=8,
            max_years=12,
            experience_scope="overall_professional",
            evidence_text="8+ years building simulation engines",
        )
        session.add(req2)

        # Job 3: Unspecified YOE role
        j3 = Job(
            job_id="test:unspecified",
            source_id="arista_smartrecruiters",
            provider_posting_id="103",
            title="Edge AI & Embedded Firmware Engineer",
            canonical_category="Silicon & AI",
            location="Santa Clara, CA",
            work_arrangement="onsite",
            apply_url="https://jobs.smartrecruiters.com/arista/103",
            lifecycle_status=LifecycleStatus.ACTIVE.value,
            normalized_description="Develop low-level RTOS and FreeRTOS firmware.",
            description_hash="hash103",
        )
        session.add(j3)

        await session.commit()
        yield session

    await test_engine.dispose()

@pytest.mark.asyncio
async def test_years_range_filter_behavior(expansion_session: AsyncSession):
    async def override_get_db():
        yield expansion_session

    app.dependency_overrides[get_db_session] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Without filter: all 3 jobs returned; the card number is the stored years rule
        resp_all = await ac.get("/api/jobs")
        assert resp_all.status_code == 200
        jobs_all = {j["job_id"]: j for j in resp_all.json()["jobs"]}
        assert len(jobs_all) == 3
        assert jobs_all["test:early"]["primary_min_yoe"] == 2
        assert jobs_all["test:unspecified"]["primary_min_yoe"] is None

        # 0-6 range: 8 YOE job excluded; unspecified stays in the list (labeled unspecified, not "0-6")
        resp_filtered = await ac.get("/api/jobs?yoe_min=0&yoe_max=6")
        filtered_ids = {j["job_id"] for j in resp_filtered.json()["jobs"]}
        assert filtered_ids == {"test:early", "test:unspecified"}

        # Legacy alias still works
        resp_alias = await ac.get("/api/jobs?max_required_yoe=6")
        assert {j["job_id"] for j in resp_alias.json()["jobs"]} == filtered_ids

        # Excluding unspecified keeps only roles that state their years
        resp_strict = await ac.get("/api/jobs?yoe_min=0&yoe_max=6&include_unspecified_yoe=false")
        assert {j["job_id"] for j in resp_strict.json()["jobs"]} == {"test:early"}

        # Min bound
        resp_senior = await ac.get("/api/jobs?yoe_min=5&include_unspecified_yoe=false")
        assert {j["job_id"] for j in resp_senior.json()["jobs"]} == {"test:staff"}

    app.dependency_overrides.clear()

def test_granular_role_focus_tracks_registered():
    expected_tracks = [
        "ai npcs & game ai",
        "physics & simulation",
        "gpu / cuda & silicon",
        "edge ai & embedded ece",
        "ai servers & cloud",
    ]
    for track in expected_tracks:
        assert track in ROLE_FOCUS_MAP
        assert len(ROLE_FOCUS_MAP[track]["skills"]) > 0
        assert len(ROLE_FOCUS_MAP[track]["keywords"]) > 0

@pytest.mark.asyncio
async def test_new_connectors_structure_and_no_data_fabrication():
    ashby = AshbyConnector({
        "source_id": "test_ashby",
        "board_token": "roblox",
        "base_url": "https://api.ashbyhq.com",
    })
    assert ashby.board_token == "roblox"
    assert "api.ashbyhq.com" in ashby.client.allowed_hosts

    lever = LeverConnector({
        "source_id": "test_lever",
        "company": "cerebras",
        "base_url": "https://api.lever.co",
    })
    assert lever.company == "cerebras"
    assert "api.lever.co" in lever.client.allowed_hosts

    sr = SmartRecruitersConnector({
        "source_id": "test_sr",
        "company": "AristaNetworks",
        "base_url": "https://api.smartrecruiters.com",
    })
    assert sr.company == "AristaNetworks"
    assert "api.smartrecruiters.com" in sr.client.allowed_hosts
