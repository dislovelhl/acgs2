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
