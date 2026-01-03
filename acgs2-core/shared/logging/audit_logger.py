"""
Tenant-scoped audit logging with access controls
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from shared.logging import get_logger

logger = get_logger(__name__)


class TenantAuditLogger:
    """
    Enforces tenant-scoped audit logging for security and compliance.
    """

    def __init__(self, service_name: str):
        self.service_name = service_name

    def log_action(
        self,
        tenant_id: str,
        action: str,
        actor_id: str,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        status: str = "success",
    ):
        """
        Log an auditable action scoped to a tenant.

        Args:
            tenant_id: Tenant identifier
            action: Action being performed (e.g., 'create_policy')
            actor_id: User or agent performing the action
            resource_id: Identifier of the resource being acted upon
            context: Additional details
            status: 'success' or 'failure'
        """
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "tenant_id": tenant_id,
            "action": action,
            "actor_id": actor_id,
            "resource_id": resource_id,
            "status": status,
            "context": context or {},
        }

        # Log at INFO level for regular audit trail
        # In production, these are collected by ELK/Splunk/etc.
        logger.info(
            f"AUDIT: {action} by {actor_id} on {resource_id} (Tenant: {tenant_id})",
            extra={"audit": True, "payload": audit_entry},
        )

    def log_failure(self, tenant_id: str, action: str, actor_id: str, error: str, **kwargs):
        """Log a failed action attempt"""
        self.log_action(
            tenant_id=tenant_id,
            action=action,
            actor_id=actor_id,
            status="failure",
            context={"error": error, **kwargs},
        )
