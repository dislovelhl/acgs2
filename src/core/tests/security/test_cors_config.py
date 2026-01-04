"""
Tests for Secure CORS Configuration
Constitutional Hash: cdd01ef066bc6cf2

Tests verify:
- Environment detection
- Origin validation
- Production security enforcement
- Configuration from environment
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.core.shared.security.cors_config import (
    CONSTITUTIONAL_HASH,
    DEFAULT_ORIGINS,
    CORSConfig,
    CORSEnvironment,
    detect_environment,
    get_cors_config,
    get_origins_from_env,
    validate_origin,
)


class TestCORSConfig:
    """Test CORSConfig class."""

    def test_valid_development_config(self):
        """Valid development configuration should work."""
        config = CORSConfig(
            allow_origins=["http://localhost:3000"],
            environment=CORSEnvironment.DEVELOPMENT,
        )
        assert config.allow_origins == ["http://localhost:3000"]
        assert config.allow_credentials is True

    def test_wildcard_with_credentials_blocked_in_production(self):
        """Wildcard + credentials must be blocked in production."""
        with pytest.raises(ValueError) as exc_info:
            CORSConfig(
                allow_origins=["*"],
                allow_credentials=True,
                environment=CORSEnvironment.PRODUCTION,
            )
        assert "SECURITY ERROR" in str(exc_info.value)
        assert "critical security vulnerability" in str(exc_info.value).lower()

    def test_wildcard_blocked_in_production(self):
        """Wildcard origins not allowed in production."""
        with pytest.raises(ValueError) as exc_info:
            CORSConfig(
                allow_origins=["*"],
                allow_credentials=False,
                environment=CORSEnvironment.PRODUCTION,
            )
        assert "Wildcard origins not allowed in production" in str(exc_info.value)

    def test_wildcard_warning_in_development(self, caplog):
        """Wildcard + credentials should warn in development."""
        import logging

        caplog.set_level(logging.WARNING)

        config = CORSConfig(
            allow_origins=["*"],
            allow_credentials=True,
            environment=CORSEnvironment.DEVELOPMENT,
        )

        # Should succeed but log warning
        assert config.allow_origins == ["*"]

    def test_invalid_origin_format(self):
        """Invalid origin format should be rejected."""
        with pytest.raises(ValueError) as exc_info:
            CORSConfig(
                allow_origins=["not-a-valid-url"],
                environment=CORSEnvironment.DEVELOPMENT,
            )
        assert "Invalid origin format" in str(exc_info.value)

    def test_to_middleware_kwargs(self):
        """Test conversion to middleware kwargs."""
        config = CORSConfig(
            allow_origins=["http://localhost:3000"],
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            max_age=300,
            environment=CORSEnvironment.DEVELOPMENT,
        )

        kwargs = config.to_middleware_kwargs()

        assert kwargs["allow_origins"] == ["http://localhost:3000"]
        assert kwargs["allow_credentials"] is True
        assert kwargs["allow_methods"] == ["GET", "POST"]
        assert kwargs["max_age"] == 300


class TestEnvironmentDetection:
    """Test environment detection."""

    def test_detect_development_default(self, monkeypatch):
        """Default should be development."""
        monkeypatch.delenv("CORS_ENVIRONMENT", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)
        monkeypatch.delenv("ENV", raising=False)

        env = detect_environment()
        assert env == CORSEnvironment.DEVELOPMENT

    def test_detect_from_cors_environment(self, monkeypatch):
        """Should detect from CORS_ENVIRONMENT."""
        monkeypatch.setenv("CORS_ENVIRONMENT", "production")

        env = detect_environment()
        assert env == CORSEnvironment.PRODUCTION

    def test_detect_from_environment(self, monkeypatch):
        """Should detect from ENVIRONMENT variable."""
        monkeypatch.delenv("CORS_ENVIRONMENT", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "staging")

        env = detect_environment()
        assert env == CORSEnvironment.STAGING

    def test_detect_aliases(self, monkeypatch):
        """Test environment aliases."""
        test_cases = [
            ("dev", CORSEnvironment.DEVELOPMENT),
            ("prod", CORSEnvironment.PRODUCTION),
            ("stage", CORSEnvironment.STAGING),
            ("testing", CORSEnvironment.TEST),
        ]

        for alias, expected in test_cases:
            monkeypatch.setenv("ENV", alias)
            assert detect_environment() == expected


class TestGetOriginsFromEnv:
    """Test origins from environment variable."""

    def test_no_env_returns_none(self, monkeypatch):
        """No env variable should return None."""
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)
        assert get_origins_from_env() is None

    def test_parse_single_origin(self, monkeypatch):
        """Parse single origin."""
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.com")
        origins = get_origins_from_env()
        assert origins == ["https://example.com"]

    def test_parse_multiple_origins(self, monkeypatch):
        """Parse comma-separated origins."""
        monkeypatch.setenv(
            "CORS_ALLOWED_ORIGINS",
            "https://app1.example.com, https://app2.example.com, https://app3.example.com",
        )
        origins = get_origins_from_env()
        assert origins == [
            "https://app1.example.com",
            "https://app2.example.com",
            "https://app3.example.com",
        ]


class TestGetCorsConfig:
    """Test get_cors_config function."""

    def test_development_config(self, monkeypatch):
        """Test development configuration."""
        monkeypatch.setenv("ENV", "development")
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

        config = get_cors_config()

        assert "http://localhost:3000" in config["allow_origins"]
        assert config["allow_credentials"] is True

    def test_production_config(self, monkeypatch):
        """Test production configuration."""
        monkeypatch.setenv("ENV", "production")
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

        config = get_cors_config()

        assert "*" not in config["allow_origins"]
        # Should have production default origins
        for origin in config["allow_origins"]:
            assert origin.startswith("https://")

    def test_additional_origins(self, monkeypatch):
        """Test adding additional origins."""
        monkeypatch.setenv("ENV", "development")
        monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

        config = get_cors_config(additional_origins=["https://custom.example.com"])

        assert "https://custom.example.com" in config["allow_origins"]

    def test_env_origins_override(self, monkeypatch):
        """Env origins should take precedence."""
        monkeypatch.setenv("ENV", "development")
        monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://override.example.com")

        config = get_cors_config()

        # Should use env origins, not defaults
        assert "https://override.example.com" in config["allow_origins"]


class TestValidateOrigin:
    """Test origin validation."""

    def test_validate_allowed_origin(self):
        """Test validating allowed origins."""
        allowed = ["https://app.example.com", "https://api.example.com"]

        assert validate_origin("https://app.example.com", allowed) is True
        assert validate_origin("https://api.example.com", allowed) is True
        assert validate_origin("https://other.example.com", allowed) is False

    def test_wildcard_allows_all(self):
        """Wildcard should allow all origins."""
        allowed = ["*"]

        assert validate_origin("https://anything.example.com", allowed) is True
        assert validate_origin("http://localhost:3000", allowed) is True


class TestDefaultOrigins:
    """Test default origins by environment."""

    def test_development_defaults(self):
        """Development defaults include localhost."""
        origins = DEFAULT_ORIGINS[CORSEnvironment.DEVELOPMENT]

        assert "http://localhost:3000" in origins
        assert "http://localhost:8080" in origins

    def test_production_defaults_are_https(self):
        """Production defaults should all be HTTPS."""
        origins = DEFAULT_ORIGINS[CORSEnvironment.PRODUCTION]

        for origin in origins:
            assert origin.startswith("https://"), f"Production origin not HTTPS: {origin}"


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_present(self):
        """Constitutional hash should be exported."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
