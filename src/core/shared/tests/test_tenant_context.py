"""
Tests for Tenant Context Middleware
Constitutional Hash: cdd01ef066bc6cf2

Tests verify:
- TenantValidationError exception class
- TenantContextConfig from defaults and environment variables
- Tenant ID validation (format, dangerous characters, path traversal)
- Tenant ID sanitization
- TenantContextMiddleware behavior (missing/invalid/valid headers, exempt paths)
- FastAPI dependencies (get_tenant_id, get_optional_tenant_id)
- Cross-tenant access prevention (require_tenant_scope)
- Context variable handling (get_current_tenant_id)
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import FastAPI, HTTPException  # noqa: E402, I001
from fastapi.testclient import TestClient  # noqa: E402, I001
from starlette.requests import Request  # noqa: E402, I001

from src.core.shared.security.tenant_context import (  # noqa: E402, I001
    CONSTITUTIONAL_HASH,
    TENANT_ID_MAX_LENGTH,
    TENANT_ID_MIN_LENGTH,
    TENANT_ID_PATTERN,
    TenantContextConfig,
    TenantContextMiddleware,
    TenantValidationError,
    get_current_tenant_id,
    get_optional_tenant_id,
    get_tenant_id,
    require_tenant_scope,
    sanitize_tenant_id,
    validate_tenant_id,
)

# ============================================================================
# TenantValidationError Tests
# ============================================================================


class TestTenantValidationError:
    """Test TenantValidationError exception class."""

    def test_error_with_message(self):
        """Test error creation with message."""
        error = TenantValidationError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.tenant_id is None

    def test_error_with_tenant_id(self):
        """Test error creation with tenant ID."""
        error = TenantValidationError("Invalid format", tenant_id="bad-tenant")
        assert error.message == "Invalid format"
        assert error.tenant_id == "bad-tenant"

    def test_error_inherits_from_exception(self):
        """Test error inherits from Exception."""
        error = TenantValidationError("Test")
        assert isinstance(error, Exception)


# ============================================================================
# TenantContextConfig Tests
# ============================================================================


class TestTenantContextConfig:
    """Test TenantContextConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TenantContextConfig()
        assert config.header_name == "X-Tenant-ID"
        assert config.enabled is True
        assert config.required is True
        assert "/health" in config.exempt_paths
        assert "/metrics" in config.exempt_paths
        assert config.allow_query_param is False
        assert config.echo_header is True
        assert config.fail_open is False

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TenantContextConfig(
            header_name="X-Custom-Tenant",
            enabled=False,
            required=False,
            exempt_paths=["/custom-path"],
            allow_query_param=True,
            echo_header=False,
            fail_open=True,
        )
        assert config.header_name == "X-Custom-Tenant"
        assert config.enabled is False
        assert config.required is False
        assert config.exempt_paths == ["/custom-path"]
        assert config.allow_query_param is True
        assert config.echo_header is False
        assert config.fail_open is True

    def test_from_env_defaults(self, monkeypatch):
        """Test from_env with no environment variables set."""
        # Clear relevant env vars
        env_vars_to_clear = [
            "TENANT_HEADER_NAME",
            "TENANT_CONTEXT_ENABLED",
            "TENANT_CONTEXT_REQUIRED",
            "TENANT_EXEMPT_PATHS",
            "TENANT_ALLOW_QUERY_PARAM",
            "TENANT_ECHO_HEADER",
            "TENANT_FAIL_OPEN",
        ]
        for key in env_vars_to_clear:
            monkeypatch.delenv(key, raising=False)

        config = TenantContextConfig.from_env()
        assert config.header_name == "X-Tenant-ID"
        assert config.enabled is True
        assert config.required is True
        assert "/health" in config.exempt_paths

    def test_from_env_custom(self, monkeypatch):
        """Test from_env with custom environment variables."""
        monkeypatch.setenv("TENANT_HEADER_NAME", "X-Custom-Tenant")
        monkeypatch.setenv("TENANT_CONTEXT_ENABLED", "false")
        monkeypatch.setenv("TENANT_CONTEXT_REQUIRED", "false")
        monkeypatch.setenv("TENANT_EXEMPT_PATHS", "/api/public,/api/status")
        monkeypatch.setenv("TENANT_ALLOW_QUERY_PARAM", "true")
        monkeypatch.setenv("TENANT_ECHO_HEADER", "false")
        monkeypatch.setenv("TENANT_FAIL_OPEN", "true")

        config = TenantContextConfig.from_env()
        assert config.header_name == "X-Custom-Tenant"
        assert config.enabled is False
        assert config.required is False
        assert "/api/public" in config.exempt_paths
        assert "/api/status" in config.exempt_paths
        assert config.allow_query_param is True
        assert config.echo_header is False
        assert config.fail_open is True

    def test_from_env_case_insensitive_booleans(self, monkeypatch):
        """Test from_env handles case-insensitive boolean values."""
        monkeypatch.setenv("TENANT_CONTEXT_ENABLED", "TRUE")
        monkeypatch.setenv("TENANT_FAIL_OPEN", "True")
        monkeypatch.setenv("TENANT_EXEMPT_PATHS", "")

        config = TenantContextConfig.from_env()
        assert config.enabled is True
        assert config.fail_open is True


