from typing import Dict, Any, List, Tuple
from backend.connectors.greenhouse import GreenhouseConnector
from backend.connectors.workday import WorkdayConnector
from backend.connectors.ashby import AshbyConnector
from backend.connectors.lever import LeverConnector
from backend.connectors.smartrecruiters import SmartRecruitersConnector

class ConnectorManager:
    """Instantiates and routes to the appropriate ATS connector."""
    
    @staticmethod
    async def fetch_source_jobs(source_dict: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], bool, int]:
        provider = source_dict["provider_type"].lower()
        if provider == "greenhouse":
            conn = GreenhouseConnector(source_dict)
            return await conn.fetch_jobs()
        elif provider == "workday":
            conn = WorkdayConnector(source_dict)
            return await conn.fetch_jobs()
        elif provider == "ashby":
            conn = AshbyConnector(source_dict)
            return await conn.fetch_jobs()
        elif provider == "lever":
            conn = LeverConnector(source_dict)
            return await conn.fetch_jobs()
        elif provider == "smartrecruiters":
            conn = SmartRecruitersConnector(source_dict)
            return await conn.fetch_jobs()
        else:
            raise ValueError(f"Unsupported provider_type: {provider}")
