"""
Webhook authentication exceptions for ACGS-2 Integration Service.

This module defines custom exception classes for webhook authentication errors,
providing detailed error codes, HTTP status codes, and contextual details for
debugging and error handling.
"""

from typing import Any, Dict, Optional


class WebhookAuthError(Exception):
    """Base exception for webhook authentication errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "AUTH_ERROR",
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class InvalidSignatureError(WebhookAuthError):
    """Raised when HMAC signature verification fails."""

    def __init__(
        self, message: str = "Invalid signature", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="INVALID_SIGNATURE",
            status_code=401,
            details=details,
        )


class InvalidApiKeyError(WebhookAuthError):
    """Raised when API key validation fails."""

    def __init__(
        self, message: str = "Invalid or missing API key", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="INVALID_API_KEY",
            status_code=401,
            details=details,
        )


class InvalidBearerTokenError(WebhookAuthError):
    """Raised when Bearer token validation fails."""

    def __init__(
        self,
        message: str = "Invalid or expired bearer token",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="INVALID_BEARER_TOKEN",
            status_code=401,
            details=details,
        )


class TokenExpiredError(WebhookAuthError):
    """Raised when OAuth token has expired."""

    def __init__(
        self, message: str = "Token has expired", details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="TOKEN_EXPIRED",
            status_code=401,
            details=details,
        )


class SignatureTimestampError(WebhookAuthError):
    """Raised when signature timestamp is outside acceptable window."""

    def __init__(
        self,
        message: str = "Request timestamp is too old or in the future",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="TIMESTAMP_ERROR",
            status_code=401,
            details=details,
        )


class MissingAuthHeaderError(WebhookAuthError):
    """Raised when required authentication header is missing."""

    def __init__(
        self,
        header_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        msg = message or f"Missing required header: {header_name}"
        super().__init__(
            message=msg,
            error_code="MISSING_AUTH_HEADER",
            status_code=401,
            details={"header": header_name, **(details or {})},
        )


__all__ = [
    "WebhookAuthError",
    "InvalidSignatureError",
    "InvalidApiKeyError",
    "InvalidBearerTokenError",
    "TokenExpiredError",
    "SignatureTimestampError",
    "MissingAuthHeaderError",
]
