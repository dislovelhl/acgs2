"""
Pydantic models for webhook framework.

Defines models for webhook subscriptions, events, deliveries, and results
with comprehensive validation, authentication support, and delivery tracking.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

from ..integration_types import JSONDict, ValidatorValue


class WebhookState(str, Enum):
    """State of a webhook subscription."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING_VERIFICATION = "pending_verification"
    FAILED = "failed"


class WebhookAuthType(str, Enum):
    """Authentication types supported by webhooks."""

    NONE = "none"
    API_KEY = "api_key"
    BEARER = "bearer"
    BASIC = "basic"
    HMAC = "hmac"
    OAUTH2 = "oauth2"


class WebhookDeliveryStatus(str, Enum):
    """Status of a webhook delivery attempt."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTERED = "dead_lettered"


class WebhookEventType(str, Enum):
    """Types of governance events that can trigger webhooks."""

    POLICY_VIOLATION = "policy.violation"
    POLICY_CREATED = "policy.created"
    POLICY_UPDATED = "policy.updated"
    POLICY_DELETED = "policy.deleted"
    ACCESS_REVIEW_STARTED = "access_review.started"
    ACCESS_REVIEW_COMPLETED = "access_review.completed"
    COMPLIANCE_CHECK_PASSED = "compliance.check.passed"
    COMPLIANCE_CHECK_FAILED = "compliance.check.failed"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"
    INTEGRATION_ERROR = "integration.error"
    SYSTEM_ALERT = "system.alert"


class WebhookSignatureAlgorithm(str, Enum):
    """HMAC signature algorithms for webhook verification."""

    SHA256 = "sha256"
    SHA512 = "sha512"


class WebhookConfig(BaseModel):
    """Configuration for a webhook endpoint within a subscription."""

    # Endpoint settings
    url: str = Field(..., description="Webhook endpoint URL")
    method: Literal["POST", "PUT"] = Field(
        default="POST", description="HTTP method for webhook delivery"
    )

    # Authentication
    auth_type: WebhookAuthType = Field(
        default=WebhookAuthType.NONE, description="Authentication type"
    )
    auth_header: str = Field(default="Authorization", description="Header name for authentication")
    auth_value: Optional[SecretStr] = Field(
        None, description="Authentication value (token, API key, etc.)"
    )

    # HMAC signature settings
    hmac_secret: Optional[SecretStr] = Field(
        None, description="HMAC secret for signature verification"
    )
    hmac_header: str = Field(default="X-Webhook-Signature", description="Header for HMAC signature")
    hmac_algorithm: WebhookSignatureAlgorithm = Field(
        default=WebhookSignatureAlgorithm.SHA256, description="HMAC algorithm"
    )

    # Request settings
    content_type: str = Field(default="application/json", description="Content-Type header value")
    custom_headers: Dict[str, str] = Field(
        default_factory=dict, description="Additional headers to include"
    )
    timeout_seconds: float = Field(
        default=30.0, ge=1.0, le=120.0, description="Request timeout in seconds"
    )

    # TLS settings
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate webhook URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v.rstrip("/")

    @model_validator(mode="after")
    def validate_auth_config(self) -> "WebhookConfig":
        """Validate authentication configuration consistency."""
        if self.auth_type in (WebhookAuthType.API_KEY, WebhookAuthType.BEARER):
            if not self.auth_value:
                raise ValueError(
                    f"auth_value is required for {self.auth_type.value} authentication"
                )
        if self.auth_type == WebhookAuthType.HMAC:
            if not self.hmac_secret:
                raise ValueError("hmac_secret is required for HMAC authentication")
        return self


class WebhookSubscription(BaseModel):
    """
    Webhook subscription model.

    Represents a registered webhook endpoint that will receive
    governance events based on configured filters.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for this webhook subscription",
    )
    name: str = Field(
        ..., min_length=1, max_length=255, description="Display name for the subscription"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Description of this webhook"
    )

    # State and ownership
    state: WebhookState = Field(
        default=WebhookState.PENDING_VERIFICATION,
        description="Current state of the subscription",
    )
    owner_id: Optional[str] = Field(
        None, description="User or service account that owns this subscription"
    )
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenant deployments")

    # Endpoint configuration
    config: WebhookConfig = Field(..., description="Webhook endpoint configuration")

    # Event filtering
    event_types: List[WebhookEventType] = Field(
        default_factory=lambda: [WebhookEventType.POLICY_VIOLATION],
        description="Event types to subscribe to",
    )
    severity_filter: List[str] = Field(
        default_factory=lambda: ["critical", "high", "medium", "low", "info"],
        description="Filter events by severity levels",
    )
    resource_filters: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="Filter events by resource attributes (e.g., {'policy_id': ['POL-001']})",
    )
    tag_filters: List[str] = Field(
        default_factory=list,
        description="Filter events by tags",
    )

    # Retry settings
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum delivery attempts")
    retry_delay_seconds: float = Field(
        default=1.0, ge=0.5, le=60, description="Initial retry delay"
    )
    retry_exponential_base: float = Field(
        default=2.0, ge=1.5, le=4.0, description="Exponential backoff multiplier"
    )
    max_retry_delay_seconds: float = Field(
        default=300.0, ge=1.0, le=3600, description="Maximum retry delay"
    )

    # Rate limiting
    rate_limit_per_minute: Optional[int] = Field(
        None, ge=1, le=1000, description="Maximum deliveries per minute (None = unlimited)"
    )

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Subscription creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Subscription last update timestamp",
    )
    last_triggered_at: Optional[datetime] = Field(
        None, description="Last time a delivery was attempted"
    )
    verification_token: Optional[str] = Field(None, description="Token for endpoint verification")
    verified_at: Optional[datetime] = Field(None, description="When the endpoint was verified")

    # Statistics
    total_deliveries: int = Field(default=0, ge=0, description="Total delivery attempts")
    successful_deliveries: int = Field(default=0, ge=0, description="Successful deliveries")
    failed_deliveries: int = Field(default=0, ge=0, description="Failed deliveries")
    consecutive_failures: int = Field(
        default=0, ge=0, description="Consecutive failures (resets on success)"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @field_validator("tags", mode="before")
    @classmethod
    def validate_tags(cls, v: ValidatorValue) -> List[str]:
        """Ensure tags is a list of strings."""
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return list(v)

    @field_validator("severity_filter", mode="before")
    @classmethod
    def validate_severity_filter(cls, v: ValidatorValue) -> List[str]:
        """Validate severity filter values."""
        if v is None:
            return ["critical", "high", "medium", "low", "info"]

        valid_severities = {"critical", "high", "medium", "low", "info"}
        if isinstance(v, str):
            v = [v]

        invalid = set(v) - valid_severities
        if invalid:
            raise ValueError(f"Invalid severity values: {invalid}")
        return list(v)

    def should_deliver_event(self, event: "WebhookEvent") -> bool:
        """
        Check if an event should be delivered to this subscription.

        Args:
            event: The webhook event to check

        Returns:
            True if the event matches subscription filters
        """
        # Check state
        if self.state != WebhookState.ACTIVE:
            return False

        # Check event type
        if event.event_type not in self.event_types:
            return False

        # Check severity
        if event.severity and event.severity not in self.severity_filter:
            return False

        # Check resource filters
        for key, allowed_values in self.resource_filters.items():
            event_value = event.resource_attributes.get(key)
            if event_value and event_value not in allowed_values:
                return False

        # Check tag filters
        if self.tag_filters:
            if not any(tag in event.tags for tag in self.tag_filters):
                return False

        return True


class WebhookEvent(BaseModel):
    """
    Webhook event payload model.

    Represents a governance event that will be delivered to webhook endpoints.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique event identifier",
    )
    event_type: WebhookEventType = Field(..., description="Type of governance event")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp in UTC",
    )
    severity: str = Field(
        default="info",
        description="Event severity level",
    )
    source: str = Field(default="acgs2", description="Source system")

    # Event content
    title: str = Field(..., description="Event title/summary")
    description: Optional[str] = Field(None, description="Detailed description")
    details: JSONDict = Field(default_factory=dict, description="Additional event details")

    # Resource context
    policy_id: Optional[str] = Field(None, description="Related policy ID")
    resource_id: Optional[str] = Field(None, description="Affected resource ID")
    resource_type: Optional[str] = Field(None, description="Type of affected resource")
    resource_attributes: Dict[str, str] = Field(
        default_factory=dict, description="Resource attributes for filtering"
    )

    # User context
    user_id: Optional[str] = Field(None, description="User who triggered the event")
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenant deployments")

    # Tracing
    correlation_id: Optional[str] = Field(None, description="Correlation ID for request tracing")
    tags: List[str] = Field(default_factory=list, description="Event tags")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @field_validator("severity", mode="before")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        """Validate and normalize severity."""
        v = v.lower().strip()
        valid = {"critical", "high", "medium", "low", "info"}
        if v not in valid:
            raise ValueError(f"Invalid severity '{v}', must be one of {valid}")
        return v

    def to_payload(self) -> JSONDict:
        """
        Convert event to webhook payload format.

        Returns:
            Dictionary suitable for JSON serialization and delivery
        """
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "source": self.source,
            "title": self.title,
            "description": self.description,
            "details": self.details,
            "policy_id": self.policy_id,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "resource_attributes": self.resource_attributes,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "correlation_id": self.correlation_id,
            "tags": self.tags,
        }


class WebhookDelivery(BaseModel):
    """
    Webhook delivery attempt model.

    Tracks individual delivery attempts for a webhook event
    including retry state and delivery details.
    """

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique delivery identifier",
    )
    subscription_id: str = Field(..., description="ID of the webhook subscription")
    event_id: str = Field(..., description="ID of the event being delivered")

    # Status
    status: WebhookDeliveryStatus = Field(
        default=WebhookDeliveryStatus.PENDING,
        description="Current delivery status",
    )

    # Attempt tracking
    attempt_number: int = Field(default=1, ge=1, description="Current attempt number")
    max_attempts: int = Field(default=3, ge=1, le=10, description="Maximum attempts allowed")
    next_retry_at: Optional[datetime] = Field(
        None, description="When the next retry will be attempted"
    )

    # Timing
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the delivery was created",
    )
    started_at: Optional[datetime] = Field(None, description="When delivery attempt started")
    completed_at: Optional[datetime] = Field(None, description="When delivery attempt completed")
    duration_ms: Optional[int] = Field(None, ge=0, description="Delivery duration in milliseconds")

    # Request/Response details
    request_url: Optional[str] = Field(None, description="Target URL")
    request_method: Optional[str] = Field(None, description="HTTP method used")
    request_headers: Dict[str, str] = Field(
        default_factory=dict,
        description="Request headers (sensitive values redacted)",
    )
    request_body_size: Optional[int] = Field(None, ge=0, description="Request body size in bytes")

    response_status_code: Optional[int] = Field(None, description="HTTP response status code")
    response_headers: Dict[str, str] = Field(default_factory=dict, description="Response headers")
    response_body: Optional[str] = Field(
        None, max_length=10000, description="Response body (truncated)"
    )

    # Error tracking
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(
        None, max_length=1000, description="Error message if failed"
    )

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    @property
    def can_retry(self) -> bool:
        """Check if delivery can be retried."""
        return (
            self.status in (WebhookDeliveryStatus.FAILED, WebhookDeliveryStatus.RETRYING)
            and self.attempt_number < self.max_attempts
        )

    @property
    def is_final(self) -> bool:
        """Check if delivery is in a final state."""
        return self.status in (
            WebhookDeliveryStatus.DELIVERED,
            WebhookDeliveryStatus.DEAD_LETTERED,
        )


class WebhookDeliveryResult(BaseModel):
    """
    Result of a webhook delivery operation.

    Provides detailed information about the outcome of a delivery attempt.
    """

    success: bool = Field(..., description="Whether delivery was successful")
    delivery_id: str = Field(..., description="ID of the delivery attempt")
    subscription_id: str = Field(..., description="ID of the subscription")
    event_id: str = Field(..., description="ID of the event")

    # Timing
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Result timestamp",
    )
    duration_ms: int = Field(default=0, ge=0, description="Delivery duration in milliseconds")

    # Status details
    status_code: Optional[int] = Field(None, description="HTTP status code received")
    status: WebhookDeliveryStatus = Field(..., description="Final delivery status")

    # Retry information
    attempt_number: int = Field(default=1, ge=1, description="Which attempt this was")
    should_retry: bool = Field(default=False, description="Whether delivery should be retried")
    retry_after_seconds: Optional[float] = Field(
        None, ge=0, description="Seconds to wait before retry"
    )

    # Error details
    error_code: Optional[str] = Field(None, description="Error code if failed")
    error_message: Optional[str] = Field(
        None, max_length=1000, description="Error message if failed"
    )
    error_details: JSONDict = Field(default_factory=dict, description="Additional error details")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @classmethod
    def success_result(
        cls,
        delivery_id: str,
        subscription_id: str,
        event_id: str,
        status_code: int,
        duration_ms: int,
        attempt_number: int = 1,
    ) -> "WebhookDeliveryResult":
        """Create a successful delivery result."""
        return cls(
            success=True,
            delivery_id=delivery_id,
            subscription_id=subscription_id,
            event_id=event_id,
            status_code=status_code,
            status=WebhookDeliveryStatus.DELIVERED,
            duration_ms=duration_ms,
            attempt_number=attempt_number,
            should_retry=False,
        )

    @classmethod
    def failure_result(
        cls,
        delivery_id: str,
        subscription_id: str,
        event_id: str,
        error_code: str,
        error_message: str,
        status_code: Optional[int] = None,
        duration_ms: int = 0,
        attempt_number: int = 1,
        should_retry: bool = True,
        retry_after_seconds: Optional[float] = None,
        max_attempts: int = 3,
    ) -> "WebhookDeliveryResult":
        """Create a failed delivery result."""
        # Determine if we've exhausted retries
        is_dead_lettered = not should_retry or attempt_number >= max_attempts

        return cls(
            success=False,
            delivery_id=delivery_id,
            subscription_id=subscription_id,
            event_id=event_id,
            status_code=status_code,
            status=(
                WebhookDeliveryStatus.DEAD_LETTERED
                if is_dead_lettered
                else WebhookDeliveryStatus.RETRYING
            ),
            duration_ms=duration_ms,
            attempt_number=attempt_number,
            should_retry=should_retry and attempt_number < max_attempts,
            retry_after_seconds=retry_after_seconds,
            error_code=error_code,
            error_message=error_message,
        )
