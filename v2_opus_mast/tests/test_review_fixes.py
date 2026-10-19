import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse, parse_qs

import httpx
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from backend.main import app
from backend.api import routes
from backend.db.session import init_db, get_db_session
from backend.db.models import (
    Company,
    Source,
    Job,
    JobSnapshot,
    JobSkillEvidence,
    JobFieldChangeEvent,
    CandidateProfile,
    CandidateSkillEvidence,
    LifecycleStatus,
)
from backend.connectors.smartrecruiters import SmartRecruitersConnector
from backend.connectors.workday import WorkdayConnector
from backend.extraction.normalizer import segment_description
from backend.extraction.pipeline import process_job_description
from backend.extraction.experience import extract_experience_requirements, governing_min_years
from backend.extraction.attributes import parse_seniority, parse_work_arrangement, parse_salary, parse_provider_timestamp
from backend.extraction.taxonomy import resolve_skill
from backend.services.reconciler import SafeReconciliationEngine
from backend.services.gap_analyzer import GapAnalyzerService
from backend.services.telemetry import TelemetryEngine

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def session():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    await init_db(custom_engine=test_engine)
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession):
    async def override_get_db():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _resp(status: int, payload=None):
    r = MagicMock(spec=httpx.Response)
    r.status_code = status
    r.json.return_value = payload
    return r


def _job(job_id: str, source_id: str, title: str, **kwargs) -> Job:
    defaults = dict(
        provider_posting_id=job_id.split(":")[-1],
        canonical_category="Game Studio",
        location="Cary, NC",
        work_arrangement="unknown",
        apply_url=f"https://example.com/{job_id}",
        lifecycle_status=LifecycleStatus.ACTIVE.value,
        normalized_description="",
        description_hash=f"hash-{job_id}",
    )
    defaults.update(kwargs)
    return Job(job_id=job_id, source_id=source_id, title=title, **defaults)


# ---------------------------------------------------------------------------
# Extraction: headings and years
# ---------------------------------------------------------------------------
def test_preferred_heading_is_not_swallowed_by_bare_qualifications():
    text = "\n".join([
        "Minimum Qualifications:",
        "- Strong C++ programming",
        "Preferred Qualifications:",
        "- Experience with CUDA",
        "Qualifications:",
        "- Python scripting",
    ])
    sections = segment_description(text)
    assert "- Strong C++ programming" in sections["REQUIRED_SECTION"]
    assert "- Experience with CUDA" in sections["PREFERRED_SECTION"]
    assert "- Python scripting" in sections["REQUIRED_SECTION"]

    res = process_job_description("Graphics Engineer", "Engineering", text)
    types = {s["skill_id"]: s["requirement_type"] for s in res["skills"]}
    assert types["cpp"] == "required"
    assert types["cuda"] == "preferred"
    assert types["python"] == "required"


def test_years_come_from_requirement_lines_only():
    text = "\n".join([
        "Epic has been building games for over 30 years.",
        "Applicants must be 18 years or older.",
        "We are celebrating 25 years in Cary.",
        "Requirements:",
        "- 4+ years of professional software engineering experience",
        "- 2+ years with C++",
    ])
    exp = extract_experience_requirements(text)
    assert {e["min_years"] for e in exp} == {4, 2}
    assert all("30 years" not in e["evidence_text"] and "18 years" not in e["evidence_text"] for e in exp)
    # Overall experience governs over the skill-specific line
    assert governing_min_years(exp) == 4


def test_governing_years_ignores_stale_age_and_history_rows():
    stored_rows = [
        {"min_years": 30, "experience_scope": "overall_professional", "evidence_text": "Shipping hits for over 30 years."},
        {"min_years": 18, "experience_scope": "overall_professional", "evidence_text": "You must be 18 years or older."},
        {"min_years": 4, "experience_scope": "degree_equivalent", "evidence_text": "BS or 4 years equivalent experience"},
    ]
    assert governing_min_years(stored_rows) is None
    assert governing_min_years(stored_rows + [
        {"min_years": 3, "experience_scope": "skill_specific", "evidence_text": "3+ years of Unreal experience"},
    ]) == 3