# ============================================================================
# validate_tenant_id Tests
# ============================================================================


class TestValidateTenantId:
    """Test validate_tenant_id function."""

    def test_valid_simple_tenant_id(self):
        """Test validation of simple tenant ID."""
        assert validate_tenant_id("tenant123") is True

    def test_valid_tenant_id_with_hyphens(self):
        """Test validation of tenant ID with hyphens."""
        assert validate_tenant_id("tenant-123") is True

    def test_valid_tenant_id_with_underscores(self):
        """Test validation of tenant ID with underscores."""
        assert validate_tenant_id("tenant_123") is True

    def test_valid_tenant_id_mixed(self):
        """Test validation of tenant ID with mixed characters."""
        assert validate_tenant_id("my-tenant_123") is True

    def test_valid_single_character(self):
        """Test validation of single character tenant ID."""
        assert validate_tenant_id("a") is True

    def test_valid_two_characters(self):
        """Test validation of two character tenant ID."""
        assert validate_tenant_id("ab") is True

    def test_valid_max_length(self):
        """Test validation of max length tenant ID."""
        tenant_id = "a" * TENANT_ID_MAX_LENGTH
        assert validate_tenant_id(tenant_id) is True

    def test_invalid_empty_string(self):
        """Test validation rejects empty string."""
        with pytest.raises(TenantValidationError, match="cannot be empty"):
            validate_tenant_id("")

    def test_invalid_too_long(self):
        """Test validation rejects tenant ID exceeding max length."""
        tenant_id = "a" * (TENANT_ID_MAX_LENGTH + 1)
        with pytest.raises(TenantValidationError, match="exceeds maximum length"):
            validate_tenant_id(tenant_id)

    def test_invalid_starts_with_hyphen(self):
        """Test validation rejects tenant ID starting with hyphen."""
        with pytest.raises(TenantValidationError, match="start and end with alphanumeric"):
            validate_tenant_id("-tenant123")

    def test_invalid_ends_with_hyphen(self):
        """Test validation rejects tenant ID ending with hyphen."""
        with pytest.raises(TenantValidationError, match="start and end with alphanumeric"):
            validate_tenant_id("tenant123-")

    def test_invalid_starts_with_underscore(self):
        """Test validation rejects tenant ID starting with underscore."""
        with pytest.raises(TenantValidationError, match="start and end with alphanumeric"):
            validate_tenant_id("_tenant123")

    def test_invalid_dangerous_chars_angle_brackets(self):
        """Test validation rejects tenant ID with angle brackets."""
        with pytest.raises(TenantValidationError, match="invalid characters"):
            validate_tenant_id("tenant<script>")

    def test_invalid_dangerous_chars_quotes(self):
        """Test validation rejects tenant ID with quotes."""
        with pytest.raises(TenantValidationError, match="invalid characters"):
            validate_tenant_id('tenant"test')

    def test_invalid_dangerous_chars_semicolon(self):
        """Test validation rejects tenant ID with semicolon."""
        with pytest.raises(TenantValidationError, match="invalid characters"):
            validate_tenant_id("tenant;drop")

    def test_invalid_dangerous_chars_backtick(self):
        """Test validation rejects tenant ID with backtick."""
        with pytest.raises(TenantValidationError, match="invalid characters"):
            validate_tenant_id("tenant`cmd`")

    def test_invalid_dangerous_chars_pipe(self):
        """Test validation rejects tenant ID with pipe."""
        with pytest.raises(TenantValidationError, match="invalid characters"):
            validate_tenant_id("tenant|cmd")

    def test_invalid_dangerous_chars_dollar(self):
        """Test validation rejects tenant ID with dollar sign."""
        with pytest.raises(TenantValidationError, match="invalid characters"):
            validate_tenant_id("tenant$var")

    def test_invalid_path_traversal_dotdot(self):
        """Test validation rejects path traversal attempt."""
        with pytest.raises(TenantValidationError, match="invalid path characters"):
            validate_tenant_id("tenant/../etc")

    def test_invalid_path_traversal_forward_slash(self):
        """Test validation rejects forward slash."""
        with pytest.raises(TenantValidationError, match="invalid path characters"):
            validate_tenant_id("tenant/etc/passwd")

    def test_invalid_path_traversal_backslash(self):
        """Test validation rejects backslash."""
        # Note: backslash is caught by DANGEROUS_CHARS first, not path traversal check
        with pytest.raises(TenantValidationError, match="invalid characters"):
            validate_tenant_id("tenant\\windows\\system32")


