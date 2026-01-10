"""
ACGS-2 Enhanced Agent Bus - Optional Imports Management
Constitutional Hash: cdd01ef066bc6cf2

Centralizes optional import handling with graceful fallbacks.
This follows the Facade pattern to hide import complexity from the main modules.
"""

import logging
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# =============================================================================
# Feature Availability Flags (set during import resolution)
# =============================================================================

METRICS_ENABLED: bool = False
OTEL_ENABLED: bool = False
CIRCUIT_BREAKER_ENABLED: bool = False
POLICY_CLIENT_AVAILABLE: bool = False
DELIBERATION_AVAILABLE: bool = False
CRYPTO_AVAILABLE: bool = False
CONFIG_AVAILABLE: bool = False
AUDIT_CLIENT_AVAILABLE: bool = False
OPA_CLIENT_AVAILABLE: bool = False
USE_RUST: bool = False
METERING_AVAILABLE: bool = False
MACI_AVAILABLE: bool = False

# =============================================================================
# Optional Module References (None if unavailable)
# =============================================================================

# Prometheus metrics
MESSAGE_QUEUE_DEPTH: Optional[Any] = None
set_service_info: Optional[Callable] = None

# OpenTelemetry
tracer: Optional[Any] = None
meter: Optional[Any] = None
QUEUE_DEPTH: Optional[Any] = None

# Circuit breaker
get_circuit_breaker: Optional[Callable] = None
circuit_breaker_health_check: Optional[Callable] = None
initialize_core_circuit_breakers: Optional[Callable] = None
CircuitBreakerConfig: Optional[type] = None

# Policy client
PolicyClient: Optional[type] = None
get_policy_client: Optional[Callable] = None

# Deliberation layer
VotingService: Optional[type] = None
VotingStrategy: Optional[type] = None
DeliberationQueue: Optional[type] = None

# Crypto service
CryptoService: Optional[type] = None

# Settings/config
settings: Optional[Any] = None

# Audit client
AuditClient: Optional[type] = None

# OPA client
OPAClient: Optional[type] = None
get_opa_client: Optional[Callable] = None

# Rust implementation
rust_bus: Optional[Any] = None

# Metering
MeteringHooks: Optional[type] = None
MeteringConfig: Optional[type] = None
AsyncMeteringQueue: Optional[type] = None
get_metering_hooks: Optional[Callable] = None
get_metering_queue: Optional[Callable] = None

# MACI enforcement
MACIEnforcer: Optional[type] = None
MACIRole: Optional[type] = None
MACIRoleRegistry: Optional[type] = None

# =============================================================================
# Import Resolution Functions
# =============================================================================


def _init_prometheus_metrics() -> None:
    """Initialize Prometheus metrics with fallback."""
    global METRICS_ENABLED, MESSAGE_QUEUE_DEPTH, set_service_info
    try:
        from core.shared.metrics import MESSAGE_QUEUE_DEPTH as _mqd
        from core.shared.metrics import set_service_info as _ssi

        MESSAGE_QUEUE_DEPTH = _mqd
        set_service_info = _ssi
        METRICS_ENABLED = True
    except ImportError:
        METRICS_ENABLED = False


def _init_opentelemetry() -> None:
    """Initialize OpenTelemetry with fallback."""
    global OTEL_ENABLED, tracer, meter, QUEUE_DEPTH
    try:
        from opentelemetry import metrics, trace

        tracer = trace.get_tracer(__name__)
        meter = metrics.get_meter(__name__)
        QUEUE_DEPTH = meter.create_up_down_counter(
            "acgs2.queue.depth", description="Current message queue depth", unit="1"
        )
        OTEL_ENABLED = True
    except ImportError:
        OTEL_ENABLED = False
        tracer = None
        meter = None
        QUEUE_DEPTH = None


def _init_circuit_breaker() -> None:
    """Initialize circuit breaker with fallback."""
    global CIRCUIT_BREAKER_ENABLED, get_circuit_breaker
    global circuit_breaker_health_check, initialize_core_circuit_breakers
    global CircuitBreakerConfig
    try:
        from core.shared.circuit_breaker import CircuitBreakerConfig as _cbc
        from core.shared.circuit_breaker import circuit_breaker_health_check as _cbhc
        from core.shared.circuit_breaker import get_circuit_breaker as _gcb
        from core.shared.circuit_breaker import initialize_core_circuit_breakers as _icb

        get_circuit_breaker = _gcb
        circuit_breaker_health_check = _cbhc
        initialize_core_circuit_breakers = _icb
        CircuitBreakerConfig = _cbc
        CIRCUIT_BREAKER_ENABLED = True
    except ImportError:
        CIRCUIT_BREAKER_ENABLED = False


