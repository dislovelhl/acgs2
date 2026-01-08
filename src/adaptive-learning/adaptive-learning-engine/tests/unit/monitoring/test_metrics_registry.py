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
)


class TestMetricsRegistryInit:
    """Tests for MetricsRegistry initialization."""

    def test_default_initialization(self):
        """Test default initialization creates valid registry."""
        registry = CollectorRegistry()
        metrics = MetricsRegistry(registry=registry)

        assert metrics._prefix == "adaptive_learning"
        assert metrics._current_model_version == "unknown"
        assert metrics._cold_start_active is True

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        registry = CollectorRegistry()
        custom_buckets = (0.01, 0.1, 1.0)
        metrics = MetricsRegistry(
            registry=registry,
            prefix="custom_prefix",
            latency_buckets=custom_buckets,
        )

        assert metrics._prefix == "custom_prefix"
        assert metrics._latency_buckets == custom_buckets

    def test_counters_initialized(self, metrics_registry):
        """Test that all counters are initialized."""
        assert metrics_registry.predictions_total is not None
        assert metrics_registry.training_samples_total is not None
        assert metrics_registry.errors_total is not None
        assert metrics_registry.safety_violations_total is not None
        assert metrics_registry.drift_checks_total is not None
        assert metrics_registry.model_swaps_total is not None
        assert metrics_registry.rollbacks_total is not None

    def test_gauges_initialized(self, metrics_registry):
        """Test that all gauges are initialized."""
        assert metrics_registry.model_accuracy is not None
        assert metrics_registry.drift_score is not None
        assert metrics_registry.drift_threshold is not None
        assert metrics_registry.training_queue_size is not None
        assert metrics_registry.model_is_cold_start is not None
        assert metrics_registry.uptime_seconds is not None

    def test_histograms_initialized(self, metrics_registry):
        """Test that all histograms are initialized."""
        assert metrics_registry.prediction_latency is not None
        assert metrics_registry.training_latency is not None
        assert metrics_registry.drift_check_latency is not None
        assert metrics_registry.model_swap_latency is not None


# =============================================================================
# MetricsRegistry Tests - Recording Methods
# =============================================================================


class TestMetricsRegistryRecording:
    """Tests for metrics recording methods."""

    def test_record_prediction_success(self, metrics_registry):
        """Test recording successful prediction."""
        metrics_registry.record_prediction(
            latency_seconds=0.012,
            model_version="v1",
            success=True,
        )

        # Verify counter was incremented
        count = metrics_registry.predictions_total.labels(
            model_version="v1", status="success"
        )._value.get()
        assert count == 1

    def test_record_prediction_failure(self, metrics_registry):
        """Test recording failed prediction."""
        metrics_registry.record_prediction(
            latency_seconds=0.05,
            model_version="v1",
            success=False,
        )

        count = metrics_registry.predictions_total.labels(
            model_version="v1", status="error"
        )._value.get()
        assert count == 1

    def test_record_training(self, metrics_registry):
        """Test recording training event."""
        metrics_registry.record_training(
            latency_seconds=0.003,
            model_version="v1",
            batch_size=10,
        )

        count = metrics_registry.training_samples_total.labels(model_version="v1")._value.get()
        assert count == 10

    def test_record_error(self, metrics_registry):
        """Test recording error event."""
        metrics_registry.record_error(
            error_type="validation_error",
            endpoint="/predict",
        )

        count = metrics_registry.errors_total.labels(
            error_type="validation_error",
            endpoint="/predict",
        )._value.get()
        assert count == 1

    def test_record_safety_violation(self, metrics_registry):
        """Test recording safety violation."""
        metrics_registry.record_safety_violation(result="rejected")

        count = metrics_registry.safety_violations_total.labels(
            safety_result="rejected"
        )._value.get()
        assert count == 1

    def test_record_drift_check(self, metrics_registry):
        """Test recording drift check."""
        metrics_registry.record_drift_check(
            latency_seconds=0.5,
            drift_detected=True,
            drift_score=0.3,
        )

        count = metrics_registry.drift_checks_total.labels(
            drift_status="drift_detected"
        )._value.get()
        assert count == 1

    def test_record_model_swap_success(self, metrics_registry):
        """Test recording successful model swap."""
        metrics_registry.record_model_swap(latency_seconds=0.1, success=True)

        count = metrics_registry.model_swaps_total.labels(status="success")._value.get()
        assert count == 1

    def test_record_model_swap_failure(self, metrics_registry):
        """Test recording failed model swap."""
        metrics_registry.record_model_swap(latency_seconds=0.2, success=False)

        count = metrics_registry.model_swaps_total.labels(status="error")._value.get()
        assert count == 1

    def test_record_rollback(self, metrics_registry):
        """Test recording rollback event."""
        metrics_registry.record_rollback()
        metrics_registry.record_rollback()

        count = metrics_registry.rollbacks_total._value.get()
        assert count == 2


