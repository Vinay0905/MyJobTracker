import asyncio
import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from collections import Counter
from fetchers import TARGETS, fetch_greenhouse_jobs, fetch_workday_jobs
from database import init_db, save_jobs, get_all_jobs

app = FastAPI(title="Career Radar & Skill Analyzer API", version="1.0.0")

# Allow future Stitch/Antigravity frontend to call this API locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for fast querying backed by SQLite database
JOBS_CACHE = []

@app.on_event("startup")
def on_startup():
    """Initializes database schema and restores existing jobs into memory."""
    global JOBS_CACHE
    init_db()
    JOBS_CACHE = get_all_jobs()

@app.post("/api/sync")
async def sync_all_career_pages():
    """Fetches live open engineering roles and extracts skills from all target companies."""
    global JOBS_CACHE
    async with httpx.AsyncClient(follow_redirects=True) as client:
        tasks = []
        for target in TARGETS:
            if target["type"] == "greenhouse":
                tasks.append(fetch_greenhouse_jobs(client, target))
            elif target["type"] == "workday":
                tasks.append(fetch_workday_jobs(client, target))
        
        nested_results = await asyncio.gather(*tasks, return_exceptions=True)
        
    flat_jobs = []
    for res in nested_results:
        if isinstance(res, list):
            flat_jobs.extend(res)
            
    JOBS_CACHE = flat_jobs
    save_jobs(JOBS_CACHE)
    return {"status": "synced", "total_engineering_jobs": len(JOBS_CACHE)}


@app.get("/api/jobs")
def get_jobs(
    company: Optional[str] = Query(None, description="Filter by company name (e.g. NVIDIA, Rockstar)"),
    category: Optional[str] = Query(None, description="Game Studio | Silicon & AI | UAE & Middle East"),
    skill: Optional[str] = Query(None, description="Filter by required skill (e.g. C++, CUDA, Docker)"),
    location: Optional[str] = Query(None, description="Filter by city/country (e.g. Dubai, Abu Dhabi, India)")
):
    """Returns filtered engineering/deployment jobs with their extracted required skills."""
    filtered = JOBS_CACHE
    if company:
        filtered = [j for j in filtered if company.lower() in j["company"].lower()]
    if category:
        filtered = [j for j in filtered if category.lower() in j["category"].lower()]
    if skill:
        filtered = [j for j in filtered if any(skill.lower() == s.lower() for s in j["required_skills"])]
    if location:
        filtered = [j for j in filtered if location.lower() in j["location"].lower()]

    return {"count": len(filtered), "jobs": filtered}


@app.get("/api/skills/top")
def get_top_requested_skills(category: Optional[str] = None):
    """Shows which technical skills companies are asking for the most right now."""
    pool = [j for j in JOBS_CACHE if not category or category.lower() in j["category"].lower()]
    counter = Counter()
    for job in pool:
        counter.update(job["required_skills"])
    
    return {
        "total_jobs_analyzed": len(pool),
        "top_skills": [{"skill": k, "job_count": v} for k, v in counter.most_common(20)]
    }
