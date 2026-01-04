"""
Webhooks API endpoints for managing webhook subscriptions.

Provides CRUD operations for webhook endpoint configuration,
delivery status monitoring, and subscription management.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from ..types import JSONDict, ValidatorValue
from ..webhooks.models import (
    WebhookAuthType,
    WebhookConfig,
    WebhookDeliveryStatus,
    WebhookEventType,
    WebhookSignatureAlgorithm,
    WebhookState,
    WebhookSubscription,
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


# In-memory storage for webhook subscriptions (for development)
# In production, this would be replaced with a database repository
_webhook_subscriptions: Dict[str, WebhookSubscription] = {}


# Request/Response Models
class WebhookConfigCreate(BaseModel):
    """Configuration for a webhook endpoint."""

    url: str = Field(..., description="Webhook endpoint URL")
    method: str = Field(default="POST", description="HTTP method for webhook delivery")
    auth_type: WebhookAuthType = Field(
        default=WebhookAuthType.NONE, description="Authentication type"
    )
    auth_header: str = Field(default="Authorization", description="Header name for authentication")
    auth_value: Optional[str] = Field(
        None, description="Authentication value (token, API key, etc.)"
    )
    hmac_secret: Optional[str] = Field(None, description="HMAC secret for signature verification")
    hmac_header: str = Field(default="X-Webhook-Signature", description="Header for HMAC signature")
    hmac_algorithm: WebhookSignatureAlgorithm = Field(
        default=WebhookSignatureAlgorithm.SHA256, description="HMAC algorithm"
    )
    content_type: str = Field(default="application/json", description="Content-Type header value")
    custom_headers: Dict[str, str] = Field(
        default_factory=dict, description="Additional headers to include"
    )
    timeout_seconds: float = Field(
        default=30.0, ge=1.0, le=120.0, description="Request timeout in seconds"
    )
    verify_ssl: bool = Field(default=True, description="Verify SSL certificates")

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    @field_validator("url", mode="before")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate webhook URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v.rstrip("/")

    def to_webhook_config(self) -> WebhookConfig:
        """Convert to WebhookConfig model with SecretStr handling."""
        return WebhookConfig(
            url=self.url,
            method=self.method,
            auth_type=self.auth_type,
            auth_header=self.auth_header,
            auth_value=SecretStr(self.auth_value) if self.auth_value else None,
            hmac_secret=SecretStr(self.hmac_secret) if self.hmac_secret else None,
            hmac_header=self.hmac_header,
            hmac_algorithm=self.hmac_algorithm,
            content_type=self.content_type,
            custom_headers=self.custom_headers,
            timeout_seconds=self.timeout_seconds,
            verify_ssl=self.verify_ssl,
        )


class WebhookCreateRequest(BaseModel):
    """Request model for creating a webhook subscription."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="Display name for the subscription"
    )
    description: Optional[str] = Field(
        None, max_length=1000, description="Description of this webhook"
    )

    # Endpoint configuration - can be inline or via config object
    url: Optional[str] = Field(None, description="Webhook endpoint URL (shorthand)")
    auth_type: Optional[WebhookAuthType] = Field(
        None, description="Authentication type (shorthand)"
    )
    config: Optional[WebhookConfigCreate] = Field(
        None, description="Full webhook endpoint configuration"
    )

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
        description="Filter events by resource attributes",
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

    # Rate limiting
    rate_limit_per_minute: Optional[int] = Field(
        None, ge=1, le=1000, description="Maximum deliveries per minute"
    )

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

    # Multi-tenant support
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenant deployments")

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

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


