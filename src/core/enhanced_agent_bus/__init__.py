"""
ACGS-2 Enhanced Agent Communication Bus
Constitutional Hash: cdd01ef066bc6cf2

High-performance, multi-tenant agent communication infrastructure for ACGS-2
constitutional governance platform.
"""

__version__ = "2.0.0"
__constitutional_hash__ = "cdd01ef066bc6cf2"

# Import centralized constitutional hash from shared module
try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    # Fallback for standalone usage
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

from typing import Any

# Refactored modules for cleaner architecture
from .config import BusConfiguration
from .core import EnhancedAgentBus, MessageProcessor
from .examples.validation_integration_example import IntegratedValidationSystem
from .exceptions import (  # Base; Agent; Bus Operations; Configuration; Constitutional; Deliberation; Message; Policy/OPA
    AgentAlreadyRegisteredError,
    AgentBusError,
    AgentCapabilityError,
    AgentError,
    AgentNotRegisteredError,
    BusAlreadyStartedError,
    BusNotStartedError,
    BusOperationError,
    ConfigurationError,
    ConstitutionalError,
    ConstitutionalHashMismatchError,
    ConstitutionalValidationError,
    DeliberationError,
    DeliberationTimeoutError,
    HandlerExecutionError,
    MessageDeliveryError,
    MessageError,
    MessageRoutingError,
    MessageTimeoutError,
    MessageValidationError,
    OPAConnectionError,
    OPANotInitializedError,
    PolicyError,
    PolicyEvaluationError,
    PolicyNotFoundError,
    ReviewConsensusError,
    SignatureCollectionError,
)
from .imports import (
    CIRCUIT_BREAKER_ENABLED,
    DELIBERATION_AVAILABLE,
    METERING_AVAILABLE,
    METRICS_ENABLED,
    USE_RUST,
    get_import_status,
)
from .interfaces import (
    AgentRegistry,
    MessageHandler,
    MessageRouter,
    MetricsCollector,
    ValidationStrategy,
)
from .metering_manager import MeteringManager, create_metering_manager
from .models import CONSTITUTIONAL_HASH as MODEL_HASH
from .models import (
    AgentMessage,
    MessagePriority,  # DEPRECATED: Use Priority instead (v3.0.0 removal)
    MessageStatus,
    MessageType,
    Priority,
    RoutingContext,
    ValidationStatus,
)
from .registry import (
    CapabilityBasedRouter,
    CompositeValidationStrategy,
    DirectMessageRouter,
    DynamicPolicyValidationStrategy,
    InMemoryAgentRegistry,
    RedisAgentRegistry,
    RustValidationStrategy,
    StaticHashValidationStrategy,
)
from .runtime_security import (
    RuntimeSecurityConfig,
    RuntimeSecurityScanner,
    SecurityEvent,
    SecurityEventType,
    SecurityScanResult,
    SecuritySeverity,
    get_runtime_security_scanner,
    scan_content,
)
from .siem_integration import (
    AlertLevel,
    AlertManager,
    AlertThreshold,
    EventCorrelator,
    SIEMConfig,
    SIEMEventFormatter,
    SIEMFormat,
    SIEMIntegration,
    close_siem,
    get_siem_integration,
    initialize_siem,
    log_security_event,
    security_audit,
)
from .validators import ValidationResult

# Cache Warming Integration for FastAPI startup
# Import cache warming module for pre-populating caches at service startup
try:
    from src.core.shared.cache_warming import (
        CacheWarmer,
        WarmingConfig,
        WarmingProgress,
        WarmingResult,
        WarmingStatus,
        get_cache_warmer,
        reset_cache_warmer,
        warm_cache_on_startup,
    )

    CACHE_WARMING_AVAILABLE = True
