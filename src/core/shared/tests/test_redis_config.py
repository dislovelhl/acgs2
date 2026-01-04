"""
ACGS-2 Redis Configuration Module Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for shared/redis_config.py
"""

import os
import threading
from unittest.mock import MagicMock, patch

import pytest

# Import module under test
from src.core.shared.redis_config import (
    CONSTITUTIONAL_HASH,
    REDIS_URL,
    REDIS_URL_WITH_DB,
    RedisConfig,
    RedisHealthCheckConfig,
    RedisHealthListener,
    RedisHealthState,
    get_redis_config,
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


# ============================================================================
# Constitutional Compliance Tests
# ============================================================================


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_present(self):
        """Verify constitutional hash is present and correct."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_constitutional_hash_in_module(self):
        """Verify constitutional hash is exported."""
        from shared import redis_config

        assert hasattr(redis_config, "CONSTITUTIONAL_HASH")
        assert redis_config.CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


# ============================================================================
# RedisHealthState Enum Tests
# ============================================================================


class TestRedisHealthState:
    """Test RedisHealthState enum."""

    def test_healthy_state(self):
        """Test HEALTHY state value."""
        assert RedisHealthState.HEALTHY.value == "healthy"

    def test_unhealthy_state(self):
        """Test UNHEALTHY state value."""
        assert RedisHealthState.UNHEALTHY.value == "unhealthy"

    def test_recovering_state(self):
        """Test RECOVERING state value."""
        assert RedisHealthState.RECOVERING.value == "recovering"

    def test_unknown_state(self):
        """Test UNKNOWN state value."""
        assert RedisHealthState.UNKNOWN.value == "unknown"

    def test_all_states_defined(self):
        """Test all expected states exist."""
        states = [s.value for s in RedisHealthState]
        assert "healthy" in states
        assert "unhealthy" in states
        assert "recovering" in states
        assert "unknown" in states


# ============================================================================
# RedisHealthCheckConfig Tests
# ============================================================================


class TestRedisHealthCheckConfig:
    """Test RedisHealthCheckConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RedisHealthCheckConfig()
        assert config.check_interval == 30.0
        assert config.timeout == 5.0
        assert config.unhealthy_threshold == 3
        assert config.healthy_threshold == 1

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RedisHealthCheckConfig(
            check_interval=60.0,
            timeout=10.0,
            unhealthy_threshold=5,
            healthy_threshold=2,
        )
        assert config.check_interval == 60.0
        assert config.timeout == 10.0
        assert config.unhealthy_threshold == 5
        assert config.healthy_threshold == 2

    def test_partial_custom_values(self):
        """Test partial custom configuration."""
        config = RedisHealthCheckConfig(check_interval=15.0)
        assert config.check_interval == 15.0
        assert config.timeout == 5.0  # Default


# ============================================================================
# RedisHealthListener Tests
# ============================================================================


class TestRedisHealthListener:
    """Test Redis health listener."""

    def test_listener_initialization(self):
        """Test listener initializes correctly."""
        listener = RedisHealthListener("test_redis")
        assert listener.name == "test_redis"
        assert listener.constitutional_hash == CONSTITUTIONAL_HASH

    def test_listener_default_name(self):
        """Test listener default name."""
        listener = RedisHealthListener()
        assert listener.name == "redis"

    def test_state_change_logging(self):
        """Test state change is logged."""
        listener = RedisHealthListener("test_redis")

        with patch("shared.redis_config.logger") as mock_logger:
            listener.on_state_change(RedisHealthState.UNKNOWN, RedisHealthState.HEALTHY)
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "test_redis" in call_args
            assert "unknown" in call_args
            assert "healthy" in call_args

    def test_health_check_success_logging(self):
        """Test successful health check is logged."""
        listener = RedisHealthListener("test_redis")

        with patch("shared.redis_config.logger") as mock_logger:
            listener.on_health_check_success(1.5)
            mock_logger.debug.assert_called_once()
            call_args = mock_logger.debug.call_args[0][0]
            assert "test_redis" in call_args
            assert "1.50" in call_args  # Latency formatted

    def test_health_check_failure_logging(self):
        """Test failed health check is logged."""
        listener = RedisHealthListener("test_redis")

        with patch("shared.redis_config.logger") as mock_logger:
            listener.on_health_check_failure(ConnectionError("Test error"))
            mock_logger.warning.assert_called_once()
            call_args = mock_logger.warning.call_args[0][0]
            assert "test_redis" in call_args
            assert "ConnectionError" in call_args
            assert "Test error" in call_args


# ============================================================================
# RedisConfig Health Check Tests
# ============================================================================


class TestRedisConfigHealthCheck:
    """Test RedisConfig health check functionality."""

    @pytest.fixture
    def redis_config(self):
        """Create a fresh RedisConfig instance for testing."""
        return RedisConfig()

    def test_initial_state_unknown(self, redis_config):
        """Test initial health state is UNKNOWN."""
        assert redis_config.current_state == RedisHealthState.UNKNOWN

    def test_is_healthy_property(self, redis_config):
        """Test is_healthy property."""
        assert redis_config.is_healthy is False  # UNKNOWN is not healthy

    def test_register_health_callback(self, redis_config):
        """Test registering a health callback."""
        callback_called = []

        def test_callback(old_state, new_state):
            callback_called.append((old_state, new_state))

        with patch("shared.redis_config.logger"):
            redis_config.register_health_callback(test_callback)

        # Callback should be registered
        assert test_callback in redis_config._callbacks

    def test_unregister_health_callback(self, redis_config):
        """Test unregistering a health callback."""

        def test_callback(old_state, new_state):
            pass

        with patch("shared.redis_config.logger"):
            redis_config.register_health_callback(test_callback)
            result = redis_config.unregister_health_callback(test_callback)

        assert result is True
        assert test_callback not in redis_config._callbacks

    def test_unregister_nonexistent_callback(self, redis_config):
        """Test unregistering a callback that doesn't exist."""

        def test_callback(old_state, new_state):
            pass

        result = redis_config.unregister_health_callback(test_callback)
        assert result is False

    def test_add_listener(self, redis_config):
        """Test adding a health listener."""
        listener = RedisHealthListener("custom_listener")
        redis_config.add_listener(listener)

        assert listener in redis_config._listeners

    def test_health_check_success(self, redis_config):
        """Test health check with successful ping."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        is_healthy, latency = redis_config.health_check(redis_client=mock_client)

        assert is_healthy is True
        assert latency is not None
        assert latency >= 0
        mock_client.ping.assert_called_once()

    def test_health_check_failure(self, redis_config):
        """Test health check with failed ping."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")

        is_healthy, latency = redis_config.health_check(redis_client=mock_client)

        assert is_healthy is False
        assert latency is not None

    def test_health_check_no_client(self, redis_config):
        """Test health check when client creation fails."""
        with patch.object(redis_config, "_get_or_create_client", return_value=None):
            is_healthy, latency = redis_config.health_check()

        assert is_healthy is False

    def test_consecutive_failures_threshold(self, redis_config):
        """Test state becomes UNHEALTHY after consecutive failures."""
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")

        # Perform multiple failed checks
        for _ in range(redis_config.health_config.unhealthy_threshold):
            redis_config.health_check(redis_client=mock_client)

        assert redis_config.current_state == RedisHealthState.UNHEALTHY
        assert redis_config._consecutive_failures == redis_config.health_config.unhealthy_threshold

    def test_consecutive_successes_threshold(self, redis_config):
        """Test state becomes HEALTHY after consecutive successes."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        # Perform multiple successful checks
        for _ in range(redis_config.health_config.healthy_threshold):
            redis_config.health_check(redis_client=mock_client)

        assert redis_config.current_state == RedisHealthState.HEALTHY
        assert redis_config._consecutive_successes >= redis_config.health_config.healthy_threshold

    def test_state_transition_callback(self, redis_config):
        """Test callback is invoked on state transition."""
        callback_invocations = []

        def test_callback(old_state, new_state):
            callback_invocations.append((old_state, new_state))

        with patch("shared.redis_config.logger"):
            redis_config.register_health_callback(test_callback)

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        # Trigger state change from UNKNOWN to HEALTHY
        redis_config.health_check(redis_client=mock_client)

        assert len(callback_invocations) == 1
        assert callback_invocations[0] == (RedisHealthState.UNKNOWN, RedisHealthState.HEALTHY)

    def test_last_latency_ms_property(self, redis_config):
        """Test last_latency_ms property is updated."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        redis_config.health_check(redis_client=mock_client)

        assert redis_config.last_latency_ms is not None
        assert redis_config.last_latency_ms >= 0

    def test_last_check_time_property(self, redis_config):
        """Test last_check_time property is updated."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        redis_config.health_check(redis_client=mock_client)

        assert redis_config.last_check_time is not None

    def test_get_health_stats(self, redis_config):
        """Test get_health_stats returns comprehensive stats."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        redis_config.health_check(redis_client=mock_client)
        stats = redis_config.get_health_stats()

        assert "state" in stats
        assert "is_healthy" in stats
        assert "consecutive_failures" in stats
        assert "consecutive_successes" in stats
        assert "last_latency_ms" in stats
        assert "last_check_time" in stats
        assert "config" in stats
        assert stats["is_healthy"] is True

    def test_get_health_stats_config_section(self, redis_config):
        """Test get_health_stats includes config section."""
        stats = redis_config.get_health_stats()

        assert "config" in stats
        config = stats["config"]
        assert "check_interval" in config
        assert "timeout" in config
        assert "unhealthy_threshold" in config
        assert "healthy_threshold" in config

    def test_reset_state(self, redis_config):
        """Test reset method resets state to UNKNOWN."""
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        # Get to HEALTHY state
        redis_config.health_check(redis_client=mock_client)
        assert redis_config.current_state == RedisHealthState.HEALTHY

        # Reset
        with patch("shared.redis_config.logger"):
            redis_config.reset()

        assert redis_config.current_state == RedisHealthState.UNKNOWN
        assert redis_config._consecutive_failures == 0
        assert redis_config._consecutive_successes == 0
        assert redis_config._last_check_time is None
        assert redis_config._last_latency_ms is None

    def test_reset_triggers_callback(self, redis_config):
        """Test reset triggers callback when state changes."""
        callback_invocations = []

        def test_callback(old_state, new_state):
            callback_invocations.append((old_state, new_state))

        mock_client = MagicMock()
        mock_client.ping.return_value = True

        with patch("shared.redis_config.logger"):
            redis_config.register_health_callback(test_callback)

        redis_config.health_check(redis_client=mock_client)
        callback_invocations.clear()

        with patch("shared.redis_config.logger"):
            redis_config.reset()

        assert len(callback_invocations) == 1
        assert callback_invocations[0] == (RedisHealthState.HEALTHY, RedisHealthState.UNKNOWN)


