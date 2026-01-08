"""
Adaptive Learning Engine - Drift Detector
Constitutional Hash: cdd01ef066bc6cf2

Evidently-based data drift detection for monitoring model performance.
See DRIFT_DESIGN.md for detailed design rationale and statistical foundations.
"""

import asyncio
import hashlib
import logging
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset

from .drift.enums import DriftStatus
from .drift.models import DriftAlert, DriftMetrics, DriftResult

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Evidently-based drift detector for governance model monitoring.
    Monitors data drift by comparing reference (baseline) vs current data.
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
        # _all_data should be large enough to hold combined windows without premature truncation during tests
        self._all_data: Deque[Dict[str, Any]] = deque(maxlen=10000)

        # State tracking
        self._reference_locked = False
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

        # Caching
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
            },
        )

    def add_data_point(
        self,
        features: Dict[str, Any],
        label: Optional[int] = None,
        prediction: Optional[int] = None,
        timestamp: Optional[float] = None,
    ) -> None:
        if not self._enabled:
            return

        with self._lock:
            record = features.copy()
            if label is not None:
                record["_label"] = label
            if prediction is not None:
                record["_prediction"] = prediction
            record["_timestamp"] = timestamp or time.time()

            self._known_columns.update(k for k in features.keys() if not k.startswith("_"))

            self._current_data.append(record)
            self._all_data.append(record)

            if not self._reference_locked:
                self._reference_data.append(record)
                self._clear_reference_cache()

            self._invalidate_current_cache()

    def add_batch(
        self,
        data_points: List[Dict[str, Any]],
        labels: Optional[List[int]] = None,
        predictions: Optional[List[int]] = None,
    ) -> int:
        count = 0
        for i, features in enumerate(data_points):
            label = labels[i] if labels and i < len(labels) else None
            prediction = predictions[i] if predictions and i < len(predictions) else None
            self.add_data_point(features=features, label=label, prediction=prediction)
            count += 1
        return count

    def lock_reference_data(self) -> None:
        with self._lock:
            self._reference_locked = True
            logger.info("Reference data locked", extra={"size": len(self._reference_data)})

    def unlock_reference_data(self) -> None:
        with self._lock:
            self._reference_locked = False
            logger.info("Reference data unlocked")

    def update_reference_from_current(self) -> int:
        with self._lock:
            self._reference_data.clear()
            self._reference_data.extend(self._current_data)
            self._reference_locked = True
            self._clear_reference_cache()
            return len(self._reference_data)

    def set_reference_data(self, reference_df: pd.DataFrame) -> None:
        with self._lock:
            self._reference_data.clear()
            for _, row in reference_df.iterrows():
                self._reference_data.append(row.to_dict())
            self._reference_locked = True
            self._known_columns.update(
                c for c in reference_df.columns if not str(c).startswith("_")
            )
            self._clear_reference_cache()

    def check_drift(self) -> DriftResult:
        with self._lock:
            timestamp = time.time()
            self._last_check_time = timestamp
            self._total_checks += 1

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

            # Check cache
            if self._cache_enabled:
                ref_chk = self._compute_deque_checksum(self._reference_data)
                cur_chk = self._compute_deque_checksum(self._current_data)
                combined_checksum = hashlib.md5(f"{ref_chk}|{cur_chk}".encode()).hexdigest()

                if combined_checksum == self._report_cache_checksum and self._last_report_cache:
                    cached = self._last_report_cache
                    return DriftResult(
                        status=cached.status,
                        drift_detected=cached.drift_detected,
                        drift_score=cached.drift_score,
                        drift_threshold=cached.drift_threshold,
                        columns_drifted=cached.columns_drifted,
                        column_drift_scores=cached.column_drift_scores,
                        reference_size=cached.reference_size,
                        current_size=cached.current_size,
                        timestamp=timestamp,
                        message=cached.message,
                    )

            try:
                ref_df = self._to_dataframe(list(self._reference_data), "reference")
                cur_df = self._to_dataframe(list(self._current_data), "current")

                feature_cols = [
                    c
                    for c in (set(ref_df.columns) & set(cur_df.columns))
                    if not str(c).startswith("_")
                ]
                if not feature_cols:
                    return self._error_result(
                        "No common feature columns found", timestamp, ref_size, cur_size
                    )

                report = Report(metrics=[DataDriftPreset(drift_share=self.drift_share_threshold)])
                snapshot = report.run(
                    reference_data=ref_df[feature_cols], current_data=cur_df[feature_cols]
                )

                result = self._parse_drift_report(
                    snapshot.dict(), ref_size, cur_size, timestamp, feature_cols
                )
                self._update_state(result)

                if self._cache_enabled:
                    self._report_cache_checksum = combined_checksum
                    self._last_report_cache = result

                return result

            except Exception as e:
                logger.error(f"Drift detection error: {e}", exc_info=True)
                return self._error_result(
                    f"Error during drift detection: {str(e)}", timestamp, ref_size, cur_size
                )

    async def check_drift_async(self) -> DriftResult:
        return await asyncio.get_event_loop().run_in_executor(None, self.check_drift)

    def get_status(self) -> DriftResult:
        with self._lock:
            if self._last_report_cache:
                return self._last_report_cache
            return DriftResult(
                status=self._current_status,
                drift_detected=False,
                drift_score=0.0,
                drift_threshold=self.drift_threshold,
                columns_drifted={},
                column_drift_scores={},
                reference_size=len(self._reference_data),
                current_size=len(self._current_data),
                timestamp=time.time(),
                message="No drift check performed yet",
            )

    def get_metrics(self) -> DriftMetrics:
        with self._lock:
            avg_score = (
                sum(self._drift_score_history) / len(self._drift_score_history)
                if self._drift_score_history
                else 0.0
            )
            return DriftMetrics(
                total_checks=self._total_checks,
                drift_detections=self._drift_detections,
                last_check_time=self._last_check_time,
                last_drift_time=self._last_drift_time,
                current_drift_score=self._drift_score_history[-1]
                if self._drift_score_history
                else 0.0,
                average_drift_score=avg_score,
                status=self._current_status,
                consecutive_drift_count=self._consecutive_drift_count,
                data_points_collected=len(self._all_data),
            )

    def get_reference_data(self) -> pd.DataFrame:
        with self._lock:
            return self._to_dataframe(list(self._reference_data), "reference")

    def get_current_data(self) -> pd.DataFrame:
        with self._lock:
            return self._to_dataframe(list(self._current_data), "current")

    def get_all_data(self) -> pd.DataFrame:
        with self._lock:
            return pd.DataFrame(list(self._all_data))

    def get_pending_alerts(self) -> List[DriftAlert]:
        with self._lock:
            return list(self._pending_alerts)

    def enable(self) -> None:
        """Enable drift detection."""
        with self._lock:
            self._enabled = True
            if self._current_status == DriftStatus.DISABLED:
                self._current_status = DriftStatus.INSUFFICIENT_DATA
            logger.info("DriftDetector enabled")

    def disable(self) -> None:
        """Disable drift detection."""
        with self._lock:
            self._enabled = False
            self._current_status = DriftStatus.DISABLED
            logger.info("DriftDetector disabled")

    def is_enabled(self) -> bool:
        """Check if drift detection is enabled."""
        return self._enabled

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge a pending drift alert by ID.

        Args:
            alert_id: The ID of the alert to acknowledge.

        Returns:
            True if alert was found and acknowledged, False otherwise.
        """
        with self._lock:
            for alert in self._pending_alerts:
                if alert.alert_id == alert_id:
                    alert.acknowledged = True
                    return True
            return False

    def generate_html_report(self, output_path: str) -> bool:
        """Generate an HTML drift report.

        Args:
            output_path: Path to save the HTML report.

        Returns:
            True if report was generated successfully, False otherwise.
        """
        with self._lock:
            try:
                ref_size = len(self._reference_data)
                cur_size = len(self._current_data)

                if ref_size < self.min_samples_for_drift or cur_size < self.min_samples_for_drift:
                    logger.warning("Insufficient data for HTML report generation")
                    return False

                ref_df = self._to_dataframe(list(self._reference_data), "reference")
                cur_df = self._to_dataframe(list(self._current_data), "current")

                feature_cols = [
                    c
                    for c in (set(ref_df.columns) & set(cur_df.columns))
                    if not str(c).startswith("_")
                ]
                if not feature_cols:
                    return False

                report = Report(metrics=[DataDriftPreset(drift_share=self.drift_share_threshold)])
                snapshot = report.run(
                    reference_data=ref_df[feature_cols], current_data=cur_df[feature_cols]
                )
                snapshot.save_html(output_path)
                return True
            except Exception as e:
                logger.error(f"Error generating HTML report: {e}")
                return False

    def _update_state(self, result: DriftResult) -> None:
        self._drift_score_history.append(result.drift_score)
        if result.drift_detected:
            self._drift_detections += 1
            self._consecutive_drift_count += 1
            self._last_drift_time = result.timestamp
            self._current_status = DriftStatus.DRIFT_DETECTED
            self._trigger_alert(result)
        else:
            self._consecutive_drift_count = 0
            self._current_status = DriftStatus.NO_DRIFT

    def _parse_drift_report(
        self,
        report_dict: Dict,
        ref_size: int,
        cur_size: int,
        timestamp: float,
        feature_cols: List[str],
    ) -> DriftResult:
        """Parse Evidently 0.7.x Snapshot dict format."""
        metrics = report_dict.get("metrics", [])

        # Find DriftedColumnsCount metric for overall drift info
        drift_count_metric = next(
            (m for m in metrics if "DriftedColumnsCount" in m.get("metric_name", "")), None
        )

        drift_score = 0.0
        if drift_count_metric:
            value = drift_count_metric.get("value", {})
            drift_score = value.get("share", 0.0) if isinstance(value, dict) else 0.0

        # Determine if drift detected based on share threshold
        drift_detected = drift_score >= self.drift_share_threshold

        # Parse per-column drift from ValueDrift metrics
        drift_by_col = {}
        scores_by_col = {}
        for m in metrics:
            metric_name = m.get("metric_name", "")
            if "ValueDrift" in metric_name:
                config = m.get("config", {})
                col_name = config.get("column", "")
                threshold = config.get("threshold", 0.05)
                p_value = m.get("value", 1.0)

                # Drift detected if p-value < threshold
                col_drifted = p_value < threshold if isinstance(p_value, (int, float)) else False
                drift_by_col[col_name] = col_drifted
                scores_by_col[col_name] = p_value if isinstance(p_value, (int, float)) else 0.0

        return DriftResult(
            status=DriftStatus.DRIFT_DETECTED if drift_detected else DriftStatus.NO_DRIFT,
            drift_detected=drift_detected,
            drift_score=drift_score,
            drift_threshold=self.drift_threshold,
            columns_drifted=drift_by_col,
            column_drift_scores=scores_by_col,
            reference_size=ref_size,
            current_size=cur_size,
            timestamp=timestamp,
        )

    def _trigger_alert(self, result: DriftResult) -> None:
        severity = "critical" if self._consecutive_drift_count >= 3 else "warning"
        alert = DriftAlert(drift_result=result, severity=severity)
        self._pending_alerts.append(alert)
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in drift alert callback: {e}")

    def _error_result(self, msg: str, ts: float, ref: int, cur: int) -> DriftResult:
        self._current_status = DriftStatus.ERROR
        return DriftResult(
            status=DriftStatus.ERROR,
            drift_detected=False,
            drift_score=0.0,
            drift_threshold=self.drift_threshold,
            columns_drifted={},
            column_drift_scores={},
            reference_size=ref,
            current_size=cur,
            timestamp=ts,
            message=msg,
        )

    def _to_dataframe(self, data: List[Dict], data_source: str) -> pd.DataFrame:
        if self._cache_enabled:
            if data_source == "reference" and self._reference_df_cache is not None:
                return self._reference_df_cache
            if data_source == "current" and self._current_df_cache is not None:
                return self._current_df_cache

        df = pd.DataFrame(data)
        if self._cache_enabled:
            if data_source == "reference":
                self._reference_df_cache = df
                self._reference_checksum = self._compute_deque_checksum(self._reference_data)
            else:
                self._current_df_cache = df
                self._current_checksum = self._compute_deque_checksum(self._current_data)
        return df

    def _compute_deque_checksum(self, d: Deque) -> str:
        # Improved checksum by hashing the string representation of data
        return hashlib.md5(str(list(d)).encode()).hexdigest()

    def _invalidate_current_cache(self) -> None:
        self._current_df_cache = None
        self._current_checksum = None
        self._report_cache_checksum = None
        self._last_report_cache = None

    def _clear_reference_cache(self) -> None:
        self._reference_df_cache = None
        self._reference_checksum = None
        self._report_cache_checksum = None
        self._last_report_cache = None

    def register_alert_callback(self, callback: Callable[[DriftAlert], None]) -> None:
        self._alert_callbacks.append(callback)

    def reset(self) -> None:
        with self._lock:
            self._reference_data.clear()
            self._current_data.clear()
            self._all_data.clear()
            self._total_checks = 0
            self._drift_detections = 0
            self._consecutive_drift_count = 0
            self._drift_score_history.clear()
            self._pending_alerts.clear()
            self._reference_locked = False
            self._last_report_cache = None
            self._report_cache_checksum = None
            self._clear_reference_cache()
            self._invalidate_current_cache()
            logger.info("DriftDetector reset")

    def __repr__(self) -> str:
        return f"DriftDetector(status={self._current_status.value}, ref_size={len(self._reference_data)}, cur_size={len(self._current_data)}, checks={self._total_checks})"