except ImportError:
    # Fallback for environments without cache warming module
    CACHE_WARMING_AVAILABLE = False
    CacheWarmer = Any  # type: ignore[assignment, misc]
    WarmingConfig = Any  # type: ignore[assignment, misc]
    WarmingProgress = Any  # type: ignore[assignment, misc]
    WarmingResult = Any  # type: ignore[assignment, misc]
    WarmingStatus = Any  # type: ignore[assignment, misc]
    get_cache_warmer = Any  # type: ignore[assignment, misc]
    reset_cache_warmer = Any  # type: ignore[assignment, misc]
    warm_cache_on_startup = Any  # type: ignore[assignment, misc]

__all__ = [
    "CONSTITUTIONAL_HASH",
    # Refactored Configuration
    "BusConfiguration",
    "MeteringManager",
    "create_metering_manager",
    "get_import_status",
    "METRICS_ENABLED",
    "CIRCUIT_BREAKER_ENABLED",
    "DELIBERATION_AVAILABLE",
    "USE_RUST",
    "METERING_AVAILABLE",
    # Models
    "AgentMessage",
    "MessageType",
    "Priority",
    "MessagePriority",  # DEPRECATED: Use Priority instead (v3.0.0 removal)
    "MessageStatus",
    "ValidationStatus",
    "RoutingContext",
    # Core
    "EnhancedAgentBus",
    "MessageProcessor",
    "ValidationResult",
    "IntegratedValidationSystem",
    # Protocol Interfaces (DI)
    "AgentRegistry",
    "MessageRouter",
    "ValidationStrategy",
    "MessageHandler",
    "MetricsCollector",
    # Default Implementations (DI)
    "InMemoryAgentRegistry",
    "DirectMessageRouter",
    "CapabilityBasedRouter",
    "StaticHashValidationStrategy",
    "DynamicPolicyValidationStrategy",
    "RustValidationStrategy",
    "CompositeValidationStrategy",
    "RedisAgentRegistry",
    # Exceptions - Base
    "AgentBusError",
    # Exceptions - Constitutional
    "ConstitutionalError",
    "ConstitutionalHashMismatchError",
    "ConstitutionalValidationError",
    # Exceptions - Message
    "MessageError",
    "MessageValidationError",
    "MessageDeliveryError",
    "MessageTimeoutError",
    "MessageRoutingError",
    # Exceptions - Agent
    "AgentError",
    "AgentNotRegisteredError",
    "AgentAlreadyRegisteredError",
    "AgentCapabilityError",
    # Exceptions - Policy/OPA
    "PolicyError",
    "PolicyEvaluationError",
    "PolicyNotFoundError",
    "OPAConnectionError",
    "OPANotInitializedError",
    # Exceptions - Deliberation
    "DeliberationError",
    "DeliberationTimeoutError",
    "SignatureCollectionError",
    "ReviewConsensusError",
    # Exceptions - Bus Operations
    "BusOperationError",
    "BusNotStartedError",
    "BusAlreadyStartedError",
    "HandlerExecutionError",
    # Exceptions - Configuration
    "ConfigurationError",
    # Runtime Security
    "RuntimeSecurityConfig",
    "RuntimeSecurityScanner",
    "SecurityEvent",
    "SecurityEventType",
    "SecurityScanResult",
    "SecuritySeverity",
    "get_runtime_security_scanner",
    "scan_content",
    # SIEM Integration
    "SIEMFormat",
    "SIEMConfig",
    "SIEMEventFormatter",
    "SIEMIntegration",
    "AlertLevel",
    "AlertThreshold",
    "AlertManager",
    "EventCorrelator",
    "initialize_siem",
    "close_siem",
    "get_siem_integration",
    "log_security_event",
    "security_audit",
    # Cache Warming
    "CACHE_WARMING_AVAILABLE",
    "CacheWarmer",
    "WarmingConfig",
    "WarmingProgress",
    "WarmingResult",
    "WarmingStatus",
    "get_cache_warmer",
    "reset_cache_warmer",
    "warm_cache_on_startup",
]
