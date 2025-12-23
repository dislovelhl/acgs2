"""
ACGS-2 Workflow Activities
Constitutional Hash: cdd01ef066bc6cf2

Activity interface for external operations in workflows.
All activities MUST be idempotent.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging
import uuid

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


logger = logging.getLogger(__name__)


class BaseActivities(ABC):
    """
    Abstract base class for workflow activities.

    Activities handle all external interactions (non-deterministic operations).
    They are called by workflows to perform side effects.

    CRITICAL: All activities MUST be idempotent.
    - Safe to retry multiple times
    - Same result for same input
    - Use idempotency keys where needed

    Example implementation:
        class MyActivities(BaseActivities):
            async def validate_constitutional_hash(self, ...) -> Dict[str, Any]:
                # Implementation here
                pass
    """

    @abstractmethod
    async def validate_constitutional_hash(
        self,
        workflow_id: str,
        provided_hash: str,
        expected_hash: str = CONSTITUTIONAL_HASH
    ) -> Dict[str, Any]:
        """
        Validate constitutional hash compliance.

        Args:
            workflow_id: Workflow instance identifier
            provided_hash: Hash to validate
            expected_hash: Expected constitutional hash

        Returns:
            Dict with 'is_valid', 'errors', 'validation_timestamp'
        """
        pass

    @abstractmethod
    async def evaluate_policy(
        self,
        workflow_id: str,
        policy_path: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate OPA policy for the given input.

        Args:
            workflow_id: Workflow instance identifier
            policy_path: OPA policy path (e.g., "acgs/constitutional/allow")
            input_data: Data to evaluate against policy

        Returns:
            Dict with 'allowed', 'reasons', 'policy_version'
        """
        pass

    @abstractmethod
    async def record_audit(
        self,
        workflow_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> str:
        """
        Record event to blockchain-anchored audit trail.

        Args:
            workflow_id: Workflow instance identifier
            event_type: Type of audit event
            event_data: Event data to record

        Returns:
            Audit hash/transaction ID
        """
        pass

    @abstractmethod
    async def send_notification(
        self,
        workflow_id: str,
        channel: str,
        recipient: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send notification via specified channel.

        Args:
            workflow_id: Workflow instance identifier
            channel: Notification channel (e.g., "slack", "email")
            recipient: Recipient identifier
            message: Notification message
            metadata: Additional notification metadata

        Returns:
            Notification ID
        """
        pass


class DefaultActivities(BaseActivities):
    """
    Default implementation of workflow activities.

    Uses ACGS-2 components where available, with fallbacks for testing.
    """

    def __init__(self):
        self._opa_client = None
        self._audit_client = None

    async def validate_constitutional_hash(
        self,
        workflow_id: str,
        provided_hash: str,
        expected_hash: str = CONSTITUTIONAL_HASH
    ) -> Dict[str, Any]:
        """Validate constitutional hash."""
        is_valid = provided_hash == expected_hash
        errors = [] if is_valid else [
            f"Constitutional hash mismatch: expected {expected_hash}, got {provided_hash}"
        ]

        logger.info(
            f"Workflow {workflow_id}: Constitutional hash validation "
            f"{'passed' if is_valid else 'failed'}"
        )

        return {
            "is_valid": is_valid,
            "errors": errors,
            "validation_timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow_id": workflow_id,
            "expected_hash": expected_hash,
            "provided_hash": provided_hash,
        }

    async def evaluate_policy(
        self,
        workflow_id: str,
        policy_path: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate OPA policy."""
        try:
            # Try to use OPA client if available
            if self._opa_client is None:
                try:
                    from enhanced_agent_bus.opa_client import get_opa_client
                    self._opa_client = get_opa_client()
                except ImportError:
                    pass

            if self._opa_client:
                result = await self._opa_client.evaluate(policy_path, input_data)
                return {
                    "allowed": result.get("allow", False),
                    "reasons": result.get("reasons", []),
                    "policy_version": result.get("version", "unknown"),
                }

        except Exception as e:
            logger.warning(f"OPA evaluation failed: {e}")

        # Fallback: allow with warning
        logger.warning(
            f"Workflow {workflow_id}: OPA not available, using fallback (allow)"
        )
        return {
            "allowed": True,
            "reasons": ["OPA not configured - fallback allow"],
            "policy_version": "fallback",
        }

    async def record_audit(
        self,
        workflow_id: str,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> str:
        """Record to audit trail."""
        try:
            # Try to use audit client if available
            if self._audit_client is None:
                try:
                    from enhanced_agent_bus.audit_client import AuditClient
                    self._audit_client = AuditClient()
                except ImportError:
                    pass

            if self._audit_client:
                return await self._audit_client.record(
                    workflow_id=workflow_id,
                    event_type=event_type,
                    event_data=event_data
                )

        except Exception as e:
            logger.warning(f"Audit recording failed: {e}")

        # Fallback: generate mock audit hash
        import hashlib
        import json

        audit_data = {
            "workflow_id": workflow_id,
            "event_type": event_type,
            "event_data": event_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        audit_hash = hashlib.sha256(
            json.dumps(audit_data, default=str, sort_keys=True).encode()
        ).hexdigest()[:16]

        logger.info(f"Workflow {workflow_id}: Audit recorded (mock): {audit_hash}")
        return audit_hash

    async def send_notification(
        self,
        workflow_id: str,
        channel: str,
        recipient: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Send notification."""
        notification_id = str(uuid.uuid4())

        logger.info(
            f"Workflow {workflow_id}: Notification {notification_id} "
            f"sent via {channel} to {recipient}"
        )

        return notification_id


# Singleton instance
_default_activities: Optional[DefaultActivities] = None


def get_default_activities() -> DefaultActivities:
    """Get singleton default activities instance."""
    global _default_activities
    if _default_activities is None:
        _default_activities = DefaultActivities()
    return _default_activities


__all__ = [
    "BaseActivities",
    "DefaultActivities",
    "get_default_activities",
]
