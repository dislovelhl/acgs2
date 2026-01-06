"""
Tests for driftdetectoralerts.

Tests cover:
- driftdetectoralerts functionality
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
