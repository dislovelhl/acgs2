"""
ACGS-2 Multi-Approver Workflow Engine
Constitutional Hash: cdd01ef066bc6cf2

Enterprise-grade approval workflow supporting:
- Multiple required approvers
- Role-based approval policies
- Timeout and escalation handling
- Audit trail integration
- Slack/Teams/Email notifications
"""

import asyncio
import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from uuid import uuid4

logger = logging.getLogger(__name__)
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class ApprovalStatus(Enum):
    """Status of an approval request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class ApproverRole(Enum):
    """Roles that can approve requests."""
    SECURITY_TEAM = "security_team"
    COMPLIANCE_TEAM = "compliance_team"
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    POLICY_OWNER = "policy_owner"
    ENGINEERING_LEAD = "engineering_lead"
    ON_CALL = "on_call"


class EscalationLevel(Enum):
    """Escalation levels for overdue approvals."""
    LEVEL_1 = 1  # Initial notification
    LEVEL_2 = 2  # First escalation
    LEVEL_3 = 3  # Critical escalation
    EXECUTIVE = 4  # Executive override


@dataclass
class Approver:
    """Represents an individual approver."""
    id: str
    name: str
    email: str
    roles: List[ApproverRole]
    slack_id: Optional[str] = None
    teams_id: Optional[str] = None
    timezone: str = "UTC"
    is_active: bool = True

    def has_role(self, role: ApproverRole) -> bool:
        return role in self.roles


@dataclass
class ApprovalDecision:
    """Record of a single approver's decision."""
    approver_id: str
    approver_name: str
    decision: ApprovalStatus
    reasoning: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "decision": self.decision.value,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ApprovalPolicy:
    """Defines approval requirements for a type of request."""
    name: str
    required_roles: List[ApproverRole]
    min_approvers: int = 1
    require_all_roles: bool = False
    timeout_hours: float = 24.0
    escalation_hours: float = 4.0
    allow_self_approval: bool = False
    require_reasoning: bool = True
    auto_approve_low_risk: bool = False
    risk_threshold: float = 0.5

    def validate_approvers(
        self,
        decisions: List[ApprovalDecision],
        approvers: Dict[str, Approver],
        requester_id: str
    ) -> tuple[bool, str]:
        """
        Validate if approval requirements are met.

        Returns:
            Tuple of (is_valid, reason)
        """
        approved_decisions = [d for d in decisions if d.decision == ApprovalStatus.APPROVED]

        # Check minimum approvers
        if len(approved_decisions) < self.min_approvers:
            return False, f"Need {self.min_approvers} approvers, got {len(approved_decisions)}"

        # Check self-approval
        if not self.allow_self_approval:
            for decision in approved_decisions:
                if decision.approver_id == requester_id:
                    return False, "Self-approval not allowed"

        # Check required roles
        if self.require_all_roles:
            approved_roles: Set[ApproverRole] = set()
            for decision in approved_decisions:
                approver = approvers.get(decision.approver_id)
                if approver:
                    approved_roles.update(approver.roles)

            missing_roles = set(self.required_roles) - approved_roles
            if missing_roles:
                return False, f"Missing approvals from roles: {[r.value for r in missing_roles]}"
        else:
            # At least one required role must approve
            has_required_role = False
            for decision in approved_decisions:
                approver = approvers.get(decision.approver_id)
                if approver and any(r in self.required_roles for r in approver.roles):
                    has_required_role = True
                    break

            if not has_required_role and self.required_roles:
                return False, f"No approver with required role: {[r.value for r in self.required_roles]}"

        return True, "All requirements met"


