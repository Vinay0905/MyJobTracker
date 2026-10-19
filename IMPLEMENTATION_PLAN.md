# DevRadar Implementation Plan & Execution Milestones

## Phase 1: Architecture & Foundation
- [x] Inspect `design/DESIGN.md`, `design/code.html`, `design/screen.png`.
- [x] Create `ARCHITECTURE.md`.
- [ ] Create `.env.example`.
- [ ] Build normalized SQLAlchemy models (`backend/db/models.py`).
- [ ] Build DB connection session factory & migration initializer (`backend/db/session.py`).
- [ ] Write unit tests for relational schema and constraints (`tests/test_db_models.py`).

## Phase 2 & 3: Resilient Connectors & Safe Reconciliation Engine
- [ ] Build robust HTTP client with retries, exponential backoff, jitter & per-host rate limits (`backend/connectors/base.py`).
- [ ] Implement Greenhouse connector with pagination & detail parsing (`backend/connectors/greenhouse.py`).
- [ ] Implement Workday CXS connector with tenant validation & limit guards (`backend/connectors/workday.py`).
- [ ] Implement Source Registry & Manager (`backend/connectors/manager.py`).
- [ ] Build Safe Reconciliation State Machine (`ACTIVE -> MISSING_CANDIDATE -> CLOSED`) (`backend/services/reconciler.py`).
- [ ] Write `pytest` test suite:
  - Verify sync idempotency.
  - Verify failed / incomplete sync never closes jobs (`is_reconciliation_safe == False`).
  - Verify resurrected jobs return to `ACTIVE` and log lifecycle event.

## Phase 4: Hybrid Skill & Experience Extraction Pipeline
- [ ] Implement HTML normalization & section segmenter using `selectolax` (`backend/extraction/normalizer.py`).
- [ ] Implement curated, token-aware, negation-aware regex taxonomy (`backend/extraction/taxonomy.py`).
- [ ] Implement multi-scope experience extractor (`backend/extraction/experience.py`).
- [ ] Implement strict engineering role inclusion/exclusion filter (`backend/extraction/filter.py`).
- [ ] Build labeled evaluation fixtures (`tests/fixtures/eval_descriptions.json`).
- [ ] Write comprehensive unit tests for adversarial cases (`tests/test_extraction.py`):
  - `C` vs `C++` vs `C#`.
  - `Go` (programming language vs English verb).
  - Negations ("CUDA is not required").
  - Preferred vs Required sections.
  - Overall YOE vs Skill-specific YOE.

## Phase 5: Telemetry, Gap Analyzer & FastAPI REST Surface
- [ ] Build 1-Skill Away Gap Analyzer (`backend/services/gap_analyzer.py`).
- [ ] Build Market Telemetry Engine (`backend/services/telemetry.py`).
- [ ] Implement FastAPI Pydantic schemas (`backend/api/schemas.py`).
- [ ] Implement FastAPI routes:
  - `GET /api/health`
  - `GET /api/jobs` (paginated, filtered)
  - `GET /api/jobs/{job_id}` (full evidence and audit trails)
  - `GET /api/skills/top` & `GET /api/telemetry/skills`
  - `GET /api/sources`, `GET /api/sync/runs`, `POST /api/sync`
  - `GET /api/candidate/profile`, `PUT /api/candidate/profile`, `GET /api/candidate/gap-analysis`
- [ ] Write `pytest` test suite for API endpoints (`tests/test_api.py`).

## Phase 6 & 7: Modular Frontend in `frontend/` (Vite + React + TypeScript + Tailwind)
- [ ] Scaffold `frontend/` directory structure with Vite + React + TS.
- [ ] Configure `tailwind.config.js` and `src/index.css` matching `design/DESIGN.md`.
- [ ] Implement full TypeScript API models in `frontend/src/types/api.ts`.
- [ ] Implement typed API client in `frontend/src/api/client.ts`.
- [ ] Build modular components:
  - Navigation & Top Bar with live sync and status beacon.
  - Left Filter Sidebar with sector pills and role checkboxes.
  - Job Radar Feed & Job Cards with required/preferred chips.
  - Slide-over Job Detail Drawer showing cited sentence quotes.
  - Market Telemetry view with 30d comparison & degraded source banners.
  - "1-Skill Away" Candidate Gap Analyzer view.
  - Source Health & Sync History views.
- [ ] Run `npm run build` to verify zero TypeScript errors.

## Phase 8: Hardening, Documentation & Verification
- [ ] Create `README.md` with startup instructions.
- [ ] Create `KNOWN_LIMITATIONS.md` outlining provider constraints.
- [ ] Run test suite verifying 100% pass rate.
- [ ] Verify frontend and backend end-to-end.
