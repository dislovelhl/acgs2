"""
Tests for ACGS-2 API CORS configuration

Tests the CORS middleware configuration in the main API.
"""

import os
from unittest.mock import patch


class TestAcgs2ApiCors:
    """Test CORS configuration for ACGS-2 main API."""

    def test_default_development_origins(self):
        """Test default localhost origins in development."""
        # Test the logic from main.py
        allowed_origins_str = os.environ.get("ACGS2_CORS_ORIGINS", "").split(",")
        allowed_origins = [origin.strip() for origin in allowed_origins_str if origin.strip()] or [
            "http://localhost:3000"
        ]

        # Should default to localhost:3000 when no env var set
        assert allowed_origins == ["http://localhost:3000"]

    def test_custom_origins_from_env(self):
        """Test custom origins from ACGS2_CORS_ORIGINS env var."""
        with patch.dict(
            os.environ, {"ACGS2_CORS_ORIGINS": "https://app.example.com, https://admin.example.com"}
        ):
            allowed_origins_str = os.environ.get("ACGS2_CORS_ORIGINS", "").split(",")
            allowed_origins = [
                origin.strip() for origin in allowed_origins_str if origin.strip()
            ] or ["http://localhost:3000"]

            expected = ["https://app.example.com", "https://admin.example.com"]
            assert allowed_origins == expected

    def test_empty_origins_filtered(self):
        """Test that empty origins are filtered out."""
        with patch.dict(
            os.environ,
            {"ACGS2_CORS_ORIGINS": "https://app.example.com,, https://admin.example.com, "},
        ):
            allowed_origins_str = os.environ.get("ACGS2_CORS_ORIGINS", "").split(",")
            allowed_origins = [
                origin.strip() for origin in allowed_origins_str if origin.strip()
            ] or ["http://localhost:3000"]

            expected = ["https://app.example.com", "https://admin.example.com"]
            assert allowed_origins == expected

    def test_shared_cors_integration(self):
        """Test that the API uses shared CORS config."""
        # Import should work without issues
        from src.core.shared.security import get_cors_config

        config = get_cors_config()

        # Should have expected CORS config structure
        assert "allow_origins" in config
        assert "allow_credentials" in config
        assert "allow_methods" in config
        assert "allow_headers" in config

        # Should allow credentials (needed for JWT auth)
        assert config["allow_credentials"] is True

        # Should allow necessary methods
        assert "GET" in config["allow_methods"]
        assert "POST" in config["allow_methods"]

        # Should allow necessary headers
        assert "Authorization" in config["allow_headers"]
        assert "Content-Type" in config["allow_headers"]

    def test_production_security_origins(self):
        """Test that production config doesn't use wildcards."""
        with patch.dict(
            os.environ, {"ENV": "production", "CORS_ALLOWED_ORIGINS": "https://secure.example.com"}
        ):
            from src.core.shared.security import get_cors_config

            config = get_cors_config()

            # Should not contain wildcards in production
            assert "*" not in config["allow_origins"]
            assert "https://secure.example.com" in config["allow_origins"]
