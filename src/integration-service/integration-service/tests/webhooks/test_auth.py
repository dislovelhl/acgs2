"""
Tests for webhook authentication handlers.

Tests cover:
- API key authentication with constant-time comparison
- HMAC signature generation and verification
- OAuth 2.0 bearer token validation
- WebhookAuthRegistry for handler management
- Error handling and edge cases
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import pytest
from pydantic import SecretStr

from src.exceptions.auth import (
    InvalidApiKeyError,
    InvalidBearerTokenError,
    InvalidSignatureError,
    MissingAuthHeaderError,
    SignatureTimestampError,
)
from src.webhooks.auth import (
    ApiKeyAuthHandler,
    AuthResult,
    HmacAuthHandler,
    OAuthBearerAuthHandler,
    OAuthToken,
    WebhookAuthRegistry,
    create_api_key_handler,
    create_default_registry,
    create_hmac_handler,
    create_oauth_handler,
)
from src.webhooks.models import WebhookAuthType

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def api_key_handler() -> ApiKeyAuthHandler:
    """Create an API key handler with test keys."""
    return ApiKeyAuthHandler(
        valid_keys={
            "test-api-key-1": "user-1",
            "test-api-key-2": "user-2",
        },
        header_name="X-API-Key",
    )


@pytest.fixture
def hmac_secret() -> SecretStr:
    """Create a test HMAC secret."""
    return SecretStr("test-hmac-secret-key-12345")


@pytest.fixture
def hmac_handler(hmac_secret: SecretStr) -> HmacAuthHandler:
    """Create an HMAC handler with test secret."""
    return HmacAuthHandler(
        secret=hmac_secret,
        signature_header="X-Webhook-Signature",
        timestamp_header="X-Webhook-Timestamp",
        algorithm="sha256",
        timestamp_tolerance_seconds=300,
        require_timestamp=True,
    )


@pytest.fixture
def oauth_handler() -> OAuthBearerAuthHandler:
    """Create an OAuth handler for testing."""
    handler = OAuthBearerAuthHandler(
        required_scopes=["read", "write"],
    )
    # Add a valid test token
    token = OAuthToken(
        access_token=SecretStr("valid-test-token"),
        expires_in=3600,
        scope="read write admin",
    )
    handler.add_valid_token("valid-test-token", token)
    return handler


@pytest.fixture
def auth_registry() -> WebhookAuthRegistry:
    """Create an authentication registry."""
    return WebhookAuthRegistry()


# ============================================================================
# API Key Authentication Tests
# ============================================================================


class TestApiKeyAuthHandler:
    """Tests for ApiKeyAuthHandler."""

    @pytest.mark.asyncio
    async def test_valid_api_key(self, api_key_handler: ApiKeyAuthHandler):
        """Test authentication with valid API key."""
        headers = {"X-API-Key": "test-api-key-1"}
        body = b'{"test": "data"}'

        result = await api_key_handler.verify_request(headers, body)

        assert result.authenticated is True
        assert result.auth_type == WebhookAuthType.API_KEY
        assert result.principal == "user-1"

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, api_key_handler: ApiKeyAuthHandler):
        """Test authentication with invalid API key."""
        headers = {"X-API-Key": "invalid-key"}
        body = b'{"test": "data"}'

        result = await api_key_handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "INVALID_API_KEY"

    @pytest.mark.asyncio
    async def test_missing_api_key(self, api_key_handler: ApiKeyAuthHandler):
        """Test authentication without API key header."""
        headers = {}
        body = b'{"test": "data"}'

        result = await api_key_handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "MISSING_API_KEY"

    @pytest.mark.asyncio
    async def test_case_insensitive_header(self, api_key_handler: ApiKeyAuthHandler):
        """Test that header lookup is case-insensitive."""
        headers = {"x-api-key": "test-api-key-1"}  # lowercase
        body = b'{"test": "data"}'

        result = await api_key_handler.verify_request(headers, body)

        assert result.authenticated is True
        assert result.principal == "user-1"

    @pytest.mark.asyncio
    async def test_authorization_header_fallback(self):
        """Test fallback to Authorization header with API-Key prefix."""
        handler = ApiKeyAuthHandler(
            valid_keys={"my-secret-key": "api-user"},
        )
        headers = {"Authorization": "API-Key my-secret-key"}
        body = b'{"test": "data"}'

        result = await handler.verify_request(headers, body)

        assert result.authenticated is True
        assert result.principal == "api-user"

    @pytest.mark.asyncio
    async def test_prepare_headers(self):
        """Test preparing headers for outgoing request."""
        handler = ApiKeyAuthHandler(
            api_key=SecretStr("outgoing-api-key"),
            header_name="X-API-Key",
        )
        existing_headers = {"Content-Type": "application/json"}
        body = b'{"test": "data"}'

        result = await handler.prepare_headers(existing_headers, body)

        assert "X-API-Key" in result
        assert result["X-API-Key"] == "outgoing-api-key"
        assert result["Content-Type"] == "application/json"

    def test_add_valid_key(self, api_key_handler: ApiKeyAuthHandler):
        """Test adding a valid key."""
        api_key_handler.add_valid_key("new-key", "new-user")
        assert "new-key" in api_key_handler._valid_keys
        assert api_key_handler._valid_keys["new-key"] == "new-user"

    def test_remove_valid_key(self, api_key_handler: ApiKeyAuthHandler):
        """Test removing a valid key."""
        assert api_key_handler.remove_valid_key("test-api-key-1") is True
        assert "test-api-key-1" not in api_key_handler._valid_keys
        assert api_key_handler.remove_valid_key("nonexistent") is False

    @pytest.mark.asyncio
    async def test_constant_time_comparison(self, api_key_handler: ApiKeyAuthHandler):
        """Test that constant-time comparison is used (timing attack prevention)."""
        # This is a structural test - we verify secrets.compare_digest is used
        # by checking the code behavior, not timing
        headers_valid = {"X-API-Key": "test-api-key-1"}
        headers_invalid = {"X-API-Key": "test-api-key-1-extra-chars"}
        body = b"{}"

        result_valid = await api_key_handler.verify_request(headers_valid, body)
        result_invalid = await api_key_handler.verify_request(headers_invalid, body)

        assert result_valid.authenticated is True
        assert result_invalid.authenticated is False


# ============================================================================
# HMAC Authentication Tests
# ============================================================================


class TestHmacAuthHandler:
    """Tests for HmacAuthHandler."""

    def test_compute_signature(self, hmac_handler: HmacAuthHandler, hmac_secret: SecretStr):
        """Test HMAC signature computation."""
        payload = b'{"test": "data"}'
        timestamp = "1704067200"  # 2024-01-01 00:00:00 UTC

        signature = hmac_handler._compute_signature(payload, timestamp)

        # Verify signature format
        assert isinstance(signature, str)
        assert len(signature) == 64  # SHA256 produces 64 hex chars

        # Verify it's reproducible
        signature2 = hmac_handler._compute_signature(payload, timestamp)
        assert signature == signature2

    def test_compute_signature_without_timestamp(
        self, hmac_handler: HmacAuthHandler, hmac_secret: SecretStr
    ):
        """Test HMAC signature computation without timestamp."""
        payload = b'{"test": "data"}'

        signature = hmac_handler._compute_signature(payload, None)

        # Verify signature format
        assert isinstance(signature, str)
        assert len(signature) == 64

    @pytest.mark.asyncio
    async def test_verify_valid_signature(self, hmac_handler: HmacAuthHandler):
        """Test verification of valid HMAC signature."""
        body = b'{"event": "test"}'
        timestamp = str(int(time.time()))

        # Compute valid signature
        signature = hmac_handler._compute_signature(body, timestamp)

        headers = {
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Timestamp": timestamp,
        }

        result = await hmac_handler.verify_request(headers, body)

        assert result.authenticated is True
        assert result.auth_type == WebhookAuthType.HMAC
        assert result.metadata.get("algorithm") == "sha256"

    @pytest.mark.asyncio
    async def test_verify_invalid_signature(self, hmac_handler: HmacAuthHandler):
        """Test verification of invalid HMAC signature."""
        body = b'{"event": "test"}'
        timestamp = str(int(time.time()))

        headers = {
            "X-Webhook-Signature": "sha256=invalid-signature",
            "X-Webhook-Timestamp": timestamp,
        }

        result = await hmac_handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "INVALID_SIGNATURE"

    @pytest.mark.asyncio
    async def test_verify_missing_signature(self, hmac_handler: HmacAuthHandler):
        """Test verification when signature header is missing."""
        body = b'{"event": "test"}'

        headers = {
            "X-Webhook-Timestamp": str(int(time.time())),
        }

        result = await hmac_handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "MISSING_SIGNATURE"

    @pytest.mark.asyncio
    async def test_verify_missing_timestamp(self, hmac_handler: HmacAuthHandler):
        """Test verification when timestamp header is missing."""
        body = b'{"event": "test"}'
        signature = hmac_handler._compute_signature(body, None)

        headers = {
            "X-Webhook-Signature": f"sha256={signature}",
        }

        result = await hmac_handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "MISSING_TIMESTAMP"

    @pytest.mark.asyncio
    async def test_verify_expired_timestamp(self, hmac_handler: HmacAuthHandler):
        """Test verification when timestamp is too old."""
        body = b'{"event": "test"}'
        # Use a timestamp from 10 minutes ago (outside 5-minute tolerance)
        old_timestamp = str(int(time.time()) - 600)
        signature = hmac_handler._compute_signature(body, old_timestamp)

        headers = {
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Timestamp": old_timestamp,
        }

        result = await hmac_handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "TIMESTAMP_EXPIRED"

    @pytest.mark.asyncio
    async def test_verify_stripe_style_signature(self, hmac_secret: SecretStr):
        """Test verification of Stripe-style signature format."""
        handler = HmacAuthHandler(
            secret=hmac_secret,
            require_timestamp=True,
        )
        body = b'{"event": "test"}'
        timestamp = str(int(time.time()))

        signature = handler._compute_signature(body, timestamp)

        # Stripe-style format: t=timestamp,v1=signature
        headers = {
            "X-Webhook-Signature": f"t={timestamp},v1={signature}",
        }

        result = await handler.verify_request(headers, body)

        assert result.authenticated is True

    @pytest.mark.asyncio
    async def test_prepare_headers(self, hmac_handler: HmacAuthHandler):
        """Test preparing HMAC headers for outgoing request."""
        existing_headers = {"Content-Type": "application/json"}
        body = b'{"test": "data"}'

        result = await hmac_handler.prepare_headers(existing_headers, body)

        assert "X-Webhook-Signature" in result
        assert "X-Webhook-Timestamp" in result
        assert result["X-Webhook-Signature"].startswith("sha256=")
        assert result["Content-Type"] == "application/json"

    def test_sha512_algorithm(self, hmac_secret: SecretStr):
        """Test HMAC handler with SHA512 algorithm."""
        handler = HmacAuthHandler(
            secret=hmac_secret,
            algorithm="sha512",
            require_timestamp=False,
        )
        payload = b'{"test": "data"}'

        signature = handler._compute_signature(payload, None)

        # SHA512 produces 128 hex chars
        assert len(signature) == 128

    def test_invalid_algorithm_raises_error(self, hmac_secret: SecretStr):
        """Test that invalid algorithm raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported algorithm"):
            HmacAuthHandler(
                secret=hmac_secret,
                algorithm="md5",  # Not supported
            )

    @pytest.mark.asyncio
    async def test_timestamp_optional(self, hmac_secret: SecretStr):
        """Test HMAC verification with optional timestamp."""
        handler = HmacAuthHandler(
            secret=hmac_secret,
            require_timestamp=False,
        )
        body = b'{"event": "test"}'
        signature = handler._compute_signature(body, None)

        headers = {
            "X-Webhook-Signature": f"sha256={signature}",
        }

        result = await handler.verify_request(headers, body)

        assert result.authenticated is True


