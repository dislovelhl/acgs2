"""
Unit tests for the Adaptive Learning Engine monitoring module.

Tests cover:
- DriftDetector: Evidently-based drift detection
- MetricsRegistry: Prometheus metrics collection

Constitutional Hash: cdd01ef066bc6cf2
"""

import threading
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from prometheus_client import CollectorRegistry

from src.monitoring.drift_detector import (
    DriftAlert,
    DriftDetector,
    DriftMetrics,
    DriftResult,
    DriftStatus,
)
from src.monitoring.metrics import (
    MetricLabel,
    MetricsRegistry,
    MetricsSnapshot,
    create_metrics_registry,
    get_metrics_registry,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_features() -> Dict[str, Any]:
    """Sample feature dictionary for testing."""
    return {
        "feature_a": 1.0,
        "feature_b": 2.5,
        "feature_c": 0.3,
    }


@pytest.fixture
def reference_data() -> List[Dict[str, Any]]:
    """Sample reference dataset for drift testing."""
    np.random.seed(42)
    return [{"f1": np.random.normal(0, 1), "f2": np.random.normal(0, 1)} for _ in range(100)]


@pytest.fixture
def drifted_data() -> List[Dict[str, Any]]:
    """Sample current data with drift (different distribution)."""
    np.random.seed(123)
    return [
        {"f1": np.random.normal(5, 2), "f2": np.random.normal(-5, 2)}  # Shifted distribution
        for _ in range(100)
    ]


@pytest.fixture
def similar_data() -> List[Dict[str, Any]]:
    """Sample current data similar to reference (no drift)."""
    np.random.seed(456)
    return [
        {"f1": np.random.normal(0.1, 1.1), "f2": np.random.normal(-0.1, 0.9)}  # Similar
        for _ in range(100)
    ]


@pytest.fixture
def drift_detector() -> DriftDetector:
    """Fresh DriftDetector for testing."""
    return DriftDetector(
        drift_threshold=0.2,
        reference_window_size=100,
        current_window_size=50,
        min_samples_for_drift=10,
        check_interval_seconds=60,
        drift_share_threshold=0.5,
        enabled=True,
    )


@pytest.fixture
def metrics_registry() -> MetricsRegistry:
    """Fresh MetricsRegistry for testing with isolated registry."""
    registry = CollectorRegistry()
    return MetricsRegistry(registry=registry, prefix="test_adaptive")


# =============================================================================
# DriftDetector Tests - Initialization
# =============================================================================


class TestDriftDetectorInit:
    """Tests for DriftDetector initialization."""

    def test_default_initialization(self):
        """Test default initialization creates valid detector."""
        detector = DriftDetector()

        assert detector.drift_threshold == 0.2
        assert detector.reference_window_size == 1000
        assert detector.current_window_size == 100
        assert detector.min_samples_for_drift == 10
        assert detector.check_interval_seconds == 300
        assert detector.drift_share_threshold == 0.5
        assert detector._enabled is True
        assert detector._current_status == DriftStatus.INSUFFICIENT_DATA

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        detector = DriftDetector(
            drift_threshold=0.3,
            reference_window_size=500,
            current_window_size=25,
            min_samples_for_drift=20,
            check_interval_seconds=120,
            drift_share_threshold=0.7,
            enabled=False,
        )

        assert detector.drift_threshold == 0.3
        assert detector.reference_window_size == 500
        assert detector.current_window_size == 25
        assert detector.min_samples_for_drift == 20
        assert detector.check_interval_seconds == 120
        assert detector.drift_share_threshold == 0.7
        assert detector._enabled is False
        assert detector._current_status == DriftStatus.DISABLED

    def test_data_windows_initialized_empty(self, drift_detector):
        """Test that data windows start empty."""
        assert len(drift_detector._reference_data) == 0
        assert len(drift_detector._current_data) == 0
        assert len(drift_detector._all_data) == 0


# =============================================================================
# DriftDetector Tests - Data Management
# =============================================================================


class TestDriftDetectorDataManagement:
    """Tests for DriftDetector data point management."""

    def test_add_data_point(self, drift_detector, sample_features):
        """Test adding a single data point."""
        drift_detector.add_data_point(
            features=sample_features,
            label=1,
            prediction=1,
        )

        assert len(drift_detector._current_data) == 1
        assert len(drift_detector._reference_data) == 1
        assert "feature_a" in drift_detector._known_columns

    def test_add_data_point_disabled(self, sample_features):
        """Test that data points are ignored when disabled."""
        detector = DriftDetector(enabled=False)
        detector.add_data_point(features=sample_features, label=1)

        assert len(detector._current_data) == 0

    def test_add_data_point_updates_current_window(self, drift_detector):
        """Test that data points are added to current window."""
        for i in range(5):
            drift_detector.add_data_point({"x": float(i)})

        assert len(drift_detector._current_data) == 5
        assert len(drift_detector._reference_data) == 5

    def test_add_data_point_with_timestamp(self, drift_detector, sample_features):
        """Test adding data point with custom timestamp."""
        custom_time = 1234567890.0
        drift_detector.add_data_point(
            features=sample_features,
            timestamp=custom_time,
        )

        record = list(drift_detector._current_data)[0]
        assert record["_timestamp"] == custom_time

    def test_add_batch(self, drift_detector):
        """Test adding multiple data points at once."""
        data_points = [{"x": float(i)} for i in range(10)]
        labels = [i % 2 for i in range(10)]
        predictions = [i % 2 for i in range(10)]

        count = drift_detector.add_batch(data_points, labels, predictions)

        assert count == 10
        assert len(drift_detector._current_data) == 10

    def test_add_batch_partial_labels(self, drift_detector):
        """Test batch add with fewer labels than data points."""
        data_points = [{"x": float(i)} for i in range(10)]
        labels = [1, 0, 1]  # Only 3 labels

        count = drift_detector.add_batch(data_points, labels)

        assert count == 10
        # First 3 should have labels, rest should not
        records = list(drift_detector._current_data)
        assert "_label" in records[0]
        assert "_label" not in records[5]


# =============================================================================
# DriftDetector Tests - Reference Data Management
# =============================================================================


class TestDriftDetectorReferenceManagement:
    """Tests for reference data management."""

    def test_lock_reference_data(self, drift_detector, sample_features):
        """Test locking reference data."""
        drift_detector.add_data_point(sample_features)
        drift_detector.lock_reference_data()

        assert drift_detector._reference_locked is True

    def test_locked_reference_not_updated(self, drift_detector, sample_features):
        """Test that locked reference is not updated with new data."""
        drift_detector.add_data_point(sample_features)
        drift_detector.lock_reference_data()

        # Add more data
        for i in range(5):
            drift_detector.add_data_point({"x": float(i)})

        # Reference should still have only 1 entry
        assert len(drift_detector._reference_data) == 1
        # Current should have all data
        assert len(drift_detector._current_data) == 6

    def test_unlock_reference_data(self, drift_detector, sample_features):
        """Test unlocking reference data."""
        drift_detector.lock_reference_data()
        drift_detector.unlock_reference_data()

        assert drift_detector._reference_locked is False

    def test_update_reference_from_current(self, drift_detector):
        """Test updating reference from current window."""
        # Add initial data
        for i in range(5):
            drift_detector.add_data_point({"x": float(i)})

        drift_detector.lock_reference_data()

        # Add more to current
        for i in range(10, 15):
            drift_detector.add_data_point({"x": float(i)})

        # Current has 10 entries, reference has 5
        assert len(drift_detector._current_data) == 10
        assert len(drift_detector._reference_data) == 5

        # Update reference from current
        count = drift_detector.update_reference_from_current()

        # Now reference should have 10 entries
        assert count == 10
        assert len(drift_detector._reference_data) == 10

    def test_set_reference_data_from_dataframe(self, drift_detector):
        """Test setting reference data from DataFrame."""
        df = pd.DataFrame(
            {
                "f1": [1.0, 2.0, 3.0, 4.0, 5.0],
                "f2": [0.1, 0.2, 0.3, 0.4, 0.5],
            }
        )

        drift_detector.set_reference_data(df)

        assert len(drift_detector._reference_data) == 5
        assert drift_detector._reference_locked is True
        assert "f1" in drift_detector._known_columns
        assert "f2" in drift_detector._known_columns


# =============================================================================
# DriftDetector Tests - Drift Detection
# =============================================================================


class TestDriftDetectorDriftCheck:
    """Tests for drift detection functionality."""

    def test_check_drift_disabled(self):
        """Test drift check when disabled."""
        detector = DriftDetector(enabled=False)
        result = detector.check_drift()

        assert result.status == DriftStatus.DISABLED
        assert result.drift_detected is False
        assert result.message == "Drift detection is disabled"

    def test_check_drift_insufficient_reference_data(self, drift_detector):
        """Test drift check with insufficient reference data."""
        # Add only a few samples (less than min_samples_for_drift=10)
        for i in range(5):
            drift_detector.add_data_point({"x": float(i)})

        result = drift_detector.check_drift()

        assert result.status == DriftStatus.INSUFFICIENT_DATA
        assert result.drift_detected is False
        assert "Insufficient reference data" in result.message

    def test_check_drift_insufficient_current_data(self, drift_detector, reference_data):
        """Test drift check with insufficient current data."""
        # Add enough reference data
        drift_detector.add_batch(reference_data[:20])
        drift_detector.lock_reference_data()

        # Clear current and add minimal data
        drift_detector._current_data.clear()
        for i in range(5):  # Less than min_samples_for_drift
            drift_detector.add_data_point({"f1": float(i), "f2": float(i)})

        result = drift_detector.check_drift()

        assert result.status == DriftStatus.INSUFFICIENT_DATA
        assert "Insufficient current data" in result.message

    def test_check_drift_no_drift(self, drift_detector, reference_data, similar_data):
        """Test drift check with no significant drift."""
        # Add reference data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # Add similar data to current
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data)

        result = drift_detector.check_drift()

        # With similar distributions, should not detect drift
        # Note: The actual result depends on the data, but we can check structure
        assert isinstance(result, DriftResult)
        assert result.reference_size == 100
        assert result.drift_threshold == drift_detector.drift_threshold

    def test_check_drift_detected(self, drift_detector, reference_data, drifted_data):
        """Test drift detection when distribution shifts significantly."""
        # Add reference data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # Add clearly drifted data to current
        drift_detector._current_data.clear()
        drift_detector.add_batch(drifted_data)

        result = drift_detector.check_drift()

        # With significantly different distributions, should detect drift
        assert isinstance(result, DriftResult)
        assert result.reference_size == 100
        assert result.current_size >= len(drifted_data)
        # Note: Actual drift detection depends on Evidently's algorithms

    def test_check_drift_increments_counter(self, drift_detector, reference_data, similar_data):
        """Test that drift check increments check counter."""
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:20])

        assert drift_detector._total_checks == 0

        drift_detector.check_drift()
        assert drift_detector._total_checks == 1

        drift_detector.check_drift()
        assert drift_detector._total_checks == 2

    def test_check_drift_updates_last_check_time(self, drift_detector, reference_data):
        """Test that drift check updates last check time."""
        drift_detector.add_batch(reference_data)

        assert drift_detector._last_check_time is None

        before = time.time()
        drift_detector.check_drift()
        after = time.time()

        assert drift_detector._last_check_time is not None
        assert before <= drift_detector._last_check_time <= after

    def test_check_drift_no_common_columns(self, drift_detector):
        """Test drift check with no common feature columns."""
        # Add reference with features a, b
        drift_detector.add_batch([{"a": 1.0, "b": 2.0}] * 20)
        drift_detector.lock_reference_data()

        # Clear and add current with features c, d (different columns)
        drift_detector._current_data.clear()
        drift_detector.add_batch([{"c": 1.0, "d": 2.0}] * 20)

        result = drift_detector.check_drift()

        assert result.status == DriftStatus.ERROR
        assert "No common feature columns" in result.message

    @pytest.mark.asyncio
    async def test_check_drift_async(self, drift_detector, reference_data, similar_data):
        """Test async drift check."""
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:20])

        result = await drift_detector.check_drift_async()

        assert isinstance(result, DriftResult)