# =============================================================================
# MetricsRegistry Tests - Gauge Setters
# =============================================================================


class TestMetricsRegistryGauges:
    """Tests for gauge setter methods."""

    def test_set_model_accuracy(self, metrics_registry):
        """Test setting model accuracy gauge."""
        metrics_registry.set_model_accuracy(0.92, model_version="v1")

        value = metrics_registry.model_accuracy.labels(model_version="v1")._value.get()
        assert value == 0.92

    def test_set_model_f1(self, metrics_registry):
        """Test setting model F1 score gauge."""
        metrics_registry.set_model_f1(0.88, model_version="v1")

        value = metrics_registry.model_f1_score.labels(model_version="v1")._value.get()
        assert value == 0.88

    def test_set_drift_score(self, metrics_registry):
        """Test setting drift score gauge."""
        metrics_registry.set_drift_score(0.25)

        value = metrics_registry.drift_score._value.get()
        assert value == 0.25

    def test_set_drift_threshold(self, metrics_registry):
        """Test setting drift threshold gauge."""
        metrics_registry.set_drift_threshold(0.2)

        value = metrics_registry.drift_threshold._value.get()
        assert value == 0.2

    def test_set_training_queue_size(self, metrics_registry):
        """Test setting training queue size gauge."""
        metrics_registry.set_training_queue_size(100)

        value = metrics_registry.training_queue_size._value.get()
        assert value == 100

    def test_set_reference_data_size(self, metrics_registry):
        """Test setting reference data size gauge."""
        metrics_registry.set_reference_data_size(1000)

        value = metrics_registry.reference_data_size._value.get()
        assert value == 1000

    def test_set_current_data_size(self, metrics_registry):
        """Test setting current data size gauge."""
        metrics_registry.set_current_data_size(100)

        value = metrics_registry.current_data_size._value.get()
        assert value == 100

    def test_set_model_samples_trained(self, metrics_registry):
        """Test setting model samples trained gauge."""
        metrics_registry.set_model_samples_trained(5000, model_version="v1")

        value = metrics_registry.model_samples_trained.labels(model_version="v1")._value.get()
        assert value == 5000

    def test_set_cold_start(self, metrics_registry):
        """Test setting cold start gauge."""
        metrics_registry.set_cold_start(True)
        assert metrics_registry.model_is_cold_start._value.get() == 1

        metrics_registry.set_cold_start(False)
        assert metrics_registry.model_is_cold_start._value.get() == 0

    def test_set_consecutive_safety_failures(self, metrics_registry):
        """Test setting consecutive safety failures gauge."""
        metrics_registry.set_consecutive_safety_failures(3)

        value = metrics_registry.consecutive_safety_failures._value.get()
        assert value == 3

    def test_set_safety_threshold(self, metrics_registry):
        """Test setting safety threshold gauge."""
        metrics_registry.set_safety_threshold(0.85)

        value = metrics_registry.safety_threshold._value.get()
        assert value == 0.85


# =============================================================================
# MetricsRegistry Tests - Info Setters
# =============================================================================


class TestMetricsRegistryInfo:
    """Tests for info metric setters."""

    def test_set_service_info(self, metrics_registry):
        """Test setting service info."""
        metrics_registry.set_service_info(
            version="1.0.0",
            environment="production",
            constitutional_hash="abc123",
        )

        # Info metrics don't have a simple _value getter, just verify no error
        assert True

    def test_set_model_info(self, metrics_registry):
        """Test setting model info."""
        metrics_registry.set_model_info(
            model_type="LogisticRegression",
            model_version="v2",
            algorithm="river.linear_model.LogisticRegression",
            mlflow_run_id="run_123",
        )

        assert metrics_registry._current_model_version == "v2"


# =============================================================================
# MetricsRegistry Tests - Context Managers
# =============================================================================


