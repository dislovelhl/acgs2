"""
ACGS-2 A/B Testing Framework Module
Constitutional Hash: cdd01ef066bc6cf2

Implements A/B testing framework for comparing champion vs candidate model versions
with traffic routing based on hash(request_id) and comprehensive metrics tracking.

Key Features:
- Traffic routing: 90% champion / 10% candidate (configurable via AB_TEST_SPLIT)
- Deterministic routing based on hash(request_id) for consistent user experience
- Per-cohort metrics tracking (accuracy, latency, throughput)
- Model comparison and validation before promotion
- Integration with MLflow for model loading via champion/candidate aliases

Configuration:
- AB_TEST_SPLIT: Fraction of traffic to route to candidate model (default: 0.1)
- CHAMPION_ALIAS: MLflow alias for production model (default: 'champion')
- CANDIDATE_ALIAS: MLflow alias for testing model (default: 'candidate')
- AB_TEST_MIN_SAMPLES: Minimum samples before allowing promotion (default: 1000)

Usage:
    from ab_testing import ABTestRouter, get_ab_test_router

    # Initialize router
    router = get_ab_test_router()

    # Route request and get prediction
    result = router.route_and_predict(request_id="req-123", features=features)

    # Record outcome for metrics
    router.record_outcome(request_id="req-123", predicted=result.prediction, actual=1)

    # Check if candidate is ready for promotion
    comparison = router.compare_metrics()
    if comparison.candidate_is_better and comparison.is_significant:
        router.promote_candidate()
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# Type checking imports for static analysis
if TYPE_CHECKING:
    pass

# Optional numpy support
try:
    import numpy as np_module

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np_module = None

logger = logging.getLogger(__name__)

# Configuration from environment
AB_TEST_SPLIT = float(os.getenv("AB_TEST_SPLIT", "0.1"))
CHAMPION_ALIAS = os.getenv("CHAMPION_ALIAS", "champion")
CANDIDATE_ALIAS = os.getenv("CANDIDATE_ALIAS", "candidate")
AB_TEST_MIN_SAMPLES = int(os.getenv("AB_TEST_MIN_SAMPLES", "1000"))
AB_TEST_CONFIDENCE_LEVEL = float(os.getenv("AB_TEST_CONFIDENCE_LEVEL", "0.95"))
AB_TEST_MIN_IMPROVEMENT = float(os.getenv("AB_TEST_MIN_IMPROVEMENT", "0.01"))
MODEL_REGISTRY_NAME = os.getenv("MODEL_REGISTRY_NAME", "governance_impact_scorer")


class CohortType(str, Enum):
    """Type of A/B test cohort for traffic routing."""

    CHAMPION = "champion"
    CANDIDATE = "candidate"


class PromotionStatus(str, Enum):
    """Status of model promotion validation."""

    READY = "ready"  # Candidate is ready for promotion
    NOT_READY = "not_ready"  # Insufficient samples or validation
    BLOCKED = "blocked"  # Candidate performance is worse
    PROMOTED = "promoted"  # Candidate was promoted to champion
    ERROR = "error"  # Error during promotion


class ComparisonResult(str, Enum):
    """Result of model comparison."""

    CANDIDATE_BETTER = "candidate_better"
    CHAMPION_BETTER = "champion_better"
    NO_DIFFERENCE = "no_difference"
    INSUFFICIENT_DATA = "insufficient_data"


@dataclass
class CohortMetrics:
    """Metrics for a single A/B test cohort."""

    cohort: CohortType
    request_count: int = 0
    correct_predictions: int = 0
    total_predictions: int = 0
    accuracy: float = 0.0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    errors: int = 0
    first_request_at: Optional[datetime] = None
    last_request_at: Optional[datetime] = None
    latencies: List[float] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency in milliseconds."""
        if self.request_count == 0:
            return 0.0
        return self.total_latency_ms / self.request_count

    def record_request(
        self,
        latency_ms: float,
        prediction: Any = None,
        actual: Any = None,
        is_error: bool = False,
    ) -> None:
        """
        Record a request to this cohort.

        Args:
            latency_ms: Request latency in milliseconds
            prediction: Predicted value (optional)
            actual: Actual value for accuracy calculation (optional)
            is_error: Whether the request resulted in an error
        """
        now = datetime.now(timezone.utc)

        self.request_count += 1
        self.total_latency_ms += latency_ms

        # Track latency bounds
        if latency_ms < self.min_latency_ms:
            self.min_latency_ms = latency_ms
        if latency_ms > self.max_latency_ms:
            self.max_latency_ms = latency_ms

        # Store latencies for percentile calculation
        self.latencies.append(latency_ms)

        # Track timestamps
        if self.first_request_at is None:
            self.first_request_at = now
        self.last_request_at = now

        # Track errors
        if is_error:
            self.errors += 1
            return

        # Track predictions and accuracy
        if prediction is not None:
            self.total_predictions += 1
            if actual is not None and prediction == actual:
                self.correct_predictions += 1
                self.accuracy = self.correct_predictions / self.total_predictions

    def calculate_percentiles(self) -> None:
        """Calculate latency percentiles from recorded latencies."""
        if not self.latencies:
            return

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)

        # Calculate percentiles
        self.p50_latency_ms = sorted_latencies[int(n * 0.50)] if n > 0 else 0.0
        self.p95_latency_ms = sorted_latencies[int(n * 0.95)] if n > 0 else 0.0
        self.p99_latency_ms = sorted_latencies[int(n * 0.99)] if n > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for serialization."""
        self.calculate_percentiles()
        return {
            "cohort": self.cohort.value,
            "request_count": self.request_count,
            "correct_predictions": self.correct_predictions,
            "total_predictions": self.total_predictions,
            "accuracy": self.accuracy,
            "avg_latency_ms": self.avg_latency_ms,
            "min_latency_ms": self.min_latency_ms if self.min_latency_ms != float("inf") else 0.0,
            "max_latency_ms": self.max_latency_ms,
            "p50_latency_ms": self.p50_latency_ms,
            "p95_latency_ms": self.p95_latency_ms,
            "p99_latency_ms": self.p99_latency_ms,
            "errors": self.errors,
            "error_rate": self.errors / self.request_count if self.request_count > 0 else 0.0,
            "first_request_at": (
                self.first_request_at.isoformat() if self.first_request_at else None
            ),
            "last_request_at": self.last_request_at.isoformat() if self.last_request_at else None,
        }


@dataclass
class RoutingResult:
    """Result of A/B test traffic routing."""

    cohort: CohortType
    request_id: str
    model_version: Optional[int] = None
    routed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PredictionResult:
    """Result of an A/B test prediction."""

    prediction: Any
    cohort: CohortType
    request_id: str
    latency_ms: float
    model_version: Optional[int] = None
    confidence: Optional[float] = None
    probabilities: Optional[Dict[Any, float]] = None
    error: Optional[str] = None


@dataclass
class MetricsComparison:
    """Comparison between champion and candidate metrics."""

    champion_metrics: CohortMetrics
    candidate_metrics: CohortMetrics
    result: ComparisonResult
    accuracy_delta: float = 0.0
    latency_delta_ms: float = 0.0
    sample_size_champion: int = 0
    sample_size_candidate: int = 0
    is_significant: bool = False
    candidate_is_better: bool = False
    recommendation: str = ""
    compared_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert comparison to dictionary for serialization."""
        return {
            "result": self.result.value,
            "accuracy_delta": self.accuracy_delta,
            "latency_delta_ms": self.latency_delta_ms,
            "sample_size_champion": self.sample_size_champion,
            "sample_size_candidate": self.sample_size_candidate,
            "is_significant": self.is_significant,
            "candidate_is_better": self.candidate_is_better,
            "recommendation": self.recommendation,
            "compared_at": self.compared_at.isoformat(),
            "champion_metrics": self.champion_metrics.to_dict(),
            "candidate_metrics": self.candidate_metrics.to_dict(),
        }


