"""
ACGS-2 Drift Monitoring Module
Constitutional Hash: cdd01ef066bc6cf2

Implements data drift detection using Evidently AI with PSI (Population Stability Index)
method for governance model monitoring. Drift detection triggers retraining decisions
and alerts when production data distribution diverges from training baseline.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

# Type checking imports for static analysis
if TYPE_CHECKING:
    import pandas as pd

try:
    import pandas as pd_module

    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd_module = None

try:
    from evidently.metric_preset import DataDriftPreset
    from evidently.report import Report as EvidentlyReport

    EVIDENTLY_AVAILABLE = True
except ImportError:
    EVIDENTLY_AVAILABLE = False
    EvidentlyReport = None
    DataDriftPreset = None

logger = logging.getLogger(__name__)

# Configuration from environment
REFERENCE_DATA_PATH = os.getenv(
    "EVIDENTLY_REFERENCE_DATA_PATH", "data/reference/training_baseline.parquet"
)
DRIFT_CHECK_INTERVAL_HOURS = int(os.getenv("DRIFT_CHECK_INTERVAL_HOURS", "6"))
DRIFT_PSI_THRESHOLD = float(os.getenv("DRIFT_PSI_THRESHOLD", "0.2"))
DRIFT_SHARE_THRESHOLD = float(os.getenv("DRIFT_SHARE_THRESHOLD", "0.5"))
MIN_SAMPLES_FOR_DRIFT = int(os.getenv("MIN_SAMPLES_FOR_DRIFT", "100"))


class DriftSeverity(str, Enum):
    """Severity level of detected drift."""

    NONE = "none"  # No drift detected
    LOW = "low"  # Minor drift, monitoring recommended
    MODERATE = "moderate"  # Significant drift, investigation needed
    HIGH = "high"  # Severe drift, retraining recommended
    CRITICAL = "critical"  # Critical drift, immediate action required


class DriftStatus(str, Enum):
    """Status of drift detection operation."""

    SUCCESS = "success"  # Detection completed successfully
    INSUFFICIENT_DATA = "insufficient_data"  # Not enough samples
    NO_REFERENCE = "no_reference"  # Reference data not available
    ERROR = "error"  # Detection failed


@dataclass
class FeatureDriftResult:
    """Drift detection result for a single feature."""

    feature_name: str
    drift_detected: bool
    drift_score: float
    stattest: str = "psi"
    threshold: float = DRIFT_PSI_THRESHOLD
    psi_value: Optional[float] = None
    reference_distribution: Optional[Dict[str, Any]] = None
    current_distribution: Optional[Dict[str, Any]] = None


@dataclass
class DriftReport:
    """Complete drift detection report."""

    timestamp: datetime
    status: DriftStatus
    dataset_drift: bool = False
    drift_severity: DriftSeverity = DriftSeverity.NONE
    drift_share: float = 0.0
    total_features: int = 0
    drifted_features: int = 0
    feature_results: List[FeatureDriftResult] = field(default_factory=list)
    reference_samples: int = 0
    current_samples: int = 0
    error_message: Optional[str] = None
    raw_results: Optional[Dict[str, Any]] = None
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "status": self.status.value,
            "dataset_drift": self.dataset_drift,
            "drift_severity": self.drift_severity.value,
            "drift_share": self.drift_share,
            "total_features": self.total_features,
            "drifted_features": self.drifted_features,
            "feature_results": [
                {
                    "feature_name": f.feature_name,
                    "drift_detected": f.drift_detected,
                    "drift_score": f.drift_score,
                    "stattest": f.stattest,
                    "threshold": f.threshold,
                    "psi_value": f.psi_value,
                }
                for f in self.feature_results
            ],
            "reference_samples": self.reference_samples,
            "current_samples": self.current_samples,
            "error_message": self.error_message,
            "recommendations": self.recommendations,
        }


@dataclass
class DriftAlertConfig:
    """Configuration for drift alerting."""

    enabled: bool = True
    low_threshold: float = 0.1  # Drift share for low severity
    moderate_threshold: float = 0.25  # Drift share for moderate severity
    high_threshold: float = 0.5  # Drift share for high severity
    critical_threshold: float = 0.75  # Drift share for critical severity
    alert_on_severity: List[DriftSeverity] = field(
        default_factory=lambda: [DriftSeverity.HIGH, DriftSeverity.CRITICAL]
    )
    webhook_url: Optional[str] = None
    email_recipients: List[str] = field(default_factory=list)


class DriftDetector:
    """
    Detects data drift using Evidently AI with PSI (Population Stability Index) method.

    PSI is recommended over KS test for stability in production environments.
    Drift detection triggers retraining decisions, not automatic retrains.

    Usage:
        detector = DriftDetector()
        detector.load_reference_data("data/reference/training_baseline.parquet")
        report = detector.detect_drift(current_production_data)

        if report.dataset_drift:
            trigger_retraining_pipeline()
            send_drift_alert(report)
    """

    def __init__(
        self,
        reference_data_path: Optional[str] = None,
        psi_threshold: float = DRIFT_PSI_THRESHOLD,
        drift_share_threshold: float = DRIFT_SHARE_THRESHOLD,
        min_samples: int = MIN_SAMPLES_FOR_DRIFT,
        alert_config: Optional[DriftAlertConfig] = None,
    ):
        """
        Initialize the drift detector.

        Args:
            reference_data_path: Path to reference baseline data (parquet file)
            psi_threshold: PSI threshold for individual feature drift detection
            drift_share_threshold: Proportion of features that must drift for dataset drift
            min_samples: Minimum samples required for valid drift detection
            alert_config: Configuration for drift alerting
        """
        self.reference_data_path = reference_data_path or REFERENCE_DATA_PATH
        self.psi_threshold = psi_threshold
        self.drift_share_threshold = drift_share_threshold
        self.min_samples = min_samples
        self.alert_config = alert_config or DriftAlertConfig()

        self._reference_data: Optional[pd.DataFrame] = None
        self._feature_columns: Optional[List[str]] = None
        self._last_report: Optional[DriftReport] = None
        self._drift_history: List[DriftReport] = []

    def _check_dependencies(self) -> None:
        """Check that required dependencies are available."""
        if not PANDAS_AVAILABLE:
            raise ImportError(
                "pandas is required for drift detection. Install with: pip install pandas"
            )
        if not EVIDENTLY_AVAILABLE:
            raise ImportError(
                "evidently is required for drift detection. Install with: pip install evidently"
            )

    def load_reference_data(
        self,
        data: Optional[Union[pd.DataFrame, str, Path]] = None,
    ) -> bool:
        """
        Load reference baseline data for drift comparison.

        Args:
            data: Reference data as DataFrame, file path string, or Path object.
                  If None, uses configured reference_data_path.

        Returns:
            True if reference data loaded successfully, False otherwise
        """
        self._check_dependencies()

        try:
            if data is None:
                data = self.reference_data_path

            if isinstance(data, (str, Path)):
                path = Path(data)
                if not path.exists():
                    logger.error(f"Reference data file not found: {path}")
                    return False

                if path.suffix == ".parquet":
                    self._reference_data = pd_module.read_parquet(path)
                elif path.suffix == ".csv":
                    self._reference_data = pd_module.read_csv(path)
                else:
                    logger.error(f"Unsupported file format: {path.suffix}")
                    return False

            elif hasattr(data, "to_dict"):  # DataFrame-like
                self._reference_data = data
            else:
                logger.error(f"Unsupported reference data type: {type(data)}")
                return False

            # Extract feature columns (exclude target-like columns)
            self._feature_columns = [
                col
                for col in self._reference_data.columns
                if col.lower() not in ("target", "label", "y", "prediction", "timestamp", "id")
            ]

            logger.info(
                f"Loaded reference data: {len(self._reference_data)} samples, "
                f"{len(self._feature_columns)} features"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load reference data: {e}")
            return False

    def set_reference_data(self, data: pd.DataFrame) -> bool:
        """
        Set reference data from a DataFrame directly.

        Args:
            data: Reference DataFrame

        Returns:
            True if set successfully, False otherwise
        """
        return self.load_reference_data(data)

    @property
    def reference_data(self) -> Optional[pd.DataFrame]:
        """Get the current reference data."""
        return self._reference_data

    @property
    def has_reference_data(self) -> bool:
        """Check if reference data is loaded."""
        return self._reference_data is not None and len(self._reference_data) > 0

    def detect_drift(
        self,
        current_data: Union[pd.DataFrame, str, Path],
        feature_columns: Optional[List[str]] = None,
    ) -> DriftReport:
        """
        Detect drift between reference and current data.

        Uses PSI (Population Stability Index) method which is more stable
        than KS test for production use.

        Args:
            current_data: Current production data as DataFrame or file path
            feature_columns: Specific columns to check for drift (None = all features)

        Returns:
            DriftReport with detection results and recommendations
        """
        timestamp = datetime.now(timezone.utc)

        try:
            self._check_dependencies()
        except ImportError as e:
            return DriftReport(
                timestamp=timestamp,
                status=DriftStatus.ERROR,
                error_message=str(e),
                recommendations=["Install required dependencies: pip install evidently pandas"],
            )

        # Load current data if path provided
        if isinstance(current_data, (str, Path)):
            path = Path(current_data)
            if not path.exists():
                return DriftReport(
                    timestamp=timestamp,
                    status=DriftStatus.ERROR,
                    error_message=f"Current data file not found: {path}",
                )
            try:
                if path.suffix == ".parquet":
                    current_data = pd_module.read_parquet(path)
                else:
                    current_data = pd_module.read_csv(path)
            except Exception as e:
                return DriftReport(
                    timestamp=timestamp,
                    status=DriftStatus.ERROR,
                    error_message=f"Failed to load current data: {e}",
                )

        # Check reference data
        if not self.has_reference_data:
            # Try to load from default path
            if not self.load_reference_data():
                return DriftReport(
                    timestamp=timestamp,
                    status=DriftStatus.NO_REFERENCE,
                    error_message="No reference data available. Call load_reference_data() first.",
                    recommendations=["Load reference baseline data before running drift detection"],
                )

        # Validate sample sizes
        reference_samples = len(self._reference_data)
        current_samples = len(current_data)

        if current_samples < self.min_samples:
            return DriftReport(
                timestamp=timestamp,
                status=DriftStatus.INSUFFICIENT_DATA,
                reference_samples=reference_samples,
                current_samples=current_samples,
                error_message=(
                    f"Insufficient current data samples ({current_samples}). "
                    f"Minimum required: {self.min_samples}"
                ),
                recommendations=[
                    f"Collect at least {self.min_samples} samples before running drift detection",
                    "Increase data collection window if necessary",
                ],
            )

        if reference_samples < self.min_samples:
            return DriftReport(
                timestamp=timestamp,
                status=DriftStatus.INSUFFICIENT_DATA,
                reference_samples=reference_samples,
                current_samples=current_samples,
                error_message=(
                    f"Insufficient reference data samples ({reference_samples}). "
                    f"Minimum required: {self.min_samples}"
                ),
                recommendations=["Update reference baseline with more training data samples"],
            )

        # Determine features to analyze
        columns_to_check = feature_columns or self._feature_columns

        # Ensure columns exist in both datasets
        available_columns = [
            col
            for col in columns_to_check
            if col in self._reference_data.columns and col in current_data.columns
        ]

        if not available_columns:
            return DriftReport(
                timestamp=timestamp,
                status=DriftStatus.ERROR,
                error_message="No common feature columns found between reference and current data",
                recommendations=["Verify feature columns match between reference and current data"],
            )

        # Filter data to available columns
        reference_filtered = self._reference_data[available_columns]
        current_filtered = current_data[available_columns]

        try:
            # Generate drift report using Evidently
            report = EvidentlyReport(
                metrics=[
                    DataDriftPreset(
                        drift_share=self.drift_share_threshold,
                        stattest="psi",
                        stattest_threshold=self.psi_threshold,
                    )
                ]
            )

            report.run(reference_data=reference_filtered, current_data=current_filtered)

            # Extract results programmatically
            drift_results = report.as_dict()

            # Parse Evidently results
            drift_report = self._parse_evidently_results(
                drift_results=drift_results,
                timestamp=timestamp,
                reference_samples=reference_samples,
                current_samples=current_samples,
                columns=available_columns,
            )

            # Store report
            self._last_report = drift_report
            self._drift_history.append(drift_report)

            # Log drift status
            if drift_report.dataset_drift:
                logger.warning(
                    f"Dataset drift detected: {drift_report.drifted_features}/{drift_report.total_features} "
                    f"features drifted ({drift_report.drift_share:.1%}). "
                    f"Severity: {drift_report.drift_severity.value}"
                )
            else:
                logger.info(
                    f"No significant dataset drift detected. "
                    f"Drift share: {drift_report.drift_share:.1%}"
                )

            return drift_report

        except Exception as e:
            logger.error(f"Drift detection failed: {e}")
            return DriftReport(
                timestamp=timestamp,
                status=DriftStatus.ERROR,
                reference_samples=reference_samples,
                current_samples=current_samples,
                error_message=f"Drift detection failed: {e}",
                recommendations=["Check data format and compatibility with Evidently"],
            )

    def _parse_evidently_results(
        self,
        drift_results: Dict[str, Any],
        timestamp: datetime,
        reference_samples: int,
        current_samples: int,
        columns: List[str],
    ) -> DriftReport:
        """Parse Evidently drift results into DriftReport."""
        # Extract dataset-level drift info
        metrics = drift_results.get("metrics", [{}])
        dataset_drift_result = metrics[0].get("result", {}) if metrics else {}

        dataset_drift = dataset_drift_result.get("dataset_drift", False)
        drift_share = dataset_drift_result.get("share_of_drifted_columns", 0.0)
        drifted_columns = dataset_drift_result.get("number_of_drifted_columns", 0)
        total_columns = dataset_drift_result.get("number_of_columns", len(columns))

        # Extract per-feature drift info
        drift_by_columns = dataset_drift_result.get("drift_by_columns", {})
        feature_results: List[FeatureDriftResult] = []

        for column in columns:
            column_drift = drift_by_columns.get(column, {})
            feature_results.append(
                FeatureDriftResult(
                    feature_name=column,
                    drift_detected=column_drift.get("drift_detected", False),
                    drift_score=column_drift.get("drift_score", 0.0),
                    stattest=column_drift.get("stattest_name", "psi"),
                    threshold=column_drift.get("stattest_threshold", self.psi_threshold),
                    psi_value=column_drift.get("drift_score"),
                )
            )

        # Determine severity
        severity = self._calculate_severity(drift_share)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            dataset_drift=dataset_drift,
            severity=severity,
            drift_share=drift_share,
            drifted_columns=drifted_columns,
            feature_results=feature_results,
        )

        return DriftReport(
            timestamp=timestamp,
            status=DriftStatus.SUCCESS,
            dataset_drift=dataset_drift,
            drift_severity=severity,
            drift_share=drift_share,
            total_features=total_columns,
            drifted_features=drifted_columns,
            feature_results=feature_results,
            reference_samples=reference_samples,
            current_samples=current_samples,
            raw_results=drift_results,
            recommendations=recommendations,
        )

    def _calculate_severity(self, drift_share: float) -> DriftSeverity:
        """Calculate drift severity based on drift share."""
        if drift_share >= self.alert_config.critical_threshold:
            return DriftSeverity.CRITICAL
        elif drift_share >= self.alert_config.high_threshold:
            return DriftSeverity.HIGH
        elif drift_share >= self.alert_config.moderate_threshold:
            return DriftSeverity.MODERATE
        elif drift_share >= self.alert_config.low_threshold:
            return DriftSeverity.LOW
        else:
            return DriftSeverity.NONE

    def _generate_recommendations(
        self,
        dataset_drift: bool,
        severity: DriftSeverity,
        drift_share: float,
        drifted_columns: int,
        feature_results: List[FeatureDriftResult],
    ) -> List[str]:
        """Generate actionable recommendations based on drift results."""
        recommendations: List[str] = []

        if not dataset_drift:
            recommendations.append("No action required - model performance should be stable")
            return recommendations

        # Severity-based recommendations
        if severity == DriftSeverity.CRITICAL:
            recommendations.extend(
                [
                    "IMMEDIATE ACTION: Consider pausing model predictions if accuracy is critical",
                    "Schedule emergency model retraining with recent data",
                    "Investigate root cause of significant data distribution change",
                ]
            )
        elif severity == DriftSeverity.HIGH:
            recommendations.extend(
                [
                    "Schedule model retraining within 24-48 hours",
                    "Monitor model prediction accuracy closely",
                    "Review recent changes in data collection or upstream systems",
                ]
            )
        elif severity == DriftSeverity.MODERATE:
            recommendations.extend(
                [
                    "Plan model retraining for next maintenance window",
                    "Analyze drifted features for business impact",
                    "Consider collecting more training data with current distribution",
                ]
            )
        else:  # LOW
            recommendations.append("Monitor drift trends - no immediate action required")

        # Feature-specific recommendations
        high_drift_features = [
            f.feature_name
            for f in feature_results
            if f.drift_detected and f.drift_score > self.psi_threshold * 2
        ]

        if high_drift_features:
            recommendations.append(
                f"Features with highest drift: {', '.join(high_drift_features[:5])}"
            )

        return recommendations

    def get_last_report(self) -> Optional[DriftReport]:
        """Get the most recent drift report."""
        return self._last_report

    def get_drift_history(
        self,
        limit: int = 10,
        since: Optional[datetime] = None,
    ) -> List[DriftReport]:
        """
        Get drift detection history.

        Args:
            limit: Maximum number of reports to return
            since: Filter to reports after this timestamp

        Returns:
            List of DriftReport ordered by timestamp (newest first)
        """
        history = self._drift_history

        if since:
            history = [r for r in history if r.timestamp >= since]

        return sorted(history, key=lambda r: r.timestamp, reverse=True)[:limit]

    def should_trigger_retraining(self, report: Optional[DriftReport] = None) -> bool:
        """
        Determine if drift severity warrants model retraining.

        Args:
            report: Drift report to evaluate (uses last report if None)

        Returns:
            True if retraining is recommended
        """
        report = report or self._last_report

        if report is None:
            return False

        return report.dataset_drift and report.drift_severity in (
            DriftSeverity.HIGH,
            DriftSeverity.CRITICAL,
        )

    def should_send_alert(self, report: Optional[DriftReport] = None) -> bool:
        """
        Determine if drift severity warrants sending an alert.

        Args:
            report: Drift report to evaluate (uses last report if None)

        Returns:
            True if alert should be sent
        """
        if not self.alert_config.enabled:
            return False

        report = report or self._last_report

        if report is None:
            return False

        return report.drift_severity in self.alert_config.alert_on_severity

    def update_reference_baseline(
        self,
        new_data: pd.DataFrame,
        strategy: str = "replace",
    ) -> bool:
        """
        Update the reference baseline data.

        Args:
            new_data: New data to use as reference
            strategy: Update strategy:
                - "replace": Replace reference entirely with new data
                - "append": Add new data to existing reference
                - "rolling": Keep most recent N samples

        Returns:
            True if update successful
        """
        self._check_dependencies()

        try:
            if strategy == "replace":
                self._reference_data = new_data.copy()

            elif strategy == "append":
                if self._reference_data is not None:
                    self._reference_data = pd_module.concat(
                        [self._reference_data, new_data],
                        ignore_index=True,
                    )
                else:
                    self._reference_data = new_data.copy()

            elif strategy == "rolling":
                if self._reference_data is not None:
                    combined = pd_module.concat(
                        [self._reference_data, new_data],
                        ignore_index=True,
                    )
                    # Keep most recent samples
                    max_samples = len(new_data) * 2  # 2x the new data size
                    self._reference_data = combined.tail(max_samples)
                else:
                    self._reference_data = new_data.copy()

            else:
                logger.error(f"Unknown update strategy: {strategy}")
                return False

            # Update feature columns
            self._feature_columns = [
                col
                for col in self._reference_data.columns
                if col.lower() not in ("target", "label", "y", "prediction", "timestamp", "id")
            ]

            logger.info(
                f"Reference baseline updated ({strategy}): "
                f"{len(self._reference_data)} samples, {len(self._feature_columns)} features"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update reference baseline: {e}")
            return False

    def save_reference_baseline(
        self,
        path: Optional[Union[str, Path]] = None,
    ) -> bool:
        """
        Save current reference baseline to file.

        Args:
            path: File path (uses configured path if None)

        Returns:
            True if saved successfully
        """
        if self._reference_data is None:
            logger.error("No reference data to save")
            return False

        try:
            save_path = Path(path or self.reference_data_path)
            save_path.parent.mkdir(parents=True, exist_ok=True)

            if save_path.suffix == ".parquet":
                self._reference_data.to_parquet(save_path, index=False)
            else:
                self._reference_data.to_csv(save_path, index=False)

            logger.info(f"Reference baseline saved to: {save_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save reference baseline: {e}")
            return False


# Module-level detector instance
_drift_detector: Optional[DriftDetector] = None


def get_drift_detector(
    reference_data_path: Optional[str] = None,
    psi_threshold: float = DRIFT_PSI_THRESHOLD,
) -> DriftDetector:
    """
    Get the global drift detector instance.

    Args:
        reference_data_path: Path to reference baseline data
        psi_threshold: PSI threshold for drift detection

    Returns:
        Initialized DriftDetector
    """
    global _drift_detector

    if _drift_detector is None:
        _drift_detector = DriftDetector(
            reference_data_path=reference_data_path,
            psi_threshold=psi_threshold,
        )

    return _drift_detector


def detect_drift(
    current_data: Union[pd.DataFrame, str, Path],
    reference_data: Optional[Union[pd.DataFrame, str, Path]] = None,
) -> DriftReport:
    """
    Detect drift using the global detector.

    Args:
        current_data: Current production data
        reference_data: Reference baseline (uses configured path if None)

    Returns:
        DriftReport with detection results
    """
    detector = get_drift_detector()

    if reference_data is not None:
        detector.load_reference_data(reference_data)

    return detector.detect_drift(current_data)


def check_drift_and_alert(
    current_data: Union[pd.DataFrame, str, Path],
) -> Dict[str, Any]:
    """
    Check for drift and return alert status.

    Args:
        current_data: Current production data

    Returns:
        Dict with drift status, alert recommendation, and report
    """
    detector = get_drift_detector()
    report = detector.detect_drift(current_data)

    return {
        "drift_detected": report.dataset_drift,
        "severity": report.drift_severity.value,
        "should_alert": detector.should_send_alert(report),
        "should_retrain": detector.should_trigger_retraining(report),
        "report": report.to_dict(),
    }


# Export key classes and functions
__all__ = [
    # Enums
    "DriftSeverity",
    "DriftStatus",
    # Data Classes
    "FeatureDriftResult",
    "DriftReport",
    "DriftAlertConfig",
    # Main Class
    "DriftDetector",
    # Availability Flags
    "EVIDENTLY_AVAILABLE",
    "PANDAS_AVAILABLE",
    # Configuration
    "REFERENCE_DATA_PATH",
    "DRIFT_CHECK_INTERVAL_HOURS",
    "DRIFT_PSI_THRESHOLD",
    "DRIFT_SHARE_THRESHOLD",
    "MIN_SAMPLES_FOR_DRIFT",
    # Convenience Functions
    "get_drift_detector",
    "detect_drift",
    "check_drift_and_alert",
]
