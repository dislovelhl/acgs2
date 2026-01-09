"""
Authentication exception classes for the integration-service.

Provides exceptions for webhook and API authentication errors including:
- API key validation failures
- HMAC signature verification failures
- OAuth/Bearer token validation failures
- Missing authentication headers
- Timestamp validation errors
"""

from typing import Any, Dict, Optional

from .base import BaseIntegrationServiceError


class AuthenticationError(BaseIntegrationServiceError):
    """
    Base exception for authentication-related errors.

    All authentication exceptions inherit from this class to enable
    catch-all authentication error handling.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error identifier
        status_code: HTTP status code (defaults to 401 Unauthorized)
        details: Additional context about the authentication failure

    Example:
        >>> error = AuthenticationError(
        ...     message="Authentication failed",
        ...     error_code="AUTH_ERROR",
        ...     details={"reason": "invalid credentials"}
        ... )
        >>> error.status_code
        401
    """

    def __init__(
        self,
        message: str,
        error_code: str = "AUTH_ERROR",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize authentication error.

        Args:
            message: Human-readable error description
            error_code: Machine-readable error identifier (default: "AUTH_ERROR")
            status_code: HTTP status code (default: 401)
            details: Additional context about the error (default: {})
        """
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class InvalidSignatureError(AuthenticationError):
    """
    Raised when HMAC signature verification fails.

    This error indicates that the computed signature does not match
    the provided signature, suggesting the request may have been
    tampered with or is using an incorrect secret.

    Example:
        >>> raise InvalidSignatureError(
        ...     message="Signature mismatch",
        ...     details={"algorithm": "sha256"}
        ... )
    """

    def __init__(
        self,
        message: str = "Invalid signature",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize invalid signature error.

        Args:
            message: Human-readable error description (default: "Invalid signature")
            details: Additional context (e.g., algorithm, header name)
        """
        super().__init__(
            message=message,
            error_code="INVALID_SIGNATURE",
            status_code=401,
            details=details,
        )


class InvalidApiKeyError(AuthenticationError):
    """
    Raised when API key validation fails.

    This error indicates the provided API key is either invalid,
    missing, or does not match any known valid keys.

    Example:
        >>> raise InvalidApiKeyError(
        ...     message="API key not recognized",
        ...     details={"header": "X-API-Key"}
        ... )
    """

    def __init__(
        self,
        message: str = "Invalid or missing API key",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize invalid API key error.

        Args:
            message: Human-readable error description (default: "Invalid or missing API key")
            details: Additional context (e.g., header name, key format)
        """
        super().__init__(
            message=message,
            error_code="INVALID_API_KEY",
            status_code=401,
            details=details,
        )


class InvalidBearerTokenError(AuthenticationError):
    """
    Raised when Bearer token validation fails.

    This error indicates the OAuth/Bearer token is invalid, malformed,
    or failed validation against the token introspection endpoint.

    Example:
        >>> raise InvalidBearerTokenError(
        ...     message="Token validation failed",
        ...     details={"token_endpoint": "https://auth.example.com/validate"}
        ... )
    """

    def __init__(
        self,
        message: str = "Invalid or expired bearer token",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize invalid bearer token error.

        Args:
            message: Human-readable error description (default: "Invalid or expired bearer token")
            details: Additional context (e.g., validation endpoint, reason)
        """
        super().__init__(
            message=message,
            error_code="INVALID_BEARER_TOKEN",
            status_code=401,
            details=details,
        )


class TokenExpiredError(AuthenticationError):
    """
    Raised when OAuth/Bearer token has expired.

    This error specifically indicates the token was valid but has
    exceeded its lifetime. The client should refresh the token.

    Example:
        >>> raise TokenExpiredError(
        ...     message="Access token expired at 2024-01-01T12:00:00Z",
        ...     details={"expired_at": "2024-01-01T12:00:00Z"}
        ... )
    """

    def __init__(
        self,
        message: str = "Token has expired",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize token expired error.

        Args:
            message: Human-readable error description (default: "Token has expired")
            details: Additional context (e.g., expiration time, issued_at)
        """
        super().__init__(
            message=message,
            error_code="TOKEN_EXPIRED",
            status_code=401,
            details=details,
        )


class SignatureTimestampError(AuthenticationError):
    """
    Raised when signature timestamp is outside acceptable window.

    This error provides replay attack protection by rejecting requests
    with timestamps that are too old or in the future.

    Example:
        >>> raise SignatureTimestampError(
        ...     message="Request is 600 seconds old (max: 300)",
        ...     details={"age_seconds": 600, "max_age": 300}
        ... )
    """

    def __init__(
        self,
        message: str = "Request timestamp is too old or in the future",
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize signature timestamp error.

        Args:
            message: Human-readable error description
                (default: "Request timestamp is too old or in the future")
            details: Additional context (e.g., timestamp, age_seconds, tolerance)
        """
        super().__init__(
            message=message,
            error_code="TIMESTAMP_ERROR",
            status_code=401,
            details=details,
        )


class MissingAuthHeaderError(AuthenticationError):
    """
    Raised when required authentication header is missing.

    This error indicates the request did not include a required
    authentication header (e.g., Authorization, X-API-Key).

    Example:
        >>> raise MissingAuthHeaderError(
        ...     header_name="X-API-Key",
        ...     message="X-API-Key header is required"
        ... )
    """

    def __init__(
        self,
        header_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize missing auth header error.

        Args:
            header_name: Name of the missing header
            message: Human-readable error description (default: auto-generated from header_name)
            details: Additional context (automatically includes header name)
        """
        msg = message or f"Missing required header: {header_name}"
        # Merge header_name into details
        merged_details = {"header": header_name}
        if details:
            merged_details.update(details)

        super().__init__(
            message=msg,
            error_code="MISSING_AUTH_HEADER",
            status_code=401,
            details=merged_details,
        )


# Backward compatibility alias
WebhookAuthError = AuthenticationError