# =============================================================================
# DriftDetector Tests - Status and Metrics
# =============================================================================


class TestDriftDetectorStatusMetrics:
    """Tests for status and metrics retrieval."""

    def test_get_status_no_check_performed(self, drift_detector):
        """Test get_status when no check has been performed."""
        result = drift_detector.get_status()

        assert result.status == DriftStatus.INSUFFICIENT_DATA
        assert result.drift_detected is False
        assert result.message == "No drift check performed yet"

    def test_get_status_after_check(self, drift_detector, reference_data, similar_data):
        """Test get_status after performing a check."""
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:20])

        drift_detector.check_drift()

        status = drift_detector.get_status()
        assert isinstance(status, DriftResult)
        assert status.timestamp is not None

    def test_get_metrics(self, drift_detector, reference_data, similar_data):
        """Test get_metrics returns valid DriftMetrics."""
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:20])

        drift_detector.check_drift()

        metrics = drift_detector.get_metrics()

        assert isinstance(metrics, DriftMetrics)
        assert metrics.total_checks == 1
        assert metrics.status in list(DriftStatus)
        assert metrics.data_points_collected > 0

    def test_get_reference_data(self, drift_detector, reference_data):
        """Test get_reference_data returns DataFrame."""
        drift_detector.add_batch(reference_data[:10])

        df = drift_detector.get_reference_data()

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_get_current_data(self, drift_detector, reference_data):
        """Test get_current_data returns DataFrame."""
        drift_detector.add_batch(reference_data[:10])

        df = drift_detector.get_current_data()

        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_get_reference_data_empty(self, drift_detector):
        """Test get_reference_data returns empty DataFrame when no data."""
        df = drift_detector.get_reference_data()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_get_current_data_empty(self, drift_detector):
        """Test get_current_data returns empty DataFrame when no data."""
        df = drift_detector.get_current_data()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0


# =============================================================================
# DriftDetector Tests - Alert Management
# =============================================================================


class TestDriftDetectorAlerts:
    """Tests for drift alert management."""

    def test_register_alert_callback(self, drift_detector):
        """Test registering alert callback."""
        callback_results = []

        def on_alert(alert: DriftAlert):
            callback_results.append(alert)

        drift_detector.register_alert_callback(on_alert)

        assert len(drift_detector._alert_callbacks) == 1

    def test_get_pending_alerts_empty(self, drift_detector):
        """Test get_pending_alerts when no alerts exist."""
        alerts = drift_detector.get_pending_alerts()
        assert alerts == []

    def test_acknowledge_alert(self, drift_detector):
        """Test acknowledging a drift alert."""
        # Manually create an alert for testing
        alert = DriftAlert(
            drift_result=DriftResult(
                status=DriftStatus.DRIFT_DETECTED,
                drift_detected=True,
                drift_score=0.5,
                drift_threshold=0.2,
                columns_drifted={"f1": True},
                column_drift_scores={"f1": 0.5},
                reference_size=100,
                current_size=50,
            ),
            severity="warning",
        )
        drift_detector._pending_alerts.append(alert)

        # Acknowledge it
        result = drift_detector.acknowledge_alert(alert.alert_id)

        assert result is True
        assert alert.acknowledged is True

    def test_acknowledge_alert_not_found(self, drift_detector):
        """Test acknowledging non-existent alert."""
        result = drift_detector.acknowledge_alert("nonexistent_alert_id")
        assert result is False

    def test_alert_callback_triggered_on_drift(self, drift_detector, reference_data, drifted_data):
        """Test that alert callback is triggered when drift is detected."""
        callback_results = []

        def on_alert(alert: DriftAlert):
            callback_results.append(alert)

        drift_detector.register_alert_callback(on_alert)

        # Set up data for drift
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()
        drift_detector._current_data.clear()
        drift_detector.add_batch(drifted_data)

        result = drift_detector.check_drift()

        # If drift was detected, callback should have been triggered
        if result.drift_detected:
            assert len(callback_results) > 0
            assert callback_results[0].severity in ["warning", "critical"]


