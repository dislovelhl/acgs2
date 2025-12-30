"""
ACGS-2 Alerting Module
Constitutional Hash: cdd01ef066bc6cf2

Alert management with severity levels and status tracking.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class AlertSeverity(Enum):
    """Alert severity levels."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(Enum):
    """Alert status values."""

    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


@dataclass
class Alert:
    """Alert data class with lifecycle management."""

    title: str
    description: str = ""
    severity: AlertSeverity = AlertSeverity.INFO
    source: str = "unknown"
    status: AlertStatus = AlertStatus.TRIGGERED
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    constitutional_hash: str = CONSTITUTIONAL_HASH
    metadata: Dict[str, Any] = field(default_factory=dict)
    acknowledgment_time: Optional[datetime] = None
    resolution_time: Optional[datetime] = None

    def acknowledge(self) -> None:
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledgment_time = datetime.now(timezone.utc)

    def resolve(self) -> None:
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolution_time = datetime.now(timezone.utc)

    def duration(self) -> Optional[timedelta]:
        """Calculate alert duration from trigger to resolution."""
        if self.resolution_time is None:
            return None
        return self.resolution_time - self.timestamp


__all__ = [
    "CONSTITUTIONAL_HASH",
    "AlertSeverity",
    "AlertStatus",
    "Alert",
]
