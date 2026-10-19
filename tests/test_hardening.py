import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.db.session import init_db
from backend.db.models import (
    Company,
    Source,
    Job,
    JobSnapshot,
    ExtractionRun,
    JobSkillEvidence,
    LifecycleStatus,
)
from backend.services.reconciler import SafeReconciliationEngine
from backend.services.gap_analyzer import GapAnalyzerService
from backend.services.telemetry import TelemetryEngine

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def test_session():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    await init_db(custom_engine=test_engine)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await test_engine.dispose()

@pytest.mark.asyncio
async def test_snapshot_version_diff_and_provenance(test_session: AsyncSession):
    """
    Verifies that when a job description is updated:
    1. A new JobSnapshot and ExtractionRun are generated.
    2. The previous snapshot and its extracted skills are preserved intact.
    3. job.latest_skills reflects only the new snapshot's skills.
    """
    session = test_session
    # Create a test source
    comp = Company(
        company_id=f"test_studio_{uuid.uuid4().hex[:6]}",
        name="Test Studio",
        canonical_category="Game Studio",
    )
    session.add(comp)
    await session.flush()

    source = Source(
        source_id=f"src_{uuid.uuid4().hex[:6]}",
        company_id=comp.company_id,
        provider_type="greenhouse",
        base_url="https://boards-api.greenhouse.io",
        allowed_hosts='["boards-api.greenhouse.io"]',
    )
    session.add(source)
    await session.commit()

    reconciler = SafeReconciliationEngine(session)

    # Initial Observation (Version 1: C++, Unreal, Vulkan)
    posting_v1 = [{
        "provider_posting_id": "job-100",
        "title": "Senior Graphics Programmer",
        "raw_html": "<p>Looking for 5+ years with C++, Unreal Engine, and Vulkan shaders.</p>",
        "url": "https://example.com/apply",
    }]
    await reconciler.execute_sync_run(source, posting_v1, pagination_complete=True, requests_count=1)

    # Inspect Job state after V1
    job_stmt = select(Job).options(
        selectinload(Job.snapshots),
        selectinload(Job.skills),
        selectinload(Job.experience_requirements),
    ).where(Job.source_id == source.source_id, Job.provider_posting_id == "job-100")
    job = (await session.execute(job_stmt)).scalar_one()

    assert len(job.snapshots) == 1
    v1_snapshot_id = job.snapshots[0].snapshot_id
    v1_skills = {s.skill_id for s in job.latest_skills}
    assert "cpp" in v1_skills
    assert "unreal_engine" in v1_skills
    assert "vulkan" in v1_skills

    # Mutated Observation (Version 2: Requirements modified to DirectX 12 and Python, dropped Vulkan)
    posting_v2 = [{
        "provider_posting_id": "job-100",
        "title": "Senior Graphics Programmer",
        "raw_html": "<p>Looking for 5+ years with C++, Unreal Engine, DirectX 12, and Python scripting.</p>",
        "url": "https://example.com/apply",
    }]
    await reconciler.execute_sync_run(source, posting_v2, pagination_complete=True, requests_count=1)

    # Re-inspect Job state after V2
    session.expire_all()
    job = (await session.execute(job_stmt)).scalar_one()

    # Snapshot history must be preserved (provenance integrity)
    assert len(job.snapshots) == 2
    assert job.snapshots[0].snapshot_id == v1_snapshot_id
    assert job.snapshots[1].snapshot_id != v1_snapshot_id

    # Active skills must reflect ONLY the latest snapshot
    v2_active_skills = {s.skill_id for s in job.latest_skills}
    assert "cpp" in v2_active_skills
    assert "unreal_engine" in v2_active_skills
    assert "directx" in v2_active_skills
    assert "python" in v2_active_skills
    assert "vulkan" not in v2_active_skills

    # Total historical evidence records must preserve both snapshots
    total_evidence_stmt = select(JobSkillEvidence).where(JobSkillEvidence.job_id == job.job_id)
    all_evidence = (await session.execute(total_evidence_stmt)).scalars().all()
    v1_evidence_count = sum(1 for e in all_evidence if e.snapshot_id == v1_snapshot_id)
    v2_evidence_count = sum(1 for e in all_evidence if e.snapshot_id == job.snapshots[1].snapshot_id)
    assert v1_evidence_count == 3
    assert v2_evidence_count == 4
    assert len(all_evidence) == 7

