"""
Adaptive Learning Engine - Online Learner
Constitutional Hash: cdd01ef066bc6cf2

River-based online learning model for real-time governance decisions.
Implements progressive validation (predict first, then learn) paradigm.
"""

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

from river import compose, linear_model, metrics, optim, preprocessing

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Supported online learning model types."""

    LOGISTIC_REGRESSION = "logistic_regression"
    PERCEPTRON = "perceptron"
    PA_CLASSIFIER = "pa_classifier"  # Passive-Aggressive


class ModelState(Enum):
    """Current state of the online learner."""

    COLD_START = "cold_start"  # No training samples yet
    WARMING = "warming"  # Below min_training_samples
    ACTIVE = "active"  # Trained and ready
    PAUSED = "paused"  # Learning paused due to safety bounds


@dataclass
class PredictionResult:
    """Result from a single prediction."""

    prediction: int
    confidence: float
    probabilities: Dict[int, float]
    model_state: ModelState
    sample_count: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class TrainingResult:
    """Result from a single training update."""

    success: bool
    sample_count: int
    current_accuracy: float
    model_state: ModelState
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ModelMetrics:
    """Current metrics for the online learner."""

    accuracy: float
    sample_count: int
    model_state: ModelState
    recent_accuracy: float  # Rolling window accuracy
    last_update_time: float
    predictions_count: int
    model_type: str


class OnlineLearner:
    """River-based online learning model for governance decisions.

    Implements the River online learning paradigm:
    - One sample at a time (true online learning)
    - Predict first, then learn (progressive validation)
    - No separate fit phase

    Features:
    - Cold start handling with conservative defaults
    - Time-weighted learning for conflicting signals
    - Thread-safe operations for concurrent requests
    - Rolling accuracy tracking

    Example usage:
        learner = OnlineLearner()

        # Progressive validation: predict first, then learn
        prediction = learner.predict_one(features)
        learner.learn_one(features, label)

        # Get current metrics
        metrics = learner.get_metrics()
    """

    # Default deny prediction for cold start
    DEFAULT_PREDICTION = 0
    DEFAULT_CONFIDENCE = 0.5

    def __init__(
        self,
        model_type: ModelType = ModelType.LOGISTIC_REGRESSION,
        min_training_samples: int = 1000,
        learning_rate: float = 0.1,
        l2_regularization: float = 0.01,
        rolling_window_size: int = 100,
        time_decay_factor: float = 0.99,
    ) -> None:
        """Initialize the online learner.

        Args:
            model_type: Type of online learning model to use.
            min_training_samples: Minimum samples before model is active.
            learning_rate: Learning rate for the optimizer.
            l2_regularization: L2 regularization strength.
            rolling_window_size: Window size for rolling accuracy.
            time_decay_factor: Factor for time-weighted learning (0.0-1.0).
        """
        self.model_type = model_type
        self.min_training_samples = min_training_samples
        self.learning_rate = learning_rate
        self.l2_regularization = l2_regularization
        self.rolling_window_size = rolling_window_size
        self.time_decay_factor = time_decay_factor

        # Thread safety
        self._lock = threading.RLock()

        # Build the model pipeline
        self._model = self._build_pipeline()

        # Metrics tracking
        self._accuracy_metric = metrics.Accuracy()
        self._rolling_accuracy_metric = metrics.Rolling(
            metrics.Accuracy(), window_size=rolling_window_size
        )

        # State tracking
        self._sample_count = 0
        self._predictions_count = 0
        self._state = ModelState.COLD_START
        self._last_update_time: Optional[float] = None
        self._is_paused = False

        # Recent predictions for drift detection (thread-safe deque)
        self._recent_predictions: Deque[Tuple[Dict[str, Any], int, float]] = deque(
            maxlen=rolling_window_size
        )

        # Feature statistics for input validation
        self._feature_stats: Dict[str, Dict[str, float]] = {}

        logger.info(
            "OnlineLearner initialized",
            extra={
                "model_type": model_type.value,
                "min_training_samples": min_training_samples,
                "learning_rate": learning_rate,
            },
        )

    def _build_pipeline(self) -> compose.Pipeline:
        """Build the River model pipeline with preprocessing.

        Returns:
            Composed pipeline with preprocessing and model.
        """
        # Select the base model
        if self.model_type == ModelType.LOGISTIC_REGRESSION:
            model = linear_model.LogisticRegression(
                optimizer=optim.SGD(self.learning_rate),
                l2=self.l2_regularization,
            )
        elif self.model_type == ModelType.PERCEPTRON:
            model = linear_model.Perceptron(l2=self.l2_regularization)
        elif self.model_type == ModelType.PA_CLASSIFIER:
            model = linear_model.PAClassifier(C=self.learning_rate)
        else:
            # Default to logistic regression
            model = linear_model.LogisticRegression(
                optimizer=optim.SGD(self.learning_rate),
                l2=self.l2_regularization,
            )

        # Build pipeline with preprocessing
        pipeline = compose.Pipeline(
            ("scaler", preprocessing.StandardScaler()),
            ("model", model),
        )

        return pipeline

    def predict_one(self, x: Dict[str, Any]) -> PredictionResult:
        """Make a prediction for a single sample.

        In the progressive validation paradigm, predict BEFORE learning.
        This simulates production reality where we predict before knowing outcome.

        Args:
            x: Feature dictionary with numeric values.

        Returns:
            PredictionResult with prediction, confidence, and metadata.
        """
        with self._lock:
            self._predictions_count += 1
            timestamp = time.time()

            # Cold start: return conservative default (deny)
            if self._state == ModelState.COLD_START:
                return PredictionResult(
                    prediction=self.DEFAULT_PREDICTION,
                    confidence=self.DEFAULT_CONFIDENCE,
                    probabilities={0: 0.5, 1: 0.5},
                    model_state=self._state,
                    sample_count=self._sample_count,
                    timestamp=timestamp,
                )

            # Get probability predictions
            try:
                proba = self._model.predict_proba_one(x)

                # Handle case where model hasn't seen both classes yet
                if proba is None or not proba:
                    prediction = self.DEFAULT_PREDICTION
                    confidence = self.DEFAULT_CONFIDENCE
                    probabilities = {0: 0.5, 1: 0.5}
                else:
                    # Get prediction and confidence
                    prediction = max(proba.keys(), key=lambda k: proba[k])
                    confidence = proba.get(prediction, self.DEFAULT_CONFIDENCE)
                    probabilities = dict(proba)

                    # Ensure both classes are represented
                    if 0 not in probabilities:
                        probabilities[0] = 1.0 - probabilities.get(1, 0.5)
                    if 1 not in probabilities:
                        probabilities[1] = 1.0 - probabilities.get(0, 0.5)

            except Exception as e:
                logger.warning(f"Prediction error, using default: {e}")
                prediction = self.DEFAULT_PREDICTION
                confidence = self.DEFAULT_CONFIDENCE
                probabilities = {0: 0.5, 1: 0.5}

            return PredictionResult(
                prediction=prediction,
                confidence=confidence,
                probabilities=probabilities,
                model_state=self._state,
                sample_count=self._sample_count,
                timestamp=timestamp,
            )

    def learn_one(
        self,
        x: Dict[str, Any],
        y: int,
        sample_weight: Optional[float] = None,
    ) -> TrainingResult:
        """Update the model with a single training sample.

        In the progressive validation paradigm, learn AFTER predicting.
        This follows River's one-sample-at-a-time online learning.

        Args:
            x: Feature dictionary with numeric values.
            y: Target label (0 or 1 for binary classification).
            sample_weight: Optional weight for time-weighted learning.

        Returns:
            TrainingResult with success status and metrics.
        """
        with self._lock:
            timestamp = time.time()

            # Check if learning is paused
            if self._is_paused:
                return TrainingResult(
                    success=False,
                    sample_count=self._sample_count,
                    current_accuracy=self.get_accuracy(),
                    model_state=ModelState.PAUSED,
                    message="Learning is paused due to safety bounds",
                    timestamp=timestamp,
                )

            try:
                # Validate input
                if not isinstance(y, int) or y not in (0, 1):
                    return TrainingResult(
                        success=False,
                        sample_count=self._sample_count,
                        current_accuracy=self.get_accuracy(),
                        model_state=self._state,
                        message=f"Invalid label: {y}. Must be 0 or 1.",
                        timestamp=timestamp,
                    )

                # Progressive validation: get prediction before learning
                if self._sample_count > 0:
                    try:
                        y_pred = self._model.predict_one(x)
                        if y_pred is not None:
                            self._accuracy_metric.update(y, y_pred)
                            self._rolling_accuracy_metric.update(y, y_pred)
                    except Exception as e:
                        logger.debug(f"Could not update accuracy metrics: {e}")

                # Apply time-weighted learning if weight provided
                if sample_weight is not None and sample_weight != 1.0:
                    # River doesn't directly support sample weights in learn_one
                    # We approximate by learning multiple times for weight > 1
                    # or using a probability for weight < 1
                    if sample_weight > 1.0:
                        # Learn multiple times (rounded)
                        for _ in range(int(sample_weight)):
                            self._model.learn_one(x, y)
                    elif sample_weight > 0:
                        # Learn with probability = weight
                        import random

                        if random.random() < sample_weight:
                            self._model.learn_one(x, y)
                else:
                    # Standard learning
                    self._model.learn_one(x, y)

                # Update state
                self._sample_count += 1
                self._last_update_time = timestamp

                # Store for drift detection
                self._recent_predictions.append((x.copy(), y, timestamp))

                # Update feature statistics
                self._update_feature_stats(x)

                # Update model state
                self._update_state()

                return TrainingResult(
                    success=True,
                    sample_count=self._sample_count,
                    current_accuracy=self.get_accuracy(),
                    model_state=self._state,
                    message="Training sample processed successfully",
                    timestamp=timestamp,
                )

            except Exception as e:
                logger.error(f"Training error: {e}")
                return TrainingResult(
                    success=False,
                    sample_count=self._sample_count,
                    current_accuracy=self.get_accuracy(),
                    model_state=self._state,
                    message=f"Training error: {str(e)}",
                    timestamp=timestamp,
                )

    def predict_and_learn(
        self,
        x: Dict[str, Any],
        y: int,
        sample_weight: Optional[float] = None,
    ) -> Tuple[PredictionResult, TrainingResult]:
        """Predict and then learn in a single atomic operation.

        Implements progressive validation: predict before learning.

        Args:
            x: Feature dictionary with numeric values.
            y: Target label.
            sample_weight: Optional weight for time-weighted learning.

        Returns:
            Tuple of (PredictionResult, TrainingResult).
        """
        with self._lock:
            prediction = self.predict_one(x)
            training = self.learn_one(x, y, sample_weight)
            return prediction, training

    def get_accuracy(self) -> float:
        """Get the current cumulative accuracy.

        Returns:
            Accuracy value between 0 and 1.
        """
        with self._lock:
            if self._sample_count == 0:
                return 0.0
            try:
                return float(self._accuracy_metric.get())
            except Exception:
                return 0.0

    def get_rolling_accuracy(self) -> float:
        """Get the rolling window accuracy.

        Returns:
            Rolling accuracy value between 0 and 1.
        """
        with self._lock:
            if self._sample_count == 0:
                return 0.0
            try:
                return float(self._rolling_accuracy_metric.get())
            except Exception:
                return 0.0

    def get_metrics(self) -> ModelMetrics:
        """Get current model metrics.

        Returns:
            ModelMetrics dataclass with all current metrics.
        """
        with self._lock:
            return ModelMetrics(
                accuracy=self.get_accuracy(),
                sample_count=self._sample_count,
                model_state=self._state,
                recent_accuracy=self.get_rolling_accuracy(),
                last_update_time=self._last_update_time or 0.0,
                predictions_count=self._predictions_count,
                model_type=self.model_type.value,
            )

    def get_recent_data(self) -> List[Tuple[Dict[str, Any], int, float]]:
        """Get recent training data for drift detection.

        Returns:
            List of (features, label, timestamp) tuples.
        """
        with self._lock:
            return list(self._recent_predictions)

    def get_state(self) -> ModelState:
        """Get the current model state.

        Returns:
            Current ModelState enum value.
        """
        with self._lock:
            return self._state

    def get_sample_count(self) -> int:
        """Get the total number of training samples processed.

        Returns:
            Number of samples.
        """
        with self._lock:
            return self._sample_count

    def is_ready(self) -> bool:
        """Check if the model is ready for production predictions.

        Returns:
            True if model is in ACTIVE state.
        """
        with self._lock:
            return self._state == ModelState.ACTIVE

    def pause_learning(self) -> None:
        """Pause online learning (used by safety bounds)."""
        with self._lock:
            self._is_paused = True
            self._state = ModelState.PAUSED
            logger.warning("Online learning paused due to safety bounds trigger")

    def resume_learning(self) -> None:
        """Resume online learning."""
        with self._lock:
            self._is_paused = False
            self._update_state()
            logger.info("Online learning resumed")

    def reset(self) -> None:
        """Reset the model to initial state.

        Warning: This clears all learned weights and metrics.
        """
        with self._lock:
            self._model = self._build_pipeline()
            self._accuracy_metric = metrics.Accuracy()
            self._rolling_accuracy_metric = metrics.Rolling(
                metrics.Accuracy(), window_size=self.rolling_window_size
            )
            self._sample_count = 0
            self._predictions_count = 0
            self._state = ModelState.COLD_START
            self._last_update_time = None
            self._is_paused = False
            self._recent_predictions.clear()
            self._feature_stats.clear()
            logger.info("OnlineLearner reset to initial state")

    def clone(self) -> "OnlineLearner":
        """Create a copy of the learner with the same configuration.

        Note: This creates a fresh learner without learned weights.

        Returns:
            New OnlineLearner instance.
        """
        return OnlineLearner(
            model_type=self.model_type,
            min_training_samples=self.min_training_samples,
            learning_rate=self.learning_rate,
            l2_regularization=self.l2_regularization,
            rolling_window_size=self.rolling_window_size,
            time_decay_factor=self.time_decay_factor,
        )

    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model for serialization.

        Returns:
            Dictionary with model configuration and state.
        """
        with self._lock:
            return {
                "model_type": self.model_type.value,
                "min_training_samples": self.min_training_samples,
                "learning_rate": self.learning_rate,
                "l2_regularization": self.l2_regularization,
                "rolling_window_size": self.rolling_window_size,
                "time_decay_factor": self.time_decay_factor,
                "sample_count": self._sample_count,
                "predictions_count": self._predictions_count,
                "state": self._state.value,
                "accuracy": self.get_accuracy(),
                "rolling_accuracy": self.get_rolling_accuracy(),
                "last_update_time": self._last_update_time,
                "is_paused": self._is_paused,
            }

    def _update_state(self) -> None:
        """Update the model state based on current sample count."""
        if self._is_paused:
            self._state = ModelState.PAUSED
        elif self._sample_count == 0:
            self._state = ModelState.COLD_START
        elif self._sample_count < self.min_training_samples:
            self._state = ModelState.WARMING
        else:
            self._state = ModelState.ACTIVE

    def _update_feature_stats(self, x: Dict[str, Any]) -> None:
        """Update running statistics for features.

        Used for input validation and drift detection baseline.
        """
        for key, value in x.items():
            if not isinstance(value, (int, float)):
                continue

            if key not in self._feature_stats:
                self._feature_stats[key] = {
                    "min": float("inf"),
                    "max": float("-inf"),
                    "count": 0,
                    "sum": 0.0,
                    "sum_sq": 0.0,
                }

            stats = self._feature_stats[key]
            stats["min"] = min(stats["min"], value)
            stats["max"] = max(stats["max"], value)
            stats["count"] += 1
            stats["sum"] += value
            stats["sum_sq"] += value * value

    def get_feature_stats(self) -> Dict[str, Dict[str, float]]:
        """Get computed feature statistics.

        Returns:
            Dictionary of feature names to stats (min, max, mean, std).
        """
        with self._lock:
            result = {}
            for key, stats in self._feature_stats.items():
                count = stats["count"]
                if count > 0:
                    mean = stats["sum"] / count
                    variance = (stats["sum_sq"] / count) - (mean * mean)
                    std = variance**0.5 if variance > 0 else 0.0
                    result[key] = {
                        "min": stats["min"],
                        "max": stats["max"],
                        "mean": mean,
                        "std": std,
                        "count": count,
                    }
            return result

    @property
    def model(self) -> compose.Pipeline:
        """Access the underlying River pipeline (read-only).

        Returns:
            The River Pipeline object.
        """
        return self._model

    def __repr__(self) -> str:
        """String representation of the learner."""
        return (
            f"OnlineLearner("
            f"type={self.model_type.value}, "
            f"state={self._state.value}, "
            f"samples={self._sample_count}, "
            f"accuracy={self.get_accuracy():.3f})"
        )