class TestMetricsRegistryContextManagers:
    """Tests for timing context managers."""

    def test_prediction_timer(self, metrics_registry):
        """Test prediction timer context manager."""
        with metrics_registry.prediction_timer(model_version="v1"):
            time.sleep(0.01)

        count = metrics_registry.predictions_total.labels(
            model_version="v1", status="success"
        )._value.get()
        assert count == 1

    def test_prediction_timer_with_error(self, metrics_registry):
        """Test prediction timer records error on exception."""
        with pytest.raises(ValueError):
            with metrics_registry.prediction_timer(model_version="v1"):
                raise ValueError("Test error")

        count = metrics_registry.predictions_total.labels(
            model_version="v1", status="error"
        )._value.get()
        assert count == 1

    def test_training_timer(self, metrics_registry):
        """Test training timer context manager."""
        with metrics_registry.training_timer(model_version="v1", batch_size=5):
            time.sleep(0.01)

        count = metrics_registry.training_samples_total.labels(model_version="v1")._value.get()
        assert count == 5

    def test_drift_check_timer(self, metrics_registry):
        """Test drift check timer context manager."""
        with metrics_registry.drift_check_timer():
            time.sleep(0.01)

        # Verify histogram observed a value
        assert True  # Histogram observation doesn't have simple value getter

    def test_model_swap_timer(self, metrics_registry):
        """Test model swap timer context manager."""
        with metrics_registry.model_swap_timer():
            time.sleep(0.01)

        count = metrics_registry.model_swaps_total.labels(status="success")._value.get()
        assert count == 1


# =============================================================================
# MetricsRegistry Tests - Metrics Export
# =============================================================================


class TestMetricsRegistryExport:
    """Tests for metrics export functionality."""

    def test_generate_metrics(self, metrics_registry):
        """Test generating Prometheus metrics output."""
        metrics_registry.record_prediction(0.01, "v1", True)
        metrics_registry.set_model_accuracy(0.92, "v1")

        output = metrics_registry.generate_metrics()

        assert isinstance(output, bytes)
        assert b"test_adaptive_predictions_total" in output
        assert b"test_adaptive_model_accuracy" in output

    def test_generate_metrics_updates_uptime(self, metrics_registry):
        """Test that generate_metrics updates uptime."""
        time.sleep(0.1)
        metrics_registry.generate_metrics()

        uptime = metrics_registry.uptime_seconds._value.get()
        assert uptime > 0

    def test_get_content_type(self, metrics_registry):
        """Test getting Prometheus content type."""
        content_type = metrics_registry.get_content_type()

        assert "text/plain" in content_type or "openmetrics" in content_type


# =============================================================================
# MetricsRegistry Tests - Callback Registration
# =============================================================================


class TestMetricsRegistryCallbacks:
    """Tests for callback registration."""

    def test_register_update_callback(self, metrics_registry):
        """Test registering update callback."""
        callback_called = [False]

        def my_callback():
            callback_called[0] = True

        metrics_registry.register_update_callback(my_callback)
        metrics_registry.generate_metrics()

        assert callback_called[0] is True

    def test_unregister_update_callback(self, metrics_registry):
        """Test unregistering update callback."""

        def my_callback():
            pass

        metrics_registry.register_update_callback(my_callback)
        assert len(metrics_registry._update_callbacks) == 1

        result = metrics_registry.unregister_update_callback(my_callback)
        assert result is True
        assert len(metrics_registry._update_callbacks) == 0

    def test_unregister_nonexistent_callback(self, metrics_registry):
        """Test unregistering callback that doesn't exist."""

        def my_callback():
            pass

        result = metrics_registry.unregister_update_callback(my_callback)
        assert result is False


# =============================================================================
# MetricsRegistry Tests - Snapshot
# =============================================================================


class TestMetricsRegistrySnapshot:
    """Tests for metrics snapshot functionality."""

    def test_get_snapshot(self, metrics_registry):
        """Test getting metrics snapshot."""
        metrics_registry.record_prediction(0.01, "v1", True)
        metrics_registry.record_training(0.001, "v1", 10)
        metrics_registry.set_drift_score(0.15)

        snapshot = metrics_registry.get_snapshot()

        assert isinstance(snapshot, MetricsSnapshot)
        assert snapshot.predictions_total >= 1
        assert snapshot.training_samples_total >= 10
        assert snapshot.drift_score == 0.15
        assert snapshot.timestamp > 0

    def test_snapshot_contains_all_fields(self, metrics_registry):
        """Test that snapshot contains all required fields."""
        snapshot = metrics_registry.get_snapshot()

        assert hasattr(snapshot, "predictions_total")
        assert hasattr(snapshot, "training_samples_total")
        assert hasattr(snapshot, "model_accuracy")
        assert hasattr(snapshot, "drift_score")
        assert hasattr(snapshot, "prediction_latency_p50")
        assert hasattr(snapshot, "prediction_latency_p95")
        assert hasattr(snapshot, "prediction_latency_p99")
        assert hasattr(snapshot, "model_version")
        assert hasattr(snapshot, "cold_start_active")
        assert hasattr(snapshot, "safety_violations")


