"""
Retry exception classes for the integration-service.

Provides exceptions for retry logic and webhook delivery failures including:
- Retryable errors that should trigger retry logic
- Non-retryable errors that should fail immediately
- Max retries exceeded errors when all retry attempts are exhausted
"""

from typing import Any, Dict, Optional

from .base import BaseIntegrationServiceError


class RetryError(BaseIntegrationServiceError):
    """
    Base exception for retry-related errors.

    All retry exceptions inherit from this class to enable
    catch-all retry error handling.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error identifier
        status_code: HTTP status code (defaults to 503 Service Unavailable)
        details: Additional context about the retry failure

    Example:
        >>> error = RetryError(
        ...     message="Retry operation failed",
        ...     error_code="RETRY_ERROR",
        ...     details={"reason": "service unavailable"}
        ... )
        >>> error.status_code
        503
    """

    def __init__(
        self,
        message: str,
        error_code: str = "RETRY_ERROR",
        status_code: int = 503,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize retry error.

        Args:
            message: Human-readable error description
            error_code: Machine-readable error identifier (default: "RETRY_ERROR")
            status_code: HTTP status code (default: 503)
            details: Additional context about the error (default: {})
        """
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class RetryableError(RetryError):
    """
    Indicates an error that should trigger retry logic.

    This error signals that the operation failed temporarily and should
    be retried with backoff. Optionally includes a retry_after duration
    from the server (e.g., from Retry-After header).

    Attributes:
        retry_after: Optional delay in seconds before next retry attempt

    Example:
        >>> raise RetryableError(
        ...     message="Service temporarily unavailable",
        ...     status_code=503,
        ...     retry_after=60.0,
        ...     details={"service": "webhook-delivery"}
        ... )
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        retry_after: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize retryable error.

        Args:
            message: Human-readable error description
            status_code: HTTP status code (default: 503 if not specified)
            retry_after: Delay in seconds before next retry (default: None)
            details: Additional context about the error (default: {})
        """
        # Store retry_after as instance attribute for easy access
        self.retry_after = retry_after

        # Add retry_after to details if provided
        merged_details = details or {}
        if retry_after is not None:
            merged_details["retry_after"] = retry_after

        super().__init__(
            message=message,
            error_code="RETRYABLE_ERROR",
            status_code=status_code or 503,
            details=merged_details,
        )


class NonRetryableError(RetryError):
    """
    Indicates an error that should NOT trigger retry logic.

    This error signals a permanent failure that will not be resolved
    by retrying (e.g., invalid request, authentication failure, 4xx errors).

    Example:
        >>> raise NonRetryableError(
        ...     message="Invalid webhook payload",
        ...     status_code=400,
        ...     details={"validation_error": "missing required field"}
        ... )
    """

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize non-retryable error.

        Args:
            message: Human-readable error description
            status_code: HTTP status code (default: 400 if not specified)
            details: Additional context about the error (default: {})
        """
        super().__init__(
            message=message,
            error_code="NON_RETRYABLE_ERROR",
            status_code=status_code or 400,
            details=details,
        )


class MaxRetriesExceededError(RetryError):
    """
    Raised when a webhook delivery fails after exhausting all retry attempts.

    This error indicates that the operation was retried the maximum number
    of times but continued to fail. It includes the total attempt count and
    details about the last failure for debugging.

    Attributes:
        attempts: Total number of retry attempts made
        last_error: The exception from the final retry attempt
        last_status_code: HTTP status code from the final attempt (if applicable)

    Example:
        >>> last_err = RetryableError("Connection timeout")
        >>> raise MaxRetriesExceededError(
        ...     message="Webhook delivery failed after 3 attempts",
        ...     attempts=3,
        ...     last_error=last_err,
        ...     last_status_code=503
        ... )
    """

    def __init__(
        self,
        message: str,
        attempts: int,
        last_error: Optional[Exception] = None,
        last_status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize max retries exceeded error.

        Args:
            message: Human-readable error description
            attempts: Total number of retry attempts made
            last_error: The exception from the final retry attempt (default: None)
            last_status_code: HTTP status code from final attempt (default: None)
            details: Additional context (automatically includes attempts and last_status_code)
        """
        # Store as instance attributes for easy access
        self.attempts = attempts
        self.last_error = last_error
        self.last_status_code = last_status_code

        # Merge retry context into details
        merged_details = {
            "attempts": attempts,
            "last_status_code": last_status_code,
        }
        if last_error is not None:
            merged_details["last_error_type"] = type(last_error).__name__
            merged_details["last_error_message"] = str(last_error)
        if details:
            merged_details.update(details)

        super().__init__(
            message=message,
            error_code="MAX_RETRIES_EXCEEDED",
            status_code=last_status_code or 503,
            details=merged_details,
        )


# Backward compatibility alias
WebhookRetryError = MaxRetriesExceededError
