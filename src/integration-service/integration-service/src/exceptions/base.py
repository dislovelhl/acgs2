"""
Base exception classes for the integration-service.

Provides the foundational exception hierarchy that all other exceptions inherit from,
ensuring consistent error handling patterns across the service.
"""

from typing import Any, Dict, Optional


class BaseIntegrationServiceError(Exception):
    """
    Base exception for all integration-service errors.

    All custom exceptions in the integration-service should inherit from this class
    to ensure consistent error attributes and behavior.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error identifier for logging/monitoring
        status_code: HTTP status code (when applicable) for API responses
        details: Flexible dictionary for context-specific information

    Example:
        >>> error = BaseIntegrationServiceError(
        ...     message="Something went wrong",
        ...     error_code="INTEGRATION_ERROR",
        ...     status_code=500,
        ...     details={"context": "additional info"}
        ... )
        >>> error.to_dict()
        {
            'error': 'BaseIntegrationServiceError',
            'message': 'Something went wrong',
            'error_code': 'INTEGRATION_ERROR',
            'status_code': 500,
            'details': {'context': 'additional info'}
        }
    """

    def __init__(
        self,
        message: str,
        error_code: str = "INTEGRATION_ERROR",
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the base integration service error.

        Args:
            message: Human-readable error description
            error_code: Machine-readable error identifier (default: "INTEGRATION_ERROR")
            status_code: HTTP status code if applicable (default: None)
            details: Additional context about the error (default: {})
        """
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary representation.

        Useful for serializing errors in API responses or logging.

        Returns:
            Dictionary containing error information with keys:
            - error: Exception class name
            - message: Human-readable error message
            - error_code: Machine-readable error code
            - status_code: HTTP status code (if set)
            - details: Additional error context
        """
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "status_code": self.status_code,
            "details": self.details,
        }

    def __str__(self) -> str:
        """String representation of the error."""
        return f"{self.error_code}: {self.message}"

    def __repr__(self) -> str:
        """Developer-friendly representation of the error."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code!r}, "
            f"status_code={self.status_code!r}, "
            f"details={self.details!r})"
        )
