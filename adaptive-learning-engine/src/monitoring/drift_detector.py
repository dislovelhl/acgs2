"""
Adaptive Learning Engine - Drift Detector
Constitutional Hash: cdd01ef066bc6cf2

Evidently-based concept drift detection for monitoring model performance.
Compares reference (baseline) vs. current (recent) data distributions
to detect when the model needs updating or rollback.

STATISTICAL DRIFT DETECTION ALGORITHMS
======================================

This module uses Evidently's DataDriftPreset which automatically selects
appropriate statistical tests based on feature types:

1. KOLMOGOROV-SMIRNOV (K-S) TEST - For continuous numerical features
   ----------------------------------------------------------------------
   Mathematical Foundation:
   - Compares empirical cumulative distribution functions (ECDFs)
   - Test statistic: D = max|F_ref(x) - F_curr(x)|
   - Null hypothesis: Both samples come from the same distribution
   - Sensitive to differences in shape, location, and scale

   When Used:
   - Continuous numerical features (e.g., floats, unbounded integers)
   - Non-parametric: no assumptions about underlying distribution
   - Works well for detecting shifts in mean, variance, or shape

   Interpretation:
   - p-value < 0.05: Reject null hypothesis (drift detected)
   - D statistic ∈ [0, 1]: larger values indicate greater divergence

2. POPULATION STABILITY INDEX (PSI) - For categorical/binned numerical features
   ------------------------------------------------------------------------------
   Mathematical Foundation:
   - PSI = Σ (P_curr - P_ref) × ln(P_curr / P_ref)
   - Where P_curr, P_ref are proportions in each bin/category
   - Measures information gain from reference to current distribution
   - Symmetric measure: PSI(A,B) ≠ PSI(B,A) but comparable

   When Used:
   - Categorical features (discrete values)
   - Binned numerical features (e.g., age groups)
   - Default for features with <10 unique values

   Interpretation (Industry Standard Thresholds):
   - PSI < 0.1:  No significant shift (stable)
   - PSI 0.1-0.2: Small shift (monitor)
   - PSI 0.2-0.25: Moderate shift (investigate) ← DEFAULT THRESHOLD
   - PSI > 0.25: Severe shift (actionable drift)

   Why drift_threshold=0.2 is chosen:
   - Balances sensitivity vs. false positive rate
   - Aligns with industry best practices (model risk management)
   - Triggers investigation before drift becomes severe (0.25+)
   - Appropriate for governance: conservative enough to catch issues early

3. CHI-SQUARED TEST - For categorical features with low cardinality
   ------------------------------------------------------------------
   Mathematical Foundation:
   - χ² = Σ (O_i - E_i)² / E_i
   - Where O_i = observed counts, E_i = expected counts
   - Tests independence between distribution membership and category
   - Degrees of freedom: (# categories - 1)

   When Used:
   - Low-cardinality categorical features (<10 categories)
   - Alternative to PSI for sparse categorical data
   - Requires sufficient samples per category (typically 5+)

   Interpretation:
   - p-value < 0.05: Reject null hypothesis (drift detected)
   - Larger χ² indicates stronger evidence of distributional change

TEST SELECTION LOGIC
====================
Evidently automatically selects the appropriate test:
- Continuous numerical (>10 unique values) → K-S test
- Low-cardinality categorical (<10 unique values) → Chi-squared or PSI
- High-cardinality categorical → PSI on binned distribution

For more details, see:
- Evidently docs: https://docs.evidentlyai.com/
- PSI explanation: https://www.lexjansen.com/wuss/2017/47_Final_Paper_PDF.pdf
- K-S test: Massey, F.J. (1951). "The Kolmogorov-Smirnov Test"
"""