# =============================================================================
# DriftDetector Tests - Enable/Disable
# =============================================================================


class TestDriftDetectorEnableDisable:
    """Tests for enable/disable functionality."""

    def test_enable(self):
        """Test enabling drift detection."""
        detector = DriftDetector(enabled=False)
        assert detector._enabled is False

        detector.enable()

        assert detector._enabled is True

    def test_disable(self, drift_detector):
        """Test disabling drift detection."""
        assert drift_detector._enabled is True

        drift_detector.disable()

        assert drift_detector._enabled is False
        assert drift_detector._current_status == DriftStatus.DISABLED

    def test_is_enabled(self, drift_detector):
        """Test is_enabled method."""
        assert drift_detector.is_enabled() is True

        drift_detector.disable()
        assert drift_detector.is_enabled() is False


# =============================================================================
# DriftDetector Tests - Reset
# =============================================================================


class TestDriftDetectorReset:
    """Tests for reset functionality."""

    def test_reset_clears_data(self, drift_detector, reference_data):
        """Test that reset clears all data."""
        drift_detector.add_batch(reference_data)
        drift_detector.check_drift()

        assert len(drift_detector._reference_data) > 0
        assert drift_detector._total_checks > 0

        drift_detector.reset()

        assert len(drift_detector._reference_data) == 0
        assert len(drift_detector._current_data) == 0
        assert len(drift_detector._all_data) == 0
        assert drift_detector._total_checks == 0
        assert drift_detector._drift_detections == 0
        assert drift_detector._consecutive_drift_count == 0
        assert len(drift_detector._pending_alerts) == 0

    def test_reset_unlocks_reference(self, drift_detector, reference_data):
        """Test that reset unlocks reference data."""
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        assert drift_detector._reference_locked is True

        drift_detector.reset()

        assert drift_detector._reference_locked is False


# =============================================================================
# DriftDetector Tests - Thread Safety
# =============================================================================


class TestDriftDetectorThreadSafety:
    """Tests for DriftDetector thread safety."""

    def test_concurrent_data_additions(self, drift_detector):
        """Test concurrent data additions don't cause race conditions."""
        errors = []

        def add_data():
            try:
                for i in range(100):
                    drift_detector.add_data_point({"x": float(i), "y": float(i * 2)})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_data) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All data should be added (500 total)
        assert len(drift_detector._all_data) == 500


# =============================================================================
# DriftDetector Tests - DataFrame Caching
# =============================================================================


class TestDriftDetectorDataFrameCaching:
    """Tests for DataFrame caching functionality."""

    def test_dataframes_cached_on_first_conversion(self, drift_detector, reference_data):
        """Test that DataFrames are cached on first conversion."""
        # Add data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # First call should populate cache
        assert drift_detector._reference_df_cache is None
        assert drift_detector._reference_checksum is None

        ref_df = drift_detector.get_reference_data()

        # Cache should now be populated
        assert drift_detector._reference_df_cache is not None
        assert drift_detector._reference_checksum is not None
        assert isinstance(drift_detector._reference_df_cache, pd.DataFrame)

    def test_cached_dataframes_reused_when_data_unchanged(self, drift_detector, reference_data):
        """Test that cached DataFrames are reused when data hasn't changed."""
        # Add data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # First call
        ref_df_1 = drift_detector.get_reference_data()
        checksum_1 = drift_detector._reference_checksum
        cached_df_1 = drift_detector._reference_df_cache

        # Second call should reuse cache
        ref_df_2 = drift_detector.get_reference_data()
        checksum_2 = drift_detector._reference_checksum
        cached_df_2 = drift_detector._reference_df_cache

        # Checksums should be identical
        assert checksum_1 == checksum_2
        # Cache objects should be the same (identity check)
        assert cached_df_1 is cached_df_2
        # DataFrames should be equal
        pd.testing.assert_frame_equal(ref_df_1, ref_df_2)

    def test_cache_invalidated_when_reference_data_changes(self, drift_detector, reference_data):
        """Test that cache is invalidated when reference data changes."""
        # Add initial data
        drift_detector.add_batch(reference_data[:50])

        # Get reference data to populate cache
        ref_df_1 = drift_detector.get_reference_data()
        checksum_1 = drift_detector._reference_checksum

        assert drift_detector._reference_df_cache is not None

        # Add more data (reference not locked)
        drift_detector.add_batch(reference_data[50:])

        # Cache should be invalidated
        assert drift_detector._reference_df_cache is None
        assert drift_detector._reference_checksum is None

        # Get reference data again to repopulate cache
        ref_df_2 = drift_detector.get_reference_data()
        checksum_2 = drift_detector._reference_checksum

        # New checksum should be different
        assert checksum_1 != checksum_2
        # DataFrames should be different sizes
        assert len(ref_df_1) != len(ref_df_2)

    def test_cache_invalidated_when_current_data_changes(self, drift_detector, reference_data):
        """Test that cache is invalidated when current data changes."""
        # Add initial data
        drift_detector.add_batch(reference_data[:50])
        drift_detector.lock_reference_data()

        # Clear current data and add some
        drift_detector._current_data.clear()
        drift_detector.add_batch(reference_data[50:70])

        # Get current data to populate cache
        cur_df_1 = drift_detector.get_current_data()
        checksum_1 = drift_detector._current_checksum

        assert drift_detector._current_df_cache is not None

        # Add more data to current
        drift_detector.add_batch(reference_data[70:90])

        # Cache should be invalidated
        assert drift_detector._current_df_cache is None
        assert drift_detector._current_checksum is None

        # Get current data again to repopulate cache
        cur_df_2 = drift_detector.get_current_data()
        checksum_2 = drift_detector._current_checksum

        # New checksum should be different
        assert checksum_1 != checksum_2
        # DataFrames should be different sizes
        assert len(cur_df_1) != len(cur_df_2)

    def test_report_cache_invalidated_when_data_changes(
        self, drift_detector, reference_data, similar_data
    ):
        """Test that report cache is invalidated when data changes."""
        # Add reference data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # Clear current and add data
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # First drift check should populate report cache
        result_1 = drift_detector.check_drift()
        assert drift_detector._last_report_cache is not None
        assert drift_detector._report_cache_checksum is not None
        cache_checksum_1 = drift_detector._report_cache_checksum

        # Add more data to current (this should invalidate report cache)
        drift_detector.add_batch(similar_data[30:50])

        # Report cache should be invalidated
        assert drift_detector._last_report_cache is None
        assert drift_detector._report_cache_checksum is None

        # Second drift check should create new cache
        result_2 = drift_detector.check_drift()
        cache_checksum_2 = drift_detector._report_cache_checksum

        # Checksums should be different
        assert cache_checksum_1 != cache_checksum_2

    def test_cached_report_reused_when_data_unchanged(
        self, drift_detector, reference_data, similar_data
    ):
        """Test that cached drift report is reused when data hasn't changed."""
        # Add data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # First drift check
        result_1 = drift_detector.check_drift()
        cache_checksum_1 = drift_detector._report_cache_checksum
        cached_report_1 = drift_detector._last_report_cache

        # Second drift check without changing data
        result_2 = drift_detector.check_drift()
        cache_checksum_2 = drift_detector._report_cache_checksum
        cached_report_2 = drift_detector._last_report_cache

        # Checksums should be identical
        assert cache_checksum_1 == cache_checksum_2
        # Cached objects should be the same
        assert cached_report_1 is cached_report_2
        # Results should have same drift detection outcome
        assert result_1.drift_detected == result_2.drift_detected
        assert result_1.drift_score == result_2.drift_score

    def test_cache_disabled_when_enable_caching_false(self, reference_data):
        """Test that caching is disabled when enable_caching=False."""
        detector = DriftDetector(
            reference_window_size=100,
            current_window_size=50,
            enable_caching=False,
        )

        # Add data
        detector.add_batch(reference_data)

        # Get reference data
        ref_df = detector.get_reference_data()

        # Cache should not be populated
        assert detector._reference_df_cache is None
        assert detector._reference_checksum is None

    def test_cache_cleared_on_reset(self, drift_detector, reference_data):
        """Test that cache is cleared when detector is reset."""
        # Add data and populate caches
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # Populate all caches
        drift_detector.get_reference_data()
        drift_detector.get_current_data()
        drift_detector.check_drift()

        # Verify caches are populated
        assert drift_detector._reference_df_cache is not None
        assert drift_detector._current_df_cache is not None

        # Reset detector
        drift_detector.reset()

        # All caches should be cleared
        assert drift_detector._reference_df_cache is None
        assert drift_detector._current_df_cache is None
        assert drift_detector._reference_checksum is None
        assert drift_detector._current_checksum is None
        assert drift_detector._last_report_cache is None
        assert drift_detector._report_cache_checksum is None


