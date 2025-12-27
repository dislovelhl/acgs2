"""
ACGS-2 SDK Models
Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from acgs2_sdk.constants import CONSTITUTIONAL_HASH


# =============================================================================
# Enums
# =============================================================================


class MessageType(str, Enum):
    """Agent message types."""

    COMMAND = "command"
    QUERY = "query"
    EVENT = "event"
    RESPONSE = "response"
    ERROR = "error"


class Priority(str, Enum):
    """Message priority levels."""

    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class PolicyStatus(str, Enum):
    """Policy lifecycle status."""

    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class ApprovalStatus(str, Enum):
    """Approval request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class ComplianceStatus(str, Enum):
    """Compliance check status."""

    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PENDING_REVIEW = "pending_review"
    UNKNOWN = "unknown"


class EventSeverity(str, Enum):
    """Audit event severity levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventCategory(str, Enum):
    """Audit event categories."""

    GOVERNANCE = "governance"
    POLICY = "policy"
    AGENT = "agent"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    AUDIT = "audit"
    SYSTEM = "system"


# =============================================================================
# Base Models
# =============================================================================


class ConstitutionalModel(BaseModel):
    """Base model with constitutional hash validation."""

    constitutional_hash: str = Field(
        default=CONSTITUTIONAL_HASH,
        alias="constitutionalHash",
    )

    @field_validator("constitutional_hash")
    @classmethod
    def validate_hash(cls, v: str) -> str:
        if v != CONSTITUTIONAL_HASH:
            raise ValueError(
                f"Constitutional hash mismatch: expected {CONSTITUTIONAL_HASH}, got {v}"
            )
        return v

    model_config = {"populate_by_name": True}


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated API response."""

    data: list[T]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
    total_pages: int = Field(alias="totalPages")

    model_config = {"populate_by_name": True}


# =============================================================================
# Agent Models
# =============================================================================


class AgentMessage(ConstitutionalModel):
    """Agent communication message."""

    id: UUID
    type: MessageType
    priority: Priority = Priority.NORMAL
    source_agent_id: str = Field(alias="sourceAgentId")
    target_agent_id: str | None = Field(default=None, alias="targetAgentId")
    payload: dict[str, Any]
    timestamp: datetime
    correlation_id: UUID | None = Field(default=None, alias="correlationId")
    metadata: dict[str, str] | None = None


class AgentInfo(BaseModel):
    """Agent information."""

    id: str
    name: str
    type: str
    status: str
    capabilities: list[str]
    metadata: dict[str, str]
    last_seen: datetime = Field(alias="lastSeen")
    constitutional_hash: str = Field(alias="constitutionalHash")

    model_config = {"populate_by_name": True}


# =============================================================================
# Policy Models
# =============================================================================


class Policy(ConstitutionalModel):
    """Policy definition."""

    id: UUID
    name: str = Field(min_length=1, max_length=255)
    version: str
    description: str | None = None
    status: PolicyStatus
    rules: list[dict[str, Any]]
    tenant_id: str | None = Field(default=None, alias="tenantId")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    created_by: str = Field(alias="createdBy")
    tags: list[str] | None = None
    compliance_tags: list[str] | None = Field(default=None, alias="complianceTags")


# =============================================================================
# Compliance Models
# =============================================================================


class ComplianceViolation(BaseModel):
    """Compliance rule violation."""

    rule_id: str = Field(alias="ruleId")
    message: str
    severity: EventSeverity

    model_config = {"populate_by_name": True}


class ComplianceResult(ConstitutionalModel):
    """Compliance validation result."""

    policy_id: UUID = Field(alias="policyId")
    status: ComplianceStatus
    score: float = Field(ge=0, le=100)
    violations: list[ComplianceViolation]
    timestamp: datetime


# =============================================================================
# Approval Models
# =============================================================================


class ApprovalDecision(BaseModel):
    """Individual approval decision."""

    approver_id: str = Field(alias="approverId")
    decision: ApprovalStatus
    reasoning: str | None = None
    timestamp: datetime

    model_config = {"populate_by_name": True}