# ---------------------------------------------------------------------------
# Attributes: seniority, arrangement, pay, timestamps
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("title,level", [
    ("Software Engineering Intern", "intern"),
    ("Associate Gameplay Programmer", "associate"),
    ("Junior Tools Engineer", "associate"),
    ("Mid-Level Graphics Engineer", "mid"),
    ("Senior CUDA Engineer", "senior"),
    ("Sr. Rendering Engineer", "senior"),
    ("Senior Staff Systems Engineer", "staff"),
    ("Principal Engine Architect", "principal"),
    ("Gameplay Programmer", "unspecified"),
    ("Lead Physics Programmer", "unspecified"),
])
def test_seniority_from_title(title, level):
    assert parse_seniority(title) == level


def test_work_arrangement_from_posting_or_location():
    assert parse_work_arrangement("OnSite", "Remote - US") == "onsite"
    assert parse_work_arrangement("hybrid", "") == "hybrid"
    assert parse_work_arrangement(None, "Remote - US") == "remote"
    assert parse_work_arrangement(None, "London (Hybrid)") == "hybrid"
    assert parse_work_arrangement(None, "Santa Clara, CA") == "unknown"


def test_salary_only_when_stated():
    assert parse_salary("The base pay range is $150,000 - $200,000 USD per year.") == {
        "salary_min": 150000.0, "salary_max": 200000.0, "salary_currency": "USD",
    }
    assert parse_salary("£60k–£75k plus bonus")["salary_currency"] == "GBP"
    assert parse_salary("$100-150k")["salary_min"] == 100000.0
    # Hourly, bare numbers, and years ranges are not salaries
    assert parse_salary("$45 - $60 per hour")["salary_min"] is None
    assert parse_salary("3-5 years of experience, 401k match")["salary_min"] is None
    assert parse_salary("")["salary_min"] is None
    assert parse_salary("", {"min": 120000, "max": 140000, "currency": "USD", "interval": "per-year-salary"})["salary_max"] == 140000.0
    assert parse_salary("", {"min": 50, "max": 70, "currency": "USD", "interval": "per-hour-wage"})["salary_min"] is None


def test_provider_timestamps():
    assert parse_provider_timestamp("2026-09-01T10:00:00Z") == datetime(2026, 9, 1, 10, tzinfo=timezone.utc)
    assert parse_provider_timestamp(1767225600000) == datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert parse_provider_timestamp("Posted 30+ Days Ago") is None


# ---------------------------------------------------------------------------
# Connectors: incomplete pagination
# ---------------------------------------------------------------------------
def _sr_connector():
    return SmartRecruitersConnector({"source_id": "sr_test", "board_token": "AristaNetworks"})


def _sr_mock(total_found: int, failing_detail_ids=()):
    async def mock_request(method, url, **kwargs):
        parsed = urlparse(url)
        if parsed.path.endswith("/postings"):
            qs = parse_qs(parsed.query)
            offset, limit = int(qs["offset"][0]), int(qs["limit"][0])
            ids = list(range(offset, min(offset + limit, total_found)))
            return _resp(200, {"totalFound": total_found, "content": [
                {"id": f"p{i}", "name": f"Software Engineer {i}", "location": {"city": "Santa Clara", "country": "us"}}
                for i in ids
            ]})
        posting_id = parsed.path.rsplit("/", 1)[-1]
        if posting_id in failing_detail_ids:
            return _resp(500)
        return _resp(200, {"jobAd": {"sections": {"jobDescription": {"text": "<p>C++ work</p>"}}}})
    return mock_request


@pytest.mark.asyncio
async def test_smartrecruiters_paginates_until_total_found():
    conn = _sr_connector()
    with patch.object(conn.client, "request", side_effect=_sr_mock(5)):
        jobs, complete, _ = await conn.fetch_jobs(limit=2)
    assert len(jobs) == 5
    assert complete is True


