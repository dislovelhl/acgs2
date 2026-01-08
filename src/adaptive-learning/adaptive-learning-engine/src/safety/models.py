"""
Safety Bounds Checker Models
=============================

Dataclasses for safety check results, alerts and metrics.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# Import enums to avoid duplication
from src.safety.enums import CheckResult, SafetyStatus


@dataclass
class SafetyCheckResult:
    """Result of a safety bounds check."""

    passed: bool
    result: CheckResult
    current_accuracy: float
    threshold: float
    message: str
    consecutive_failures: int
    safety_status: SafetyStatus
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "passed": self.passed,
            "result": self.result.value,
            "current_accuracy": self.current_accuracy,
            "threshold": self.threshold,
            "message": self.message,
            "consecutive_failures": self.consecutive_failures,
            "safety_status": self.safety_status.value,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class SafetyAlert:
    """Alert generated when safety bounds are violated."""

    severity: str  # "warning", "critical"
    message: str
    consecutive_failures: int
    current_accuracy: float
    threshold: float
    action_taken: str  # "none", "paused_learning", "alert_sent"
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "severity": self.severity,
            "message": self.message,
            "consecutive_failures": self.consecutive_failures,
            "current_accuracy": self.current_accuracy,
            "threshold": self.threshold,
            "action_taken": self.action_taken,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class SafetyMetrics:
    """Metrics for safety bounds checking."""

    total_checks: int
    passed_checks: int
    failed_checks: int
    consecutive_failures: int
    max_consecutive_failures: int
    times_paused: int
    times_resumed: int
    current_status: SafetyStatus
    last_check_time: Optional[float]
    last_failure_time: Optional[float]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "consecutive_failures": self.consecutive_failures,
            "max_consecutive_failures": self.max_consecutive_failures,
            "times_paused": self.times_paused,
            "times_resumed": self.times_resumed,
            "current_status": self.current_status.value,
            "last_check_time": self.last_check_time,
            "last_failure_time": self.last_failure_time,
        }
