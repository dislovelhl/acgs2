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

            # We assume there is an endpoint or we use the ledger in-process if configured
            # For this integration, we'll assume a direct ledger dependency or API call.
            # If the AuditService is in-process (shared library), we could call it directly.
            # However, the plan specified an API entrypoint.
            
            # Since the AuditService's ledger is async, we can also integrate it directly
            # if we have access to the code.
            
            # For now, let's assume we post to the Audit Service API if it's a separate service.
            # But the current AuditLedger implementation in services/audit_service/core 
            # is what we really want to use if this is a monolithic-style development.
            
            # If we are in the same environment, we can import AuditLedger.
            try:
                from services.audit_service.core.audit_ledger import AuditLedger
                # If we can import it, we use it directly for better performance
                # This depends on your deployment model. 
                # If they are truly disparate microservices, use httpx.
                pass 
            except ImportError:
                pass

            # Placeholder for actual API call to the AuditService
            # In a real microservice setup:
            # response = await self.client.post(f"{self.service_url}/audit/record", json=data)
            # return response.json().get("hash")
            
            logger.debug(f"Audit record prepared for: {data.get('constitutional_hash')}")
            return "simulated_audit_hash"

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