@pytest.mark.asyncio
async def test_smartrecruiters_incomplete_when_full_page_remains():
    conn = _sr_connector()
    with patch.object(conn.client, "request", side_effect=_sr_mock(5)):
        jobs, complete, _ = await conn.fetch_jobs(limit=2, max_pages=2)
    assert len(jobs) == 4
    assert complete is False


@pytest.mark.asyncio
async def test_smartrecruiters_incomplete_when_detail_fetch_fails():
    conn = _sr_connector()
    with patch.object(conn.client, "request", side_effect=_sr_mock(3, failing_detail_ids={"p1"})):
        jobs, complete, _ = await conn.fetch_jobs(limit=10)
    assert complete is False
    failed = next(j for j in jobs if j["provider_posting_id"] == "p1")
    assert failed["description_status"] == "unavailable"


def _workday_connector(search_text=""):
    return WorkdayConnector({
        "source_id": "wd_test",
        "base_url": "https://nvidia.wd5.myworkdayjobs.com",
        "endpoint": "/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs",
        "allowed_hosts": '["nvidia.wd5.myworkdayjobs.com"]',
        "search_text": search_text,
    })


def _workday_mock(catalog_size: int, report_total=True, total_on_first_page_only=True):
    async def mock_request(method, url, json_data=None, **kwargs):
        if method == "GET":
            return _resp(404)
        offset, limit = json_data["offset"], json_data["limit"]
        ids = range(offset, min(offset + limit, catalog_size))
        payload = {"jobPostings": [
            {"title": f"Engineer {i}", "externalPath": f"/job/x/Engineer_JR{i}", "bulletFields": [f"JR{i}"]}
            for i in ids
        ]}
        if report_total:
            payload["total"] = catalog_size if (offset == 0 or not total_on_first_page_only) else 0
        return _resp(200, payload)
    return mock_request


@pytest.mark.asyncio
async def test_workday_remembers_total_from_first_page():
    conn = _workday_connector()
    with patch.object(conn.client, "request", side_effect=_workday_mock(50)):
        jobs, complete, _ = await conn.fetch_jobs(max_pages=5)
    assert len(jobs) == 50
    assert complete is True


@pytest.mark.asyncio
async def test_workday_missing_total_is_incomplete():
    conn = _workday_connector()
    with patch.object(conn.client, "request", side_effect=_workday_mock(25, report_total=False)):
        jobs, complete, _ = await conn.fetch_jobs(max_pages=5)
    assert len(jobs) == 25
    assert complete is False


@pytest.mark.asyncio
async def test_workday_row_cap_is_incomplete():
    conn = _workday_connector()
    with patch.object(conn.client, "request", side_effect=_workday_mock(500)):
        jobs, complete, _ = await conn.fetch_jobs(max_pages=5)
    assert len(jobs) == 100
    assert complete is False


@pytest.mark.asyncio
async def test_workday_search_slice_is_never_a_complete_catalog():
    conn = _workday_connector(search_text="Engineer")
    with patch.object(conn.client, "request", side_effect=_workday_mock(10)):
        jobs, complete, _ = await conn.fetch_jobs(max_pages=5)
    assert len(jobs) == 10
    assert complete is False


# ---------------------------------------------------------------------------
# Reconciler
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_demo_jobs_survive_live_syncs(session: AsyncSession):
    source = await session.get(Source, "epic_greenhouse")
    for i in range(10):
        session.add(_job(f"epic_greenhouse:demo-{i}", "epic_greenhouse", f"Demo Engine Programmer {i}", is_demo=True))
    await session.commit()

    reconciler = SafeReconciliationEngine(session, consecutive_missing_threshold=2)
    live = [{"provider_posting_id": "live-1", "title": "Engine Programmer", "raw_html": "<p>C++</p>"}]

    # Ten active demo jobs must not trip the volume-drop guard against a one-job live feed
    run = await reconciler.execute_sync_run(source, live, pagination_complete=True, requests_count=1)
    assert run.is_reconciliation_safe is True

    for _ in range(3):
        await reconciler.execute_sync_run(await session.get(Source, "epic_greenhouse"), live, pagination_complete=True, requests_count=1)

    demo_jobs = (await session.execute(select(Job).where(Job.is_demo == True))).scalars().all()
    assert len(demo_jobs) == 10
    assert all(j.lifecycle_status == LifecycleStatus.ACTIVE.value for j in demo_jobs)
    assert all(j.consecutive_missing_syncs == 0 for j in demo_jobs)


