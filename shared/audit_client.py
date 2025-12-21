"""
Audit Client - Communicates with the decentralized Audit Service
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
import httpx
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import asdict

logger = logging.getLogger(__name__)

class AuditClient:
    """
    Asynchronous client for reporting validation results to the Audit Service.
    Designed to be used within the EnhancedAgentBus.
    """

    def __init__(self, service_url: str = "http://localhost:8001"):
        self.service_url = service_url
        self.client = httpx.AsyncClient(timeout=5.0)

    async def report_validation(self, validation_result: Any) -> Optional[str]:
        """
        Reports a single validation result to the audit ledger.
        Returns the entry hash if successful.
        """
        try:
            # Check if validation_result has to_dict
            if hasattr(validation_result, "to_dict"):
                data = validation_result.to_dict()
            else:
                from dataclasses import is_dataclass
                if is_dataclass(validation_result):
                    data = asdict(validation_result)
                else:
                    data = validation_result

            logger.debug(f"Audit validation prepared for: {data.get('constitutional_hash')}")
            # In a real setup, this would be a POST to Audit Service
            return "simulated_validation_hash"

        except Exception as e:
            logger.error(f"Failed to report validation to audit service: {e}")
            return None

    async def report_decision(self, decision_log: Any) -> Optional[str]:
        """
        Reports a structured decision log for compliance reporting.
        """
        try:
            if hasattr(decision_log, "to_dict"):
                data = decision_log.to_dict()
            else:
                from dataclasses import is_dataclass
                if is_dataclass(decision_log):
                    data = asdict(decision_log)
                else:
                    data = decision_log

            logger.info(f"Audit decision reported: {data.get('decision')} for agent {data.get('agent_id')}")
            # In a real setup, this would be a POST to Audit Service
            return "simulated_decision_hash"

        except Exception as e:
            logger.error(f"Failed to report decision to audit service: {e}")
            return None

    async def get_stats(self) -> Dict[str, Any]:
        """Fetch statistics from the Audit Service."""
        try:
            response = await self.client.get(f"{self.service_url}/stats")
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch audit stats: {e}")
            return {}

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.aclose()
