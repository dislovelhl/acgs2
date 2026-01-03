"""
Adaptive Learning Engine - Online Learner
Constitutional Hash: cdd01ef066bc6cf2

River-based online learning model for real-time governance decisions.
Implements progressive validation (predict first, then learn) paradigm.

PROGRESSIVE VALIDATION (PREQUENTIAL EVALUATION)
===============================================

River implements the "prequential evaluation" paradigm (predictive sequential),
originally proposed by Dawid (1984) for online learning systems. This evaluation
approach more accurately simulates production reality than traditional batch
learning with train/test splits.

Key Principle: "Test, then train"
---------------------------------
For each incoming sample, the model:
1. Makes a prediction FIRST (without seeing the true label)
2. Records the prediction for evaluation
3. Only THEN learns from the sample (after prediction is recorded)

This order is critical - it ensures the model is evaluated on genuinely unseen
data, exactly as it would behave in production where labels arrive after predictions.

Contrast with Batch Learning
-----------------------------
Traditional ML:
- Split data into train/test sets upfront
- Train on all training data
- Evaluate on held-out test set
- Problem: Assumes static data distribution (i.i.d. assumption)
- Problem: Test set may not represent future production data

Progressive Validation (Online Learning):
- No upfront split - each sample is "test, then train"
- Model predicts on sample i, then learns from it
- Sample i+1 becomes the next test case
- Advantage: Simulates production streaming reality
- Advantage: Naturally handles distribution shift (non-stationary data)
- Advantage: More realistic performance estimates

Why This Matters for Governance
--------------------------------
Governance policies evolve over time - new regulations emerge, organizational
priorities shift, user behavior adapts. Progressive validation ensures our
adaptive learning system is evaluated on its ability to:
1. Handle distribution shift (policy drift over time)
2. Learn incrementally without catastrophic forgetting
3. Maintain performance as new governance patterns emerge

The prequential paradigm gives us a more honest estimate of production
performance than batch learning would, since governance is inherently
a streaming, non-stationary problem.

Theoretical Guarantees
----------------------
Under the prequential paradigm:
- Cumulative accuracy converges to true model performance in stationary settings
- Rolling accuracy tracks recent performance for drift detection
- No "future information leakage" - all predictions are truly out-of-sample
- Evaluation is unbiased (no overfitting to a fixed test set)

References
----------
- Dawid, A. P. (1984). "Present Position and Potential Developments: Some
  Personal Views: Statistical Theory: The Prequential Approach."
  Journal of the Royal Statistical Society, Series A.

- Gama, J., Žliobaitė, I., Bifet, A., Pechenizkiy, M., & Bouchachia, A. (2014).
  "A Survey on Concept Drift Adaptation." ACM Computing Surveys, 46(4), 1-37.
  https://doi.org/10.1145/2523813

- River documentation on progressive validation:
  https://riverml.xyz/latest/introduction/getting-started/

- Bifet, A., & Gavaldà, R. (2007). "Learning from Time-Changing Data with
  Adaptive Windowing." SIAM International Conference on Data Mining.
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

    Implements the River online learning paradigm with progressive validation
    (prequential evaluation), which more accurately simulates production ML
    systems than traditional batch learning approaches.

    Core Paradigm: Progressive Validation
    --------------------------------------
    Unlike batch ML where you train once on historical data and deploy:
    1. Each sample arrives as a stream (one at a time)
    2. Model makes prediction WITHOUT seeing the label (production simulation)
    3. True label arrives (delayed feedback in real systems)
    4. Model learns from the labeled sample
    5. Next sample arrives → repeat

    This "test-then-train" cycle ensures:
    - No future information leakage (all predictions are truly out-of-sample)
    - Realistic performance estimates (simulates production streaming)
    - Natural handling of distribution drift (model adapts continuously)
    - Memory efficiency (no need to store entire training dataset)

    Why This Matters for Governance
    --------------------------------
    Governance is NOT a static problem with i.i.d. data:
    - Policies evolve (new regulations, changing organizational priorities)
    - User behavior adapts (users learn the system, adversarial actors probe)
    - Context shifts (seasonal patterns, organizational restructuring)

    Progressive validation gives us honest performance metrics under these
    non-stationary conditions. Batch learning would overfit to historical
    patterns that may no longer apply.

    Implementation Features
    -----------------------
    - One sample at a time (true online learning, not mini-batches)
    - Predict first, then learn (progressive validation / prequential)
    - No separate fit phase (learning is continuous)
    - Cold start handling with conservative defaults (fail-safe for governance)
    - Time-weighted learning for conflicting signals (recent data matters more)
    - Thread-safe operations for concurrent requests (production-ready)
    - Rolling accuracy tracking (detect performance degradation early)

    Model State Lifecycle
    ----------------------
    COLD_START → WARMING → ACTIVE
                          ↕
                       PAUSED (safety circuit breaker)

    - COLD_START: No training samples yet, returns conservative defaults
    - WARMING: Collecting samples but below min_training_samples threshold
    - ACTIVE: Sufficient samples (≥1000), ready for production predictions
    - PAUSED: Safety bounds triggered, learning halted (requires intervention)

    Example usage:
        learner = OnlineLearner()

        # Progressive validation workflow (THE CORRECT ORDER):
        # 1. Predict first (without label)
        prediction = learner.predict_one(features)

        # 2. Later, when true label arrives, learn from it
        learner.learn_one(features, label)

        # Combined atomic operation (ensures correct order):
        prediction, training_result = learner.predict_and_learn(features, label)

        # Monitor performance
        metrics = learner.get_metrics()
        print(f"Cumulative accuracy: {metrics.accuracy:.3f}")
        print(f"Rolling accuracy (last 100): {metrics.recent_accuracy:.3f}")

    References
    ----------
    - River ML: https://riverml.xyz/
    - Gama et al. (2014): "A Survey on Concept Drift Adaptation"
    - Dawid (1984): "The Prequential Approach" (original progressive validation)
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

        CRITICAL: In the progressive validation paradigm, learn AFTER predicting.
        This method should only be called after predict_one() for the same sample.

        Progressive Validation Implementation
        --------------------------------------
        River's prequential evaluation requires this specific order:
        1. predict_one(x) → get prediction without seeing label y
        2. learn_one(x, y) → update model with labeled sample

        This method internally verifies this order by making a prediction
        and comparing it to the true label BEFORE updating the model weights.
        This ensures:
        - Accuracy metrics reflect truly out-of-sample performance
        - No information leakage (model hasn't seen y when predicting)
        - Simulation of production: predict now, learn later when label arrives

        Why One Sample at a Time?
        --------------------------
        True online learning processes samples individually, not in batches:
        - Immediate adaptation to new patterns (no waiting for batch)
        - Memory-efficient (no need to accumulate samples)
        - Handles non-stationary distributions (concept drift)
        - Simulates real-time systems (streaming governance decisions)

        Args:
            x: Feature dictionary with numeric values.
            y: Target label (0 or 1 for binary classification).
            sample_weight: Optional weight for time-weighted learning.
                          Weights >1.0 strengthen signal (learn multiple times).
                          Weights <1.0 weaken signal (probabilistic learning).
                          This enables time-decay for handling non-stationary data.

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

                # PREQUENTIAL EVALUATION: Predict before learning
                # ================================================
                # This is the CORE of progressive validation. For sample i:
                # 1. Get prediction using model trained on samples 1...i-1
                # 2. Compare prediction to true label y (for accuracy)
                # 3. Only THEN update model weights with sample i
                #
                # This ensures accuracy metrics are computed on truly unseen data,
                # exactly as they would be in production where predictions happen
                # before labels arrive. It gives an unbiased estimate of future
                # performance.
                if self._sample_count > 0:
                    try:
                        y_pred = self._model.predict_one(x)
                        if y_pred is not None:
                            # Update cumulative accuracy (overall model health)
                            self._accuracy_metric.update(y, y_pred)
                            # Update rolling accuracy (recent performance for drift detection)
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

        PROGRESSIVE VALIDATION CONVENIENCE METHOD
        =========================================
        This method enforces the correct "test-then-train" order required by
        prequential evaluation. It guarantees that:

        1. predict_one(x) is called FIRST (without seeing label y)
        2. learn_one(x, y) is called SECOND (after prediction recorded)
        3. Both operations are thread-safe (atomic under lock)

        Why Use This Instead of Separate Calls?
        ----------------------------------------
        Calling predict_one() and learn_one() separately is valid, but this
        combined method provides:
        - Guaranteed correct order (prevents accidentally learning before predicting)
        - Thread safety (both operations under single lock acquisition)
        - Convenience (simpler API for common use case)
        - Performance (single lock acquisition instead of two)

        Production Streaming Scenario
        ------------------------------
        In real-world streaming systems, labels often arrive delayed:
        - T=0: Request arrives, predict_one(features) → decision
        - T=1-60min: User action or human review provides true label
        - T=60min: learn_one(features, label) → model adapts

        This method simulates that scenario when you have both features and
        label available simultaneously (e.g., batch replay of historical data
        for model initialization).

        Args:
            x: Feature dictionary with numeric values.
            y: Target label (0 or 1 for binary classification).
            sample_weight: Optional weight for time-weighted learning.
                          Use this for time-decay in non-stationary environments.

        Returns:
            Tuple of (PredictionResult, TrainingResult).
            The prediction is what the model would have predicted in production,
            and the training result confirms whether learning succeeded.

        Example:
            # Replay historical data with progressive validation
            for features, label in historical_data:
                pred, train = learner.predict_and_learn(features, label)
                print(f"Predicted: {pred.prediction}, Actual: {label}, "
                      f"Accuracy so far: {train.current_accuracy:.3f}")
        """
        with self._lock:
            # Step 1: Predict (simulate production prediction without label)
            prediction = self.predict_one(x)
            # Step 2: Learn (simulate delayed label arrival and model update)
            training = self.learn_one(x, y, sample_weight)
            return prediction, training

    def get_accuracy(self) -> float:
        """Get the current cumulative accuracy.

        PROGRESSIVE VALIDATION METRIC
        ==============================
        This accuracy is computed using prequential evaluation - each prediction
        was made on a sample BEFORE the model learned from it. This ensures:

        - No overfitting to test set (every sample was "test, then train")
        - Unbiased performance estimate (truly out-of-sample predictions)
        - Production-realistic metric (simulates streaming deployment)

        Cumulative accuracy tracks overall model health across all samples.
        It converges to the true model performance in stationary settings.

        For non-stationary data (concept drift), also monitor rolling_accuracy
        which tracks recent performance and can detect degradation earlier.

        Returns:
            Accuracy value between 0 and 1 (cumulative across all samples).
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

        DRIFT DETECTION METRIC
        =======================
        This tracks accuracy over the most recent N samples (default: 100).
        Unlike cumulative accuracy which averages over all history, rolling
        accuracy is sensitive to recent performance changes.

        Use rolling accuracy to:
        - Detect concept drift (sudden performance degradation)
        - Monitor adaptation speed (how quickly model recovers)
        - Trigger retraining or model swaps (if rolling << cumulative)

        Progressive Validation Property
        --------------------------------
        Like cumulative accuracy, this is computed using prequential evaluation.
        Each prediction was made before learning from that sample, ensuring
        honest performance measurement even in the rolling window.

        Example Drift Detection:
            if learner.get_rolling_accuracy() < learner.get_accuracy() - 0.1:
                # Rolling accuracy dropped 10% below cumulative
                # Likely concept drift - model struggling on recent data
                trigger_drift_alert()

        Returns:
            Rolling accuracy value between 0 and 1 (last N samples only).
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