@pytest.mark.asyncio
async def test_unavailable_description_keeps_stored_description_and_skills(session: AsyncSession):
    source = await session.get(Source, "arista_smartrecruiters")
    reconciler = SafeReconciliationEngine(session)
    first = {
        "provider_posting_id": "sr-1",
        "title": "Senior Software Engineer",
        "location": "Santa Clara, us",
        "apply_url": "https://jobs.smartrecruiters.com/AristaNetworks/sr-1",
        "raw_html": "<p>Requirements:</p><p>5+ years of C++ and CUDA experience.</p>",
        "description_status": "available",
    }
    await reconciler.execute_sync_run(source, [first], pagination_complete=True, requests_count=1)

    second = dict(first, title="Staff Software Engineer", location="Remote, us", raw_html="", description_status="unavailable")
    await reconciler.execute_sync_run(await session.get(Source, source.source_id), [second], pagination_complete=False, requests_count=1)

    job = (await session.execute(
        select(Job).options(selectinload(Job.snapshots), selectinload(Job.skills)).where(Job.job_id == "arista_smartrecruiters:sr-1")
    )).scalar_one()
    assert "C++" in job.normalized_description
    assert len(job.snapshots) == 1
    assert {s.skill_id for s in job.latest_skills} == {"cpp", "cuda"}
    assert job.required_yoe == 5
    # Metadata still follows the live posting
    assert job.title == "Staff Software Engineer"
    assert job.seniority == "staff"
    assert job.location == "Remote, us"
    assert job.work_arrangement == "remote"


@pytest.mark.asyncio
async def test_reobservation_updates_posting_fields_and_timestamps(session: AsyncSession):
    source = await session.get(Source, "epic_greenhouse")
    reconciler = SafeReconciliationEngine(session)
    posting = {
        "provider_posting_id": "gh-1",
        "title": "Gameplay Programmer",
        "department": "Gameplay",
        "location": "",
        "apply_url": "https://boards.greenhouse.io/epicgames/jobs/1",
        "source_created_at": "2026-09-01T10:00:00Z",
        "source_updated_at": "2026-09-05T10:00:00Z",
        "raw_html": "<p>C++ gameplay. Salary range: $120,000 - $160,000 USD</p>",
    }
    await reconciler.execute_sync_run(source, [posting], pagination_complete=True, requests_count=1)
    job = await session.get(Job, "epic_greenhouse:gh-1")
    assert job.location == "Location not listed"
    assert job.work_arrangement == "unknown"
    assert job.salary_min == 120000 and job.salary_max == 160000 and job.salary_currency == "USD"
    assert parse_provider_timestamp(job.source_created_at.isoformat()) == datetime(2026, 9, 1, 10, tzinfo=timezone.utc)

    updated = dict(
        posting,
        title="Senior Gameplay Programmer",
        department="Core Gameplay",
        location="Cary, NC (Hybrid)",
        apply_url="https://boards.greenhouse.io/epicgames/jobs/1?v=2",
        source_updated_at="2026-10-01T00:00:00Z",
    )
    await reconciler.execute_sync_run(await session.get(Source, "epic_greenhouse"), [updated], pagination_complete=True, requests_count=1)
    await session.refresh(job)
    assert job.title == "Senior Gameplay Programmer"
    assert job.seniority == "senior"
    assert job.department == "Core Gameplay"
    assert job.location == "Cary, NC (Hybrid)"
    assert job.work_arrangement == "hybrid"
    assert job.apply_url.endswith("?v=2")
    assert job.source_updated_at.replace(tzinfo=timezone.utc) == datetime(2026, 10, 1, tzinfo=timezone.utc)

    changes = (await session.execute(
        select(JobFieldChangeEvent.field_name).where(JobFieldChangeEvent.job_id == job.job_id)
    )).scalars().all()
    assert {"title", "department", "location", "work_arrangement", "apply_url"} <= set(changes)


