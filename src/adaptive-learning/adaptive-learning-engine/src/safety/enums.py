"""
Safety Enums for Adaptive Learning Engine.
Constitutional Hash: cdd01ef066bc6cf2
"""

from enum import Enum


class SafetyStatus(Enum):
    """Overall status of the model learning safety."""

    OK = "ok"
    WARNING = "warning"
    PAUSED = "paused"
    CRITICAL = "critical"


class CheckResult(Enum):
    """Result of an individual safety check."""

    PASSED = "passed"
    FAILED_ACCURACY = "failed_accuracy"
    FAILED_DEGRADATION = "failed_degradation"
    FAILED_DRIFT = "failed_drift"
    SKIPPED_COLD_START = "skipped_cold_start"
    SKIPPED_INSUFFICIENT_DATA = "skipped_insufficient_data"