def _init_policy_client() -> None:
    """Initialize policy client with fallback."""
    global POLICY_CLIENT_AVAILABLE, PolicyClient, get_policy_client
    try:
        try:
            from .policy_client import PolicyClient as _pc
            from .policy_client import get_policy_client as _gpc
        except ImportError:
            from policy_client import PolicyClient as _pc
            from policy_client import get_policy_client as _gpc
        PolicyClient = _pc
        get_policy_client = _gpc
        POLICY_CLIENT_AVAILABLE = True
    except ImportError:
        POLICY_CLIENT_AVAILABLE = False
        PolicyClient = None

        def _null_get_policy_client(fail_closed: Optional[bool] = None):
            return None

        get_policy_client = _null_get_policy_client


def _init_deliberation_layer() -> None:
    """Initialize deliberation layer with fallback."""
    global DELIBERATION_AVAILABLE, VotingService, VotingStrategy, DeliberationQueue
    try:
        try:
            from .deliberation_layer.deliberation_queue import DeliberationQueue as _dq
            from .deliberation_layer.voting_service import VotingService as _vs
            from .deliberation_layer.voting_service import VotingStrategy as _vst
        except ImportError:
            from deliberation_layer.deliberation_queue import DeliberationQueue as _dq
            from deliberation_layer.voting_service import VotingService as _vs
            from deliberation_layer.voting_service import VotingStrategy as _vst
        VotingService = _vs
        VotingStrategy = _vst
        DeliberationQueue = _dq
        DELIBERATION_AVAILABLE = True
    except ImportError:
        DELIBERATION_AVAILABLE = False


def _init_crypto_service() -> None:
    """Initialize crypto service with fallback."""
    global CRYPTO_AVAILABLE, CryptoService
    try:
        from core.services.policy_registry.app.services.crypto_service import CryptoService as _cs

        CryptoService = _cs
        CRYPTO_AVAILABLE = True
    except ImportError:
        try:
            from ..services.crypto_service import CryptoService as _cs

            CryptoService = _cs
            CRYPTO_AVAILABLE = True
        except ImportError:
            CRYPTO_AVAILABLE = False
            CryptoService = None


def _init_settings() -> None:
    """Initialize settings/config with fallback."""
    global CONFIG_AVAILABLE, settings
    try:
        from core.shared.config import settings as _s

        settings = _s
        CONFIG_AVAILABLE = True
    except ImportError:
        CONFIG_AVAILABLE = False
        settings = None


def _init_audit_client() -> None:
    """Initialize audit client with fallback."""
    global AUDIT_CLIENT_AVAILABLE, AuditClient
    try:
        from core.shared.audit_client import AuditClient as _ac

        AuditClient = _ac
        AUDIT_CLIENT_AVAILABLE = True
    except ImportError:
        try:
            try:
                from .audit_client import AuditClient as _ac
            except ImportError:
                from audit_client import AuditClient as _ac
            AuditClient = _ac
            AUDIT_CLIENT_AVAILABLE = True
        except ImportError:
            AUDIT_CLIENT_AVAILABLE = False
            AuditClient = None


def _init_opa_client() -> None:
    """Initialize OPA client with fallback."""
    global OPA_CLIENT_AVAILABLE, OPAClient, get_opa_client
    try:
        try:
            from .opa_client import OPAClient as _oc
            from .opa_client import get_opa_client as _goc
        except ImportError:
            from opa_client import OPAClient as _oc
            from opa_client import get_opa_client as _goc
        OPAClient = _oc
        get_opa_client = _goc
        OPA_CLIENT_AVAILABLE = True
    except ImportError:
        OPA_CLIENT_AVAILABLE = False
        OPAClient = None

        def _null_get_opa_client():
            return None

        get_opa_client = _null_get_opa_client


def _init_rust_backend() -> None:
    """Initialize Rust backend with fallback."""
    global USE_RUST, rust_bus
    try:
        import src.core.enhanced_agent_bus_rust as _rb

        rust_bus = _rb
        USE_RUST = True
    except ImportError:
        USE_RUST = False
        rust_bus = None


def _init_metering() -> None:
    """Initialize metering integration with fallback."""
    global METERING_AVAILABLE, MeteringHooks, MeteringConfig
    global AsyncMeteringQueue, get_metering_hooks, get_metering_queue
    try:
        try:
            from .metering_integration import METERING_AVAILABLE as _ma
            from .metering_integration import AsyncMeteringQueue as _amq
            from .metering_integration import MeteringConfig as _mc
            from .metering_integration import MeteringHooks as _mh
            from .metering_integration import get_metering_hooks as _gmh
            from .metering_integration import get_metering_queue as _gmq
        except ImportError:
            from metering_integration import METERING_AVAILABLE as _ma
            from metering_integration import AsyncMeteringQueue as _amq
            from metering_integration import MeteringConfig as _mc
            from metering_integration import MeteringHooks as _mh
            from metering_integration import get_metering_hooks as _gmh
            from metering_integration import get_metering_queue as _gmq
        MeteringHooks = _mh
        MeteringConfig = _mc
        AsyncMeteringQueue = _amq
        get_metering_hooks = _gmh
        get_metering_queue = _gmq
        METERING_AVAILABLE = _ma
    except ImportError:
        METERING_AVAILABLE = False
        MeteringHooks = None
        MeteringConfig = None
        AsyncMeteringQueue = None
        get_metering_hooks = None
        get_metering_queue = None