# ---------------------------------------------------------------------------
# API filters
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def filter_jobs(session: AsyncSession):
    now = datetime.now(timezone.utc)
    session.add_all([
        _job("epic_greenhouse:1", "epic_greenhouse", "Senior Gameplay Programmer", seniority="senior",
             salary_min=150000, salary_max=180000, salary_currency="USD", required_yoe=5,
             location="Cary, NC", source_created_at=now - timedelta(days=1), source_updated_at=now - timedelta(days=20),
             first_seen_at=now - timedelta(days=30), last_seen_at=now - timedelta(days=30)),
        _job("rockstar_greenhouse:2", "rockstar_greenhouse", "Principal Engine Programmer", seniority="principal",
             salary_min=90000, salary_max=95000, salary_currency="GBP", required_yoe=10,
             location="Edinburgh, UK", source_created_at=now - timedelta(days=10), source_updated_at=now - timedelta(days=2),
             first_seen_at=now - timedelta(days=1), last_seen_at=now),
        _job("roblox_greenhouse:3", "roblox_greenhouse", "Software Engineer, C++ Runtime",
             location="Casablanca, Morocco", first_seen_at=now - timedelta(days=5), last_seen_at=now),
        _job("nvidia_workday:4", "nvidia_workday", "Software Engineering Intern", seniority="intern",
             canonical_category="Silicon & AI", location="Toronto, Ukraine-Office", required_yoe=0),
    ])
    await session.commit()


@pytest.mark.asyncio
async def test_company_filter_uses_exact_ids(client, filter_jobs):
    resp = await client.get("/api/jobs?company=epicgames,rockstar")
    assert {j["job_id"] for j in resp.json()["jobs"]} == {"epic_greenhouse:1", "rockstar_greenhouse:2"}
    # "rock" is a substring of a name/id, not an id
    assert (await client.get("/api/jobs?company=rock")).json()["total_count"] == 0


@pytest.mark.asyncio
async def test_seniority_filter(client, filter_jobs):
    resp = await client.get("/api/jobs?seniority=senior,principal")
    assert {j["job_id"] for j in resp.json()["jobs"]} == {"epic_greenhouse:1", "rockstar_greenhouse:2"}
    unspecified = await client.get("/api/jobs?seniority=unspecified")
    assert [j["job_id"] for j in unspecified.json()["jobs"]] == ["roblox_greenhouse:3"]
    assert (await client.get("/api/jobs?seniority=wizard")).status_code == 400


@pytest.mark.asyncio
async def test_pay_band_filter_and_card_fields(client, filter_jobs):
    resp = await client.get("/api/jobs?pay_band=150_200k")
    jobs = resp.json()["jobs"]
    assert [j["job_id"] for j in jobs] == ["epic_greenhouse:1"]
    assert jobs[0]["salary_currency"] == "USD"
    under = await client.get("/api/jobs?pay_band=under_100k")
    assert [j["job_id"] for j in under.json()["jobs"]] == ["rockstar_greenhouse:2"]
    unknown = await client.get("/api/jobs?pay_band=unknown")
    assert {j["job_id"] for j in unknown.json()["jobs"]} == {"roblox_greenhouse:3", "nvidia_workday:4"}


@pytest.mark.asyncio
async def test_location_presets_use_word_boundaries(client, filter_jobs):
    resp = await client.get("/api/jobs?location=US+%2F+EU")
    ids = {j["job_id"] for j in resp.json()["jobs"]}
    assert ids == {"epic_greenhouse:1", "rockstar_greenhouse:2"}  # not Casablanca (%ca%) or Ukraine (%uk%)


@pytest.mark.asyncio
async def test_cpp_job_is_not_every_role_focus_track(client, filter_jobs, session: AsyncSession):
    session.add(JobSkillEvidence(job_id="roblox_greenhouse:3", skill_id="cpp", requirement_type="required", evidence_text="C++"))
    await session.commit()
    for track in ["AI NPCs & Game AI", "Physics & Simulation", "Edge AI & Embedded ECE"]:
        resp = await client.get("/api/jobs", params={"role_focus": track})
        assert "roblox_greenhouse:3" not in {j["job_id"] for j in resp.json()["jobs"]}, track
    resp = await client.get("/api/jobs", params={"role_focus": "Systems / C++"})
    assert "roblox_greenhouse:3" in {j["job_id"] for j in resp.json()["jobs"]}


