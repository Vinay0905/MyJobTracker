import httpx
from typing import List, Dict
from extractor import is_engineering_or_deployment_role, extract_skills_and_exp

# Sample Target Registry (Add more studios, Silicon, or UAE companies anytime)
TARGETS = [
    {
        "company": "NVIDIA",
        "category": "Silicon & AI",
        "region": "Global / India / US / Middle East",
        "type": "workday",
        "base_url": "https://nvidia.wd5.myworkdayjobs.com",
        "endpoint": "/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs",
        "public_url": "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
    },
    {
        "company": "Epic Games",
        "category": "Game Studio",
        "region": "Global",
        "type": "greenhouse",
        "board_token": "epicgames"
    },
    {
        "company": "Careem (UAE)",
        "category": "UAE & Middle East",
        "region": "UAE / Middle East",
        "type": "greenhouse",
        "board_token": "careem"
    }
]

async def fetch_greenhouse_jobs(client: httpx.AsyncClient, target: Dict) -> List[Dict]:
    """Pulls open positions + descriptions directly from a company's Greenhouse JSON API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{target['board_token']}/jobs?content=true"
    resp = await client.get(url, timeout=15.0)
    if resp.status_code != 200:
        return []

    data = resp.json().get("jobs", [])
    results = []

    for job in data:
        title = job.get("title", "")
        depts = ", ".join([d.get("name", "") for d in job.get("departments", [])])
        
        if not is_engineering_or_deployment_role(title, depts):
            continue

        content_html = job.get("content", "")
        extracted = extract_skills_and_exp(content_html)

        results.append({
            "job_id": f"gh_{target['board_token']}_{job.get('id')}",
            "company": target["company"],
            "category": target["category"],
            "title": title,
            "location": job.get("location", {}).get("name", "Unknown"),
            "department": depts,
            "required_skills": extracted["skills"],
            "min_experience_years": extracted["min_experience_years"],
            "apply_url": job.get("absolute_url"),
            "updated_at": job.get("updated_at")
        })
    return results


async def fetch_workday_jobs(client: httpx.AsyncClient, target: Dict) -> List[Dict]:
    """Pulls open positions from a company's Workday career page JSON API."""
    url = f"{target['base_url']}{target['endpoint']}"
    payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "Engineer"}
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    resp = await client.post(url, json=payload, headers=headers, timeout=15.0)
    if resp.status_code != 200:
        return []

    postings = resp.json().get("jobPostings", [])
    results = []

    for post in postings:
        title = post.get("title", "")
        if not is_engineering_or_deployment_role(title):
            continue

        ext_path = post.get("externalPath", "")
        detail_url = f"{target['base_url']}/wday/cxs/nvidia/NVIDIAExternalCareerSite{ext_path}"
        
        # Fetch individual job JSON to extract the required skills
        detail_resp = await client.get(detail_url, headers=headers, timeout=10.0)
        desc_html = ""
        if detail_resp.status_code == 200:
            desc_html = detail_resp.json().get("jobPostingInfo", {}).get("jobDescription", "")

        extracted = extract_skills_and_exp(desc_html)

        results.append({
            "job_id": f"wd_{target['company']}_{post.get('bulletFields', ['unknown'])[0]}",
            "company": target["company"],
            "category": target["category"],
            "title": title,
            "location": post.get("locationsText", "Multiple Locations"),
            "department": "Engineering",
            "required_skills": extracted["skills"],
            "min_experience_years": extracted["min_experience_years"],
            "apply_url": f"{target['public_url']}{ext_path}",
            "updated_at": post.get("postedOn", "Recent")
        })
    return results
