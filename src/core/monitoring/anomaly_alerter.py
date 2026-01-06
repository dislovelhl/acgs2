"""
ACGS-2 Real-Time Anomaly Alert Pipeline
Constitutional Hash: cdd01ef066bc6cf2

Real-time anomaly detection and alerting system for ACGS-2 governance platform.
Integrates with drift detection, impact scoring, and security scanners.
"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of alerts."""

    DRIFT = "drift"
    INJECTION = "injection"
    ANOMALY = "anomaly"
    SECURITY = "security"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    RATE_LIMIT = "rate_limit"
    ERROR = "error"


@dataclass
class Alert:
    """Represents an alert."""

    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    source: str  # Component that generated the alert
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False
    resolved: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_id": self.alert_id,
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


class AlertHandler:
    """Base class for alert handlers."""

    async def handle(self, alert: Alert) -> bool:
        """
        Handle an alert.

        Returns:
            True if handled successfully, False otherwise
        """
        raise NotImplementedError


class LoggingAlertHandler(AlertHandler):
    """Logs alerts to logger."""

    def __init__(self, logger_name: Optional[str] = None):
        self.logger = logging.getLogger(logger_name or __name__)

    async def handle(self, alert: Alert) -> bool:
        """Log alert."""
        level = {
            AlertSeverity.INFO: logging.INFO,
            AlertSeverity.LOW: logging.WARNING,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.CRITICAL: logging.CRITICAL,
        }.get(alert.severity, logging.WARNING)

        self.logger.log(
            level,
            f"[{alert.alert_type.value.upper()}] {alert.title}: {alert.message}",
            extra={"alert": alert.to_dict()},
        )
        return True


class WebhookAlertHandler(AlertHandler):
    """Sends alerts to webhook endpoint."""

    def __init__(self, webhook_url: str, timeout: float = 5.0):
        self.webhook_url = webhook_url
        self.timeout = timeout

    async def handle(self, alert: Alert) -> bool:
        """Send alert to webhook."""
        try:
            import httpx

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.webhook_url, json=alert.to_dict())
                response.raise_for_status()
                return True
        except ImportError:
            logger.warning("httpx not available for webhook alerts")
            return False
        except Exception as e:
            logger.error(f"Failed to send alert to webhook: {e}")
            return False


class EmailAlertHandler(AlertHandler):
    """Sends alerts via email (placeholder)."""

    def __init__(self, recipients: List[str], smtp_config: Optional[Dict[str, Any]] = None):
        self.recipients = recipients
        self.smtp_config = smtp_config or {}

    async def handle(self, alert: Alert) -> bool:
        """Send alert via email."""
        # Placeholder - would integrate with email service
        logger.info(f"Email alert would be sent to {self.recipients}: {alert.title}")
        return True


class SlackAlertHandler(AlertHandler):
    """Sends alerts to Slack."""

    def __init__(self, webhook_url: str, channel: Optional[str] = None):
        self.webhook_url = webhook_url
        self.channel = channel

    async def handle(self, alert: Alert) -> bool:
        """Send alert to Slack."""
        try:
            import httpx

            # Format alert for Slack
            color = {
                AlertSeverity.INFO: "#36a64f",
                AlertSeverity.LOW: "#ffcc00",
                AlertSeverity.MEDIUM: "#ff9900",
                AlertSeverity.HIGH: "#ff0000",
                AlertSeverity.CRITICAL: "#8b0000",
            }.get(alert.severity, "#808080")

            payload = {
                "text": f"ACGS-2 Alert: {alert.title}",
                "attachments": [
                    {
                        "color": color,
                        "fields": [
                            {"title": "Severity", "value": alert.severity.value, "short": True},
                            {"title": "Type", "value": alert.alert_type.value, "short": True},
                            {"title": "Source", "value": alert.source, "short": True},
                            {"title": "Message", "value": alert.message, "short": False},
                        ],
                        "ts": int(alert.timestamp.timestamp()),
                    }
                ],
            }

            if self.channel:
                payload["channel"] = self.channel

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                return True
        except ImportError:
            logger.warning("httpx not available for Slack alerts")
            return False
        except Exception as e:
            logger.error(f"Failed to send alert to Slack: {e}")
            return False


