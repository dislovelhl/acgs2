"""
HITL Approvals Service Data Models

Pydantic models for approval workflows, escalation policies, and audit trail.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApprovalStatus(str, Enum):
    """Status of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalPriority(str, Enum):
    """Priority level for approval requests."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalLevel(BaseModel):
    """A single level in an approval chain."""

    level: int = Field(..., ge=1, description="Approval level number (1-based)")
    role: str = Field(..., description="Required role for approval at this level")
    approvers: List[str] = Field(
        default_factory=list, description="List of user IDs who can approve"
    )
    timeout_minutes: Optional[int] = Field(
        None, description="Timeout before auto-escalation (overrides default)"
    )


class ApprovalChain(BaseModel):
    """Definition of a multi-level approval chain."""

    chain_id: str = Field(..., description="Unique identifier for the approval chain")
    name: str = Field(..., description="Human-readable name for the chain")
    description: Optional[str] = Field(None, description="Description of when this chain applies")
    levels: List[ApprovalLevel] = Field(
        ..., min_length=1, description="Ordered list of approval levels"
    )
    fallback_approver: Optional[str] = Field(
        None, description="Emergency approver if chain is exhausted"
    )


class ApprovalRequest(BaseModel):
    """A request for approval in the HITL workflow."""

    request_id: str = Field(..., description="Unique identifier for the request")
    chain_id: str = Field(..., description="ID of the approval chain to use")
    current_level: int = Field(1, ge=1, description="Current level in the approval chain")
    status: ApprovalStatus = Field(ApprovalStatus.PENDING, description="Current status")
    priority: ApprovalPriority = Field(ApprovalPriority.MEDIUM, description="Priority level")

    # Decision context
    decision_type: str = Field(..., description="Type of AI decision requiring approval")
    decision_context: Dict[str, Any] = Field(
        default_factory=dict, description="Context data for the decision"
    )
    impact_level: str = Field(..., description="Impact level (low, medium, high, critical)")

    # Requestor information
    requestor_id: str = Field(..., description="ID of the user/system requesting approval")
    requestor_service: Optional[str] = Field(None, description="Service that initiated the request")

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the request was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the request was last updated"
    )
    escalated_at: Optional[datetime] = Field(None, description="When the request was escalated")
    resolved_at: Optional[datetime] = Field(None, description="When the request was resolved")

    # Escalation tracking
    escalation_count: int = Field(0, ge=0, description="Number of escalations")
    escalation_history: List[Dict[str, Any]] = Field(
        default_factory=list, description="History of escalation events"
    )


class ApprovalDecision(BaseModel):
    """A decision made by an approver."""

    request_id: str = Field(..., description="ID of the approval request")
    approver_id: str = Field(..., description="ID of the user making the decision")
    approver_role: str = Field(..., description="Role of the approver")
    decision: ApprovalStatus = Field(..., description="The decision made")
    rationale: Optional[str] = Field(None, description="Reason for the decision")
    conditions: Optional[str] = Field(None, description="Any conditions attached to approval")
    decided_at: datetime = Field(
        default_factory=datetime.utcnow, description="When the decision was made"
    )


class AuditEvent(BaseModel):
    """An immutable audit log entry for approval events."""

    event_id: str = Field(..., description="Unique identifier for the audit event")
    event_type: str = Field(
        ..., description="Type of event (created, approved, rejected, escalated)"
    )
    request_id: str = Field(..., description="ID of the related approval request")
    actor_id: str = Field(..., description="ID of the user/system that triggered the event")
    actor_role: Optional[str] = Field(None, description="Role of the actor")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the event occurred"
    )
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional event details")
    previous_state: Optional[str] = Field(None, description="State before the event")
    new_state: Optional[str] = Field(None, description="State after the event")


class NotificationPayload(BaseModel):
    """Payload for sending notifications via external providers."""

    request_id: str = Field(..., description="ID of the approval request")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message body")
    approval_url: str = Field(..., description="URL to the approval interface")
    priority: ApprovalPriority = Field(ApprovalPriority.MEDIUM, description="Notification priority")
    channels: List[str] = Field(default_factory=list, description="Target notification channels")
    recipients: List[str] = Field(default_factory=list, description="Target user/role IDs")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for the notification"
    )


class EscalationPolicy(BaseModel):
    """Policy defining escalation behavior."""

    policy_id: str = Field(..., description="Unique identifier for the policy")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Policy description")
    priority: ApprovalPriority = Field(..., description="Priority level this policy applies to")
    timeout_minutes: int = Field(30, ge=1, description="Minutes before escalation triggers")
    max_escalations: int = Field(3, ge=1, description="Maximum number of escalations allowed")
    notify_on_escalation: bool = Field(
        True, description="Whether to send notification on escalation"
    )
    pagerduty_on_critical: bool = Field(
        True, description="Whether to trigger PagerDuty for critical escalations"
    )
