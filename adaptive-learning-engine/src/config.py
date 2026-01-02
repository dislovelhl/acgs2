"""
Adaptive Learning Engine - Configuration
Constitutional Hash: cdd01ef066bc6cf2

Configuration dataclass for the Adaptive Learning Engine.
Follows the Builder pattern for clean configuration management.
"""

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Optional

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
    DEFAULT_REDIS_URL = "redis://localhost:6379/0"


@dataclass
class AdaptiveLearningConfig:
    """Configuration for the Adaptive Learning Engine.

    Consolidates all configuration options into a single, immutable dataclass.
    This follows the Configuration Object pattern for clean dependency management.

    Example usage:
        # Default configuration
        config = AdaptiveLearningConfig()

        # Custom configuration
        config = AdaptiveLearningConfig(
            safety_accuracy_threshold=0.90,
            drift_check_interval_seconds=600,
            enable_prometheus=True,
        )

        # Build configuration from environment
        config = AdaptiveLearningConfig.from_environment()
    """

    # Server settings
    port: int = 8001
    log_level: str = "INFO"

    # ML Model settings
    min_training_samples: int = 1000
    safety_accuracy_threshold: float = 0.85
    safety_consecutive_failures_limit: int = 3

    # Drift detection settings
    drift_check_interval_seconds: int = 300
    drift_window_size: int = 1000
    drift_threshold: float = 0.2  # PSI threshold for drift detection
    min_predictions_for_drift: int = 10  # Minimum predictions per minute

    # MLflow settings
    mlflow_tracking_uri: str = "sqlite:///mlruns/mlflow.db"
    mlflow_model_name: str = "governance_model"
    mlflow_champion_alias: str = "champion"

    # Integration URLs
    redis_url: str = DEFAULT_REDIS_URL
    kafka_bootstrap_servers: str = "kafka:29092"
    agent_bus_url: str = "http://agent-bus:8000"
    opa_url: str = "http://opa:8181"

    # Feature flags
    enable_prometheus: bool = True
    enable_kafka: bool = False
    enable_redis_cache: bool = True
    enable_drift_detection: bool = True
    enable_safety_bounds: bool = True

    # Optional dependency injections (set to None for defaults)
    # Note: These are typed as Any to avoid circular imports at runtime
    model_manager: Optional[Any] = None
    drift_detector: Optional[Any] = None
    mlflow_registry: Optional[Any] = None

    # Constitutional settings
    constitutional_hash: str = field(default=CONSTITUTIONAL_HASH)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        # Ensure constitutional hash is always set
        if not self.constitutional_hash:
            self.constitutional_hash = CONSTITUTIONAL_HASH

        # Validate thresholds
        if not 0.0 <= self.safety_accuracy_threshold <= 1.0:
            raise ValueError(
                f"safety_accuracy_threshold must be between 0 and 1, got {self.safety_accuracy_threshold}"
            )

        if not 0.0 <= self.drift_threshold <= 1.0:
            raise ValueError(f"drift_threshold must be between 0 and 1, got {self.drift_threshold}")

        if self.min_training_samples <= 0:
            raise ValueError(
                f"min_training_samples must be positive, got {self.min_training_samples}"
            )

        if self.drift_check_interval_seconds <= 0:
            raise ValueError(
                f"drift_check_interval_seconds must be positive, got {self.drift_check_interval_seconds}"
            )

    @classmethod
    def from_environment(cls) -> "AdaptiveLearningConfig":
        """Create configuration from environment variables.

        Environment variables:
            ADAPTIVE_LEARNING_PORT: Service port (default: 8001)
            LOG_LEVEL: Logging level (default: INFO)
            MIN_TRAINING_SAMPLES: Minimum samples before model is active
            SAFETY_ACCURACY_THRESHOLD: Accuracy threshold for safety bounds
            SAFETY_CONSECUTIVE_FAILURES_LIMIT: Max consecutive safety failures
            DRIFT_CHECK_INTERVAL_SECONDS: Interval for drift checks
            DRIFT_WINDOW_SIZE: Window size for drift detection
            DRIFT_THRESHOLD: PSI threshold for drift detection
            MIN_PREDICTIONS_FOR_DRIFT: Minimum predictions for drift check
            MLFLOW_TRACKING_URI: MLflow tracking URI
            MLFLOW_MODEL_NAME: Model name in MLflow registry
            REDIS_URL: Redis connection URL
            KAFKA_BOOTSTRAP: Kafka bootstrap servers
            AGENT_BUS_URL: Agent Bus service URL
            OPA_URL: OPA service URL
            PROMETHEUS_ENABLED: Enable Prometheus metrics (true/false)
            KAFKA_ENABLED: Enable Kafka integration (true/false)
            REDIS_CACHE_ENABLED: Enable Redis caching (true/false)
            DRIFT_DETECTION_ENABLED: Enable drift detection (true/false)
            SAFETY_BOUNDS_ENABLED: Enable safety bounds (true/false)
        """
        import os

        def _parse_bool(value: Optional[str], default: bool = False) -> bool:
            if value is None:
                return default
            return value.lower() in ("true", "1", "yes", "on")

        def _parse_int(value: Optional[str], default: int) -> int:
            if value is None:
                return default
            try:
                return int(value)
            except ValueError:
                return default

        def _parse_float(value: Optional[str], default: float) -> float:
            if value is None:
                return default
            try:
                return float(value)
            except ValueError:
                return default

        return cls(
            # Server settings
            port=_parse_int(os.environ.get("ADAPTIVE_LEARNING_PORT"), 8001),
            log_level=os.environ.get("LOG_LEVEL", "INFO"),
            # ML Model settings
            min_training_samples=_parse_int(os.environ.get("MIN_TRAINING_SAMPLES"), 1000),
            safety_accuracy_threshold=_parse_float(
                os.environ.get("SAFETY_ACCURACY_THRESHOLD"), 0.85
            ),
            safety_consecutive_failures_limit=_parse_int(
                os.environ.get("SAFETY_CONSECUTIVE_FAILURES_LIMIT"), 3
            ),
            # Drift detection settings
            drift_check_interval_seconds=_parse_int(
                os.environ.get("DRIFT_CHECK_INTERVAL_SECONDS"), 300
            ),
            drift_window_size=_parse_int(os.environ.get("DRIFT_WINDOW_SIZE"), 1000),
            drift_threshold=_parse_float(os.environ.get("DRIFT_THRESHOLD"), 0.2),
            min_predictions_for_drift=_parse_int(os.environ.get("MIN_PREDICTIONS_FOR_DRIFT"), 10),
            # MLflow settings
            mlflow_tracking_uri=os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlruns/mlflow.db"),
            mlflow_model_name=os.environ.get("MLFLOW_MODEL_NAME", "governance_model"),
            # Integration URLs
            redis_url=os.environ.get("REDIS_URL", DEFAULT_REDIS_URL),
            kafka_bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP", "kafka:29092"),
            agent_bus_url=os.environ.get("AGENT_BUS_URL", "http://agent-bus:8000"),
            opa_url=os.environ.get("OPA_URL", "http://opa:8181"),
            # Feature flags
            enable_prometheus=_parse_bool(os.environ.get("PROMETHEUS_ENABLED"), True),
            enable_kafka=_parse_bool(os.environ.get("KAFKA_ENABLED"), False),
            enable_redis_cache=_parse_bool(os.environ.get("REDIS_CACHE_ENABLED"), True),
            enable_drift_detection=_parse_bool(os.environ.get("DRIFT_DETECTION_ENABLED"), True),
            enable_safety_bounds=_parse_bool(os.environ.get("SAFETY_BOUNDS_ENABLED"), True),
        )

    @classmethod
    def for_testing(cls) -> "AdaptiveLearningConfig":
        """Create a minimal configuration for unit testing.

        Disables all optional features for fast, isolated testing.
        """
        return cls(
            min_training_samples=10,  # Low threshold for quick tests
            safety_accuracy_threshold=0.5,  # Relaxed for testing
            drift_check_interval_seconds=60,  # Shorter interval for tests
            drift_window_size=100,  # Smaller window for tests
            enable_prometheus=False,
            enable_kafka=False,
            enable_redis_cache=False,
            enable_drift_detection=False,
            enable_safety_bounds=False,
        )

    @classmethod
    def for_production(cls) -> "AdaptiveLearningConfig":
        """Create a configuration suitable for production use.

        Enables all production features with conservative safety settings.
        """
        return cls(
            min_training_samples=1000,
            safety_accuracy_threshold=0.85,
            safety_consecutive_failures_limit=3,
            drift_check_interval_seconds=300,
            drift_window_size=1000,
            drift_threshold=0.2,
            enable_prometheus=True,
            enable_kafka=True,
            enable_redis_cache=True,
            enable_drift_detection=True,
            enable_safety_bounds=True,
        )

    def with_model_manager(self, model_manager: Any) -> "AdaptiveLearningConfig":
        """Return a new configuration with the specified model manager.

        Builder pattern method for fluent configuration.
        Uses dataclasses.replace() for immutable field updates.
        """
        return replace(self, model_manager=model_manager)

    def with_drift_detector(self, drift_detector: Any) -> "AdaptiveLearningConfig":
        """Return a new configuration with the specified drift detector.

        Builder pattern method for fluent configuration.
        Uses dataclasses.replace() for immutable field updates.
        """
        return replace(self, drift_detector=drift_detector)

    def with_mlflow_registry(self, mlflow_registry: Any) -> "AdaptiveLearningConfig":
        """Return a new configuration with the specified MLflow registry.

        Builder pattern method for fluent configuration.
        Uses dataclasses.replace() for immutable field updates.
        """
        return replace(self, mlflow_registry=mlflow_registry)

    def to_dict(self) -> dict:
        """Convert configuration to dictionary for logging/serialization."""
        return {
            # Server settings
            "port": self.port,
            "log_level": self.log_level,
            # ML Model settings
            "min_training_samples": self.min_training_samples,
            "safety_accuracy_threshold": self.safety_accuracy_threshold,
            "safety_consecutive_failures_limit": self.safety_consecutive_failures_limit,
            # Drift detection settings
            "drift_check_interval_seconds": self.drift_check_interval_seconds,
            "drift_window_size": self.drift_window_size,
            "drift_threshold": self.drift_threshold,
            "min_predictions_for_drift": self.min_predictions_for_drift,
            # MLflow settings
            "mlflow_tracking_uri": self.mlflow_tracking_uri,
            "mlflow_model_name": self.mlflow_model_name,
            "mlflow_champion_alias": self.mlflow_champion_alias,
            # Integration URLs
            "redis_url": self.redis_url,
            "kafka_bootstrap_servers": self.kafka_bootstrap_servers,
            "agent_bus_url": self.agent_bus_url,
            "opa_url": self.opa_url,
            # Feature flags
            "enable_prometheus": self.enable_prometheus,
            "enable_kafka": self.enable_kafka,
            "enable_redis_cache": self.enable_redis_cache,
            "enable_drift_detection": self.enable_drift_detection,
            "enable_safety_bounds": self.enable_safety_bounds,
            # Constitutional settings
            "constitutional_hash": self.constitutional_hash,
            # Dependency injection status
            "has_custom_model_manager": self.model_manager is not None,
            "has_custom_drift_detector": self.drift_detector is not None,
            "has_custom_mlflow_registry": self.mlflow_registry is not None,
        }
