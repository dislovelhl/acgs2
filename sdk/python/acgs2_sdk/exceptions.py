"""
ACGS-2 SDK Exceptions
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import Any

from acgs2_sdk.constants import CONSTITUTIONAL_HASH


class ACGS2Error(Exception):
    """Base exception for ACGS-2 SDK errors."""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        constitutional_hash: str = CONSTITUTIONAL_HASH,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.constitutional_hash = constitutional_hash
        self.details = details or {}

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"constitutional_hash={self.constitutional_hash!r})"
        )


class ConstitutionalHashMismatchError(ACGS2Error):
    """Raised when constitutional hash validation fails."""

    def __init__(
        self,
        message: str = "Constitutional hash mismatch",
        expected: str = CONSTITUTIONAL_HASH,
        received: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="CONSTITUTIONAL_HASH_MISMATCH",
            details={"expected": expected, "received": received},
        )
        self.expected = expected
        self.received = received


class AuthenticationError(ACGS2Error):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message=message, code="AUTHENTICATION_ERROR")


class AuthorizationError(ACGS2Error):
    """Raised when authorization is denied."""

    def __init__(self, message: str = "Authorization denied") -> None:
        super().__init__(message=message, code="AUTHORIZATION_ERROR")


class ValidationError(ACGS2Error):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        errors: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"errors": errors or {}},
        )
        self.errors = errors or {}


class NetworkError(ACGS2Error):
    """Raised when a network error occurs."""

    def __init__(
        self,
        message: str = "Network error",
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="NETWORK_ERROR",
            details={"status_code": status_code},
        )
        self.status_code = status_code


class RateLimitError(ACGS2Error):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="RATE_LIMIT_ERROR",
            details={"retry_after": retry_after},
        )
        self.retry_after = retry_after


class TimeoutError(ACGS2Error):
    """Raised when a request times out."""

    def __init__(self, message: str = "Request timed out") -> None:
        super().__init__(message=message, code="TIMEOUT_ERROR")


class ResourceNotFoundError(ACGS2Error):
    """Raised when a resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            details={"resource_type": resource_type, "resource_id": resource_id},
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class ConflictError(ACGS2Error):
    """Raised when a resource conflict occurs."""

    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message=message, code="CONFLICT_ERROR")


class ServiceUnavailableError(ACGS2Error):
    """Raised when the service is unavailable."""

    def __init__(self, message: str = "Service unavailable") -> None:
        super().__init__(message=message, code="SERVICE_UNAVAILABLE")
