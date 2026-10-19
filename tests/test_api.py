import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.main import app
from backend.db.session import init_db, get_db_session
from backend.db.models import Job, Source, LifecycleStatus

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_session():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    await init_db(custom_engine=test_engine)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with session_factory() as session:
        # Seed an active engineering job
        job = Job(
            job_id="epic_greenhouse:999",
            source_id="epic_greenhouse",
            provider_posting_id="999",
            title="Lead Gameplay Programmer",
            canonical_category="Game Studio",
            location="Cary, NC",
            work_arrangement="hybrid",
            apply_url="https://boards.greenhouse.io/epicgames/jobs/999",
            lifecycle_status=LifecycleStatus.ACTIVE.value,
            normalized_description="Engine dev with C++ and Unreal",
            description_hash="testhash999",
        )
        session.add(job)
        await session.commit()
        yield session

    await test_engine.dispose()

@pytest.mark.asyncio
async def test_api_health_endpoint(test_session: AsyncSession):
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["database"] == "connected"

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_api_jobs_endpoint(test_session: AsyncSession):
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert "jobs" in data
        assert data["total_count"] >= 1
        assert data["jobs"][0]["job_id"] == "epic_greenhouse:999"
        assert "sector_counts" in data
        assert data["sector_counts"].get("Game Studio", 0) >= 1

        # Test location preset (US / EU)
        loc_resp = await ac.get("/api/jobs?location=US+%2F+EU")
        assert loc_resp.status_code == 200
        assert loc_resp.json()["total_count"] >= 1

        # Test role focus filter
        rf_resp = await ac.get("/api/jobs?role_focus=Game+Engine+%2F+Graphics")
        assert rf_resp.status_code == 200
        assert rf_resp.json()["total_count"] >= 1

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_api_telemetry_endpoint(test_session: AsyncSession):
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/telemetry/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert "skills_telemetry" in data
        assert "total_eligible_jobs" in data

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_api_candidate_gap_analysis(test_session: AsyncSession):
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/candidate/gap-analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert "candidate_yoe" in data
        assert "total_roles_analyzed" in data

    app.dependency_overrides.clear()
