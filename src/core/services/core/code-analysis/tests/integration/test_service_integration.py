"""
ACGS Code Analysis Engine - Service Integration Tests
Integration tests for service endpoints and constitutional compliance.

Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from code_analysis_service.app.utils.constitutional import CONSTITUTIONAL_HASH
from code_analysis_service.config.settings import get_settings


class TestServiceConfiguration:
    """Integration tests for service configuration."""

    @pytest.mark.integration
    def test_settings_integration(self) -> None:
        """Test settings can be loaded and accessed."""
        settings = get_settings()

        assert settings.service_name == "acgs-code-analysis-engine"
        assert settings.port == 8007
        assert settings.constitutional_hash == CONSTITUTIONAL_HASH

    @pytest.mark.integration
    def test_database_url_valid_format(self) -> None:
        """Test database URL is valid for asyncpg."""
        settings = get_settings()
        db_url = settings.database_url

        assert db_url.startswith("postgresql+asyncpg://")
        # Should contain host and port
        assert ":" in db_url
        assert "/" in db_url

    @pytest.mark.integration
    def test_redis_url_valid_format(self) -> None:
        """Test Redis URL is valid format."""
        settings = get_settings()
        redis_url = settings.redis_url

        assert redis_url.startswith("redis://")


class TestConstitutionalIntegration:
    """Integration tests for constitutional compliance across modules."""

    @pytest.mark.integration
    @pytest.mark.constitutional
    def test_constitutional_hash_consistency(self) -> None:
        """Test constitutional hash is consistent across all modules."""
        from code_analysis_service.app.utils.constitutional import (
            CONSTITUTIONAL_HASH as UTILS_HASH,
        )
        from code_analysis_service.config.settings import (
            CONSTITUTIONAL_HASH as SETTINGS_HASH,
        )

        assert SETTINGS_HASH == UTILS_HASH
        assert SETTINGS_HASH == "cdd01ef066bc6cf2"

    @pytest.mark.integration
    @pytest.mark.constitutional
    def test_settings_has_constitutional_hash(self) -> None:
        """Test settings instance has correct constitutional hash."""
        settings = get_settings()

        assert hasattr(settings, "constitutional_hash")
        assert settings.constitutional_hash == CONSTITUTIONAL_HASH

    @pytest.mark.integration
    @pytest.mark.constitutional
    def test_to_dict_includes_hash(self) -> None:
        """Test settings to_dict includes constitutional hash."""
        settings = get_settings()
        data = settings.to_dict()

        assert "constitutional_hash" in data
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH


class TestServiceURLConfiguration:
    """Integration tests for ACGS service URL configuration."""

    @pytest.mark.integration
    def test_auth_service_url(self) -> None:
        """Test auth service URL is configured."""
        settings = get_settings()

        assert hasattr(settings, "auth_service_url")
        assert "localhost:8016" in settings.auth_service_url or "8016" in settings.auth_service_url

    @pytest.mark.integration
    def test_context_service_url(self) -> None:
        """Test context service URL is configured."""
        settings = get_settings()

        assert hasattr(settings, "context_service_url")
        assert (
            "localhost:8012" in settings.context_service_url
            or "8012" in settings.context_service_url
        )

    @pytest.mark.integration
    def test_service_registry_url(self) -> None:
        """Test service registry URL is configured."""
        settings = get_settings()

        assert hasattr(settings, "service_registry_url")
        assert (
            "localhost:8010" in settings.service_registry_url
            or "8010" in settings.service_registry_url
        )


class TestACGSStandardPorts:
    """Integration tests for ACGS standard port configuration."""

    @pytest.mark.integration
    def test_api_port_default(self) -> None:
        """Test API runs on port 8007 by default."""
        settings = get_settings()
        assert settings.port == 8007

    @pytest.mark.integration
    def test_postgresql_acgs_standard_port(self) -> None:
        """Test PostgreSQL uses ACGS standard port 5439."""
        settings = get_settings()
        assert settings.postgresql_port == 5439

    @pytest.mark.integration
    def test_redis_acgs_standard_port(self) -> None:
        """Test Redis uses ACGS standard port 6389."""
        settings = get_settings()
        assert settings.redis_port == 6389
