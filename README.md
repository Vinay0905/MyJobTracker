# DevRadar - Autonomous Engineering Career Radar & Market Telemetry Engine

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

## Directory Structure

```text
├── backend/
│   ├── api/
│   │   ├── routes.py          # FastAPI REST endpoints
│   │   └── schemas.py         # Pydantic request/response models
│   ├── connectors/
│   │   ├── base.py            # Resilient HTTP client (retries, jitter, SSRF guard)
│   │   ├── greenhouse.py      # Greenhouse JSON board connector
│   │   ├── workday.py         # Workday CXS career portal connector
│   │   └── manager.py         # ATS routing manager
│   ├── db/
│   │   ├── models.py          # Normalized SQLAlchemy 2.0 async models
│   │   └── session.py         # Async session factory & seed data
│   ├── extraction/
│   │   ├── normalizer.py      # HTML tag cleaner & section segmenter
│   │   ├── filter.py          # Strict engineering role filter
│   │   ├── taxonomy.py        # Token & negation-aware skill extractor
│   │   ├── experience.py      # Multi-scope experience requirements parser
│   │   └── pipeline.py        # Unified extraction facade
│   ├── services/
│   │   ├── reconciler.py      # Safe reconciliation & state machine
│   │   ├── telemetry.py       # Market skill share % & trend engine
│   │   └── gap_analyzer.py    # 1-Skill Away candidate gap analyzer
│   ├── main.py                # FastAPI application entry point
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/client.ts      # Typed async client
│   │   ├── types/api.ts       # TypeScript interfaces
│   │   ├── components/
│   │   │   ├── layout/        # TopNavbar & Sidebar
│   │   │   ├── jobs/          # JobCard & JobDetailDrawer
│   │   │   ├── telemetry/     # SkillTelemetryView
│   │   │   ├── candidate/     # GapAnalyzerView
│   │   │   └── sources/       # SourceHealthView
│   │   └── App.tsx            # Central state & tab controller
│   ├── package.json
│   └── vite.config.ts         # Vite dev proxy to :8000
├── tests/
│   ├── fixtures/              # Adversarial test cases
│   ├── test_api.py            # API route integration tests
│   ├── test_db_models.py      # Relational schema tests
│   ├── test_extraction.py     # Skill & experience extractor tests
│   └── test_reconciliation.py  # Safe closure state machine tests
├── ARCHITECTURE.md            # System architecture & formulation
├── IMPLEMENTATION_PLAN.md     # Milestones checklist
├── KNOWN_LIMITATIONS.md       # Known provider constraints
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
# MyJobTracker
# MyJobTracker
