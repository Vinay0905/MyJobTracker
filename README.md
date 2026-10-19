# MyJobTracker (DevRadar)

Autonomous engineering career radar and market telemetry engine

**DevRadar** is an automated, production-grade telemetry and skill extraction engine designed for software engineers, systems programmers, and AI researchers. It pulls open roles directly from public career APIs of Tier-1 technology companies (NVIDIA, Epic Games, Careem, etc.), filters out non-technical roles, extracts exact required/preferred skills with cited sentence quotes from the job descriptions, safely tracks job lifecycles without data loss, and delivers real-time market trends alongside an interactive **"1-Skill Away"** candidate gap analyzer.

---

## Key Features

1. **Strict Engineering Inclusion & Exclusion:**
   - **Included:** Software, Systems/C++, GPU/CUDA, AI/ML, Compilers, Embedded/RTOS, Distributed Systems, Cloud/DevOps.
   - **Excluded:** HR, Recruiting, Sales, Marketing, Legal, Finance, non-technical 2D/3D Art.
2. **Resilient Public ATS Connectors:**
   - **Greenhouse:** Pulls full posting content, departments, and office locations atomically via public JSON board APIs.
   - **Workday CXS:** Queries external career endpoints with tenant validation and per-host concurrency controls.
   - **SSRF Host Whitelisting:** Prevents malicious outbound requests.
3. **Safe Job Closure State Machine:**
   - Transitions `ACTIVE -> MISSING_CANDIDATE -> CLOSED`.
   - Incomplete syncs or network failures never close active jobs (`is_reconciliation_safe == False`).
   - Automatically resurrects jobs back to `ACTIVE` if re-observed in employer feeds.
4. **Token-Aware & Negation-Aware Skill Extraction:**
   - Accurate disambiguation of `C`, `C++`, `C#`, and `Go` (never matching colloquial English verbs).
   - Scoped negation detection (e.g. *"CUDA is not required"*).
   - Section segmentation (`selectolax`) separating required from preferred qualifications.
5. **"1-Skill Away" Candidate Gap Analyzer:**
   - Evaluates candidate profile against live openings.
   - Highlights high-leverage roles where the candidate is exactly 1 required technical skill away.
   - Decouples learnable technical skill gaps from experience deficits.
6. **Dark Command Center Dashboard:**
   - Built with **Vite + React 18 + TypeScript + Tailwind CSS** matching the exact Linear/Vercel dark-mode palette (`#0f131c` void background, `#181c24` card surfaces, emerald green & electric lavender accents).

---

## Canonical Codebase vs Legacy Stubs

> [!IMPORTANT]
> The active, production-grade application resides exclusively in:
> - **`backend/`** (FastAPI backend, connectors, database models, extraction engine, telemetry)
> - **`frontend/`** (Vite + React 18 + TypeScript + Tailwind CSS dark terminal dashboard)
> 
> Legacy directories (`devradar-ui/` and `job-radar-api/`) are deprecated stubs retained solely for historical migration reference. All active development, scripts, and tests target `backend/` and `frontend/`.

---

## Directory Structure

```text
├── .github/workflows/
│   └── ci.yml                 # Automated CI running backend pytest & frontend Vite build
├── backend/
│   ├── api/
│   │   ├── routes.py          # FastAPI REST endpoints (/api/jobs, /api/companies, /api/sync/status, etc.)
│   │   └── schemas.py         # Pydantic request/response models
│   ├── connectors/
│   │   ├── base.py            # Resilient HTTP client (retries, jitter, SSRF guard)
│   │   ├── greenhouse.py      # Greenhouse JSON board connector (Rockstar Games, Epic Games, Naughty Dog, etc.)
│   │   ├── workday.py         # Workday CXS career portal connector (NVIDIA, etc.)
│   │   ├── ashby.py           # Ashby API connector (Cerebras, etc.)
│   │   └── manager.py         # ATS routing manager
│   ├── db/
│   │   ├── models.py          # Normalized SQLAlchemy 2.0 async models
│   │   └── session.py         # Async session factory, DATABASE_URL env config & authoritative seed data
│   ├── extraction/
│   │   ├── normalizer.py      # HTML tag cleaner & section segmenter
│   │   ├── filter.py          # Strict engineering role filter
│   │   ├── taxonomy.py        # Token & negation-aware skill extractor
│   │   ├── experience.py      # Multi-scope experience requirements parser
│   │   └── pipeline.py        # Unified extraction facade
│   ├── services/
│   │   ├── reconciler.py      # Safe reconciliation & state machine (2-run grace period)
│   │   ├── telemetry.py       # Market skill share % & trend engine
│   │   └── gap_analyzer.py    # 1-Skill Away candidate gap analyzer
│   ├── main.py                # FastAPI application entry point
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/client.ts      # Typed async client with sorting & company support
│   │   ├── types/api.ts       # TypeScript interfaces
│   │   ├── components/
│   │   │   ├── layout/        # TopNavbar & Sidebar (Target Companies filter & sectors)
│   │   │   ├── jobs/          # JobCard (multi-tier logo pipeline) & JobDetailDrawer
│   │   │   ├── constellation/ # Interactive Deep-Tech Skill Dependency Constellation Graph
│   │   │   ├── salary/        # Tech Stack Scarcity Multiplier & UAE Tax-Free Calculator
│   │   │   ├── telemetry/     # SkillTelemetryView
│   │   │   ├── candidate/     # GapAnalyzerView
│   │   │   └── sources/       # SourceHealthView
│   │   ├── utils/audio.ts     # Cyberpunk Web Audio sound synthesizer
│   │   └── App.tsx            # Central state, live polling & keyboard shortcuts
│   ├── package.json
│   ├── tailwind.config.js     # Color Hunt Palette (#790D16, #E5D3AF, #F5EFE1, #AEC4D4)
│   └── vite.config.ts         # Vite dev proxy to :8000
├── tests/
│   ├── fixtures/              # Adversarial test cases
│   ├── test_api.py            # API route integration tests (companies, sync status, 8 sort orders)
│   ├── test_data_trust.py     # Anti-fabrication, zero-hallucination regression tests
│   ├── test_db_models.py      # Relational schema tests
│   ├── test_extraction.py     # Skill & experience extractor tests
│   ├── test_hardening.py      # Snapshot isolation & reconciliation tests
│   └── test_reconciliation.py # Safe closure state machine tests
├── ARCHITECTURE.md            # System architecture & formulation
└── .env.example               # Environment template
```

---

## Running the Application

### 1. Backend (FastAPI)

```bash
# Activate virtual environment
source .venv/bin/activate

# Run test suite
pytest

# Start backend server
python -m backend.main
```
The FastAPI documentation is automatically accessible at `http://127.0.0.1:8000/docs`.

### 2. Frontend (Vite + React + TypeScript)

```bash
cd frontend
npm install
npm run dev
```
Open `http://127.0.0.1:5173` in your browser. All `/api/*` requests will be proxied automatically to `http://127.0.0.1:8000`.