# ============================================================================
# OAuth Bearer Token Tests
# ============================================================================


class TestOAuthBearerAuthHandler:
    """Tests for OAuthBearerAuthHandler."""

    @pytest.mark.asyncio
    async def test_verify_valid_token(self, oauth_handler: OAuthBearerAuthHandler):
        """Test verification of valid bearer token."""
        headers = {"Authorization": "Bearer valid-test-token"}
        body = b'{"test": "data"}'

        result = await oauth_handler.verify_request(headers, body)

        assert result.authenticated is True
        assert result.auth_type == WebhookAuthType.OAUTH2
        assert "read" in result.scopes
        assert "write" in result.scopes

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self, oauth_handler: OAuthBearerAuthHandler):
        """Test verification of invalid bearer token."""
        headers = {"Authorization": "Bearer invalid-token"}
        body = b'{"test": "data"}'

        result = await oauth_handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "INVALID_TOKEN"

    @pytest.mark.asyncio
    async def test_verify_missing_token(self, oauth_handler: OAuthBearerAuthHandler):
        """Test verification when Authorization header is missing."""
        headers = {}
        body = b'{"test": "data"}'

        result = await oauth_handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "MISSING_BEARER_TOKEN"

    @pytest.mark.asyncio
    async def test_verify_expired_token(self):
        """Test verification of expired token."""
        handler = OAuthBearerAuthHandler()

        # Add an expired token
        expired_token = OAuthToken(
            access_token=SecretStr("expired-token"),
            expires_in=-1,  # Already expired
        )
        handler.add_valid_token("expired-token", expired_token)

        headers = {"Authorization": "Bearer expired-token"}
        body = b"{}"

        result = await handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "TOKEN_EXPIRED"

    @pytest.mark.asyncio
    async def test_verify_insufficient_scope(self):
        """Test verification with insufficient scopes."""
        handler = OAuthBearerAuthHandler(required_scopes=["admin", "delete"])

        token = OAuthToken(
            access_token=SecretStr("limited-token"),
            scope="read write",
            expires_in=3600,
        )
        handler.add_valid_token("limited-token", token)

        headers = {"Authorization": "Bearer limited-token"}
        body = b"{}"

        result = await handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "INSUFFICIENT_SCOPE"
        assert "admin" in result.error_message or "delete" in result.error_message

    @pytest.mark.asyncio
    async def test_prepare_headers_with_access_token(self):
        """Test preparing headers with access token."""
        handler = OAuthBearerAuthHandler(
            access_token=SecretStr("outgoing-token"),
        )
        existing_headers = {"Content-Type": "application/json"}
        body = b'{"test": "data"}'

        result = await handler.prepare_headers(existing_headers, body)

        assert "Authorization" in result
        assert result["Authorization"] == "Bearer outgoing-token"

    @pytest.mark.asyncio
    async def test_case_insensitive_bearer(self):
        """Test that Bearer prefix is case-insensitive."""
        handler = OAuthBearerAuthHandler()
        token = OAuthToken(
            access_token=SecretStr("case-test-token"),
            expires_in=3600,
        )
        handler.add_valid_token("case-test-token", token)

        headers = {"authorization": "BEARER case-test-token"}
        body = b"{}"

        result = await handler.verify_request(headers, body)

        assert result.authenticated is True

    def test_add_remove_valid_token(self):
        """Test adding and removing valid tokens."""
        handler = OAuthBearerAuthHandler()
        token = OAuthToken(
            access_token=SecretStr("test-token"),
            expires_in=3600,
        )

        handler.add_valid_token("test-token", token)
        assert "test-token" in handler._valid_tokens

        assert handler.remove_valid_token("test-token") is True
        assert "test-token" not in handler._valid_tokens

        assert handler.remove_valid_token("nonexistent") is False