@pytest.mark.asyncio
async def test_sorting_uses_provider_timestamps(client, filter_jobs):
    posted = (await client.get("/api/jobs?sort_by=recently_posted")).json()["jobs"]
    assert [j["job_id"] for j in posted[:2]] == ["epic_greenhouse:1", "rockstar_greenhouse:2"]
    updated = (await client.get("/api/jobs?sort_by=recently_updated")).json()["jobs"]
    # Rockstar was updated by the provider more recently, even though Epic's last_seen is older
    assert [j["job_id"] for j in updated[:2]] == ["rockstar_greenhouse:2", "epic_greenhouse:1"]


@pytest.mark.asyncio
async def test_pager_contract(client, filter_jobs):
    pages = []
    for page in (1, 2, 3):
        data = (await client.get(f"/api/jobs?page={page}&page_size=2&sort_by=title_asc")).json()
        assert data["total_count"] == 4
        assert data["total_pages"] == 2
        assert data["page"] == page
        pages.append([j["job_id"] for j in data["jobs"]])
    assert len(pages[0]) == 2 and len(pages[1]) == 2
    assert not set(pages[0]) & set(pages[1])
    assert pages[2] == []


@pytest.mark.asyncio
async def test_sector_counts_follow_the_same_filters(client, filter_jobs):
    data = (await client.get("/api/jobs?company=nvidia&category=Game+Studio")).json()
    assert data["total_count"] == 0
    # Sector counts ignore only the sector filter
    assert data["sector_counts"] == {"Silicon & AI": 1, "All Sectors": 1}
    data = (await client.get("/api/jobs?seniority=senior")).json()
    assert data["sector_counts"]["All Sectors"] == 1


# ---------------------------------------------------------------------------
# Skills and candidate profile
# ---------------------------------------------------------------------------
def test_cpp_and_csharp_skill_aliases():
    assert resolve_skill("C++")["skill_id"] == "cpp"
    assert resolve_skill("c#")["skill_id"] == "csharp"
    assert resolve_skill("PyTorch")["skill_id"] == "pytorch"
    assert resolve_skill("k8s")["skill_id"] == "kubernetes"
    assert resolve_skill("klingon") is None


@pytest.mark.asyncio
async def test_skill_resolve_endpoint_and_unknown_rejection(client, session: AsyncSession):
    assert (await client.get("/api/skills/resolve", params={"q": "C++"})).json()["skill_id"] == "cpp"
    assert (await client.get("/api/skills/resolve", params={"q": "klingon"})).status_code == 404

    bad = await client.put("/api/candidate/profile", json={"name": "Me", "skills": [{"skill_id": "c__"}]})
    assert bad.status_code == 400


@pytest.mark.asyncio
async def test_profile_save_keeps_years_unless_sent(client, session: AsyncSession):
    ok = await client.put("/api/candidate/profile", json={"name": "Me", "overall_yoe": 4.5, "skills": [{"skill_id": "cpp"}]})
    assert ok.status_code == 200
    ok = await client.put("/api/candidate/profile", json={"name": "Me", "skills": [{"skill_id": "cpp"}, {"skill_id": "cuda"}]})
    assert ok.status_code == 200
    profile = (await client.get("/api/candidate/profile")).json()
    assert profile["overall_yoe"] == 4.5
    assert {s["skill_id"] for s in profile["skills"]} == {"cpp", "cuda"}


