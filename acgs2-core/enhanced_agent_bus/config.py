"""
ACGS-2 Enhanced Agent Bus - Configuration
Constitutional Hash: cdd01ef066bc6cf2

Configuration dataclass for the Enhanced Agent Bus.
Follows the Builder pattern for clean configuration management.
"""

from dataclasses import dataclass, field, replace
from typing import Any, Optional, TYPE_CHECKING

# Import types conditionally to avoid circular imports
if TYPE_CHECKING:
    from .interfaces import AgentRegistry, MessageRouter, ValidationStrategy
    from .message_processor import MessageProcessor


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

    @classmethod
    def from_environment(cls) -> 'BusConfiguration':
        """Create configuration from environment variables.

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
        """
        import os

        def _parse_bool(value: Optional[str], default: bool = False) -> bool:
            if value is None:
                return default
            return value.lower() in ('true', '1', 'yes', 'on')

        return cls(
            redis_url=os.environ.get('REDIS_URL', DEFAULT_REDIS_URL),
            kafka_bootstrap_servers=os.environ.get(
                'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'
            ),
            audit_service_url=os.environ.get(
                'AUDIT_SERVICE_URL', 'http://localhost:8001'
            ),
            use_dynamic_policy=_parse_bool(
                os.environ.get('USE_DYNAMIC_POLICY'), False
            ),
            policy_fail_closed=_parse_bool(
                os.environ.get('POLICY_FAIL_CLOSED'), False
            ),
            use_kafka=_parse_bool(os.environ.get('USE_KAFKA'), False),
            use_redis_registry=_parse_bool(
                os.environ.get('USE_REDIS_REGISTRY'), False
            ),
            use_rust=_parse_bool(os.environ.get('USE_RUST_BACKEND'), True),
            enable_metering=_parse_bool(os.environ.get('METERING_ENABLED'), True),
            # SECURITY FIX: Default to True per audit finding 2025-12
            enable_maci=_parse_bool(os.environ.get('MACI_ENABLED'), True),
            maci_strict_mode=_parse_bool(os.environ.get('MACI_STRICT_MODE'), True),
        )

    @classmethod
    def for_testing(cls) -> 'BusConfiguration':
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
        )

    @classmethod
    def for_production(cls) -> 'BusConfiguration':
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
        )

    def with_registry(self, registry: Any) -> 'BusConfiguration':
        """Return a new configuration with the specified registry.

        Builder pattern method for fluent configuration.
        Uses dataclasses.replace() for immutable field updates.
        """
        return replace(self, registry=registry)

    def with_validator(self, validator: Any) -> 'BusConfiguration':
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
            "has_custom_registry": self.registry is not None,
            "has_custom_router": self.router is not None,
            "has_custom_validator": self.validator is not None,
            "has_custom_processor": self.processor is not None,
            "has_metering_config": self.metering_config is not None,
        }