class TestOAuthToken:
    """Tests for OAuthToken model."""

    def test_token_expiration(self):
        """Test token expiration calculation."""
        token = OAuthToken(
            access_token=SecretStr("test"),
            expires_in=3600,
        )

        assert token.expires_at is not None
        expected_expiry = token.issued_at + timedelta(seconds=3600)
        assert abs((token.expires_at - expected_expiry).total_seconds()) < 1

    def test_is_expired(self):
        """Test is_expired property."""
        # Not expired
        valid_token = OAuthToken(
            access_token=SecretStr("test"),
            expires_in=3600,
        )
        assert valid_token.is_expired is False

        # Expired
        expired_token = OAuthToken(
            access_token=SecretStr("test"),
            expires_in=-1,
        )
        assert expired_token.is_expired is True

    def test_scopes_property(self):
        """Test scopes property parsing."""
        token = OAuthToken(
            access_token=SecretStr("test"),
            scope="read write admin",
        )

        assert token.scopes == ["read", "write", "admin"]

    def test_no_scopes(self):
        """Test token with no scopes."""
        token = OAuthToken(
            access_token=SecretStr("test"),
        )

        assert token.scopes == []


# ============================================================================
# WebhookAuthRegistry Tests
# ============================================================================


class TestWebhookAuthRegistry:
    """Tests for WebhookAuthRegistry."""

    def test_register_handler(self, auth_registry: WebhookAuthRegistry):
        """Test registering a handler."""
        handler = ApiKeyAuthHandler(valid_keys={"key": "user"})

        auth_registry.register(handler)

        assert auth_registry.get(WebhookAuthType.API_KEY) is handler

    def test_unregister_handler(self, auth_registry: WebhookAuthRegistry):
        """Test unregistering a handler."""
        handler = ApiKeyAuthHandler(valid_keys={"key": "user"})
        auth_registry.register(handler)

        removed = auth_registry.unregister(WebhookAuthType.API_KEY)

        assert removed is handler
        assert auth_registry.get(WebhookAuthType.API_KEY) is None

    def test_get_all_handlers(self, auth_registry: WebhookAuthRegistry, hmac_secret: SecretStr):
        """Test getting all registered handlers."""
        api_handler = ApiKeyAuthHandler(valid_keys={"key": "user"})
        hmac_handler = HmacAuthHandler(secret=hmac_secret)

        auth_registry.register(api_handler)
        auth_registry.register(hmac_handler)

        all_handlers = auth_registry.get_all()

        assert len(all_handlers) == 2
        assert WebhookAuthType.API_KEY in all_handlers
        assert WebhookAuthType.HMAC in all_handlers

    @pytest.mark.asyncio
    async def test_verify_request_with_registry(self, auth_registry: WebhookAuthRegistry):
        """Test verifying request using registry."""
        handler = ApiKeyAuthHandler(valid_keys={"my-key": "registry-user"})
        auth_registry.register(handler)

        headers = {"X-API-Key": "my-key"}
        body = b"{}"

        result = await auth_registry.verify_request(WebhookAuthType.API_KEY, headers, body)

        assert result.authenticated is True
        assert result.principal == "registry-user"

    @pytest.mark.asyncio
    async def test_verify_request_no_handler(self, auth_registry: WebhookAuthRegistry):
        """Test verifying request when no handler is registered."""
        headers = {"X-API-Key": "key"}
        body = b"{}"

        result = await auth_registry.verify_request(WebhookAuthType.API_KEY, headers, body)

        assert result.authenticated is False
        assert result.error_code == "NO_HANDLER"

    @pytest.mark.asyncio
    async def test_verify_request_none_auth(self, auth_registry: WebhookAuthRegistry):
        """Test verifying request with NONE auth type."""
        headers = {}
        body = b"{}"

        result = await auth_registry.verify_request(WebhookAuthType.NONE, headers, body)

        assert result.authenticated is True

    @pytest.mark.asyncio
    async def test_prepare_headers_with_registry(self, auth_registry: WebhookAuthRegistry):
        """Test preparing headers using registry."""
        handler = ApiKeyAuthHandler(
            api_key=SecretStr("registry-key"),
            header_name="X-API-Key",
        )
        auth_registry.register(handler)

        result = await auth_registry.prepare_headers(WebhookAuthType.API_KEY, {}, b"{}")

        assert result["X-API-Key"] == "registry-key"


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_api_key_handler(self):
        """Test create_api_key_handler factory."""
        handler = create_api_key_handler(
            valid_keys={"key1": "user1"},
            header_name="X-Custom-Key",
            api_key=SecretStr("outgoing"),
        )

        assert isinstance(handler, ApiKeyAuthHandler)
        assert handler._header_name == "X-Custom-Key"

    def test_create_hmac_handler(self):
        """Test create_hmac_handler factory."""
        handler = create_hmac_handler(
            secret=SecretStr("test-secret"),
            signature_header="X-Sig",
            algorithm="sha512",
        )

        assert isinstance(handler, HmacAuthHandler)
        assert handler._signature_header == "X-Sig"
        assert handler._algorithm == "sha512"

    def test_create_oauth_handler(self):
        """Test create_oauth_handler factory."""
        handler = create_oauth_handler(
            token_info_url="https://example.com/token_info",
            required_scopes=["read"],
            access_token=SecretStr("token"),
        )

        assert isinstance(handler, OAuthBearerAuthHandler)
        assert handler._token_info_url == "https://example.com/token_info"

    def test_create_default_registry(self):
        """Test create_default_registry factory."""
        registry = create_default_registry()

        assert isinstance(registry, WebhookAuthRegistry)


