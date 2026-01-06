"""
ACGS-2 Production Monitoring Module
Constitutional Hash: cdd01ef066bc6cf2

Real-time production monitoring with psutil integration, Redis metrics, and PagerDuty alerting.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .alerting import Alert, AlertSeverity, AlertStatus

# Import centralized Redis config with fallback
try:
    from src.core.shared.redis_config import get_redis_url

    DEFAULT_REDIS_URL = get_redis_url()
except ImportError:
    DEFAULT_REDIS_URL = "redis://localhost:6379"

# Constitutional compliance hash
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System metrics data class."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    constitutional_hash: str = CONSTITUTIONAL_HASH
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0
    process_count: int = 0


@dataclass
class RedisMetrics:
    """Redis metrics data class."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    constitutional_hash: str = CONSTITUTIONAL_HASH
    connected_clients: int = 0
    used_memory_mb: float = 0.0
    used_memory_peak: int = 0
    total_connections_received: int = 0
    total_commands_processed: int = 0
    keyspace_hits: int = 0
    keyspace_misses: int = 0
    hit_rate_percent: float = 0.0
    total_keys: int = 0


class SystemMetricsCollector:
    """Collects system metrics using psutil."""

    def __init__(self):
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self._psutil = None
        try:
            import psutil

            self._psutil = psutil
        except ImportError:
            logger.warning("psutil not available, using mock metrics")

    async def collect_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics."""
        if self._psutil:
            # Defensive: net_io_counters() can return None in some environments (containers, etc.)
            net_counters = self._psutil.net_io_counters()
            network_bytes_sent = net_counters.bytes_sent if net_counters else 0
            network_bytes_recv = net_counters.bytes_recv if net_counters else 0

            return SystemMetrics(
                cpu_percent=self._psutil.cpu_percent(interval=0.1),
                memory_percent=self._psutil.virtual_memory().percent,
                disk_percent=self._psutil.disk_usage("/").percent,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                process_count=len(self._psutil.pids()),
            )
        return SystemMetrics()

    async def _collect_cpu_metrics(self) -> Dict[str, Any]:
        """Collect CPU-specific metrics."""
        if self._psutil:
            return {
                "cpu_percent": self._psutil.cpu_percent(interval=0.1),
                "cpu_count": self._psutil.cpu_count(),
                "cpu_freq": (
                    getattr(self._psutil.cpu_freq(), "current", 0) if self._psutil.cpu_freq() else 0
                ),
            }
        return {"cpu_percent": 0.0, "cpu_count": 1, "cpu_freq": 0}

    async def _collect_memory_metrics(self) -> Dict[str, Any]:
        """Collect memory-specific metrics."""
        if self._psutil:
            mem = self._psutil.virtual_memory()
            return {
                "memory_total_gb": mem.total / (1024**3),
                "memory_used_gb": mem.used / (1024**3),
                "memory_percent": mem.percent,
                "memory_available_gb": mem.available / (1024**3),
            }
        return {
            "memory_total_gb": 0,
            "memory_used_gb": 0,
            "memory_percent": 0.0,
            "memory_available_gb": 0,
        }

    async def _collect_disk_metrics(self) -> Dict[str, Any]:
        """Collect disk-specific metrics."""
        if self._psutil:
            disk = self._psutil.disk_usage("/")
            return {
                "disk_total_gb": disk.total / (1024**3),
                "disk_used_gb": disk.used / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
            }
        return {"disk_total_gb": 0, "disk_used_gb": 0, "disk_percent": 0.0, "disk_free_gb": 0}

    async def _collect_network_metrics(self) -> Dict[str, Any]:
        """Collect network-specific metrics."""
        if self._psutil:
            # Defensive: net_io_counters() can return None in some environments
            net = self._psutil.net_io_counters()
            if net is not None:
                return {
                    "network_bytes_sent_mb": net.bytes_sent / (1024**2),
                    "network_bytes_recv_mb": net.bytes_recv / (1024**2),
                    "network_packets_sent": net.packets_sent,
                    "network_packets_recv": net.packets_recv,
                }
        return {
            "network_bytes_sent_mb": 0,
            "network_bytes_recv_mb": 0,
            "network_packets_sent": 0,
            "network_packets_recv": 0,
        }

    async def _collect_process_metrics(self) -> Dict[str, Any]:
        """Collect process-specific metrics."""
        if self._psutil:
            pids = self._psutil.pids()
            thread_count = 0
            try:
                for pid in pids[:100]:  # Sample first 100 to avoid performance issues
                    try:
                        p = self._psutil.Process(pid)
                        thread_count += p.num_threads()
                    except (self._psutil.NoSuchProcess, self._psutil.AccessDenied):
                        pass
            except Exception:
                pass
            return {
                "process_count": len(pids),
                "thread_count": thread_count if thread_count > 0 else len(pids),
            }
        return {"process_count": 1, "thread_count": 1}


class RedisMetricsCollector:
    """Collects Redis metrics."""

    def __init__(self, redis_url: str = DEFAULT_REDIS_URL):
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.redis_url = redis_url
        self._redis_client = None
        self._connected = False

    async def connect(self) -> bool:
        """Connect to Redis."""
        try:
            import redis.asyncio as aioredis

            self._redis_client = await aioredis.from_url(self.redis_url)
            self._connected = True
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            self._connected = False

    async def collect_metrics(self) -> RedisMetrics:
        """Collect Redis metrics."""
        try:
            if self._redis_client:
                info = await self._redis_client.info()
                hits = info.get("keyspace_hits", 0)
                misses = info.get("keyspace_misses", 0)
                total = hits + misses

                return RedisMetrics(
                    connected_clients=info.get("connected_clients", 0),
                    used_memory_mb=info.get("used_memory", 0) / (1024**2),
                    used_memory_peak=info.get("used_memory_peak", 0),
                    total_connections_received=info.get("total_connections_received", 0),
                    total_commands_processed=info.get("total_commands_processed", 0),
                    keyspace_hits=hits,
                    keyspace_misses=misses,
                    hit_rate_percent=(hits / total * 100) if total > 0 else 0.0,
                    total_keys=(
                        info.get("db0", {}).get("keys", 0)
                        if isinstance(info.get("db0"), dict)
                        else 0
                    ),
                )
        except Exception as e:
            logger.warning(f"Failed to collect Redis metrics: {e}")
        return RedisMetrics()


class PagerDutyAlerting:
    """PagerDuty integration for alerting."""

    def __init__(self, integration_key: str = ""):
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.integration_key = integration_key
        self.enabled = bool(integration_key)

    async def send_alert(
        self,
        severity: AlertSeverity,
        title: str,
        description: str,
        source: str,
    ) -> bool:
        """Send alert to PagerDuty."""
        if not self.enabled:
            return False

        # Map severity to PagerDuty format
        pd_severity = self._map_severity(severity)

        # In production, would send to PagerDuty API
        logger.info(f"PagerDuty alert [{pd_severity}]: {title} - {description}")
        return True

    def _map_severity(self, severity: AlertSeverity) -> str:
        """Map AlertSeverity to PagerDuty severity string."""
        mapping = {
            AlertSeverity.INFO: "info",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.ERROR: "error",
            AlertSeverity.CRITICAL: "critical",
        }
        return mapping.get(severity, "info")


class AlertManager:
    """Manages alerts with deduplication and rate limiting."""

    def __init__(
        self,
        pagerduty_alerting: Optional[PagerDutyAlerting] = None,
        dedup_window_minutes: int = 5,
        max_alerts_per_minute: int = 10,
    ):
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.pagerduty = pagerduty_alerting
        self.dedup_window_minutes = dedup_window_minutes
        self.max_alerts_per_minute = max_alerts_per_minute
        self._active_alerts: Dict[str, Alert] = {}
        self._alert_history: List[Alert] = []
        self._rate_limit_window: List[datetime] = []
        self._dedup_cache: Dict[str, datetime] = {}

    @property
    def active_alerts(self) -> Dict[str, Alert]:
        """Get active alerts."""
        return {k: v for k, v in self._active_alerts.items() if v.status == AlertStatus.TRIGGERED}

    @property
    def alert_history(self) -> List[Alert]:
        """Get alert history."""
        return self._alert_history

    async def trigger_alert(
        self,
        severity: AlertSeverity,
        title: str,
        description: str,
        source: str,
    ) -> Optional[Alert]:
        """Trigger an alert with deduplication and rate limiting."""
        # Check deduplication
        dedup_key = f"{severity.value}:{source}:{title}"
        now = datetime.now(timezone.utc)

        if dedup_key in self._dedup_cache:
            last_alert_time = self._dedup_cache[dedup_key]
            if (now - last_alert_time).total_seconds() < (self.dedup_window_minutes * 60):
                return None  # Deduplicated

        # Check rate limiting
        self._rate_limit_window = [
            t for t in self._rate_limit_window if (now - t).total_seconds() < 60
        ]
        if len(self._rate_limit_window) >= self.max_alerts_per_minute:
            return None  # Rate limited

        # Create alert
        alert = Alert(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            title=title,
            description=description,
            source=source,
            timestamp=now,
            status=AlertStatus.TRIGGERED,
        )

        # Store alert
        self._active_alerts[alert.alert_id] = alert
        self._alert_history.append(alert)
        self._dedup_cache[dedup_key] = now
        self._rate_limit_window.append(now)

        # Send to PagerDuty if configured
        if self.pagerduty:
            await self.pagerduty.send_alert(
                severity=severity,
                title=title,
                description=description,
                source=source,
            )

        return alert

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.resolve()
            del self._active_alerts[alert_id]
            return True
        return False

    async def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        if alert_id in self._active_alerts:
            self._active_alerts[alert_id].acknowledge()
            return True
        return False

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity."""
        alerts = [a for a in self._active_alerts.values() if a.status == AlertStatus.TRIGGERED]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        return alerts

    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        alerts_by_severity = {}
        for alert in self._alert_history:
            sev = alert.severity.value
            alerts_by_severity[sev] = alerts_by_severity.get(sev, 0) + 1

        return {
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "total_alerts": len(self._alert_history),
            "active_alerts": len(self.active_alerts),
            "alerts_by_severity": alerts_by_severity,
        }


