"""Constitutional Hash: cdd01ef066bc6cf2
Audit trail for HITL approval events
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from ..config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class AuditEvent:
    """Audit event record"""

    event_id: str
    event_type: str
    request_id: str
    tenant_id: str
    user_id: str
    action: str
    resource: str
    details: Dict[str, Any]
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None


class AuditTrail:
    """Audit trail manager for approval events"""

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.audit_service_url = settings.audit_service_url

    async def log_event(self, event: AuditEvent):
        """Log an audit event"""
        try:
            # Convert to dict for serialization
            event_dict = asdict(event)
            event_dict["timestamp"] = event.timestamp.isoformat()

            # Log locally
            logger.info(
                f"AUDIT: {event.event_type} - {event.action} by {event.user_id} on {event.resource}"
            )

            # Send to audit service if configured
            if self.audit_service_url:
                await self._send_to_audit_service(event_dict)

            # Could also write to local file/database for redundancy
            await self._write_to_local_log(event_dict)

        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")
            # Don't raise exception - audit failures shouldn't break the main flow

    async def _send_to_audit_service(self, event_dict: Dict[str, Any]):
        """Send audit event to centralized audit service"""
        try:
            response = await self.client.post(
                f"{self.audit_service_url}/api/v1/audit/events",
                json=event_dict,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code not in [200, 201, 202]:
                logger.warning(f"Failed to send audit event to service: {response.status_code}")

        except Exception as e:
            logger.error(f"Error sending audit event to service: {e}")

    async def _write_to_local_log(self, event_dict: Dict[str, Any]):
        """Write audit event to local log file for redundancy"""
        try:
            # In a real implementation, this would write to a structured log file
            # or local database that can be forwarded later if the audit service is down
            audit_log_entry = json.dumps(event_dict, default=str)
            logger.debug(f"Local audit log: {audit_log_entry}")

        except Exception as e:
            logger.error(f"Error writing local audit log: {e}")

    async def query_events(
        self,
        tenant_id: Optional[str] = None,
        request_id: Optional[str] = None,
        event_type: Optional[str] = None,
        user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query audit events with filters"""
        try:
            if not self.audit_service_url:
                logger.warning("Audit service not configured, cannot query events")
                return []

            # Build query parameters
            params = {}
            if tenant_id:
                params["tenant_id"] = tenant_id
            if request_id:
                params["request_id"] = request_id
            if event_type:
                params["event_type"] = event_type
            if user_id:
                params["user_id"] = user_id
            if start_date:
                params["start_date"] = start_date.isoformat()
            if end_date:
                params["end_date"] = end_date.isoformat()
            params["limit"] = str(limit)

            response = await self.client.get(
                f"{self.audit_service_url}/api/v1/audit/events", params=params
            )

            if response.status_code == 200:
                return response.json().get("events", [])
            else:
                logger.error(f"Failed to query audit events: {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error querying audit events: {e}")
            return []

    async def get_request_audit_trail(self, request_id: str) -> List[Dict[str, Any]]:
        """Get complete audit trail for an approval request"""
        return await self.query_events(request_id=request_id)

    async def get_tenant_audit_summary(
        self,
        tenant_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get audit summary for a tenant"""
        try:
            events = await self.query_events(
                tenant_id=tenant_id, start_date=start_date, end_date=end_date, limit=1000
            )

            # Analyze events
            summary = {
                "tenant_id": tenant_id,
                "total_events": len(events),
                "event_types": {},
                "approvals_count": 0,
                "rejections_count": 0,
                "escalations_count": 0,
                "time_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None,
                },
            }

            for event in events:
                event_type = event.get("event_type", "unknown")
                summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1

                if event_type == "approval.submitted":
                    summary["approvals_count"] += 1
                elif event_type == "approval.rejected":
                    summary["rejections_count"] += 1
                elif event_type == "approval.escalated":
                    summary["escalations_count"] += 1

            return summary

        except Exception as e:
            logger.error(f"Error getting tenant audit summary: {e}")
            return {"error": str(e)}

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()


# Global audit trail instance
audit_trail = AuditTrail()


# Helper functions for common audit events
async def audit_approval_requested(
    request_id: str,
    tenant_id: str,
    user_id: str,
    decision_id: str,
    priority: str,
    context: Dict[str, Any],
):
    """Audit event for approval request creation"""
    event = AuditEvent(
        event_id=str(uuid4()),
        event_type="approval.requested",
        request_id=request_id,
        tenant_id=tenant_id,
        user_id=user_id,
        action="create",
        resource=f"approval_request/{request_id}",
        details={"decision_id": decision_id, "priority": priority, "context": context},
        timestamp=datetime.utcnow(),
    )
    await audit_trail.log_event(event)


async def audit_approval_decision(
    request_id: str,
    tenant_id: str,
    user_id: str,
    decision: str,
    rationale: Optional[str],
    step_index: int,
):
    """Audit event for approval decision"""
    event = AuditEvent(
        event_id=str(uuid4()),
        event_type=f"approval.{decision}",
        request_id=request_id,
        tenant_id=tenant_id,
        user_id=user_id,
        action=decision,
        resource=f"approval_request/{request_id}",
        details={"decision": decision, "rationale": rationale, "step_index": step_index},
        timestamp=datetime.utcnow(),
    )
    await audit_trail.log_event(event)


async def audit_approval_escalated(
    request_id: str, tenant_id: str, escalation_level: int, reason: str
):
    """Audit event for approval escalation"""
    event = AuditEvent(
        event_id=str(uuid4()),
        event_type="approval.escalated",
        request_id=request_id,
        tenant_id=tenant_id,
        user_id="system",
        action="escalate",
        resource=f"approval_request/{request_id}",
        details={"escalation_level": escalation_level, "reason": reason},
        timestamp=datetime.utcnow(),
    )
    await audit_trail.log_event(event)


async def audit_notification_sent(
    request_id: str,
    tenant_id: str,
    provider: str,
    success: bool,
    error_message: Optional[str] = None,
):
    """Audit event for notification delivery"""
    event = AuditEvent(
        event_id=str(uuid4()),
        event_type="notification.sent",
        request_id=request_id,
        tenant_id=tenant_id,
        user_id="system",
        action="notify",
        resource=f"notification/{provider}",
        details={"provider": provider, "success": success, "error_message": error_message},
        timestamp=datetime.utcnow(),
    )
    await audit_trail.log_event(event)