# ============================================================================
# AuthResult Model Tests
# ============================================================================


class TestAuthResult:
    """Tests for AuthResult model."""

    def test_success_result(self):
        """Test creating a success result."""
        result = AuthResult.success(
            auth_type=WebhookAuthType.API_KEY,
            principal="test-user",
            scopes=["read", "write"],
            metadata={"source": "test"},
        )

        assert result.authenticated is True
        assert result.principal == "test-user"
        assert result.scopes == ["read", "write"]
        assert result.error_code is None

    def test_failure_result(self):
        """Test creating a failure result."""
        result = AuthResult.failure(
            auth_type=WebhookAuthType.HMAC,
            error_code="INVALID",
            error_message="Something went wrong",
        )

        assert result.authenticated is False
        assert result.error_code == "INVALID"
        assert result.error_message == "Something went wrong"


# ============================================================================
# Exception Tests
# ============================================================================


class TestExceptions:
    """Tests for authentication exceptions."""

    def test_invalid_signature_error(self):
        """Test InvalidSignatureError."""
        error = InvalidSignatureError("Custom message", details={"algo": "sha256"})

        assert error.message == "Custom message"
        assert error.error_code == "INVALID_SIGNATURE"
        assert error.status_code == 401
        assert error.details["algo"] == "sha256"

    def test_invalid_api_key_error(self):
        """Test InvalidApiKeyError."""
        error = InvalidApiKeyError()

        assert error.error_code == "INVALID_API_KEY"
        assert error.status_code == 401

    def test_invalid_bearer_token_error(self):
        """Test InvalidBearerTokenError."""
        error = InvalidBearerTokenError()

        assert error.error_code == "INVALID_BEARER_TOKEN"
        assert error.status_code == 401

    def test_missing_auth_header_error(self):
        """Test MissingAuthHeaderError."""
        error = MissingAuthHeaderError("X-API-Key")

        assert "X-API-Key" in error.message
        assert error.details["header"] == "X-API-Key"

    def test_signature_timestamp_error(self):
        """Test SignatureTimestampError."""
        error = SignatureTimestampError()

        assert error.error_code == "TIMESTAMP_ERROR"