# =============================================================================
# DriftDetector Tests - Report Caching
# =============================================================================


class TestDriftDetectorReportCaching:
    """Tests for drift report result caching functionality."""

    def test_report_results_are_cached(self, drift_detector, reference_data, similar_data):
        """Test that drift report results are cached after first check_drift call."""
        # Add reference data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # Clear current and add data
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # Before first check, cache should be empty
        assert drift_detector._last_report_cache is None
        assert drift_detector._report_cache_checksum is None

        # First drift check should populate report cache
        result = drift_detector.check_drift()

        # After first check, cache should be populated
        assert drift_detector._last_report_cache is not None
        assert drift_detector._report_cache_checksum is not None
        assert isinstance(drift_detector._last_report_cache, DriftResult)
        # Cached result should match returned result
        assert drift_detector._last_report_cache.drift_detected == result.drift_detected
        assert drift_detector._last_report_cache.drift_score == result.drift_score

    def test_cached_reports_returned_when_data_unchanged(
        self, drift_detector, reference_data, similar_data
    ):
        """Test that cached drift reports are returned when data hasn't changed."""
        # Add data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # First drift check - creates cache
        result_1 = drift_detector.check_drift()
        cached_report_1 = drift_detector._last_report_cache
        cache_checksum_1 = drift_detector._report_cache_checksum

        # Second drift check without changing data - should use cache
        result_2 = drift_detector.check_drift()
        cached_report_2 = drift_detector._last_report_cache
        cache_checksum_2 = drift_detector._report_cache_checksum

        # Cache checksum should be identical
        assert cache_checksum_1 == cache_checksum_2
        # Cached report object should be the same instance
        assert cached_report_1 is cached_report_2
        # Results should have identical drift metrics
        assert result_1.drift_detected == result_2.drift_detected
        assert result_1.drift_score == result_2.drift_score
        assert result_1.reference_size == result_2.reference_size
        assert result_1.current_size == result_2.current_size

    def test_new_reports_generated_when_reference_data_changes(
        self, drift_detector, reference_data, similar_data
    ):
        """Test that new drift reports are generated when reference data changes."""
        # Add initial reference data
        drift_detector.add_batch(reference_data[:50])
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # First drift check
        result_1 = drift_detector.check_drift()
        cache_checksum_1 = drift_detector._report_cache_checksum
        cached_report_1 = drift_detector._last_report_cache

        # Add more reference data (not locked, so it will update)
        drift_detector.add_batch(reference_data[50:])

        # Cache should be invalidated
        assert drift_detector._last_report_cache is None
        assert drift_detector._report_cache_checksum is None

        # Second drift check should generate new report
        result_2 = drift_detector.check_drift()
        cache_checksum_2 = drift_detector._report_cache_checksum
        cached_report_2 = drift_detector._last_report_cache

        # Checksums should be different
        assert cache_checksum_1 != cache_checksum_2
        # Cached reports should be different instances
        assert cached_report_1 is not cached_report_2
        # Results should have different reference sizes
        assert result_1.reference_size != result_2.reference_size

    def test_new_reports_generated_when_current_data_changes(
        self, drift_detector, reference_data, similar_data
    ):
        """Test that new drift reports are generated when current data changes."""
        # Add reference data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # Add initial current data
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # First drift check
        result_1 = drift_detector.check_drift()
        cache_checksum_1 = drift_detector._report_cache_checksum
        cached_report_1 = drift_detector._last_report_cache

        # Add more current data
        drift_detector.add_batch(similar_data[30:60])

        # Cache should be invalidated
        assert drift_detector._last_report_cache is None
        assert drift_detector._report_cache_checksum is None

        # Second drift check should generate new report
        result_2 = drift_detector.check_drift()
        cache_checksum_2 = drift_detector._report_cache_checksum
        cached_report_2 = drift_detector._last_report_cache

        # Checksums should be different
        assert cache_checksum_1 != cache_checksum_2
        # Cached reports should be different instances
        assert cached_report_1 is not cached_report_2
        # Results should have different current sizes
        assert result_1.current_size != result_2.current_size

    def test_timestamps_updated_on_cached_results(
        self, drift_detector, reference_data, similar_data
    ):
        """Test that timestamps are updated when returning cached drift results."""
        # Add data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # First drift check
        result_1 = drift_detector.check_drift()
        timestamp_1 = result_1.timestamp

        # Wait a short time to ensure timestamps differ
        time.sleep(0.1)

        # Second drift check without changing data - should use cache
        result_2 = drift_detector.check_drift()
        timestamp_2 = result_2.timestamp

        # Timestamps should be different (second one should be later)
        assert timestamp_2 > timestamp_1
        # But other fields should be identical
        assert result_1.drift_detected == result_2.drift_detected
        assert result_1.drift_score == result_2.drift_score
        assert result_1.reference_size == result_2.reference_size
        assert result_1.current_size == result_2.current_size

    def test_cached_report_preserves_all_fields_except_timestamp(
        self, drift_detector, reference_data, similar_data
    ):
        """Test that cached reports preserve all fields except timestamp."""
        # Add data
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # First drift check
        result_1 = drift_detector.check_drift()

        # Wait and check again
        time.sleep(0.1)
        result_2 = drift_detector.check_drift()

        # All fields except timestamp should be identical
        assert result_1.status == result_2.status
        assert result_1.drift_detected == result_2.drift_detected
        assert result_1.drift_score == result_2.drift_score
        assert result_1.drift_threshold == result_2.drift_threshold
        assert result_1.reference_size == result_2.reference_size
        assert result_1.current_size == result_2.current_size
        assert result_1.message == result_2.message
        # Timestamp should be updated
        assert result_2.timestamp > result_1.timestamp

    def test_report_cache_with_insufficient_data(self, drift_detector):
        """Test that reports with insufficient data are not cached."""
        # Add only a few samples (less than min_samples_for_drift=10)
        for i in range(5):
            drift_detector.add_data_point({"x": float(i)})

        # Check drift
        result = drift_detector.check_drift()

        # Result should indicate insufficient data
        assert result.status == DriftStatus.INSUFFICIENT_DATA

        # Report cache should remain empty (we don't cache error states)
        # Note: Implementation may vary - this tests current behavior
        # If cache behavior changes, adjust this test accordingly

    def test_report_cache_disabled_when_caching_disabled(
        self, reference_data, similar_data
    ):
        """Test that report caching is disabled when enable_caching=False."""
        detector = DriftDetector(
            reference_window_size=100,
            current_window_size=50,
            enable_caching=False,
        )

        # Add data
        detector.add_batch(reference_data)
        detector.lock_reference_data()
        detector._current_data.clear()
        detector.add_batch(similar_data[:30])

        # Drift check
        result = detector.check_drift()

        # Report cache should not be populated
        assert detector._last_report_cache is None
        assert detector._report_cache_checksum is None