@dataclass
class PromotionResult:
    """Result of promoting candidate to champion."""

    status: PromotionStatus
    previous_champion_version: Optional[int] = None
    new_champion_version: Optional[int] = None
    comparison: Optional[MetricsComparison] = None
    error_message: Optional[str] = None
    promoted_at: Optional[datetime] = None


class ABTestMetricsManager:
    """
    Manages A/B testing metrics collection, analysis, and reporting.

    Handles all metrics-related operations including outcome recording,
    statistical comparison, and traffic distribution analysis.
    """

    def __init__(self, split_ratio: float, min_samples: int, confidence_level: float):
        """Initialize metrics manager."""
        self.split_ratio = split_ratio
        self.min_samples = min_samples
        self.confidence_level = confidence_level

        # Metrics storage
        self.champion_metrics = CohortMetrics(
            cohort=CohortType.CHAMPION,
            request_count=0,
            correct_predictions=0,
            total_predictions=0,
            accuracy=0.0,
            total_latency_ms=0.0,
            min_latency_ms=float("inf"),
        )

        self.candidate_metrics = CohortMetrics(
            cohort=CohortType.CANDIDATE,
            request_count=0,
            correct_predictions=0,
            total_predictions=0,
            accuracy=0.0,
            total_latency_ms=0.0,
            min_latency_ms=float("inf"),
        )

    def record_outcome(
        self, cohort: CohortType, predicted: Any, actual: Any, latency_ms: float
    ) -> None:
        """Record prediction outcome for metrics tracking."""
        metrics = self.champion_metrics if cohort == CohortType.CHAMPION else self.candidate_metrics

        metrics.request_count += 1
        metrics.total_predictions += 1
        metrics.total_latency_ms += latency_ms
        metrics.min_latency_ms = min(metrics.min_latency_ms, latency_ms)

        is_correct = predicted == actual
        if is_correct:
            metrics.correct_predictions += 1

        # Update accuracy
        metrics.accuracy = (
            metrics.correct_predictions / metrics.total_predictions
            if metrics.total_predictions > 0
            else 0.0
        )

    def compare_metrics(self) -> MetricsComparison:
        """Compare champion and candidate metrics."""
        champion_accuracy = (
            self.champion_metrics.successful_predictions / self.champion_metrics.total_requests
            if self.champion_metrics.total_requests > 0
            else 0.0
        )

        candidate_accuracy = (
            self.candidate_metrics.successful_predictions / self.candidate_metrics.total_requests
            if self.candidate_metrics.total_requests > 0
            else 0.0
        )

        improvement = candidate_accuracy - champion_accuracy

        # Check if we have enough samples
        total_samples = self.champion_metrics.request_count + self.candidate_metrics.request_count
        has_min_samples = total_samples >= self.min_samples

        # Check significance (simplified statistical test)
        is_significant = self._check_significance(champion_accuracy, candidate_accuracy)

        candidate_better = improvement > 0 and is_significant and has_min_samples

        return MetricsComparison(
            champion_accuracy=champion_accuracy,
            candidate_accuracy=candidate_accuracy,
            improvement=improvement,
            champion_samples=self.champion_metrics.request_count,
            candidate_samples=self.candidate_metrics.request_count,
            is_significant=is_significant,
            has_min_samples=has_min_samples,
            candidate_is_better=candidate_better,
        )

    def _check_significance(self, champion_acc: float, candidate_acc: float) -> bool:
        """Check if the difference between accuracies is statistically significant."""
        # Simplified significance test - in production, use proper statistical tests
        if self.champion_metrics.request_count < 30 or self.candidate_metrics.request_count < 30:
            return False

        # Simple z-test approximation
        p1, p2 = champion_acc, candidate_acc
        n1, n2 = self.champion_metrics.request_count, self.candidate_metrics.request_count

        if n1 == 0 or n2 == 0:
            return False

        p_combined = (p1 * n1 + p2 * n2) / (n1 + n2)
        se = ((p_combined * (1 - p_combined)) * (1 / n1 + 1 / n2)) ** 0.5

        if se == 0:
            return abs(p1 - p2) > 0.01  # Fallback for edge cases

        z_score = abs(p1 - p2) / se
        return z_score > 1.96  # 95% confidence level

    def get_champion_metrics(self) -> CohortMetrics:
        """Get champion cohort metrics."""
        return self.champion_metrics

    def get_candidate_metrics(self) -> CohortMetrics:
        """Get candidate cohort metrics."""
        return self.candidate_metrics

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary."""
        comparison = self.compare_metrics()

        return {
            "champion": {
                "accuracy": comparison.champion_accuracy,
                "samples": comparison.champion_samples,
                "avg_latency": (
                    self.champion_metrics.total_latency_ms / self.champion_metrics.request_count
                    if self.champion_metrics.request_count > 0
                    else 0
                ),
            },
            "candidate": {
                "accuracy": comparison.candidate_accuracy,
                "samples": comparison.candidate_samples,
                "avg_latency": (
                    self.candidate_metrics.total_latency_ms / self.candidate_metrics.request_count
                    if self.candidate_metrics.request_count > 0
                    else 0
                ),
            },
            "comparison": {
                "improvement": comparison.improvement,
                "is_significant": comparison.is_significant,
                "has_min_samples": comparison.has_min_samples,
                "candidate_better": comparison.candidate_is_better,
            },
            "traffic_distribution": self.get_traffic_distribution(),
        }

    def get_traffic_distribution(self, n_requests: int = 1000) -> Dict[str, Any]:
        """Calculate expected traffic distribution."""
        champion_count = 0
        candidate_count = 0

        # Simulate traffic distribution
        for i in range(n_requests):
            # Simple hash-based routing simulation
            hash_value = hash(f"request-{i}") % 100
            if hash_value < (self.split_ratio * 100):
                candidate_count += 1
            else:
                champion_count += 1

        return {
            "champion_requests": champion_count,
            "candidate_requests": candidate_count,
            "champion_percentage": (champion_count / n_requests) * 100,
            "candidate_percentage": (candidate_count / n_requests) * 100,
            "expected_split": self.split_ratio,
        }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.champion_metrics = CohortMetrics(
            cohort=CohortType.CHAMPION,
            request_count=0,
            correct_predictions=0,
            total_predictions=0,
            accuracy=0.0,
            total_latency_ms=0.0,
            min_latency_ms=float("inf"),
        )

        self.candidate_metrics = CohortMetrics(
            cohort=CohortType.CANDIDATE,
            request_count=0,
            correct_predictions=0,
            total_predictions=0,
            accuracy=0.0,
            total_latency_ms=0.0,
            min_latency_ms=float("inf"),
        )


class ABTestModelManager:
    """
    Manages model loading and versioning for A/B testing.

    Handles loading champion and candidate models from MLflow registry,
    tracks versions, and provides model access to the router.
    """

    def __init__(self, champion_alias: str, candidate_alias: str, model_registry_name: str):
        """Initialize model manager."""
        self.champion_alias = champion_alias
        self.candidate_alias = candidate_alias
        self.model_registry_name = model_registry_name

        self.champion_model = None
        self.candidate_model = None
        self.champion_version = None
        self.candidate_version = None
        self.models_loaded = False

    def load_models(self) -> bool:
        """Load champion and candidate models from registry."""
        try:
            import mlflow.sklearn
            from mlflow.tracking import MlflowClient

            client = MlflowClient()

            # Load champion model
            champion_mv = client.get_model_version_by_alias(
                self.model_registry_name, self.champion_alias
            )
            self.champion_model = mlflow.sklearn.load_model(
                f"models:/{self.model_registry_name}@{self.champion_alias}"
            )
            self.champion_version = champion_mv.version

            # Load candidate model
            candidate_mv = client.get_model_version_by_alias(
                self.model_registry_name, self.candidate_alias
            )
            self.candidate_model = mlflow.sklearn.load_model(
                f"models:/{self.model_registry_name}@{self.candidate_alias}"
            )
            self.candidate_version = candidate_mv.version

            self.models_loaded = True
            logger.info(
                f"Loaded champion v{self.champion_version} and candidate v{self.candidate_version}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            self.models_loaded = False
            return False

    def set_champion_model(self, model: Any, version: Optional[int] = None) -> None:
        """Manually set champion model."""
        self.champion_model = model
        self.champion_version = version
        self.models_loaded = self.models_loaded or (self.candidate_model is not None)

    def set_candidate_model(self, model: Any, version: Optional[int] = None) -> None:
        """Manually set candidate model."""
        self.candidate_model = model
        self.candidate_version = version
        self.models_loaded = self.models_loaded or (self.champion_model is not None)

    def get_champion_model(self) -> Any:
        """Get champion model."""
        return self.champion_model

    def get_candidate_model(self) -> Any:
        """Get candidate model."""
        return self.candidate_model

    def is_ready(self) -> bool:
        """Check if both models are loaded."""
        return (
            self.models_loaded
            and self.champion_model is not None
            and self.candidate_model is not None
        )


class ABTestRouter:
    """
    A/B testing router for comparing champion vs candidate models.

    Routes traffic between champion and candidate models using deterministic
    hashing of request_id for consistent user experience. Now uses composition
    with specialized managers for metrics and model handling.
    """

    def __init__(
        self,
        split_ratio: float = AB_TEST_SPLIT,
        champion_alias: str = CHAMPION_ALIAS,
        candidate_alias: str = CANDIDATE_ALIAS,
        min_samples: int = AB_TEST_MIN_SAMPLES,
        confidence_level: float = AB_TEST_CONFIDENCE_LEVEL,
        model_registry_name: str = MODEL_REGISTRY_NAME,
    ):
        """Initialize A/B test router."""
        self.split_ratio = split_ratio
        self.ab_test_active = True

        # Initialize managers
        self.metrics_manager = ABTestMetricsManager(split_ratio, min_samples, confidence_level)
        self.model_manager = ABTestModelManager(
            champion_alias, candidate_alias, model_registry_name
        )

        # Load models on initialization
        self._ensure_initialized()

    def _ensure_initialized(self) -> None:
        """Ensure models are loaded and router is ready."""
        if not self.model_manager.is_ready():
            success = self.model_manager.load_models()
            if not success:
                logger.warning("Failed to load models from registry, A/B testing disabled")
                self.ab_test_active = False

    def route(self, request_id: str) -> RoutingResult:
        """Route request to champion or candidate based on hash."""
        if not self.ab_test_active or not self.model_manager.is_ready():
            return RoutingResult(cohort=CohortType.CHAMPION, request_id=request_id)

        hash_value = self._compute_hash_value(request_id)
        cohort = CohortType.CANDIDATE if hash_value < self.split_ratio else CohortType.CHAMPION

        return RoutingResult(cohort=cohort, request_id=request_id)

    def _compute_hash_value(self, request_id: str) -> float:
        """Compute hash value for deterministic routing."""
        hash_obj = hashlib.sha256(request_id.encode())
        hash_int = int(hash_obj.hexdigest(), 16)
        return (hash_int % 10000) / 10000.0  # Value between 0 and 1

    def predict(self, cohort: CohortType, features: Any) -> PredictionResult:
        """Make prediction using specified cohort's model."""
        start_time = time.time()

        try:
            if cohort == CohortType.CHAMPION:
                model = self.model_manager.get_champion_model()
            else:
                model = self.model_manager.get_candidate_model()

            if model is None:
                raise ValueError(f"Model for {cohort.value} not available")

            # Make prediction
            if hasattr(model, "predict"):
                prediction = model.predict(features)
            else:
                # Assume it's a function
                prediction = model(features)

            latency_ms = (time.time() - start_time) * 1000

            return PredictionResult(
                prediction=prediction, cohort=cohort, latency_ms=latency_ms, success=True
            )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            logger.error(f"Prediction failed for {cohort.value}: {e}")

            return PredictionResult(
                prediction=None, cohort=cohort, latency_ms=latency_ms, success=False, error=str(e)
            )

    def route_and_predict(self, request_id: str, features: Any) -> PredictionResult:
        """Route request and make prediction in one call."""
        routing = self.route(request_id)
        return self.predict(routing.cohort, features)

    def record_outcome(
        self, request_id: str, predicted: Any, actual: Any, latency_ms: Optional[float] = None
    ) -> None:
        """Record prediction outcome for metrics."""
        routing = self.route(request_id)
        if latency_ms is None:
            latency_ms = 0.0  # Could be improved to track actual latency
        self.metrics_manager.record_outcome(routing.cohort, predicted, actual, latency_ms)

    def compare_metrics(self) -> MetricsComparison:
        """Compare champion and candidate performance."""
        return self.metrics_manager.compare_metrics()

    def promote_candidate(self, force: bool = False) -> PromotionResult:
        """Promote candidate model to champion."""
        comparison = self.compare_metrics()

        if not force and not comparison.candidate_is_better:
            return PromotionResult(
                success=False,
                status=PromotionStatus.BLOCKED,
                message="Candidate not ready for promotion",
                comparison=comparison,
            )

        try:
            # In a real implementation, this would update the registry aliases
            # For now, just swap the models in memory
            champion_model = self.model_manager.get_champion_model()
            champion_version = self.model_manager.champion_version

            self.model_manager.set_champion_model(
                self.model_manager.get_candidate_model(), self.model_manager.candidate_version
            )
            self.model_manager.set_candidate_model(champion_model, champion_version)

            # Reset metrics for new candidate
            self.metrics_manager.reset_metrics()

            return PromotionResult(
                success=True,
                status=PromotionStatus.PROMOTED,
                message="Candidate promoted to champion",
                comparison=comparison,
            )

        except Exception as e:
            return PromotionResult(
                success=False,
                status=PromotionStatus.ERROR,
                message=f"Promotion failed: {e}",
                comparison=comparison,
            )

    # Delegate other methods to managers
    def set_champion_model(self, model: Any, version: Optional[int] = None) -> None:
        """Set champion model."""
        self.model_manager.set_champion_model(model, version)

    def set_candidate_model(self, model: Any, version: Optional[int] = None) -> None:
        """Set candidate model."""
        self.model_manager.set_candidate_model(model, version)

    def set_ab_test_active(self, active: bool) -> None:
        """Enable or disable A/B testing."""
        self.ab_test_active = active

    def get_champion_metrics(self) -> CohortMetrics:
        """Get champion metrics."""
        return self.metrics_manager.get_champion_metrics()

    def get_candidate_metrics(self) -> CohortMetrics:
        """Get candidate metrics."""
        return self.metrics_manager.get_candidate_metrics()

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return self.metrics_manager.get_metrics_summary()

    def get_traffic_distribution(self, n_requests: int = 1000) -> Dict[str, Any]:
        """Get traffic distribution."""
        return self.metrics_manager.get_traffic_distribution(n_requests)


# Export key classes and functions
__all__ = [
    # Enums
    "CohortType",
    "PromotionStatus",
    "ComparisonResult",
    # Data Classes
    "CohortMetrics",
    "RoutingResult",
    "PredictionResult",
    "MetricsComparison",
    "PromotionResult",
    # Main Class
    "ABTestRouter",
    # Configuration
    "AB_TEST_SPLIT",
    "CHAMPION_ALIAS",
    "CANDIDATE_ALIAS",
    "AB_TEST_MIN_SAMPLES",
    "AB_TEST_CONFIDENCE_LEVEL",
    "AB_TEST_MIN_IMPROVEMENT",
    "MODEL_REGISTRY_NAME",
    # Availability
    "NUMPY_AVAILABLE",
    # Convenience Functions
    "get_ab_test_router",
    "route_request",
    "route_and_predict",
    "get_ab_test_metrics",
    "compare_models",
    "promote_candidate_model",
]