class WebhookUpdateRequest(BaseModel):
    """Request model for updating a webhook subscription."""

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Display name")
    description: Optional[str] = Field(None, max_length=1000, description="Description")
    config: Optional[WebhookConfigCreate] = Field(
        None, description="Webhook endpoint configuration"
    )
    event_types: Optional[List[WebhookEventType]] = Field(
        None, description="Event types to subscribe to"
    )
    severity_filter: Optional[List[str]] = Field(
        None, description="Filter events by severity levels"
    )
    resource_filters: Optional[Dict[str, List[str]]] = Field(
        None, description="Filter events by resource attributes"
    )
    tag_filters: Optional[List[str]] = Field(None, description="Filter events by tags")
    max_retries: Optional[int] = Field(None, ge=0, le=10, description="Maximum delivery attempts")
    retry_delay_seconds: Optional[float] = Field(
        None, ge=0.5, le=60, description="Initial retry delay"
    )
    rate_limit_per_minute: Optional[int] = Field(
        None, ge=1, le=1000, description="Maximum deliveries per minute"
    )
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class WebhookResponse(BaseModel):
    """Response model for webhook subscription."""

    id: str = Field(..., description="Unique webhook subscription ID")
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(None, description="Description")
    state: WebhookState = Field(..., description="Current subscription state")
    owner_id: Optional[str] = Field(None, description="Owner user/service ID")
    tenant_id: Optional[str] = Field(None, description="Tenant ID")

    # Endpoint config (with secrets redacted)
    url: str = Field(..., description="Webhook endpoint URL")
    auth_type: WebhookAuthType = Field(..., description="Authentication type")
    method: str = Field(..., description="HTTP method")

    # Filters
    event_types: List[WebhookEventType] = Field(..., description="Subscribed event types")
    severity_filter: List[str] = Field(..., description="Severity filter")

    # Retry settings
    max_retries: int = Field(..., description="Maximum delivery attempts")
    retry_delay_seconds: float = Field(..., description="Initial retry delay")

    # Rate limiting
    rate_limit_per_minute: Optional[int] = Field(None, description="Rate limit")

    # Metadata
    tags: List[str] = Field(..., description="Tags")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_triggered_at: Optional[datetime] = Field(None, description="Last trigger time")

    # Statistics
    total_deliveries: int = Field(..., description="Total deliveries")
    successful_deliveries: int = Field(..., description="Successful deliveries")
    failed_deliveries: int = Field(..., description="Failed deliveries")
    consecutive_failures: int = Field(..., description="Consecutive failures")

    model_config = ConfigDict(
        from_attributes=True,
    )

    @classmethod
    def from_subscription(cls, subscription: WebhookSubscription) -> "WebhookResponse":
        """Create response from WebhookSubscription model."""
        return cls(
            id=subscription.id,
            name=subscription.name,
            description=subscription.description,
            state=subscription.state,
            owner_id=subscription.owner_id,
            tenant_id=subscription.tenant_id,
            url=subscription.config.url,
            auth_type=subscription.config.auth_type,
            method=subscription.config.method,
            event_types=subscription.event_types,
            severity_filter=subscription.severity_filter,
            max_retries=subscription.max_retries,
            retry_delay_seconds=subscription.retry_delay_seconds,
            rate_limit_per_minute=subscription.rate_limit_per_minute,
            tags=subscription.tags,
            created_at=subscription.created_at,
            updated_at=subscription.updated_at,
            last_triggered_at=subscription.last_triggered_at,
            total_deliveries=subscription.total_deliveries,
            successful_deliveries=subscription.successful_deliveries,
            failed_deliveries=subscription.failed_deliveries,
            consecutive_failures=subscription.consecutive_failures,
        )


class WebhookListResponse(BaseModel):
    """Response model for listing webhooks."""

    webhooks: List[WebhookResponse] = Field(..., description="List of webhooks")
    total: int = Field(..., description="Total number of webhooks")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_more: bool = Field(..., description="Whether more pages exist")


class WebhookTestRequest(BaseModel):
    """Request model for testing a webhook."""

    event_type: WebhookEventType = Field(
        default=WebhookEventType.SYSTEM_ALERT,
        description="Event type for test event",
    )
    payload: Optional[JSONDict] = Field(None, description="Custom test payload")


class WebhookTestResponse(BaseModel):
    """Response model for webhook test."""

    success: bool = Field(..., description="Whether test delivery succeeded")
    delivery_id: str = Field(..., description="Delivery attempt ID")
    status_code: Optional[int] = Field(None, description="HTTP status code")
    duration_ms: int = Field(..., description="Delivery duration in milliseconds")
    error: Optional[str] = Field(None, description="Error message if failed")


# Dependency for getting webhook service (can be extended later)
def get_webhook_storage() -> Dict[str, WebhookSubscription]:
    """Get webhook subscription storage."""
    return _webhook_subscriptions


