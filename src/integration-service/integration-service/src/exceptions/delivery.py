"""
Delivery exception classes for the integration-service.

Provides exceptions for webhook and event delivery failures including:
- Timeout errors when delivery takes too long
- Connection errors when the endpoint is unreachable
- General delivery failures with delivery tracking
"""

from typing import Any, Dict, Optional

from .base import BaseIntegrationServiceError


class DeliveryError(BaseIntegrationServiceError):
    """
    Base exception for webhook and event delivery errors.

    All delivery exceptions inherit from this class to enable
    catch-all delivery error handling. Includes delivery_id tracking
    to correlate errors with specific delivery attempts.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error identifier
        status_code: HTTP status code (defaults to 502 Bad Gateway)
        details: Additional context about the delivery failure
        delivery_id: Optional delivery attempt identifier for tracking

    Example:
        >>> error = DeliveryError(
        ...     message="Failed to deliver webhook",
        ...     error_code="DELIVERY_ERROR",
        ...     delivery_id="dlv_abc123",
        ...     details={"endpoint": "https://example.com/webhook"}
        ... )
        >>> error.delivery_id
        'dlv_abc123'
    """

    def __init__(
        self,
        message: str,
        error_code: str = "DELIVERY_ERROR",
        status_code: int = 502,
        delivery_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize delivery error.

        Args:
            message: Human-readable error description
            error_code: Machine-readable error identifier (default: "DELIVERY_ERROR")
            status_code: HTTP status code (default: 502)
            delivery_id: Optional delivery attempt identifier (default: None)
            details: Additional context about the error (default: {})
        """
        # Store delivery_id as instance attribute for easy access
        self.delivery_id = delivery_id

        # Add delivery_id to details if provided
        merged_details = details or {}
        if delivery_id is not None:
            merged_details["delivery_id"] = delivery_id

        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=merged_details,
        )


class DeliveryTimeoutError(DeliveryError):
    """
    Raised when webhook or event delivery times out.

    This error indicates that the delivery request exceeded the
    configured timeout duration, suggesting the endpoint is slow
    to respond or unresponsive.

    Example:
        >>> raise DeliveryTimeoutError(
        ...     message="Webhook delivery timed out after 30 seconds",
        ...     delivery_id="dlv_xyz789",
        ...     details={"timeout_seconds": 30, "endpoint": "https://slow.example.com"}
        ... )
    """

    def __init__(
        self,
        message: str = "Delivery request timed out",
        delivery_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize delivery timeout error.

        Args:
            message: Human-readable error description (default: "Delivery request timed out")
            delivery_id: Optional delivery attempt identifier (default: None)
            details: Additional context (e.g., timeout duration, endpoint)
        """
        super().__init__(
            message=message,
            error_code="DELIVERY_TIMEOUT",
            status_code=504,  # Gateway Timeout
            delivery_id=delivery_id,
            details=details,
        )


class DeliveryConnectionError(DeliveryError):
    """
    Raised when connection to webhook endpoint fails.

    This error indicates that the service could not establish a
    connection to the target endpoint, suggesting DNS issues,
    network problems, or the endpoint being unavailable.

    Example:
        >>> raise DeliveryConnectionError(
        ...     message="Failed to connect to webhook endpoint",
        ...     delivery_id="dlv_abc456",
        ...     details={
        ...         "endpoint": "https://unreachable.example.com",
        ...         "error": "Connection refused"
        ...     }
        ... )
    """

    def __init__(
        self,
        message: str = "Failed to connect to delivery endpoint",
        delivery_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize delivery connection error.

        Args:
            message: Human-readable error description
                (default: "Failed to connect to delivery endpoint")
            delivery_id: Optional delivery attempt identifier (default: None)
            details: Additional context (e.g., endpoint URL, network error)
        """
        super().__init__(
            message=message,
            error_code="DELIVERY_CONNECTION_ERROR",
            status_code=502,  # Bad Gateway
            delivery_id=delivery_id,
            details=details,
        )


# Backward compatibility aliases
WebhookDeliveryError = DeliveryError
WebhookTimeoutError = DeliveryTimeoutError
WebhookConnectionError = DeliveryConnectionError
