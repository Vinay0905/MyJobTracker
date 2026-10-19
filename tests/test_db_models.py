import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.db.models import Base, Company, Source, Job, LifecycleStatus, SyncRun, RunStatus
from backend.db.session import init_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def async_session():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    await init_db(custom_engine=test_engine)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await test_engine.dispose()

@pytest.mark.asyncio
async def test_seed_initialization(async_session: AsyncSession):
    nvidia = await async_session.get(Company, "nvidia")
    assert nvidia is not None
    assert nvidia.name == "NVIDIA"
    assert nvidia.canonical_category == "Silicon & AI"

    source = await async_session.get(Source, "nvidia_workday")
    assert source is not None
    assert source.provider_type == "workday"

@pytest.mark.asyncio
async def test_job_creation_and_constraints(async_session: AsyncSession):
    job = Job(
        job_id="epic_greenhouse:1001",
        source_id="epic_greenhouse",
        provider_posting_id="1001",
        title="Unreal Engine Core Programmer",
        canonical_category="Game Studio",
        location="Cary, NC",
        work_arrangement="hybrid",
        apply_url="https://boards.greenhouse.io/epicgames/jobs/1001",
        lifecycle_status=LifecycleStatus.ACTIVE.value,
        description_hash="dummyhash",
        normalized_description="Engine dev",
    )
    async_session.add(job)
    await async_session.commit()

    saved_job = await async_session.get(Job, "epic_greenhouse:1001")
    assert saved_job is not None
    assert saved_job.title == "Unreal Engine Core Programmer"
    assert saved_job.lifecycle_status == LifecycleStatus.ACTIVE.value
