"""Constitutional Hash: cdd01ef066bc6cf2
Notification Orchestrator Service
Routes notifications to appropriate channels (Slack/Teams/PagerDuty)
"""

import logging

from ..config.settings import settings
from ..models.approval_request import ApprovalRequest
from ..notifications.base import NotificationMessage, notification_manager

logger = logging.getLogger(__name__)


class NotificationOrchestrator:
    """
    Orchestrates notification delivery across multiple channels.
    """

    async def send_approval_request_notification(self, request: ApprovalRequest):
        """Send notification for a new or escalated approval request"""
        message = NotificationMessage(
            title=f"Approval Required: {request.title}",
            message=request.description or "No description provided",
            priority=request.priority,
            request_id=str(request.id),
            approval_url=f"{settings.agent_bus_url}/approvals/{request.id}",  # Placeholder URL
            tenant_id=request.tenant_id,
            metadata={
                "decision_id": request.decision_id,
                "requested_by": request.requested_by,
                "current_step": request.current_step_index,
            },
        )

        # Determine providers based on priority
        providers = ["slack", "teams"]
        if request.priority in ["high", "critical"]:
            providers.append("pagerduty")

        results = await notification_manager.send_notifications(message, providers=providers)
        logger.info(f"Notifications sent for request {request.id}: {results}")
        return results

    async def send_escalation_notification(self, request: ApprovalRequest, escalation_level: int):
        """Send notification when a request is escalated"""
        message = NotificationMessage(
            title=f"ESCALATION Level {escalation_level}: {request.title}",
            message=f"Request has been escalated due to timeout. {request.description}",
            priority="high",
            request_id=str(request.id),
            approval_url=f"{settings.agent_bus_url}/approvals/{request.id}",
            tenant_id=request.tenant_id,
            metadata={
                "decision_id": request.decision_id,
                "escalation_level": escalation_level,
                "current_step": request.current_step_index,
            },
        )

        # For escalations, always include PagerDuty if it's high level
        providers = ["slack", "teams"]
        if escalation_level >= 2 or request.priority == "critical":
            providers.append("pagerduty")

        results = await notification_manager.send_notifications(message, providers=providers)
        logger.info(f"Escalation notifications sent for request {request.id}: {results}")
        return results
