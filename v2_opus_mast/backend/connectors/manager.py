from typing import Dict, Any, List, Tuple, Optional
from backend.connectors.greenhouse import GreenhouseConnector
from backend.connectors.workday import WorkdayConnector
from backend.connectors.ashby import AshbyConnector
from backend.connectors.lever import LeverConnector
from backend.connectors.smartrecruiters import SmartRecruitersConnector

_CONNECTORS = {
    "greenhouse": GreenhouseConnector,
    "workday": WorkdayConnector,
    "ashby": AshbyConnector,
    "lever": LeverConnector,
    "smartrecruiters": SmartRecruitersConnector,
}

class ConnectorManager:
    """Instantiates and routes to the appropriate ATS connector."""

    SUPPORTED_PROVIDERS = frozenset(_CONNECTORS)

    @staticmethod
    def feed_status(provider_type: Optional[str], enabled: bool) -> str:
        """
        live | disabled | no_public_feed. Providers without a connector (Eightfold, Phenom,
        GR8 People) have no public unauthenticated feed and are never reported as sync failures.
        """
        provider = (provider_type or "").lower()
        if provider not in _CONNECTORS:
            return "no_public_feed"
        return "live" if enabled else "disabled"

    @staticmethod
    async def fetch_source_jobs(source_dict: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool, int]:
        provider = source_dict["provider_type"].lower()
        connector_cls = _CONNECTORS.get(provider)
        if connector_cls is None:
            raise ValueError(f"Unsupported provider_type: {provider}")
        conn = connector_cls(source_dict)
        return await conn.fetch_jobs()
