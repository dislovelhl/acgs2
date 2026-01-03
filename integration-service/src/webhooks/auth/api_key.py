"""
API Key authentication handler for ACGS-2 Integration Service.

This module provides API key-based authentication for webhooks, supporting
validation of incoming requests with API keys and adding API keys to outgoing
requests. Supports multiple header formats (X-API-Key, Authorization with
API-Key prefix) and implements constant-time comparison for security.
"""

import logging
import secrets
from typing import Dict, Optional

from pydantic import SecretStr

from ..models import WebhookAuthType
from .base import WebhookAuthHandler
from .models import AuthResult

logger = logging.getLogger(__name__)


class ApiKeyAuthHandler(WebhookAuthHandler):
    """
    API Key authentication handler.

    Validates API keys passed in request headers against a set of known valid keys.
    Supports multiple header formats (X-API-Key, Authorization with API-Key prefix).
    """

    def __init__(
        self,
        valid_keys: Optional[Dict[str, str]] = None,
        header_name: str = "X-API-Key",
        key_prefix: Optional[str] = None,
        api_key: Optional[SecretStr] = None,
    ):
        """
        Initialize API key handler.

        Args:
            valid_keys: Dict mapping API key values to their identifiers/principals
            header_name: Header name to look for API key
            key_prefix: Optional prefix to strip (e.g., "API-Key " or "Bearer ")
            api_key: API key for outgoing requests (SecretStr for security)
        """
        self._valid_keys: Dict[str, str] = valid_keys or {}
        self._header_name = header_name
        self._key_prefix = key_prefix
        self._api_key = api_key

    @property
    def auth_type(self) -> WebhookAuthType:
        return WebhookAuthType.API_KEY

    def add_valid_key(self, key: str, principal: str) -> None:
        """Add a valid API key."""
        self._valid_keys[key] = principal

    def remove_valid_key(self, key: str) -> bool:
        """Remove a valid API key. Returns True if key was present."""
        if key in self._valid_keys:
            del self._valid_keys[key]
            return True
        return False

    def _get_header_value(self, headers: Dict[str, str]) -> Optional[str]:
        """Get the API key from headers (case-insensitive lookup)."""
        # Normalize header names to lowercase for lookup
        normalized_headers = {k.lower(): v for k, v in headers.items()}
        header_name_lower = self._header_name.lower()

        value = normalized_headers.get(header_name_lower)
        if value is None:
            # Try Authorization header as fallback
            auth_header = normalized_headers.get("authorization")
            if auth_header and auth_header.lower().startswith("api-key "):
                value = auth_header[8:]  # len("API-Key ") = 8

        if value and self._key_prefix:
            if value.startswith(self._key_prefix):
                value = value[len(self._key_prefix) :]
            else:
                # Prefix expected but not found
                return None

        return value.strip() if value else None

    async def verify_request(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> AuthResult:
        """Verify API key in request headers."""
        api_key = self._get_header_value(headers)

        if api_key is None:
            return AuthResult.failure(
                auth_type=self.auth_type,
                error_code="MISSING_API_KEY",
                error_message=f"API key not found in {self._header_name} header",
            )

        # Use constant-time comparison to prevent timing attacks
        for valid_key, principal in self._valid_keys.items():
            if secrets.compare_digest(api_key, valid_key):
                logger.debug(f"API key authenticated for principal: {principal}")
                return AuthResult.success(
                    auth_type=self.auth_type,
                    principal=principal,
                    metadata={"header": self._header_name},
                )

        logger.warning("Invalid API key provided")
        return AuthResult.failure(
            auth_type=self.auth_type,
            error_code="INVALID_API_KEY",
            error_message="Invalid API key",
        )

    async def prepare_headers(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> Dict[str, str]:
        """Add API key to outgoing request headers."""
        result = dict(headers)

        if self._api_key:
            key_value = self._api_key.get_secret_value()
            if self._key_prefix:
                key_value = f"{self._key_prefix}{key_value}"
            result[self._header_name] = key_value

        return result


__all__ = [
    "ApiKeyAuthHandler",
]
