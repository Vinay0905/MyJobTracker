from typing import List, Dict, Any, Tuple
import json
import logging
import asyncio
from backend.connectors.base import ResilientHTTPClient

logger = logging.getLogger("devradar.connectors.smartrecruiters")

class SmartRecruitersConnector:
    """
    Public REST API Connector for SmartRecruiters Job Postings.
    List Endpoint: https://api.smartrecruiters.com/v1/companies/{company}/postings
    Detail Endpoint: https://api.smartrecruiters.com/v1/companies/{company}/postings/{id}
    """
    def __init__(self, source_config: Dict[str, Any]):
        self.source_id = source_config["source_id"]
        self.company = source_config.get("company") or source_config.get("board_token")
        self.base_url = source_config.get("base_url", "https://api.smartrecruiters.com").rstrip("/")
        allowed_hosts = json.loads(source_config.get("allowed_hosts", "[]"))
        if not allowed_hosts:
            allowed_hosts = ["api.smartrecruiters.com", "jobs.smartrecruiters.com"]

        self.client = ResilientHTTPClient(
            allowed_hosts=allowed_hosts,
            concurrency_limit=source_config.get("concurrency_limit", 2),
            timeout=source_config.get("timeout_seconds", 15.0),
        )

    async def fetch_jobs(self, limit: int = 50) -> Tuple[List[Dict[str, Any]], bool, int]:
        """
        Fetches job postings and retrieves genuine detail descriptions from SmartRecruiters.
        Returns: (jobs_list, pagination_complete, request_count)
        """
        url = f"{self.base_url}/v1/companies/{self.company}/postings?limit={limit}"
        headers = {"Accept": "application/json"}
        total_requests = 1

        try:
            resp = await self.client.request("GET", url, headers=headers)
            if resp.status_code != 200:
                logger.error(f"SmartRecruiters company {self.company} returned HTTP {resp.status_code}")
                return [], False, total_requests

            data = resp.json()
            if not isinstance(data, dict) or "content" not in data:
                logger.error(f"SmartRecruiters response schema invalid: missing 'content' key at {url}")
                return [], False, total_requests

            raw_postings = data.get("content", [])
            all_postings = []

            for post in raw_postings:
                posting_id = str(post.get("id"))
                title = post.get("name", "").strip()
                dept = post.get("department", {}).get("label") or ""
                loc_obj = post.get("location", {})
                city = loc_obj.get("city") or ""
                country = loc_obj.get("country") or ""
                location_str = f"{city}, {country}".strip(", ") or "Remote / Global"
                ref_num = post.get("refNumber")

                apply_url = f"https://jobs.smartrecruiters.com/{self.company}/{posting_id}"

                all_postings.append({
                    "provider_posting_id": posting_id,
                    "requisition_id": ref_num,
                    "title": title,
                    "department": dept,
                    "location": location_str,
                    "apply_url": apply_url,
                    "source_url": apply_url,
                    "raw_html": "",
                    "description_status": "pending",
                })

            # Retrieve genuine detail descriptions from posting detail endpoint
            async def _fetch_detail(p: Dict[str, Any]) -> None:
                nonlocal total_requests
                p_id = p["provider_posting_id"]
                detail_url = f"{self.base_url}/v1/companies/{self.company}/postings/{p_id}"
                try:
                    d_resp = await self.client.request("GET", detail_url, headers=headers)
                    total_requests += 1
                    if d_resp.status_code == 200:
                        d_data = d_resp.json()
                        job_ad = d_data.get("jobAd", {})
                        sections = job_ad.get("sections", {})
                        job_desc = sections.get("jobDescription", {}).get("text", "")
                        qualifications = sections.get("qualifications", {}).get("text", "")
                        additional = sections.get("additionalInformation", {}).get("text", "")
                        full_html = f"<div>{job_desc}</div><div>{qualifications}</div><div>{additional}</div>".strip()
                        p["raw_html"] = full_html
                        p["description_status"] = "available" if full_html else "unavailable"
                    else:
                        p["raw_html"] = ""
                        p["description_status"] = "unavailable"
                except Exception as e:
                    logger.warning(f"SmartRecruiters detail fetch failed for {p_id}: {e}")
                    p["raw_html"] = ""
                    p["description_status"] = "unavailable"

            if all_postings:
                await asyncio.gather(*[_fetch_detail(p) for p in all_postings])

            return all_postings, True, total_requests

        except Exception as e:
            logger.error(f"SmartRecruiters fetch failed for {self.company}: {e}")
            return [], False, total_requests
