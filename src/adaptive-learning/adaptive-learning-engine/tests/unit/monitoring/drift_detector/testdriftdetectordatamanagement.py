"""
Tests for driftdetectordatamanagement.

Tests cover:
- driftdetectordatamanagement functionality
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
