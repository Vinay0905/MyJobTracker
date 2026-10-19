# DevRadar - Known Limitations & Architectural Tradeoffs

This document outlines architectural boundaries, external ATS provider behaviors, and operational constraints in DevRadar.

---

## 1. ATS Connector & Provider Behaviors

### A. Workday CXS APIs (e.g. NVIDIA)
- **Tenant Idiosyncrasies:** Workday deployments differ between tenants. The CXS JSON endpoint (`/wday/cxs/.../jobs`) is standard for public external sites, but query facets, offset limits, and description detail payload shapes can vary.
- **Deep Pagination Truncation:** Workday typically caps maximum offset results on broad searches. The connector uses explicit search tokens (`searchText: "Engineer"`) to stay within stable pagination windows.
- **Search slices never close jobs:** A `searchText` result, a missing `total`, or hitting the 100-row page cap marks the run `pagination_complete=False`, so postings outside the fetched window are never moved toward closure.
- **Rate Throttling:** Workday returns HTTP 429 when concurrency exceeds tenant thresholds. DevRadar applies per-host concurrency semaphores ($N=2$) and exponential backoff with jitter.

### B. Greenhouse Public Board APIs (e.g. Epic Games, Careem)
- **Content Payload Size:** Using `?content=true` fetches full HTML descriptions for all positions in a single atomic response. For enterprise studios with 500+ listings, payload sizes may exceed 5MB.
- **Atomic Completeness:** Greenhouse returns the entire active catalog atomically. An omission in a 200 OK response is considered a verified candidate for job closure.

### C. Anti-Bot and Cloudflare WAF Portals (No Evasion Rule)
- In strict compliance with the **No Evasion Rule**, DevRadar **never** implements CAPTCHA bypasses, fingerprint spoofing, or headless stealth browser injections.
- If a portal deploys aggressive anti-bot challenges (e.g. Cloudflare Turnstile / Akamai), the connector marks the source status as `DEGRADED` in `sources` and records the error in `sync_runs`.
- Degraded status triggers an automated warning banner across telemetry and UI feeds to prevent missing data from masquerading as declining skill demand.

### D. Employers with no public feed (EA, Qualcomm, G42)
- **EA** uses GR8 People (`ea.gr8people.com`). A plain unauthenticated `GET https://ea.gr8people.com/jobs` returned CloudFront HTTP 403 ("Request forbidden by administrative rules"), so there is no public JSON feed and `ea_gr8people` stays disabled.
- **Qualcomm** (Eightfold) and **G42** (Phenom) returned 403 and have no connector.
- These sources are badged "No public feed" in the UI and are not counted as sync failures. `--seed-demo` skips their fixtures unless `--include-unsupported` is passed; any demo cards appear only in Demo mode and are labeled DEMO.

---

## 2. Skill & Experience Extraction Pipeline

### A. Deterministic Regex vs LLM Extraction
- **Zero Latency:** Deterministic extraction executes in $<1$ ms per posting, eliminating API costs and rate limit risks.
- **Edge Cases in Unstructured Text:** Novel acronyms or non-standard syntax (e.g., *"experience with our proprietary in-house engine"*) will not be attributed to known taxonomy entities unless mapped in `TAXONOMY_SPECS`.
- **Negation Range:** Scoped negation detection evaluates within the sentence unit. Complex multi-clause paragraphs containing both required and optional qualifications require clean sentence boundaries.

### B. Experience Years Ambiguity
- When postings state *"3 to 5 years experience in C++ and/or relevant degrees"*, the extractor captures `min_years=3` and `max_years=5` scoped under `skill_specific`.
- Postings with no explicit numeric year statements are classified as `None` rather than assuming arbitrary defaults.

---

## 3. Database Scaling (SQLite to PostgreSQL)

- **Development Storage:** Local SQLite using `aiosqlite` is zero-config, single-file, and ideal for local developer telemetry.
- **Production Concurrency:** SQLite does not support high-concurrency parallel write transactions. To transition to PostgreSQL in production:
  1. Set `DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/devradar` in `.env`.
  2. All SQLAlchemy 2.0 models use standard types and ANSI-compatible indexes and will function with zero code changes.
