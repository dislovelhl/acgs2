"""
OPA Service for Policy Registry
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
import httpx
from typing import Any, Dict, Optional

try:
    from shared.config import settings
except ImportError:
    # Fallback for local development or testing
    try:
        from ....shared.config import settings
    except ImportError:
        settings = None

logger = logging.getLogger(__name__)

class OPAService:
    """
    Service for interacting with Open Policy Agent (OPA).
    Used for RBAC and granular authorization.
    """
    
    def __init__(self):
        if settings:
            self.opa_url = settings.opa.url
            self.fail_closed = settings.opa.fail_closed
        else:
            self.opa_url = "http://localhost:8181"
            self.fail_closed = True
        
    async def check_authorization(
        self, 
        user: Dict[str, Any], 
        action: str, 
        resource: str
    ) -> bool:
        """
        Check if a user is authorized for an action on a resource.
        Queries the 'acgs.rbac.allow' rule in OPA.
        """
        input_data = {
            "input": {
                "user": user,
                "action": action,
                "resource": resource
            }
        }
        
        # OPA data API path for the rbac policy
        policy_path = "acgs/rbac/allow"
        url = f"{self.opa_url}/v1/data/{policy_path}"
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(url, json=input_data)
                
                if response.status_code == 200:
                    data = response.json()
                    # OPA returns {"result": true/false}
                    result = data.get("result", False)
                    logger.info(f"OPA RBAC check: user={user.get('agent_id')}, role={user.get('role')}, action={action}, resource={resource}, result={result}")
                    return result
                else:
                    logger.error(f"OPA returned non-200 status: {response.status_code} - {response.text}")
                    return False if self.fail_closed else True
                    
        except Exception as e:
            logger.error(f"Error connecting to OPA: {e}")
            return False if self.fail_closed else True