@dataclass
class ApprovalRequest:
    """A request requiring multi-approver workflow."""
    id: str
    request_type: str
    requester_id: str
    requester_name: str
    tenant_id: str
    title: str
    description: str
    risk_score: float
    policy: ApprovalPolicy
    payload: Dict[str, Any]
    status: ApprovalStatus = ApprovalStatus.PENDING
    decisions: List[ApprovalDecision] = field(default_factory=list)
    escalation_level: EscalationLevel = EscalationLevel.LEVEL_1
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deadline: Optional[datetime] = None
    constitutional_hash: str = CONSTITUTIONAL_HASH
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.constitutional_hash != CONSTITUTIONAL_HASH:
            raise ValueError(f"Invalid constitutional hash: {self.constitutional_hash}")
        if self.deadline is None:
            self.deadline = self.created_at + timedelta(hours=self.policy.timeout_hours)

    def compute_hash(self) -> str:
        """Compute unique hash for audit purposes."""
        content = json.dumps({
            "id": self.id,
            "request_type": self.request_type,
            "requester_id": self.requester_id,
            "title": self.title,
            "risk_score": self.risk_score,
            "created_at": self.created_at.isoformat(),
            "constitutional_hash": self.constitutional_hash
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "request_type": self.request_type,
            "requester_id": self.requester_id,
            "requester_name": self.requester_name,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "description": self.description,
            "risk_score": self.risk_score,
            "status": self.status.value,
            "decisions": [d.to_dict() for d in self.decisions],
            "escalation_level": self.escalation_level.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "constitutional_hash": self.constitutional_hash,
            "request_hash": self.compute_hash()
        }


class NotificationChannel(ABC):
    """Abstract base for notification channels."""

    @abstractmethod
    async def send_approval_request(
        self,
        request: ApprovalRequest,
        approvers: List[Approver]
    ) -> bool:
        pass

    @abstractmethod
    async def send_decision_notification(
        self,
        request: ApprovalRequest,
        decision: ApprovalDecision
    ) -> bool:
        pass

    @abstractmethod
    async def send_escalation_notification(
        self,
        request: ApprovalRequest,
        escalation_level: EscalationLevel
    ) -> bool:
        pass


class SlackNotificationChannel(NotificationChannel):
    """Slack notification implementation."""

    def __init__(self, webhook_url: Optional[str] = None, bot_token: Optional[str] = None):
        self.webhook_url = webhook_url or os.environ.get("SLACK_WEBHOOK_URL")
        self.bot_token = bot_token or os.environ.get("SLACK_BOT_TOKEN")

    async def send_approval_request(
        self,
        request: ApprovalRequest,
        approvers: List[Approver]
    ) -> bool:
        risk_emoji = self._get_risk_emoji(request.risk_score)
        approver_mentions = " ".join(
            f"<@{a.slack_id}>" for a in approvers if a.slack_id
        )

        payload = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{risk_emoji} Approval Required: {request.title}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Requester:*\n{request.requester_name}"},
                        {"type": "mrkdwn", "text": f"*Risk Score:*\n{request.risk_score:.2f}"},
                        {"type": "mrkdwn", "text": f"*Type:*\n{request.request_type}"},
                        {"type": "mrkdwn", "text": f"*Deadline:*\n{request.deadline.strftime('%Y-%m-%d %H:%M UTC') if request.deadline else 'N/A'}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Description:*\n{request.description[:500]}"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Approvers Needed:*\n{approver_mentions or 'See policy requirements'}"
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Approve"},
                            "style": "primary",
                            "action_id": f"approve_{request.id}"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Reject"},
                            "style": "danger",
                            "action_id": f"reject_{request.id}"
                        },
                        {
                            "type": "button",
                            "text": {"type": "plain_text", "text": "View Details"},
                            "action_id": f"details_{request.id}"
                        }
                    ]
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Request ID: `{request.id}` | Constitutional Hash: `{request.constitutional_hash}`"
                        }
                    ]
                }
            ]
        }

        # In production, this would use aiohttp to send to Slack
        logger.info(f"Slack notification for request {request.id}: {json.dumps(payload, indent=2)}")
        return True

    async def send_decision_notification(
        self,
        request: ApprovalRequest,
        decision: ApprovalDecision
    ) -> bool:
        emoji = "\u2705" if decision.decision == ApprovalStatus.APPROVED else "\u274c"
        payload = {
            "text": f"{emoji} *{decision.approver_name}* {decision.decision.value} request `{request.id}`",
            "attachments": [
                {
                    "color": "good" if decision.decision == ApprovalStatus.APPROVED else "danger",
                    "fields": [
                        {"title": "Reasoning", "value": decision.reasoning, "short": False}
                    ]
                }
            ]
        }
        logger.info(f"Slack decision notification: {json.dumps(payload, indent=2)}")
        return True

    async def send_escalation_notification(
        self,
        request: ApprovalRequest,
        escalation_level: EscalationLevel
    ) -> bool:
        level_config = {
            EscalationLevel.LEVEL_1: ("Reminder", "\u23f0"),
            EscalationLevel.LEVEL_2: ("Escalation", "\u26a0\ufe0f"),
            EscalationLevel.LEVEL_3: ("Critical", "\ud83d\udea8"),
            EscalationLevel.EXECUTIVE: ("Executive Override Required", "\ud83d\udd34")
        }
        title, emoji = level_config.get(escalation_level, ("Notification", "\ud83d\udce2"))

        payload = {
            "text": f"{emoji} *{title}*: Approval request `{request.id}` requires attention",
            "attachments": [
                {
                    "color": "warning",
                    "fields": [
                        {"title": "Request", "value": request.title, "short": True},
                        {"title": "Escalation Level", "value": str(escalation_level.value), "short": True}
                    ]
                }
            ]
        }
        logger.info(f"Slack escalation notification: {json.dumps(payload, indent=2)}")
        return True

    def _get_risk_emoji(self, score: float) -> str:
        if score >= 0.9:
            return "\ud83d\udd34"  # Red circle
        elif score >= 0.7:
            return "\ud83d\udfe0"  # Orange circle
        elif score >= 0.5:
            return "\ud83d\udfe1"  # Yellow circle
        else:
            return "\ud83d\udfe2"  # Green circle


