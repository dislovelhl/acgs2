"""
Integration exception classes for the integration-service.

Provides exceptions for third-party integration errors including:
- Generic integration failures
- Rate limiting errors
- Connection errors to external services
"""

from typing import Any, Dict, Optional

from .base import BaseIntegrationServiceError


class IntegrationError(BaseIntegrationServiceError):
    """
    Base exception for third-party integration errors.

    All integration-specific exceptions inherit from this class to enable
    catch-all integration error handling. This exception adds integration_name
    tracking to identify which integration failed.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error identifier
        status_code: HTTP status code (defaults to 500 Internal Server Error)
        details: Additional context about the integration failure
        integration_name: Name of the integration that failed

    Example:
        >>> error = IntegrationError(
        ...     message="Failed to connect to Splunk",
        ...     integration_name="splunk-prod",
        ...     error_code="INTEGRATION_ERROR",
        ...     details={"endpoint": "https://splunk.example.com"}
        ... )
        >>> error.integration_name
        'splunk-prod'
    """

    def __init__(
        self,
        message: str,
        integration_name: str = "",
        error_code: str = "INTEGRATION_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize integration error.

        Args:
            message: Human-readable error description
            integration_name: Name of the integration that failed (default: "")
            error_code: Machine-readable error identifier (default: "INTEGRATION_ERROR")
            status_code: HTTP status code (default: 500)
            details: Additional context about the error (default: {})
        """
        # Store integration_name as instance attribute for easy access
        self.integration_name = integration_name

        # Merge integration_name into details if provided
        merged_details = details or {}
        if integration_name:
            merged_details["integration_name"] = integration_name

        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=merged_details,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary representation.

        Extends the base to_dict() to include the integration_name attribute
        for backward compatibility with existing IntegrationError usage.

        Returns:
            Dictionary containing error information with keys:
            - error: Exception class name
            - message: Human-readable error message
            - error_code: Machine-readable error code
            - status_code: HTTP status code
            - integration_name: Integration name if set (for backward compatibility)
            - details: Additional error context
        """
        result = super().to_dict()
        # Add integration_name to top-level for backward compatibility
        result["integration_name"] = self.integration_name
        return result


class RateLimitError(IntegrationError):
    """
    Raised when external service rate limit is exceeded.

    This error indicates the integration has hit the rate limit of the
    external service. The retry_after attribute specifies when to retry,
    if provided by the service.

    Attributes:
        retry_after: Optional seconds to wait before retrying

    Example:
        >>> raise RateLimitError(
        ...     message="Splunk rate limit exceeded: 100 requests/minute",
        ...     integration_name="splunk-prod",
        ...     retry_after=60,
        ...     details={"limit": 100, "window": "1 minute"}
        ... )
    """

    def __init__(
        self,
        message: str,
        integration_name: str = "",
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize rate limit error.

        Args:
            message: Human-readable error description
            integration_name: Name of the integration that was rate limited
            retry_after: Optional seconds to wait before retrying
            details: Additional context (automatically includes retry_after if provided)
        """
        # Store retry_after as instance attribute for easy access
        self.retry_after = retry_after

        # Merge retry_after into details if provided
        merged_details = details or {}
        if retry_after is not None:
            merged_details["retry_after"] = retry_after

        super().__init__(
            message=message,
            integration_name=integration_name,
            error_code="RATE_LIMIT_ERROR",
            status_code=429,
            details=merged_details,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary representation.

        Extends the base to_dict() to include the retry_after attribute
        for backward compatibility with existing RateLimitError usage.

        Returns:
            Dictionary containing error information with keys:
            - error: Exception class name
            - message: Human-readable error message
            - error_code: Machine-readable error code
            - status_code: HTTP status code (429)
            - integration_name: Integration name if set
            - retry_after: Seconds to wait before retry if set
            - details: Additional error context
        """
        result = super().to_dict()
        # Add retry_after to top-level for backward compatibility
        result["retry_after"] = self.retry_after
        return result


class IntegrationConnectionError(IntegrationError):
    """
    Raised when connection to external service fails.

    This error indicates a network-level failure when attempting to
    communicate with the external service, such as DNS resolution
    failure, connection timeout, or connection refused.

    Example:
        >>> raise IntegrationConnectionError(
        ...     message="Failed to connect to Jira: Connection timeout",
        ...     integration_name="jira-cloud",
        ...     details={"host": "example.atlassian.net", "timeout": 30}
        ... )
    """

    def __init__(
        self,
        message: str,
        integration_name: str = "",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize integration connection error.

        Args:
            message: Human-readable error description
            integration_name: Name of the integration with connection failure
            details: Additional context (e.g., host, port, timeout)
        """
        super().__init__(
            message=message,
            integration_name=integration_name,
            error_code="CONNECTION_ERROR",
            status_code=502,
            details=details,
        )
