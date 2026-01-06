"""
Escalation Models for HITL Approvals.
Constitutional Hash: cdd01ef066bc6cf2
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from app.config import settings
from app.models import ApprovalPriority

from .enums import EscalationReason

# SLA warning threshold (percentage of timeout before warning)
DEFAULT_SLA_WARNING_THRESHOLD_PERCENT = 75


@dataclass
class SLAConfig:
    """Configuration for SLA thresholds and monitoring."""

    critical_timeout_minutes: int = field(
        default_factory=lambda: settings.critical_escalation_timeout_minutes
    )
    high_timeout_minutes: int = field(
        default_factory=lambda: int(settings.default_escalation_timeout_minutes * 0.75)
    )
    medium_timeout_minutes: int = field(
        default_factory=lambda: settings.default_escalation_timeout_minutes
    )
    low_timeout_minutes: int = field(
        default_factory=lambda: int(settings.default_escalation_timeout_minutes * 1.5)
    )
    warning_threshold_percent: int = DEFAULT_SLA_WARNING_THRESHOLD_PERCENT
    max_escalations: int = 3
    pagerduty_on_critical: bool = True

    def get_timeout_for_priority(self, priority: ApprovalPriority) -> int:
        if priority == ApprovalPriority.CRITICAL:
            return self.critical_timeout_minutes
        elif priority == ApprovalPriority.HIGH:
            return self.high_timeout_minutes
        elif priority == ApprovalPriority.MEDIUM:
            return self.medium_timeout_minutes
        else:  # LOW
            return self.low_timeout_minutes

    def get_warning_threshold_minutes(self, priority: ApprovalPriority) -> float:
        timeout = self.get_timeout_for_priority(priority)
        return timeout * (self.warning_threshold_percent / 100)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "critical_timeout_minutes": self.critical_timeout_minutes,
            "high_timeout_minutes": self.high_timeout_minutes,
            "medium_timeout_minutes": self.medium_timeout_minutes,
            "low_timeout_minutes": self.low_timeout_minutes,
            "warning_threshold_percent": self.warning_threshold_percent,
            "max_escalations": self.max_escalations,
            "pagerduty_on_critical": self.pagerduty_on_critical,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SLAConfig":
        return cls(
            critical_timeout_minutes=int(data.get("critical_timeout_minutes", 15)),
            high_timeout_minutes=int(data.get("high_timeout_minutes", 22)),
            medium_timeout_minutes=int(data.get("medium_timeout_minutes", 30)),
            low_timeout_minutes=int(data.get("low_timeout_minutes", 45)),
            warning_threshold_percent=int(data.get("warning_threshold_percent", 75)),
            max_escalations=int(data.get("max_escalations", 3)),
            pagerduty_on_critical=bool(data.get("pagerduty_on_critical", True)),
        )


@dataclass
class SLAMetrics:
    """Tracks SLA compliance metrics over time."""

    total_requests: int = 0
    completed_within_sla: int = 0
    sla_breaches: int = 0
    warnings_triggered: int = 0
    escalations_performed: int = 0
    total_response_time_seconds: float = 0.0
    min_response_time_seconds: float = float("inf")
    max_response_time_seconds: float = 0.0
    breaches_by_priority: Dict[str, int] = field(default_factory=dict)
    escalations_by_priority: Dict[str, int] = field(default_factory=dict)
    window_start: Optional[float] = None
    window_end: Optional[float] = None

    @property
    def compliance_rate(self) -> float:
        if self.total_requests == 0:
            return 100.0
        return (self.completed_within_sla / self.total_requests) * 100

    @property
    def breach_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.sla_breaches / self.total_requests) * 100

    @property
    def average_response_time_seconds(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time_seconds / self.total_requests

    @property
    def average_response_time_minutes(self) -> float:
        return self.average_response_time_seconds / 60

    def record_completion(
        self, response_time_seconds: float, within_sla: bool, priority: ApprovalPriority
    ) -> None:
        self.total_requests += 1
        self.total_response_time_seconds += response_time_seconds
        self.min_response_time_seconds = min(self.min_response_time_seconds, response_time_seconds)
        self.max_response_time_seconds = max(self.max_response_time_seconds, response_time_seconds)
        if within_sla:
            self.completed_within_sla += 1

    def record_breach(self, priority: ApprovalPriority) -> None:
        self.sla_breaches += 1
        priority_key = priority.value
        self.breaches_by_priority[priority_key] = self.breaches_by_priority.get(priority_key, 0) + 1

    def record_escalation(self, priority: ApprovalPriority) -> None:
        self.escalations_performed += 1
        priority_key = priority.value
        self.escalations_by_priority[priority_key] = (
            self.escalations_by_priority.get(priority_key, 0) + 1
        )

    def record_warning(self) -> None:
        self.warnings_triggered += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_requests": self.total_requests,
            "completed_within_sla": self.completed_within_sla,
            "sla_breaches": self.sla_breaches,
            "warnings_triggered": self.warnings_triggered,
            "escalations_performed": self.escalations_performed,
            "total_response_time_seconds": self.total_response_time_seconds,
            "min_response_time_seconds": self.min_response_time_seconds,
            "max_response_time_seconds": self.max_response_time_seconds,
            "breaches_by_priority": self.breaches_by_priority,
            "escalations_by_priority": self.escalations_by_priority,
            "compliance_rate": self.compliance_rate,
            "breach_rate": self.breach_rate,
            "average_response_time_seconds": self.average_response_time_seconds,
            "window_start": self.window_start,
            "window_end": self.window_end,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SLAMetrics":
        metrics = cls(
            total_requests=int(data.get("total_requests", 0)),
            completed_within_sla=int(data.get("completed_within_sla", 0)),
            sla_breaches=int(data.get("sla_breaches", 0)),
            warnings_triggered=int(data.get("warnings_triggered", 0)),
            escalations_performed=int(data.get("escalations_performed", 0)),
            total_response_time_seconds=float(data.get("total_response_time_seconds", 0.0)),
            min_response_time_seconds=float(data.get("min_response_time_seconds", float("inf"))),
            max_response_time_seconds=float(data.get("max_response_time_seconds", 0.0)),
            breaches_by_priority=data.get("breaches_by_priority", {}),
            escalations_by_priority=data.get("escalations_by_priority", {}),
            window_start=data.get("window_start"),
            window_end=data.get("window_end"),
        )
        return metrics


@dataclass
class SLABreach:
    """Represents an SLA breach event."""

    breach_id: str
    request_id: str
    priority: ApprovalPriority
    breach_time: float  # Unix timestamp
    sla_timeout_minutes: int
    actual_time_minutes: float
    breach_reason: EscalationReason
    escalation_level: int
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def overage_minutes(self) -> float:
        return self.actual_time_minutes - self.sla_timeout_minutes

    @property
    def overage_percent(self) -> float:
        if self.sla_timeout_minutes == 0:
            return 0.0
        return (self.overage_minutes / self.sla_timeout_minutes) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "breach_id": self.breach_id,
            "request_id": self.request_id,
            "priority": self.priority.value,
            "breach_time": self.breach_time,
            "sla_timeout_minutes": self.sla_timeout_minutes,
            "actual_time_minutes": self.actual_time_minutes,
            "breach_reason": self.breach_reason.value,
            "escalation_level": self.escalation_level,
            "overage_minutes": self.overage_minutes,
            "overage_percent": self.overage_percent,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SLABreach":
        return cls(
            breach_id=data["breach_id"],
            request_id=data["request_id"],
            priority=ApprovalPriority(data["priority"]),
            breach_time=float(data["breach_time"]),
            sla_timeout_minutes=int(data["sla_timeout_minutes"]),
            actual_time_minutes=float(data["actual_time_minutes"]),
            breach_reason=EscalationReason(data["breach_reason"]),
            escalation_level=int(data.get("escalation_level", 1)),
            metadata=data.get("metadata", {}),
        )


@dataclass
class EscalationTimer:
    """Represents an escalation timer for an approval request."""

    request_id: str
    priority: ApprovalPriority
    timeout_minutes: int
    created_at: float  # Unix timestamp
    expires_at: float  # Unix timestamp
    current_level: int = 1
    escalation_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at

    @property
    def time_remaining_seconds(self) -> float:
        return max(0, self.expires_at - time.time())

    @property
    def time_remaining_minutes(self) -> float:
        return self.time_remaining_seconds / 60

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "priority": self.priority.value,
            "timeout_minutes": self.timeout_minutes,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "current_level": self.current_level,
            "escalation_count": self.escalation_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EscalationTimer":
        return cls(
            request_id=data["request_id"],
            priority=ApprovalPriority(data["priority"]),
            timeout_minutes=int(data["timeout_minutes"]),
            created_at=float(data["created_at"]),
            expires_at=float(data["expires_at"]),
            current_level=int(data.get("current_level", 1)),
            escalation_count=int(data.get("escalation_count", 0)),
            metadata=data.get("metadata", {}),
        )