def _init_maci() -> None:
    """Initialize MACI enforcement with fallback stub classes."""
    global MACI_AVAILABLE, MACIEnforcer, MACIRole, MACIRoleRegistry
    try:
        try:
            from .maci_enforcement import MACIEnforcer as _me
            from .maci_enforcement import MACIRole as _mr
            from .maci_enforcement import MACIRoleRegistry as _mrr
        except ImportError:
            from maci_enforcement import MACIEnforcer as _me
            from maci_enforcement import MACIRole as _mr
            from maci_enforcement import MACIRoleRegistry as _mrr
        MACIEnforcer = _me
        MACIRole = _mr
        MACIRoleRegistry = _mrr
        MACI_AVAILABLE = True
    except ImportError:
        MACI_AVAILABLE = True  # Stubs available

        class _StubMACIRole:
            """Stub MACI role for when enforcement module unavailable."""

            WORKER = "worker"
            CRITIC = "critic"
            SECURITY_AUDITOR = "security_auditor"
            MONITOR = "monitor"

        class _StubMACIEnforcer:
            """Stub MACI enforcer for when enforcement module unavailable."""

            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            async def validate_action(self, *args: Any, **kwargs: Any) -> bool:
                return True

        class _StubMACIRoleRegistry:
            """Stub MACI role registry for when enforcement module unavailable."""

            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            async def register_agent(self, *args: Any, **kwargs: Any) -> None:
                pass

            async def get_role(self, *args: Any, **kwargs: Any) -> str:
                return "worker"

        MACIRole = _StubMACIRole
        MACIEnforcer = _StubMACIEnforcer
        MACIRoleRegistry = _StubMACIRoleRegistry


def _init_redis_config() -> str:
    """Initialize Redis config and return default URL."""
    try:
        from core.shared.redis_config import get_redis_url

        return get_redis_url()
    except ImportError:
        return "redis://localhost:6379"


# =============================================================================
# Module Initialization
# =============================================================================


def initialize_all_imports() -> None:
    """Initialize all optional imports at module load time.

    Call this once at application startup to resolve all optional dependencies.
    """
    _init_prometheus_metrics()
    _init_opentelemetry()
    _init_circuit_breaker()
    _init_policy_client()
    _init_deliberation_layer()
    _init_crypto_service()
    _init_settings()
    _init_audit_client()
    _init_opa_client()
    _init_rust_backend()
    _init_metering()
    _init_maci()


# Initialize on module load (maintains backward compatibility)
DEFAULT_REDIS_URL: str = _init_redis_config()
initialize_all_imports()

# =============================================================================
# Generic Import Utilities (for reducing redundant try/except patterns)
# =============================================================================


def try_import(
    relative_path: str,
    absolute_path: str,
    names: list[str],
) -> tuple[bool, dict[str, Any]]:
    """Try importing from relative path first, then absolute path.

    This utility reduces the common pattern of:
        try:
            from .module import Something
        except ImportError:
            from module import Something

    Args:
        relative_path: Relative import path (e.g., ".models")
        absolute_path: Absolute import path fallback (e.g., "models")
        names: List of names to import from the module

    Returns:
        Tuple of (success: bool, imports: dict mapping name to imported object)

    Example:
        success, imports = try_import(".models", "models", ["AgentMessage", "Priority"])
        if success:
            AgentMessage = imports["AgentMessage"]
            Priority = imports["Priority"]
    """
    import importlib

    result: dict[str, Any] = {}

    # Try relative import first
    try:
        module = importlib.import_module(relative_path, package=__package__)
        for name in names:
            result[name] = getattr(module, name)
        return True, result
    except (ImportError, AttributeError):
        pass

    # Fall back to absolute import
    try:
        module = importlib.import_module(absolute_path)
        for name in names:
            result[name] = getattr(module, name)
        return True, result
    except (ImportError, AttributeError):
        pass

    return False, result