# ============================================================================
# RedisConfig Thread Safety Tests
# ============================================================================


class TestRedisConfigThreadSafety:
    """Test thread safety of RedisConfig health checks."""

    def test_concurrent_health_checks(self):
        """Test concurrent health checks are thread-safe."""
        config = RedisConfig()
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        results = []
        errors = []

        def perform_check():
            try:
                is_healthy, latency = config.health_check(redis_client=mock_client)
                results.append((is_healthy, latency))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=perform_check) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10
        assert all(r[0] is True for r in results)

    def test_concurrent_callback_registration(self):
        """Test concurrent callback registration is thread-safe."""
        config = RedisConfig()
        errors = []

        def register_callback():
            try:

                def callback(old, new):
                    pass

                with patch("shared.redis_config.logger"):
                    config.register_health_callback(callback)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_callback) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(config._callbacks) == 10


# ============================================================================
# get_redis_config Singleton Tests
# ============================================================================


class TestGetRedisConfigSingleton:
    """Test get_redis_config singleton function."""

    def test_returns_redis_config_instance(self):
        """Test get_redis_config returns RedisConfig instance."""
        # Reset global to test fresh state
        import src.core.shared.redis_config as rc

        with patch.object(rc, "_global_redis_config", None):
            config = get_redis_config()
            assert isinstance(config, RedisConfig)

    def test_returns_same_instance(self):
        """Test get_redis_config returns same instance on multiple calls."""
        import src.core.shared.redis_config as rc

        with patch.object(rc, "_global_redis_config", None):
            config1 = get_redis_config()
            config2 = get_redis_config()
            assert config1 is config2