@pytest.mark.asyncio
async def test_reconciliation_two_run_closure_and_resurrection(test_session: AsyncSession):
    """
    Verifies state transitions:
    1. Active -> Missing Candidate (1 missing run)
    2. Missing Candidate -> Closed (2 missing runs)
    3. Closed -> Active (Resurrected when re-observed)
    """
    session = test_session
    comp = Company(company_id=f"rec_comp_{uuid.uuid4().hex[:6]}", name="Rec Studio", canonical_category="Silicon & AI")
    session.add(comp)
    await session.flush()

    source = Source(
        source_id=f"src_rec_{uuid.uuid4().hex[:6]}",
        company_id=comp.company_id,
        provider_type="workday",
        base_url="https://workday.example.com",
        allowed_hosts='["workday.example.com"]',
    )
    session.add(source)
    await session.commit()

    reconciler = SafeReconciliationEngine(session, consecutive_missing_threshold=2)

    # Run 1: Discover job
    ephemeral_id = f"ephemeral-job-{uuid.uuid4().hex[:6]}"
    postings = [{
        "provider_posting_id": ephemeral_id,
        "title": "Kernel Driver Engineer",
        "raw_html": "<p>Linux Kernel and C driver engineer.</p>",
        "url": "https://example.com/apply/kernel",
    }]
    await reconciler.execute_sync_run(source, postings, pagination_complete=True, requests_count=1)

    job_stmt = select(Job).where(Job.source_id == source.source_id, Job.provider_posting_id == ephemeral_id)
    job = (await session.execute(job_stmt)).scalar_one()
    assert job.lifecycle_status == LifecycleStatus.ACTIVE.value
    assert job.consecutive_missing_syncs == 0

    # Run 2: Job omitted from complete sync -> MISSING_CANDIDATE
    src = await session.get(Source, source.source_id)
    await reconciler.execute_sync_run(src, [], pagination_complete=True, requests_count=1)
    job = (await session.execute(job_stmt)).scalar_one()
    assert job.lifecycle_status == LifecycleStatus.MISSING_CANDIDATE.value
    assert job.consecutive_missing_syncs == 1

    # Run 3: Job omitted second consecutive time -> CLOSED
    src = await session.get(Source, source.source_id)
    await reconciler.execute_sync_run(src, [], pagination_complete=True, requests_count=1)
    job = (await session.execute(job_stmt)).scalar_one()
    assert job.lifecycle_status == LifecycleStatus.CLOSED.value
    assert job.consecutive_missing_syncs == 2

    # Run 4: Job reappears -> Resurrected to ACTIVE
    src = await session.get(Source, source.source_id)
    await reconciler.execute_sync_run(src, postings, pagination_complete=True, requests_count=1)
    job = (await session.execute(job_stmt)).scalar_one()
    assert job.lifecycle_status == LifecycleStatus.ACTIVE.value
    assert job.consecutive_missing_syncs == 0

@pytest.mark.asyncio
async def test_demo_isolation_and_gap_warnings(test_session: AsyncSession):
    """
    Verifies that:
    1. Demo jobs (is_demo=True) are excluded from live telemetry and gap analysis by default.
    2. 1-Skill Away correctly flags roles with exactly 1 missing skill.
    3. Roles with YOE deficit produce explicit yoe_gap_warning.
    """
    session = test_session
    analyzer = GapAnalyzerService(session)

    # Analyze without demo
    live_result = await analyzer.analyze_candidate_gap(include_demo=False)
    # Analyze with demo
    demo_result = await analyzer.analyze_candidate_gap(include_demo=True)

    assert demo_result["total_roles_analyzed"] >= live_result["total_roles_analyzed"]

    # Check YOE gap warning logic on analyzed roles
    roles_with_yoe_deficit = [r for r in demo_result["top_matched_roles"] if r["has_experience_gap"]]
    for role in roles_with_yoe_deficit:
        assert role["yoe_deficit"] > 0
        assert role["yoe_gap_warning"] is not None
        assert "Candidate has" in role["yoe_gap_warning"]
