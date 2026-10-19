from typing import List, Dict, Any, Tuple, Optional
import json
import logging
from backend.connectors.base import ResilientHTTPClient

logger = logging.getLogger("devradar.connectors.ashby")

class AshbyConnector:
    """
    Public JSON API Connector for Ashby Job Boards.
    Endpoint: https://api.ashbyhq.com/posting-api/job-board/{board_token}
    """
    def __init__(self, source_config: Dict[str, Any]):
        self.source_id = source_config["source_id"]
        self.board_token = source_config["board_token"]
        self.base_url = source_config.get("base_url", "https://api.ashbyhq.com").rstrip("/")
        allowed_hosts = json.loads(source_config.get("allowed_hosts", "[]"))
        if not allowed_hosts:
            allowed_hosts = ["api.ashbyhq.com", "jobs.ashbyhq.com"]

        self.client = ResilientHTTPClient(
            allowed_hosts=allowed_hosts,
            concurrency_limit=source_config.get("concurrency_limit", 2),
            timeout=source_config.get("timeout_seconds", 15.0),
        )

    @staticmethod
    def _annual_salary(compensation: Any) -> Optional[Dict[str, Any]]:
        """Picks the salary component Ashby publishes when includeCompensation=true."""
        if not isinstance(compensation, dict):
            return None
        for comp in compensation.get("summaryComponents") or []:
            if not isinstance(comp, dict) or str(comp.get("compensationType", "")).lower() != "salary":
                continue
            interval = str(comp.get("interval") or "")
            return {
                "min": comp.get("minValue"),
                "max": comp.get("maxValue"),
                "currency": comp.get("currencyCode"),
                "interval": "year" if "YEAR" in interval.upper() else interval,
            }
        return None

    async def fetch_jobs(self) -> Tuple[List[Dict[str, Any]], bool, int]:
        """
        Fetches all active jobs with descriptions from the Ashby board API.
        Returns: (jobs_list, pagination_complete, request_count)
        """
        url = f"{self.base_url}/posting-api/job-board/{self.board_token}?includeCompensation=true"
        headers = {"Accept": "application/json"}
        total_requests = 1

        try:
            resp = await self.client.request("GET", url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Ashby board {self.board_token} returned HTTP {resp.status_code}")
                return [], False, total_requests

            data = resp.json()
            if not isinstance(data, dict) or "jobs" not in data:
                logger.error(f"Ashby response schema invalid: missing 'jobs' key at {url}")
                return [], False, total_requests

            raw_jobs = data.get("jobs", [])
            results: List[Dict[str, Any]] = []

            for item in raw_jobs:
                posting_id = str(item.get("id"))
                title = item.get("title", "").strip()
                dept = item.get("department") or item.get("team") or ""
                loc = item.get("location") or ""
                apply_url = item.get("jobUrl") or f"https://jobs.ashbyhq.com/{self.board_token}/{posting_id}"
                desc_html = item.get("descriptionHtml") or item.get("descriptionPlain") or ""
                arrangement = item.get("workplaceType") or ("remote" if item.get("isRemote") is True else None)

                results.append({
                    "provider_posting_id": posting_id,
                    "requisition_id": item.get("secondaryId"),
                    "title": title,
                    "department": dept,
                    "location": loc,
                    "work_arrangement": arrangement,
                    "apply_url": apply_url,
                    "source_url": apply_url,
                    "source_created_at": item.get("publishedAt"),
                    "source_updated_at": item.get("updatedAt"),
                    "salary": self._annual_salary(item.get("compensation")),
                    "raw_html": desc_html,
                    "description_status": "available" if desc_html else "unavailable",
                })

            return results, True, total_requests

        except Exception as e:
            logger.error(f"Ashby board fetch failed for {self.board_token}: {e}")
            return [], False, total_requests
