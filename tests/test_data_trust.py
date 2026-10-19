import pytest
import pytest_asyncio
import uuid
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.connectors.base import ResilientHTTPClient
from backend.connectors.workday import WorkdayConnector
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.db.session import init_db
from backend.db.models import (
    Company,
    Source,
    Job,
    JobSnapshot,
    CandidateProfile,
    LifecycleStatus,
)
from backend.services.reconciler import SafeReconciliationEngine
from backend.services.gap_analyzer import GapAnalyzerService
from backend.services.telemetry import TelemetryEngine

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest_asyncio.fixture
async def memory_session():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    await init_db(custom_engine=test_engine)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await test_engine.dispose()

# ---------------------------------------------------------------------------
# 1. P0-1: Workday Zero-Fabrication & Genuine Detail Handling
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_workday_never_fabricates_synthetic_descriptions():
    """
    Verifies that Workday connector:
    1. Fetches genuine job description via CXS detail endpoint.
    2. When detail fetch fails or is missing, description remains empty/unavailable.
    3. NEVER injects hardcoded CUDA / C++ placeholder text.
    """
    source_cfg = {
        "source_id": "nvidia_test",
        "base_url": "https://nvidia.wd5.myworkdayjobs.com",
        "endpoint": "/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs",
        "allowed_hosts": '["nvidia.wd5.myworkdayjobs.com"]',
        "timeout_seconds": 5.0,
        "concurrency_limit": 2,
    }

    connector = WorkdayConnector(source_cfg)

    # Mock search POST response
    search_response = MagicMock(spec=httpx.Response)
    search_response.status_code = 200
    search_response.json.return_value = {
        "total": 2,
        "jobPostings": [
            {
                "title": "Senior AI Architect",
                "externalPath": "/job/Santa-Clara/Senior-AI-Architect_JR101",
                "locationsText": "Santa Clara, CA",
                "bulletFields": ["JR101"],
            },
            {
                "title": "Software Infrastructure Specialist",
                "externalPath": "/job/Austin/Infra-Specialist_JR102",
                "locationsText": "Austin, TX",
                "bulletFields": ["JR102"],
            }
        ]
    }

    # Detail responses: Job 1 succeeds with real HTML; Job 2 fails with 404
    detail_resp_1 = MagicMock(spec=httpx.Response)
    detail_resp_1.status_code = 200
    detail_resp_1.json.return_value = {
        "jobPostingInfo": {
            "jobDescription": "<p>Lead architecture for large distributed inference clusters using PyTorch.</p>",
            "jobReqId": "JR101",
            "startDate": "2026-10-01",
        }
    }

    detail_resp_2 = MagicMock(spec=httpx.Response)
    detail_resp_2.status_code = 404

    async def mock_request(method, url, **kwargs):
        if method == "POST":
            return search_response
        elif "JR101" in url:
            return detail_resp_1
        else:
            return detail_resp_2

    with patch.object(connector.client, "request", side_effect=mock_request):
        jobs, complete, count = await connector.fetch_jobs(max_pages=1)

    assert len(jobs) == 2
    assert complete is True

    # Job 1 has real description
    job1 = jobs[0]
    assert "PyTorch" in job1["raw_html"]
    assert job1["description_status"] == "available"
    assert "CUDA kernel optimization" not in job1["raw_html"], "Fabricated placeholder text was injected!"

    # Job 2 failed detail fetch: description must be empty/unavailable, NEVER fabricated
    job2 = jobs[1]
    assert job2["raw_html"] == ""
    assert job2["description_status"] == "unavailable"
    assert "CUDA" not in job2["raw_html"]
    assert "C++ runtime development" not in job2["raw_html"]

# ---------------------------------------------------------------------------
# 2. P0-2: Remove Implicit Candidate YOE Defaults
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_unconfigured_candidate_profile_has_no_invented_yoe(memory_session: AsyncSession):
    """
    Verifies that when a candidate profile is unconfigured:
    1. overall_yoe is None (never defaulted to 3.0 or 4.5).
    2. Gap analysis marks experience_alignment as 'unknown_candidate_yoe'.
    3. analysis_complete is False with explicit configuration callout.
    """
    session = memory_session
    # Create a fresh candidate profile with NO YOE specified
    cand_id = f"test_cand_{uuid.uuid4().hex[:6]}"
    cand = CandidateProfile(candidate_id=cand_id, name="Test Anonymous", overall_yoe=None)
    session.add(cand)
    await session.commit()

    analyzer = GapAnalyzerService(session)
    result = await analyzer.analyze_candidate_gap(candidate_id=cand_id)

    assert result["candidate_yoe"] is None, f"Expected None, got {result['candidate_yoe']}"
    assert result["experience_alignment"] == "unknown_candidate_yoe"
    assert result["analysis_complete"] is False
    assert "Configure your profile" in result["status_message"]

    # For individual analyzed roles, yoe_deficit is None and warning states unconfigured
    for role in result["top_matched_roles"]:
        assert role["has_experience_gap"] is False
        assert role["yoe_deficit"] is None
        assert role["yoe_gap_warning"] == "Candidate experience not configured"

