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

    def test_set_reference_data_invalidates_reference_cache(self, drift_detector, reference_data):
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