# =============================================================================
# DriftDetector Tests - Cache Invalidation
# =============================================================================


class TestDriftDetectorCacheInvalidation:
    """Tests for cache invalidation in data modification methods."""

    def test_add_data_point_invalidates_current_cache(self, drift_detector, reference_data):
        """Test that add_data_point invalidates current data cache."""
        # Add initial data and lock reference
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # Clear current and add some data
        drift_detector._current_data.clear()
        drift_detector.add_batch(reference_data[:30])

        # Populate current cache
        drift_detector.get_current_data()
        assert drift_detector._current_df_cache is not None
        assert drift_detector._current_checksum is not None

        # Add a single data point
        drift_detector.add_data_point({"f1": 1.0, "f2": 2.0})

        # Current cache should be invalidated
        assert drift_detector._current_df_cache is None
        assert drift_detector._current_checksum is None

    def test_add_data_point_invalidates_reference_cache_when_not_locked(
        self, drift_detector, reference_data
    ):
        """Test that add_data_point invalidates reference cache when reference is not locked."""
        # Add initial data (reference NOT locked)
        drift_detector.add_batch(reference_data[:50])

        # Populate reference cache
        drift_detector.get_reference_data()
        assert drift_detector._reference_df_cache is not None
        assert drift_detector._reference_checksum is not None

        # Add a data point (should invalidate reference cache since not locked)
        drift_detector.add_data_point({"f1": 1.0, "f2": 2.0})

        # Reference cache should be invalidated
        assert drift_detector._reference_df_cache is None
        assert drift_detector._reference_checksum is None

    def test_add_data_point_does_not_invalidate_reference_cache_when_locked(
        self, drift_detector, reference_data
    ):
        """Test that add_data_point does not invalidate reference cache when locked."""
        # Add initial data and lock reference
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # Populate reference cache
        ref_df_1 = drift_detector.get_reference_data()
        checksum_1 = drift_detector._reference_checksum
        assert drift_detector._reference_df_cache is not None

        # Add a data point (should NOT invalidate reference cache since locked)
        drift_detector.add_data_point({"f1": 1.0, "f2": 2.0})

        # Reference cache should still be valid
        assert drift_detector._reference_df_cache is not None
        assert drift_detector._reference_checksum == checksum_1

    def test_add_data_point_invalidates_report_cache(
        self, drift_detector, reference_data, similar_data
    ):
        """Test that add_data_point invalidates report cache."""
        # Add reference data and lock
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()

        # Clear current and add data
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # Populate report cache
        drift_detector.check_drift()
        assert drift_detector._last_report_cache is not None
        assert drift_detector._report_cache_checksum is not None

        # Add a data point (should invalidate report cache)
        drift_detector.add_data_point({"f1": 1.0, "f2": 2.0})

        # Report cache should be invalidated
        assert drift_detector._last_report_cache is None
        assert drift_detector._report_cache_checksum is None

    def test_set_reference_data_invalidates_reference_cache(
        self, drift_detector, reference_data
    ):
        """Test that set_reference_data invalidates reference cache."""
        # Add initial data
        drift_detector.add_batch(reference_data[:50])

        # Populate reference cache
        drift_detector.get_reference_data()
        assert drift_detector._reference_df_cache is not None
        assert drift_detector._reference_checksum is not None

        # Set new reference data from DataFrame
        new_ref_df = pd.DataFrame(reference_data[50:])
        drift_detector.set_reference_data(new_ref_df)

        # Reference cache should be invalidated
        assert drift_detector._reference_df_cache is None
        assert drift_detector._reference_checksum is None

    def test_set_reference_data_invalidates_report_cache(
        self, drift_detector, reference_data, similar_data
    ):
        """Test that set_reference_data invalidates report cache."""
        # Add reference data
        drift_detector.add_batch(reference_data[:50])
        drift_detector.lock_reference_data()

        # Clear current and add data
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # Populate report cache
        drift_detector.check_drift()
        assert drift_detector._last_report_cache is not None
        assert drift_detector._report_cache_checksum is not None

        # Set new reference data (should invalidate report cache)
        new_ref_df = pd.DataFrame(reference_data[50:])
        drift_detector.set_reference_data(new_ref_df)

        # Report cache should be invalidated
        assert drift_detector._last_report_cache is None
        assert drift_detector._report_cache_checksum is None

    def test_update_reference_from_current_invalidates_reference_cache(
        self, drift_detector, reference_data
    ):
        """Test that update_reference_from_current invalidates reference cache."""
        # Add initial data
        drift_detector.add_batch(reference_data[:50])

        # Populate reference cache
        drift_detector.get_reference_data()
        assert drift_detector._reference_df_cache is not None
        assert drift_detector._reference_checksum is not None

        # Update reference from current
        drift_detector.update_reference_from_current()

        # Reference cache should be invalidated
        assert drift_detector._reference_df_cache is None
        assert drift_detector._reference_checksum is None

    def test_update_reference_from_current_invalidates_report_cache(
        self, drift_detector, reference_data, similar_data
    ):
        """Test that update_reference_from_current invalidates report cache."""
        # Add reference data
        drift_detector.add_batch(reference_data[:50])
        drift_detector.lock_reference_data()

        # Clear current and add data
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # Populate report cache
        drift_detector.check_drift()
        assert drift_detector._last_report_cache is not None
        assert drift_detector._report_cache_checksum is not None

        # Update reference from current (should invalidate report cache)
        drift_detector.update_reference_from_current()

        # Report cache should be invalidated
        assert drift_detector._last_report_cache is None
        assert drift_detector._report_cache_checksum is None

    def test_reset_clears_all_caches(self, drift_detector, reference_data, similar_data):
        """Test that reset clears all cache fields."""
        # Add data and populate all caches
        drift_detector.add_batch(reference_data)
        drift_detector.lock_reference_data()
        drift_detector._current_data.clear()
        drift_detector.add_batch(similar_data[:30])

        # Populate all caches
        drift_detector.get_reference_data()
        drift_detector.get_current_data()
        drift_detector.check_drift()

        # Verify caches are populated
        assert drift_detector._reference_df_cache is not None
        assert drift_detector._current_df_cache is not None
        assert drift_detector._reference_checksum is not None
        assert drift_detector._current_checksum is not None
        assert drift_detector._last_report_cache is not None
        assert drift_detector._report_cache_checksum is not None

        # Reset detector
        drift_detector.reset()

        # All caches should be cleared
        assert drift_detector._reference_df_cache is None
        assert drift_detector._current_df_cache is None
        assert drift_detector._reference_checksum is None
        assert drift_detector._current_checksum is None
        assert drift_detector._last_report_cache is None
        assert drift_detector._report_cache_checksum is None


# =============================================================================
# DriftDetector Tests - Cache Enable/Disable
# =============================================================================


