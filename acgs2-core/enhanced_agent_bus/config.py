"""
ACGS-2 Enhanced Agent Bus - Configuration
Constitutional Hash: cdd01ef066bc6cf2

Configuration dataclass for the Enhanced Agent Bus.
Follows the Builder pattern for clean configuration management.
"""

import os
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Optional
from urllib.parse import urlparse

import litellm
from litellm.caching import Cache

# Import types conditionally to avoid circular imports
if TYPE_CHECKING:
    pass


# Import centralized constitutional hash with fallback
try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Default Redis URL with fallback
try:
    from shared.redis_config import get_redis_url

    DEFAULT_REDIS_URL = get_redis_url()
except ImportError:
    DEFAULT_REDIS_URL = "redis://localhost:6379"


@dataclass
class BusConfiguration:
    """Configuration for EnhancedAgentBus.

    Consolidates all configuration options into a single, immutable dataclass.
    This follows the Configuration Object pattern for clean dependency management.

    Example usage:
        # Default configuration
        config = BusConfiguration()

        # Custom configuration
        config = BusConfiguration(
            use_dynamic_policy=True,
            policy_fail_closed=True,
            enable_metering=True,
        )

        # Build configuration from environment
        config = BusConfiguration.from_environment()
    """

    # Connection settings
    redis_url: str = DEFAULT_REDIS_URL
    kafka_bootstrap_servers: str = "localhost:9092"
    audit_service_url: str = "http://localhost:8001"

    # Feature flags
    use_dynamic_policy: bool = False
    # SECURITY FIX (2025-12): Default to fail-closed for security-first behavior
    policy_fail_closed: bool = True
    use_kafka: bool = False
    use_redis_registry: bool = False
    use_rust: bool = True
    enable_metering: bool = True

    # MACI role separation settings
    # SECURITY FIX (audit finding 2025-12): MACI enabled by default to prevent
    # Gödel bypass attacks through role separation enforcement.
    # Set enable_maci=False only for legacy/testing - see for_testing() method.
    enable_maci: bool = True
    maci_strict_mode: bool = True

    # LLM classification settings
    # Controls hybrid intent classification with LLM fallback for ambiguous cases
    llm_enabled: bool = True
    llm_model_version: str = "openai/gpt-4o-mini"
    llm_cache_ttl: int = 3600  # seconds
    llm_confidence_threshold: float = 0.8
    llm_max_tokens: int = 100
    llm_use_cache: bool = True

    # A/B testing settings for LLM vs rule-based comparison
    enable_ab_testing: bool = False
    ab_test_llm_percentage: int = 20  # Percentage of ambiguous cases routed to LLM

    # Optional dependency injections (set to None for defaults)
    # Note: These are typed as Any to avoid circular imports at runtime
    registry: Optional[Any] = None
    router: Optional[Any] = None
    validator: Optional[Any] = None
    processor: Optional[Any] = None
    metering_config: Optional[Any] = None

    # Constitutional settings
    constitutional_hash: str = field(default=CONSTITUTIONAL_HASH)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Ensure constitutional hash is always set
        if not self.constitutional_hash:
            self.constitutional_hash = CONSTITUTIONAL_HASH

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        """Parse various representations of boolean values."""
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        s = str(value).lower()
        return s in ("true", "1", "yes", "on", "y", "t")

    @staticmethod
    def _parse_int(value: Optional[str], default: int) -> int:
        """Parse integer value with fallback to default."""
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    @staticmethod
    def _parse_float(value: Optional[str], default: float) -> float:
        """Parse float value with fallback to default."""
        if value is None:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    @classmethod
    def from_environment(cls) -> "BusConfiguration":
        """Load configuration from environment variables.

        Environment variables:
            REDIS_URL: Redis connection URL
            KAFKA_BOOTSTRAP_SERVERS: Kafka servers
            AUDIT_SERVICE_URL: Audit service endpoint
            USE_DYNAMIC_POLICY: Enable dynamic policy (true/false)
            POLICY_FAIL_CLOSED: Fail closed mode (true/false)
            USE_KAFKA: Enable Kafka (true/false)
            USE_REDIS_REGISTRY: Use Redis registry (true/false)
            USE_RUST_BACKEND: Enable Rust backend (true/false)
            METERING_ENABLED: Enable metering (true/false)
            MACI_ENABLED: Enable MACI (true/false)
            MACI_STRICT_MODE: MACI strict mode (true/false)
            LLM_ENABLED: Enable LLM classification (true/false)
            LLM_MODEL_VERSION: LLM model version (e.g., openai/gpt-4o-mini)
            LLM_CACHE_TTL: LLM cache TTL in seconds
            LLM_CONFIDENCE_THRESHOLD: Confidence threshold for LLM fallback (0.0-1.0)
            LLM_MAX_TOKENS: Maximum tokens for LLM response
            LLM_USE_CACHE: Enable LLM response caching (true/false)
            ENABLE_AB_TESTING: Enable A/B testing (true/false)
            AB_TEST_LLM_PERCENTAGE: Percentage of ambiguous cases for LLM (0-100)
        """
        config = cls(
            redis_url=os.getenv("REDIS_URL", DEFAULT_REDIS_URL),
            kafka_bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            audit_service_url=os.getenv("AUDIT_SERVICE_URL", "http://localhost:8001"),
            use_dynamic_policy=cls._parse_bool(os.getenv("USE_DYNAMIC_POLICY", "false")),
            policy_fail_closed=cls._parse_bool(os.getenv("POLICY_FAIL_CLOSED", "true")),
            use_kafka=cls._parse_bool(os.getenv("USE_KAFKA", "false")),
            use_redis_registry=cls._parse_bool(os.getenv("USE_REDIS_REGISTRY", "false")),
            use_rust=cls._parse_bool(os.getenv("USE_RUST", "true")),
            enable_metering=cls._parse_bool(os.getenv("ENABLE_METERING", "true")),
            enable_maci=cls._parse_bool(os.getenv("ENABLE_MACI", "true")),
            maci_strict_mode=cls._parse_bool(os.getenv("MACI_STRICT_MODE", "true")),
            llm_enabled=cls._parse_bool(os.getenv("LLM_ENABLED", "true")),
            llm_model_version=os.getenv("LLM_MODEL_VERSION", "openai/gpt-4o-mini"),
            llm_cache_ttl=cls._parse_int(os.getenv("LLM_CACHE_TTL"), 3600),
            llm_confidence_threshold=cls._parse_float(os.getenv("LLM_CONFIDENCE_THRESHOLD"), 0.8),
            llm_max_tokens=cls._parse_int(os.getenv("LLM_MAX_TOKENS"), 100),
            llm_use_cache=cls._parse_bool(os.getenv("LLM_USE_CACHE", "true")),
            enable_ab_testing=cls._parse_bool(os.getenv("ENABLE_AB_TESTING", "false")),
            ab_test_llm_percentage=cls._parse_int(os.getenv("AB_TEST_LLM_PERCENTAGE"), 20),
        )

        # Initialize LiteLLM Cache if enabled
        if config.llm_use_cache:
            try:
                parsed_url = urlparse(config.redis_url)
                litellm.cache = Cache(
                    type="redis",
                    host=parsed_url.hostname or "localhost",
                    port=parsed_url.port or 6379,
                    password=parsed_url.password,
                )
            except Exception:
                # Fallback to in-memory if redis fails or isn't available
                litellm.cache = Cache()

        return config

    @classmethod
    def for_testing(cls) -> "BusConfiguration":
        """Create a minimal configuration for unit testing.

        Disables all optional features for fast, isolated testing.
        """
        return cls(
            use_dynamic_policy=False,
            policy_fail_closed=False,
            use_kafka=False,
            use_redis_registry=False,
            use_rust=False,
            enable_metering=False,
            enable_maci=False,
            maci_strict_mode=False,
            llm_enabled=False,
            llm_use_cache=False,
            enable_ab_testing=False,
        )

    @classmethod
    def for_production(cls) -> "BusConfiguration":
        """Create a configuration suitable for production use.

        Enables all production features with fail-closed security.
        """
        return cls(
            use_dynamic_policy=True,
            policy_fail_closed=True,
            use_kafka=True,
            use_redis_registry=True,
            use_rust=True,
            enable_metering=True,
            enable_maci=True,
            maci_strict_mode=True,
            llm_enabled=True,
            llm_confidence_threshold=0.8,
            llm_use_cache=True,
            enable_ab_testing=False,
        )

    def with_registry(self, registry: Any) -> "BusConfiguration":
        """Return a new configuration with the specified registry.

        Builder pattern method for fluent configuration.
        Uses dataclasses.replace() for immutable field updates.
        """
        return replace(self, registry=registry)

    def with_validator(self, validator: Any) -> "BusConfiguration":
        """Return a new configuration with the specified validator.

        Builder pattern method for fluent configuration.
        Uses dataclasses.replace() for immutable field updates.
        """
        return replace(self, validator=validator)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary for logging/serialization."""
        return {
            "redis_url": self.redis_url,
            "kafka_bootstrap_servers": self.kafka_bootstrap_servers,
            "audit_service_url": self.audit_service_url,
            "use_dynamic_policy": self.use_dynamic_policy,
            "policy_fail_closed": self.policy_fail_closed,
            "use_kafka": self.use_kafka,
            "use_redis_registry": self.use_redis_registry,
            "use_rust": self.use_rust,
            "enable_metering": self.enable_metering,
            "enable_maci": self.enable_maci,
            "maci_strict_mode": self.maci_strict_mode,
            "constitutional_hash": self.constitutional_hash,
            "llm_enabled": self.llm_enabled,
            "llm_model_version": self.llm_model_version,
            "llm_cache_ttl": self.llm_cache_ttl,
            "llm_confidence_threshold": self.llm_confidence_threshold,
            "llm_max_tokens": self.llm_max_tokens,
            "llm_use_cache": self.llm_use_cache,
            "enable_ab_testing": self.enable_ab_testing,
            "ab_test_llm_percentage": self.ab_test_llm_percentage,
            "has_custom_registry": self.registry is not None,
            "has_custom_router": self.router is not None,
            "has_custom_validator": self.validator is not None,
            "has_custom_processor": self.processor is not None,
            "has_metering_config": self.metering_config is not None,
        }


try:
    from shared.config import settings
except ImportError:
    settings = BusConfiguration()  # Use as fallback if shared settings not available
