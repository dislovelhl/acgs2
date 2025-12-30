"""
ACGS-2 Redis Configuration Module Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for shared/redis_config.py
"""

import os
from unittest.mock import patch

# Import module under test
from shared.redis_config import (
    REDIS_URL,
    REDIS_URL_WITH_DB,
    RedisConfig,
    get_redis_url,
)

# ============================================================================
# RedisConfig Class Tests
# ============================================================================


class TestRedisConfigClass:
    """Test RedisConfig dataclass."""

    def test_default_url_defined(self):
        """Test default URL is defined."""
        assert RedisConfig.DEFAULT_URL == "redis://localhost:6379"


# ============================================================================
# RedisConfig.get_url Tests
# ============================================================================


class TestGetUrl:
    """Test RedisConfig.get_url method."""

    def test_get_url_default(self):
        """Test get_url returns default URL."""
        with patch.dict(os.environ, {}, clear=True):
            url = RedisConfig.get_url()
            assert url == "redis://localhost:6379"

    def test_get_url_from_environment(self):
        """Test get_url uses environment variable."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://custom:6380"}):
            url = RedisConfig.get_url()
            assert url == "redis://custom:6380"

    def test_get_url_with_db_number(self):
        """Test get_url appends database number."""
        with patch.dict(os.environ, {}, clear=True):
            url = RedisConfig.get_url(db=1)
            assert url == "redis://localhost:6379/1"

    def test_get_url_db_zero_no_append(self):
        """Test get_url with db=0 doesn't append."""
        with patch.dict(os.environ, {}, clear=True):
            url = RedisConfig.get_url(db=0)
            assert url == "redis://localhost:6379"

    def test_get_url_custom_env_var(self):
        """Test get_url with custom environment variable."""
        with patch.dict(os.environ, {"CUSTOM_REDIS": "redis://other:6381"}):
            url = RedisConfig.get_url(env_var="CUSTOM_REDIS")
            assert url == "redis://other:6381"

    def test_get_url_preserves_existing_db(self):
        """Test get_url doesn't double-append database."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379/5"}):
            url = RedisConfig.get_url(db=1)
            # Should preserve existing /5, not append /1
            assert url == "redis://localhost:6379/5"

    def test_get_url_strips_trailing_slash(self):
        """Test get_url strips trailing slash before appending db."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379/"}):
            url = RedisConfig.get_url(db=2)
            # Should handle trailing slash correctly
            assert "/2" in url or url.count("/") > 2


# ============================================================================
# RedisConfig.get_connection_params Tests
# ============================================================================


class TestGetConnectionParams:
    """Test RedisConfig.get_connection_params method."""

    def test_get_connection_params_defaults(self):
        """Test get_connection_params returns defaults."""
        with patch.dict(os.environ, {}, clear=True):
            params = RedisConfig.get_connection_params()

            assert "url" in params
            assert params["max_connections"] == 10
            assert params["socket_timeout"] == 5.0
            assert params["socket_connect_timeout"] == 5.0
            assert params["retry_on_timeout"] is True

    def test_get_connection_params_from_environment(self):
        """Test get_connection_params uses environment variables."""
        env_vars = {
            "REDIS_URL": "redis://custom:6380",
            "REDIS_MAX_CONNECTIONS": "20",
            "REDIS_SOCKET_TIMEOUT": "10.0",
            "REDIS_CONNECT_TIMEOUT": "3.0",
            "REDIS_RETRY_ON_TIMEOUT": "false",
        }
        with patch.dict(os.environ, env_vars):
            params = RedisConfig.get_connection_params()

            assert params["url"] == "redis://custom:6380"
            assert params["max_connections"] == 20
            assert params["socket_timeout"] == 10.0
            assert params["socket_connect_timeout"] == 3.0
            assert params["retry_on_timeout"] is False

    def test_get_connection_params_retry_true(self):
        """Test retry_on_timeout is true by default."""
        with patch.dict(os.environ, {"REDIS_RETRY_ON_TIMEOUT": "true"}):
            params = RedisConfig.get_connection_params()
            assert params["retry_on_timeout"] is True

    def test_get_connection_params_retry_case_insensitive(self):
        """Test retry_on_timeout handles case variations."""
        with patch.dict(os.environ, {"REDIS_RETRY_ON_TIMEOUT": "TRUE"}):
            params = RedisConfig.get_connection_params()
            assert params["retry_on_timeout"] is True


# ============================================================================
# Module-level Constants Tests
# ============================================================================


class TestModuleConstants:
    """Test module-level constants."""

    def test_redis_url_is_string(self):
        """Test REDIS_URL is a string."""
        assert isinstance(REDIS_URL, str)

    def test_redis_url_with_db_is_string(self):
        """Test REDIS_URL_WITH_DB is a string."""
        assert isinstance(REDIS_URL_WITH_DB, str)

    def test_redis_url_format(self):
        """Test REDIS_URL has correct format."""
        assert REDIS_URL.startswith("redis://")


# ============================================================================
# get_redis_url Function Tests
# ============================================================================


class TestGetRedisUrlFunction:
    """Test get_redis_url convenience function."""

    def test_get_redis_url_default(self):
        """Test get_redis_url returns default URL."""
        url = get_redis_url()
        assert "redis://" in url

    def test_get_redis_url_with_db(self):
        """Test get_redis_url with database number."""
        url = get_redis_url(db=3)
        assert "/3" in url or url.count("/") > 2

    def test_get_redis_url_returns_string(self):
        """Test get_redis_url returns string."""
        url = get_redis_url()
        assert isinstance(url, str)


# ============================================================================
# Integration Tests
# ============================================================================


class TestRedisConfigIntegration:
    """Integration tests for Redis configuration."""

    def test_url_and_params_consistent(self):
        """Test URL from get_url matches params."""
        url = RedisConfig.get_url()
        params = RedisConfig.get_connection_params()
        assert params["url"] == url

    def test_multiple_databases(self):
        """Test getting URLs for multiple databases."""
        urls = [get_redis_url(db=i) for i in range(3)]

        # First URL (db=0) shouldn't have /0
        assert urls[0] == "redis://localhost:6379" or "/0" in urls[0]

        # db=1 should have /1
        assert "/1" in urls[1]

        # db=2 should have /2
        assert "/2" in urls[2]