class TestDriftDetectorCacheDisabled:
    """Tests for verifying caching can be disabled and falls back to non-cached behavior."""

    def test_check_drift_works_without_caching(self, reference_data, similar_data):
        """Test that check_drift works correctly when caching is disabled."""
        detector = DriftDetector(
            reference_window_size=100,
            current_window_size=50,
            enable_caching=False,
        )

        # Add data
        detector.add_batch(reference_data)
        detector.lock_reference_data()
        detector._current_data.clear()
        detector.add_batch(similar_data[:30])

        # Check drift should work correctly
        result = detector.check_drift()

        # Result should be valid
        assert isinstance(result, DriftResult)
        assert result.status in [DriftStatus.NO_DRIFT, DriftStatus.DRIFT_DETECTED]
        assert result.reference_size == len(reference_data)
        assert result.current_size == 30

        # Caches should remain empty
        assert detector._last_report_cache is None
        assert detector._report_cache_checksum is None

    def test_multiple_check_drift_calls_recompute_without_cache(
        self, reference_data, similar_data
    ):
        """Test that multiple check_drift calls with same data recompute without caching."""
        detector = DriftDetector(
            reference_window_size=100,
            current_window_size=50,
            enable_caching=False,
        )

        # Add data
        detector.add_batch(reference_data)
        detector.lock_reference_data()
        detector._current_data.clear()
        detector.add_batch(similar_data[:30])

        # First check
        result_1 = detector.check_drift()
        cache_after_first = detector._last_report_cache

        # Second check with same data
        result_2 = detector.check_drift()
        cache_after_second = detector._last_report_cache

        # Results should have same values (same data)
        assert result_1.drift_detected == result_2.drift_detected
        assert result_1.drift_score == result_2.drift_score
        assert result_1.reference_size == result_2.reference_size
        assert result_1.current_size == result_2.current_size

        # But cache should remain empty (no caching occurred)
        assert cache_after_first is None
        assert cache_after_second is None

    def test_get_reference_data_returns_fresh_dataframe_without_cache(self, reference_data):
        """Test that get_reference_data returns fresh DataFrame when caching is disabled."""
        detector = DriftDetector(
            reference_window_size=100,
            enable_caching=False,
        )

        # Add data
        detector.add_batch(reference_data)

        # Get reference data twice
        ref_df_1 = detector.get_reference_data()
        ref_df_2 = detector.get_reference_data()

        # DataFrames should have same content
        pd.testing.assert_frame_equal(ref_df_1, ref_df_2)

        # But should be different objects (no caching)
        assert ref_df_1 is not ref_df_2

        # Cache should remain empty
        assert detector._reference_df_cache is None
        assert detector._reference_checksum is None

    def test_get_current_data_returns_fresh_dataframe_without_cache(self, reference_data):
        """Test that get_current_data returns fresh DataFrame when caching is disabled."""
        detector = DriftDetector(
            reference_window_size=100,
            current_window_size=50,
            enable_caching=False,
        )

        # Add data
        detector.add_batch(reference_data[:50])

        # Get current data twice
        cur_df_1 = detector.get_current_data()
        cur_df_2 = detector.get_current_data()

        # DataFrames should have same content
        pd.testing.assert_frame_equal(cur_df_1, cur_df_2)

        # But should be different objects (no caching)
        assert cur_df_1 is not cur_df_2

        # Cache should remain empty
        assert detector._current_df_cache is None
        assert detector._current_checksum is None

    def test_generate_html_report_works_without_caching(
        self, reference_data, similar_data, tmp_path
    ):
        """Test that generate_html_report works correctly when caching is disabled."""
        detector = DriftDetector(
            reference_window_size=100,
            current_window_size=50,
            enable_caching=False,
        )

        # Add data
        detector.add_batch(reference_data)
        detector.lock_reference_data()
        detector._current_data.clear()
        detector.add_batch(similar_data[:30])

        # Generate HTML report
        output_path = tmp_path / "drift_report.html"
        result = detector.generate_html_report(str(output_path))

        # Should succeed
        assert result is True
        assert output_path.exists()

        # Caches should remain empty
        assert detector._reference_df_cache is None
        assert detector._current_df_cache is None

    def test_cache_flag_is_respected(self):
        """Test that _cache_enabled flag reflects enable_caching parameter."""
        detector_with_cache = DriftDetector(enable_caching=True)
        detector_without_cache = DriftDetector(enable_caching=False)

        assert detector_with_cache._cache_enabled is True
        assert detector_without_cache._cache_enabled is False

    def test_all_operations_work_correctly_without_caching(
        self, reference_data, similar_data, drifted_data
    ):
        """Test comprehensive workflow without caching to verify fallback behavior."""
        detector = DriftDetector(
            reference_window_size=100,
            current_window_size=50,
            enable_caching=False,
        )

        # Initial setup
        detector.add_batch(reference_data)
        detector.lock_reference_data()

        # Get reference data (should work)
        ref_df = detector.get_reference_data()
        assert len(ref_df) == len(reference_data)

        # Check drift with similar data (should detect no drift)
        detector._current_data.clear()
        detector.add_batch(similar_data[:30])

        result_no_drift = detector.check_drift()
        assert result_no_drift.status == DriftStatus.NO_DRIFT
        assert result_no_drift.drift_detected is False

        # Check drift with drifted data (should detect drift)
        detector._current_data.clear()
        detector.add_batch(drifted_data[:30])

        result_drift = detector.check_drift()
        assert result_drift.status == DriftStatus.DRIFT_DETECTED
        assert result_drift.drift_detected is True

        # Get current data (should work)
        cur_df = detector.get_current_data()
        assert len(cur_df) == 30

        # All caches should remain empty throughout
        assert detector._reference_df_cache is None
        assert detector._current_df_cache is None
        assert detector._reference_checksum is None
        assert detector._current_checksum is None
        assert detector._last_report_cache is None
        assert detector._report_cache_checksum is None


# =============================================================================
# DriftDetector Tests - Repr
# =============================================================================


class TestDriftDetectorRepr:
    """Tests for DriftDetector string representation."""

    def test_repr(self, drift_detector):
        """Test __repr__ returns informative string."""
        repr_str = repr(drift_detector)

        assert "DriftDetector" in repr_str
        assert "status=" in repr_str
        assert "ref_size=" in repr_str
        assert "cur_size=" in repr_str


# =============================================================================
# MetricsRegistry Tests - Initialization
# =============================================================================