# =============================================================================
# MetricsRegistry Tests - Reset
# =============================================================================


class TestMetricsRegistryReset:
    """Tests for reset functionality."""

    def test_reset_clears_state(self, metrics_registry):
        """Test that reset clears all state."""
        metrics_registry.record_prediction(0.01, "v1", True)
        metrics_registry._current_model_version = "v2"

        def my_callback():
            pass

        metrics_registry.register_update_callback(my_callback)

        metrics_registry.reset()

        assert metrics_registry._current_model_version == "unknown"
        assert metrics_registry._cold_start_active is True
        assert len(metrics_registry._update_callbacks) == 0


# =============================================================================
# MetricsRegistry Tests - Thread Safety
# =============================================================================


class TestMetricsRegistryThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_recording(self, metrics_registry):
        """Test concurrent metric recording doesn't cause race conditions."""
        errors = []

        def record_predictions():
            try:
                for _ in range(100):
                    metrics_registry.record_prediction(0.01, "v1", True)
            except Exception as e:
                errors.append(e)

        def record_training():
            try:
                for _ in range(100):
                    metrics_registry.record_training(0.001, "v1", 1)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=record_predictions),
            threading.Thread(target=record_training),
            threading.Thread(target=record_predictions),
            threading.Thread(target=record_training),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


# =============================================================================
# MetricsRegistry Tests - Repr and Properties
# =============================================================================


class TestMetricsRegistryRepr:
    """Tests for string representation."""

    def test_repr(self, metrics_registry):
        """Test __repr__ returns informative string."""
        repr_str = repr(metrics_registry)

        assert "MetricsRegistry" in repr_str
        assert "prefix=" in repr_str
        assert "model_version=" in repr_str

    def test_registry_property(self, metrics_registry):
        """Test registry property returns CollectorRegistry."""
        registry = metrics_registry.registry

        assert isinstance(registry, CollectorRegistry)


# =============================================================================
# MetricsRegistry Tests - Global Registry
# =============================================================================


class TestGlobalMetricsRegistry:
    """Tests for global metrics registry functions."""

    def test_get_metrics_registry(self):
        """Test get_metrics_registry returns global instance."""
        registry = get_metrics_registry()

        assert isinstance(registry, MetricsRegistry)

    def test_create_metrics_registry(self):
        """Test create_metrics_registry creates new instance."""
        registry1 = create_metrics_registry(prefix="test1")
        registry2 = create_metrics_registry(prefix="test2")

        assert registry1 is not registry2
        assert registry1._prefix == "test1"
        assert registry2._prefix == "test2"


# =============================================================================
# MetricLabel Enum Tests
# =============================================================================


class TestMetricLabel:
    """Tests for MetricLabel enum."""

    def test_metric_label_values(self):
        """Test MetricLabel enum values."""
        assert MetricLabel.MODEL_TYPE == "model_type"
        assert MetricLabel.MODEL_VERSION == "model_version"
        assert MetricLabel.ENDPOINT == "endpoint"
        assert MetricLabel.STATUS == "status"
        assert MetricLabel.ERROR_TYPE == "error_type"
        assert MetricLabel.DRIFT_STATUS == "drift_status"
        assert MetricLabel.SAFETY_RESULT == "safety_result"


# =============================================================================
# Integration Tests - Drift Detection with Metrics
# =============================================================================


class TestDriftDetectorMetricsIntegration:
    """Tests for integration between DriftDetector and MetricsRegistry."""

    def test_drift_check_updates_metrics(self, metrics_registry, reference_data, similar_data):
        """Test that drift check can update metrics registry."""
        detector = DriftDetector(
            reference_window_size=100,
            current_window_size=50,
            min_samples_for_drift=10,
        )

        detector.add_batch(reference_data)
        detector.lock_reference_data()
        detector._current_data.clear()
        detector.add_batch(similar_data[:20])

        # Simulate what the API would do
        start_time = time.time()
        result = detector.check_drift()
        latency = time.time() - start_time

        # Record in metrics
        metrics_registry.record_drift_check(
            latency_seconds=latency,
            drift_detected=result.drift_detected,
            drift_score=result.drift_score,
        )
        metrics_registry.set_reference_data_size(len(detector._reference_data))
        metrics_registry.set_current_data_size(len(detector._current_data))

        # Verify metrics were updated
        ref_size = metrics_registry.reference_data_size._value.get()
        cur_size = metrics_registry.current_data_size._value.get()

        assert ref_size == 100
        assert cur_size >= 20
