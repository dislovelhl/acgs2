"""
ACGS Code Analysis Engine - Settings Tests
Unit tests for settings configuration.

Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from code_analysis_service.config.settings import (
    CONSTITUTIONAL_HASH,
    Settings,
    get_settings,
)


class TestSettings:
    """Tests for Settings class."""

    @pytest.fixture
    def settings(self) -> Settings:
        """Create settings instance for tests."""
        return Settings()

    def test_service_name(self, settings: Settings) -> None:
        """Test default service name."""
        assert settings.service_name == "acgs-code-analysis-engine"

    def test_service_version(self, settings: Settings) -> None:
        """Test default service version."""
        assert settings.service_version == "1.0.0"

    def test_default_port(self, settings: Settings) -> None:
        """Test default API port."""
        assert settings.port == 8007

    def test_default_postgresql_port(self, settings: Settings) -> None:
        """Test default PostgreSQL port (ACGS standard)."""
        assert settings.postgresql_port == 5439

    def test_default_redis_port(self, settings: Settings) -> None:
        """Test default Redis port (ACGS standard)."""
        assert settings.redis_port == 6389

    @pytest.mark.constitutional
    def test_constitutional_hash(self, settings: Settings) -> None:
        """Test constitutional hash is set correctly."""
        assert settings.constitutional_hash == CONSTITUTIONAL_HASH
        assert settings.constitutional_hash == "cdd01ef066bc6cf2"

    def test_database_url_format(self, settings: Settings) -> None:
        """Test database URL is properly formatted."""
        db_url = settings.database_url
        assert db_url.startswith("postgresql+asyncpg://")
        assert str(settings.postgresql_port) in db_url
        assert settings.postgresql_host in db_url

    def test_redis_url_format(self, settings: Settings) -> None:
        """Test Redis URL is properly formatted."""
        redis_url = settings.redis_url
        assert redis_url.startswith("redis://")
        assert str(settings.redis_port) in redis_url
        assert settings.redis_host in redis_url

    def test_to_dict_contains_required_fields(self, settings: Settings) -> None:
        """Test to_dict includes all required fields."""
        data = settings.to_dict()

        required_fields = [
            "service_name",
            "service_version",
            "debug",
            "host",
            "port",
            "api_prefix",
            "constitutional_hash",
            "postgresql_host",
            "postgresql_port",
            "redis_host",
            "redis_port",
        ]

        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    @pytest.mark.constitutional
    def test_to_dict_constitutional_hash(self, settings: Settings) -> None:
        """Test to_dict includes correct constitutional hash."""
        data = settings.to_dict()
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH


class TestGetSettings:
    """Tests for get_settings function."""

    def test_get_settings_returns_settings(self) -> None:
        """Test get_settings returns Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_is_cached(self) -> None:
        """Test get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2

    @pytest.mark.constitutional
    def test_get_settings_has_constitutional_hash(self) -> None:
        """Test cached settings has constitutional hash."""
        settings = get_settings()
        assert settings.constitutional_hash == CONSTITUTIONAL_HASH


class TestSettingsDefaults:
    """Tests for settings default values.

    Note: Settings class attributes are evaluated at class definition time,
    so environment variables need to be set before module import.
    These tests verify default values are used correctly.
    """

    def test_port_default_value(self) -> None:
        """Test port configuration has correct default."""
        settings = Settings()
        # Default value when API_PORT not set
        assert settings.port == 8007

    def test_debug_default_value(self) -> None:
        """Test debug configuration has correct default."""
        settings = Settings()
        # Default value when DEBUG not set or not "true"
        assert settings.debug is False

    def test_postgresql_port_default_value(self) -> None:
        """Test PostgreSQL port has correct ACGS default."""
        settings = Settings()
        # Default ACGS standard port
        assert settings.postgresql_port == 5439

    def test_redis_port_default_value(self) -> None:
        """Test Redis port has correct ACGS default."""
        settings = Settings()
        # Default ACGS standard port
        assert settings.redis_port == 6389

    def test_log_level_default_value(self) -> None:
        """Test log level has correct default."""
        settings = Settings()
        # Default value
        assert settings.log_level == "INFO"
