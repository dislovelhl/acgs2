"""
ACGS-2 Observability Module
Constitutional Hash: cdd01ef066bc6cf2

Unified OpenTelemetry instrumentation for the enhanced agent bus
and breakthrough architecture layers.
"""

from .telemetry import (
    configure_telemetry,
    get_tracer,
    get_meter,
    TracingContext,
    MetricsRegistry,
    CONSTITUTIONAL_HASH,
    OTEL_AVAILABLE,
)

from .decorators import (
    traced,
    metered,
    timed,
)

from .timeout_budget import (
    LayerTimeoutBudget,
    TimeoutBudgetManager,
    LayerTimeoutError,
)

__all__ = [
    # Core telemetry
    "configure_telemetry",
    "get_tracer",
    "get_meter",
    "TracingContext",
    "MetricsRegistry",
    "CONSTITUTIONAL_HASH",
    "OTEL_AVAILABLE",
    # Decorators
    "traced",
    "metered",
    "timed",
    # Timeout management
    "LayerTimeoutBudget",
    "TimeoutBudgetManager",
    "LayerTimeoutError",
]
