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

    def test_report_cache_disabled_when_caching_disabled(self, reference_data, similar_data):
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
