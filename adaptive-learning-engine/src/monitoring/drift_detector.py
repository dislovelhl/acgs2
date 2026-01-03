"""
Adaptive Learning Engine - Drift Detector
Constitutional Hash: cdd01ef066bc6cf2

Evidently-based concept drift detection for monitoring model performance.
Compares reference (baseline) vs. current (recent) data distributions
to detect when the model needs updating or rollback.
"""

import asyncio
import hashlib
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional

import numpy as np
import pandas as pd
from evidently.metric_preset import DataDriftPreset
from evidently.report import Report

logger = logging.getLogger(__name__)


class DriftStatus(Enum):
    """Current drift detection status."""

    NO_DRIFT = "no_drift"  # No significant drift detected
    DRIFT_DETECTED = "drift_detected"  # Significant drift detected
    INSUFFICIENT_DATA = "insufficient_data"  # Not enough data for detection
    DISABLED = "disabled"  # Drift detection is disabled
    ERROR = "error"  # Error during drift detection


@dataclass
class DriftResult:
    """Result from a drift detection check."""

    status: DriftStatus
    drift_detected: bool
    drift_score: float  # Share of drifted columns (0.0 - 1.0)
    drift_threshold: float
    columns_drifted: Dict[str, bool]  # Per-column drift status
    column_drift_scores: Dict[str, float]  # Per-column drift scores
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


