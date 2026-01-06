"""
Drift Models for Monitoring.
Constitutional Hash: cdd01ef066bc6cf2
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Optional

from .enums import DriftStatus


@dataclass
class DriftResult:
    """Result from a drift detection check."""

    status: DriftStatus
    drift_detected: bool
    drift_score: float  # Share of drifted columns (0.0 - 1.0)
    drift_threshold: float
    columns_drifted: Dict[str, bool]
    column_drift_scores: Dict[str, float]
    reference_size: int
    current_size: int
    timestamp: float = field(default_factory=time.time)
    message: str = ""


@dataclass
class DriftAlert:
    """Alert generated when drift is detected."""

    drift_result: DriftResult
    severity: str  # "warning" or "critical"
    triggered_at: float = field(default_factory=time.time)
    acknowledged: bool = False
    alert_id: str = field(default_factory=lambda: f"drift_{int(time.time() * 1000)}")


@dataclass
class DriftMetrics:
    """Aggregated drift detection metrics."""

    total_checks: int
    drift_detections: int
    last_check_time: Optional[float]
    last_drift_time: Optional[float]
    current_drift_score: float
    average_drift_score: float
    status: DriftStatus
    consecutive_drift_count: int
    data_points_collected: int
