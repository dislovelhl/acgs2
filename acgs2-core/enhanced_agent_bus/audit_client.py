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

        Note: This is designed to be fire-and-forget or async monitored.
        """
        try:
            # Check if validation_result has to_dict
            if hasattr(validation_result, "to_dict"):
                data = validation_result.to_dict()
            else:
                # Fallback to asdict if it's a dataclass
                from dataclasses import is_dataclass
                if is_dataclass(validation_result):
                    data = asdict(validation_result)
                else:
                    data = validation_result

            # Post to the Audit Service API (FR-1.3)
            try:
                response = await self.client.post(f"{self.service_url}/record", json=data)
                if response.status_code == 200:
                    audit_hash = response.json().get("entry_hash")
                    logger.info(f"Audit record successful: {audit_hash}")
                    return audit_hash
                else:
                    logger.error(f"Audit Service returned error {response.status_code}: {response.text}")
                    return None
            except httpx.RequestError as e:
                logger.error(f"Network error communicating with Audit Service: {e}")
                return None

        except Exception as e:
            logger.error(f"Failed to report validation to audit service: {e}")
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
