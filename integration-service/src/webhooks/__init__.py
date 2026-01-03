"""
Webhook Framework for ACGS-2 Integration Service.

Provides models, configuration, and delivery infrastructure for custom webhook
integrations with configurable authentication, retry logic, and delivery tracking.
"""

from .config import (
    WebhookFrameworkConfig,
    WebhookRetryPolicy,
    WebhookSecurityConfig,
)
from .delivery import (
    DeadLetterQueue,
    WebhookAuthenticationError,
    WebhookConnectionError,
    WebhookDeliveryEngine,
    WebhookDeliveryError,
    WebhookTimeoutError,
    create_delivery_engine,
)
from .models import (
    WebhookAuthType,
    WebhookConfig,
    WebhookDelivery,
    WebhookDeliveryResult,
    WebhookDeliveryStatus,
    WebhookEvent,
    WebhookEventType,
    WebhookSignatureAlgorithm,
    WebhookState,
    WebhookSubscription,
)
from .retry import (
    ExponentialBackoff,
    NonRetryableError,
    RetryableError,
    RetryState,
    WebhookRetryError,
    extract_retry_after,
    retry_with_backoff,
    should_retry_status_code,
    with_retry,
)

__all__ = [
    # Enums
    "WebhookState",
    "WebhookAuthType",
    "WebhookDeliveryStatus",
    "WebhookEventType",
    "WebhookSignatureAlgorithm",
    # Models
    "WebhookConfig",
    "WebhookSubscription",
    "WebhookEvent",
    "WebhookDelivery",
    "WebhookDeliveryResult",
    # Configuration
    "WebhookFrameworkConfig",
    "WebhookRetryPolicy",
    "WebhookSecurityConfig",
    # Delivery Engine
    "WebhookDeliveryEngine",
    "DeadLetterQueue",
    "create_delivery_engine",
    # Delivery Exceptions
    "WebhookDeliveryError",
    "WebhookAuthenticationError",
    "WebhookConnectionError",
    "WebhookTimeoutError",
    # Retry Logic
    "ExponentialBackoff",
    "RetryState",
    "RetryableError",
    "NonRetryableError",
    "WebhookRetryError",
    "should_retry_status_code",
    "extract_retry_after",
    "retry_with_backoff",
    "with_retry",
]
