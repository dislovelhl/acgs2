"""
Tests for driftdetectorstatusmetrics.

Tests cover:
- driftdetectorstatusmetrics functionality
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