# ============================================================================
# sanitize_tenant_id Tests
# ============================================================================


class TestSanitizeTenantId:
    """Test sanitize_tenant_id function."""

    def test_strips_leading_whitespace(self):
        """Test sanitize strips leading whitespace."""
        assert sanitize_tenant_id("  tenant123") == "tenant123"

    def test_strips_trailing_whitespace(self):
        """Test sanitize strips trailing whitespace."""
        assert sanitize_tenant_id("tenant123  ") == "tenant123"

    def test_strips_both_sides_whitespace(self):
        """Test sanitize strips whitespace from both sides."""
        assert sanitize_tenant_id("  tenant123  ") == "tenant123"

    def test_preserves_clean_input(self):
        """Test sanitize preserves clean input."""
        assert sanitize_tenant_id("tenant123") == "tenant123"


# ============================================================================
# TenantContextMiddleware Tests
# ============================================================================


class TestTenantContextMiddleware:
    """Test TenantContextMiddleware class."""

    def create_test_app(self, config: TenantContextConfig = None) -> FastAPI:
        """Create a test FastAPI app with middleware."""
        app = FastAPI()
        if config is None:
            config = TenantContextConfig()
        app.add_middleware(TenantContextMiddleware, config=config)

        @app.get("/api/test")
        async def test_endpoint(request: Request):
            tenant_id = getattr(request.state, "tenant_id", None)
            return {"tenant_id": tenant_id}

        @app.get("/health")
        async def health_endpoint():
            return {"status": "healthy"}

        @app.get("/metrics")
        async def metrics_endpoint():
            return {"metrics": []}

        return app

    def test_middleware_extracts_valid_tenant_id(self):
        """Test middleware extracts valid X-Tenant-ID header."""
        app = self.create_test_app()
        client = TestClient(app)

        response = client.get("/api/test", headers={"X-Tenant-ID": "tenant123"})
        assert response.status_code == 200
        assert response.json()["tenant_id"] == "tenant123"

    def test_middleware_echoes_tenant_id_in_response(self):
        """Test middleware echoes tenant ID in response header."""
        config = TenantContextConfig(echo_header=True)
        app = self.create_test_app(config=config)
        client = TestClient(app)

        response = client.get("/api/test", headers={"X-Tenant-ID": "tenant123"})
        assert response.status_code == 200
        assert response.headers.get("X-Tenant-ID") == "tenant123"

    def test_middleware_rejects_missing_header(self):
        """Test middleware rejects request without X-Tenant-ID header."""
        app = self.create_test_app()
        client = TestClient(app)

        response = client.get("/api/test")
        assert response.status_code == 400
        assert response.json()["code"] == "MISSING_TENANT_ID"

    def test_middleware_rejects_invalid_tenant_id(self):
        """Test middleware rejects invalid tenant ID."""
        app = self.create_test_app()
        client = TestClient(app)

        response = client.get("/api/test", headers={"X-Tenant-ID": "tenant<script>"})
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_TENANT_ID"

    def test_middleware_allows_exempt_paths(self):
        """Test middleware allows requests to exempt paths."""
        app = self.create_test_app()
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_middleware_allows_metrics_exempt(self):
        """Test middleware allows /metrics endpoint without tenant ID."""
        app = self.create_test_app()
        client = TestClient(app)

        response = client.get("/metrics")
        assert response.status_code == 200

    def test_middleware_disabled(self):
        """Test middleware is disabled when enabled=False."""
        config = TenantContextConfig(enabled=False)
        app = self.create_test_app(config=config)
        client = TestClient(app)

        response = client.get("/api/test")
        assert response.status_code == 200
        # No tenant_id should be set
        assert response.json()["tenant_id"] is None

    def test_middleware_fail_open_mode(self):
        """Test middleware allows requests without tenant ID in fail-open mode."""
        config = TenantContextConfig(fail_open=True)
        app = self.create_test_app(config=config)
        client = TestClient(app)

        response = client.get("/api/test")
        assert response.status_code == 200

    def test_middleware_not_required_mode(self):
        """Test middleware allows requests without tenant ID when not required."""
        config = TenantContextConfig(required=False)
        app = self.create_test_app(config=config)
        client = TestClient(app)

        response = client.get("/api/test")
        assert response.status_code == 200

    def test_middleware_constitutional_hash_in_error_response(self):
        """Test middleware includes constitutional hash in error responses."""
        app = self.create_test_app()
        client = TestClient(app)

        response = client.get("/api/test")
        assert response.status_code == 400
        assert response.json()["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_middleware_custom_header_name(self):
        """Test middleware uses custom header name."""
        config = TenantContextConfig(header_name="X-Custom-Tenant")
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware, config=config)

        @app.get("/api/test")
        async def test_endpoint(request: Request):
            tenant_id = getattr(request.state, "tenant_id", None)
            return {"tenant_id": tenant_id}

        client = TestClient(app)
        response = client.get("/api/test", headers={"X-Custom-Tenant": "tenant123"})
        assert response.status_code == 200
        assert response.json()["tenant_id"] == "tenant123"

    def test_middleware_query_param_fallback(self):
        """Test middleware extracts tenant ID from query param when enabled."""
        config = TenantContextConfig(allow_query_param=True)
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware, config=config)

        @app.get("/api/test")
        async def test_endpoint(request: Request):
            tenant_id = getattr(request.state, "tenant_id", None)
            return {"tenant_id": tenant_id}

        client = TestClient(app)
        response = client.get("/api/test?tenant_id=tenant123")
        assert response.status_code == 200
        assert response.json()["tenant_id"] == "tenant123"

    def test_middleware_header_takes_precedence_over_query_param(self):
        """Test header takes precedence over query parameter."""
        config = TenantContextConfig(allow_query_param=True)
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware, config=config)

        @app.get("/api/test")
        async def test_endpoint(request: Request):
            tenant_id = getattr(request.state, "tenant_id", None)
            return {"tenant_id": tenant_id}

        client = TestClient(app)
        response = client.get(
            "/api/test?tenant_id=query-tenant",
            headers={"X-Tenant-ID": "header-tenant"},
        )
        assert response.status_code == 200
        assert response.json()["tenant_id"] == "header-tenant"


