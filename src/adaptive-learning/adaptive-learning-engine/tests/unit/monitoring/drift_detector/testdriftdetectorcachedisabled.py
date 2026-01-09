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

    def test_multiple_check_drift_calls_recompute_without_cache(self, reference_data, similar_data):
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
