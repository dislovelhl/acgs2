"""
ACGS-2 Enterprise Dashboard Engine
Real-time KPIs, alerting, and monitoring dashboards
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import prometheus_client as prom

logger = logging.getLogger(__name__)


class DashboardType(Enum):
    """Types of monitoring dashboards"""

    EXECUTIVE = "executive"
    OPERATIONAL = "operational"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    CHAOS_ENGINEERING = "chaos_engineering"


class KPICategory(Enum):
    """KPI categories"""

    AVAILABILITY = "availability"
    PERFORMANCE = "performance"
    SECURITY = "security"
    COMPLIANCE = "compliance"
    BUSINESS = "business"
    OPERATIONAL = "operational"


class AlertSeverity(Enum):
    """Alert severity levels"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class MetricType(Enum):
    """Types of metrics"""

    GAUGE = "gauge"
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class KPI:
    """Key Performance Indicator"""

    id: str
    name: str
    description: str
    category: KPICategory
    metric_type: MetricType
    query: str  # PromQL or similar query
    unit: str
    target_value: Optional[float] = None
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    refresh_interval_seconds: int = 30


@dataclass
class AlertRule:
    """Alert rule configuration"""

    id: str
    name: str
    description: str
    kpi_id: str
    condition: str  # e.g., "value > 90"
    severity: AlertSeverity
    duration_seconds: int = 300  # How long condition must be true
    cooldown_minutes: int = 5
    channels: List[str] = field(default_factory=lambda: ["email"])
    enabled: bool = True


@dataclass
class DashboardPanel:
    """Dashboard panel configuration"""

    id: str
    title: str
    kpi_ids: List[str]
    chart_type: str  # line, bar, gauge, table, etc.
    time_range: str = "1h"
    refresh_interval_seconds: int = 30
    width: int = 6  # Grid width (1-12)
    height: int = 4
    position: Dict[str, int] = field(default_factory=dict)


@dataclass
class Dashboard:
    """Complete dashboard configuration"""

    id: str
    name: str
    description: str
    dashboard_type: DashboardType
    panels: List[DashboardPanel]
    tags: List[str] = field(default_factory=list)
    refresh_interval_seconds: int = 30
    auto_refresh: bool = True
    public_access: bool = False
    owner: str = "system"
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class KPIValue:
    """KPI value at a point in time"""

    kpi_id: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ActiveAlert:
    """Currently active alert"""

    id: str
    rule_id: str
    kpi_id: str
    severity: AlertSeverity
    message: str
    value: float
    threshold: float
    started_at: datetime
    last_notification: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


@dataclass
class AlertNotification:
    """Alert notification record"""

    id: str
    alert_id: str
    channel: str
    recipient: str
    message: str
    sent_at: datetime
    status: str  # sent, failed, pending


