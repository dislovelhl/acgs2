"""
ACGS-2 Observability Module
Constitutional Hash: cdd01ef066bc6cf2

Unified OpenTelemetry instrumentation for the enhanced agent bus
and breakthrough architecture layers.
"""

from .decorators import metered, timed, traced
from .telemetry import (
    CONSTITUTIONAL_HASH,
    OTEL_AVAILABLE,
    MetricsRegistry,
    TracingContext,
    configure_telemetry,
    get_meter,
    get_tracer,
)
from .timeout_budget import LayerTimeoutBudget, LayerTimeoutError, TimeoutBudgetManager

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
