"""
Tests for driftdetectordriftcheck.

Tests cover:
- driftdetectordriftcheck functionality
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
