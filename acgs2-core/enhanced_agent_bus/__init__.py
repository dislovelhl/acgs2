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
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    # Fallback for standalone usage
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Refactored modules for cleaner architecture
from .config import BusConfiguration
from .core import (
    EnhancedAgentBus,
    MessageProcessor,
)
from .exceptions import (
    AgentAlreadyRegisteredError,
    # Base
    AgentBusError,
    AgentCapabilityError,
    # Agent
    AgentError,
    AgentNotRegisteredError,
    BusAlreadyStartedError,
    BusNotStartedError,
    # Bus Operations
    BusOperationError,
    # Configuration
    ConfigurationError,
    # Constitutional
    ConstitutionalError,
    ConstitutionalHashMismatchError,
    ConstitutionalValidationError,
    # Deliberation
    DeliberationError,
    DeliberationTimeoutError,
    HandlerExecutionError,
    MessageDeliveryError,
    # Message
    MessageError,
    MessageRoutingError,
    MessageTimeoutError,
    MessageValidationError,
    OPAConnectionError,
    OPANotInitializedError,
    # Policy/OPA
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
from .models import (
    CONSTITUTIONAL_HASH as MODEL_HASH,
)
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
from .validation_integration_example import (
    IntegratedValidationSystem,
)
from .validators import (
    ValidationResult,
)

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
]
