"""
OAuth 2.0 Bearer token authentication handler for ACGS-2 Integration Service.

This module provides OAuth 2.0 bearer token authentication for webhooks, supporting
token validation against remote token info endpoints, local token validation, token
refresh using refresh tokens, and scope verification. Implements proper token
expiration handling with clock skew tolerance.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import SecretStr

from ..models import WebhookAuthType
from .base import WebhookAuthHandler
from .models import AuthResult, OAuthToken

logger = logging.getLogger(__name__)


class OAuthBearerAuthHandler(WebhookAuthHandler):
    """
    OAuth 2.0 Bearer token authentication handler.

    Supports:
    - Token validation against token info endpoint
    - Local token validation with optional JWKS
    - Token refresh using refresh tokens
    - Scope verification
    """

    def __init__(
        self,
        token_info_url: Optional[str] = None,
        required_scopes: Optional[List[str]] = None,
        access_token: Optional[SecretStr] = None,
        refresh_token: Optional[SecretStr] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[SecretStr] = None,
        token_url: Optional[str] = None,
        valid_tokens: Optional[Dict[str, OAuthToken]] = None,
    ):
        """
        Initialize OAuth bearer handler.

        Args:
            token_info_url: URL to validate tokens (e.g., /oauth/token_info)
            required_scopes: Required scopes for authorization
            access_token: Access token for outgoing requests
            refresh_token: Refresh token for token refresh
            client_id: OAuth client ID for token refresh
            client_secret: OAuth client secret for token refresh
            token_url: Token endpoint URL for refresh
            valid_tokens: Dict of valid tokens (for local validation)
        """
        self._token_info_url = token_info_url
        self._required_scopes = set(required_scopes or [])
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._valid_tokens: Dict[str, OAuthToken] = valid_tokens or {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self._current_token: Optional[OAuthToken] = None

    @property
    def auth_type(self) -> WebhookAuthType:
        return WebhookAuthType.OAUTH2

    async def _get_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def add_valid_token(self, token_value: str, token: OAuthToken) -> None:
        """Add a valid token for local validation."""
        self._valid_tokens[token_value] = token

    def remove_valid_token(self, token_value: str) -> bool:
        """Remove a valid token. Returns True if token was present."""
        if token_value in self._valid_tokens:
            del self._valid_tokens[token_value]
            return True
        return False

    def _extract_bearer_token(self, headers: Dict[str, str]) -> Optional[str]:
        """Extract bearer token from Authorization header."""
        normalized_headers = {k.lower(): v for k, v in headers.items()}
        auth_header = normalized_headers.get("authorization")

        if auth_header is None:
            return None

        # Bearer token format: "Bearer <token>"
        match = re.match(r"^Bearer\s+(.+)$", auth_header, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return None

    async def _validate_token_local(self, token_value: str) -> Tuple[bool, Optional[OAuthToken]]:
        """Validate token against local store."""
        token = self._valid_tokens.get(token_value)
        if token is None:
            return False, None

        if token.is_expired:
            return False, token

        return True, token

    async def _validate_token_remote(
        self, token_value: str
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate token against remote token info endpoint."""
        if self._token_info_url is None:
            return False, None

        try:
            client = await self._get_http_client()
            response = await client.post(
                self._token_info_url,
                data={"token": token_value},
            )

            if response.status_code != 200:
                return False, None

            token_info = response.json()

            # Check if token is active
            if not token_info.get("active", False):
                return False, token_info

            return True, token_info

        except Exception as e:
            logger.error(f"Token validation request failed: {e}")
            return False, None

    async def verify_request(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> AuthResult:
        """Verify bearer token in request."""
        token_value = self._extract_bearer_token(headers)

        if token_value is None:
            return AuthResult.failure(
                auth_type=self.auth_type,
                error_code="MISSING_BEARER_TOKEN",
                error_message="Missing or invalid Authorization header",
            )

        # Try local validation first
        is_valid, token = await self._validate_token_local(token_value)

        if is_valid and token is not None:
            # Check scopes
            token_scopes = set(token.scopes)
            if self._required_scopes and not self._required_scopes.issubset(token_scopes):
                missing = self._required_scopes - token_scopes
                return AuthResult.failure(
                    auth_type=self.auth_type,
                    error_code="INSUFFICIENT_SCOPE",
                    error_message=f"Missing required scopes: {', '.join(missing)}",
                )

            return AuthResult.success(
                auth_type=self.auth_type,
                principal="oauth_user",
                scopes=list(token_scopes),
                metadata={"expires_at": token.expires_at.isoformat() if token.expires_at else None},
            )

        if token is not None and token.is_expired:
            return AuthResult.failure(
                auth_type=self.auth_type,
                error_code="TOKEN_EXPIRED",
                error_message="Bearer token has expired",
            )

        # Try remote validation
        if self._token_info_url:
            is_valid, token_info = await self._validate_token_remote(token_value)

            if is_valid and token_info:
                # Check scopes from token info
                scope_str = token_info.get("scope", "")
                token_scopes = set(scope_str.split()) if scope_str else set()

                if self._required_scopes and not self._required_scopes.issubset(token_scopes):
                    missing = self._required_scopes - token_scopes
                    return AuthResult.failure(
                        auth_type=self.auth_type,
                        error_code="INSUFFICIENT_SCOPE",
                        error_message=f"Missing required scopes: {', '.join(missing)}",
                    )

                return AuthResult.success(
                    auth_type=self.auth_type,
                    principal=token_info.get("sub") or token_info.get("username") or "oauth_user",
                    scopes=list(token_scopes),
                    metadata={"token_info": token_info},
                )

        return AuthResult.failure(
            auth_type=self.auth_type,
            error_code="INVALID_TOKEN",
            error_message="Bearer token validation failed",
        )

    async def prepare_headers(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> Dict[str, str]:
        """Add bearer token to outgoing request headers."""
        result = dict(headers)

        # Check if we need to refresh the token
        await self._ensure_valid_token()

        if self._current_token and not self._current_token.is_expired:
            token_value = self._current_token.access_token.get_secret_value()
            result["Authorization"] = f"Bearer {token_value}"
        elif self._access_token:
            result["Authorization"] = f"Bearer {self._access_token.get_secret_value()}"

        return result

    async def _ensure_valid_token(self) -> None:
        """Ensure we have a valid access token, refreshing if necessary."""
        if self._current_token is None and self._access_token:
            # Initialize current token from access_token
            self._current_token = OAuthToken(
                access_token=self._access_token,
                refresh_token=self._refresh_token,
            )
            return

        if self._current_token is None:
            return

        if not self._current_token.is_expired:
            return

        # Try to refresh
        if self._current_token.refresh_token and self._token_url:
            try:
                new_token = await self._refresh_access_token()
                if new_token:
                    self._current_token = new_token
            except Exception as e:
                logger.error(f"Token refresh failed: {e}")

    async def _refresh_access_token(self) -> Optional[OAuthToken]:
        """Refresh the access token using refresh token."""
        if not self._token_url or not self._current_token or not self._current_token.refresh_token:
            return None

        try:
            client = await self._get_http_client()

            data = {
                "grant_type": "refresh_token",
                "refresh_token": self._current_token.refresh_token.get_secret_value(),
            }

            if self._client_id:
                data["client_id"] = self._client_id
            if self._client_secret:
                data["client_secret"] = self._client_secret.get_secret_value()

            response = await client.post(self._token_url, data=data)

            if response.status_code != 200:
                logger.error(f"Token refresh failed with status {response.status_code}")
                return None

            token_data = response.json()
            return OAuthToken(
                access_token=SecretStr(token_data["access_token"]),
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in"),
                refresh_token=(
                    SecretStr(token_data["refresh_token"])
                    if "refresh_token" in token_data
                    else self._current_token.refresh_token
                ),
                scope=token_data.get("scope"),
            )

        except Exception as e:
            logger.error(f"Token refresh request failed: {e}")
            return None

    async def refresh_token(self) -> Optional[OAuthToken]:
        """
        Public method to refresh the access token.

        Returns:
            New OAuthToken if refresh succeeded, None otherwise
        """
        return await self._refresh_access_token()


__all__ = [
    "OAuthBearerAuthHandler",
]
