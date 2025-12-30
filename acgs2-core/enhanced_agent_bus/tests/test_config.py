"""
ACGS-2 Enhanced Agent Bus - Configuration Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for BusConfiguration dataclass with builder pattern.
"""

import os
from unittest.mock import patch

import pytest

try:
    from config import CONSTITUTIONAL_HASH, DEFAULT_REDIS_URL, BusConfiguration
except ImportError:
    from ..config import CONSTITUTIONAL_HASH, DEFAULT_REDIS_URL, BusConfiguration


class TestBusConfigurationDefaults:
    """Tests for BusConfiguration default values."""

    def test_default_redis_url(self):
        """Test default Redis URL."""
        config = BusConfiguration()
        assert config.redis_url == DEFAULT_REDIS_URL

    def test_default_kafka_servers(self):
        """Test default Kafka servers."""
        config = BusConfiguration()
        assert config.kafka_bootstrap_servers == "localhost:9092"

    def test_default_audit_service_url(self):
        """Test default audit service URL."""
        config = BusConfiguration()
        assert config.audit_service_url == "http://localhost:8001"

    def test_default_feature_flags(self):
        """Test default feature flag values."""
        config = BusConfiguration()
        assert config.use_dynamic_policy is False
        # SECURITY FIX (2025-12): Default to fail-closed for security-first behavior
        assert config.policy_fail_closed is True
        assert config.use_kafka is False
        assert config.use_redis_registry is False
        assert config.use_rust is True
        assert config.enable_metering is True

    def test_default_maci_settings(self):
        """Test default MACI settings - enabled by default per audit finding 2025-12."""
        config = BusConfiguration()
        # SECURITY: MACI enabled by default to prevent Gödel bypass attacks
        assert config.enable_maci is True
        assert config.maci_strict_mode is True

    def test_default_optional_dependencies(self):
        """Test default optional dependencies are None."""
        config = BusConfiguration()
        assert config.registry is None
        assert config.router is None
        assert config.validator is None
        assert config.processor is None
        assert config.metering_config is None

    def test_constitutional_hash_default(self):
        """Test constitutional hash defaults correctly."""
        config = BusConfiguration()
        assert config.constitutional_hash == CONSTITUTIONAL_HASH
        assert config.constitutional_hash == "cdd01ef066bc6cf2"


class TestBusConfigurationCustomValues:
    """Tests for BusConfiguration with custom values."""

    def test_custom_redis_url(self):
        """Test custom Redis URL."""
        config = BusConfiguration(redis_url="redis://custom:6379")
        assert config.redis_url == "redis://custom:6379"

    def test_custom_kafka_servers(self):
        """Test custom Kafka servers."""
        config = BusConfiguration(kafka_bootstrap_servers="kafka1:9092,kafka2:9092")
        assert config.kafka_bootstrap_servers == "kafka1:9092,kafka2:9092"

    def test_custom_feature_flags(self):
        """Test custom feature flags."""
        config = BusConfiguration(
            use_dynamic_policy=True,
            policy_fail_closed=True,
            use_kafka=True,
            use_redis_registry=True,
            use_rust=False,
            enable_metering=False,
        )
        assert config.use_dynamic_policy is True
        assert config.policy_fail_closed is True
        assert config.use_kafka is True
        assert config.use_redis_registry is True
        assert config.use_rust is False
        assert config.enable_metering is False

    def test_custom_maci_settings(self):
        """Test custom MACI settings."""
        config = BusConfiguration(enable_maci=True, maci_strict_mode=False)
        assert config.enable_maci is True
        assert config.maci_strict_mode is False


class TestBusConfigurationPostInit:
    """Tests for BusConfiguration __post_init__ validation."""

    def test_empty_constitutional_hash_filled(self):
        """Test that empty constitutional hash is filled with default."""
        config = BusConfiguration(constitutional_hash="")
        assert config.constitutional_hash == CONSTITUTIONAL_HASH

    def test_provided_constitutional_hash_kept(self):
        """Test that provided constitutional hash is kept."""
        custom_hash = "custom123456789"
        config = BusConfiguration(constitutional_hash=custom_hash)
        assert config.constitutional_hash == custom_hash