class DriftDetector:
    """Evidently-based drift detector for governance model monitoring.

    Monitors concept drift by comparing reference (baseline) data distribution
    against current (recent) prediction data. Uses Evidently's DataDriftPreset
    which includes multiple statistical tests (K-S, PSI, etc.).

    Features:
    - Configurable drift threshold (PSI-based)
    - Automatic reference data management
    - Low-traffic detection (insufficient data warning)
    - Alert callbacks for integration
    - Thread-safe operations
    - Graceful degradation on errors
    - DataFrame caching for performance optimization

    Caching:
        The detector implements an intelligent caching system to avoid redundant
        DataFrame conversions and drift report computations. Caches are automatically
        invalidated when the underlying data changes. Caching can be disabled for
        testing or debugging purposes using the enable_caching parameter.

    Example usage:
        detector = DriftDetector(
            drift_threshold=0.2,
            reference_window_size=1000,
            current_window_size=100,
        )

        # Add prediction data
        detector.add_data_point(features={"f1": 1.0, "f2": 2.0}, label=1)

        # Check for drift
        result = detector.check_drift()
        if result.drift_detected:
            print(f"Drift detected! Score: {result.drift_score}")
    """

    def __init__(
        self,
        drift_threshold: float = 0.2,
        reference_window_size: int = 1000,
        current_window_size: int = 100,
        min_samples_for_drift: int = 10,
        check_interval_seconds: int = 300,
        drift_share_threshold: float = 0.5,
        enabled: bool = True,
        enable_caching: bool = True,
    ) -> None:
        """Initialize the drift detector.

        Args:
            drift_threshold: PSI threshold for column drift (default 0.2).
            reference_window_size: Number of samples in reference dataset.
            current_window_size: Number of recent samples for comparison.
            min_samples_for_drift: Minimum samples needed for drift check.
            check_interval_seconds: Interval between automatic checks.
            drift_share_threshold: Fraction of columns that must drift
                to trigger dataset-level drift alert.
            enabled: Whether drift detection is enabled.
            enable_caching: Whether to cache DataFrame conversions and drift
                reports for performance. When enabled, the detector caches
                reference/current DataFrames and reuses them when data hasn't
                changed (detected via checksums). Disable for testing or when
                memory is constrained. Default is True.
        """
        self.drift_threshold = drift_threshold
        self.reference_window_size = reference_window_size
        self.current_window_size = current_window_size
        self.min_samples_for_drift = min_samples_for_drift
        self.check_interval_seconds = check_interval_seconds
        self.drift_share_threshold = drift_share_threshold
        self._enabled = enabled

        # Thread safety
        self._lock = threading.RLock()

        # Data storage
        self._reference_data: Deque[Dict[str, Any]] = deque(maxlen=reference_window_size)
        self._current_data: Deque[Dict[str, Any]] = deque(maxlen=current_window_size)
        self._all_data: Deque[Dict[str, Any]] = deque(
            maxlen=reference_window_size + current_window_size
        )

        # State tracking
        self._reference_locked = False  # Whether reference data is frozen
        self._last_check_time: Optional[float] = None
        self._last_drift_time: Optional[float] = None
        self._total_checks = 0
        self._drift_detections = 0
        self._consecutive_drift_count = 0
        self._drift_score_history: Deque[float] = deque(maxlen=100)
        self._current_status = DriftStatus.INSUFFICIENT_DATA if enabled else DriftStatus.DISABLED

        # Alert callbacks
        self._alert_callbacks: List[Callable[[DriftAlert], None]] = []
        self._pending_alerts: Deque[DriftAlert] = deque(maxlen=100)

        # Column tracking
        self._known_columns: set = set()

        # Caching infrastructure
        self._cache_enabled = enable_caching
        self._reference_df_cache: Optional[pd.DataFrame] = None
        self._current_df_cache: Optional[pd.DataFrame] = None
        self._reference_checksum: Optional[str] = None
        self._current_checksum: Optional[str] = None
        self._last_report_cache: Optional[DriftResult] = None
        self._report_cache_checksum: Optional[str] = None

        logger.info(
            "DriftDetector initialized",
            extra={
                "drift_threshold": drift_threshold,
                "reference_window_size": reference_window_size,
                "current_window_size": current_window_size,
                "enabled": enabled,
                "enable_caching": enable_caching,
            },
        )

    def add_data_point(
        self,
        features: Dict[str, Any],
        label: Optional[int] = None,
        prediction: Optional[int] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        """Add a single data point for drift monitoring.

        Args:
            features: Feature dictionary with numeric values.
            label: Optional true label.
            prediction: Optional model prediction.
            timestamp: Optional timestamp (uses current time if not provided).
        """
        if not self._enabled:
            return

        with self._lock:
            # Build data record
            record = features.copy()

            # Add optional fields
            if label is not None:
                record["_label"] = label
            if prediction is not None:
                record["_prediction"] = prediction
            record["_timestamp"] = timestamp or time.time()

            # Update known columns
            self._known_columns.update(k for k in features.keys() if not k.startswith("_"))

            # Add to current data window
            self._current_data.append(record)
            self._all_data.append(record)

            # If reference is not locked, also add to reference
            if not self._reference_locked:
                self._reference_data.append(record)

    def add_batch(
        self,
        data_points: List[Dict[str, Any]],
        labels: Optional[List[int]] = None,
        predictions: Optional[List[int]] = None,
    ) -> int:
        """Add multiple data points at once.

        Args:
            data_points: List of feature dictionaries.
            labels: Optional list of true labels.
            predictions: Optional list of model predictions.

        Returns:
            Number of points added.
        """
        count = 0
        for i, features in enumerate(data_points):
            label = labels[i] if labels and i < len(labels) else None
            prediction = predictions[i] if predictions and i < len(predictions) else None
            self.add_data_point(features=features, label=label, prediction=prediction)
            count += 1
        return count

    def lock_reference_data(self) -> None:
        """Lock the reference data to prevent further updates.

        Call this once you have enough baseline data to establish
        a reference distribution for drift comparison.
        """
        with self._lock:
            self._reference_locked = True
            logger.info(
                "Reference data locked",
                extra={"reference_size": len(self._reference_data)},
            )

    def unlock_reference_data(self) -> None:
        """Unlock reference data to allow updates."""
        with self._lock:
            self._reference_locked = False
            logger.info("Reference data unlocked")

    def update_reference_from_current(self) -> int:
        """Update reference data with current data.

        Useful for resetting the reference baseline after model updates.

        Returns:
            Number of points in new reference.
        """
        with self._lock:
            # Copy current data to reference
            self._reference_data.clear()
            self._reference_data.extend(self._current_data)
            self._reference_locked = True
            logger.info(
                "Reference data updated from current",
                extra={"reference_size": len(self._reference_data)},
            )
            return len(self._reference_data)

    def set_reference_data(self, reference_df: pd.DataFrame) -> None:
        """Set reference data from a DataFrame.

        Args:
            reference_df: DataFrame with feature columns.
        """
        with self._lock:
            self._reference_data.clear()
            for _, row in reference_df.iterrows():
                self._reference_data.append(row.to_dict())
            self._reference_locked = True
            self._known_columns.update(
                c for c in reference_df.columns if not str(c).startswith("_")
            )
            logger.info(
                "Reference data set from DataFrame",
                extra={"reference_size": len(self._reference_data)},
            )

    def check_drift(self) -> DriftResult:
        """Check for data drift between reference and current data.

        Uses Evidently's DataDriftPreset which includes multiple
        statistical tests (K-S test, PSI, etc.) to detect distribution shifts.

        Returns:
            DriftResult with drift status, scores, and details.
        """
        with self._lock:
            timestamp = time.time()
            self._last_check_time = timestamp
            self._total_checks += 1

            # Check if disabled
            if not self._enabled:
                return DriftResult(
                    status=DriftStatus.DISABLED,
                    drift_detected=False,
                    drift_score=0.0,
                    drift_threshold=self.drift_threshold,
                    columns_drifted={},
                    column_drift_scores={},
                    reference_size=0,
                    current_size=0,
                    timestamp=timestamp,
                    message="Drift detection is disabled",
                )

            # Check for sufficient data
            ref_size = len(self._reference_data)
            cur_size = len(self._current_data)

            if ref_size < self.min_samples_for_drift:
                self._current_status = DriftStatus.INSUFFICIENT_DATA
                return DriftResult(
                    status=DriftStatus.INSUFFICIENT_DATA,
                    drift_detected=False,
                    drift_score=0.0,
                    drift_threshold=self.drift_threshold,
                    columns_drifted={},
                    column_drift_scores={},
                    reference_size=ref_size,
                    current_size=cur_size,
                    timestamp=timestamp,
                    message=f"Insufficient reference data: {ref_size} < {self.min_samples_for_drift}",
                )

            if cur_size < self.min_samples_for_drift:
                self._current_status = DriftStatus.INSUFFICIENT_DATA
                return DriftResult(
                    status=DriftStatus.INSUFFICIENT_DATA,
                    drift_detected=False,
                    drift_score=0.0,
                    drift_threshold=self.drift_threshold,
                    columns_drifted={},
                    column_drift_scores={},
                    reference_size=ref_size,
                    current_size=cur_size,
                    timestamp=timestamp,
                    message=f"Insufficient current data: {cur_size} < {self.min_samples_for_drift}",
                )

            try:
                # Convert to DataFrames (with caching)
                reference_df = self._to_dataframe(list(self._reference_data), data_source="reference")
                current_df = self._to_dataframe(list(self._current_data), data_source="current")

                # Ensure same columns
                common_columns = list(set(reference_df.columns) & set(current_df.columns))
                # Filter out internal columns
                feature_columns = [c for c in common_columns if not str(c).startswith("_")]

                if not feature_columns:
                    return DriftResult(
                        status=DriftStatus.ERROR,
                        drift_detected=False,
                        drift_score=0.0,
                        drift_threshold=self.drift_threshold,
                        columns_drifted={},
                        column_drift_scores={},
                        reference_size=ref_size,
                        current_size=cur_size,
                        timestamp=timestamp,
                        message="No common feature columns found",
                    )

                reference_df = reference_df[feature_columns]
                current_df = current_df[feature_columns]

                # Run Evidently drift detection
                drift_report = Report(
                    metrics=[
                        DataDriftPreset(
                            drift_share=self.drift_share_threshold,
                        )
                    ]
                )
                drift_report.run(
                    reference_data=reference_df,
                    current_data=current_df,
                )

                # Extract results
                report_dict = drift_report.as_dict()

                # Parse drift results from report
                result = self._parse_drift_report(
                    report_dict=report_dict,
                    ref_size=ref_size,
                    cur_size=cur_size,
                    timestamp=timestamp,
                )

                # Update tracking
                self._drift_score_history.append(result.drift_score)

                if result.drift_detected:
                    self._drift_detections += 1
                    self._consecutive_drift_count += 1
                    self._last_drift_time = timestamp
                    self._current_status = DriftStatus.DRIFT_DETECTED

                    # Trigger alert
                    self._trigger_alert(result)

                    logger.warning(
                        "Drift detected",
                        extra={
                            "drift_score": result.drift_score,
                            "threshold": self.drift_threshold,
                            "columns_drifted": sum(result.columns_drifted.values()),
                        },
                    )
                else:
                    self._consecutive_drift_count = 0
                    self._current_status = DriftStatus.NO_DRIFT

                return result

            except Exception as e:
                # Graceful degradation: log error but don't crash
                logger.error(f"Drift detection error: {e}", exc_info=True)
                self._current_status = DriftStatus.ERROR
                return DriftResult(
                    status=DriftStatus.ERROR,
                    drift_detected=False,
                    drift_score=0.0,
                    drift_threshold=self.drift_threshold,
                    columns_drifted={},
                    column_drift_scores={},
                    reference_size=ref_size,
                    current_size=cur_size,
                    timestamp=timestamp,
                    message=f"Error during drift detection: {str(e)}",
                )

    async def check_drift_async(self) -> DriftResult:
        """Async version of check_drift for non-blocking operation.

        Returns:
            DriftResult with drift status, scores, and details.
        """
        # Run sync check in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.check_drift)

    def get_status(self) -> DriftResult:
        """Get current drift status without running a new check.

        Returns:
            Last drift result or default if no checks performed.
        """
        with self._lock:
            timestamp = time.time()

            if self._last_check_time is None:
                return DriftResult(
                    status=self._current_status,
                    drift_detected=False,
                    drift_score=0.0,
                    drift_threshold=self.drift_threshold,
                    columns_drifted={},
                    column_drift_scores={},
                    reference_size=len(self._reference_data),
                    current_size=len(self._current_data),
                    timestamp=timestamp,
                    message="No drift check performed yet",
                )

            # Return current status
            return DriftResult(
                status=self._current_status,
                drift_detected=self._current_status == DriftStatus.DRIFT_DETECTED,
                drift_score=(self._drift_score_history[-1] if self._drift_score_history else 0.0),
                drift_threshold=self.drift_threshold,
                columns_drifted={},
                column_drift_scores={},
                reference_size=len(self._reference_data),
                current_size=len(self._current_data),
                timestamp=self._last_check_time,
                message=f"Last check at {datetime.fromtimestamp(self._last_check_time).isoformat()}",
            )

    def get_metrics(self) -> DriftMetrics:
        """Get aggregated drift detection metrics.

        Returns:
            DriftMetrics with check counts and statistics.
        """
        with self._lock:
            avg_score = (
                float(np.mean(list(self._drift_score_history)))
                if self._drift_score_history
                else 0.0
            )
            current_score = self._drift_score_history[-1] if self._drift_score_history else 0.0

            return DriftMetrics(
                total_checks=self._total_checks,
                drift_detections=self._drift_detections,
                last_check_time=self._last_check_time,
                last_drift_time=self._last_drift_time,
                current_drift_score=current_score,
                average_drift_score=avg_score,
                status=self._current_status,
                consecutive_drift_count=self._consecutive_drift_count,
                data_points_collected=len(self._all_data),
            )

    def register_alert_callback(self, callback: Callable[[DriftAlert], None]) -> None:
        """Register a callback for drift alerts.

        Args:
            callback: Function called when drift is detected.
        """
        with self._lock:
            self._alert_callbacks.append(callback)

    def get_pending_alerts(self) -> List[DriftAlert]:
        """Get list of unacknowledged alerts.

        Returns:
            List of DriftAlert objects.
        """
        with self._lock:
            return [a for a in self._pending_alerts if not a.acknowledged]

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a drift alert.

        Args:
            alert_id: ID of the alert to acknowledge.

        Returns:
            True if alert was found and acknowledged.
        """
        with self._lock:
            for alert in self._pending_alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return True
            return False

    def enable(self) -> None:
        """Enable drift detection."""
        with self._lock:
            self._enabled = True
            self._current_status = (
                DriftStatus.INSUFFICIENT_DATA
                if len(self._reference_data) < self.min_samples_for_drift
                else DriftStatus.NO_DRIFT
            )
            logger.info("Drift detection enabled")

    def disable(self) -> None:
        """Disable drift detection."""
        with self._lock:
            self._enabled = False
            self._current_status = DriftStatus.DISABLED
            logger.info("Drift detection disabled")

    def is_enabled(self) -> bool:
        """Check if drift detection is enabled."""
        return self._enabled

    def reset(self) -> None:
        """Reset detector to initial state.

        Clears all data and resets metrics.
        """
        with self._lock:
            self._reference_data.clear()
            self._current_data.clear()
            self._all_data.clear()
            self._reference_locked = False
            self._last_check_time = None
            self._last_drift_time = None
            self._total_checks = 0
            self._drift_detections = 0
            self._consecutive_drift_count = 0
            self._drift_score_history.clear()
            self._pending_alerts.clear()
            self._known_columns.clear()
            self._current_status = (
                DriftStatus.INSUFFICIENT_DATA if self._enabled else DriftStatus.DISABLED
            )
            logger.info("DriftDetector reset")

    def _compute_deque_checksum(self, data: Deque[Dict[str, Any]], num_items: int = 3) -> str:
        """Compute a fast checksum of deque data to detect changes.

        Uses length + hash of first/last few items for performance.
        This allows detecting data changes without converting the entire
        deque to a DataFrame or hashing all items.

        Args:
            data: Deque of data dictionaries.
            num_items: Number of items to hash from start and end (default 3).

        Returns:
            Hex string checksum representing the data.
        """
        if not data:
            return hashlib.md5(b"empty", usedforsecurity=False).hexdigest()

        # Start with length
        components = [str(len(data))]

        # Hash first few items
        first_items = list(data)[:num_items]
        for item in first_items:
            # Convert dict to sorted tuple of items for consistent hashing
            item_str = str(sorted(item.items()))
            components.append(item_str)

        # Hash last few items (if different from first)
        if len(data) > num_items:
            last_items = list(data)[-num_items:]
            for item in last_items:
                item_str = str(sorted(item.items()))
                components.append(item_str)

        # Combine all components and hash
        combined = "|".join(components)
        checksum = hashlib.md5(combined.encode("utf-8"), usedforsecurity=False).hexdigest()

        return checksum

    def _to_dataframe(
        self, data: List[Dict[str, Any]], data_source: Optional[str] = None
    ) -> pd.DataFrame:
        """Convert list of dictionaries to DataFrame.

        Filters to numeric columns only for drift detection.

        Args:
            data: List of feature dictionaries.
            data_source: Optional identifier for cache lookup ('reference' or 'current').
                Used to enable DataFrame caching for performance optimization.

        Returns:
            DataFrame with numeric columns.
        """
        # Check cache if enabled and data_source is provided
        cache_checksum = None
        if self._cache_enabled and data_source:
            # Compute checksum of current data
            current_checksum = self._compute_deque_checksum(deque(data))

            # Try to return cached DataFrame
            if data_source == "reference":
                if (
                    self._reference_checksum == current_checksum
                    and self._reference_df_cache is not None
                ):
                    return self._reference_df_cache
            elif data_source == "current":
                if (
                    self._current_checksum == current_checksum
                    and self._current_df_cache is not None
                ):
                    return self._current_df_cache

            # Cache miss - will need to convert and update cache
            cache_checksum = current_checksum

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Select only numeric columns
        numeric_df = df.select_dtypes(include=[np.number])

        # Update cache if we computed a checksum (caching enabled with data_source)
        if cache_checksum is not None:
            if data_source == "reference":
                self._reference_df_cache = numeric_df
                self._reference_checksum = cache_checksum
            elif data_source == "current":
                self._current_df_cache = numeric_df
                self._current_checksum = cache_checksum

        return numeric_df

    def _parse_drift_report(
        self,
        report_dict: Dict[str, Any],
        ref_size: int,
        cur_size: int,
        timestamp: float,
    ) -> DriftResult:
        """Parse Evidently drift report into DriftResult.

        Args:
            report_dict: Evidently report as dictionary.
            ref_size: Reference data size.
            cur_size: Current data size.
            timestamp: Check timestamp.

        Returns:
            Parsed DriftResult.
        """
        columns_drifted: Dict[str, bool] = {}
        column_drift_scores: Dict[str, float] = {}
        dataset_drift = False
        share_of_drifted_columns = 0.0

        try:
            metrics_list = report_dict.get("metrics", [])

            for metric in metrics_list:
                result = metric.get("result", {})

                # Dataset-level drift
                if "dataset_drift" in result:
                    dataset_drift = result["dataset_drift"]
                    share_of_drifted_columns = result.get("share_of_drifted_columns", 0.0)

                # Column-level drift
                drift_by_columns = result.get("drift_by_columns", {})
                for col_name, col_data in drift_by_columns.items():
                    if isinstance(col_data, dict):
                        columns_drifted[col_name] = col_data.get("drift_detected", False)
                        # Try to get drift score (p-value or statistic varies by test)
                        drift_score = col_data.get("drift_score", 0.0)
                        if drift_score is None:
                            drift_score = col_data.get("stattest_score", 0.0) or 0.0
                        column_drift_scores[col_name] = float(drift_score)

        except Exception as e:
            logger.warning(f"Error parsing drift report: {e}")

        # Build result
        status = DriftStatus.DRIFT_DETECTED if dataset_drift else DriftStatus.NO_DRIFT
        num_drifted = sum(1 for v in columns_drifted.values() if v)

        return DriftResult(
            status=status,
            drift_detected=dataset_drift,
            drift_score=share_of_drifted_columns,
            drift_threshold=self.drift_threshold,
            columns_drifted=columns_drifted,
            column_drift_scores=column_drift_scores,
            reference_size=ref_size,
            current_size=cur_size,
            timestamp=timestamp,
            message=(
                f"Drift detected in {num_drifted} columns"
                if dataset_drift
                else "No significant drift detected"
            ),
        )

    def _trigger_alert(self, result: DriftResult) -> None:
        """Trigger drift alert callbacks.

        Args:
            result: Drift result that triggered the alert.
        """
        # Determine severity
        severity = "critical" if self._consecutive_drift_count >= 3 else "warning"

        alert = DriftAlert(
            drift_result=result,
            severity=severity,
        )

        # Store alert
        self._pending_alerts.append(alert)

        # Call callbacks (outside lock if possible, but we're already in lock)
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Alert callback error: {e}")

    def get_reference_data(self) -> pd.DataFrame:
        """Get reference data as DataFrame.

        Returns:
            Reference DataFrame.
        """
        with self._lock:
            if not self._reference_data:
                return pd.DataFrame()
            return self._to_dataframe(list(self._reference_data), data_source="reference")

    def get_current_data(self) -> pd.DataFrame:
        """Get current data as DataFrame.

        Returns:
            Current DataFrame.
        """
        with self._lock:
            if not self._current_data:
                return pd.DataFrame()
            return self._to_dataframe(list(self._current_data), data_source="current")

    def generate_html_report(self, output_path: str) -> bool:
        """Generate an HTML drift report.

        Args:
            output_path: Path to save the HTML report.

        Returns:
            True if report was generated successfully.
        """
        with self._lock:
            if (
                len(self._reference_data) < self.min_samples_for_drift
                or len(self._current_data) < self.min_samples_for_drift
            ):
                logger.warning("Insufficient data for HTML report")
                return False

            try:
                reference_df = self._to_dataframe(list(self._reference_data))
                current_df = self._to_dataframe(list(self._current_data))

                # Ensure same columns
                common_columns = list(set(reference_df.columns) & set(current_df.columns))
                feature_columns = [c for c in common_columns if not str(c).startswith("_")]

                if not feature_columns:
                    return False

                reference_df = reference_df[feature_columns]
                current_df = current_df[feature_columns]

                drift_report = Report(
                    metrics=[DataDriftPreset(drift_share=self.drift_share_threshold)]
                )
                drift_report.run(
                    reference_data=reference_df,
                    current_data=current_df,
                )
                drift_report.save_html(output_path)

                logger.info(f"Drift report saved to {output_path}")
                return True

            except Exception as e:
                logger.error(f"Error generating HTML report: {e}")
                return False

    def __repr__(self) -> str:
        """String representation of the detector."""
        return (
            f"DriftDetector("
            f"status={self._current_status.value}, "
            f"ref_size={len(self._reference_data)}, "
            f"cur_size={len(self._current_data)}, "
            f"checks={self._total_checks}, "
            f"drifts={self._drift_detections})"
        )