def import_with_fallback(
    module_paths: list[str],
    names: list[str],
    default_values: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Import names from the first available module in the paths list.

    Args:
        module_paths: List of module paths to try in order
        names: List of names to import from the module
        default_values: Optional dict of default values if all imports fail

    Returns:
        Dict mapping name to imported object (or default value)

    Example:
        imports = import_with_fallback(
            ["shared.constants", "enhanced_agent_bus.models"],
            ["CONSTITUTIONAL_HASH"],
            {"CONSTITUTIONAL_HASH": "cdd01ef066bc6cf2"}
        )
        CONSTITUTIONAL_HASH = imports["CONSTITUTIONAL_HASH"]
    """
    import importlib

    for module_path in module_paths:
        try:
            module = importlib.import_module(module_path)
            result = {}
            for name in names:
                result[name] = getattr(module, name)
            return result
        except (ImportError, AttributeError):
            continue

    # Return defaults if all imports fail
    if default_values:
        return default_values
    return {name: None for name in names}


def optional_import(module_path: str, name: str, default: Any = None) -> Any:
    """Import a single name from a module, returning default if unavailable.

    This is the simplest utility for optional dependencies.

    Args:
        module_path: Module path to import from
        name: Name to import from the module
        default: Default value if import fails

    Returns:
        Imported object or default value

    Example:
        get_circuit_breaker = optional_import("shared.circuit_breaker", "get_circuit_breaker")
        if get_circuit_breaker:
            breaker = get_circuit_breaker("my-service")
    """
    import importlib

    try:
        module = importlib.import_module(module_path)
        return getattr(module, name, default)
    except (ImportError, AttributeError):
        return default


def try_relative_import(
    relative_module: str,
    absolute_module: str,
    name: str,
    default: Any = None,
) -> Any:
    """Try relative import first, then absolute, returning default if both fail.

    Simplest form for single-name imports with relative/absolute fallback.

    Args:
        relative_module: Relative module path (e.g., ".models")
        absolute_module: Absolute module path (e.g., "models")
        name: Name to import
        default: Default value if all imports fail

    Returns:
        Imported object or default value

    Example:
        ValidationResult = try_relative_import(".validators", "validators", "ValidationResult")
    """
    import importlib

    # Try relative import
    try:
        module = importlib.import_module(relative_module, package=__package__)
        return getattr(module, name, default)
    except (ImportError, AttributeError):
        pass

    # Try absolute import
    try:
        module = importlib.import_module(absolute_module)
        return getattr(module, name, default)
    except (ImportError, AttributeError):
        pass

    return default


# =============================================================================
# Status reporting (useful for debugging and health checks)
# =============================================================================


def get_import_status() -> dict:
    """Return a dict of feature availability for debugging."""
    return {
        "metrics_enabled": METRICS_ENABLED,
        "otel_enabled": OTEL_ENABLED,
        "circuit_breaker_enabled": CIRCUIT_BREAKER_ENABLED,
        "policy_client_available": POLICY_CLIENT_AVAILABLE,
        "deliberation_available": DELIBERATION_AVAILABLE,
        "crypto_available": CRYPTO_AVAILABLE,
        "config_available": CONFIG_AVAILABLE,
        "audit_client_available": AUDIT_CLIENT_AVAILABLE,
        "opa_client_available": OPA_CLIENT_AVAILABLE,
        "use_rust": USE_RUST,
        "metering_available": METERING_AVAILABLE,
        "default_redis_url": DEFAULT_REDIS_URL,
    }


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Feature Availability Flags
    "METRICS_ENABLED",
    "OTEL_ENABLED",
    "CIRCUIT_BREAKER_ENABLED",
    "POLICY_CLIENT_AVAILABLE",
    "DELIBERATION_AVAILABLE",
    "CRYPTO_AVAILABLE",
    "CONFIG_AVAILABLE",
    "AUDIT_CLIENT_AVAILABLE",
    "OPA_CLIENT_AVAILABLE",
    "USE_RUST",
    "METERING_AVAILABLE",
    "MACI_AVAILABLE",
    "DEFAULT_REDIS_URL",
    # Optional Module References
    "MESSAGE_QUEUE_DEPTH",
    "set_service_info",
    "tracer",
    "meter",
    "QUEUE_DEPTH",
    "get_circuit_breaker",
    "circuit_breaker_health_check",
    "initialize_core_circuit_breakers",
    "CircuitBreakerConfig",
    "PolicyClient",
    "get_policy_client",
    "VotingService",
    "VotingStrategy",
    "DeliberationQueue",
    "CryptoService",
    "settings",
    "AuditClient",
    "OPAClient",
    "get_opa_client",
    "rust_bus",
    "MeteringHooks",
    "MeteringConfig",
    "AsyncMeteringQueue",
    "get_metering_hooks",
    "get_metering_queue",
    "MACIEnforcer",
    "MACIRole",
    "MACIRoleRegistry",
    # Import Utilities
    "try_import",
    "import_with_fallback",
    "optional_import",
    "try_relative_import",
    # Lifecycle
    "initialize_all_imports",
    "get_import_status",
]
