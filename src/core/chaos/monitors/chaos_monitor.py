"""
ACGS-2 Chaos Engineering Monitoring
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional

import aiofiles
import prometheus_client as prom


class MonitorSeverity(Enum):
    """Monitoring severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status"""

    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


@dataclass
class MetricThreshold:
    """Metric threshold configuration"""

    metric_name: str
    operator: str  # 'gt', 'lt', 'eq', 'ne'
    value: float
    duration_seconds: int
    severity: MonitorSeverity


@dataclass
class AlertRule:
    """Alert rule configuration"""

    id: str
    name: str
    description: str
    thresholds: List[MetricThreshold]
    channels: List[str]  # email, slack, pagerduty, etc.
    cooldown_minutes: int = 5
    enabled: bool = True


@dataclass
class Alert:
    """Active alert"""

    id: str
    rule_id: str
    experiment_id: str
    severity: MonitorSeverity
    message: str
    value: float
    threshold: float
    timestamp: datetime
    status: AlertStatus
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None


@dataclass
class SystemHealth:
    """System health snapshot"""

    timestamp: datetime
    services: Dict[str, bool]
    metrics: Dict[str, float]
    alerts: List[Alert]
    overall_status: str  # healthy, degraded, unhealthy


class ChaosMonitor:
    """Enterprise chaos monitoring system"""

    def __init__(self):
        self.logger = logging.getLogger("ChaosMonitor")
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.health_callbacks: List[Callable[[SystemHealth], None]] = []
        self.alert_callbacks: List[Callable[[Alert], None]] = []

        # Prometheus metrics
        self.alerts_total = prom.Counter(
            "chaos_alerts_total", "Total number of chaos alerts", ["severity", "status", "rule_id"]
        )

        self.health_status = prom.Gauge(
            "chaos_system_health_status",
            "Overall system health status (0=healthy, 1=degraded, 2=unhealthy)",
        )

        self.active_experiments = prom.Gauge(
            "chaos_active_experiments", "Number of currently active chaos experiments"
        )

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add an alert rule"""
        self.alert_rules[rule.id] = rule
        self.logger.info(f"Added alert rule: {rule.name}")

    def remove_alert_rule(self, rule_id: str) -> None:
        """Remove an alert rule"""
        if rule_id in self.alert_rules:
            del self.alert_rules[rule_id]
            self.logger.info(f"Removed alert rule: {rule_id}")

    def add_health_callback(self, callback: Callable[[SystemHealth], None]) -> None:
        """Add health monitoring callback"""
        self.health_callbacks.append(callback)

    def add_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add alert callback"""
        self.alert_callbacks.append(callback)

    async def monitor_experiment(self, experiment_id: str, duration_minutes: int) -> None:
        """Monitor a chaos experiment"""
        self.logger.info(f"Starting monitoring for experiment {experiment_id}")

        end_time = datetime.utcnow() + timedelta(minutes=duration_minutes)
        last_health_check = datetime.utcnow()

        while datetime.utcnow() < end_time:
            current_time = datetime.utcnow()

            # Periodic health check
            if (current_time - last_health_check).total_seconds() >= 30:
                health = await self.check_system_health(experiment_id)
                self._notify_health_callbacks(health)
                last_health_check = current_time

                # Update health status metric
                status_value = {"healthy": 0, "degraded": 1, "unhealthy": 2}.get(
                    health.overall_status, 2
                )
                self.health_status.set(status_value)

            # Check alert rules
            await self.check_alert_rules(experiment_id)

            await asyncio.sleep(10)  # Check every 10 seconds

        self.logger.info(f"Completed monitoring for experiment {experiment_id}")

    async def check_system_health(self, experiment_id: str) -> SystemHealth:
        """Check overall system health"""
        # In a real implementation, this would query various monitoring systems
        services = {
            "api_gateway": True,
            "agent_bus": True,
            "policy_engine": True,
            "audit_service": True,
            "database": True,
            "redis": True,
            "kafka": True,
        }

        metrics = {
            "cpu_usage_percent": 45.0,
            "memory_usage_percent": 60.0,
            "disk_usage_percent": 30.0,
            "network_latency_ms": 15.0,
            "error_rate_percent": 0.1,
        }

        # Determine overall status
        overall_status = "healthy"
        if any(not healthy for healthy in services.values()):
            overall_status = "unhealthy"
        elif any(value > 80 for value in metrics.values()):
            overall_status = "degraded"

        active_alerts = [
            alert
            for alert in self.active_alerts.values()
            if alert.experiment_id == experiment_id and alert.status == AlertStatus.ACTIVE
        ]

        return SystemHealth(
            timestamp=datetime.utcnow(),
            services=services,
            metrics=metrics,
            alerts=active_alerts,
            overall_status=overall_status,
        )

    async def check_alert_rules(self, experiment_id: str) -> None:
        """Check all alert rules and trigger alerts if necessary"""
        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue

            for threshold in rule.thresholds:
                if await self.check_threshold(experiment_id, threshold):
                    await self.trigger_alert(experiment_id, rule, threshold)

    async def check_threshold(self, experiment_id: str, threshold: MetricThreshold) -> bool:
        """Check if a metric threshold is breached"""
        # In a real implementation, this would query monitoring systems
        # For now, simulate some basic checks
        metric_value = await self.get_metric_value(threshold.metric_name, experiment_id)

        if threshold.operator == "gt" and metric_value > threshold.value:
            return True
        elif threshold.operator == "lt" and metric_value < threshold.value:
            return True
        elif threshold.operator == "eq" and metric_value == threshold.value:
            return True
        elif threshold.operator == "ne" and metric_value != threshold.value:
            return True

        return False

    async def get_metric_value(self, metric_name: str, experiment_id: str) -> float:
        """Get current metric value"""
        # In a real implementation, this would query Prometheus, DataDog, etc.
        # For simulation, return some reasonable values
        metrics = {
            "cpu_usage_percent": 45.0,
            "memory_usage_percent": 60.0,
            "disk_usage_percent": 30.0,
            "network_latency_ms": 15.0,
            "error_rate_percent": 0.1,
            "response_time_ms": 250.0,
            "throughput_rps": 150.0,
        }

        return metrics.get(metric_name, 0.0)

    async def trigger_alert(
        self, experiment_id: str, rule: AlertRule, threshold: MetricThreshold
    ) -> None:
        """Trigger an alert"""
        alert_id = f"{experiment_id}_{rule.id}_{threshold.metric_name}"

        # Check if alert is already active and within cooldown
        if alert_id in self.active_alerts:
            existing_alert = self.active_alerts[alert_id]
            if (datetime.utcnow() - existing_alert.timestamp).total_seconds() < (
                rule.cooldown_minutes * 60
            ):
                return  # Still in cooldown

        metric_value = await self.get_metric_value(threshold.metric_name, experiment_id)

        alert = Alert(
            id=alert_id,
            rule_id=rule.id,
            experiment_id=experiment_id,
            severity=threshold.severity,
            message=f"{rule.name}: {threshold.metric_name} {threshold.operator} "
            f"{threshold.value} (current: {metric_value})",
            value=metric_value,
            threshold=threshold.value,
            timestamp=datetime.utcnow(),
            status=AlertStatus.ACTIVE,
        )

        self.active_alerts[alert_id] = alert
        self.alerts_total.labels(
            severity=threshold.severity.value, status=AlertStatus.ACTIVE.value, rule_id=rule.id
        ).inc()

        # Notify callbacks
        self._notify_alert_callbacks(alert)

        # Send notifications
        await self.send_notifications(alert, rule.channels)

        self.logger.warning(f"Alert triggered: {alert.message}")

    async def send_notifications(self, alert: Alert, channels: List[str]) -> None:
        """Send alert notifications"""
        for channel in channels:
            if channel == "email":
                await self.send_email_alert(alert)
            elif channel == "slack":
                await self.send_slack_alert(alert)
            elif channel == "pagerduty":
                await self.send_pagerduty_alert(alert)

    async def send_email_alert(self, alert: Alert) -> None:
        """Send email alert"""
        # In a real implementation, this would use SMTP or a service like SendGrid
        self.logger.info(f"Sending email alert: {alert.message}")

    async def send_slack_alert(self, alert: Alert) -> None:
        """Send Slack alert"""
        # In a real implementation, this would use Slack API
        self.logger.info(f"Sending Slack alert: {alert.message}")

    async def send_pagerduty_alert(self, alert: Alert) -> None:
        """Send PagerDuty alert"""
        # In a real implementation, this would use PagerDuty API
        self.logger.info(f"Sending PagerDuty alert: {alert.message}")

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert"""
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_by = user
        alert.acknowledged_at = datetime.utcnow()

        self.alerts_total.labels(
            severity=alert.severity.value,
            status=AlertStatus.ACKNOWLEDGED.value,
            rule_id=alert.rule_id,
        ).inc()

        self.logger.info(f"Alert {alert_id} acknowledged by {user}")
        return True

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()

        self.alerts_total.labels(
            severity=alert.severity.value, status=AlertStatus.RESOLVED.value, rule_id=alert.rule_id
        ).inc()

        self.logger.info(f"Alert {alert_id} resolved")
        return True

    def get_active_alerts(self, experiment_id: Optional[str] = None) -> List[Alert]:
        """Get active alerts"""
        alerts = [
            alert for alert in self.active_alerts.values() if alert.status == AlertStatus.ACTIVE
        ]

        if experiment_id:
            alerts = [alert for alert in alerts if alert.experiment_id == experiment_id]

        return alerts

    def get_alert_history(
        self, experiment_id: Optional[str] = None, hours: int = 24
    ) -> List[Alert]:
        """Get alert history"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        alerts = [alert for alert in self.active_alerts.values() if alert.timestamp >= cutoff_time]

        if experiment_id:
            alerts = [alert for alert in alerts if alert.experiment_id == experiment_id]

        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)

    async def export_metrics(self, filepath: str) -> None:
        """Export monitoring metrics to file"""
        metrics_data = {
            "alerts_total": self.alerts_total._value,
            "active_alerts": len(self.get_active_alerts()),
            "alert_rules": len(self.alert_rules),
            "timestamp": datetime.utcnow().isoformat(),
        }

        async with aiofiles.open(filepath, "w") as f:
            await f.write(json.dumps(metrics_data, indent=2, default=str))

    def _notify_health_callbacks(self, health: SystemHealth) -> None:
        """Notify health monitoring callbacks"""
        for callback in self.health_callbacks:
            try:
                callback(health)
            except Exception as e:
                self.logger.error(f"Health callback failed: {e}")

    def _notify_alert_callbacks(self, alert: Alert) -> None:
        """Notify alert callbacks"""
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")


# Global monitor instance
monitor = ChaosMonitor()

# Default alert rules
default_alert_rules = [
    AlertRule(
        id="high_cpu_usage",
        name="High CPU Usage",
        description="CPU usage exceeds 80%",
        thresholds=[
            MetricThreshold(
                metric_name="cpu_usage_percent",
                operator="gt",
                value=80.0,
                duration_seconds=300,
                severity=MonitorSeverity.WARNING,
            )
        ],
        channels=["email", "slack"],
    ),
    AlertRule(
        id="high_memory_usage",
        name="High Memory Usage",
        description="Memory usage exceeds 85%",
        thresholds=[
            MetricThreshold(
                metric_name="memory_usage_percent",
                operator="gt",
                value=85.0,
                duration_seconds=300,
                severity=MonitorSeverity.ERROR,
            )
        ],
        channels=["email", "slack", "pagerduty"],
    ),
    AlertRule(
        id="high_error_rate",
        name="High Error Rate",
        description="Error rate exceeds 5%",
        thresholds=[
            MetricThreshold(
                metric_name="error_rate_percent",
                operator="gt",
                value=5.0,
                duration_seconds=60,
                severity=MonitorSeverity.CRITICAL,
            )
        ],
        channels=["email", "slack", "pagerduty"],
    ),
    AlertRule(
        id="high_latency",
        name="High Response Latency",
        description="Response latency exceeds 500ms",
        thresholds=[
            MetricThreshold(
                metric_name="response_time_ms",
                operator="gt",
                value=500.0,
                duration_seconds=60,
                severity=MonitorSeverity.WARNING,
            )
        ],
        channels=["email", "slack"],
    ),
    AlertRule(
        id="experiment_emergency",
        name="Experiment Emergency Stop",
        description="System health degraded during experiment",
        thresholds=[
            MetricThreshold(
                metric_name="system_health_score",
                operator="lt",
                value=0.5,
                duration_seconds=30,
                severity=MonitorSeverity.CRITICAL,
            )
        ],
        channels=["email", "slack", "pagerduty"],
        cooldown_minutes=1,
    ),
]

# Initialize default alert rules
for rule in default_alert_rules:
    monitor.add_alert_rule(rule)
