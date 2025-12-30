"""
ACGS-2 Constitutional Profiler for NeMo-Agent-Toolkit
Constitutional Hash: cdd01ef066bc6cf2

Provides profiling and metrics collection for AI agents
with constitutional governance tracking.
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    pass

CONSTITUTIONAL_HASH: str = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


class MetricType(str, Enum):
    """Types of metrics collected."""

    LATENCY = "latency"
    THROUGHPUT = "throughput"
    COMPLIANCE = "compliance"
    VIOLATION = "violation"
    TOKEN_USAGE = "token_usage"
    COST = "cost"
    GUARDRAIL_CHECK = "guardrail_check"


@dataclass
class GovernanceMetrics:
    """Governance-specific metrics for AI agents."""

    # Compliance metrics
    total_requests: int = 0
    compliant_requests: int = 0
    blocked_requests: int = 0
    modified_requests: int = 0

    # Violation metrics
    privacy_violations: int = 0
    safety_violations: int = 0
    ethics_violations: int = 0
    compliance_violations: int = 0

    # Guardrail metrics
    input_checks: int = 0
    output_checks: int = 0
    input_blocks: int = 0
    output_blocks: int = 0
    pii_redactions: int = 0

    # Performance metrics
    average_check_latency_ms: float = 0.0
    p50_check_latency_ms: float = 0.0
    p95_check_latency_ms: float = 0.0
    p99_check_latency_ms: float = 0.0

    # Constitutional tracking
    constitutional_hash: str = CONSTITUTIONAL_HASH
    collection_start: datetime = field(default_factory=lambda: datetime.now(UTC))
    collection_end: datetime | None = None

    @property
    def compliance_rate(self) -> float:
        """Calculate compliance rate."""
        if self.total_requests == 0:
            return 1.0
        return self.compliant_requests / self.total_requests

    @property
    def block_rate(self) -> float:
        """Calculate block rate."""
        if self.total_requests == 0:
            return 0.0
        return self.blocked_requests / self.total_requests

    @property
    def violation_rate(self) -> float:
        """Calculate violation rate."""
        total_violations = (
            self.privacy_violations
            + self.safety_violations
            + self.ethics_violations
            + self.compliance_violations
        )
        if self.total_requests == 0:
            return 0.0
        return total_violations / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "compliant_requests": self.compliant_requests,
            "blocked_requests": self.blocked_requests,
            "modified_requests": self.modified_requests,
            "compliance_rate": self.compliance_rate,
            "block_rate": self.block_rate,
            "violation_rate": self.violation_rate,
            "violations": {
                "privacy": self.privacy_violations,
                "safety": self.safety_violations,
                "ethics": self.ethics_violations,
                "compliance": self.compliance_violations,
            },
            "guardrails": {
                "input_checks": self.input_checks,
                "output_checks": self.output_checks,
                "input_blocks": self.input_blocks,
                "output_blocks": self.output_blocks,
                "pii_redactions": self.pii_redactions,
            },
            "latency": {
                "average_ms": self.average_check_latency_ms,
                "p50_ms": self.p50_check_latency_ms,
                "p95_ms": self.p95_check_latency_ms,
                "p99_ms": self.p99_check_latency_ms,
            },
            "constitutional_hash": self.constitutional_hash,
            "collection_start": self.collection_start.isoformat(),
            "collection_end": self.collection_end.isoformat() if self.collection_end else None,
        }


@dataclass
class ProfilerEvent:
    """A profiler event."""

    event_type: str
    name: str
    duration_ms: float
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    constitutional_hash: str = CONSTITUTIONAL_HASH


class ConstitutionalProfiler:
    """
    Profiler for AI agents with constitutional governance tracking.

    Integrates with NeMo-Agent-Toolkit's profiling capabilities
    while adding constitutional compliance metrics.
    """

    def __init__(
        self,
        name: str = "default",
        enable_detailed_logging: bool = False,
        export_interval_seconds: float = 60.0,
    ) -> None:
        """
        Initialize the profiler.

        Args:
            name: Profiler instance name
            enable_detailed_logging: Enable detailed event logging
            export_interval_seconds: Interval for metric exports
        """
        self._name = name
        self._detailed_logging = enable_detailed_logging
        self._export_interval = export_interval_seconds

        self._metrics = GovernanceMetrics()
        self._events: list[ProfilerEvent] = []
        self._latencies: list[float] = []
        self._callbacks: list[Callable[[dict[str, Any]], None]] = []

        self._running = False
        self._export_task: asyncio.Task | None = None

    @property
    def name(self) -> str:
        """Get profiler name."""
        return self._name

    @property
    def metrics(self) -> GovernanceMetrics:
        """Get current metrics."""
        return self._metrics

    def start(self) -> None:
        """Start the profiler."""
        if self._running:
            return

        self._running = True
        self._metrics = GovernanceMetrics()
        self._events.clear()
        self._latencies.clear()

        logger.info(f"Profiler '{self._name}' started")

    def stop(self) -> GovernanceMetrics:
        """Stop the profiler and return final metrics."""
        self._running = False
        self._metrics.collection_end = datetime.now(UTC)

        if self._export_task:
            self._export_task.cancel()
            self._export_task = None

        # Calculate final latency percentiles
        self._update_latency_stats()

        logger.info(f"Profiler '{self._name}' stopped")
        return self._metrics

    def record_request(
        self,
        compliant: bool,
        blocked: bool = False,
        modified: bool = False,
    ) -> None:
        """Record a request."""
        self._metrics.total_requests += 1
        if compliant:
            self._metrics.compliant_requests += 1
        if blocked:
            self._metrics.blocked_requests += 1
        if modified:
            self._metrics.modified_requests += 1

    def record_violation(
        self,
        violation_type: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Record a violation."""
        if violation_type == "privacy":
            self._metrics.privacy_violations += 1
        elif violation_type == "safety":
            self._metrics.safety_violations += 1
        elif violation_type == "ethics":
            self._metrics.ethics_violations += 1
        elif violation_type == "compliance":
            self._metrics.compliance_violations += 1

        if self._detailed_logging:
            self._record_event("violation", violation_type, 0, details or {})

    def record_guardrail_check(
        self,
        direction: str,
        blocked: bool,
        pii_redacted: bool = False,
        latency_ms: float = 0.0,
    ) -> None:
        """Record a guardrail check."""
        if direction == "input":
            self._metrics.input_checks += 1
            if blocked:
                self._metrics.input_blocks += 1
        elif direction == "output":
            self._metrics.output_checks += 1
            if blocked:
                self._metrics.output_blocks += 1

        if pii_redacted:
            self._metrics.pii_redactions += 1

        if latency_ms > 0:
            self._latencies.append(latency_ms)

        if self._detailed_logging:
            self._record_event(
                "guardrail_check",
                direction,
                latency_ms,
                {
                    "blocked": blocked,
                    "pii_redacted": pii_redacted,
                },
            )

    def record_latency(self, latency_ms: float) -> None:
        """Record a latency measurement."""
        self._latencies.append(latency_ms)

    def _record_event(
        self,
        event_type: str,
        name: str,
        duration_ms: float,
        metadata: dict[str, Any],
    ) -> None:
        """Record a detailed event."""
        event = ProfilerEvent(
            event_type=event_type,
            name=name,
            duration_ms=duration_ms,
            metadata=metadata,
        )
        self._events.append(event)

        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(event.__dict__)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def _update_latency_stats(self) -> None:
        """Update latency statistics."""
        if not self._latencies:
            return

        sorted_latencies = sorted(self._latencies)
        n = len(sorted_latencies)

        self._metrics.average_check_latency_ms = statistics.mean(sorted_latencies)
        self._metrics.p50_check_latency_ms = sorted_latencies[int(n * 0.50)]
        self._metrics.p95_check_latency_ms = (
            sorted_latencies[int(n * 0.95)] if n >= 20 else sorted_latencies[-1]
        )
        self._metrics.p99_check_latency_ms = (
            sorted_latencies[int(n * 0.99)] if n >= 100 else sorted_latencies[-1]
        )

    def add_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Add a callback for profiler events."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """Remove a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_events(self) -> list[ProfilerEvent]:
        """Get all recorded events."""
        return self._events.copy()

    async def export_metrics(self) -> dict[str, Any]:
        """Export current metrics."""
        self._update_latency_stats()
        return self._metrics.to_dict()

    def create_context_manager(self, operation_name: str) -> ProfilerContext:
        """Create a context manager for timing operations."""
        return ProfilerContext(self, operation_name)

    def time_operation(self, name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator to time an operation."""

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            if asyncio.iscoroutinefunction(func):

                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    start = time.perf_counter()
                    try:
                        return await func(*args, **kwargs)
                    finally:
                        elapsed = (time.perf_counter() - start) * 1000
                        self.record_latency(elapsed)
                        if self._detailed_logging:
                            self._record_event("operation", name, elapsed, {})

                return async_wrapper
            else:

                def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                    start = time.perf_counter()
                    try:
                        return func(*args, **kwargs)
                    finally:
                        elapsed = (time.perf_counter() - start) * 1000
                        self.record_latency(elapsed)
                        if self._detailed_logging:
                            self._record_event("operation", name, elapsed, {})

                return sync_wrapper

        return decorator

    def get_summary(self) -> str:
        """Get a human-readable summary of metrics."""
        m = self._metrics
        return f"""
Constitutional Profiler Summary: {self._name}
============================================
Total Requests: {m.total_requests}
Compliance Rate: {m.compliance_rate:.2%}
Block Rate: {m.block_rate:.2%}
Violation Rate: {m.violation_rate:.2%}

Violations:
  - Privacy: {m.privacy_violations}
  - Safety: {m.safety_violations}
  - Ethics: {m.ethics_violations}
  - Compliance: {m.compliance_violations}

Guardrail Checks:
  - Input Checks: {m.input_checks} (Blocked: {m.input_blocks})
  - Output Checks: {m.output_checks} (Blocked: {m.output_blocks})
  - PII Redactions: {m.pii_redactions}

Latency:
  - Average: {m.average_check_latency_ms:.2f}ms
  - P50: {m.p50_check_latency_ms:.2f}ms
  - P95: {m.p95_check_latency_ms:.2f}ms
  - P99: {m.p99_check_latency_ms:.2f}ms

Constitutional Hash: {m.constitutional_hash}
Collection Period: {m.collection_start.isoformat()} - {m.collection_end.isoformat() if m.collection_end else 'ongoing'}
"""


class ProfilerContext:
    """Context manager for timing operations."""

    def __init__(self, profiler: ConstitutionalProfiler, operation_name: str) -> None:
        """Initialize context."""
        self._profiler = profiler
        self._operation_name = operation_name
        self._start_time: float = 0

    def __enter__(self) -> ProfilerContext:
        """Enter context."""
        self._start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context."""
        elapsed = (time.perf_counter() - self._start_time) * 1000
        self._profiler.record_latency(elapsed)
        if self._profiler._detailed_logging:
            self._profiler._record_event(
                "operation",
                self._operation_name,
                elapsed,
                {"error": str(exc_val) if exc_val else None},
            )

    async def __aenter__(self) -> ProfilerContext:
        """Async enter context."""
        self._start_time = time.perf_counter()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async exit context."""
        elapsed = (time.perf_counter() - self._start_time) * 1000
        self._profiler.record_latency(elapsed)
        if self._profiler._detailed_logging:
            self._profiler._record_event(
                "operation",
                self._operation_name,
                elapsed,
                {"error": str(exc_val) if exc_val else None},
            )


class NeMoProfilerBridge:
    """
    Bridge between ACGS-2 profiler and NeMo-Agent-Toolkit profiler.

    Allows seamless integration with NeMo's built-in profiling
    while adding constitutional governance metrics.
    """

    def __init__(
        self,
        constitutional_profiler: ConstitutionalProfiler,
    ) -> None:
        """
        Initialize the bridge.

        Args:
            constitutional_profiler: ACGS-2 constitutional profiler
        """
        self._profiler = constitutional_profiler
        self._nemo_profiler: Any = None

    def connect_nemo_profiler(self, nemo_profiler: Any) -> None:
        """
        Connect to NeMo-Agent-Toolkit profiler.

        Args:
            nemo_profiler: NeMo profiler instance
        """
        self._nemo_profiler = nemo_profiler

        # Add callback to sync events
        if hasattr(nemo_profiler, "add_callback"):
            nemo_profiler.add_callback(self._on_nemo_event)

    def _on_nemo_event(self, event: dict[str, Any]) -> None:
        """Handle events from NeMo profiler."""
        # Map NeMo events to constitutional profiler
        event_type = event.get("type", "unknown")

        if event_type == "inference":
            latency = event.get("duration_ms", 0)
            self._profiler.record_latency(latency)

        elif event_type == "tool_call":
            # Track tool calls for governance
            self._profiler._record_event(
                "nemo_tool_call",
                event.get("tool_name", "unknown"),
                event.get("duration_ms", 0),
                event,
            )

    def get_combined_metrics(self) -> dict[str, Any]:
        """Get combined metrics from both profilers."""
        metrics = self._profiler.metrics.to_dict()

        if self._nemo_profiler and hasattr(self._nemo_profiler, "get_metrics"):
            nemo_metrics = self._nemo_profiler.get_metrics()
            metrics["nemo_metrics"] = nemo_metrics

        return metrics

    def export_for_nemo(self) -> dict[str, Any]:
        """Export metrics in NeMo-compatible format."""
        metrics = self._profiler.metrics

        return {
            "governance": {
                "compliance_rate": metrics.compliance_rate,
                "violation_rate": metrics.violation_rate,
                "block_rate": metrics.block_rate,
            },
            "performance": {
                "avg_latency_ms": metrics.average_check_latency_ms,
                "p50_latency_ms": metrics.p50_check_latency_ms,
                "p95_latency_ms": metrics.p95_check_latency_ms,
                "p99_latency_ms": metrics.p99_check_latency_ms,
            },
            "guardrails": {
                "total_checks": metrics.input_checks + metrics.output_checks,
                "total_blocks": metrics.input_blocks + metrics.output_blocks,
                "pii_redactions": metrics.pii_redactions,
            },
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }
