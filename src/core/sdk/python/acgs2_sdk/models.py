"""
ACGS-2 SDK Models
Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar, Union
from uuid import UUID

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONValue = Union[str, int, float, bool, None, dict[str, Any], list[Any]]  # type: ignore[misc]
    JSONDict = dict[str, JSONValue]  # type: ignore[misc]

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
    ML_MODEL = "ml_model"
    PREDICTION = "prediction"


class ModelTrainingStatus(str, Enum):
    """ML model training status."""

    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class DriftDirection(str, Enum):
    """Model drift direction."""

    NONE = "none"
    INCREASE = "increase"
    DECREASE = "decrease"


class ABNTestStatus(str, Enum):
    """A/B test status."""

    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


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
    rules: list[JSONDict] | None = None
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
    details: JSONDict | None = None
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
# ML Governance Models
# =============================================================================


class MLModel(ConstitutionalModel):
    """ML model information."""

    id: str
    name: str
    version: str
    description: str | None = None
    model_type: str = Field(alias="modelType")
    framework: str
    accuracy_score: float | None = Field(default=None, alias="accuracyScore")
    training_status: ModelTrainingStatus = Field(alias="trainingStatus")
    last_trained_at: datetime | None = Field(default=None, alias="lastTrainedAt")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class ModelPrediction(ConstitutionalModel):
    """ML model prediction result."""

    id: str
    input_features: JSONDict = Field(alias="inputFeatures")
    prediction: JSONValue
    confidence_score: float | None = Field(default=None, alias="confidenceScore")
    prediction_metadata: JSONDict | None = Field(default=None, alias="predictionMetadata")
    timestamp: datetime


class DriftDetection(ConstitutionalModel):
    """Model drift detection result."""

    model_id: str = Field(alias="modelId")
    drift_score: float = Field(alias="driftScore")
    drift_direction: DriftDirection = Field(alias="driftDirection")
    baseline_accuracy: float = Field(alias="baselineAccuracy")
    current_accuracy: float = Field(alias="currentAccuracy")
    features_affected: list[str] = Field(alias="featuresAffected")
    detected_at: datetime = Field(alias="detectedAt")
    recommendations: list[str]


class ABNTest(ConstitutionalModel):
    """A/B test configuration."""

    id: str
    name: str
    description: str | None = None
    model_a_id: str = Field(alias="modelAId")
    model_b_id: str = Field(alias="modelBId")
    status: ABNTestStatus
    test_duration_days: int = Field(alias="testDurationDays")
    traffic_split_percentage: float = Field(alias="trafficSplitPercentage")  # A/B split
    success_metric: str = Field(alias="successMetric")
    created_at: datetime = Field(alias="createdAt")
    completed_at: datetime | None = Field(default=None, alias="completedAt")


class FeedbackSubmission(ConstitutionalModel):
    """User feedback for model training."""

    prediction_id: str | None = Field(default=None, alias="predictionId")
    model_id: str = Field(alias="modelId")
    feedback_type: str = Field(alias="feedbackType")  # "correction" | "rating" | "explanation"
    feedback_value: JSONValue = Field(
        alias="feedbackValue"
    )  # Correct value, rating score, or explanation
    user_id: str | None = Field(default=None, alias="userId")
    context: JSONDict | None = None
    submitted_at: datetime = Field(alias="submittedAt")


# =============================================================================
# Request Models
# =============================================================================


class CreatePolicyRequest(BaseModel):
    """Request to create a new policy."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    rules: list[JSONDict]
    tags: list[str] | None = None
    compliance_tags: list[str] | None = Field(default=None, alias="complianceTags")

    model_config = {"populate_by_name": True}


class UpdatePolicyRequest(BaseModel):
    """Request to update a policy."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    rules: list[JSONDict] | None = None
    status: PolicyStatus | None = None
    tags: list[str] | None = None
    compliance_tags: list[str] | None = Field(default=None, alias="complianceTags")

    model_config = {"populate_by_name": True}


class SendMessageRequest(BaseModel):
    """Request to send an agent message."""

    type: MessageType
    priority: Priority = Priority.NORMAL
    target_agent_id: str | None = Field(default=None, alias="targetAgentId")
    payload: JSONDict
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
    context: JSONDict

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


class CreateMLModelRequest(BaseModel):
    """Request to create/register an ML model."""

    name: str
    description: str | None = None
    model_type: str = Field(alias="modelType")
    framework: str
    initial_accuracy_score: float | None = Field(default=None, alias="initialAccuracyScore")

    model_config = {"populate_by_name": True}


class UpdateMLModelRequest(BaseModel):
    """Request to update an ML model."""

    name: str | None = None
    description: str | None = None
    accuracy_score: float | None = Field(default=None, alias="accuracyScore")

    model_config = {"populate_by_name": True}


class MakePredictionRequest(BaseModel):
    """Request to make a prediction with an ML model."""

    model_id: str = Field(alias="modelId")
    features: JSONDict
    include_confidence: bool | None = Field(default=None, alias="includeConfidence")

    model_config = {"populate_by_name": True}


class SubmitFeedbackRequest(BaseModel):
    """Request to submit feedback for model training."""

    prediction_id: str | None = Field(default=None, alias="predictionId")
    model_id: str = Field(alias="modelId")
    feedback_type: str = Field(alias="feedbackType")
    feedback_value: JSONValue = Field(alias="feedbackValue")
    user_id: str | None = Field(default=None, alias="userId")
    context: JSONDict | None = None

    model_config = {"populate_by_name": True}


class CreateABNTestRequest(BaseModel):
    """Request to create an A/B test."""

    name: str
    description: str | None = None
    model_a_id: str = Field(alias="modelAId")
    model_b_id: str = Field(alias="modelBId")
    test_duration_days: int = Field(alias="testDurationDays")
    traffic_split_percentage: float = Field(alias="trafficSplitPercentage")
    success_metric: str = Field(alias="successMetric")

    model_config = {"populate_by_name": True}