# ============================================================================
# get_tenant_id Dependency Tests
# ============================================================================


class TestGetTenantIdDependency:
    """Test get_tenant_id FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_get_tenant_id_from_request_state(self):
        """Test get_tenant_id extracts from request state."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.tenant_id = "tenant123"

        result = await get_tenant_id(request, x_tenant_id=None)
        assert result == "tenant123"

    @pytest.mark.asyncio
    async def test_get_tenant_id_from_header(self):
        """Test get_tenant_id extracts from header."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        # No tenant_id in state
        del request.state.tenant_id

        result = await get_tenant_id(request, x_tenant_id="tenant456")
        assert result == "tenant456"

    @pytest.mark.asyncio
    async def test_get_tenant_id_missing_raises_error(self):
        """Test get_tenant_id raises HTTPException when missing."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.tenant_id = None

        with pytest.raises(HTTPException) as exc_info:
            await get_tenant_id(request, x_tenant_id=None)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "MISSING_TENANT_ID"

    @pytest.mark.asyncio
    async def test_get_tenant_id_invalid_raises_error(self):
        """Test get_tenant_id raises HTTPException for invalid ID."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.tenant_id = None

        with pytest.raises(HTTPException) as exc_info:
            await get_tenant_id(request, x_tenant_id="invalid<>tenant")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "INVALID_TENANT_ID"


# ============================================================================
# get_optional_tenant_id Dependency Tests
# ============================================================================


class TestGetOptionalTenantIdDependency:
    """Test get_optional_tenant_id FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_get_optional_tenant_id_from_request_state(self):
        """Test get_optional_tenant_id extracts from request state."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.tenant_id = "tenant123"

        result = await get_optional_tenant_id(request, x_tenant_id=None)
        assert result == "tenant123"

    @pytest.mark.asyncio
    async def test_get_optional_tenant_id_from_header(self):
        """Test get_optional_tenant_id extracts from header."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        del request.state.tenant_id

        result = await get_optional_tenant_id(request, x_tenant_id="tenant456")
        assert result == "tenant456"

    @pytest.mark.asyncio
    async def test_get_optional_tenant_id_returns_none_when_missing(self):
        """Test get_optional_tenant_id returns None when missing."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.tenant_id = None

        result = await get_optional_tenant_id(request, x_tenant_id=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_tenant_id_invalid_raises_error(self):
        """Test get_optional_tenant_id raises HTTPException for invalid ID."""
        request = MagicMock(spec=Request)
        request.state = MagicMock()
        request.state.tenant_id = None

        with pytest.raises(HTTPException) as exc_info:
            await get_optional_tenant_id(request, x_tenant_id="invalid<>tenant")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail["code"] == "INVALID_TENANT_ID"


# ============================================================================
# require_tenant_scope Tests
# ============================================================================


class TestRequireTenantScope:
    """Test require_tenant_scope function."""

    def test_same_tenant_id_passes(self):
        """Test require_tenant_scope passes for matching tenant IDs."""
        # Should not raise
        require_tenant_scope("tenant-a", "tenant-a")

    def test_different_tenant_id_raises_error(self):
        """Test require_tenant_scope raises HTTPException for different tenants."""
        with pytest.raises(HTTPException) as exc_info:
            require_tenant_scope("tenant-a", "tenant-b")

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail["code"] == "CROSS_TENANT_ACCESS_DENIED"

    def test_cross_tenant_access_logging(self):
        """Test require_tenant_scope logs cross-tenant access attempts."""
        with patch("shared.security.tenant_context.logger") as mock_logger:
            with pytest.raises(HTTPException):
                require_tenant_scope("tenant-a", "tenant-b")

            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "Cross-tenant access attempt" in call_args
            assert "tenant-a" in call_args
            assert "tenant-b" in call_args


# ============================================================================
# get_current_tenant_id Tests
# ============================================================================


class TestGetCurrentTenantId:
    """Test get_current_tenant_id function."""

    def test_returns_none_when_not_set(self):
        """Test get_current_tenant_id returns None when not in context."""
        result = get_current_tenant_id()
        assert result is None


# ============================================================================
# Constitutional Compliance Tests
# ============================================================================


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_present(self):
        """Constitutional hash should be defined."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_tenant_id_constants_defined(self):
        """Tenant ID constants should be defined."""
        assert TENANT_ID_MAX_LENGTH == 64
        assert TENANT_ID_MIN_LENGTH == 1
        assert TENANT_ID_PATTERN is not None