# ---------------------------------------------------------------------------
# 3. P0-3: Strict Snapshot Binding in latest_skills (No Stale Fallback)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_latest_skills_bound_strictly_to_newest_snapshot_even_when_zero_skills(memory_session: AsyncSession):
    """
    Proves regression fix:
    If Snapshot 1 has skills [C++, CUDA] and employer modifies description to text
    with 0 extracted skills in Snapshot 2, job.latest_skills MUST return [] and
    never fall back to Snapshot 1 skills.
    """
    session = memory_session
    comp = Company(
        company_id=f"snap_comp_{uuid.uuid4().hex[:6]}",
        name="Snapshot Test Corp",
        canonical_category="Silicon & AI",
    )
    session.add(comp)
    await session.flush()

    source = Source(
        source_id=f"src_snap_{uuid.uuid4().hex[:6]}",
        company_id=comp.company_id,
        provider_type="greenhouse",
        base_url="https://boards-api.greenhouse.io",
        allowed_hosts='["boards-api.greenhouse.io"]',
    )
    session.add(source)
    await session.commit()

    reconciler = SafeReconciliationEngine(session, consecutive_missing_threshold=2)
    posting_id = f"job-snap-{uuid.uuid4().hex[:6]}"

    # Run 1: Description with C++ and CUDA
    payload_v1 = [{
        "provider_posting_id": posting_id,
        "title": "Staff GPU Systems Engineer",
        "department": "Compute",
        "location": "Santa Clara, CA",
        "apply_url": "https://example.com/apply",
        "raw_html": "<p>Must have deep experience in C++ and CUDA kernel development.</p>",
    }]
    await reconciler.execute_sync_run(source, payload_v1, pagination_complete=True, requests_count=1)

    job_stmt = select(Job).options(
        selectinload(Job.snapshots),
        selectinload(Job.skills),
    ).where(Job.source_id == source.source_id, Job.provider_posting_id == posting_id)
    job = (await session.execute(job_stmt)).scalar_one()

    assert len(job.snapshots) == 1
    assert len(job.latest_skills) == 2
    skill_ids_v1 = {s.skill_id for s in job.latest_skills}
    assert "cpp" in skill_ids_v1
    assert "cuda" in skill_ids_v1

    # Run 2: Employer rewrites description to generic team lead text with 0 technical skills
    payload_v2 = [{
        "provider_posting_id": posting_id,
        "title": "Staff GPU Systems Engineer",
        "department": "Compute",
        "location": "Santa Clara, CA",
        "apply_url": "https://example.com/apply",
        "raw_html": "<p>Responsible for team management, agile sprint planning, and quarterly reviews.</p>",
    }]
    src = await session.get(Source, source.source_id)
    await reconciler.execute_sync_run(src, payload_v2, pagination_complete=True, requests_count=1)

    await session.refresh(job, ["snapshots", "skills"])

    assert len(job.snapshots) == 2, "Expected 2 snapshots"
    # CRITICAL ASSERT: latest_skills must return [] for Snapshot 2, NOT fallback to Snapshot 1!
    assert job.latest_skills == [], f"Expected empty skills on newest snapshot, got {job.latest_skills}"