class AnomalyAlerter:
    """
    Real-time anomaly alert pipeline for ACGS-2.

    Features:
    - Multi-handler alert routing
    - Alert deduplication
    - Severity-based filtering
    - Alert aggregation
    - Acknowledgment tracking
    - Integration with drift detection and security scanners
    """

    def __init__(
        self,
        handlers: Optional[List[AlertHandler]] = None,
        deduplication_window: int = 300,  # 5 minutes
        min_severity: AlertSeverity = AlertSeverity.LOW,
    ):
        """
        Initialize anomaly alerter.

        Args:
            handlers: List of alert handlers
            deduplication_window: Window in seconds for deduplication
            min_severity: Minimum severity to alert
        """
        self.handlers = handlers or [LoggingAlertHandler()]
        self.deduplication_window = deduplication_window
        self.min_severity = min_severity

        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=10000)
        self.alert_counts: Dict[str, int] = {}  # Count by type/severity
        self._lock = asyncio.Lock()

    async def alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Alert]:
        """
        Create and send an alert.

        Args:
            alert_type: Type of alert
            severity: Severity level
            title: Alert title
            message: Alert message
            source: Source component
            metadata: Optional metadata

        Returns:
            Alert object if sent, None if filtered/deduplicated
        """
        # Check minimum severity
        if self._severity_value(severity) < self._severity_value(self.min_severity):
            return None

        # Generate alert ID
        alert_id = self._generate_alert_id(alert_type, severity, title, source)

        # Check for duplicate
        if await self._is_duplicate(alert_id):
            return None

        # Create alert
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            source=source,
            metadata=metadata or {},
        )

        async with self._lock:
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)

            # Update counts
            key = f"{alert_type.value}:{severity.value}"
            self.alert_counts[key] = self.alert_counts.get(key, 0) + 1

        # Send to all handlers
        await self._send_to_handlers(alert)

        return alert

    async def _is_duplicate(self, alert_id: str) -> bool:
        """Check if alert is a duplicate within deduplication window."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            age = (datetime.now(timezone.utc) - alert.timestamp).total_seconds()
            if age < self.deduplication_window:
                return True
        return False

    async def _send_to_handlers(self, alert: Alert):
        """Send alert to all handlers."""
        tasks = [handler.handle(alert) for handler in self.handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Handler {i} failed: {result}")
            elif not result:
                logger.warning(f"Handler {i} returned False")

    def _generate_alert_id(
        self, alert_type: AlertType, severity: AlertSeverity, title: str, source: str
    ) -> str:
        """Generate unique alert ID."""
        import hashlib

        content = f"{alert_type.value}:{severity.value}:{title}:{source}"
        hash_obj = hashlib.md5(content.encode())
        return f"{alert_type.value}_{hash_obj.hexdigest()[:8]}"

    @staticmethod
    def _severity_value(severity: AlertSeverity) -> int:
        """Get numeric value for severity comparison."""
        return {
            AlertSeverity.INFO: 0,
            AlertSeverity.LOW: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.HIGH: 3,
            AlertSeverity.CRITICAL: 4,
        }.get(severity, 0)

    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert."""
        async with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now(timezone.utc)
                return True
        return False

    async def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an alert."""
        async with self._lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                # Keep in history but remove from active
                del self.active_alerts[alert_id]
                return True
        return False

    def get_active_alerts(
        self,
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        source: Optional[str] = None,
    ) -> List[Alert]:
        """Get active alerts with optional filtering."""
        alerts = list(self.active_alerts.values())

        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        if source:
            alerts = [a for a in alerts if a.source == source]

        return sorted(alerts, key=lambda a: self._severity_value(a.severity), reverse=True)

    def get_statistics(self) -> Dict[str, Any]:
        """Get alert statistics."""
        return {
            "active_alerts": len(self.active_alerts),
            "total_alerts": len(self.alert_history),
            "by_type": {
                alert_type.value: len(
                    [a for a in self.active_alerts.values() if a.alert_type == alert_type]
                )
                for alert_type in AlertType
            },
            "by_severity": {
                severity.value: len(
                    [a for a in self.active_alerts.values() if a.severity == severity]
                )
                for severity in AlertSeverity
            },
            "alert_counts": self.alert_counts,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    # Convenience methods for common alert types
    async def alert_drift(
        self,
        agent_id: str,
        drift_type: str,
        severity: AlertSeverity,
        deviation_score: float,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Alert for context drift detection."""
        return await self.alert(
            alert_type=AlertType.DRIFT,
            severity=severity,
            title=f"Context drift detected for agent {agent_id}",
            message=f"Drift type: {drift_type}, Deviation score: {deviation_score:.2f}",
            source="context_drift_detector",
            metadata={
                "agent_id": agent_id,
                "drift_type": drift_type,
                "deviation_score": deviation_score,
                **(metadata or {}),
            },
        )

    async def alert_injection(
        self,
        agent_id: Optional[str],
        injection_type: str,
        severity: AlertSeverity,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Alert for prompt injection detection."""
        return await self.alert(
            alert_type=AlertType.INJECTION,
            severity=severity,
            title="Prompt injection detected",
            message=f"Injection type: {injection_type}, Confidence: {confidence:.2f}",
            source="injection_detector",
            metadata={
                "agent_id": agent_id,
                "injection_type": injection_type,
                "confidence": confidence,
                **(metadata or {}),
            },
        )

    async def alert_anomaly(
        self,
        source: str,
        anomaly_type: str,
        severity: AlertSeverity,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Alert for general anomaly."""
        return await self.alert(
            alert_type=AlertType.ANOMALY,
            severity=severity,
            title=f"Anomaly detected: {anomaly_type}",
            message=description,
            source=source,
            metadata={
                "anomaly_type": anomaly_type,
                **(metadata or {}),
            },
        )

    async def alert_security(
        self,
        source: str,
        security_event: str,
        severity: AlertSeverity,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Alert for security events."""
        return await self.alert(
            alert_type=AlertType.SECURITY,
            severity=severity,
            title=f"Security event: {security_event}",
            message=description,
            source=source,
            metadata={
                "security_event": security_event,
                **(metadata or {}),
            },
        )


# Global instance
_alerter: Optional[AnomalyAlerter] = None


def get_alerter() -> AnomalyAlerter:
    """Get the global anomaly alerter instance."""
    global _alerter
    if _alerter is None:
        _alerter = AnomalyAlerter()
    return _alerter


def configure_alerter(
    handlers: Optional[List[AlertHandler]] = None,
    min_severity: AlertSeverity = AlertSeverity.LOW,
) -> AnomalyAlerter:
    """Configure and return the global alerter."""
    global _alerter
    _alerter = AnomalyAlerter(handlers=handlers, min_severity=min_severity)
    return _alerter
