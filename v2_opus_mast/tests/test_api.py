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

@pytest.mark.asyncio
async def test_api_companies_endpoint(test_session: AsyncSession):
    """Verifies GET /api/companies returns companies with live active job counts."""
    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/companies")
        assert resp.status_code == 200
        companies = resp.json()
        assert isinstance(companies, list)
        assert len(companies) >= 1
        epic = next((c for c in companies if "epic" in c["company_id"].lower()), None)
        assert epic is not None
        assert epic["name"] == "Epic Games"
        assert epic["active_jobs_count"] >= 1

    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_api_sync_status_endpoint():
    """Verifies GET /api/sync/status returns real-time lifecycle observability."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/sync/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "is_active" in data
        assert "status" in data
        assert "total_sources" in data
        assert "completed_sources" in data
        assert "summary" in data

@pytest.mark.asyncio
async def test_api_company_filtering_and_sorting(test_session: AsyncSession):
    """Verifies exact company_id filtering (single and multi) as well as all 8 backend sort orders."""
    # Seed a second job for a different company
    job2 = Job(
        job_id="rockstar_greenhouse:888",
        source_id="rockstar_greenhouse",
        provider_posting_id="888",
        title="Animation Programmer",
        canonical_category="Game Studio",
        location="Edinburgh, UK",
        work_arrangement="onsite",
        apply_url="https://boards.greenhouse.io/rockstargames/jobs/888",
        lifecycle_status=LifecycleStatus.ACTIVE.value,
        normalized_description="Animation systems in C++",
        description_hash="testhash888",
    )
    test_session.add(job2)
    await test_session.commit()

    async def override_get_db():
        yield test_session

    app.dependency_overrides[get_db_session] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Single company filter (exact company_id)
        resp_single = await ac.get("/api/jobs?company=epicgames")
        assert resp_single.status_code == 200
        data_single = resp_single.json()
        assert data_single["total_count"] == 1
        assert data_single["jobs"][0]["job_id"] == "epic_greenhouse:999"
        assert data_single["jobs"][0]["company_id"] == "epicgames"

        # A partial id is not a company id
        resp_partial = await ac.get("/api/jobs?company=epic")
        assert resp_partial.json()["total_count"] == 0

        # 2. Multi-company filter (comma-separated exact ids)
        resp_multi = await ac.get("/api/jobs?company=epicgames,rockstar")
        assert resp_multi.status_code == 200
        data_multi = resp_multi.json()
        assert data_multi["total_count"] == 2
        returned_ids = {j["job_id"] for j in data_multi["jobs"]}
        assert "epic_greenhouse:999" in returned_ids
        assert "rockstar_greenhouse:888" in returned_ids

        # 3. Test all 8 sort orders
        sort_orders = [
            "newest_discovered",
            "recently_posted",
            "company_asc",
            "company_desc",
            "title_asc",
            "title_desc",
            "location_asc",
            "recently_updated",
        ]
        for sort_by in sort_orders:
            sort_resp = await ac.get(f"/api/jobs?sort_by={sort_by}")
            assert sort_resp.status_code == 200, f"Sort order failed: {sort_by}"
            data_sort = sort_resp.json()
            assert data_sort["total_count"] == 2
            assert len(data_sort["jobs"]) == 2

        # Verify company_asc vs company_desc
        asc_resp = await ac.get("/api/jobs?sort_by=company_asc")
        desc_resp = await ac.get("/api/jobs?sort_by=company_desc")
        assert asc_resp.json()["jobs"][0]["company"] == "Epic Games"
        assert desc_resp.json()["jobs"][0]["company"] == "Rockstar Games"

        # Verify title_asc vs title_desc
        t_asc_resp = await ac.get("/api/jobs?sort_by=title_asc")
        t_desc_resp = await ac.get("/api/jobs?sort_by=title_desc")
        assert t_asc_resp.json()["jobs"][0]["title"] == "Animation Programmer"
        assert t_desc_resp.json()["jobs"][0]["title"] == "Lead Gameplay Programmer"

    app.dependency_overrides.clear()