# ============================================================================
# Integration Tests
# ============================================================================


class TestMiddlewareIntegration:
    """Integration tests for tenant context middleware."""

    def test_full_request_flow_with_valid_tenant(self):
        """Test full request flow with valid tenant ID."""
        app = FastAPI()
        config = TenantContextConfig()
        app.add_middleware(TenantContextMiddleware, config=config)

        @app.get("/api/resources")
        async def get_resources(request: Request):
            tenant_id = getattr(request.state, "tenant_id", None)
            return {"resources": [], "tenant_id": tenant_id}

        client = TestClient(app)
        response = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": "enterprise-tenant-1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "enterprise-tenant-1"
        assert response.headers.get("X-Tenant-ID") == "enterprise-tenant-1"

    def test_request_rejection_for_injection_attempt(self):
        """Test request is rejected for injection attempts."""
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware)

        @app.get("/api/data")
        async def get_data():
            return {"data": []}

        client = TestClient(app)

        # SQL injection attempt
        response = client.get(
            "/api/data",
            headers={"X-Tenant-ID": "tenant'; DROP TABLE users;--"},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_TENANT_ID"

    def test_request_rejection_for_path_traversal(self):
        """Test request is rejected for path traversal attempts."""
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware)

        @app.get("/api/files")
        async def get_files():
            return {"files": []}

        client = TestClient(app)

        # Path traversal attempt
        response = client.get(
            "/api/files",
            headers={"X-Tenant-ID": "../../../etc/passwd"},
        )
        assert response.status_code == 400
        assert response.json()["code"] == "INVALID_TENANT_ID"

    def test_multiple_exempt_paths(self):
        """Test multiple exempt paths work correctly."""
        config = TenantContextConfig(exempt_paths=["/health", "/ready", "/metrics", "/docs"])
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware, config=config)

        @app.get("/health")
        async def health():
            return {"status": "ok"}

        @app.get("/ready")
        async def ready():
            return {"ready": True}

        @app.get("/docs")
        async def docs():
            return {"docs": "available"}

        client = TestClient(app)

        # All exempt paths should work without tenant ID
        for path in ["/health", "/ready", "/docs"]:
            response = client.get(path)
            assert response.status_code == 200, f"Failed for path: {path}"


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_whitespace_only_tenant_id(self):
        """Test whitespace-only tenant ID is rejected."""
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware)

        @app.get("/api/test")
        async def test_endpoint():
            return {"ok": True}

        client = TestClient(app)
        response = client.get("/api/test", headers={"X-Tenant-ID": "   "})
        assert response.status_code == 400

    def test_tenant_id_with_leading_trailing_spaces(self):
        """Test tenant ID with spaces is sanitized."""
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware)

        @app.get("/api/test")
        async def test_endpoint(request: Request):
            return {"tenant_id": getattr(request.state, "tenant_id", None)}

        client = TestClient(app)
        response = client.get("/api/test", headers={"X-Tenant-ID": "  valid-tenant  "})
        assert response.status_code == 200
        assert response.json()["tenant_id"] == "valid-tenant"

    def test_exempt_path_prefix_matching(self):
        """Test exempt path matches prefixes."""
        config = TenantContextConfig(exempt_paths=["/health"])
        app = FastAPI()
        app.add_middleware(TenantContextMiddleware, config=config)

        @app.get("/health/detailed")
        async def detailed_health():
            return {"detailed": True}

        client = TestClient(app)
        response = client.get("/health/detailed")
        assert response.status_code == 200

    def test_unicode_tenant_id_rejected(self):
        """Test tenant ID with unicode characters is rejected."""
        # Test validation directly since httpx cannot encode unicode headers
        # Unicode characters (like zero-width space) should fail the pattern check
        with pytest.raises(TenantValidationError):
            validate_tenant_id("tenant\u200b123")

        # Also test that non-ASCII characters fail validation
        with pytest.raises(TenantValidationError):
            validate_tenant_id("tëñant123")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
