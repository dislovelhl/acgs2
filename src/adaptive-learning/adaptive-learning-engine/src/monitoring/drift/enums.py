"""
Drift Enums for Monitoring.
Constitutional Hash: cdd01ef066bc6cf2
"""

from enum import Enum


class DriftStatus(Enum):
    """Current drift detection status."""

    NO_DRIFT = "no_drift"
    DRIFT_DETECTED = "drift_detected"
    INSUFFICIENT_DATA = "insufficient_data"
    DISABLED = "disabled"
    ERROR = "error"
