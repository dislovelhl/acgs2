"""
Adaptive Learning Engine - Prometheus Metrics Collector
Constitutional Hash: cdd01ef066bc6cf2

Prometheus metrics export for model prediction, training, and monitoring.
Provides comprehensive instrumentation for Grafana dashboards and alerting.
"""

import logging
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Generator, List, Optional

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

logger = logging.getLogger(__name__)


class MetricLabel(str, Enum):
    """Standard metric labels for consistency."""

    MODEL_TYPE = "model_type"
    MODEL_VERSION = "model_version"
    ENDPOINT = "endpoint"
    STATUS = "status"
    ERROR_TYPE = "error_type"
    DRIFT_STATUS = "drift_status"
    SAFETY_RESULT = "safety_result"


@dataclass
class MetricsSnapshot:
    """Point-in-time snapshot of key metrics."""

    predictions_total: int
    training_samples_total: int
    model_accuracy: float
    drift_score: float
    prediction_latency_p50: float
    prediction_latency_p95: float
    prediction_latency_p99: float
    training_latency_p50: float
    training_latency_p95: float
    model_version: str
    cold_start_active: bool
    safety_violations: int
    timestamp: float = field(default_factory=time.time)


class MetricsRegistry:
    """Prometheus metrics registry for the Adaptive Learning Engine.

    Provides comprehensive metrics for monitoring model performance,
    training throughput, drift detection, and safety bounds.

    Metric types follow Prometheus best practices:
    - Counter: Monotonically increasing values (predictions, samples, errors)
    - Gauge: Values that go up/down (accuracy, drift score, model version)
    - Histogram: Latency measurements with configurable buckets
    - Info: Static metadata (model info, service info)

    Example usage:
        # Get the global metrics registry
        from src.monitoring.metrics import metrics_registry

        # Record a prediction
        metrics_registry.record_prediction(
            latency_seconds=0.012,
            model_version="v1",
            success=True,
        )

        # Record training
        metrics_registry.record_training(
            latency_seconds=0.003,
            model_version="v1",
        )

        # Update model accuracy
        metrics_registry.set_model_accuracy(0.92)

        # Get metrics for Prometheus scrape
        metrics_output = metrics_registry.generate_metrics()
    """

    # Default latency buckets (in seconds)
    # Fine-grained for low-latency ML serving: 1ms to 10s
    DEFAULT_LATENCY_BUCKETS = (
        0.001,  # 1ms
        0.005,  # 5ms
        0.01,  # 10ms
        0.025,  # 25ms
        0.05,  # 50ms - target P95
        0.1,  # 100ms
        0.25,  # 250ms
        0.5,  # 500ms
        1.0,  # 1s
        2.5,  # 2.5s
        5.0,  # 5s
        10.0,  # 10s
    )

    def __init__(
        self,
        registry: Optional[CollectorRegistry] = None,
        prefix: str = "adaptive_learning",
        latency_buckets: Optional[tuple] = None,
    ) -> None:
        """Initialize the metrics registry.

        Args:
            registry: Prometheus collector registry (creates new if not provided).
            prefix: Metric name prefix (default: adaptive_learning).
            latency_buckets: Custom latency histogram buckets.
        """
        self._lock = threading.RLock()
        self._registry = registry or CollectorRegistry()
        self._prefix = prefix
        self._latency_buckets = latency_buckets or self.DEFAULT_LATENCY_BUCKETS

        # Initialize all metrics
        self._init_counters()
        self._init_gauges()
        self._init_histograms()
        self._init_info_metrics()

        # Callback registry for custom metric updates
        self._update_callbacks: List[Callable[[], None]] = []

        # Internal state for snapshot
        self._current_model_version = "unknown"
        self._cold_start_active = True

        logger.info(
            "MetricsRegistry initialized",
            extra={"prefix": prefix, "registry": id(self._registry)},
        )

    def _init_counters(self) -> None:
        """Initialize counter metrics."""
        # Prediction counters
        self.predictions_total = Counter(
            f"{self._prefix}_predictions_total",
            "Total number of predictions made",
            labelnames=[MetricLabel.MODEL_VERSION, MetricLabel.STATUS],
            registry=self._registry,
        )

        # Training counters
        self.training_samples_total = Counter(
            f"{self._prefix}_training_samples_total",
            "Total number of training samples processed",
            labelnames=[MetricLabel.MODEL_VERSION],
            registry=self._registry,
        )

        # Error counters
        self.errors_total = Counter(
            f"{self._prefix}_errors_total",
            "Total number of errors by type",
            labelnames=[MetricLabel.ERROR_TYPE, MetricLabel.ENDPOINT],
            registry=self._registry,
        )

        # Safety counters
        self.safety_violations_total = Counter(
            f"{self._prefix}_safety_violations_total",
            "Total number of safety bound violations",
            labelnames=[MetricLabel.SAFETY_RESULT],
            registry=self._registry,
        )

        # Drift detection counters
        self.drift_checks_total = Counter(
            f"{self._prefix}_drift_checks_total",
            "Total number of drift detection checks",
            labelnames=[MetricLabel.DRIFT_STATUS],
            registry=self._registry,
        )

        # Model swap counters
        self.model_swaps_total = Counter(
            f"{self._prefix}_model_swaps_total",
            "Total number of model hot-swaps",
            labelnames=[MetricLabel.STATUS],
            registry=self._registry,
        )

        # Rollback counters
        self.rollbacks_total = Counter(
            f"{self._prefix}_rollbacks_total",
            "Total number of model rollbacks",
            registry=self._registry,
        )

    def _init_gauges(self) -> None:
        """Initialize gauge metrics."""
        # Model performance gauges
        self.model_accuracy = Gauge(
            f"{self._prefix}_model_accuracy",
            "Current model accuracy (0-1)",
            labelnames=[MetricLabel.MODEL_VERSION],
            registry=self._registry,
        )

        self.model_f1_score = Gauge(
            f"{self._prefix}_model_f1_score",
            "Current model F1 score (0-1)",
            labelnames=[MetricLabel.MODEL_VERSION],
            registry=self._registry,
        )

        # Drift gauges
        self.drift_score = Gauge(
            f"{self._prefix}_drift_score",
            "Current drift score (share of drifted columns)",
            registry=self._registry,
        )

        self.drift_threshold = Gauge(
            f"{self._prefix}_drift_threshold",
            "Configured drift detection threshold",
            registry=self._registry,
        )

        # Data gauges
        self.training_queue_size = Gauge(
            f"{self._prefix}_training_queue_size",
            "Number of samples waiting in training queue",
            registry=self._registry,
        )

        self.reference_data_size = Gauge(
            f"{self._prefix}_reference_data_size",
            "Number of samples in drift reference dataset",
            registry=self._registry,
        )

        self.current_data_size = Gauge(
            f"{self._prefix}_current_data_size",
            "Number of samples in drift current window",
            registry=self._registry,
        )

        # Model state gauges
        self.model_samples_trained = Gauge(
            f"{self._prefix}_model_samples_trained",
            "Total samples the current model has been trained on",
            labelnames=[MetricLabel.MODEL_VERSION],
            registry=self._registry,
        )

        self.model_is_cold_start = Gauge(
            f"{self._prefix}_model_is_cold_start",
            "Whether the model is in cold start mode (1=yes, 0=no)",
            registry=self._registry,
        )

        # Safety gauges
        self.consecutive_safety_failures = Gauge(
            f"{self._prefix}_consecutive_safety_failures",
            "Number of consecutive safety check failures",
            registry=self._registry,
        )

        self.safety_threshold = Gauge(
            f"{self._prefix}_safety_threshold",
            "Configured safety accuracy threshold",
            registry=self._registry,
        )

        # Uptime gauge
        self._start_time = time.time()
        self.uptime_seconds = Gauge(
            f"{self._prefix}_uptime_seconds",
            "Time since service started in seconds",
            registry=self._registry,
        )

    def _init_histograms(self) -> None:
        """Initialize histogram metrics."""
        # Prediction latency
        self.prediction_latency = Histogram(
            f"{self._prefix}_prediction_latency_seconds",
            "Prediction latency in seconds",
            labelnames=[MetricLabel.MODEL_VERSION],
            buckets=self._latency_buckets,
            registry=self._registry,
        )

        # Training latency
        self.training_latency = Histogram(
            f"{self._prefix}_training_latency_seconds",
            "Training (learn_one) latency in seconds",
            labelnames=[MetricLabel.MODEL_VERSION],
            buckets=self._latency_buckets,
            registry=self._registry,
        )

        # Drift check latency
        self.drift_check_latency = Histogram(
            f"{self._prefix}_drift_check_latency_seconds",
            "Drift detection check latency in seconds",
            buckets=self._latency_buckets,
            registry=self._registry,
        )

        # Model swap latency
        self.model_swap_latency = Histogram(
            f"{self._prefix}_model_swap_latency_seconds",
            "Model hot-swap latency in seconds",
            buckets=self._latency_buckets,
            registry=self._registry,
        )

    def _init_info_metrics(self) -> None:
        """Initialize info metrics for static metadata."""
        self.service_info = Info(
            f"{self._prefix}_service",
            "Service metadata",
            registry=self._registry,
        )

        self.model_info = Info(
            f"{self._prefix}_model",
            "Current model metadata",
            registry=self._registry,
        )

    # --- Recording Methods ---

    def record_prediction(
        self,
        latency_seconds: float,
        model_version: str = "unknown",
        success: bool = True,
    ) -> None:
        """Record a prediction event.

        Args:
            latency_seconds: Time taken for prediction.
            model_version: Version of the model used.
            success: Whether prediction succeeded.
        """
        with self._lock:
            status = "success" if success else "error"
            self.predictions_total.labels(
                model_version=model_version,
                status=status,
            ).inc()
            self.prediction_latency.labels(model_version=model_version).observe(latency_seconds)
            self._current_model_version = model_version

    def record_training(
        self,
        latency_seconds: float,
        model_version: str = "unknown",
        batch_size: int = 1,
    ) -> None:
        """Record a training event.

        Args:
            latency_seconds: Time taken for training.
            model_version: Version of the model trained.
            batch_size: Number of samples in this batch.
        """
        with self._lock:
            self.training_samples_total.labels(model_version=model_version).inc(batch_size)
            self.training_latency.labels(model_version=model_version).observe(latency_seconds)

    def record_error(self, error_type: str, endpoint: str = "unknown") -> None:
        """Record an error event.

        Args:
            error_type: Type/category of error.
            endpoint: API endpoint where error occurred.
        """
        with self._lock:
            self.errors_total.labels(error_type=error_type, endpoint=endpoint).inc()

    def record_safety_violation(self, result: str = "rejected") -> None:
        """Record a safety bound violation.

        Args:
            result: Type of safety violation (rejected, paused, etc).
        """
        with self._lock:
            self.safety_violations_total.labels(safety_result=result).inc()

    def record_drift_check(
        self,
        latency_seconds: float,
        drift_detected: bool,
        drift_score: float,
    ) -> None:
        """Record a drift detection check.

        Args:
            latency_seconds: Time taken for drift check.
            drift_detected: Whether drift was detected.
            drift_score: Drift score (share of drifted columns).
        """
        with self._lock:
            status = "drift_detected" if drift_detected else "no_drift"
            self.drift_checks_total.labels(drift_status=status).inc()
            self.drift_check_latency.observe(latency_seconds)
            self.drift_score.set(drift_score)

    def record_model_swap(
        self,
        latency_seconds: float,
        success: bool = True,
    ) -> None:
        """Record a model hot-swap event.

        Args:
            latency_seconds: Time taken for swap.
            success: Whether swap succeeded.
        """
        with self._lock:
            status = "success" if success else "error"
            self.model_swaps_total.labels(status=status).inc()
            self.model_swap_latency.observe(latency_seconds)

    def record_rollback(self) -> None:
        """Record a model rollback event."""
        with self._lock:
            self.rollbacks_total.inc()

    # --- Gauge Setters ---

    def set_model_accuracy(self, accuracy: float, model_version: str = "unknown") -> None:
        """Set the current model accuracy.

        Args:
            accuracy: Accuracy value (0-1).
            model_version: Model version for labeling.
        """
        with self._lock:
            self.model_accuracy.labels(model_version=model_version).set(accuracy)

    def set_model_f1(self, f1_score: float, model_version: str = "unknown") -> None:
        """Set the current model F1 score.

        Args:
            f1_score: F1 score value (0-1).
            model_version: Model version for labeling.
        """
        with self._lock:
            self.model_f1_score.labels(model_version=model_version).set(f1_score)

    def set_drift_score(self, score: float) -> None:
        """Set the current drift score.

        Args:
            score: Drift score (0-1, share of drifted columns).
        """
        with self._lock:
            self.drift_score.set(score)

    def set_drift_threshold(self, threshold: float) -> None:
        """Set the drift detection threshold.

        Args:
            threshold: Configured threshold value.
        """
        with self._lock:
            self.drift_threshold.set(threshold)

    def set_training_queue_size(self, size: int) -> None:
        """Set the training queue size.

        Args:
            size: Number of samples in queue.
        """
        with self._lock:
            self.training_queue_size.set(size)

    def set_reference_data_size(self, size: int) -> None:
        """Set the drift reference data size.

        Args:
            size: Number of samples in reference dataset.
        """
        with self._lock:
            self.reference_data_size.set(size)

    def set_current_data_size(self, size: int) -> None:
        """Set the drift current data size.

        Args:
            size: Number of samples in current window.
        """
        with self._lock:
            self.current_data_size.set(size)

    def set_model_samples_trained(self, count: int, model_version: str = "unknown") -> None:
        """Set the number of samples the model was trained on.

        Args:
            count: Total training samples.
            model_version: Model version for labeling.
        """
        with self._lock:
            self.model_samples_trained.labels(model_version=model_version).set(count)

    def set_cold_start(self, is_cold_start: bool) -> None:
        """Set the cold start status.

        Args:
            is_cold_start: Whether model is in cold start mode.
        """
        with self._lock:
            self._cold_start_active = is_cold_start
            self.model_is_cold_start.set(1 if is_cold_start else 0)

    def set_consecutive_safety_failures(self, count: int) -> None:
        """Set the consecutive safety failure count.

        Args:
            count: Number of consecutive failures.
        """
        with self._lock:
            self.consecutive_safety_failures.set(count)

    def set_safety_threshold(self, threshold: float) -> None:
        """Set the safety accuracy threshold.

        Args:
            threshold: Configured threshold value.
        """
        with self._lock:
            self.safety_threshold.set(threshold)

    # --- Info Setters ---

    def set_service_info(
        self,
        version: str = "unknown",
        environment: str = "development",
        constitutional_hash: str = "unknown",
    ) -> None:
        """Set service metadata.

        Args:
            version: Service version string.
            environment: Deployment environment.
            constitutional_hash: Constitutional hash for integrity.
        """
        self.service_info.info(
            {
                "version": version,
                "environment": environment,
                "constitutional_hash": constitutional_hash,
            }
        )

    def set_model_info(
        self,
        model_type: str = "unknown",
        model_version: str = "unknown",
        algorithm: str = "unknown",
        mlflow_run_id: Optional[str] = None,
    ) -> None:
        """Set current model metadata.

        Args:
            model_type: Type of model (e.g., LogisticRegression).
            model_version: Version string.
            algorithm: Algorithm name.
            mlflow_run_id: MLflow run ID if applicable.
        """
        info_dict = {
            "model_type": model_type,
            "model_version": model_version,
            "algorithm": algorithm,
        }
        if mlflow_run_id:
            info_dict["mlflow_run_id"] = mlflow_run_id

        self.model_info.info(info_dict)
        self._current_model_version = model_version

    # --- Context Managers ---

    @contextmanager
    def prediction_timer(self, model_version: str = "unknown") -> Generator[None, None, None]:
        """Context manager for timing predictions.

        Example:
            with metrics.prediction_timer(model_version="v1"):
                result = model.predict_one(features)
        """
        start = time.perf_counter()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            latency = time.perf_counter() - start
            self.record_prediction(
                latency_seconds=latency,
                model_version=model_version,
                success=success,
            )

    @contextmanager
    def training_timer(
        self, model_version: str = "unknown", batch_size: int = 1
    ) -> Generator[None, None, None]:
        """Context manager for timing training.

        Example:
            with metrics.training_timer(model_version="v1"):
                model.learn_one(features, label)
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            latency = time.perf_counter() - start
            self.record_training(
                latency_seconds=latency,
                model_version=model_version,
                batch_size=batch_size,
            )

    @contextmanager
    def drift_check_timer(self) -> Generator[None, None, None]:
        """Context manager for timing drift checks.

        Note: Drift score should be set separately after check completes.
        """
        start = time.perf_counter()
        try:
            yield
        finally:
            latency = time.perf_counter() - start
            self.drift_check_latency.observe(latency)

    @contextmanager
    def model_swap_timer(self) -> Generator[None, None, None]:
        """Context manager for timing model swaps."""
        start = time.perf_counter()
        success = True
        try:
            yield
        except Exception:
            success = False
            raise
        finally:
            latency = time.perf_counter() - start
            self.record_model_swap(latency_seconds=latency, success=success)

    # --- Metrics Export ---

    def generate_metrics(self) -> bytes:
        """Generate Prometheus metrics output.

        Returns:
            Prometheus exposition format bytes.
        """
        with self._lock:
            # Update uptime
            self.uptime_seconds.set(time.time() - self._start_time)

            # Run any registered update callbacks
            for callback in self._update_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.warning(f"Metrics update callback error: {e}")

        return generate_latest(self._registry)

    def get_content_type(self) -> str:
        """Get the Prometheus content type for HTTP responses.

        Returns:
            Content-Type header value.
        """
        return CONTENT_TYPE_LATEST

    # --- Callback Registration ---

    def register_update_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to update metrics before scrape.

        Callbacks are invoked when generate_metrics() is called.

        Args:
            callback: Function to call for metric updates.
        """
        with self._lock:
            self._update_callbacks.append(callback)

    def unregister_update_callback(self, callback: Callable[[], None]) -> bool:
        """Unregister a previously registered callback.

        Args:
            callback: Callback to remove.

        Returns:
            True if callback was found and removed.
        """
        with self._lock:
            try:
                self._update_callbacks.remove(callback)
                return True
            except ValueError:
                return False

    # --- Snapshot ---

    def get_snapshot(self) -> MetricsSnapshot:
        """Get a point-in-time snapshot of key metrics.

        Returns:
            MetricsSnapshot with current values.
        """
        with self._lock:
            # Get counter values (cumulative)
            pred_total = sum(
                self.predictions_total.labels(model_version=v, status=s)._value.get()
                for v in [self._current_model_version, "unknown"]
                for s in ["success", "error"]
            )
            train_total = sum(
                self.training_samples_total.labels(model_version=v)._value.get()
                for v in [self._current_model_version, "unknown"]
            )

            # Get safety violations
            safety_total = sum(
                self.safety_violations_total.labels(safety_result=r)._value.get()
                for r in ["rejected", "paused"]
            )

            # Note: Histogram percentiles require observation data which
            # isn't directly accessible. Return 0 as placeholder.
            # Real percentiles are computed by Prometheus queries.
            return MetricsSnapshot(
                predictions_total=int(pred_total),
                training_samples_total=int(train_total),
                model_accuracy=0.0,  # Would need label-specific query
                drift_score=self.drift_score._value.get(),
                prediction_latency_p50=0.0,  # Computed by Prometheus
                prediction_latency_p95=0.0,  # Computed by Prometheus
                prediction_latency_p99=0.0,  # Computed by Prometheus
                training_latency_p50=0.0,  # Computed by Prometheus
                training_latency_p95=0.0,  # Computed by Prometheus
                model_version=self._current_model_version,
                cold_start_active=self._cold_start_active,
                safety_violations=int(safety_total),
            )

    def reset(self) -> None:
        """Reset all metrics to initial state.

        Warning: This should only be used in testing.
        """
        with self._lock:
            # Re-initialize with new registry
            self._registry = CollectorRegistry()
            self._init_counters()
            self._init_gauges()
            self._init_histograms()
            self._init_info_metrics()
            self._update_callbacks.clear()
            self._current_model_version = "unknown"
            self._cold_start_active = True
            self._start_time = time.time()
            logger.info("MetricsRegistry reset")

    @property
    def registry(self) -> CollectorRegistry:
        """Get the Prometheus collector registry."""
        return self._registry

    def __repr__(self) -> str:
        """String representation of the registry."""
        return (
            f"MetricsRegistry("
            f"prefix='{self._prefix}', "
            f"model_version='{self._current_model_version}', "
            f"callbacks={len(self._update_callbacks)})"
        )


# Global metrics registry instance
metrics_registry = MetricsRegistry()


def get_metrics_registry() -> MetricsRegistry:
    """Get the global metrics registry instance.

    Returns:
        The global MetricsRegistry singleton.
    """
    return metrics_registry


def create_metrics_registry(
    registry: Optional[CollectorRegistry] = None,
    prefix: str = "adaptive_learning",
) -> MetricsRegistry:
    """Create a new metrics registry instance.

    Use this for testing or isolated metric collection.

    Args:
        registry: Prometheus collector registry.
        prefix: Metric name prefix.

    Returns:
        New MetricsRegistry instance.
    """
    return MetricsRegistry(registry=registry, prefix=prefix)