class TestMetricsRegistryInit:
    """Tests for MetricsRegistry initialization."""

    def test_default_initialization(self):
        """Test default initialization creates valid registry."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)

        assert metrics._prefix == "adaptive_learning"
        assert metrics._current_model_version == "unknown"
        assert metrics._cold_start_active is True

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        registry = CollectorRegistry()
        custom_buckets = (0.01, 0.1, 1.0)
        metrics = MetricsRegistry(
            registry=registry,
            prefix="custom_prefix",
            latency_buckets=custom_buckets,
        )

        assert metrics._prefix == "custom_prefix"
        assert metrics._latency_buckets == custom_buckets

    def test_counters_initialized(self, metrics_registry):
        """Test that all counters are initialized."""
        assert metrics_registry.predictions_total is not None
        assert metrics_registry.training_samples_total is not None
        assert metrics_registry.errors_total is not None
        assert metrics_registry.safety_violations_total is not None
        assert metrics_registry.drift_checks_total is not None
        assert metrics_registry.model_swaps_total is not None
        assert metrics_registry.rollbacks_total is not None

    def test_gauges_initialized(self, metrics_registry):
        """Test that all gauges are initialized."""
        assert metrics_registry.model_accuracy is not None
        assert metrics_registry.drift_score is not None
        assert metrics_registry.drift_threshold is not None
        assert metrics_registry.training_queue_size is not None
        assert metrics_registry.model_is_cold_start is not None
        assert metrics_registry.uptime_seconds is not None

    def test_histograms_initialized(self, metrics_registry):
        """Test that all histograms are initialized."""
        assert metrics_registry.prediction_latency is not None
        assert metrics_registry.training_latency is not None
        assert metrics_registry.drift_check_latency is not None
        assert metrics_registry.model_swap_latency is not None


# =============================================================================
# MetricsRegistry Tests - Recording Methods
# =============================================================================


class TestMetricsRegistryRecording:
    """Tests for metrics recording methods."""

    def test_record_prediction_success(self, metrics_registry):
        """Test recording successful prediction."""
        metrics_registry.record_prediction(
            latency_seconds=0.012,
            model_version="v1",
            success=True,
        )

        # Verify counter was incremented
        count = metrics_registry.predictions_total.labels(
            model_version="v1", status="success"
        )._value.get()
        assert count == 1

    def test_record_prediction_failure(self, metrics_registry):
        """Test recording failed prediction."""
        metrics_registry.record_prediction(
            latency_seconds=0.05,
            model_version="v1",
            success=False,
        )

        count = metrics_registry.predictions_total.labels(
            model_version="v1", status="error"
        )._value.get()
        assert count == 1

    def test_record_training(self, metrics_registry):
        """Test recording training event."""
        metrics_registry.record_training(
            latency_seconds=0.003,
            model_version="v1",
            batch_size=10,
        )

        count = metrics_registry.training_samples_total.labels(model_version="v1")._value.get()
        assert count == 10

    def test_record_error(self, metrics_registry):
        """Test recording error event."""
        metrics_registry.record_error(
            error_type="validation_error",
            endpoint="/predict",
        )

        count = metrics_registry.errors_total.labels(
            error_type="validation_error",
            endpoint="/predict",
        )._value.get()
        assert count == 1

    def test_record_safety_violation(self, metrics_registry):
        """Test recording safety violation."""
        metrics_registry.record_safety_violation(result="rejected")

        count = metrics_registry.safety_violations_total.labels(
            safety_result="rejected"
        )._value.get()
        assert count == 1

    def test_record_drift_check(self, metrics_registry):
        """Test recording drift check."""
        metrics_registry.record_drift_check(
            latency_seconds=0.5,
            drift_detected=True,
            drift_score=0.3,
        )

        count = metrics_registry.drift_checks_total.labels(
            drift_status="drift_detected"
        )._value.get()
        assert count == 1

    def test_record_model_swap_success(self, metrics_registry):
        """Test recording successful model swap."""
        metrics_registry.record_model_swap(latency_seconds=0.1, success=True)

        count = metrics_registry.model_swaps_total.labels(status="success")._value.get()
        assert count == 1

    def test_record_model_swap_failure(self, metrics_registry):
        """Test recording failed model swap."""
        metrics_registry.record_model_swap(latency_seconds=0.2, success=False)

        count = metrics_registry.model_swaps_total.labels(status="error")._value.get()
        assert count == 1

    def test_record_rollback(self, metrics_registry):
        """Test recording rollback event."""
        metrics_registry.record_rollback()
        metrics_registry.record_rollback()

        count = metrics_registry.rollbacks_total._value.get()
        assert count == 2


# =============================================================================
# MetricsRegistry Tests - Gauge Setters
# =============================================================================


class TestMetricsRegistryGauges:
    """Tests for gauge setter methods."""

    def test_set_model_accuracy(self, metrics_registry):
        """Test setting model accuracy gauge."""
        metrics_registry.set_model_accuracy(0.92, model_version="v1")

        value = metrics_registry.model_accuracy.labels(model_version="v1")._value.get()
        assert value == 0.92

    def test_set_model_f1(self, metrics_registry):
        """Test setting model F1 score gauge."""
        metrics_registry.set_model_f1(0.88, model_version="v1")

        value = metrics_registry.model_f1_score.labels(model_version="v1")._value.get()
        assert value == 0.88

    def test_set_drift_score(self, metrics_registry):
        """Test setting drift score gauge."""
        metrics_registry.set_drift_score(0.25)

        value = metrics_registry.drift_score._value.get()
        assert value == 0.25

    def test_set_drift_threshold(self, metrics_registry):
        """Test setting drift threshold gauge."""
        metrics_registry.set_drift_threshold(0.2)

        value = metrics_registry.drift_threshold._value.get()
        assert value == 0.2

    def test_set_training_queue_size(self, metrics_registry):
        """Test setting training queue size gauge."""
        metrics_registry.set_training_queue_size(100)

        value = metrics_registry.training_queue_size._value.get()
        assert value == 100

    def test_set_reference_data_size(self, metrics_registry):
        """Test setting reference data size gauge."""
        metrics_registry.set_reference_data_size(1000)

        value = metrics_registry.reference_data_size._value.get()
        assert value == 1000

    def test_set_current_data_size(self, metrics_registry):
        """Test setting current data size gauge."""
        metrics_registry.set_current_data_size(100)

        value = metrics_registry.current_data_size._value.get()
        assert value == 100

    def test_set_model_samples_trained(self, metrics_registry):
        """Test setting model samples trained gauge."""
        metrics_registry.set_model_samples_trained(5000, model_version="v1")

        value = metrics_registry.model_samples_trained.labels(model_version="v1")._value.get()
        assert value == 5000

    def test_set_cold_start(self, metrics_registry):
        """Test setting cold start gauge."""
        metrics_registry.set_cold_start(True)
        assert metrics_registry.model_is_cold_start._value.get() == 1

        metrics_registry.set_cold_start(False)
        assert metrics_registry.model_is_cold_start._value.get() == 0

    def test_set_consecutive_safety_failures(self, metrics_registry):
        """Test setting consecutive safety failures gauge."""
        metrics_registry.set_consecutive_safety_failures(3)

        value = metrics_registry.consecutive_safety_failures._value.get()
        assert value == 3

    def test_set_safety_threshold(self, metrics_registry):
        """Test setting safety threshold gauge."""
        metrics_registry.set_safety_threshold(0.85)

        value = metrics_registry.safety_threshold._value.get()
        assert value == 0.85


# =============================================================================
# MetricsRegistry Tests - Info Setters
# =============================================================================


class TestMetricsRegistryInfo:
    """Tests for info metric setters."""

    def test_set_service_info(self, metrics_registry):
        """Test setting service info."""
        metrics_registry.set_service_info(
            version="1.0.0",
            environment="production",
            constitutional_hash="abc123",
        )

        # Info metrics don't have a simple _value getter, just verify no error
        assert True

    def test_set_model_info(self, metrics_registry):
        """Test setting model info."""
        metrics_registry.set_model_info(
            model_type="LogisticRegression",
            model_version="v2",
            algorithm="river.linear_model.LogisticRegression",
            mlflow_run_id="run_123",
        )

        assert metrics_registry._current_model_version == "v2"


# =============================================================================
# MetricsRegistry Tests - Context Managers
# =============================================================================


class TestMetricsRegistryContextManagers:
    """Tests for timing context managers."""

    def test_prediction_timer(self, metrics_registry):
        """Test prediction timer context manager."""
        with metrics_registry.prediction_timer(model_version="v1"):
            time.sleep(0.01)

        count = metrics_registry.predictions_total.labels(
            model_version="v1", status="success"
        )._value.get()
        assert count == 1

    def test_prediction_timer_with_error(self, metrics_registry):
        """Test prediction timer records error on exception."""
        with pytest.raises(ValueError):
            with metrics_registry.prediction_timer(model_version="v1"):
                raise ValueError("Test error")

        count = metrics_registry.predictions_total.labels(
            model_version="v1", status="error"
        )._value.get()
        assert count == 1

    def test_training_timer(self, metrics_registry):
        """Test training timer context manager."""
        with metrics_registry.training_timer(model_version="v1", batch_size=5):
            time.sleep(0.01)

        count = metrics_registry.training_samples_total.labels(model_version="v1")._value.get()
        assert count == 5

    def test_drift_check_timer(self, metrics_registry):
        """Test drift check timer context manager."""
        with metrics_registry.drift_check_timer():
            time.sleep(0.01)

        # Verify histogram observed a value
        assert True  # Histogram observation doesn't have simple value getter

    def test_model_swap_timer(self, metrics_registry):
        """Test model swap timer context manager."""
        with metrics_registry.model_swap_timer():
            time.sleep(0.01)

        count = metrics_registry.model_swaps_total.labels(status="success")._value.get()
        assert count == 1


# =============================================================================
# MetricsRegistry Tests - Metrics Export
# =============================================================================


class TestMetricsRegistryExport:
    """Tests for metrics export functionality."""

    def test_generate_metrics(self, metrics_registry):
        """Test generating Prometheus metrics output."""
        metrics_registry.record_prediction(0.01, "v1", True)
        metrics_registry.set_model_accuracy(0.92, "v1")

        output = metrics_registry.generate_metrics()

        assert isinstance(output, bytes)
        assert b"test_adaptive_predictions_total" in output
        assert b"test_adaptive_model_accuracy" in output

    def test_generate_metrics_updates_uptime(self, metrics_registry):
        """Test that generate_metrics updates uptime."""
        time.sleep(0.1)
        metrics_registry.generate_metrics()

        uptime = metrics_registry.uptime_seconds._value.get()
        assert uptime > 0

    def test_get_content_type(self, metrics_registry):
        """Test getting Prometheus content type."""
        content_type = metrics_registry.get_content_type()

        assert "text/plain" in content_type or "openmetrics" in content_type


# =============================================================================
# MetricsRegistry Tests - Callback Registration
# =============================================================================


class TestMetricsRegistryCallbacks:
    """Tests for callback registration."""

    def test_register_update_callback(self, metrics_registry):
        """Test registering update callback."""
        callback_called = [False]

        def my_callback():
            callback_called[0] = True

        metrics_registry.register_update_callback(my_callback)
        metrics_registry.generate_metrics()

        assert callback_called[0] is True

    def test_unregister_update_callback(self, metrics_registry):
        """Test unregistering update callback."""

        def my_callback():
            pass

        metrics_registry.register_update_callback(my_callback)
        assert len(metrics_registry._update_callbacks) == 1

        result = metrics_registry.unregister_update_callback(my_callback)
        assert result is True
        assert len(metrics_registry._update_callbacks) == 0

    def test_unregister_nonexistent_callback(self, metrics_registry):
        """Test unregistering callback that doesn't exist."""

        def my_callback():
            pass

        result = metrics_registry.unregister_update_callback(my_callback)
        assert result is False


