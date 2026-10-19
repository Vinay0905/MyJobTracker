from typing import List, Dict, Any, Tuple
import json
import logging
from backend.connectors.base import ResilientHTTPClient

logger = logging.getLogger("devradar.connectors.lever")

class LeverConnector:
    """
    Public JSON API Connector for Lever Job Boards.
    Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
    """
    def __init__(self, source_config: Dict[str, Any]):
        self.source_id = source_config["source_id"]
        self.company = source_config.get("company") or source_config.get("board_token")
        self.base_url = source_config.get("base_url", "https://api.lever.co").rstrip("/")
        allowed_hosts = json.loads(source_config.get("allowed_hosts", "[]"))
        if not allowed_hosts:
            allowed_hosts = ["api.lever.co", "jobs.lever.co"]

        self.client = ResilientHTTPClient(
            allowed_hosts=allowed_hosts,
            concurrency_limit=source_config.get("concurrency_limit", 2),
            timeout=source_config.get("timeout_seconds", 15.0),
        )

    async def fetch_jobs(self) -> Tuple[List[Dict[str, Any]], bool, int]:
        """
        Fetches all active jobs with descriptions from the Lever postings API.
        Returns: (jobs_list, pagination_complete, request_count)
        """
        url = f"{self.base_url}/v0/postings/{self.company}?mode=json"
        headers = {"Accept": "application/json"}
        total_requests = 1

        try:
            resp = await self.client.request("GET", url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"Lever board {self.company} returned HTTP {resp.status_code}")
                return [], False, total_requests

            data = resp.json()
            if not isinstance(data, list):
                logger.error(f"Lever response schema invalid: expected list, got {type(data)} at {url}")
                return [], False, total_requests

            results: List[Dict[str, Any]] = []

            for item in data:
                posting_id = str(item.get("id"))
                title = item.get("text", "").strip()
                categories = item.get("categories", {})
                dept = categories.get("department") or categories.get("team") or ""
                loc = categories.get("location") or "Remote / Global"
                apply_url = item.get("hostedUrl") or item.get("applyUrl") or f"https://jobs.lever.co/{self.company}/{posting_id}"
                desc_html = item.get("description") or item.get("descriptionPlain") or ""

                # Additional list of lists/qualifications
                lists_items = item.get("lists", [])
                extra_reqs = []
                for lst in lists_items:
                    text_label = lst.get("text", "")
                    content = lst.get("content", "")
                    extra_reqs.append(f"<h4>{text_label}</h4>{content}")
                if extra_reqs:
                    desc_html = f"{desc_html} {' '.join(extra_reqs)}"

                results.append({
                    "provider_posting_id": posting_id,
                    "requisition_id": None,
                    "title": title,
                    "department": dept,
                    "location": loc,
                    "apply_url": apply_url,
                    "source_url": apply_url,
                    "raw_html": desc_html,
                    "description_status": "available" if desc_html else "unavailable",
                })

            return results, True, total_requests

        except Exception as e:
            logger.error(f"Lever board fetch failed for {self.company}: {e}")
            return [], False, total_requests
