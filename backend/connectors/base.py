import asyncio
import json
import random
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import httpx

logger = logging.getLogger("devradar.connectors")

class ResilientHTTPClient:
    """
    HTTP Client with SSRF host validation, per-host concurrency limiting,
    bounded exponential backoff with jitter, Retry-After header support,
    and safe redirect validation.
    """
    def __init__(
        self,
        allowed_hosts: List[str],
        concurrency_limit: int = 2,
        timeout: float = 15.0,
        max_retries: int = 3,
        max_redirects: int = 3,
    ):
        if not allowed_hosts:
            raise ValueError("SSRF Protection: allowed_hosts cannot be empty. Explicit host whitelist is required.")
        self.allowed_hosts = {h.lower().strip() for h in allowed_hosts if h and h.strip()}
        if not self.allowed_hosts:
            raise ValueError("SSRF Protection: allowed_hosts must contain at least one valid host string.")
        self.semaphore = asyncio.Semaphore(concurrency_limit)
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_redirects = max_redirects

    def _validate_host(self, url: str) -> bool:
        """Validates destination scheme is HTTPS and hostname against allowed host whitelist to prevent SSRF."""
        if not self.allowed_hosts:
            return False
        parsed = urlparse(url)
        if parsed.scheme.lower() != "https":
            return False
        hostname = (parsed.hostname or "").lower()
        return hostname in self.allowed_hosts

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        if not self._validate_host(url):
            raise PermissionError(f"SSRF Protection: URL {url} is not allowed (must be HTTPS and in whitelist {self.allowed_hosts})")

        async with self.semaphore:
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=httpx.Timeout(self.timeout),
            ) as client:
                for attempt in range(1, self.max_retries + 1):
                    try:
                        current_url = url
                        current_method = method
                        current_json = json_data
                        current_params = params

                        for redirect_count in range(self.max_redirects + 1):
                            if not self._validate_host(current_url):
                                raise PermissionError(
                                    f"SSRF Protection: Redirect URL {current_url} is not in allowed hosts whitelist {self.allowed_hosts}"
                                )

                            response = await client.request(
                                method=current_method,
                                url=current_url,
                                headers=headers,
                                json=current_json,
                                params=current_params,
                            )

                            if response.status_code in (301, 302, 303, 307, 308):
                                location = response.headers.get("Location")
                                if not location:
                                    return response
                                if redirect_count >= self.max_redirects:
                                    raise httpx.TooManyRedirects(f"Exceeded max redirects ({self.max_redirects}) on {url}")

                                resolved_url = str(response.url.join(location))
                                current_url = resolved_url
                                if response.status_code == 303:
                                    current_method = "GET"
                                    current_json = None
                                    current_params = None
                                continue

                            # Handle rate limiting (HTTP 429)
                            if response.status_code == 429:
                                retry_after = response.headers.get("Retry-After")
                                wait_seconds = float(retry_after) if retry_after and retry_after.isdigit() else (2.0 ** attempt)
                                wait_seconds += random.uniform(0.1, 0.5)
                                logger.warning(f"Rate limited (429) on {current_url}. Backing off {wait_seconds:.2f}s (Attempt {attempt}/{self.max_retries})")
                                await asyncio.sleep(wait_seconds)
                                break  # Break redirect loop to retry outer attempt

                            # Handle 5xx server errors
                            if 500 <= response.status_code < 600:
                                wait_seconds = (2.0 ** attempt) + random.uniform(0.1, 0.5)
                                logger.warning(f"Server error ({response.status_code}) on {current_url}. Retrying in {wait_seconds:.2f}s")
                                await asyncio.sleep(wait_seconds)
                                break  # Break redirect loop to retry outer attempt

                            return response

                    except PermissionError:
                        raise
                    except (httpx.TimeoutException, httpx.NetworkError) as exc:
                        if attempt == self.max_retries:
                            logger.error(f"Network error on {url} after {self.max_retries} attempts: {exc}")
                            raise
                        wait_seconds = (2.0 ** attempt) + random.uniform(0.1, 0.5)
                        logger.warning(f"Network error on {url} ({exc}). Retrying in {wait_seconds:.2f}s")
                        await asyncio.sleep(wait_seconds)

                raise httpx.HTTPStatusError("Max retries exceeded", request=None, response=response)