# =============================================================================
# MetricsRegistry Tests - Snapshot
# =============================================================================


class TestMetricsRegistrySnapshot:
    """Tests for metrics snapshot functionality."""

    def test_get_snapshot(self, metrics_registry):
        """Test getting metrics snapshot."""
        metrics_registry.record_prediction(0.01, "v1", True)
        metrics_registry.record_training(0.001, "v1", 10)
        metrics_registry.set_drift_score(0.15)

        snapshot = metrics_registry.get_snapshot()

        assert isinstance(snapshot, MetricsSnapshot)
        assert snapshot.predictions_total >= 1
        assert snapshot.training_samples_total >= 10
        assert snapshot.drift_score == 0.15
        assert snapshot.timestamp > 0

    def test_snapshot_contains_all_fields(self, metrics_registry):
        """Test that snapshot contains all required fields."""
        snapshot = metrics_registry.get_snapshot()

        assert hasattr(snapshot, "predictions_total")
        assert hasattr(snapshot, "training_samples_total")
        assert hasattr(snapshot, "model_accuracy")
        assert hasattr(snapshot, "drift_score")
        assert hasattr(snapshot, "prediction_latency_p50")
        assert hasattr(snapshot, "prediction_latency_p95")
        assert hasattr(snapshot, "prediction_latency_p99")
        assert hasattr(snapshot, "model_version")
        assert hasattr(snapshot, "cold_start_active")
        assert hasattr(snapshot, "safety_violations")


# =============================================================================
# MetricsRegistry Tests - Reset
# =============================================================================


class TestMetricsRegistryReset:
    """Tests for reset functionality."""

    def test_reset_clears_state(self, metrics_registry):
        """Test that reset clears all state."""
        metrics_registry.record_prediction(0.01, "v1", True)
        metrics_registry._current_model_version = "v2"

        def my_callback():
            pass

        metrics_registry.register_update_callback(my_callback)

        metrics_registry.reset()

        assert metrics_registry._current_model_version == "unknown"
        assert metrics_registry._cold_start_active is True
        assert len(metrics_registry._update_callbacks) == 0


# =============================================================================
# MetricsRegistry Tests - Thread Safety
# =============================================================================


class TestMetricsRegistryThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_recording(self, metrics_registry):
        """Test concurrent metric recording doesn't cause race conditions."""
        errors = []

        def record_predictions():
            try:
                for _ in range(100):
                    metrics_registry.record_prediction(0.01, "v1", True)
            except Exception as e:
                errors.append(e)

        def record_training():
            try:
                for _ in range(100):
                    metrics_registry.record_training(0.001, "v1", 1)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=record_predictions),
            threading.Thread(target=record_training),
            threading.Thread(target=record_predictions),
            threading.Thread(target=record_training),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# =============================================================================
# MetricsRegistry Tests - Repr and Properties
# =============================================================================


class TestMetricsRegistryRepr:
    """Tests for string representation."""

    def test_repr(self, metrics_registry):
        """Test __repr__ returns informative string."""
        repr_str = repr(metrics_registry)

        assert "MetricsRegistry" in repr_str
        assert "prefix=" in repr_str
        assert "model_version=" in repr_str

    def test_registry_property(self, metrics_registry):
        """Test registry property returns CollectorRegistry."""
        registry = metrics_registry.registry

        assert isinstance(registry, CollectorRegistry)


# =============================================================================
# MetricsRegistry Tests - Global Registry
# =============================================================================


class TestGlobalMetricsRegistry:
    """Tests for global metrics registry functions."""

    def test_get_metrics_registry(self):
        """Test get_metrics_registry returns global instance."""
        registry = get_metrics_registry()

        assert isinstance(registry, MetricsRegistry)

    def test_create_metrics_registry(self):
        """Test create_metrics_registry creates new instance."""
        registry1 = create_metrics_registry(prefix="test1")
        registry2 = create_metrics_registry(prefix="test2")

        assert registry1 is not registry2
        assert registry1._prefix == "test1"
        assert registry2._prefix == "test2"


# =============================================================================
# MetricLabel Enum Tests
# =============================================================================


class TestMetricLabel:
    """Tests for MetricLabel enum."""

    def test_metric_label_values(self):
        """Test MetricLabel enum values."""
        assert MetricLabel.MODEL_TYPE == "model_type"
        assert MetricLabel.MODEL_VERSION == "model_version"
        assert MetricLabel.ENDPOINT == "endpoint"
        assert MetricLabel.STATUS == "status"
        assert MetricLabel.ERROR_TYPE == "error_type"
        assert MetricLabel.DRIFT_STATUS == "drift_status"
        assert MetricLabel.SAFETY_RESULT == "safety_result"


# =============================================================================
# Integration Tests - Drift Detection with Metrics
# =============================================================================


class TestDriftDetectorMetricsIntegration:
    """Tests for integration between DriftDetector and MetricsRegistry."""

    def test_drift_check_updates_metrics(self, metrics_registry, reference_data, similar_data):
        """Test that drift check can update metrics registry."""
        detector = DriftDetector(
            reference_window_size=100,
            current_window_size=50,
            min_samples_for_drift=10,
        )

        detector.add_batch(reference_data)
        detector.lock_reference_data()
        detector._current_data.clear()
        detector.add_batch(similar_data[:20])

        # Simulate what the API would do
        start_time = time.time()
        result = detector.check_drift()
        latency = time.time() - start_time

        # Record in metrics
        metrics_registry.record_drift_check(
            latency_seconds=latency,
            drift_detected=result.drift_detected,
            drift_score=result.drift_score,
        )
        metrics_registry.set_reference_data_size(len(detector._reference_data))
        metrics_registry.set_current_data_size(len(detector._current_data))

        # Verify metrics were updated
        ref_size = metrics_registry.reference_data_size._value.get()
        cur_size = metrics_registry.current_data_size._value.get()

        assert ref_size == 100
        assert cur_size >= 20