class TeamsNotificationChannel(NotificationChannel):
    """Microsoft Teams notification implementation."""

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.environ.get("TEAMS_WEBHOOK_URL")

    async def send_approval_request(
        self,
        request: ApprovalRequest,
        approvers: List[Approver]
    ) -> bool:
        card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": self._get_theme_color(request.risk_score),
            "summary": f"Approval Required: {request.title}",
            "sections": [
                {
                    "activityTitle": f"Approval Required: {request.title}",
                    "facts": [
                        {"name": "Requester", "value": request.requester_name},
                        {"name": "Risk Score", "value": f"{request.risk_score:.2f}"},
                        {"name": "Type", "value": request.request_type},
                        {"name": "Request ID", "value": request.id}
                    ],
                    "text": request.description[:500]
                }
            ],
            "potentialAction": [
                {
                    "@type": "ActionCard",
                    "name": "Respond",
                    "inputs": [
                        {
                            "@type": "TextInput",
                            "id": "reasoning",
                            "title": "Reasoning (required)"
                        }
                    ],
                    "actions": [
                        {
                            "@type": "HttpPOST",
                            "name": "Approve",
                            "target": f"{{{{ACGS_API_URL}}}}/approvals/{request.id}/approve"
                        },
                        {
                            "@type": "HttpPOST",
                            "name": "Reject",
                            "target": f"{{{{ACGS_API_URL}}}}/approvals/{request.id}/reject"
                        }
                    ]
                }
            ]
        }
        logger.info(f"Teams notification for request {request.id}: {json.dumps(card, indent=2)}")
        return True

    async def send_decision_notification(
        self,
        request: ApprovalRequest,
        decision: ApprovalDecision
    ) -> bool:
        logger.info(f"Teams decision notification for {request.id}: {decision.decision.value}")
        return True

    async def send_escalation_notification(
        self,
        request: ApprovalRequest,
        escalation_level: EscalationLevel
    ) -> bool:
        logger.info(f"Teams escalation for {request.id}: level {escalation_level.value}")
        return True

    def _get_theme_color(self, score: float) -> str:
        if score >= 0.9:
            return "FF0000"
        elif score >= 0.7:
            return "FFA500"
        elif score >= 0.5:
            return "FFFF00"
        else:
            return "00FF00"


