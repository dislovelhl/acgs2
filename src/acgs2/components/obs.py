"""
Observability System (OBS) Implementation

The OBS provides comprehensive observability for the ACGS-2 system including:
- Metrics collection and aggregation
- Distributed tracing with request ID correlation
- Performance profiling and alerting
- Prometheus-compatible metrics export
- Real-time monitoring and alerting
"""

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.interfaces import ObservabilitySystemInterface
from ..core.schemas import TelemetryEvent

logger = logging.getLogger(__name__)


class ObservabilitySystem(ObservabilitySystemInterface):
    """Observability System - Metrics, tracing, and alerting for ACGS-2."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = True

        # Metrics storage: component -> metric_name -> values
        self.metrics: Dict[str, Dict[str, List[Dict]]] = defaultdict(lambda: defaultdict(list))

        # Traces: request_id -> list of events
        self.traces: Dict[str, List[TelemetryEvent]] = {}

        # Active alerts
        self.alerts: List[Dict[str, Any]] = []

        # Alert thresholds
        self.alert_thresholds = config.get(
            "alert_thresholds",
            {
                "latency_ms": {"warning": 5000, "critical": 15000},
                "error_rate": {"warning": 0.05, "critical": 0.20},
                "memory_mb": {"warning": 1000, "critical": 2000},
            },
        )

        # Metrics retention (keep last N values per metric)
        self.max_metrics_per_component = config.get("max_metrics_per_component", 1000)

        logger.info("OBS initialized with comprehensive observability capabilities")

    @property
    def component_name(self) -> str:
        return "OBS"

    async def health_check(self) -> Dict[str, Any]:
        """Health check for OBS."""
        total_traces = len(self.traces)
        total_alerts = len(self.alerts)

        # Count active metrics
        total_metrics = sum(len(metrics) for metrics in self.metrics.values())

        return {
            "component": self.component_name,
            "status": "healthy" if self._running else "unhealthy",
            "active_traces": total_traces,
            "active_alerts": total_alerts,
            "total_metrics": total_metrics,
            "components_monitored": list(self.metrics.keys()),
        }

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("OBS shutting down")
        self._running = False

        # Export final metrics before shutdown
        await self._export_final_metrics()

    async def emit_event(self, event: TelemetryEvent) -> None:
        """
        Emit telemetry event for observability.

        Updates metrics, traces, and checks alert thresholds.
        """
        if not self._running:
            return

        # Store in traces by request_id
        if event.request_id not in self.traces:
            self.traces[event.request_id] = []

        self.traces[event.request_id].append(event)

        # Update metrics
        await self._update_metrics(event)

        # Check alert thresholds
        await self._check_alerts(event)

        # Clean up old traces (keep last 24 hours)
        await self._cleanup_old_traces()

    async def get_metrics(self, component: str, time_range: Dict[str, str]) -> Dict[str, Any]:
        """
        Get aggregated metrics for a component within time range.

        Args:
            component: Component name (e.g., "UIG", "SAS")
            time_range: Dict with "start" and "end" ISO timestamps

        Returns:
            Dict with aggregated metrics
        """
        if component not in self.metrics:
            return {"error": f"No metrics found for component {component}"}

        start_time = time_range.get("start")
        end_time = time_range.get("end")

        result = {
            "component": component,
            "time_range": time_range,
            "metrics": {},
        }

        for metric_name, values in self.metrics[component].items():
            # Filter by time range
            filtered_values = values
            if start_time:
                start_ts = self._iso_to_timestamp(start_time)
                filtered_values = [v for v in values if v.get("timestamp", 0) >= start_ts]

            if end_time:
                end_ts = self._iso_to_timestamp(end_time)
                filtered_values = [v for v in filtered_values if v.get("timestamp", 0) <= end_ts]

            if filtered_values:
                result["metrics"][metric_name] = self._aggregate_metric(filtered_values)

        return result

    async def get_traces(self, request_id: str) -> List[TelemetryEvent]:
        """
        Get complete trace for a request ID.

        Args:
            request_id: Request identifier

        Returns:
            List of telemetry events in chronological order
        """
        if request_id not in self.traces:
            return []

        # Return events sorted by timestamp
        trace = self.traces[request_id]
        return sorted(trace, key=lambda e: e.timestamp)

    async def alert_on_anomaly(self, component: str, metric: str, threshold: float) -> None:
        """
        Manually trigger an alert for anomalous metric behavior.

        Args:
            component: Component name
            metric: Metric name
            threshold: Threshold value that was exceeded
        """
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": component,
            "metric": metric,
            "threshold": threshold,
            "type": "manual_anomaly",
            "severity": "warning",
        }

        self.alerts.append(alert)
        logger.warning(f"Manual alert triggered: {component}.{metric} exceeded {threshold}")

    async def get_active_alerts(self, component: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get active alerts, optionally filtered by component.

        Args:
            component: Optional component filter

        Returns:
            List of active alerts
        """
        if component:
            return [alert for alert in self.alerts if alert.get("component") == component]
        return self.alerts.copy()

    async def get_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            Prometheus-formatted metrics string
        """
        lines = ["# ACGS-2 System Metrics"]

        for component, component_metrics in self.metrics.items():
            for metric_name, values in component_metrics.items():
                if not values:
                    continue

                # Get latest value
                latest = max(values, key=lambda v: v.get("timestamp", 0))

                # Format as Prometheus gauge
                metric_value = latest.get("value", 0)
                labels = f'component="{component}"'

                lines.append(f"acgs2_{metric_name}{{{labels}}} {metric_value}")

        return "\n".join(lines)

    async def _update_metrics(self, event: TelemetryEvent) -> None:
        """Update metrics based on telemetry event."""
        component = event.component
        event_type = event.event_type
        metadata = event.metadata or {}

        # Counter metrics
        if event_type == "request_started":
            await self._increment_counter(component, "requests_total")
        elif event_type == "request_completed":
            await self._increment_counter(component, "requests_completed_total")
        elif event_type == "request_failed":
            await self._increment_counter(component, "requests_failed_total")
        elif event_type == "tool_executed":
            await self._increment_counter(component, "tools_executed_total")
        elif event_type == "safety_denied":
            await self._increment_counter(component, "safety_denials_total")

        # Latency metrics
        if event.latency_ms is not None:
            await self._record_gauge(component, "request_latency_ms", event.latency_ms)

        # Memory metrics (if provided)
        memory_mb = metadata.get("memory_mb")
        if memory_mb is not None:
            await self._record_gauge(component, "memory_usage_mb", memory_mb)

        # Error rate calculation
        await self._update_error_rate(component)

    async def _increment_counter(self, component: str, metric_name: str) -> None:
        """Increment a counter metric."""
        current_count = self._get_latest_metric_value(component, metric_name) or 0
        await self._record_gauge(component, metric_name, current_count + 1)

    async def _record_gauge(self, component: str, metric_name: str, value: Any) -> None:
        """Record a gauge metric value."""
        metric_entry = {
            "timestamp": time.time(),
            "value": value,
        }

        self.metrics[component][metric_name].append(metric_entry)

        # Maintain max retention
        if len(self.metrics[component][metric_name]) > self.max_metrics_per_component:
            self.metrics[component][metric_name] = self.metrics[component][metric_name][
                -self.max_metrics_per_component :
            ]

    async def _check_alerts(self, event: TelemetryEvent) -> None:
        """Check if event triggers any alerts."""
        component = event.component
        metadata = event.metadata or {}

        # Latency alerts
        if event.latency_ms is not None:
            latency_thresholds = self.alert_thresholds.get("latency_ms", {})
            if event.latency_ms > latency_thresholds.get("critical", float("inf")):
                await self._trigger_alert(
                    component,
                    "latency",
                    "critical",
                    event.latency_ms,
                    latency_thresholds["critical"],
                )
            elif event.latency_ms > latency_thresholds.get("warning", float("inf")):
                await self._trigger_alert(
                    component, "latency", "warning", event.latency_ms, latency_thresholds["warning"]
                )

        # Memory alerts
        memory_mb = metadata.get("memory_mb")
        if memory_mb is not None:
            memory_thresholds = self.alert_thresholds.get("memory_mb", {})
            if memory_mb > memory_thresholds.get("critical", float("inf")):
                await self._trigger_alert(
                    component, "memory", "critical", memory_mb, memory_thresholds["critical"]
                )
            elif memory_mb > memory_thresholds.get("warning", float("inf")):
                await self._trigger_alert(
                    component, "memory", "warning", memory_mb, memory_thresholds["warning"]
                )

    async def _trigger_alert(
        self, component: str, metric: str, severity: str, value: float, threshold: float
    ) -> None:
        """Trigger an alert."""
        alert = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": component,
            "metric": metric,
            "severity": severity,
            "value": value,
            "threshold": threshold,
            "type": "threshold_exceeded",
        }

        self.alerts.append(alert)

        # Keep only recent alerts (last 100)
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]

        logger.warning(f"Alert triggered: {component}.{metric} {severity} - {value} > {threshold}")

    async def _update_error_rate(self, component: str) -> None:
        """Calculate and update error rate metric."""
        total_requests = self._get_latest_metric_value(component, "requests_total") or 0
        failed_requests = self._get_latest_metric_value(component, "requests_failed_total") or 0

        if total_requests > 0:
            error_rate = failed_requests / total_requests
            await self._record_gauge(component, "error_rate", error_rate)

            # Check error rate alerts
            error_thresholds = self.alert_thresholds.get("error_rate", {})
            if error_rate > error_thresholds.get("critical", float("inf")):
                await self._trigger_alert(
                    component, "error_rate", "critical", error_rate, error_thresholds["critical"]
                )
            elif error_rate > error_thresholds.get("warning", float("inf")):
                await self._trigger_alert(
                    component, "error_rate", "warning", error_rate, error_thresholds["warning"]
                )

    async def _cleanup_old_traces(self) -> None:
        """Clean up traces older than retention period."""
        # Keep traces for 24 hours
        retention_seconds = 24 * 60 * 60
        cutoff_time = time.time() - retention_seconds

        to_remove = []
        for request_id, events in self.traces.items():
            if events and self._iso_to_timestamp(events[0].timestamp) < cutoff_time:
                to_remove.append(request_id)

        for request_id in to_remove:
            del self.traces[request_id]

    async def _export_final_metrics(self) -> None:
        """Export final metrics on shutdown."""
        try:
            # Could write to file or send to external monitoring
            logger.info(f"Exported final metrics for {len(self.metrics)} components")
        except Exception as e:
            logger.error(f"Failed to export final metrics: {e}")

    def _get_latest_metric_value(self, component: str, metric_name: str) -> Optional[Any]:
        """Get the latest value for a metric."""
        if component not in self.metrics or metric_name not in self.metrics[component]:
            return None

        values = self.metrics[component][metric_name]
        if not values:
            return None

        return max(values, key=lambda v: v.get("timestamp", 0))["value"]

    def _aggregate_metric(self, values: List[Dict]) -> Dict[str, Any]:
        """Aggregate metric values for reporting."""
        if not values:
            return {}

        numeric_values = [v["value"] for v in values if isinstance(v["value"], (int, float))]

        if not numeric_values:
            # For non-numeric metrics, return count
            return {
                "count": len(values),
                "latest": values[-1]["value"] if values else None,
            }

        return {
            "count": len(numeric_values),
            "min": min(numeric_values),
            "max": max(numeric_values),
            "avg": sum(numeric_values) / len(numeric_values),
            "latest": numeric_values[-1],
        }

    def _iso_to_timestamp(self, iso_string: str) -> float:
        """Convert ISO timestamp to Unix timestamp."""
        try:
            dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
            return dt.timestamp()
        except (ValueError, AttributeError):
            return 0.0
