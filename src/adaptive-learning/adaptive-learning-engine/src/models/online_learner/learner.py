"""
Adaptive Learning Engine - Online Learner
Constitutional Hash: cdd01ef066bc6cf2

River-based online learning model for real-time governance decisions.
Implements progressive validation (predict first, then learn) paradigm.
See theory.md for detailed conceptual background.
"""

import logging
import threading
import time
from collections import deque
from typing import Any, Deque, Dict, List, Optional, Tuple

from river import compose, metrics, utils

from .enums import ModelState, ModelType
from .models import ModelMetrics, PredictionResult, TrainingResult
from .pipeline_builder import PipelineBuilder

logger = logging.getLogger(__name__)


class OnlineLearner:
    """River-based online learning model for governance decisions.

    Implements the River online learning paradigm with progressive validation
    (prequential evaluation). See theory.md for detailed background.
    """

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
        """Initialize the online learner. See theory.md for configuration guidelines."""
        self.model_type = model_type
        self.min_training_samples = min_training_samples
        self.learning_rate = learning_rate
        self.l2_regularization = l2_regularization
        self.rolling_window_size = rolling_window_size
        self.time_decay_factor = time_decay_factor

        self._lock = threading.RLock()
        self._model = self._build_pipeline()

        self._accuracy_metric = metrics.Accuracy()
        self._rolling_accuracy_metric = utils.Rolling(
            metrics.Accuracy(), window_size=rolling_window_size
        )

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

    def _build_pipeline(self):
        """Build the River model pipeline using PipelineBuilder."""
        return PipelineBuilder.build_pipeline(
            self.model_type,
            self.learning_rate,
            self.l2_regularization,
        )

    def predict_one(self, x: Dict[str, Any]) -> PredictionResult:
        """Make a prediction for a single sample.

        In the progressive validation paradigm, predict BEFORE learning.
        See theory.md for cold start safety strategy and state logic.
        """
        with self._lock:
            self._predictions_count += 1
            timestamp = time.time()

            if self._state == ModelState.COLD_START:
                return PredictionResult(
                    prediction=self.DEFAULT_PREDICTION,
                    confidence=self.DEFAULT_CONFIDENCE,
                    probabilities={0: 0.5, 1: 0.5},
                    model_state=self._state,
                    sample_count=self._sample_count,
                    timestamp=timestamp,
                )

            try:
                proba = self._model.predict_proba_one(x)

                if proba is None or not proba:
                    prediction = self.DEFAULT_PREDICTION
                    confidence = self.DEFAULT_CONFIDENCE
                    probabilities = {0: 0.5, 1: 0.5}
                else:
                    prediction = max(proba.keys(), key=lambda k: proba[k])
                    confidence = proba.get(prediction, self.DEFAULT_CONFIDENCE)
                    probabilities = dict(proba)

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

        Follows the "learn after predicting" paradigm.
        See theory.md for time-weighted learning and reinforcement strategies.
        """
        with self._lock:
            timestamp = time.time()

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
                if not isinstance(y, int) or y not in (0, 1):
                    return TrainingResult(
                        success=False,
                        sample_count=self._sample_count,
                        current_accuracy=self.get_accuracy(),
                        model_state=self._state,
                        message=f"Invalid label: {y}. Must be 0 or 1.",
                        timestamp=timestamp,
                    )

                # PREQUENTIAL EVALUATION: Predict before learning
                if self._sample_count > 0:
                    try:
                        y_pred = self._model.predict_one(x)
                        if y_pred is not None:
                            self._accuracy_metric.update(y, y_pred)
                            self._rolling_accuracy_metric.update(y, y_pred)
                    except Exception as e:
                        logger.warning(f"Error updating accuracy metrics: {e}")

                # TIME-WEIGHTED LEARNING APPROXIMATION (See theory.md)
                if sample_weight is not None and sample_weight != 1.0:
                    if sample_weight > 1.0:
                        # Strategy 1: Multiple learning
                        for _ in range(int(sample_weight)):
                            self._model.learn_one(x, y)
                    elif sample_weight > 0:
                        # Strategy 2: Probabilistic learning
                        import random

                        if random.random() < sample_weight:
                            self._model.learn_one(x, y)
                else:
                    self._model.learn_one(x, y)

                self._sample_count += 1
                self._last_update_time = timestamp
                self._recent_predictions.append((x.copy(), y, timestamp))
                self._update_feature_stats(x)
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
        """Predict and then learn in a single atomic operation. Refer to theory.md."""
        with self._lock:
            prediction = self.predict_one(x)
            training = self.learn_one(x, y, sample_weight)
            return prediction, training

    def get_accuracy(self) -> float:
        """Get the current cumulative accuracy. Refer to theory.md."""
        with self._lock:
            if self._sample_count == 0:
                return 0.0
            try:
                return float(self._accuracy_metric.get())
            except Exception:
                return 0.0

    def get_rolling_accuracy(self) -> float:
        """Get the rolling window accuracy. See theory.md for details."""
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
            self._rolling_accuracy_metric = utils.Rolling(
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
        """Update the model state based on sample count. Refer to theory.md."""
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