@pytest.mark.asyncio
async def test_one_skill_away_reports_missing_preferred_skill(session: AsyncSession):
    session.add(_job("epic_greenhouse:gap", "epic_greenhouse", "Engine Programmer"))
    session.add(JobSkillEvidence(job_id="epic_greenhouse:gap", skill_id="cpp", requirement_type="required", evidence_text="C++ required"))
    session.add(JobSkillEvidence(job_id="epic_greenhouse:gap", skill_id="cuda", requirement_type="preferred", evidence_text="CUDA is a plus"))
    cand = await session.get(CandidateProfile, "default")
    cand.overall_yoe = 3
    session.add(CandidateSkillEvidence(candidate_id="default", skill_id="cpp"))
    await session.commit()

    result = await GapAnalyzerService(session).analyze_candidate_gap()
    role = next(r for r in result["one_skill_away_roles"] if r["job_id"] == "epic_greenhouse:gap")
    assert role["missing_required"] == []
    assert role["one_skill_gap"]["skill_id"] == "cuda"
    assert role["one_skill_gap"]["requirement_type"] == "preferred"


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------
async def _add_job_with_snapshot(session, job_id, *, is_demo, first_seen, observed, skill="cpp"):
    session.add(_job(job_id, "epic_greenhouse", "Engine Programmer", is_demo=is_demo, first_seen_at=first_seen, last_seen_at=datetime.now(timezone.utc)))
    await session.flush()
    snap = JobSnapshot(job_id=job_id, observed_at=observed, raw_payload_json="{}", normalized_text="", description_hash="h")
    session.add(snap)
    await session.flush()
    job = await session.get(Job, job_id)
    job.latest_snapshot_id = snap.snapshot_id
    session.add(JobSkillEvidence(job_id=job_id, snapshot_id=snap.snapshot_id, skill_id=skill, requirement_type="required", evidence_text=skill))


@pytest.mark.asyncio
async def test_telemetry_delta_needs_live_prior_window(session: AsyncSession):
    old = datetime.now(timezone.utc) - timedelta(days=45)
    for i in range(10):
        await _add_job_with_snapshot(session, f"epic_greenhouse:demo-old-{i}", is_demo=True, first_seen=old, observed=old)
    await session.commit()

    result = await TelemetryEngine(session).get_market_telemetry(include_demo=True)
    assert result["has_prior_window"] is False  # demo history does not count as a prior window
    assert all(item["period_over_period_delta_pct"] is None for item in result["skills_telemetry"])

    for i in range(10):
        await _add_job_with_snapshot(session, f"epic_greenhouse:live-old-{i}", is_demo=False, first_seen=old, observed=old)
    await session.commit()
    result = await TelemetryEngine(session).get_market_telemetry()
    assert result["has_prior_window"] is True
    assert result["prior_window_jobs"] == 10
    cpp = next(item for item in result["skills_telemetry"] if item["skill_id"] == "cpp")
    assert cpp["period_over_period_delta_pct"] == 0.0


# ---------------------------------------------------------------------------
# Sources, seeding, and sync safety
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_startup_does_not_reenable_sources_and_badges_no_public_feed():
    test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    await init_db(custom_engine=test_engine)
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        (await s.get(Source, "epic_greenhouse")).enabled = False
        s.add(Source(source_id="ea_greenhouse", company_id="ea", provider_type="greenhouse",
                     base_url="https://boards-api.greenhouse.io", board_token="ea",
                     allowed_hosts='["boards-api.greenhouse.io"]', enabled=False))
        await s.commit()

    await init_db(custom_engine=test_engine)
    async with factory() as s:
        assert (await s.get(Source, "epic_greenhouse")).enabled is False
        assert await s.get(Source, "ea_greenhouse") is None
        assert (await s.get(Source, "naughtydog_greenhouse")).board_token == "naughtydog"
        assert (await s.get(Source, "playstation_greenhouse")).board_token == "sonyinteractiveentertainmentglobal"

        async def override_get_db():
            yield s
        app.dependency_overrides[get_db_session] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            feeds = {src["source_id"]: src["feed_status"] for src in (await ac.get("/api/sources")).json()}
            companies = {c["company_id"]: c for c in (await ac.get("/api/companies")).json()}
            health = (await ac.get("/api/health")).json()
        app.dependency_overrides.clear()

    assert feeds["ea_gr8people"] == feeds["qualcomm_eightfold"] == feeds["g42_phenom"] == "no_public_feed"
    assert feeds["epic_greenhouse"] == "disabled"
    assert companies["ea"]["feed_status"] == "no_public_feed"
    assert companies["nvidia"]["domain"] == "nvidia.com"
    assert not {"ea_gr8people", "qualcomm_eightfold", "g42_phenom"} & set(health["degraded_sources"])
    await test_engine.dispose()


