from typing import List, Dict, Any, Tuple
import json
import logging
from backend.connectors.base import ResilientHTTPClient

logger = logging.getLogger("devradar.connectors.workday")

class WorkdayConnector:
    """
    Workday CXS API Connector (e.g. NVIDIA external career site).
    Endpoint: {base_url}{endpoint}
    """
    def __init__(self, source_config: Dict[str, Any]):
        self.source_id = source_config["source_id"]
        self.base_url = source_config["base_url"].rstrip("/")
        self.endpoint = source_config.get("endpoint", "/wday/cxs/nvidia/NVIDIAExternalCareerSite/jobs")
        allowed_hosts = json.loads(source_config.get("allowed_hosts", "[]"))

        self.client = ResilientHTTPClient(
            allowed_hosts=allowed_hosts,
            concurrency_limit=source_config.get("concurrency_limit", 2),
            timeout=source_config.get("timeout_seconds", 20.0),
        )

    async def fetch_jobs(self, max_pages: int = 5) -> Tuple[List[Dict[str, Any]], bool, int]:
        """
        Paginates through Workday CXS job listings and fetches detail descriptions.
        Returns: (jobs_list, pagination_complete, request_count)
        """
        url = f"{self.base_url}{self.endpoint}"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        
        limit = 20
        offset = 0
        total_requests = 0
        all_postings = []
        pagination_complete = False

        for page in range(max_pages):
            payload = {
                "appliedFacets": {},
                "limit": limit,
                "offset": offset,
                "searchText": "Engineer",
            }

            try:
                resp = await self.client.request("POST", url, headers=headers, json_data=payload)
                total_requests += 1

                if resp.status_code != 200:
                    logger.error(f"Workday endpoint {url} returned HTTP {resp.status_code}")
                    return all_postings, False, total_requests

                data = resp.json()
                if not isinstance(data, dict) or "jobPostings" not in data:
                    logger.error(f"Workday response schema invalid: missing 'jobPostings' key at {url}")
                    return all_postings, False, total_requests

                postings = data.get("jobPostings", [])
                total_count = data.get("total", 0)

                if not postings:
                    pagination_complete = True
                    break

                for post in postings:
                    ext_path = post.get("externalPath", "")
                    bullet_fields = post.get("bulletFields", [])
                    req_id = bullet_fields[0] if bullet_fields else ext_path.split("/")[-1]
                    posting_id = post.get("bulletFields", [ext_path])[-1] or ext_path

                    all_postings.append({
                        "provider_posting_id": str(posting_id),
                        "requisition_id": str(req_id),
                        "title": post.get("title", "").strip(),
                        "department": "Engineering & Technology",
                        "location": post.get("locationsText", "Multiple Locations"),
                        "apply_url": f"{self.base_url}/en-US/NVIDIAExternalCareerSite{ext_path}",
                        "source_url": f"{self.base_url}/en-US/NVIDIAExternalCareerSite{ext_path}",
                        "external_path": ext_path,
                        "posted_on": post.get("postedOn", "Recent"),
                        "raw_html": "",
                        "description_status": "pending",
                    })

                offset += len(postings)
                if offset >= total_count or len(postings) < limit:
                    pagination_complete = True
                    break

            except Exception as e:
                logger.error(f"Workday page fetch failed at offset {offset}: {e}")
                return all_postings, False, total_requests

        # Retrieve real job descriptions from the Workday CXS job detail endpoint
        async def _fetch_detail(p: Dict[str, Any]) -> None:
            nonlocal total_requests
            ext_path = p.get("external_path", "")
            if not ext_path:
                p["raw_html"] = ""
                p["description_status"] = "unavailable"
                return

            cxs_prefix = self.endpoint.rsplit("/jobs", 1)[0]
            clean_ext = ext_path if ext_path.startswith("/") else f"/{ext_path}"
            detail_url = f"{self.base_url}{cxs_prefix}{clean_ext}"

            try:
                resp = await self.client.request("GET", detail_url, headers={"Accept": "application/json"})
                total_requests += 1
                if resp.status_code == 200:
                    detail_data = resp.json()
                    posting_info = detail_data.get("jobPostingInfo", {}) if isinstance(detail_data, dict) else {}
                    desc = posting_info.get("jobDescription", "")
                    p["raw_html"] = desc or ""
                    p["description_status"] = "available" if desc else "unavailable"
                    if posting_info.get("jobReqId"):
                        p["requisition_id"] = str(posting_info["jobReqId"])
                    if posting_info.get("startDate"):
                        p["posted_on"] = posting_info["startDate"]
                else:
                    logger.warning(f"Workday detail fetch HTTP {resp.status_code} for {detail_url}")
                    p["raw_html"] = ""
                    p["description_status"] = "unavailable"
            except Exception as e:
                logger.warning(f"Workday detail fetch failed for {detail_url}: {e}")
                p["raw_html"] = ""
                p["description_status"] = "unavailable"

        if all_postings:
            import asyncio
            await asyncio.gather(*[_fetch_detail(p) for p in all_postings])

        return all_postings, pagination_complete, total_requests