class MultiApproverWorkflowEngine:
    """
    Enterprise-grade multi-approver workflow engine.

    Features:
    - Configurable approval policies
    - Multiple notification channels
    - Automatic escalation
    - Timeout handling
    - Audit trail integration
    """

    def __init__(
        self,
        notification_channels: Optional[List[NotificationChannel]] = None,
        audit_callback: Optional[Callable[[ApprovalRequest, ApprovalDecision], None]] = None
    ):
        self.notification_channels = notification_channels or [SlackNotificationChannel()]
        self.audit_callback = audit_callback

        # Storage (in production, use Redis or database)
        self._requests: Dict[str, ApprovalRequest] = {}
        self._approvers: Dict[str, Approver] = {}
        self._policies: Dict[str, ApprovalPolicy] = {}

        # Background tasks
        self._escalation_task: Optional[asyncio.Task] = None
        self._running = False

        # Default policies
        self._initialize_default_policies()

    def _initialize_default_policies(self):
        """Initialize default approval policies."""
        self._policies = {
            "high_risk_action": ApprovalPolicy(
                name="High Risk Action",
                required_roles=[ApproverRole.SECURITY_TEAM, ApproverRole.COMPLIANCE_TEAM],
                min_approvers=2,
                require_all_roles=True,
                timeout_hours=24.0,
                escalation_hours=4.0,
                risk_threshold=0.8
            ),
            "policy_change": ApprovalPolicy(
                name="Policy Change",
                required_roles=[ApproverRole.POLICY_OWNER, ApproverRole.PLATFORM_ADMIN],
                min_approvers=2,
                require_all_roles=True,
                timeout_hours=48.0,
                escalation_hours=8.0,
                risk_threshold=0.5
            ),
            "critical_deployment": ApprovalPolicy(
                name="Critical Deployment",
                required_roles=[
                    ApproverRole.ENGINEERING_LEAD,
                    ApproverRole.SECURITY_TEAM,
                    ApproverRole.ON_CALL
                ],
                min_approvers=3,
                require_all_roles=True,
                timeout_hours=4.0,
                escalation_hours=1.0,
                risk_threshold=0.9
            ),
            "standard_request": ApprovalPolicy(
                name="Standard Request",
                required_roles=[ApproverRole.TENANT_ADMIN],
                min_approvers=1,
                require_all_roles=False,
                timeout_hours=72.0,
                escalation_hours=24.0,
                auto_approve_low_risk=True,
                risk_threshold=0.3
            )
        }

    async def start(self):
        """Start background tasks."""
        self._running = True
        self._escalation_task = asyncio.create_task(self._escalation_loop())
        logger.info("MultiApproverWorkflowEngine started")

    async def stop(self):
        """Stop background tasks."""
        self._running = False
        if self._escalation_task:
            self._escalation_task.cancel()
            try:
                await self._escalation_task
            except asyncio.CancelledError:
                pass
        logger.info("MultiApproverWorkflowEngine stopped")

    def register_approver(self, approver: Approver):
        """Register an approver."""
        self._approvers[approver.id] = approver
        logger.info(f"Registered approver: {approver.id} ({approver.name})")

    def register_policy(self, policy_id: str, policy: ApprovalPolicy):
        """Register a custom approval policy."""
        self._policies[policy_id] = policy
        logger.info(f"Registered policy: {policy_id}")

    async def create_request(
        self,
        request_type: str,
        requester_id: str,
        requester_name: str,
        tenant_id: str,
        title: str,
        description: str,
        risk_score: float,
        payload: Dict[str, Any],
        policy_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Args:
            request_type: Type of request
            requester_id: ID of the requester
            requester_name: Name of the requester
            tenant_id: Tenant ID
            title: Request title
            description: Detailed description
            risk_score: Risk score (0.0 - 1.0)
            payload: Request payload data
            policy_id: Optional policy ID (defaults to risk-based selection)
            metadata: Additional metadata

        Returns:
            Created ApprovalRequest
        """
        # Select policy based on risk if not specified
        if policy_id is None:
            policy_id = self._select_policy_for_risk(risk_score)

        policy = self._policies.get(policy_id)
        if not policy:
            raise ValueError(f"Unknown policy: {policy_id}")

        # Check auto-approve
        if policy.auto_approve_low_risk and risk_score < policy.risk_threshold:
            logger.info(f"Auto-approving low-risk request (score: {risk_score})")
            request = ApprovalRequest(
                id=str(uuid4()),
                request_type=request_type,
                requester_id=requester_id,
                requester_name=requester_name,
                tenant_id=tenant_id,
                title=title,
                description=description,
                risk_score=risk_score,
                policy=policy,
                payload=payload,
                status=ApprovalStatus.APPROVED,
                metadata=metadata or {}
            )
            self._requests[request.id] = request
            return request

        # Create pending request
        request = ApprovalRequest(
            id=str(uuid4()),
            request_type=request_type,
            requester_id=requester_id,
            requester_name=requester_name,
            tenant_id=tenant_id,
            title=title,
            description=description,
            risk_score=risk_score,
            policy=policy,
            payload=payload,
            metadata=metadata or {}
        )

        self._requests[request.id] = request

        # Notify approvers
        eligible_approvers = self._get_eligible_approvers(policy, tenant_id)
        for channel in self.notification_channels:
            try:
                await channel.send_approval_request(request, eligible_approvers)
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")

        logger.info(f"Created approval request: {request.id}")
        return request

    async def submit_decision(
        self,
        request_id: str,
        approver_id: str,
        decision: ApprovalStatus,
        reasoning: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> tuple[bool, str]:
        """
        Submit an approval decision.

        Returns:
            Tuple of (success, message)
        """
        request = self._requests.get(request_id)
        if not request:
            return False, "Request not found"

        if request.status != ApprovalStatus.PENDING:
            return False, f"Request is not pending (status: {request.status.value})"

        approver = self._approvers.get(approver_id)
        if not approver:
            return False, "Approver not registered"

        # Check if already decided
        if any(d.approver_id == approver_id for d in request.decisions):
            return False, "Approver already submitted decision"

        # Validate reasoning requirement
        if request.policy.require_reasoning and not reasoning.strip():
            return False, "Reasoning is required"

        # Record decision
        approval_decision = ApprovalDecision(
            approver_id=approver_id,
            approver_name=approver.name,
            decision=decision,
            reasoning=reasoning,
            metadata=metadata or {}
        )
        request.decisions.append(approval_decision)
        request.updated_at = datetime.now(timezone.utc)

        # Notify channels
        for channel in self.notification_channels:
            try:
                await channel.send_decision_notification(request, approval_decision)
            except Exception as e:
                logger.error(f"Failed to send decision notification: {e}")

        # Audit callback
        if self.audit_callback:
            try:
                self.audit_callback(request, approval_decision)
            except Exception as e:
                logger.error(f"Audit callback failed: {e}")

        # Check if we have enough decisions to finalize
        if decision == ApprovalStatus.REJECTED:
            # Single rejection fails the request
            request.status = ApprovalStatus.REJECTED
            logger.info(f"Request {request_id} rejected by {approver.name}")
            return True, "Request rejected"

        # Check if approval requirements are met
        is_valid, reason = request.policy.validate_approvers(
            request.decisions,
            self._approvers,
            request.requester_id
        )

        if is_valid:
            request.status = ApprovalStatus.APPROVED
            logger.info(f"Request {request_id} approved")
            return True, "Request approved"

        logger.info(f"Decision recorded for {request_id}. {reason}")
        return True, f"Decision recorded. {reason}"

    async def cancel_request(self, request_id: str, reason: str) -> bool:
        """Cancel a pending request."""
        request = self._requests.get(request_id)
        if not request or request.status != ApprovalStatus.PENDING:
            return False

        request.status = ApprovalStatus.CANCELLED
        request.updated_at = datetime.now(timezone.utc)
        request.metadata["cancellation_reason"] = reason

        logger.info(f"Request {request_id} cancelled: {reason}")
        return True

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a request by ID."""
        return self._requests.get(request_id)

    def get_pending_requests(
        self,
        tenant_id: Optional[str] = None,
        approver_id: Optional[str] = None
    ) -> List[ApprovalRequest]:
        """Get pending requests, optionally filtered."""
        requests = [
            r for r in self._requests.values()
            if r.status == ApprovalStatus.PENDING
        ]

        if tenant_id:
            requests = [r for r in requests if r.tenant_id == tenant_id]

        if approver_id:
            approver = self._approvers.get(approver_id)
            if approver:
                requests = [
                    r for r in requests
                    if any(role in r.policy.required_roles for role in approver.roles)
                    and not any(d.approver_id == approver_id for d in r.decisions)
                ]

        return sorted(requests, key=lambda r: r.created_at, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        """Get workflow statistics."""
        total = len(self._requests)
        by_status = {}
        for status in ApprovalStatus:
            by_status[status.value] = len([
                r for r in self._requests.values() if r.status == status
            ])

        return {
            "total_requests": total,
            "by_status": by_status,
            "registered_approvers": len(self._approvers),
            "registered_policies": len(self._policies),
            "constitutional_hash": CONSTITUTIONAL_HASH
        }

    def _select_policy_for_risk(self, risk_score: float) -> str:
        """Select appropriate policy based on risk score."""
        if risk_score >= 0.9:
            return "critical_deployment"
        elif risk_score >= 0.7:
            return "high_risk_action"
        elif risk_score >= 0.5:
            return "policy_change"
        else:
            return "standard_request"

    def _get_eligible_approvers(
        self,
        policy: ApprovalPolicy,
        tenant_id: str
    ) -> List[Approver]:
        """Get approvers eligible for a policy."""
        return [
            a for a in self._approvers.values()
            if a.is_active and any(r in policy.required_roles for r in a.roles)
        ]

    async def _escalation_loop(self):
        """Background task for handling escalations and timeouts."""
        while self._running:
            try:
                now = datetime.now(timezone.utc)

                for request in list(self._requests.values()):
                    if request.status != ApprovalStatus.PENDING:
                        continue

                    # Check timeout
                    if request.deadline and now > request.deadline:
                        request.status = ApprovalStatus.TIMEOUT
                        logger.warning(f"Request {request.id} timed out")
                        continue

                    # Check escalation
                    time_since_creation = (now - request.created_at).total_seconds() / 3600
                    escalation_hours = request.policy.escalation_hours

                    new_level = None
                    if time_since_creation >= escalation_hours * 3:
                        new_level = EscalationLevel.EXECUTIVE
                    elif time_since_creation >= escalation_hours * 2:
                        new_level = EscalationLevel.LEVEL_3
                    elif time_since_creation >= escalation_hours:
                        new_level = EscalationLevel.LEVEL_2

                    if new_level and new_level.value > request.escalation_level.value:
                        request.escalation_level = new_level
                        for channel in self.notification_channels:
                            try:
                                await channel.send_escalation_notification(request, new_level)
                            except Exception as e:
                                logger.error(f"Failed to send escalation: {e}")

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Escalation loop error: {e}")
                await asyncio.sleep(60)


# Convenience singleton
_workflow_engine: Optional[MultiApproverWorkflowEngine] = None


def get_workflow_engine() -> Optional[MultiApproverWorkflowEngine]:
    """Get the global workflow engine instance."""
    return _workflow_engine


async def initialize_workflow_engine(
    notification_channels: Optional[List[NotificationChannel]] = None,
    audit_callback: Optional[Callable[[ApprovalRequest, ApprovalDecision], None]] = None
) -> MultiApproverWorkflowEngine:
    """Initialize the global workflow engine."""
    global _workflow_engine
    _workflow_engine = MultiApproverWorkflowEngine(
        notification_channels=notification_channels,
        audit_callback=audit_callback
    )
    await _workflow_engine.start()
    return _workflow_engine


async def shutdown_workflow_engine():
    """Shutdown the global workflow engine."""
    global _workflow_engine
    if _workflow_engine:
        await _workflow_engine.stop()
        _workflow_engine = None


__all__ = [
    "CONSTITUTIONAL_HASH",
    "ApprovalStatus",
    "ApproverRole",
    "EscalationLevel",
    "Approver",
    "ApprovalDecision",
    "ApprovalPolicy",
    "ApprovalRequest",
    "NotificationChannel",
    "SlackNotificationChannel",
    "TeamsNotificationChannel",
    "MultiApproverWorkflowEngine",
    "get_workflow_engine",
    "initialize_workflow_engine",
    "shutdown_workflow_engine"
]