class EnterpriseDashboardEngine:
    """Enterprise dashboard engine with real-time monitoring"""

    def __init__(self):
        self.kpis: Dict[str, KPI] = {}
        self.alert_rules: Dict[str, AlertRule] = {}
        self.dashboards: Dict[str, Dashboard] = {}
        self.active_alerts: Dict[str, ActiveAlert] = {}
        self.kpi_values: Dict[str, List[KPIValue]] = defaultdict(list)
        self.alert_notifications: List[AlertNotification] = []

        # Metrics storage
        self.kpi_gauges: Dict[str, prom.Gauge] = {}
        self.alert_counters: Dict[str, prom.Counter] = {}

        # Callbacks
        self.alert_callbacks: List[Callable[[ActiveAlert], None]] = []
        self.kpi_callbacks: List[Callable[[KPIValue], None]] = []

        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.alerting_task: Optional[asyncio.Task] = None

    async def start_monitoring(self) -> None:
        """Start the monitoring engine"""
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.alerting_task = asyncio.create_task(self._alerting_loop())

    async def stop_monitoring(self) -> None:
        """Stop the monitoring engine"""
        if self.monitoring_task:
            self.monitoring_task.cancel()
        if self.alerting_task:
            self.alerting_task.cancel()

    def register_kpi(self, kpi: KPI) -> None:
        """Register a KPI"""
        self.kpis[kpi.id] = kpi

        # Create Prometheus metric
        if kpi.metric_type == MetricType.GAUGE:
            self.kpi_gauges[kpi.id] = prom.Gauge(
                f"acgs2_kpi_{kpi.id}", kpi.description, labelnames=["category", "unit"]
            )

    def register_alert_rule(self, rule: AlertRule) -> None:
        """Register an alert rule"""
        self.alert_rules[rule.id] = rule

        # Create alert counter
        self.alert_counters[rule.id] = prom.Counter(
            f"acgs2_alerts_{rule.id}_total", f"Alert count for {rule.name}", ["severity"]
        )

    def register_dashboard(self, dashboard: Dashboard) -> None:
        """Register a dashboard"""
        self.dashboards[dashboard.id] = dashboard

    def add_alert_callback(self, callback: Callable[[ActiveAlert], None]) -> None:
        """Add alert callback"""
        self.alert_callbacks.append(callback)

    def add_kpi_callback(self, callback: Callable[[KPIValue], None]) -> None:
        """Add KPI callback"""
        self.kpi_callbacks.append(callback)

    async def update_kpi_value(
        self, kpi_id: str, value: float, labels: Dict[str, str] = None
    ) -> None:
        """Update a KPI value"""
        if kpi_id not in self.kpis:
            return

        kpi = self.kpis[kpi_id]
        kpi_value = KPIValue(
            kpi_id=kpi_id, value=value, timestamp=datetime.utcnow(), labels=labels or {}
        )

        # Store value
        self.kpi_values[kpi_id].append(kpi_value)

        # Keep only recent values (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        self.kpi_values[kpi_id] = [v for v in self.kpi_values[kpi_id] if v.timestamp > cutoff]

        # Update Prometheus metric
        if kpi_id in self.kpi_gauges:
            gauge = self.kpi_gauges[kpi_id]
            gauge.labels(category=kpi.category.value, unit=kpi.unit).set(value)

        # Notify callbacks
        for callback in self.kpi_callbacks:
            try:
                callback(kpi_value)
            except Exception as e:
                logger.error(f"KPI callback failed: {e}")

    async def get_kpi_data(self, kpi_id: str, time_range: str = "1h") -> List[KPIValue]:
        """Get KPI data for a time range"""
        if kpi_id not in self.kpi_values:
            return []

        # Parse time range
        if time_range.endswith("h"):
            hours = int(time_range[:-1])
            cutoff = datetime.utcnow() - timedelta(hours=hours)
        elif time_range.endswith("m"):
            minutes = int(time_range[:-1])
            cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        else:
            cutoff = datetime.utcnow() - timedelta(hours=1)

        return [value for value in self.kpi_values[kpi_id] if value.timestamp > cutoff]

    async def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get complete dashboard data"""
        if dashboard_id not in self.dashboards:
            return {}

        dashboard = self.dashboards[dashboard_id]
        dashboard_data = {
            "dashboard": {
                "id": dashboard.id,
                "name": dashboard.name,
                "description": dashboard.description,
                "type": dashboard.dashboard_type.value,
                "refresh_interval": dashboard.refresh_interval_seconds,
            },
            "panels": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

        for panel in dashboard.panels:
            panel_data = {
                "id": panel.id,
                "title": panel.title,
                "chart_type": panel.chart_type,
                "kpis": [],
            }

            for kpi_id in panel.kpi_ids:
                kpi_data = await self.get_kpi_data(kpi_id, panel.time_range)
                if kpi_data:
                    panel_data["kpis"].append(
                        {
                            "id": kpi_id,
                            "name": self.kpis[kpi_id].name,
                            "data": [
                                {
                                    "timestamp": v.timestamp.isoformat(),
                                    "value": v.value,
                                    "labels": v.labels,
                                }
                                for v in kpi_data[-100:]  # Last 100 points
                            ],
                            "unit": self.kpis[kpi_id].unit,
                            "target": self.kpis[kpi_id].target_value,
                        }
                    )

            dashboard_data["panels"].append(panel_data)

        return dashboard_data

    def acknowledge_alert(self, alert_id: str, user: str) -> bool:
        """Acknowledge an alert"""
        if alert_id not in self.active_alerts:
            return False

        alert = self.active_alerts[alert_id]
        alert.acknowledged_by = user
        alert.acknowledged_at = datetime.utcnow()

        return True

    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            del self.active_alerts[alert_id]
            return True
        return False

    def get_active_alerts(self, severity: AlertSeverity = None) -> List[ActiveAlert]:
        """Get active alerts"""
        alerts = list(self.active_alerts.values())

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return sorted(alerts, key=lambda x: x.started_at, reverse=True)

    def get_alert_history(self, hours: int = 24) -> List[AlertNotification]:
        """Get alert notification history"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            notification
            for notification in self.alert_notifications
            if notification.sent_at > cutoff
        ]

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        while True:
            try:
                # Collect KPI data
                await self._collect_kpi_data()

                # Check alert conditions
                await self._check_alert_conditions()

                # Cleanup old data
                self._cleanup_old_data()

                await asyncio.sleep(30)  # Update every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(30)

    async def _alerting_loop(self) -> None:
        """Alert notification loop"""
        while True:
            try:
                # Send pending notifications
                await self._send_alert_notifications()

                # Check for alert escalation
                await self._check_alert_escalation()

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Alerting loop error: {e}")
                await asyncio.sleep(60)

    async def _collect_kpi_data(self) -> None:
        """Collect data for all KPIs"""
        for kpi in self.kpis.values():
            try:
                # In a real implementation, this would query Prometheus, DataDog, etc.
                # For now, simulate data collection
                value = await self._simulate_kpi_collection(kpi)
                await self.update_kpi_value(kpi.id, value)

            except Exception as e:
                logger.error(f"Failed to collect KPI {kpi.id}: {e}")

    async def _simulate_kpi_collection(self, kpi: KPI) -> float:
        """Simulate KPI data collection"""
        # Generate realistic values based on KPI type
        base_value = 50.0

        if kpi.category == KPICategory.AVAILABILITY:
            base_value = 99.9 + (0.1 * (0.5 - time.time() % 1))  # 99.9% ± 0.05%
        elif kpi.category == KPICategory.PERFORMANCE:
            base_value = 100 + (20 * (0.5 - time.time() % 1))  # 100ms ± 10ms
        elif kpi.category == KPICategory.SECURITY:
            base_value = 0.1 + (0.05 * (time.time() % 1))  # 0.1% ± 0.025% threat rate
        elif kpi.category == KPICategory.COMPLIANCE:
            base_value = 98.0 + (2.0 * (0.5 - time.time() % 1))  # 98% ± 1%

        return max(0, base_value)

    async def _check_alert_conditions(self) -> None:
        """Check all alert conditions"""
        for rule in self.alert_rules.values():
            if not rule.enabled:
                continue

            try:
                await self._evaluate_alert_rule(rule)
            except Exception as e:
                logger.error(f"Failed to evaluate alert rule {rule.id}: {e}")

    async def _evaluate_alert_rule(self, rule: AlertRule) -> None:
        """Evaluate a single alert rule"""
        kpi_data = await self.get_kpi_data(rule.kpi_id, "5m")  # Last 5 minutes

        if not kpi_data:
            return

        # Check condition over the time window
        violation_count = 0
        for value in kpi_data:
            if self._check_condition(value.value, rule.condition):
                violation_count += 1

        # Check if condition is met for required duration
        time_window_seconds = rule.duration_seconds
        check_interval = 30  # 30 seconds between checks
        required_violations = time_window_seconds // check_interval

        if violation_count >= required_violations:
            await self._trigger_alert(rule, kpi_data[-1])

    def _check_condition(self, value: float, condition: str) -> bool:
        """Check if value meets condition"""
        try:
            # Simple condition parsing (e.g., "value > 90")
            if ">" in condition:
                threshold = float(condition.split(">")[1].strip())
                return value > threshold
            elif "<" in condition:
                threshold = float(condition.split("<")[1].strip())
                return value < threshold
            elif ">=" in condition:
                threshold = float(condition.split(">=")[1].strip())
                return value >= threshold
            elif "<=" in condition:
                threshold = float(condition.split("<=")[1].strip())
                return value <= threshold
            elif "==" in condition:
                threshold = float(condition.split("==")[1].strip())
                return abs(value - threshold) < 0.001
            else:
                return False
        except (ValueError, IndexError, AttributeError) as e:
            logger.warning(f"Failed to parse condition '{condition}': {e}")
            return False

    async def _trigger_alert(self, rule: AlertRule, kpi_value: KPIValue) -> None:
        """Trigger an alert"""
        alert_id = f"{rule.id}_{int(time.time())}"

        # Check if alert is already active
        if alert_id in self.active_alerts:
            return

        alert = ActiveAlert(
            id=alert_id,
            rule_id=rule.id,
            kpi_id=rule.kpi_id,
            severity=rule.severity,
            message=f"{rule.name}: {kpi_value.value:.2f} {rule.condition}",
            value=kpi_value.value,
            threshold=self._extract_threshold(rule.condition),
            started_at=datetime.utcnow(),
        )

        self.active_alerts[alert_id] = alert

        # Update Prometheus counter
        if rule.id in self.alert_counters:
            self.alert_counters[rule.id].labels(severity=rule.severity.value).inc()

        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback failed: {e}")

    def _extract_threshold(self, condition: str) -> float:
        """Extract threshold value from condition"""
        try:
            for op in [">=", "<=", ">", "<", "=="]:
                if op in condition:
                    return float(condition.split(op)[1].strip())
            return 0.0
        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to extract threshold from condition '{condition}': {e}")
            return 0.0

    async def _send_alert_notifications(self) -> None:
        """Send pending alert notifications"""
        for alert in self.active_alerts.values():
            if alert.last_notification:
                # Check cooldown
                cooldown_end = alert.last_notification + timedelta(minutes=5)  # Default cooldown
                if datetime.utcnow() < cooldown_end:
                    continue

            # Send notifications
            for channel in self.alert_rules[alert.rule_id].channels:
                await self._send_notification(alert, channel)

            alert.last_notification = datetime.utcnow()

    async def _send_notification(self, alert: ActiveAlert, channel: str) -> None:
        """Send notification via specific channel"""
        notification = AlertNotification(
            id=f"notif_{alert.id}_{channel}_{int(time.time())}",
            alert_id=alert.id,
            channel=channel,
            recipient=self._get_recipient_for_channel(channel),
            message=self._format_alert_message(alert),
            sent_at=datetime.utcnow(),
            status="pending",
        )

        try:
            # In a real implementation, this would send via email, Slack, etc.
            if channel == "email":
                await self._send_email_notification(notification)
            elif channel == "slack":
                await self._send_slack_notification(notification)
            elif channel == "pagerduty":
                await self._send_pagerduty_notification(notification)

            notification.status = "sent"

        except Exception as e:
            notification.status = "failed"
            logger.error(f"Failed to send {channel} notification: {e}")

        self.alert_notifications.append(notification)

    async def _send_email_notification(self, notification: AlertNotification) -> None:
        """Send email notification"""
        logger.info(f"Sending email to {notification.recipient}: {notification.message}")

    async def _send_slack_notification(self, notification: AlertNotification) -> None:
        """Send Slack notification"""
        logger.info(f"Sending Slack message: {notification.message}")

    async def _send_pagerduty_notification(self, notification: AlertNotification) -> None:
        """Send PagerDuty notification"""
        logger.info(f"Sending PagerDuty alert: {notification.message}")

    def _get_recipient_for_channel(self, channel: str) -> str:
        """Get recipient for notification channel"""
        # In a real implementation, this would look up recipients from config
        if channel == "email":
            return "alerts@acgs2.com"
        elif channel == "slack":
            return "#acgs2-alerts"
        elif channel == "pagerduty":
            return "ACGS2-OnCall"
        else:
            return "unknown"

    def _format_alert_message(self, alert: ActiveAlert) -> str:
        """Format alert message"""
        kpi = self.kpis[alert.kpi_id]
        return f"""
🚨 ACGS-2 Alert: {alert.severity.value.upper()}

{alert.message}

KPI: {kpi.name}
Threshold: {alert.threshold}
Current Value: {alert.value:.2f} {kpi.unit}

Started: {alert.started_at.isoformat()}
        """.strip()

    async def _check_alert_escalation(self) -> None:
        """Check for alert escalation"""
        for alert in self.active_alerts.values():
            age_minutes = (datetime.utcnow() - alert.started_at).total_seconds() / 60

            # Escalate after 30 minutes if not acknowledged
            if age_minutes > 30 and not alert.acknowledged_by:
                await self._escalate_alert(alert)

    async def _escalate_alert(self, alert: ActiveAlert) -> None:
        """Escalate an alert"""
        logger.info(f"Escalating alert {alert.id}")

        # Add escalation channels
        rule = self.alert_rules[alert.rule_id]
        if "pagerduty" not in rule.channels:
            rule.channels.append("pagerduty")

        # Send escalation notification
        escalation_notification = AlertNotification(
            id=f"escalation_{alert.id}_{int(time.time())}",
            alert_id=alert.id,
            channel="pagerduty",
            recipient="ACGS2-Escalation",
            message=f"ESCALATION: {self._format_alert_message(alert)}",
            sent_at=datetime.utcnow(),
            status="sent",
        )

        self.alert_notifications.append(escalation_notification)

    def _cleanup_old_data(self) -> None:
        """Cleanup old KPI data and resolved alerts"""
        # Keep KPI data for 24 hours
        cutoff = datetime.utcnow() - timedelta(hours=24)

        for kpi_id in self.kpi_values:
            self.kpi_values[kpi_id] = [
                value for value in self.kpi_values[kpi_id] if value.timestamp > cutoff
            ]

        # Keep alert notifications for 7 days
        notification_cutoff = datetime.utcnow() - timedelta(days=7)
        self.alert_notifications = [
            n for n in self.alert_notifications if n.sent_at > notification_cutoff
        ]

    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get monitoring engine statistics"""
        return {
            "kpis_registered": len(self.kpis),
            "alert_rules_registered": len(self.alert_rules),
            "dashboards_registered": len(self.dashboards),
            "active_alerts": len(self.active_alerts),
            "total_kpi_data_points": sum(len(values) for values in self.kpi_values.values()),
            "total_notifications": len(self.alert_notifications),
            "monitoring_active": self.monitoring_task is not None
            and not self.monitoring_task.done(),
            "alerting_active": self.alerting_task is not None and not self.alerting_task.done(),
        }


# Global dashboard engine instance
dashboard_engine = EnterpriseDashboardEngine()


# Convenience functions
async def start_monitoring() -> None:
    """Start the monitoring engine"""
    await dashboard_engine.start_monitoring()


async def register_dashboard_kpi(kpi: KPI) -> None:
    """Register a KPI"""
    dashboard_engine.register_kpi(kpi)


async def register_dashboard_alert(rule: AlertRule) -> None:
    """Register an alert rule"""
    dashboard_engine.register_alert_rule(rule)


async def get_dashboard_data(dashboard_id: str) -> Dict[str, Any]:
    """Get dashboard data"""
    return await dashboard_engine.get_dashboard_data(dashboard_id)


def get_monitoring_stats() -> Dict[str, Any]:
    """Get monitoring statistics"""
    return dashboard_engine.get_monitoring_stats()
