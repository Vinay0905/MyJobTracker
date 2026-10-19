import sqlite3
import json
from typing import List, Dict, Optional

DB_NAME = "jobs.db"

def init_db(db_path: str = DB_NAME):
    """Initializes the SQLite database schema."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            company TEXT,
            category TEXT,
            title TEXT,
            location TEXT,
            department TEXT,
            required_skills TEXT,
            min_experience_years INTEGER,
            apply_url TEXT,
            updated_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_jobs(jobs: List[Dict], db_path: str = DB_NAME):
    """Inserts or updates jobs in the SQLite database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for job in jobs:
        cursor.execute("""
            INSERT OR REPLACE INTO jobs (
                job_id, company, category, title, location,
                department, required_skills, min_experience_years, apply_url, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.get("job_id"),
            job.get("company"),
            job.get("category"),
            job.get("title"),
            job.get("location"),
            job.get("department"),
            json.dumps(job.get("required_skills", [])),
            job.get("min_experience_years"),
            job.get("apply_url"),
            job.get("updated_at")
        ))
    conn.commit()
    conn.close()

def get_all_jobs(db_path: str = DB_NAME) -> List[Dict]:
    """Retrieves all jobs stored in the SQLite database."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs")
    rows = cursor.fetchall()
    conn.close()

    jobs = []
    for row in rows:
        item = dict(row)
        item["required_skills"] = json.loads(item["required_skills"]) if item["required_skills"] else []
        jobs.append(item)
    return jobs