# ============================================================================
# Async Health Check Tests
# ============================================================================


class TestAsyncHealthCheck:
    """Test async health check functionality."""

    @pytest.fixture
    def redis_config(self):
        """Create a fresh RedisConfig instance for testing."""
        return RedisConfig()

    @pytest.mark.asyncio
    async def test_health_check_async_success(self, redis_config):
        """Test async health check with successful ping."""
        mock_client = MagicMock()
        mock_client.ping = MagicMock(return_value=True)

        # Make ping awaitable
        async def async_ping():
            return True

        mock_client.ping = async_ping

        is_healthy, latency = await redis_config.health_check_async(redis_client=mock_client)

        assert is_healthy is True
        assert latency is not None
        assert latency >= 0

    @pytest.mark.asyncio
    async def test_health_check_async_failure(self, redis_config):
        """Test async health check with failed ping."""
        mock_client = MagicMock()

        async def async_ping():
            raise ConnectionError("Connection refused")

        mock_client.ping = async_ping

        is_healthy, latency = await redis_config.health_check_async(redis_client=mock_client)

        assert is_healthy is False
        assert latency is not None

    @pytest.mark.asyncio
    async def test_health_check_async_no_client(self, redis_config):
        """Test async health check with no client."""
        is_healthy, latency = await redis_config.health_check_async(redis_client=None)

        assert is_healthy is False
