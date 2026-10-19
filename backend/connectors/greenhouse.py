from typing import List, Dict, Any, Tuple
import html
import json
import logging
from backend.connectors.base import ResilientHTTPClient

logger = logging.getLogger("devradar.connectors.greenhouse")

class GreenhouseConnector:
    """
    Direct JSON API Connector for Greenhouse Job Boards.
    Endpoint: https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
    """
    def __init__(self, source_config: Dict[str, Any]):
        self.source_id = source_config["source_id"]
        self.board_token = source_config["board_token"]
        self.base_url = source_config.get("base_url", "https://boards-api.greenhouse.io")
        allowed_hosts = json.loads(source_config.get("allowed_hosts", "[]"))
        if not allowed_hosts:
            allowed_hosts = ["boards-api.greenhouse.io", "boards.greenhouse.io"]

        self.client = ResilientHTTPClient(
            allowed_hosts=allowed_hosts,
            concurrency_limit=source_config.get("concurrency_limit", 3),
            timeout=source_config.get("timeout_seconds", 15.0),
        )

    async def fetch_jobs(self) -> Tuple[List[Dict[str, Any]], bool, int]:
        """
        Pulls all active job postings with content payload.
        Returns: (jobs_list, pagination_complete, request_count)
        """
        url = f"{self.base_url}/v1/boards/{self.board_token}/jobs?content=true"
        resp = await self.client.request("GET", url)
        
        if resp.status_code != 200:
            logger.error(f"Greenhouse board {self.board_token} returned HTTP {resp.status_code}")
            return [], False, 1

        data = resp.json()
        if not isinstance(data, dict) or "jobs" not in data:
            logger.error(f"Greenhouse board {self.board_token} response invalid: missing 'jobs' key")
            return [], False, 1

        raw_jobs = data.get("jobs", [])
        results: List[Dict[str, Any]] = []

        for item in raw_jobs:
            posting_id = str(item.get("id"))
            depts = ", ".join([d.get("name", "") for d in item.get("departments", []) if d.get("name")])
            offices = ", ".join([o.get("name", "") for o in item.get("offices", []) if o.get("name")])
            location_str = (item.get("location") or {}).get("name") or offices or ""

            results.append({
                "provider_posting_id": posting_id,
                "requisition_id": item.get("requisition_id"),
                "internal_job_id": str(item.get("internal_job_id")) if item.get("internal_job_id") else None,
                "title": item.get("title", "").strip(),
                "department": depts,
                "location": location_str,
                "apply_url": item.get("absolute_url") or f"https://boards.greenhouse.io/{self.board_token}/jobs/{posting_id}",
                "source_url": item.get("absolute_url"),
                "source_created_at": item.get("first_published"),
                "source_updated_at": item.get("updated_at"),
                # Greenhouse returns `content` as entity-escaped HTML.
                "raw_html": html.unescape(item.get("content") or ""),
            })

        # Greenhouse single-endpoint pull is atomic and complete
        return results, True, 1
