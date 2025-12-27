"""
ACGS-2 Enhanced Agent Bus - Optional Imports Management
Constitutional Hash: cdd01ef066bc6cf2

Centralizes optional import handling with graceful fallbacks.
This follows the Facade pattern to hide import complexity from the main modules.
"""

import logging
from typing import Any, Callable, Optional, TYPE_CHECKING

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


# =============================================================================
# Import Resolution Functions
# =============================================================================

def _init_prometheus_metrics() -> None:
    """Initialize Prometheus metrics with fallback."""
    global METRICS_ENABLED, MESSAGE_QUEUE_DEPTH, set_service_info
    try:
        from shared.metrics import (
            MESSAGE_QUEUE_DEPTH as _mqd,
            set_service_info as _ssi,
        )
        MESSAGE_QUEUE_DEPTH = _mqd
        set_service_info = _ssi
        METRICS_ENABLED = True
    except ImportError:
        METRICS_ENABLED = False


def _init_opentelemetry() -> None:
    """Initialize OpenTelemetry with fallback."""
    global OTEL_ENABLED, tracer, meter, QUEUE_DEPTH
    try:
        from opentelemetry import trace, metrics
        tracer = trace.get_tracer(__name__)
        meter = metrics.get_meter(__name__)
        QUEUE_DEPTH = meter.create_up_down_counter(
            "acgs2.queue.depth",
            description="Current message queue depth",
            unit="1"
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
        from shared.circuit_breaker import (
            get_circuit_breaker as _gcb,
            circuit_breaker_health_check as _cbhc,
            initialize_core_circuit_breakers as _icb,
            CircuitBreakerConfig as _cbc,
        )
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
            from .policy_client import get_policy_client as _gpc, PolicyClient as _pc
        except ImportError:
            from policy_client import get_policy_client as _gpc, PolicyClient as _pc
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
            from .deliberation_layer.voting_service import (
                VotingService as _vs,
                VotingStrategy as _vst,
            )
            from .deliberation_layer.deliberation_queue import (
                DeliberationQueue as _dq,
            )
        except ImportError:
            from deliberation_layer.voting_service import (
                VotingService as _vs,
                VotingStrategy as _vst,
            )
            from deliberation_layer.deliberation_queue import (
                DeliberationQueue as _dq,
            )
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
        from services.policy_registry.app.services.crypto_service import (
            CryptoService as _cs,
        )
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
        from shared.config import settings as _s
        settings = _s
        CONFIG_AVAILABLE = True
    except ImportError:
        CONFIG_AVAILABLE = False
        settings = None


def _init_audit_client() -> None:
    """Initialize audit client with fallback."""
    global AUDIT_CLIENT_AVAILABLE, AuditClient
    try:
        from shared.audit_client import AuditClient as _ac
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
            from .opa_client import get_opa_client as _goc, OPAClient as _oc
        except ImportError:
            from opa_client import get_opa_client as _goc, OPAClient as _oc
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
        import enhanced_agent_bus_rust as _rb
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
            from .metering_integration import (
                MeteringHooks as _mh,
                MeteringConfig as _mc,
                AsyncMeteringQueue as _amq,
                get_metering_hooks as _gmh,
                get_metering_queue as _gmq,
                METERING_AVAILABLE as _ma,
            )
        except ImportError:
            from metering_integration import (
                MeteringHooks as _mh,
                MeteringConfig as _mc,
                AsyncMeteringQueue as _amq,
                get_metering_hooks as _gmh,
                get_metering_queue as _gmq,
                METERING_AVAILABLE as _ma,
            )
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


def _init_redis_config() -> str:
    """Initialize Redis config and return default URL."""
    try:
        from shared.redis_config import get_redis_url
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


# Initialize on module load (maintains backward compatibility)
DEFAULT_REDIS_URL: str = _init_redis_config()
initialize_all_imports()


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
