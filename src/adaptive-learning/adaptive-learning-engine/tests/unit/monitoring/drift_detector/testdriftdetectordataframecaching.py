"""
Tests for driftdetectordataframecaching.

Tests cover:
- driftdetectordataframecaching functionality
- Error handling and edge cases
- Integration with related components
"""

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
