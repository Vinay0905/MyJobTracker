from typing import List, Dict, Any, Tuple, Optional
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

    def _map_posting(self, post: Dict[str, Any]) -> Dict[str, Any]:
        posting_id = str(post.get("id"))
        loc_obj = post.get("location") or {}
        city = loc_obj.get("city") or ""
        country = loc_obj.get("country") or ""
        location_str = f"{city}, {country}".strip(", ")
        if loc_obj.get("hybrid"):
            arrangement = "hybrid"
        elif loc_obj.get("remote"):
            arrangement = "remote"
        else:
            arrangement = None
        apply_url = f"https://jobs.smartrecruiters.com/{self.company}/{posting_id}"
        return {
            "provider_posting_id": posting_id,
            "requisition_id": post.get("refNumber"),
            "title": (post.get("name") or "").strip(),
            "department": (post.get("department") or {}).get("label") or "",
            "location": location_str,
            "work_arrangement": arrangement,
            "apply_url": apply_url,
            "source_url": apply_url,
            "source_created_at": post.get("releasedDate"),
            "raw_html": "",
            "description_status": "pending",
        }

    async def fetch_jobs(self, limit: int = 100, max_pages: int = 20) -> Tuple[List[Dict[str, Any]], bool, int]:
        """
        Pages through postings with offset until totalFound is covered, then retrieves detail descriptions.
        Returns: (jobs_list, pagination_complete, request_count)

        Incomplete when a full page is left unread (page cap hit) or any detail fetch fails.
        """
        headers = {"Accept": "application/json"}
        total_requests = 0
        all_postings: List[Dict[str, Any]] = []
        seen_ids = set()
        total_found: Optional[int] = None
        offset = 0
        listing_complete = False

        try:
            for _ in range(max_pages):
                url = f"{self.base_url}/v1/companies/{self.company}/postings?limit={limit}&offset={offset}"
                resp = await self.client.request("GET", url, headers=headers)
                total_requests += 1
                if resp.status_code != 200:
                    logger.error(f"SmartRecruiters company {self.company} returned HTTP {resp.status_code}")
                    return all_postings, False, total_requests

                data = resp.json()
                if not isinstance(data, dict) or "content" not in data:
                    logger.error(f"SmartRecruiters response schema invalid: missing 'content' key at {url}")
                    return all_postings, False, total_requests

                if total_found is None and isinstance(data.get("totalFound"), int):
                    total_found = data["totalFound"]

                page = data.get("content") or []
                for post in page:
                    mapped = self._map_posting(post)
                    if mapped["provider_posting_id"] in seen_ids:
                        continue
                    seen_ids.add(mapped["provider_posting_id"])
                    all_postings.append(mapped)

                offset += len(page)
                if total_found is not None:
                    if offset >= total_found:
                        listing_complete = True
                        break
                    if not page:
                        # Provider claims more postings than it will return.
                        break
                elif len(page) < limit:
                    listing_complete = True
                    break
        except Exception as e:
            logger.error(f"SmartRecruiters fetch failed for {self.company}: {e}")
            return all_postings, False, total_requests

        if not listing_complete:
            logger.warning(
                f"SmartRecruiters {self.company}: listing incomplete (fetched {offset} of {total_found}); closures disabled for this run"
            )

        detail_failures = 0

        # Retrieve genuine detail descriptions from posting detail endpoint
        async def _fetch_detail(p: Dict[str, Any]) -> None:
            nonlocal total_requests, detail_failures
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
                    has_text = any([job_desc, qualifications, additional])
                    p["raw_html"] = f"<div>{job_desc}</div><div>{qualifications}</div><div>{additional}</div>" if has_text else ""
                    p["description_status"] = "available" if has_text else "unavailable"
                    if not has_text:
                        detail_failures += 1
                else:
                    p["raw_html"] = ""
                    p["description_status"] = "unavailable"
                    detail_failures += 1
            except Exception as e:
                logger.warning(f"SmartRecruiters detail fetch failed for {p_id}: {e}")
                p["raw_html"] = ""
                p["description_status"] = "unavailable"
                detail_failures += 1

        if all_postings:
            await asyncio.gather(*[_fetch_detail(p) for p in all_postings])

        return all_postings, listing_complete and detail_failures == 0, total_requests
