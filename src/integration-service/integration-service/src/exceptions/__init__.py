"""
Exception classes for the integration-service.

This module provides a unified exception hierarchy for consistent error handling
across all integration-service components.

The exception hierarchy is organized into categories:
- base: Base exception class with common attributes
- auth: Authentication and authorization exceptions
- validation: Configuration and data validation exceptions
- retry: Retry logic and backoff exceptions
- delivery: Event delivery and webhook exceptions
- integration: Third-party integration exceptions

All exceptions inherit from BaseIntegrationServiceError and provide:
- Consistent attributes (message, error_code, status_code, details)
- Serialization support via to_dict()
- Machine-readable error codes for monitoring
- HTTP status codes for API responses

Example:
    Basic usage:
    >>> from exceptions import BaseIntegrationServiceError
    >>> error = BaseIntegrationServiceError(
    ...     message="Operation failed",
    ...     error_code="CUSTOM_ERROR",
    ...     status_code=500
    ... )
    >>> error.to_dict()
    {'error': 'BaseIntegrationServiceError', 'message': 'Operation failed', ...}

    Category-specific exceptions:
    >>> from exceptions.auth import InvalidApiKeyError
    >>> from exceptions.retry import RetryableError
    >>> from exceptions.delivery import DeliveryError

Design Principles:
    1. Single Source of Truth: All exceptions defined in this module
    2. Consistent Attributes: Common attributes across all exceptions
    3. Backward Compatibility: Old exception names maintained as aliases
    4. Type Safety: Proper inheritance for isinstance() checks
    5. Rich Context: Error codes and details for debugging

Error Codes:
    Each exception has a default error_code that can be overridden:
    - AUTH_ERROR: Authentication failures
    - VALIDATION_ERROR: Validation failures
    - RETRY_ERROR: Retry logic errors
    - DELIVERY_ERROR: Event delivery failures
    - INTEGRATION_ERROR: Third-party integration errors

Status Codes:
    Common HTTP status codes used:
    - 400: Bad Request (validation errors)
    - 401: Unauthorized (authentication errors)
    - 403: Forbidden (authorization errors)
    - 404: Not Found (resource not found)
    - 429: Too Many Requests (rate limiting)
    - 500: Internal Server Error (general errors)
    - 502: Bad Gateway (connection errors)
    - 503: Service Unavailable (retryable errors)
    - 504: Gateway Timeout (timeout errors)
"""

from .auth import (
    AuthenticationError,
    InvalidApiKeyError,
    InvalidBearerTokenError,
    InvalidSignatureError,
    MissingAuthHeaderError,
    SignatureTimestampError,
    TokenExpiredError,
    WebhookAuthError,
)
from .base import BaseIntegrationServiceError
from .delivery import (
    DeliveryConnectionError,
    DeliveryError,
    DeliveryTimeoutError,
    WebhookConnectionError,
    WebhookDeliveryError,
    WebhookTimeoutError,
)
from .integration import IntegrationConnectionError, IntegrationError, RateLimitError
from .retry import (
    MaxRetriesExceededError,
    NonRetryableError,
    RetryableError,
    RetryError,
    WebhookRetryError,
)
from .validation import ConfigValidationError, ValidationError

# Export all exceptions
__all__ = [
    "BaseIntegrationServiceError",
    # Authentication exceptions
    "AuthenticationError",
    "InvalidApiKeyError",
    "InvalidBearerTokenError",
    "InvalidSignatureError",
    "MissingAuthHeaderError",
    "SignatureTimestampError",
    "TokenExpiredError",
    "WebhookAuthError",  # Backward compatibility alias
    # Retry exceptions
    "RetryError",
    "RetryableError",
    "NonRetryableError",
    "MaxRetriesExceededError",
    "WebhookRetryError",  # Backward compatibility alias
    # Delivery exceptions
    "DeliveryError",
    "DeliveryTimeoutError",
    "DeliveryConnectionError",
    "WebhookDeliveryError",  # Backward compatibility alias
    "WebhookTimeoutError",  # Backward compatibility alias
    "WebhookConnectionError",  # Backward compatibility alias
    # Integration exceptions
    "IntegrationError",
    "RateLimitError",
    "IntegrationConnectionError",
    # Validation exceptions
    "ValidationError",
    "ConfigValidationError",
]

# Version information
__version__ = "1.0.0"