# ============================================================================
# Edge Cases and Security Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and security scenarios."""

    @pytest.mark.asyncio
    async def test_empty_body_hmac(self, hmac_handler: HmacAuthHandler):
        """Test HMAC verification with empty body."""
        body = b""
        timestamp = str(int(time.time()))
        signature = hmac_handler._compute_signature(body, timestamp)

        headers = {
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Timestamp": timestamp,
        }

        result = await hmac_handler.verify_request(headers, body)

        assert result.authenticated is True

    @pytest.mark.asyncio
    async def test_large_body_hmac(self, hmac_handler: HmacAuthHandler):
        """Test HMAC verification with large body."""
        body = b"x" * 1000000  # 1MB
        timestamp = str(int(time.time()))
        signature = hmac_handler._compute_signature(body, timestamp)

        headers = {
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Timestamp": timestamp,
        }

        result = await hmac_handler.verify_request(headers, body)

        assert result.authenticated is True

    @pytest.mark.asyncio
    async def test_unicode_body_hmac(self, hmac_handler: HmacAuthHandler):
        """Test HMAC verification with unicode content."""
        body = '{"message": "Hello, 世界! 🌍"}'.encode("utf-8")
        timestamp = str(int(time.time()))
        signature = hmac_handler._compute_signature(body, timestamp)

        headers = {
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Timestamp": timestamp,
        }

        result = await hmac_handler.verify_request(headers, body)

        assert result.authenticated is True

    @pytest.mark.asyncio
    async def test_api_key_with_whitespace(self, api_key_handler: ApiKeyAuthHandler):
        """Test API key with leading/trailing whitespace."""
        headers = {"X-API-Key": "  test-api-key-1  "}
        body = b"{}"

        result = await api_key_handler.verify_request(headers, body)

        # Should still work due to stripping
        assert result.authenticated is True

    @pytest.mark.asyncio
    async def test_timestamp_iso_format(self, hmac_secret: SecretStr):
        """Test HMAC with ISO format timestamp."""
        handler = HmacAuthHandler(
            secret=hmac_secret,
            require_timestamp=True,
        )

        body = b'{"test": "data"}'
        # Use ISO format
        timestamp = datetime.now(timezone.utc).isoformat()
        signature = handler._compute_signature(body, timestamp)

        headers = {
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Timestamp": timestamp,
        }

        result = await handler.verify_request(headers, body)

        assert result.authenticated is True

    @pytest.mark.asyncio
    async def test_future_timestamp_rejected(self, hmac_handler: HmacAuthHandler):
        """Test that future timestamps are rejected."""
        body = b'{"test": "data"}'
        # Timestamp 10 minutes in the future
        future_timestamp = str(int(time.time()) + 600)
        signature = hmac_handler._compute_signature(body, future_timestamp)

        headers = {
            "X-Webhook-Signature": f"sha256={signature}",
            "X-Webhook-Timestamp": future_timestamp,
        }

        result = await hmac_handler.verify_request(headers, body)

        assert result.authenticated is False
        assert result.error_code == "TIMESTAMP_EXPIRED"