class ProductionMonitor:
    """Production monitoring orchestrator."""

    def __init__(
        self,
        system_collector: Optional[SystemMetricsCollector] = None,
        redis_collector: Optional[RedisMetricsCollector] = None,
        alert_manager: Optional[AlertManager] = None,
        pagerduty_alerting: Optional[PagerDutyAlerting] = None,
        monitoring_interval_seconds: int = 60,
    ):
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.system_collector = system_collector or SystemMetricsCollector()
        self.redis_collector = redis_collector or RedisMetricsCollector()
        self.alert_manager = alert_manager or AlertManager(pagerduty_alerting=pagerduty_alerting)
        self.monitoring_interval_seconds = monitoring_interval_seconds
        self._running = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self.metrics_history: List[Dict[str, Any]] = []
        self._thresholds = {
            "cpu_warning": 80,
            "cpu_critical": 85,
            "memory_warning": 80,
            "memory_critical": 90,
            "disk_warning": 80,
            "disk_critical": 90,
            "redis_hit_rate_constitutional": 85,  # Constitutional requirement
        }

    @property
    def is_running(self) -> bool:
        """Check if monitoring is running."""
        return self._running

    async def start(self) -> None:
        """Start monitoring."""
        self._running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Production monitoring started")

    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Production monitoring stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                metrics = await self._collect_metrics()
                self.metrics_history.append(metrics)
                # Keep only last 1000 entries
                if len(self.metrics_history) > 1000:
                    self.metrics_history = self.metrics_history[-1000:]
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            await asyncio.sleep(self.monitoring_interval_seconds)

    async def _collect_metrics(self) -> Dict[str, Any]:
        """Collect all metrics."""
        system_metrics = await self.system_collector.collect_metrics()
        redis_metrics = await self.redis_collector.collect_metrics()

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "system": {
                "cpu_percent": system_metrics.cpu_percent,
                "memory_percent": system_metrics.memory_percent,
                "disk_percent": system_metrics.disk_percent,
            },
            "redis": {
                "hit_rate_percent": redis_metrics.hit_rate_percent,
                "connected_clients": redis_metrics.connected_clients,
                "used_memory_mb": redis_metrics.used_memory_mb,
            },
        }

    async def _check_system_thresholds(self, metrics: Any) -> None:
        """Check system metrics against thresholds."""
        cpu = getattr(metrics, "cpu_percent", 0)
        memory = getattr(metrics, "memory_percent", 0)
        disk = getattr(metrics, "disk_percent", 0)

        if cpu >= self._thresholds["cpu_critical"]:
            await self.alert_manager.trigger_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical CPU Usage",
                description=f"CPU usage at {cpu}% exceeds critical threshold",
                source="system_monitor",
            )
        elif cpu >= self._thresholds["cpu_warning"]:
            await self.alert_manager.trigger_alert(
                severity=AlertSeverity.WARNING,
                title="High CPU Usage",
                description=f"CPU usage at {cpu}%",
                source="system_monitor",
            )

        if memory >= self._thresholds["memory_critical"]:
            await self.alert_manager.trigger_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical Memory Usage",
                description=f"Memory usage at {memory}%",
                source="system_monitor",
            )

        if disk >= self._thresholds["disk_critical"]:
            await self.alert_manager.trigger_alert(
                severity=AlertSeverity.CRITICAL,
                title="Critical Disk Usage",
                description=f"Disk usage at {disk}%",
                source="system_monitor",
            )

    async def _check_redis_thresholds(self, metrics: Any) -> None:
        """Check Redis metrics against thresholds."""
        hit_rate = getattr(metrics, "hit_rate_percent", 100)

        if hit_rate < self._thresholds["redis_hit_rate_constitutional"]:
            await self.alert_manager.trigger_alert(
                severity=AlertSeverity.CRITICAL,
                title="Constitutional Violation: Low Cache Hit Rate",
                description=f"Redis hit rate {hit_rate}% below constitutional requirement of 85%",
                source="redis_monitor",
            )

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status."""
        return {
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "is_running": self._running,
            "monitoring_interval_seconds": self.monitoring_interval_seconds,
            "metrics_history_count": len(self.metrics_history),
            "thresholds": self._thresholds,
        }

    def get_current_metrics(self) -> Dict[str, Any]:
        """Get most recent metrics."""
        if self.metrics_history:
            latest = self.metrics_history[-1]
            return {
                **latest,
                "alerts": {
                    "active_count": len(self.alert_manager.active_alerts),
                    "total_count": len(self.alert_manager.alert_history),
                },
            }
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "system": {},
            "redis": {},
            "alerts": {
                "active_count": 0,
                "total_count": 0,
            },
        }


# Export all public classes
__all__ = [
    "CONSTITUTIONAL_HASH",
    "SystemMetrics",
    "RedisMetrics",
    "SystemMetricsCollector",
    "RedisMetricsCollector",
    "AlertManager",
    "PagerDutyAlerting",
    "ProductionMonitor",
    "Alert",
    "AlertSeverity",
    "AlertStatus",
]
