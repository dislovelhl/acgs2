"""
ACGS-2 Enhanced Agent Bus - Core Module (Backward Compatibility Facade)
Constitutional Hash: cdd01ef066bc6cf2

This module provides backward compatibility by re-exporting classes from
refactored modules. New code should import directly from:
- enhanced_agent_bus.message_processor (MessageProcessor)
- enhanced_agent_bus.agent_bus (EnhancedAgentBus, get_agent_bus, reset_agent_bus)
"""

# Re-export from refactored modules for backward compatibility
try:
    from .agent_bus import DEFAULT_REDIS_URL, EnhancedAgentBus, get_agent_bus, reset_agent_bus
    from .message_processor import MessageProcessor
except (ImportError, ValueError):
    from agent_bus import (  # type: ignore
        DEFAULT_REDIS_URL,
        EnhancedAgentBus,
        get_agent_bus,
        reset_agent_bus,
    )
    from message_processor import MessageProcessor  # type: ignore

# Re-export models and interfaces
try:
    from .interfaces import AgentRegistry, MessageRouter, ProcessingStrategy, ValidationStrategy
    from .models import (
        CONSTITUTIONAL_HASH,
        AgentMessage,
        DecisionLog,
        MessagePriority,  # DEPRECATED: Use Priority instead (v3.0.0 removal)
        MessageStatus,
        MessageType,
        Priority,
    )
    from .registry import (
        CompositeProcessingStrategy,
        DirectMessageRouter,
        DynamicPolicyProcessingStrategy,
        DynamicPolicyValidationStrategy,
        InMemoryAgentRegistry,
        OPAProcessingStrategy,
        OPAValidationStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        RustValidationStrategy,
        StaticHashValidationStrategy,
    )
    from .validators import ValidationResult
except ImportError:
    # Fallback for direct execution or testing
    from interfaces import (  # type: ignore
        AgentRegistry,
        MessageRouter,
        ProcessingStrategy,
        ValidationStrategy,
    )
    from models import (  # type: ignore
        CONSTITUTIONAL_HASH,
        AgentMessage,
        DecisionLog,
        MessagePriority,  # DEPRECATED: Use Priority instead (v3.0.0 removal)
        MessageStatus,
        MessageType,
        Priority,
    )
    from registry import (  # type: ignore
        DirectMessageRouter,
        DynamicPolicyProcessingStrategy,
        DynamicPolicyValidationStrategy,
        InMemoryAgentRegistry,
        OPAProcessingStrategy,
        OPAValidationStrategy,
        PythonProcessingStrategy,
        RustProcessingStrategy,
        StaticHashValidationStrategy,
    )
    from validators import ValidationResult  # type: ignore

# Re-export feature flags
try:
    from src.core.shared.metrics import MESSAGES_TOTAL

    METRICS_ENABLED = True
except ImportError:
    METRICS_ENABLED = False

try:
    from src.core.shared.circuit_breaker import get_circuit_breaker

    CIRCUIT_BREAKER_ENABLED = True
except ImportError:
    CIRCUIT_BREAKER_ENABLED = False

try:
    import src.core.enhanced_agent_bus_rust as rust_bus

    USE_RUST = True
except ImportError:
    USE_RUST = False
    rust_bus = None

# Re-export metering integration
try:
    from .metering_integration import (
        METERING_AVAILABLE,
        AsyncMeteringQueue,
        MeteringConfig,
        MeteringHooks,
        MeteringMixin,
        get_metering_hooks,
        get_metering_queue,
        metered_operation,
        reset_metering,
    )
except ImportError:
    METERING_AVAILABLE = False
    MeteringConfig = None
    AsyncMeteringQueue = None
    MeteringHooks = None
    MeteringMixin = None
    get_metering_queue = None
    get_metering_hooks = None
    reset_metering = None
    metered_operation = None

# Backward compatibility alias
ConstitutionalValidationStrategy = StaticHashValidationStrategy

__all__ = [
    # Constants
    "CONSTITUTIONAL_HASH",
    "USE_RUST",
    "DEFAULT_REDIS_URL",
    "METRICS_ENABLED",
    "CIRCUIT_BREAKER_ENABLED",
    "METERING_AVAILABLE",
    # Core Classes
    "MessageProcessor",
    "EnhancedAgentBus",
    # Models
    "AgentMessage",
    "MessageType",
    "Priority",
    "MessagePriority",  # DEPRECATED: Use Priority instead (v3.0.0 removal)
    "MessageStatus",
    "DecisionLog",
    "ValidationResult",
    # Protocol Interfaces (DI)
    "AgentRegistry",
    "MessageRouter",
    "ValidationStrategy",
    "ProcessingStrategy",
    # Default Implementations (DI)
    "InMemoryAgentRegistry",
    "DirectMessageRouter",
    "ConstitutionalValidationStrategy",
    "StaticHashValidationStrategy",
    "DynamicPolicyValidationStrategy",
    # Processing Strategies (DI)
    "PythonProcessingStrategy",
    "RustProcessingStrategy",
    "DynamicPolicyProcessingStrategy",
    "OPAProcessingStrategy",
    "OPAValidationStrategy",
    "CompositeProcessingStrategy",
    # Metering Integration
    "MeteringConfig",
    "AsyncMeteringQueue",
    "MeteringHooks",
    "MeteringMixin",
    "get_metering_queue",
    "get_metering_hooks",
    "reset_metering",
    "metered_operation",
    # Functions
    "get_agent_bus",
    "reset_agent_bus",
]
