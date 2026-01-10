"""Constitutional Hash: cdd01ef066bc6cf2
ACGS-2 Runtime Security - Permission Scoper
Facilitates dynamic, task-specific token generation for autonomous agents.
Enforces the principle of least privilege.
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    from core.services.policy_registry.app.services.crypto_service import CryptoService
except ImportError:
    # Fallback if service not in path
    import os
    import sys

    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from core.services.policy_registry.app.services.crypto_service import CryptoService

logger = logging.getLogger(__name__)


@dataclass
class ScopedPermission:
    resource: str
    action: str
    constraints: Optional[Dict[str, Any]] = None


class PermissionScoper:
    """
    Manages dynamic scoping of agent permissions based on task context.
    Generates short-lived, task-specific tokens (SVIDs).
    """

    def __init__(self, private_key: Optional[str] = None):
        self._private_key = private_key or os.environ.get("JWT_PRIVATE_KEY")
        if not self._private_key:
            logger.warning(
                "PermissionScoper initialized without private key. Token generation will fail."
            )

    def generate_task_token(
        self,
        agent_id: str,
        tenant_id: str,
        task_id: str,
        permissions: List[ScopedPermission],
        expires_in_seconds: int = 3600,
    ) -> str:
        """
        Generates a task-scoped JWT token.
        """
        if not self._private_key:
            raise ValueError("Private key not configured for PermissionScoper")

        # Prepare extra claims for permissions and task context
        extra_claims = {
            "task_id": task_id,
            "permissions": [
                {"resource": p.resource, "action": p.action, "constraints": p.constraints}
                for p in permissions
            ],
        }

        # Use CryptoService with extra claims support
        return CryptoService.issue_agent_token(
            agent_id=agent_id,
            tenant_id=tenant_id,
            capabilities=[],  # Capabilities handled via permissions now
            private_key_b64=self._private_key,
            ttl_hours=max(1, round(expires_in_seconds / 3600)),  # Convert to hours, minimum 1 hour
            extra_claims=extra_claims,
        )

    def scope_permissions_for_task(
        self, agent_capabilities: List[str], task_requirements: List[str]
    ) -> List[ScopedPermission]:
        """
        Reduces broad agent capabilities to a minimal set required for a specific task.
        """
        scoped = []
        for req in task_requirements:
            # Simple intersection for now
            if req in agent_capabilities:
                scoped.append(ScopedPermission(resource="general", action=req))
            else:
                logger.warning(
                    f"Agent requested task requiring {req} which exceeds its capabilities."
                )

        return scoped
