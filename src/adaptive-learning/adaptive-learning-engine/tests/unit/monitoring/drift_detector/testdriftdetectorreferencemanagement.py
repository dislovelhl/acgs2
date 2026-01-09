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