# ---------------------------------------------------------------------------
# 4. P0-4: SSRF Allowlist and Redirect Guards
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ssrf_rejects_empty_allowlist_unlisted_hosts_and_unvalidated_redirects():
    """
    Verifies SSRF defenses:
    1. Empty allowed_hosts raises ValueError.
    2. Non-HTTPS scheme is rejected.
    3. Unlisted destination hostname raises PermissionError.
    4. Redirect to unlisted internal IP/hostname raises PermissionError.
    """
    # 1. Empty allowlist rejected
    with pytest.raises(ValueError, match="allowed_hosts cannot be empty"):
        ResilientHTTPClient(allowed_hosts=[])

    with pytest.raises(ValueError, match="allowed_hosts must contain at least one valid host string"):
        ResilientHTTPClient(allowed_hosts=["  "])

    client = ResilientHTTPClient(allowed_hosts=["api.greenhouse.io"])

    # 2. Reject non-HTTPS
    with pytest.raises(PermissionError, match="SSRF Protection"):
        await client.request("GET", "http://api.greenhouse.io/v1/jobs")

    # 3. Reject unlisted host
    with pytest.raises(PermissionError, match="SSRF Protection"):
        await client.request("GET", "https://169.254.169.254/latest/meta-data/")

    with pytest.raises(PermissionError, match="SSRF Protection"):
        await client.request("GET", "https://internal.corp/secret")

    # 4. Reject redirect to unlisted host
    redirect_resp = MagicMock(spec=httpx.Response)
    redirect_resp.status_code = 302
    redirect_resp.headers = {"Location": "https://attacker.com/leak"}
    redirect_resp.url = httpx.URL("https://api.greenhouse.io/redirect")

    with patch("httpx.AsyncClient.request", AsyncMock(return_value=redirect_resp)):
        with pytest.raises(PermissionError, match="Redirect URL.*not in allowed hosts"):
            await client.request("GET", "https://api.greenhouse.io/redirect")

# ---------------------------------------------------------------------------
# 5. P0-4: Reconciliation Safety Against Sudden Inventory Drops (>50%)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reconciliation_volume_drop_prevents_catastrophic_closures(memory_session: AsyncSession):
    """
    Verifies that if a previously populated source suddenly drops by >50%
    in a single run, is_reconciliation_safe is set to False, preventing
    catastrophic mass closure of genuine active roles.
    """
    session = memory_session
    comp = Company(
        company_id=f"drop_comp_{uuid.uuid4().hex[:6]}",
        name="Drop Guard Studio",
        canonical_category="Game Studio",
    )
    session.add(comp)
    await session.flush()

    source = Source(
        source_id=f"src_drop_{uuid.uuid4().hex[:6]}",
        company_id=comp.company_id,
        provider_type="greenhouse",
        base_url="https://boards-api.greenhouse.io",
        allowed_hosts='["boards-api.greenhouse.io"]',
    )
    session.add(source)
    await session.commit()

    reconciler = SafeReconciliationEngine(session, consecutive_missing_threshold=2)

    # Ingest 12 active roles initially
    postings = [
        {
            "provider_posting_id": f"drop-job-{i}",
            "title": f"Gameplay Programmer {i}",
            "raw_html": "<p>C++ and Unreal gameplay development.</p>",
        }
        for i in range(12)
    ]
    run1 = await reconciler.execute_sync_run(source, postings, pagination_complete=True, requests_count=1)
    assert run1.jobs_created == 12
    assert run1.is_reconciliation_safe is True

    # Next run: Source returns only 2 roles (83% drop - e.g. API truncated or endpoint glitch)
    src = await session.get(Source, source.source_id)
    run2 = await reconciler.execute_sync_run(src, postings[:2], pagination_complete=True, requests_count=1)

    # Reconciliation must NOT be safe!
    assert run2.is_reconciliation_safe is False
    assert "Suspicious volume drop" in run2.error_message

    # Verify other 10 jobs were NOT marked MISSING_CANDIDATE
    omitted_job_stmt = select(Job).where(
        Job.source_id == source.source_id,
        Job.provider_posting_id == "drop-job-5",
    )
    job5 = (await session.execute(omitted_job_stmt)).scalar_one()
    assert job5.lifecycle_status == LifecycleStatus.ACTIVE.value
    assert job5.consecutive_missing_syncs == 0, "Job was incorrectly incremented despite unsafe drop!"

# ---------------------------------------------------------------------------
# 6. P1-1: Honest Telemetry Semantics & Denominators
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_telemetry_honest_cohort_and_source_coverage(memory_session: AsyncSession):
    """
    Verifies that Telemetry returns:
    1. Accurate total_eligible_jobs and denominator_count.
    2. Distinct source_coverage_count.
    3. Newly observed discovery cohort count without falsely calling it a 30d market demand trend.
    """
    session = memory_session
    telemetry_engine = TelemetryEngine(session)
    result = await telemetry_engine.get_market_telemetry(include_demo=True)

    assert "total_eligible_jobs" in result
    assert "denominator_count" in result
    assert result["denominator_count"] == result["total_eligible_jobs"]
    assert "source_coverage_count" in result
    assert "newly_observed_cohort_total" in result
    assert "data_quality_warnings" in result

    # Check telemetry skill item structure
    for item in result["skills_telemetry"]:
        assert "newly_observed_cohort_count" in item
        assert item["newly_observed_cohort_count"] >= 0
        assert "company_breadth" in item
        assert "skill_share_pct" in item
