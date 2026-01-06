"""Constitutional Hash: cdd01ef066bc6cf2
Core models for HITL approval workflows and chains
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class ApprovalStatus(str, Enum):
    """Approval request status enumeration"""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalPriority(str, Enum):
    """Approval priority levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationChannel(str, Enum):
    """Supported notification channels"""

    SLACK = "slack"
    TEAMS = "teams"
    PAGERDUTY = "pagerduty"
    EMAIL = "email"


class EscalationRule(BaseModel):
    """Escalation rule configuration"""

    delay_minutes: int = Field(..., description="Minutes to wait before escalating", ge=1, le=1440)
    escalate_to: List[str] = Field(..., description="User IDs or role names to escalate to")
    notification_channels: List[NotificationChannel] = Field(
        default_factory=list, description="Channels to notify on escalation"
    )
    max_escalations: int = Field(
        default=3, description="Maximum number of escalation levels", ge=1, le=10
    )


class ApprovalStep(BaseModel):
    """Individual step in an approval chain"""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique step identifier")
    name: str = Field(..., description="Human-readable step name")
    description: Optional[str] = Field(None, description="Step description")
    approvers: List[str] = Field(
        ..., description="User IDs or role names that can approve this step"
    )
    required_approvals: int = Field(
        default=1, description="Number of approvals required from the approvers list", ge=1
    )
    timeout_minutes: int = Field(
        default=60, description="Minutes to wait for approval before escalation", ge=1, le=1440
    )
    escalation_rules: List[EscalationRule] = Field(
        default_factory=list, description="Escalation rules for this step"
    )
    notification_channels: List[NotificationChannel] = Field(
        default_factory=list, description="Notification channels for this step"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional step metadata")


class ApprovalChain(BaseModel):
    """Complete approval chain configuration"""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique chain identifier"
    )
    name: str = Field(..., description="Human-readable chain name")
    description: Optional[str] = Field(None, description="Chain description")
    trigger_conditions: Dict[str, Any] = Field(
        ..., description="Conditions that trigger this approval chain"
    )
    steps: List[ApprovalStep] = Field(..., description="Sequential approval steps")
    priority: ApprovalPriority = Field(
        default=ApprovalPriority.MEDIUM, description="Chain priority level"
    )
    sla_minutes: int = Field(
        default=480, description="SLA in minutes for complete approval", ge=1, le=10080
    )
    active: bool = Field(default=True, description="Whether this chain is active")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional chain metadata")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Chain creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Chain last update timestamp",
    )

    @validator("steps")
    def validate_steps(cls, v):
        if not v:
            raise ValueError("Approval chain must have at least one step")
        return v


class ApprovalRequest(BaseModel):
    """Approval request instance"""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique request identifier"
    )
    chain_id: str = Field(..., description="ID of the approval chain")
    title: str = Field(..., description="Human-readable request title")
    description: str = Field(..., description="Detailed request description")
    requester_id: str = Field(..., description="User ID of the requester")
    priority: ApprovalPriority = Field(
        default=ApprovalPriority.MEDIUM, description="Request priority"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict, description="Request context (AI decision details, etc.)"
    )
    current_step_index: int = Field(default=0, description="Current step in the approval chain")
    status: ApprovalStatus = Field(
        default=ApprovalStatus.PENDING, description="Current approval status"
    )
    approvals: List[Dict[str, Any]] = Field(
        default_factory=list, description="List of approval decisions"
    )
    notifications_sent: List[Dict[str, Any]] = Field(
        default_factory=list, description="Notification history"
    )
    escalations: List[Dict[str, Any]] = Field(
        default_factory=list, description="Escalation history"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Request creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Request last update timestamp",
    )
    expires_at: Optional[datetime] = Field(None, description="Request expiration timestamp")


class ApprovalDecision(BaseModel):
    """Individual approval decision"""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique decision identifier"
    )
    request_id: str = Field(..., description="Approval request ID")
    step_index: int = Field(..., description="Step index in the approval chain")
    approver_id: str = Field(..., description="User ID of the approver")
    decision: ApprovalStatus = Field(..., description="Approval decision")
    rationale: Optional[str] = Field(None, description="Decision rationale")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional decision metadata"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Decision timestamp"
    )


class NotificationTemplate(BaseModel):
    """Notification template configuration"""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique template identifier"
    )
    name: str = Field(..., description="Template name")
    channel: NotificationChannel = Field(..., description="Notification channel")
    subject_template: str = Field(..., description="Subject line template")
    body_template: str = Field(..., description="Message body template")
    variables: List[str] = Field(default_factory=list, description="Available template variables")
    active: bool = Field(default=True, description="Whether template is active")


class AuditEntry(BaseModel):
    """Audit trail entry"""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="Unique audit entry identifier"
    )
    entity_type: str = Field(
        ..., description="Type of entity being audited (request, decision, etc.)"
    )
    entity_id: str = Field(..., description="ID of the entity being audited")
    action: str = Field(..., description="Action performed")
    actor_id: str = Field(..., description="User ID performing the action")
    details: Dict[str, Any] = Field(default_factory=dict, description="Action details")
    ip_address: Optional[str] = Field(None, description="IP address of the actor")
    user_agent: Optional[str] = Field(None, description="User agent of the actor")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Audit timestamp"
    )


# API Request/Response models
class CreateApprovalRequest(BaseModel):
    """Request to create a new approval"""

    chain_id: str = Field(..., description="ID of the approval chain to use")
    title: str = Field(..., description="Approval request title")
    description: str = Field(..., description="Approval request description")
    requester_id: str = Field(..., description="User ID of the requester")
    priority: ApprovalPriority = Field(
        default=ApprovalPriority.MEDIUM, description="Request priority"
    )
    context: Dict[str, Any] = Field(default_factory=dict, description="Request context")


class ApprovalResponse(BaseModel):
    """Approval decision response"""

    request_id: str = Field(..., description="Approval request ID")
    step_index: int = Field(..., description="Step index being approved")
    approver_id: str = Field(..., description="User ID of the approver")
    decision: ApprovalStatus = Field(..., description="Approval decision")
    rationale: Optional[str] = Field(None, description="Decision rationale")


class ApprovalStatusResponse(BaseModel):
    """Approval status response"""

    request: ApprovalRequest = Field(..., description="Approval request details")
    chain: ApprovalChain = Field(..., description="Approval chain configuration")
    current_step: Optional[ApprovalStep] = Field(None, description="Current approval step")
    time_remaining_minutes: Optional[int] = Field(
        None, description="Minutes remaining for current step"
    )
    can_approve: bool = Field(default=False, description="Whether current user can approve")