class TestBusConfigurationFromEnvironment:
    """Tests for BusConfiguration.from_environment factory method."""

    def test_from_environment_defaults(self):
        """Test from_environment with no env vars set."""
        with patch.dict(os.environ, {}, clear=True):
            config = BusConfiguration.from_environment()
            assert config.redis_url == DEFAULT_REDIS_URL
            assert config.use_dynamic_policy is False
            assert config.policy_fail_closed is False

    def test_from_environment_redis_url(self):
        """Test from_environment reads REDIS_URL."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://env:6379"}, clear=True):
            config = BusConfiguration.from_environment()
            assert config.redis_url == "redis://env:6379"

    def test_from_environment_kafka_servers(self):
        """Test from_environment reads KAFKA_BOOTSTRAP_SERVERS."""
        with patch.dict(os.environ, {"KAFKA_BOOTSTRAP_SERVERS": "kafka:9092"}, clear=True):
            config = BusConfiguration.from_environment()
            assert config.kafka_bootstrap_servers == "kafka:9092"

    def test_from_environment_audit_service(self):
        """Test from_environment reads AUDIT_SERVICE_URL."""
        with patch.dict(os.environ, {"AUDIT_SERVICE_URL": "http://audit:8001"}, clear=True):
            config = BusConfiguration.from_environment()
            assert config.audit_service_url == "http://audit:8001"

    @pytest.mark.parametrize(
        "env_value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("0", False),
            ("no", False),
            ("off", False),
            ("random", False),
        ],
    )
    def test_from_environment_bool_parsing(self, env_value, expected):
        """Test boolean parsing for environment variables."""
        with patch.dict(os.environ, {"USE_DYNAMIC_POLICY": env_value}, clear=True):
            config = BusConfiguration.from_environment()
            assert config.use_dynamic_policy is expected

    def test_from_environment_all_bool_flags(self):
        """Test all boolean flags from environment."""
        env_vars = {
            "USE_DYNAMIC_POLICY": "true",
            "POLICY_FAIL_CLOSED": "true",
            "USE_KAFKA": "true",
            "USE_REDIS_REGISTRY": "true",
            "USE_RUST_BACKEND": "false",
            "METERING_ENABLED": "false",
            "MACI_ENABLED": "true",
            "MACI_STRICT_MODE": "false",
        }
        with patch.dict(os.environ, env_vars, clear=True):
            config = BusConfiguration.from_environment()
            assert config.use_dynamic_policy is True
            assert config.policy_fail_closed is True
            assert config.use_kafka is True
            assert config.use_redis_registry is True
            assert config.use_rust is False
            assert config.enable_metering is False
            assert config.enable_maci is True
            assert config.maci_strict_mode is False


class TestBusConfigurationForTesting:
    """Tests for BusConfiguration.for_testing factory method."""

    def test_for_testing_minimal_config(self):
        """Test for_testing creates minimal configuration."""
        config = BusConfiguration.for_testing()
        assert config.use_dynamic_policy is False
        assert config.policy_fail_closed is False
        assert config.use_kafka is False
        assert config.use_redis_registry is False
        assert config.use_rust is False
        assert config.enable_metering is False
        assert config.enable_maci is False
        assert config.maci_strict_mode is False

    def test_for_testing_constitutional_hash_present(self):
        """Test for_testing still has constitutional hash."""
        config = BusConfiguration.for_testing()
        assert config.constitutional_hash == CONSTITUTIONAL_HASH


class TestBusConfigurationForProduction:
    """Tests for BusConfiguration.for_production factory method."""

    def test_for_production_all_features_enabled(self):
        """Test for_production enables all features."""
        config = BusConfiguration.for_production()
        assert config.use_dynamic_policy is True
        assert config.policy_fail_closed is True
        assert config.use_kafka is True
        assert config.use_redis_registry is True
        assert config.use_rust is True
        assert config.enable_metering is True
        assert config.enable_maci is True
        assert config.maci_strict_mode is True

    def test_for_production_constitutional_hash_present(self):
        """Test for_production has constitutional hash."""
        config = BusConfiguration.for_production()
        assert config.constitutional_hash == CONSTITUTIONAL_HASH


class TestBusConfigurationBuilderMethods:
    """Tests for BusConfiguration builder pattern methods."""

    def test_with_registry(self):
        """Test with_registry returns new config."""
        original = BusConfiguration()
        mock_registry = object()
        new_config = original.with_registry(mock_registry)

        assert new_config is not original
        assert new_config.registry is mock_registry
        assert original.registry is None

    def test_with_registry_preserves_other_values(self):
        """Test with_registry preserves other configuration."""
        original = BusConfiguration(
            redis_url="redis://custom:6379",
            use_dynamic_policy=True,
        )
        mock_registry = object()
        new_config = original.with_registry(mock_registry)

        assert new_config.redis_url == "redis://custom:6379"
        assert new_config.use_dynamic_policy is True

    def test_with_validator(self):
        """Test with_validator returns new config."""
        original = BusConfiguration()
        mock_validator = object()
        new_config = original.with_validator(mock_validator)

        assert new_config is not original
        assert new_config.validator is mock_validator
        assert original.validator is None

    def test_with_validator_preserves_other_values(self):
        """Test with_validator preserves other configuration."""
        original = BusConfiguration(
            enable_maci=True,
            maci_strict_mode=True,
        )
        mock_validator = object()
        new_config = original.with_validator(mock_validator)

        assert new_config.enable_maci is True
        assert new_config.maci_strict_mode is True

    def test_builder_method_chaining(self):
        """Test builder methods can be chained."""
        mock_registry = object()
        mock_validator = object()

        config = BusConfiguration().with_registry(mock_registry).with_validator(mock_validator)

        assert config.registry is mock_registry
        assert config.validator is mock_validator


class TestBusConfigurationToDict:
    """Tests for BusConfiguration.to_dict method."""

    def test_to_dict_basic_fields(self):
        """Test to_dict includes basic fields."""
        config = BusConfiguration()
        result = config.to_dict()

        assert "redis_url" in result
        assert "kafka_bootstrap_servers" in result
        assert "audit_service_url" in result
        assert "constitutional_hash" in result

    def test_to_dict_feature_flags(self):
        """Test to_dict includes feature flags."""
        config = BusConfiguration()
        result = config.to_dict()

        assert "use_dynamic_policy" in result
        assert "policy_fail_closed" in result
        assert "use_kafka" in result
        assert "use_redis_registry" in result
        assert "use_rust" in result
        assert "enable_metering" in result
        assert "enable_maci" in result
        assert "maci_strict_mode" in result

    def test_to_dict_optional_dependencies_as_booleans(self):
        """Test to_dict shows optional dependencies as booleans."""
        config = BusConfiguration()
        result = config.to_dict()

        assert result["has_custom_registry"] is False
        assert result["has_custom_router"] is False
        assert result["has_custom_validator"] is False
        assert result["has_custom_processor"] is False
        assert result["has_metering_config"] is False

    def test_to_dict_with_custom_dependencies(self):
        """Test to_dict shows True for custom dependencies."""
        config = BusConfiguration(registry=object(), validator=object())
        result = config.to_dict()

        assert result["has_custom_registry"] is True
        assert result["has_custom_validator"] is True
        assert result["has_custom_router"] is False

    def test_to_dict_values_match_config(self):
        """Test to_dict values match configuration."""
        config = BusConfiguration(
            redis_url="redis://test:6379",
            use_dynamic_policy=True,
            enable_maci=True,
        )
        result = config.to_dict()

        assert result["redis_url"] == "redis://test:6379"
        assert result["use_dynamic_policy"] is True
        assert result["enable_maci"] is True
        assert result["constitutional_hash"] == CONSTITUTIONAL_HASH


class TestBusConfigurationImmutability:
    """Tests for configuration immutability with builder pattern."""

    def test_builder_creates_new_instance(self):
        """Test builder methods create new instances."""
        config1 = BusConfiguration()
        config2 = config1.with_registry(object())
        config3 = config2.with_validator(object())

        assert config1 is not config2
        assert config2 is not config3
        assert config1 is not config3

    def test_original_unchanged_after_builder(self):
        """Test original configuration unchanged after builder."""
        original = BusConfiguration(
            use_dynamic_policy=True,
            enable_maci=True,
        )
        _ = original.with_registry(object())

        assert original.registry is None
        assert original.use_dynamic_policy is True
        assert original.enable_maci is True