@pytest_asyncio.fixture
async def sync_env(tmp_path, monkeypatch):
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'sync.db'}", echo=False)
    await init_db(custom_engine=test_engine)
    factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        for src in (await s.execute(select(Source))).scalars().all():
            src.enabled = src.source_id in ("epic_greenhouse", "rockstar_greenhouse")
        await s.commit()
    monkeypatch.setattr(routes, "async_session_factory", factory)
    monkeypatch.setattr(routes, "GLOBAL_SYNC_STATE", routes.GlobalSyncState())
    monkeypatch.setattr(routes, "SYNC_LOCK", asyncio.Lock())
    monkeypatch.setattr(routes, "SOURCE_LOCKS", {})
    yield factory
    await test_engine.dispose()


@pytest.mark.asyncio
async def test_full_sync_holds_lock_and_never_sticks_active(sync_env):
    async def boom(cfg):
        raise RuntimeError("upstream down")

    lock_seen = {}
    real_task = routes._run_sync_task

    async def spy_task(**kwargs):
        lock_seen["held"] = routes.SYNC_LOCK.locked()
        await real_task(**kwargs)

    with patch.object(routes.ConnectorManager, "fetch_source_jobs", side_effect=boom), \
         patch.object(routes, "_run_sync_task", spy_task):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            async def override_get_db():
                async with sync_env() as s:
                    yield s
            app.dependency_overrides[get_db_session] = override_get_db
            resp = await ac.post("/api/sync")
            app.dependency_overrides.clear()

    assert resp.json()["status"] == "triggered"
    assert lock_seen["held"] is True
    state = routes.GLOBAL_SYNC_STATE
    assert state.is_active is False
    assert state.status == "partial"
    assert "upstream down" in state.last_error
    assert not routes.SYNC_LOCK.locked()

    # A crash before any source runs still clears the active flag and the lock
    def broken_factory():
        raise RuntimeError("db unavailable")
    with patch.object(routes, "async_session_factory", broken_factory):
        routes.GLOBAL_SYNC_STATE.current_run_id = "crash-run"
        await routes.SYNC_LOCK.acquire()
        await routes._run_sync_task(run_id="crash-run", held_lock=routes.SYNC_LOCK)
    assert state.is_active is False and state.status == "failed"
    assert not routes.SYNC_LOCK.locked()


@pytest.mark.asyncio
async def test_single_source_sync_does_not_reset_running_full_sync(sync_env):
    state = routes.GLOBAL_SYNC_STATE
    state.current_run_id = "full-run"
    state.is_active = True
    state.status = "running"

    source_lock = routes.SOURCE_LOCKS.setdefault("epic_greenhouse", asyncio.Lock())
    await source_lock.acquire()
    with patch.object(routes.ConnectorManager, "fetch_source_jobs", return_value=([], True, 1)):
        await routes._run_sync_task(run_id="single-run", target_source_id="epic_greenhouse", held_lock=source_lock)

    assert state.current_run_id == "full-run"
    assert state.is_active is True
    assert state.status == "running"
    assert not source_lock.locked()

    # While a full sync holds SYNC_LOCK, a single-source trigger is refused instead of racing it
    await routes.SYNC_LOCK.acquire()
    try:
        async def override_get_db():
            async with sync_env() as s:
                yield s
        app.dependency_overrides[get_db_session] = override_get_db
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/api/sync", params={"source_id": "epic_greenhouse"})
            skipped = await ac.post("/api/sync", params={"source_id": "qualcomm_eightfold"})
        app.dependency_overrides.clear()
    finally:
        routes.SYNC_LOCK.release()
    assert resp.json()["status"] == "in_progress"
    assert skipped.json()["status"] == "skipped"
    assert state.current_run_id == "full-run"