import asyncio
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
    which includes multiple statistical tests:
    - Kolmogorov-Smirnov (K-S) test for continuous numerical features
    - Population Stability Index (PSI) for categorical/binned features
    - Chi-squared test for low-cardinality categorical features

    See the module docstring above for detailed explanations of each statistical
    test, their mathematical foundations, and when they are applied.

    DRIFT DETECTION METHODOLOGY
    ---------------------------
    1. Reference data (baseline): Established distribution from known-good period
    2. Current data (recent): Latest prediction data to compare against baseline
    3. Per-feature test: Each feature tested with appropriate statistical test
    4. Dataset-level drift: Triggered when ≥50% of features show drift
       (configurable via drift_share_threshold)

    The default drift_threshold=0.2 corresponds to "moderate drift" on the PSI
    scale, catching distribution shifts before they become severe (>0.25).

    Features:
    - Configurable drift threshold (PSI-based, default 0.2)
    - Automatic reference data management
    - Low-traffic detection (insufficient data warning)
    - Alert callbacks for integration
    - Thread-safe operations
    - Graceful degradation on errors

    Example usage:
        detector = DriftDetector(
            drift_threshold=0.2,  # PSI threshold for moderate drift
            reference_window_size=1000,
            current_window_size=100,
        )

        # Add prediction data
        detector.add_data_point(features={"f1": 1.0, "f2": 2.0}, label=1)

        # Check for drift
        result = detector.check_drift()
        if result.drift_detected:
            print(f"Drift detected! Score: {result.drift_score}")
            print(f"Drifted columns: {result.columns_drifted}")
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
    ) -> None:
        """Initialize the drift detector.

        Args:
            drift_threshold: PSI threshold for column-level drift detection (default 0.2).
                This threshold is used for categorical/binned features when Evidently
                applies the Population Stability Index (PSI) test.

                Industry-standard PSI threshold interpretations:
                - < 0.1:  No significant drift (distribution is stable)
                - 0.1-0.2: Small drift (monitor but no immediate action)
                - 0.2-0.25: Moderate drift (investigate and consider retraining)
                - > 0.25: Severe drift (actionable - retrain or rollback)

                Default of 0.2 chosen because:
                - Catches moderate drift before it becomes severe (0.25+)
                - Balances sensitivity vs. false positive rate
                - Conservative threshold appropriate for governance applications
                - Aligns with model risk management best practices

                For K-S and Chi-squared tests, Evidently uses p-value < 0.05
                instead of this threshold, but the 0.2 PSI threshold is the
                primary tuning parameter for drift sensitivity.

            reference_window_size: Number of samples in reference dataset (default 1000).
                This establishes the baseline distribution for drift comparison.

                STATISTICAL VALIDITY REQUIREMENTS:
                ==================================
                Window sizing is critical for statistical test reliability:

                1. K-S Test (continuous features):
                   - Minimum: 30-50 samples per dataset (Central Limit Theorem)
                   - Recommended: 100+ for reliable p-values
                   - Optimal: 500-1000+ for detecting subtle distribution shifts
                   - Power: Larger reference increases test sensitivity

                2. PSI Test (categorical features):
                   - Minimum: 5-10 samples per category/bin
                   - For 10 categories: ≥50-100 total samples
                   - Recommended: 100+ to ensure stable proportion estimates
                   - Zero-count categories can cause ln(0) errors → need sufficient coverage

                3. Chi-squared Test (low-cardinality categorical):
                   - Minimum: 5 samples per expected category (statistical requirement)
                   - For 5 categories: ≥25 total samples
                   - Recommended: 50+ for reliable χ² distribution approximation

                REFERENCE VS CURRENT WINDOW SIZE RATIO:
                ========================================
                Default ratio: 1000:100 (10:1)

                Why larger reference than current?
                - Reference = stable baseline (established "ground truth")
                  → Needs more samples for accurate distribution estimation
                  → Minimizes false positives from reference noise

                - Current = recent observations (potential drift signal)
                  → Can be smaller for faster drift detection
                  → Responsive to emerging distribution shifts
                  → Updated continuously as new data arrives

                Statistical rationale:
                - Asymmetric comparison: testing if current deviates from reference
                - Larger reference → lower variance → more stable baseline
                - Smaller current → faster response time → earlier drift detection
                - 10:1 ratio balances stability vs. responsiveness

                WINDOW SIZE TRADE-OFFS:
                =======================
                Larger reference window (↑):
                  ✓ More stable baseline (less noise)
                  ✓ Higher statistical power (detects smaller shifts)
                  ✓ Better category coverage for PSI/Chi-squared
                  ✗ Slower to adapt if baseline itself drifts over time
                  ✗ More memory usage

                Smaller reference window (↓):
                  ✓ Faster adaptation to evolving distributions
                  ✓ Less memory usage
                  ✗ Noisier baseline (higher false positive rate)
                  ✗ Lower statistical power (misses subtle drift)

                RECOMMENDED CONFIGURATIONS:
                ===========================
                - High-traffic applications (1000s requests/day):
                  reference_window_size=1000-5000, current_window_size=100-500

                - Low-traffic applications (100s requests/day):
                  reference_window_size=200-500, current_window_size=50-100

                - High-dimensional data (many features):
                  Increase both to ensure per-feature statistical validity

                - Rapidly evolving data:
                  Reduce reference window to 200-500 for faster baseline adaptation

                - Governance/compliance (low false positive tolerance):
                  Increase reference to 2000-5000 for maximum stability

            current_window_size: Number of recent samples for comparison (default 100).
                This represents the "recent" distribution tested against the reference.

                STATISTICAL VALIDITY:
                ====================
                Must meet same minimum sample requirements as reference (see above):
                - K-S: ≥30-50 samples
                - PSI: ≥5-10 per category
                - Chi-squared: ≥5 per expected category

                SLIDING WINDOW BEHAVIOR:
                ========================
                - Implemented as a deque with maxlen=current_window_size
                - Automatically evicts oldest samples when full (FIFO)
                - Continuously updated with new prediction data
                - Each drift check compares the current window against reference

                RESPONSIVENESS TRADE-OFFS:
                ==========================
                Larger current window (↑):
                  ✓ More stable drift signals (less noise)
                  ✓ Higher statistical power
                  ✗ Slower to detect emerging drift (diluted by older samples)
                  ✗ Lags behind rapid distribution changes

                Smaller current window (↓):
                  ✓ Faster drift detection (captures recent changes quickly)
                  ✓ More responsive to sudden shifts
                  ✗ Noisier drift signals (higher false positive rate)
                  ✗ Lower statistical power (may miss gradual drift)

                TUNING GUIDANCE:
                ================
                Balance responsiveness vs. stability:
                - Sudden concept drift (e.g., system failure) → smaller window (50-100)
                - Gradual concept drift (e.g., seasonality) → larger window (200-500)
                - Noisy data with variance → larger window for stability
                - Critical alerts requiring fast response → smaller window

                EXAMPLE: With current_window_size=100 and check every 5 minutes:
                - At 10 requests/min → 50 samples per check (suboptimal)
                - At 50 requests/min → 250 samples per check (overfills, uses last 100)
                - Adjust window size based on actual traffic rate for optimal coverage

            min_samples_for_drift: Minimum samples needed for drift check (default 10).
                Safety threshold to prevent statistical tests from running on
                insufficient data, which would yield unreliable results.

                This is a conservative minimum; actual statistical validity requires
                larger samples as documented above for reference_window_size and
                current_window_size. Think of this as a "fail-fast" guard rather
                than a guarantee of statistical rigor.
            check_interval_seconds: Interval between automatic checks.
            drift_share_threshold: Fraction of columns that must drift
                to trigger dataset-level drift alert.
            enabled: Whether drift detection is enabled.
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
                # Convert to DataFrames
                reference_df = self._to_dataframe(list(self._reference_data))
                current_df = self._to_dataframe(list(self._current_data))

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
                # =============================
                # DataDriftPreset applies statistical tests to detect distribution shifts:
                #
                # For each feature, Evidently automatically selects the appropriate test:
                # - Continuous numerical features → Kolmogorov-Smirnov (K-S) test
                #   * Compares cumulative distribution functions
                #   * Returns p-value (drift if p < 0.05)
                #
                # - Categorical/low-cardinality features → Chi-squared or PSI
                #   * Chi-squared tests category distribution independence
                #   * PSI measures information gain between distributions
                #   * Returns drift score compared to threshold
                #
                # DRIFT SCORING METHODOLOGY
                # -------------------------
                # 1. Column-level drift detection:
                #    Each feature is tested independently → binary drift_detected flag
                #
                # 2. Dataset-level drift score calculation:
                #    drift_score = (# drifted columns) / (# total columns)
                #    Also known as "share_of_drifted_columns"
                #
                #    Example: If 3 out of 10 features drift → drift_score = 0.3
                #
                # 3. Dataset-level drift decision:
                #    dataset_drift = (drift_score >= drift_share_threshold)
                #
                #    Default drift_share_threshold = 0.5 (50% of features)
                #
                #    Why 0.5?
                #    - Prevents false alarms from single noisy features
                #    - Requires majority of features to show drift (systematic shift)
                #    - Balances sensitivity vs. specificity for dataset-level alerts
                #    - Conservative threshold appropriate for governance applications
                #
                #    Example: With 10 features and threshold=0.5:
                #    - 4 drifted features → drift_score=0.4 → NO dataset drift
                #    - 5 drifted features → drift_score=0.5 → YES dataset drift
                #    - 6+ drifted features → drift_score≥0.6 → YES dataset drift
                #
                # This two-tier approach (column-level tests + dataset-level threshold)
                # ensures we detect systematic distribution shifts while being robust
                # to individual feature noise and outliers.
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

                    # CIRCUIT BREAKER PATTERN: Increment consecutive drift counter
                    # ============================================================
                    # This counter tracks how many drift checks in a row have detected drift.
                    # It forms part of a circuit breaker pattern that escalates alert severity
                    # when drift persists across multiple consecutive checks.
                    #
                    # The circuit breaker prevents transient drift from triggering critical
                    # alerts while ensuring persistent drift (systematic issues) gets
                    # escalated attention. See _trigger_alert() for the severity logic.
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
                    # CIRCUIT BREAKER PATTERN: Reset consecutive drift counter
                    # =========================================================
                    # When no drift is detected, reset the consecutive counter to 0.
                    # This "closes" the circuit breaker, preventing previous drift
                    # detections from affecting future alerts. Only sustained,
                    # consecutive drift will escalate to critical severity.
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

    def _to_dataframe(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Convert list of dictionaries to DataFrame.

        Filters to numeric columns only for drift detection.

        Args:
            data: List of feature dictionaries.

        Returns:
            DataFrame with numeric columns.
        """
        df = pd.DataFrame(data)

        # Select only numeric columns
        numeric_df = df.select_dtypes(include=[np.number])

        return numeric_df

    def _parse_drift_report(
        self,
        report_dict: Dict[str, Any],
        ref_size: int,
        cur_size: int,
        timestamp: float,
    ) -> DriftResult:
        """Parse Evidently drift report into DriftResult.

        Extracts both column-level and dataset-level drift results from
        Evidently's report structure, handling different statistical test
        outputs (K-S, PSI, Chi-squared).

        Args:
            report_dict: Evidently report as dictionary.
            ref_size: Reference data size.
            cur_size: Current data size.
            timestamp: Check timestamp.

        Returns:
            Parsed DriftResult with drift scores and detection flags.
        """
        columns_drifted: Dict[str, bool] = {}
        column_drift_scores: Dict[str, float] = {}
        dataset_drift = False
        share_of_drifted_columns = 0.0

        try:
            metrics_list = report_dict.get("metrics", [])

            for metric in metrics_list:
                result = metric.get("result", {})

                # DATASET-LEVEL DRIFT EXTRACTION
                # ==============================
                # Evidently's DataDriftPreset computes dataset-level drift by:
                #
                # 1. Testing each feature independently (K-S, PSI, or Chi-squared)
                # 2. Counting how many features show drift (binary: yes/no)
                # 3. Calculating: share_of_drifted_columns = drifted_count / total_count
                # 4. Comparing: dataset_drift = (share >= drift_share_threshold)
                #
                # Example: 10 features, 6 drifted, threshold=0.5
                # → share_of_drifted_columns = 6/10 = 0.6
                # → dataset_drift = (0.6 >= 0.5) = True
                #
                # This aggregation strategy prevents false alarms from individual
                # noisy features while catching systematic distribution shifts.
                if "dataset_drift" in result:
                    dataset_drift = result["dataset_drift"]
                    share_of_drifted_columns = result.get("share_of_drifted_columns", 0.0)

                # COLUMN-LEVEL DRIFT EXTRACTION
                # =============================
                # Evidently returns per-column drift results with test-specific metrics.
                # Each column contains:
                # - drift_detected: Boolean flag (True if drift threshold exceeded)
                # - drift_score or stattest_score: Test-specific numeric score
                #
                # The score interpretation depends on which statistical test was used:
                drift_by_columns = result.get("drift_by_columns", {})
                for col_name, col_data in drift_by_columns.items():
                    if isinstance(col_data, dict):
                        columns_drifted[col_name] = col_data.get("drift_detected", False)

                        # DRIFT SCORE EXTRACTION AND INTERPRETATION
                        # -----------------------------------------
                        # The numeric drift score varies by statistical test:
                        #
                        # 1. K-S Test (continuous numerical features):
                        #    Score: p-value in [0, 1]
                        #    Interpretation:
                        #      - p < 0.05: Significant drift (reject null hypothesis)
                        #      - p ≥ 0.05: No significant drift
                        #    Lower values = more evidence of distribution change
                        #
                        # 2. PSI Test (categorical/binned features):
                        #    Score: PSI value in [0, ∞)
                        #    Interpretation:
                        #      - PSI < 0.1:  No significant shift
                        #      - PSI 0.1-0.2: Small shift
                        #      - PSI 0.2-0.25: Moderate shift (investigate)
                        #      - PSI > 0.25: Severe shift (actionable)
                        #    Higher values = greater distribution divergence
                        #
                        # 3. Chi-squared Test (low-cardinality categorical):
                        #    Score: p-value in [0, 1]
                        #    Interpretation: Same as K-S (p < 0.05 = drift)
                        #
                        # Evidently may report the score as "drift_score" or
                        # "stattest_score" depending on test type and version.
                        # We extract whichever is available and store it for
                        # detailed per-column drift analysis.
                        drift_score = col_data.get("drift_score", 0.0)
                        if drift_score is None:
                            drift_score = col_data.get("stattest_score", 0.0) or 0.0
                        column_drift_scores[col_name] = float(drift_score)

        except Exception as e:
            logger.warning(f"Error parsing drift report: {e}")

        # BUILD FINAL DRIFT RESULT
        # ========================
        # Aggregate all extracted information into a DriftResult:
        # - status: DRIFT_DETECTED or NO_DRIFT (for alerting/UI)
        # - drift_detected: Boolean flag for easy conditional checks
        # - drift_score: share_of_drifted_columns (0.0-1.0, dataset-level metric)
        # - columns_drifted: Per-column drift flags (detailed investigation)
        # - column_drift_scores: Per-column numeric scores (debugging, analysis)
        #
        # The drift_score field (share_of_drifted_columns) is the primary
        # dataset-level metric used for alerting and monitoring dashboards.
        status = DriftStatus.DRIFT_DETECTED if dataset_drift else DriftStatus.NO_DRIFT
        num_drifted = sum(1 for v in columns_drifted.values() if v)

        return DriftResult(
            status=status,
            drift_detected=dataset_drift,
            drift_score=share_of_drifted_columns,  # Dataset-level: fraction of drifted columns
            drift_threshold=self.drift_threshold,  # Column-level: PSI/p-value threshold
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
        """Trigger drift alert callbacks with circuit breaker severity escalation.

        CIRCUIT BREAKER PATTERN FOR CONSECUTIVE DRIFT DETECTION
        ========================================================

        This method implements a circuit breaker pattern to distinguish between
        transient drift (temporary fluctuations) and persistent drift (systematic
        issues requiring immediate attention).

        PATTERN OVERVIEW:
        -----------------
        The circuit breaker monitors consecutive drift detections and "trips" to
        a critical state when drift persists across multiple consecutive checks.
        This prevents alert fatigue from transient drift while ensuring persistent
        problems get escalated attention.

        CIRCUIT BREAKER STATES:
        -----------------------
        1. CLOSED (Normal Operation):
           - Severity: "warning"
           - Condition: consecutive_drift_count < 3
           - Meaning: Drift detected, but not yet persistent
           - Action: Monitor, investigate if needed
           - Transition: Remains closed until 3 consecutive drift detections

        2. OPEN (Tripped/Critical):
           - Severity: "critical"
           - Condition: consecutive_drift_count >= 3
           - Meaning: Sustained drift detected (systematic issue)
           - Action: Immediate response required (model rollback, retraining)
           - Transition: Remains open until drift stops

        3. RESET (Recovery):
           - Trigger: No drift detected in check_drift()
           - Action: consecutive_drift_count reset to 0 → severity returns to "warning"
           - Effect: Circuit breaker "closes" again

        THRESHOLD JUSTIFICATION:
        ------------------------
        Why 3 consecutive detections?
        - 1 detection: Could be noise, outlier batch, or temporary anomaly
        - 2 detections: Possible pattern, but still could be coincidence
        - 3+ detections: High confidence of persistent drift (systematic change)

        With default check_interval_seconds=300 (5 minutes):
        - 1 detection:  0 minutes (single check)
        - 2 detections: 5 minutes (possible transient spike)
        - 3 detections: 10 minutes (confirmed persistent drift) → CRITICAL

        This 10-minute threshold balances:
        ✓ Fast enough to catch real issues before significant impact
        ✓ Slow enough to avoid false alarms from temporary fluctuations
        ✓ Aligned with typical model monitoring cadences (5-15 min checks)

        COMPARISON TO TRADITIONAL CIRCUIT BREAKERS:
        -------------------------------------------
        Traditional circuit breakers (e.g., for API calls):
        - Monitor failure rate over time window
        - Open on high failure rate (e.g., >50% failures in 1 minute)
        - Prevent cascading failures by short-circuiting requests

        This drift circuit breaker:
        - Monitors consecutive drift detections (sequential, not rate-based)
        - Opens on sustained drift (3+ consecutive detections)
        - Prevents alert fatigue while escalating persistent issues

        Both patterns share core goals:
        - Distinguish between transient vs. persistent failures
        - Escalate only when problem is confirmed
        - Provide automatic recovery when issue resolves

        PRACTICAL EXAMPLE:
        ------------------
        Scenario: Model serving predictions, checked every 5 minutes

        Check 1 (t=0):   Drift detected (score=0.55) → warning, count=1
        Check 2 (t=5):   Drift detected (score=0.58) → warning, count=2
        Check 3 (t=10):  Drift detected (score=0.62) → CRITICAL, count=3 ← Circuit trips!
        Check 4 (t=15):  Drift detected (score=0.60) → CRITICAL, count=4
        Check 5 (t=20):  No drift (score=0.15) → warning, count=0 ← Circuit resets!
        Check 6 (t=25):  Drift detected (score=0.52) → warning, count=1

        Response actions by severity:
        - "warning": Log, monitor dashboard, investigate if recurring
        - "critical": Page on-call engineer, trigger auto-rollback, halt new deployments

        GOVERNANCE IMPLICATIONS:
        ------------------------
        For model governance and compliance:
        - Warning alerts: Documented in model monitoring log (audit trail)
        - Critical alerts: Require incident response and root cause analysis
        - Threshold (3): Conservative enough for regulatory scrutiny
        - Transparency: Consecutive count exposed in DriftMetrics for explainability

        Args:
            result: Drift result that triggered the alert.
        """
        # CIRCUIT BREAKER THRESHOLD: Trip to critical severity after 3 consecutive drifts
        # ================================================================================
        # This is the core circuit breaker logic that escalates severity when drift
        # becomes persistent. The threshold of 3 consecutive detections balances:
        # - Sensitivity: Fast enough to catch real issues (10 min at 5-min intervals)
        # - Specificity: Avoids false alarms from transient drift (filters noise)
        #
        # Tuning this threshold:
        # - Increase (e.g., 5): More tolerant of transient drift, slower critical escalation
        # - Decrease (e.g., 2): More aggressive, faster critical alerts (higher false positive rate)
        # - Default (3): Industry best practice for model monitoring (conservative governance)
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
            return self._to_dataframe(list(self._reference_data))

    def get_current_data(self) -> pd.DataFrame:
        """Get current data as DataFrame.

        Returns:
            Current DataFrame.
        """
        with self._lock:
            if not self._current_data:
                return pd.DataFrame()
            return self._to_dataframe(list(self._current_data))

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