class ApprovalRequest(ConstitutionalModel):
    """Approval request."""

    id: UUID
    request_type: str = Field(alias="requestType")
    requester_id: str = Field(alias="requesterId")
    status: ApprovalStatus
    risk_score: float = Field(ge=0, le=100, alias="riskScore")
    required_approvers: int = Field(ge=1, alias="requiredApprovers")
    current_approvals: int = Field(alias="currentApprovals")
    decisions: list[ApprovalDecision]
    payload: dict[str, Any]
    created_at: datetime = Field(alias="createdAt")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")


# =============================================================================
# Audit Models
# =============================================================================


class AuditEvent(ConstitutionalModel):
    """Audit event record."""

    id: UUID
    category: EventCategory
    severity: EventSeverity
    action: str
    actor: str
    resource: str
    resource_id: str | None = Field(default=None, alias="resourceId")
    outcome: str  # "success" | "failure" | "partial"
    details: dict[str, Any] | None = None
    timestamp: datetime
    tenant_id: str | None = Field(default=None, alias="tenantId")
    correlation_id: UUID | None = Field(default=None, alias="correlationId")


# =============================================================================
# Governance Models
# =============================================================================


class GovernanceDecision(ConstitutionalModel):
    """Governance decision record."""

    id: UUID
    request_id: UUID = Field(alias="requestId")
    decision: str  # "approve" | "deny" | "escalate"
    reasoning: str
    policy_violations: list[str] = Field(alias="policyViolations")
    risk_score: float = Field(ge=0, le=100, alias="riskScore")
    reviewer_ids: list[str] = Field(alias="reviewerIds")
    timestamp: datetime
    blockchain_anchor: str | None = Field(default=None, alias="blockchainAnchor")


# =============================================================================
# Request Models
# =============================================================================


class CreatePolicyRequest(BaseModel):
    """Request to create a new policy."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    rules: list[dict[str, Any]]
    tags: list[str] | None = None
    compliance_tags: list[str] | None = Field(default=None, alias="complianceTags")

    model_config = {"populate_by_name": True}


class UpdatePolicyRequest(BaseModel):
    """Request to update a policy."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    rules: list[dict[str, Any]] | None = None
    status: PolicyStatus | None = None
    tags: list[str] | None = None
    compliance_tags: list[str] | None = Field(default=None, alias="complianceTags")

    model_config = {"populate_by_name": True}


class SendMessageRequest(BaseModel):
    """Request to send an agent message."""

    type: MessageType
    priority: Priority = Priority.NORMAL
    target_agent_id: str | None = Field(default=None, alias="targetAgentId")
    payload: dict[str, Any]
    correlation_id: str | None = Field(default=None, alias="correlationId")
    metadata: dict[str, str] | None = None

    model_config = {"populate_by_name": True}


class CreateApprovalRequest(BaseModel):
    """Request to create an approval request."""

    request_type: str = Field(alias="requestType")
    payload: dict[str, Any]
    risk_score: float | None = Field(default=None, ge=0, le=100, alias="riskScore")
    required_approvers: int | None = Field(default=None, ge=1, alias="requiredApprovers")

    model_config = {"populate_by_name": True}


class SubmitApprovalDecision(BaseModel):
    """Request to submit an approval decision."""

    decision: str  # "approve" | "reject"
    reasoning: str


class ValidateComplianceRequest(BaseModel):
    """Request to validate compliance."""

    policy_id: str = Field(alias="policyId")
    context: dict[str, Any]

    model_config = {"populate_by_name": True}


class QueryAuditEventsRequest(BaseModel):
    """Request to query audit events."""

    category: EventCategory | None = None
    severity: EventSeverity | None = None
    actor: str | None = None
    resource: str | None = None
    start_time: datetime | None = Field(default=None, alias="startTime")
    end_time: datetime | None = Field(default=None, alias="endTime")
    page: int = 1
    page_size: int = Field(default=50, alias="pageSize")
    sort_by: str | None = Field(default=None, alias="sortBy")
    sort_order: str | None = Field(default=None, alias="sortOrder")

    model_config = {"populate_by_name": True}
