import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.db.models import Base, Source, Job, LifecycleStatus, SyncRun
from backend.db.session import init_db
from backend.services.reconciler import SafeReconciliationEngine

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
async def test_safe_reconciliation_state_machine(async_session: AsyncSession):
    source = await async_session.get(Source, "epic_greenhouse")
    assert source is not None

    engine = SafeReconciliationEngine(async_session, consecutive_missing_threshold=3)

    job_data_1 = {
        "provider_posting_id": "101",
        "requisition_id": "REQ-101",
        "title": "Senior Engine Programmer",
        "department": "Core Tech",
        "location": "Cary, NC",
        "apply_url": "https://boards.greenhouse.io/epicgames/jobs/101",
        "raw_html": "<h3>Senior Engine Programmer</h3><p>5+ years of C++ and Unreal Engine required.</p>",
    }

    job_data_2 = {
        "provider_posting_id": "102",
        "requisition_id": "REQ-102",
        "title": "Systems Infrastructure Engineer",
        "department": "Cloud",
        "location": "Remote",
        "apply_url": "https://boards.greenhouse.io/epicgames/jobs/102",
        "raw_html": "<h3>Systems Engineer</h3><p>Kubernetes and Docker experience needed.</p>",
    }

    # RUN 1: Discovered jobs 101 and 102
    run1 = await engine.execute_sync_run(source, [job_data_1, job_data_2], pagination_complete=True, requests_count=1)
    assert run1.jobs_created == 2
    assert run1.is_reconciliation_safe is True

    j1 = await async_session.get(Job, "epic_greenhouse:101")
    j2 = await async_session.get(Job, "epic_greenhouse:102")
    assert j1.lifecycle_status == LifecycleStatus.ACTIVE.value
    assert j2.lifecycle_status == LifecycleStatus.ACTIVE.value

    # RUN 2: FAILED SYNC (Network Timeout or Rate Limited) with empty payload
    # Must NOT touch or close any jobs!
    run2 = await engine.execute_sync_run(
        source,
        [],
        pagination_complete=False,
        requests_count=1,
        error_message="HTTP 429 Rate Limited",
    )
    assert run2.is_reconciliation_safe is False
    # Re-verify jobs are STILL ACTIVE!
    j1_after_fail = await async_session.get(Job, "epic_greenhouse:101")
    assert j1_after_fail.lifecycle_status == LifecycleStatus.ACTIVE.value
    assert j1_after_fail.consecutive_missing_syncs == 0

    # RUN 3: Complete sync where job 102 is omitted (only 101 remains)
    run3 = await engine.execute_sync_run(source, [job_data_1], pagination_complete=True, requests_count=1)
    assert run3.is_reconciliation_safe is True

    j2_omitted = await async_session.get(Job, "epic_greenhouse:102")
    # Transitioned to MISSING_CANDIDATE
    assert j2_omitted.lifecycle_status == LifecycleStatus.MISSING_CANDIDATE.value
    assert j2_omitted.consecutive_missing_syncs == 1

    # RUN 4 & 5: Job 102 missing again for 2 more consecutive syncs (hits threshold of 3)
    await engine.execute_sync_run(source, [job_data_1], pagination_complete=True, requests_count=1)
    await engine.execute_sync_run(source, [job_data_1], pagination_complete=True, requests_count=1)

    j2_closed = await async_session.get(Job, "epic_greenhouse:102")
    # Transitioned to CLOSED
    assert j2_closed.lifecycle_status == LifecycleStatus.CLOSED.value
    assert j2_closed.consecutive_missing_syncs == 3

    # RUN 6: RESURRECTION: Job 102 reappears in career feed!
    await engine.execute_sync_run(source, [job_data_1, job_data_2], pagination_complete=True, requests_count=1)
    j2_resurrected = await async_session.get(Job, "epic_greenhouse:102")
    assert j2_resurrected.lifecycle_status == LifecycleStatus.ACTIVE.value
    assert j2_resurrected.consecutive_missing_syncs == 0