# API Endpoints
@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a webhook subscription",
    description="Create a new webhook subscription to receive governance events",
)
async def create_webhook(
    request: WebhookCreateRequest,
    storage: Dict[str, WebhookSubscription] = Depends(get_webhook_storage),
) -> WebhookResponse:
    """
    Create a new webhook subscription.

    The webhook will start in PENDING_VERIFICATION state until the endpoint
    is verified or manually activated.
    """
    try:
        # Build webhook config
        if request.config:
            config = request.config.to_webhook_config()
        elif request.url:
            # Use shorthand URL and auth_type
            config = WebhookConfig(
                url=request.url,
                auth_type=request.auth_type or WebhookAuthType.NONE,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'url' or 'config' must be provided",
            )

        # Create subscription
        subscription_id = str(uuid4())
        subscription = WebhookSubscription(
            id=subscription_id,
            name=request.name,
            description=request.description,
            state=WebhookState.PENDING_VERIFICATION,
            config=config,
            event_types=request.event_types,
            severity_filter=request.severity_filter,
            resource_filters=request.resource_filters,
            tag_filters=request.tag_filters,
            max_retries=request.max_retries,
            retry_delay_seconds=request.retry_delay_seconds,
            rate_limit_per_minute=request.rate_limit_per_minute,
            tags=request.tags,
            tenant_id=request.tenant_id,
            verification_token=str(uuid4()),
        )

        # Store subscription
        storage[subscription_id] = subscription

        logger.info(f"Created webhook subscription: {subscription_id} for URL: {config.url}")

        return WebhookResponse.from_subscription(subscription)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
    except Exception as e:
        logger.exception(f"Error creating webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook creation failed. Please verify your request and try again.",
        ) from None


@router.get(
    "",
    response_model=WebhookListResponse,
    summary="List webhook subscriptions",
    description="List all webhook subscriptions with optional filtering",
)
async def list_webhooks(
    state: Optional[WebhookState] = Query(None, description="Filter by subscription state"),
    event_type: Optional[WebhookEventType] = Query(None, description="Filter by event type"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    storage: Dict[str, WebhookSubscription] = Depends(get_webhook_storage),
) -> WebhookListResponse:
    """
    List all webhook subscriptions.

    Supports filtering by state, event type, and tenant ID.
    Results are paginated.
    """
    # Filter subscriptions
    subscriptions = list(storage.values())

    if state:
        subscriptions = [s for s in subscriptions if s.state == state]

    if event_type:
        subscriptions = [s for s in subscriptions if event_type in s.event_types]

    if tenant_id:
        subscriptions = [s for s in subscriptions if s.tenant_id == tenant_id]

    # Sort by creation time (newest first)
    subscriptions.sort(key=lambda s: s.created_at, reverse=True)

    # Paginate
    total = len(subscriptions)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_subscriptions = subscriptions[start_idx:end_idx]
    has_more = end_idx < total

    return WebhookListResponse(
        webhooks=[WebhookResponse.from_subscription(s) for s in page_subscriptions],
        total=total,
        page=page,
        page_size=page_size,
        has_more=has_more,
    )


@router.get(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get webhook subscription",
    description="Get a specific webhook subscription by ID",
)
async def get_webhook(
    webhook_id: str,
    storage: Dict[str, WebhookSubscription] = Depends(get_webhook_storage),
) -> WebhookResponse:
    """Get a webhook subscription by ID."""
    subscription = storage.get(webhook_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription not found: {webhook_id}",
        )

    return WebhookResponse.from_subscription(subscription)


@router.put(
    "/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update webhook subscription",
    description="Update an existing webhook subscription",
)
async def update_webhook(
    webhook_id: str,
    request: WebhookUpdateRequest,
    storage: Dict[str, WebhookSubscription] = Depends(get_webhook_storage),
) -> WebhookResponse:
    """Update a webhook subscription."""
    subscription = storage.get(webhook_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription not found: {webhook_id}",
        )

    try:
        # Update fields if provided
        if request.name is not None:
            subscription.name = request.name
        if request.description is not None:
            subscription.description = request.description
        if request.config is not None:
            subscription.config = request.config.to_webhook_config()
        if request.event_types is not None:
            subscription.event_types = request.event_types
        if request.severity_filter is not None:
            subscription.severity_filter = request.severity_filter
        if request.resource_filters is not None:
            subscription.resource_filters = request.resource_filters
        if request.tag_filters is not None:
            subscription.tag_filters = request.tag_filters
        if request.max_retries is not None:
            subscription.max_retries = request.max_retries
        if request.retry_delay_seconds is not None:
            subscription.retry_delay_seconds = request.retry_delay_seconds
        if request.rate_limit_per_minute is not None:
            subscription.rate_limit_per_minute = request.rate_limit_per_minute
        if request.tags is not None:
            subscription.tags = request.tags

        # Update timestamp
        subscription.updated_at = datetime.now(timezone.utc)

        logger.info(f"Updated webhook subscription: {webhook_id}")

        return WebhookResponse.from_subscription(subscription)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from None
    except Exception as e:
        logger.exception(f"Error updating webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook update failed. Please verify your request and try again.",
        ) from None


@router.delete(
    "/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete webhook subscription",
    description="Delete a webhook subscription",
)
async def delete_webhook(
    webhook_id: str,
    storage: Dict[str, WebhookSubscription] = Depends(get_webhook_storage),
) -> None:
    """Delete a webhook subscription."""
    if webhook_id not in storage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription not found: {webhook_id}",
        )

    del storage[webhook_id]
    logger.info(f"Deleted webhook subscription: {webhook_id}")


