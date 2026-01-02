"""
Webhook authentication handlers for ACGS-2 Integration Service.

Provides authentication handlers for webhook endpoints including:
- API key validation
- HMAC signature verification
- OAuth 2.0 bearer token validation

Supports both incoming webhook verification (validating requests to our endpoints)
and outgoing webhook authentication (authenticating requests we send).
"""

import abc
import hashlib
import hmac
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr

from .models import WebhookAuthType

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


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


# ============================================================================
# Authentication Result Models
# ============================================================================


class AuthResult(BaseModel):
    """Result of an authentication attempt."""

    authenticated: bool = Field(..., description="Whether authentication succeeded")
    auth_type: WebhookAuthType = Field(..., description="Type of authentication used")
    principal: Optional[str] = Field(
        None, description="Authenticated principal (user, key ID, etc.)"
    )
    scopes: List[str] = Field(default_factory=list, description="Granted scopes/permissions")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional auth metadata")

    # Error details (if not authenticated)
    error_code: Optional[str] = Field(None, description="Error code if authentication failed")
    error_message: Optional[str] = Field(None, description="Error message if authentication failed")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    @classmethod
    def success(
        cls,
        auth_type: WebhookAuthType,
        principal: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AuthResult":
        """Create a successful authentication result."""
        return cls(
            authenticated=True,
            auth_type=auth_type,
            principal=principal,
            scopes=scopes or [],
            metadata=metadata or {},
        )

    @classmethod
    def failure(
        cls,
        auth_type: WebhookAuthType,
        error_code: str,
        error_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "AuthResult":
        """Create a failed authentication result."""
        return cls(
            authenticated=False,
            auth_type=auth_type,
            error_code=error_code,
            error_message=error_message,
            metadata=metadata or {},
        )


class OAuthToken(BaseModel):
    """OAuth 2.0 token model."""

    access_token: SecretStr = Field(..., description="The access token")
    token_type: str = Field(default="Bearer", description="Token type (usually Bearer)")
    expires_in: Optional[int] = Field(None, description="Token lifetime in seconds")
    refresh_token: Optional[SecretStr] = Field(None, description="Refresh token if available")
    scope: Optional[str] = Field(None, description="Granted scopes (space-separated)")

    # Computed fields
    issued_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the token was issued",
    )
    expires_at: Optional[datetime] = Field(None, description="When the token expires")

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    def model_post_init(self, _: Any) -> None:
        """Calculate expiration time if not set."""
        if self.expires_at is None and self.expires_in is not None:
            self.expires_at = self.issued_at + timedelta(seconds=self.expires_in)

    @property
    def is_expired(self) -> bool:
        """Check if token is expired."""
        if self.expires_at is None:
            return False
        # Add 30 second buffer for clock skew
        return datetime.now(timezone.utc) >= (self.expires_at - timedelta(seconds=30))

    @property
    def scopes(self) -> List[str]:
        """Get scopes as a list."""
        if self.scope is None:
            return []
        return self.scope.split()


# ============================================================================
# Abstract Base Handler
# ============================================================================


class WebhookAuthHandler(abc.ABC):
    """
    Abstract base class for webhook authentication handlers.

    Handlers can be used to:
    - Verify incoming webhook requests (requests received by our service)
    - Prepare authentication for outgoing webhook requests (requests we send)
    """

    @property
    @abc.abstractmethod
    def auth_type(self) -> WebhookAuthType:
        """Get the authentication type this handler supports."""
        pass

    @abc.abstractmethod
    async def verify_request(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> AuthResult:
        """
        Verify an incoming webhook request.

        Args:
            headers: Request headers (case-insensitive lookup)
            body: Raw request body bytes
            method: HTTP method
            url: Request URL (optional)

        Returns:
            AuthResult indicating if the request is authenticated
        """
        pass

    @abc.abstractmethod
    async def prepare_headers(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Prepare authentication headers for an outgoing request.

        Args:
            headers: Existing headers to augment
            body: Request body bytes
            method: HTTP method
            url: Request URL (optional)

        Returns:
            Headers dict with authentication headers added
        """
        pass


# ============================================================================
# API Key Authentication Handler
# ============================================================================


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


# ============================================================================
# HMAC Signature Authentication Handler
# ============================================================================


class HmacAuthHandler(WebhookAuthHandler):
    """
    HMAC signature authentication handler.

    Verifies webhook requests using HMAC signatures for payload integrity
    and authenticity. Supports SHA-256 and SHA-512 algorithms.

    Security features:
    - Constant-time signature comparison to prevent timing attacks
    - Timestamp validation for replay protection
    - Multiple signature formats (sha256=xxx, t=xxx,v1=xxx)
    """

    # Supported algorithms
    ALGORITHMS = {
        "sha256": hashlib.sha256,
        "sha512": hashlib.sha512,
    }

    def __init__(
        self,
        secret: SecretStr,
        signature_header: str = "X-Webhook-Signature",
        timestamp_header: str = "X-Webhook-Timestamp",
        algorithm: str = "sha256",
        timestamp_tolerance_seconds: int = 300,
        require_timestamp: bool = True,
    ):
        """
        Initialize HMAC handler.

        Args:
            secret: HMAC secret key
            signature_header: Header name for signature
            timestamp_header: Header name for timestamp
            algorithm: Hash algorithm (sha256 or sha512)
            timestamp_tolerance_seconds: Maximum age of request in seconds
            require_timestamp: Whether to require and validate timestamp
        """
        self._secret = secret
        self._signature_header = signature_header
        self._timestamp_header = timestamp_header
        self._timestamp_tolerance = timestamp_tolerance_seconds
        self._require_timestamp = require_timestamp

        algorithm = algorithm.lower()
        if algorithm not in self.ALGORITHMS:
            raise ValueError(f"Unsupported algorithm: {algorithm}. Use 'sha256' or 'sha512'")
        self._algorithm = algorithm
        self._hash_func = self.ALGORITHMS[algorithm]

    @property
    def auth_type(self) -> WebhookAuthType:
        return WebhookAuthType.HMAC

    def _compute_signature(self, payload: bytes, timestamp: Optional[str] = None) -> str:
        """
        Compute HMAC signature for payload.

        Args:
            payload: Request body bytes
            timestamp: Optional timestamp to include in signed data

        Returns:
            Hex-encoded signature
        """
        secret = self._secret.get_secret_value().encode("utf-8")

        # If timestamp provided, prepend it to the payload (Stripe-style)
        if timestamp:
            signed_payload = f"{timestamp}.".encode("utf-8") + payload
        else:
            signed_payload = payload

        signature = hmac.new(secret, signed_payload, self._hash_func).hexdigest()
        return signature

    def _parse_signature_header(self, header_value: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse signature header value.

        Supports multiple formats:
        - "sha256=abcd1234..."  (simple format)
        - "t=1234567890,v1=abcd1234..."  (Stripe-style with timestamp)

        Args:
            header_value: Raw header value

        Returns:
            Tuple of (signature, timestamp) - timestamp may be None
        """
        header_value = header_value.strip()

        # Try Stripe-style format: t=timestamp,v1=signature
        if "," in header_value and "=" in header_value:
            parts = {}
            for part in header_value.split(","):
                if "=" in part:
                    key, value = part.split("=", 1)
                    parts[key.strip()] = value.strip()

            timestamp = parts.get("t")
            signature = parts.get("v1") or parts.get("v2")
            if signature:
                return signature, timestamp

        # Try simple format: algorithm=signature
        if "=" in header_value:
            prefix, signature = header_value.split("=", 1)
            prefix_lower = prefix.lower().strip()
            if prefix_lower in ("sha256", "sha512"):
                return signature.strip(), None
            # If prefix doesn't match known algorithm, treat whole value as signature
            return header_value, None

        # Plain signature
        return header_value, None

    def _validate_timestamp(self, timestamp_str: str) -> bool:
        """
        Validate timestamp is within acceptable range.

        Args:
            timestamp_str: Timestamp as string (epoch seconds or ISO format)

        Returns:
            True if timestamp is valid
        """
        try:
            # Try parsing as epoch seconds
            if timestamp_str.isdigit():
                timestamp = int(timestamp_str)
                request_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            else:
                # Try ISO format
                request_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            now = datetime.now(timezone.utc)
            age = abs((now - request_time).total_seconds())

            return age <= self._timestamp_tolerance

        except (ValueError, OverflowError):
            return False

    async def verify_request(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> AuthResult:
        """Verify HMAC signature on request."""
        # Normalize headers
        normalized_headers = {k.lower(): v for k, v in headers.items()}

        # Get signature header
        sig_header_lower = self._signature_header.lower()
        signature_value = normalized_headers.get(sig_header_lower)

        if signature_value is None:
            return AuthResult.failure(
                auth_type=self.auth_type,
                error_code="MISSING_SIGNATURE",
                error_message=f"Missing {self._signature_header} header",
            )

        # Parse signature header
        provided_signature, header_timestamp = self._parse_signature_header(signature_value)

        if provided_signature is None:
            return AuthResult.failure(
                auth_type=self.auth_type,
                error_code="INVALID_SIGNATURE_FORMAT",
                error_message="Could not parse signature from header",
            )

        # Get timestamp from header or dedicated timestamp header
        timestamp = header_timestamp
        if timestamp is None:
            ts_header_lower = self._timestamp_header.lower()
            timestamp = normalized_headers.get(ts_header_lower)

        # Validate timestamp if required
        if self._require_timestamp:
            if timestamp is None:
                return AuthResult.failure(
                    auth_type=self.auth_type,
                    error_code="MISSING_TIMESTAMP",
                    error_message=f"Missing {self._timestamp_header} header",
                )

            if not self._validate_timestamp(timestamp):
                return AuthResult.failure(
                    auth_type=self.auth_type,
                    error_code="TIMESTAMP_EXPIRED",
                    error_message=(
                        f"Request timestamp is outside acceptable window "
                        f"({self._timestamp_tolerance}s)"
                    ),
                )

        # Compute expected signature
        expected_signature = self._compute_signature(body, timestamp if timestamp else None)

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(provided_signature.lower(), expected_signature.lower()):
            logger.warning("HMAC signature verification failed")
            return AuthResult.failure(
                auth_type=self.auth_type,
                error_code="INVALID_SIGNATURE",
                error_message="Signature verification failed",
            )

        logger.debug("HMAC signature verified successfully")
        return AuthResult.success(
            auth_type=self.auth_type,
            principal="hmac_verified",
            metadata={
                "algorithm": self._algorithm,
                "timestamp": timestamp,
            },
        )

    async def prepare_headers(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> Dict[str, str]:
        """Add HMAC signature to outgoing request headers."""
        result = dict(headers)

        # Generate timestamp
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        result[self._timestamp_header] = timestamp

        # Compute signature
        signature = self._compute_signature(body, timestamp)
        result[self._signature_header] = f"{self._algorithm}={signature}"

        return result


# ============================================================================
# OAuth Bearer Token Authentication Handler
# ============================================================================


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


# ============================================================================
# Authentication Handler Registry
# ============================================================================


class WebhookAuthRegistry:
    """
    Registry for webhook authentication handlers.

    Provides a centralized way to manage and lookup authentication handlers
    by type for both incoming and outgoing webhook authentication.
    """

    def __init__(self):
        """Initialize the registry."""
        self._handlers: Dict[WebhookAuthType, WebhookAuthHandler] = {}

    def register(self, handler: WebhookAuthHandler) -> None:
        """Register an authentication handler."""
        self._handlers[handler.auth_type] = handler
        logger.debug(f"Registered auth handler for {handler.auth_type.value}")

    def unregister(self, auth_type: WebhookAuthType) -> Optional[WebhookAuthHandler]:
        """Unregister and return an authentication handler."""
        return self._handlers.pop(auth_type, None)

    def get(self, auth_type: WebhookAuthType) -> Optional[WebhookAuthHandler]:
        """Get an authentication handler by type."""
        return self._handlers.get(auth_type)

    def get_all(self) -> Dict[WebhookAuthType, WebhookAuthHandler]:
        """Get all registered handlers."""
        return dict(self._handlers)

    async def verify_request(
        self,
        auth_type: WebhookAuthType,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> AuthResult:
        """
        Verify a request using the appropriate handler.

        Args:
            auth_type: Type of authentication to use
            headers: Request headers
            body: Request body bytes
            method: HTTP method
            url: Request URL

        Returns:
            AuthResult from the handler
        """
        if auth_type == WebhookAuthType.NONE:
            return AuthResult.success(auth_type=auth_type)

        handler = self._handlers.get(auth_type)
        if handler is None:
            return AuthResult.failure(
                auth_type=auth_type,
                error_code="NO_HANDLER",
                error_message=f"No handler registered for {auth_type.value}",
            )

        return await handler.verify_request(headers, body, method, url)

    async def prepare_headers(
        self,
        auth_type: WebhookAuthType,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Prepare authentication headers using the appropriate handler.

        Args:
            auth_type: Type of authentication to use
            headers: Existing headers
            body: Request body bytes
            method: HTTP method
            url: Request URL

        Returns:
            Headers dict with authentication added
        """
        if auth_type == WebhookAuthType.NONE:
            return dict(headers)

        handler = self._handlers.get(auth_type)
        if handler is None:
            logger.warning(f"No handler for {auth_type.value}, returning headers unchanged")
            return dict(headers)

        return await handler.prepare_headers(headers, body, method, url)


# ============================================================================
# Factory Functions
# ============================================================================


def create_api_key_handler(
    valid_keys: Optional[Dict[str, str]] = None,
    header_name: str = "X-API-Key",
    api_key: Optional[SecretStr] = None,
) -> ApiKeyAuthHandler:
    """
    Create an API key authentication handler.

    Args:
        valid_keys: Dict mapping API key values to principals
        header_name: Header name for API key
        api_key: API key for outgoing requests

    Returns:
        Configured ApiKeyAuthHandler
    """
    return ApiKeyAuthHandler(
        valid_keys=valid_keys,
        header_name=header_name,
        api_key=api_key,
    )


def create_hmac_handler(
    secret: SecretStr,
    signature_header: str = "X-Webhook-Signature",
    timestamp_header: str = "X-Webhook-Timestamp",
    algorithm: str = "sha256",
    timestamp_tolerance_seconds: int = 300,
) -> HmacAuthHandler:
    """
    Create an HMAC signature authentication handler.

    Args:
        secret: HMAC secret key
        signature_header: Header name for signature
        timestamp_header: Header name for timestamp
        algorithm: Hash algorithm (sha256 or sha512)
        timestamp_tolerance_seconds: Maximum request age

    Returns:
        Configured HmacAuthHandler
    """
    return HmacAuthHandler(
        secret=secret,
        signature_header=signature_header,
        timestamp_header=timestamp_header,
        algorithm=algorithm,
        timestamp_tolerance_seconds=timestamp_tolerance_seconds,
    )


def create_oauth_handler(
    token_info_url: Optional[str] = None,
    required_scopes: Optional[List[str]] = None,
    access_token: Optional[SecretStr] = None,
    refresh_token: Optional[SecretStr] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[SecretStr] = None,
    token_url: Optional[str] = None,
) -> OAuthBearerAuthHandler:
    """
    Create an OAuth bearer token authentication handler.

    Args:
        token_info_url: URL to validate tokens
        required_scopes: Required scopes for authorization
        access_token: Access token for outgoing requests
        refresh_token: Refresh token for refresh flow
        client_id: OAuth client ID
        client_secret: OAuth client secret
        token_url: Token endpoint URL

    Returns:
        Configured OAuthBearerAuthHandler
    """
    return OAuthBearerAuthHandler(
        token_info_url=token_info_url,
        required_scopes=required_scopes,
        access_token=access_token,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_url=token_url,
    )


def create_default_registry() -> WebhookAuthRegistry:
    """
    Create a registry with default handlers.

    Returns:
        WebhookAuthRegistry with common handlers registered
    """
    registry = WebhookAuthRegistry()
    # Note: Handlers need to be configured with secrets before use
    # This just provides the registry structure
    return registry