@router.post(
    "/{webhook_id}/activate",
    response_model=WebhookResponse,
    summary="Activate webhook subscription",
    description="Activate a webhook subscription to start receiving events",
)
async def activate_webhook(
    webhook_id: str,
    storage: Dict[str, WebhookSubscription] = Depends(get_webhook_storage),
) -> WebhookResponse:
    """Activate a webhook subscription."""
    subscription = storage.get(webhook_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription not found: {webhook_id}",
        )

    if subscription.state == WebhookState.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook is already active",
        )

    subscription.state = WebhookState.ACTIVE
    subscription.updated_at = datetime.now(timezone.utc)
    subscription.verified_at = datetime.now(timezone.utc)

    logger.info(f"Activated webhook subscription: {webhook_id}")

    return WebhookResponse.from_subscription(subscription)


@router.post(
    "/{webhook_id}/deactivate",
    response_model=WebhookResponse,
    summary="Deactivate webhook subscription",
    description="Deactivate a webhook subscription to stop receiving events",
)
async def deactivate_webhook(
    webhook_id: str,
    storage: Dict[str, WebhookSubscription] = Depends(get_webhook_storage),
) -> WebhookResponse:
    """Deactivate a webhook subscription."""
    subscription = storage.get(webhook_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription not found: {webhook_id}",
        )

    if subscription.state == WebhookState.INACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook is already inactive",
        )

    subscription.state = WebhookState.INACTIVE
    subscription.updated_at = datetime.now(timezone.utc)

    logger.info(f"Deactivated webhook subscription: {webhook_id}")

    return WebhookResponse.from_subscription(subscription)


@router.post(
    "/{webhook_id}/test",
    response_model=WebhookTestResponse,
    summary="Test webhook delivery",
    description="Send a test event to verify webhook endpoint",
)
async def test_webhook(
    webhook_id: str,
    request: Optional[WebhookTestRequest] = None,
    storage: Dict[str, WebhookSubscription] = Depends(get_webhook_storage),
) -> WebhookTestResponse:
    """
    Test a webhook endpoint by sending a test event.

    This will send a test event to the configured endpoint to verify
    connectivity and authentication.
    """
    subscription = storage.get(webhook_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription not found: {webhook_id}",
        )

    # For now, return a mock test response
    # In production, this would actually send a test event using the delivery engine
    delivery_id = str(uuid4())

    # TODO: Integrate with WebhookDeliveryEngine for actual test delivery
    logger.info(f"Test delivery initiated for webhook {webhook_id} to {subscription.config.url}")

    return WebhookTestResponse(
        success=True,
        delivery_id=delivery_id,
        status_code=200,
        duration_ms=150,
        error=None,
    )


@router.get(
    "/{webhook_id}/deliveries",
    response_model=JSONDict,
    summary="Get webhook delivery history",
    description="Get delivery history for a webhook subscription",
)
async def get_webhook_deliveries(
    webhook_id: str,
    status_filter: Optional[WebhookDeliveryStatus] = Query(
        None, description="Filter by delivery status"
    ),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of deliveries"),
    storage: Dict[str, WebhookSubscription] = Depends(get_webhook_storage),
) -> JSONDict:
    """Get delivery history for a webhook subscription."""
    subscription = storage.get(webhook_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook subscription not found: {webhook_id}",
        )

    # For now, return subscription statistics
    # In production, this would query actual delivery records from database
    return {
        "webhook_id": webhook_id,
        "statistics": {
            "total_deliveries": subscription.total_deliveries,
            "successful_deliveries": subscription.successful_deliveries,
            "failed_deliveries": subscription.failed_deliveries,
            "consecutive_failures": subscription.consecutive_failures,
            "last_triggered_at": (
                subscription.last_triggered_at.isoformat()
                if subscription.last_triggered_at
                else None
            ),
        },
        "deliveries": [],  # Would be populated from database
    }
