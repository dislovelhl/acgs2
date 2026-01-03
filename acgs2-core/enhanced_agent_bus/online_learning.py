"""
ACGS-2 Online Learning Module
Constitutional Hash: cdd01ef066bc6cf2

Implements online incremental learning using River AdaptiveRandomForest with
sklearn compatibility adapter. Enables continuous model updates from feedback
events without full batch retraining.

Key Points:
- River API uses predict_one(x) NOT predict(X) - adapter provides sklearn compatibility
- AdaptiveRandomForest (ARF) handles concept drift naturally
- Expect poor initial performance until ~1000+ samples seen
- All preprocessing must be online/incremental (no batch StandardScaler)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

# Type checking imports for static analysis
if TYPE_CHECKING:
    import numpy.typing as npt

# Optional numpy support
try:
    import numpy as np_module

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np_module = None

# Optional River support
try:
    from river import ensemble as river_ensemble
    from river import metrics as river_metrics
    from river import preprocessing as river_preprocessing
    from river import stats as river_stats

    RIVER_AVAILABLE = True
except ImportError:
    RIVER_AVAILABLE = False
    river_ensemble = None
    river_metrics = None
    river_preprocessing = None
    river_stats = None

logger = logging.getLogger(__name__)

# Configuration from environment
RIVER_MODEL_TYPE = os.getenv("RIVER_MODEL_TYPE", "classifier")
RIVER_N_MODELS = int(os.getenv("RIVER_N_MODELS", "10"))
RIVER_SEED = int(os.getenv("RIVER_SEED", "42"))
MIN_SAMPLES_FOR_PREDICTION = int(os.getenv("MIN_SAMPLES_FOR_PREDICTION", "500"))
ENABLE_COLD_START_FALLBACK = os.getenv("ENABLE_COLD_START_FALLBACK", "true").lower() == "true"


class ModelType(str, Enum):
    """Type of River model to use."""

    CLASSIFIER = "classifier"
    REGRESSOR = "regressor"


class LearningStatus(str, Enum):
    """Status of the online learning system."""

    COLD_START = "cold_start"  # Insufficient samples for reliable predictions
    WARMING_UP = "warming_up"  # Learning but not yet reliable
    READY = "ready"  # Sufficient samples for predictions
    ERROR = "error"  # System in error state


@dataclass
class LearningStats:
    """Statistics for online learning progress."""

    samples_learned: int = 0
    correct_predictions: int = 0
    total_predictions: int = 0
    accuracy: float = 0.0
    last_update: Optional[datetime] = None
    status: LearningStatus = LearningStatus.COLD_START
    feature_names: List[str] = field(default_factory=list)
    metrics_history: List[Dict[str, float]] = field(default_factory=list)


@dataclass
class PredictionResult:
    """Result of an online prediction."""

    prediction: Any
    confidence: Optional[float] = None
    probabilities: Optional[Dict[Any, float]] = None
    used_fallback: bool = False
    model_status: LearningStatus = LearningStatus.COLD_START


@dataclass
class LearningResult:
    """Result of a learning (update) operation."""

    success: bool
    samples_learned: int = 0
    total_samples: int = 0
    error_message: Optional[str] = None


class RiverSklearnAdapter:
    """
    Adapter to make River models compatible with sklearn API.

    River uses a fundamentally different API:
    - predict_one(x: dict) for single sample prediction
    - learn_one(x: dict, y) for single sample learning

    This adapter provides sklearn-style batch methods:
    - predict(X: array) for batch prediction
    - predict_proba(X: array) for probability prediction

    Usage:
        from river import ensemble

        # Initialize River model
        river_model = ensemble.AdaptiveRandomForestClassifier(n_models=10, seed=42)
        adapter = RiverSklearnAdapter(river_model)

        # Online learning from feedback stream
        for feedback_event in feedback_stream:
            features = feedback_event['features']
            outcome = feedback_event['actual_outcome']
            adapter.learn_one(features, outcome)

        # sklearn-style batch prediction
        predictions = adapter.predict(X_batch)
    """

    def __init__(
        self,
        river_model: Optional[Any] = None,
        model_type: ModelType = ModelType.CLASSIFIER,
        n_models: int = RIVER_N_MODELS,
        seed: int = RIVER_SEED,
        feature_names: Optional[List[str]] = None,
    ):
        """
        Initialize the River-sklearn adapter.

        Args:
            river_model: Pre-initialized River model (creates default ARF if None)
            model_type: Type of model (classifier or regressor)
            n_models: Number of trees in the ensemble
            seed: Random seed for reproducibility
            feature_names: Optional list of feature names for dict conversion
        """
        self._check_dependencies()

        self.model_type = model_type
        self.n_models = n_models
        self.seed = seed
        self.feature_names = feature_names or []

        if river_model is not None:
            self.model = river_model
        else:
            self.model = self._create_default_model()

        # Statistics tracking
        self._samples_learned = 0
        self._correct_predictions = 0
        self._total_predictions = 0
        self._last_update: Optional[datetime] = None
        self._running_accuracy = river_metrics.Accuracy() if RIVER_AVAILABLE else None

    def _check_dependencies(self) -> None:
        """Check that required dependencies are available."""
        if not RIVER_AVAILABLE:
            raise ImportError(
                "River is required for online learning. Install with: pip install river"
            )
        if not NUMPY_AVAILABLE:
            raise ImportError(
                "NumPy is required for the sklearn adapter. Install with: pip install numpy"
            )

    def _create_default_model(self) -> Any:
        """Create the default River AdaptiveRandomForest model."""
        if self.model_type == ModelType.CLASSIFIER:
            return river_ensemble.AdaptiveRandomForestClassifier(
                n_models=self.n_models,
                seed=self.seed,
            )
        else:
            return river_ensemble.AdaptiveRandomForestRegressor(
                n_models=self.n_models,
                seed=self.seed,
            )

    def predict(self, X: Union[npt.NDArray[Any], List[List[float]]]) -> npt.NDArray[Any]:
        """
        sklearn-style batch prediction.

        Args:
            X: Feature array of shape (n_samples, n_features)

        Returns:
            Array of predictions of shape (n_samples,)
        """
        predictions = []
        for x in X:
            x_dict = self._to_dict(x)
            pred = self.model.predict_one(x_dict)
            predictions.append(pred)
            self._total_predictions += 1

        return np_module.array(predictions)

    def predict_proba(self, X: Union[npt.NDArray[Any], List[List[float]]]) -> npt.NDArray[Any]:
        """
        sklearn-style probability prediction for classifiers.

        Args:
            X: Feature array of shape (n_samples, n_features)

        Returns:
            Array of probabilities of shape (n_samples, n_classes)
        """
        if self.model_type != ModelType.CLASSIFIER:
            raise ValueError("predict_proba is only available for classifiers")

        probabilities = []
        for x in X:
            x_dict = self._to_dict(x)
            proba = self.model.predict_proba_one(x_dict)
            # Convert dict to list of values in sorted key order
            if proba:
                sorted_keys = sorted(proba.keys())
                proba_values = [proba.get(k, 0.0) for k in sorted_keys]
            else:
                proba_values = [0.5, 0.5]  # Default for binary classification
            probabilities.append(proba_values)

        return np_module.array(probabilities)

    def predict_one(self, x: Union[Dict[Any, float], List[float], npt.NDArray[Any]]) -> Any:
        """
        River-style single sample prediction.

        Args:
            x: Feature values as dict, list, or numpy array

        Returns:
            Predicted value
        """
        x_dict = self._to_dict(x) if not isinstance(x, dict) else x
        self._total_predictions += 1
        return self.model.predict_one(x_dict)

    def predict_proba_one(
        self, x: Union[Dict[Any, float], List[float], npt.NDArray[Any]]
    ) -> Dict[Any, float]:
        """
        River-style single sample probability prediction.

        Args:
            x: Feature values as dict, list, or numpy array

        Returns:
            Dict mapping classes to probabilities
        """
        if self.model_type != ModelType.CLASSIFIER:
            raise ValueError("predict_proba_one is only available for classifiers")

        x_dict = self._to_dict(x) if not isinstance(x, dict) else x
        proba = self.model.predict_proba_one(x_dict)
        return proba if proba else {}

    def learn_one(
        self,
        x: Union[Dict[Any, float], List[float], npt.NDArray[Any]],
        y: Any,
    ) -> None:
        """
        River-style incremental learning update.

        Args:
            x: Feature values as dict, list, or numpy array
            y: Target value
        """
        x_dict = self._to_dict(x) if not isinstance(x, dict) else x

        # Track accuracy if classifier
        if self.model_type == ModelType.CLASSIFIER and self._running_accuracy:
            y_pred = self.model.predict_one(x_dict)
            if y_pred is not None:
                self._running_accuracy.update(y, y_pred)
                if y_pred == y:
                    self._correct_predictions += 1

        # Learn from the sample
        self.model.learn_one(x_dict, y)
        self._samples_learned += 1
        self._last_update = datetime.now(timezone.utc)

    def learn_batch(
        self,
        X: Union[npt.NDArray[Any], List[List[float]]],
        y: Union[npt.NDArray[Any], List[Any]],
    ) -> LearningResult:
        """
        Learn from a batch of samples (processed incrementally).

        Args:
            X: Feature array of shape (n_samples, n_features)
            y: Target array of shape (n_samples,)

        Returns:
            LearningResult with update status
        """
        try:
            samples_learned = 0
            for x_row, y_val in zip(X, y, strict=False):
                self.learn_one(x_row, y_val)
                samples_learned += 1

            return LearningResult(
                success=True,
                samples_learned=samples_learned,
                total_samples=self._samples_learned,
            )

        except Exception as e:
            logger.error(f"Batch learning failed: {e}")
            return LearningResult(
                success=False,
                samples_learned=0,
                total_samples=self._samples_learned,
                error_message=str(e),
            )

    def _to_dict(
        self, x: Union[List[float], npt.NDArray[Any], Dict[Any, float]]
    ) -> Dict[Any, float]:
        """
        Convert array-like features to dict for River.

        Args:
            x: Features as list, numpy array, or dict

        Returns:
            Dict mapping feature indices/names to values
        """
        if isinstance(x, dict):
            return x

        if self.feature_names and len(self.feature_names) == len(x):
            # Use provided feature names
            return {name: float(val) for name, val in zip(self.feature_names, x, strict=True)}
        else:
            # Use numeric indices as keys
            return {i: float(val) for i, val in enumerate(x)}

    def get_stats(self) -> LearningStats:
        """
        Get current learning statistics.

        Returns:
            LearningStats with current metrics
        """
        # Determine status based on samples learned
        if self._samples_learned < MIN_SAMPLES_FOR_PREDICTION // 2:
            status = LearningStatus.COLD_START
        elif self._samples_learned < MIN_SAMPLES_FOR_PREDICTION:
            status = LearningStatus.WARMING_UP
        else:
            status = LearningStatus.READY

        # Calculate accuracy
        if self._running_accuracy and self.model_type == ModelType.CLASSIFIER:
            accuracy = self._running_accuracy.get()
        elif self._total_predictions > 0:
            accuracy = self._correct_predictions / self._total_predictions
        else:
            accuracy = 0.0

        return LearningStats(
            samples_learned=self._samples_learned,
            correct_predictions=self._correct_predictions,
            total_predictions=self._total_predictions,
            accuracy=accuracy,
            last_update=self._last_update,
            status=status,
            feature_names=self.feature_names.copy(),
        )

    @property
    def is_ready(self) -> bool:
        """Check if model has learned enough samples for reliable predictions."""
        return self._samples_learned >= MIN_SAMPLES_FOR_PREDICTION

    @property
    def samples_learned(self) -> int:
        """Get the number of samples learned."""
        return self._samples_learned

    @property
    def accuracy(self) -> float:
        """Get the current running accuracy."""
        if self._running_accuracy and self.model_type == ModelType.CLASSIFIER:
            return self._running_accuracy.get()
        return 0.0

    def reset(self) -> None:
        """Reset the model and statistics."""
        self.model = self._create_default_model()
        self._samples_learned = 0
        self._correct_predictions = 0
        self._total_predictions = 0
        self._last_update = None
        self._running_accuracy = river_metrics.Accuracy() if RIVER_AVAILABLE else None
        logger.info("Online learning model reset")


class OnlineLearningPipeline:
    """
    Pipeline for online learning with preprocessing and cold start handling.

    Manages the full online learning lifecycle:
    - Cold start fallback to sklearn champion model
    - Incremental preprocessing (normalization, feature extraction)
    - Model updates from feedback stream
    - Performance monitoring and metrics

    Usage:
        pipeline = OnlineLearningPipeline(feature_names=["f1", "f2", "f3"])
        pipeline.set_fallback_model(sklearn_model)

        # Online learning from feedback
        for event in feedback_stream:
            result = pipeline.predict(event.features)
            if event.has_outcome:
                pipeline.learn(event.features, event.outcome)
    """

    def __init__(
        self,
        feature_names: Optional[List[str]] = None,
        model_type: ModelType = ModelType.CLASSIFIER,
        n_models: int = RIVER_N_MODELS,
        seed: int = RIVER_SEED,
        enable_preprocessing: bool = True,
        enable_fallback: bool = ENABLE_COLD_START_FALLBACK,
    ):
        """
        Initialize the online learning pipeline.

        Args:
            feature_names: List of feature names
            model_type: Type of model (classifier or regressor)
            n_models: Number of trees in ensemble
            seed: Random seed
            enable_preprocessing: Whether to use online preprocessing
            enable_fallback: Whether to fall back to sklearn model during cold start
        """
        self._check_dependencies()

        self.feature_names = feature_names or []
        self.model_type = model_type
        self.enable_preprocessing = enable_preprocessing
        self.enable_fallback = enable_fallback

        # Initialize River adapter
        self.adapter = RiverSklearnAdapter(
            model_type=model_type,
            n_models=n_models,
            seed=seed,
            feature_names=self.feature_names,
        )

        # Online preprocessing (running statistics for normalization)
        self._running_stats: Dict[str, Any] = {}
        if enable_preprocessing and RIVER_AVAILABLE:
            for name in self.feature_names:
                self._running_stats[name] = river_stats.Mean()

        # Fallback sklearn model for cold start
        self._fallback_model: Optional[Any] = None
        self._fallback_predictions = 0
        self._online_predictions = 0

    def _check_dependencies(self) -> None:
        """Check that required dependencies are available."""
        if not RIVER_AVAILABLE:
            raise ImportError(
                "River is required for online learning. Install with: pip install river"
            )

    def set_fallback_model(self, model: Any) -> None:
        """
        Set the sklearn model for cold start fallback.

        Args:
            model: sklearn-compatible model with predict method
        """
        self._fallback_model = model
        logger.info("Fallback sklearn model configured for cold start")

    def predict(
        self,
        x: Union[Dict[Any, float], List[float], npt.NDArray[Any]],
    ) -> PredictionResult:
        """
        Make a prediction, using fallback during cold start if enabled.

        Args:
            x: Feature values

        Returns:
            PredictionResult with prediction and metadata
        """
        stats = self.adapter.get_stats()

        # Check if we should use fallback
        use_fallback = (
            self.enable_fallback and not self.adapter.is_ready and self._fallback_model is not None
        )

        if use_fallback:
            try:
                # Use sklearn fallback model
                x_array = self._to_array(x)
                prediction = self._fallback_model.predict([x_array])[0]

                # Get probabilities if classifier
                probabilities = None
                confidence = None
                if hasattr(self._fallback_model, "predict_proba"):
                    proba = self._fallback_model.predict_proba([x_array])[0]
                    confidence = float(max(proba))
                    if hasattr(self._fallback_model, "classes_"):
                        probabilities = dict(
                            zip(self._fallback_model.classes_, proba.tolist(), strict=True)
                        )

                self._fallback_predictions += 1

                return PredictionResult(
                    prediction=prediction,
                    confidence=confidence,
                    probabilities=probabilities,
                    used_fallback=True,
                    model_status=stats.status,
                )

            except Exception as e:
                logger.warning(f"Fallback prediction failed: {e}, using online model")

        # Use online River model
        prediction = self.adapter.predict_one(x)

        # Get probabilities if classifier
        probabilities = None
        confidence = None
        if self.model_type == ModelType.CLASSIFIER:
            proba_dict = self.adapter.predict_proba_one(x)
            if proba_dict:
                probabilities = proba_dict
                confidence = max(proba_dict.values()) if proba_dict else None

        self._online_predictions += 1

        return PredictionResult(
            prediction=prediction,
            confidence=confidence,
            probabilities=probabilities,
            used_fallback=False,
            model_status=stats.status,
        )

    def learn(
        self,
        x: Union[Dict[Any, float], List[float], npt.NDArray[Any]],
        y: Any,
    ) -> None:
        """
        Learn from a single sample.

        Args:
            x: Feature values
            y: Target value
        """
        # Update running statistics for preprocessing
        if self.enable_preprocessing and isinstance(x, dict):
            for name, value in x.items():
                if name in self._running_stats:
                    self._running_stats[name].update(value)

        # Learn from the sample
        self.adapter.learn_one(x, y)

    def learn_from_feedback(
        self,
        features: Dict[str, Any],
        outcome: Any,
        decision_id: Optional[str] = None,
    ) -> LearningResult:
        """
        Learn from a feedback event.

        Args:
            features: Feature dict from the feedback event
            outcome: Actual outcome (target value)
            decision_id: Optional decision ID for logging

        Returns:
            LearningResult with update status
        """
        try:
            # Convert features to expected format
            x_dict = {k: float(v) for k, v in features.items() if isinstance(v, (int, float))}

            self.learn(x_dict, outcome)

            if decision_id:
                logger.debug(f"Learned from feedback for decision {decision_id}")

            return LearningResult(
                success=True,
                samples_learned=1,
                total_samples=self.adapter.samples_learned,
            )

        except Exception as e:
            logger.error(f"Failed to learn from feedback: {e}")
            return LearningResult(
                success=False,
                samples_learned=0,
                total_samples=self.adapter.samples_learned,
                error_message=str(e),
            )

    def _to_array(
        self, x: Union[Dict[Any, float], List[float], npt.NDArray[Any]]
    ) -> npt.NDArray[Any]:
        """Convert features to numpy array for sklearn fallback."""
        if isinstance(x, dict):
            if self.feature_names:
                return np_module.array([x.get(name, 0.0) for name in self.feature_names])
            else:
                return np_module.array(list(x.values()))
        elif hasattr(x, "__array__"):
            return np_module.asarray(x)
        else:
            return np_module.array(x)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get pipeline statistics.

        Returns:
            Dict with learning stats and pipeline metrics
        """
        adapter_stats = self.adapter.get_stats()

        total_predictions = self._fallback_predictions + self._online_predictions
        fallback_rate = (
            self._fallback_predictions / total_predictions if total_predictions > 0 else 0.0
        )

        return {
            "learning_stats": {
                "samples_learned": adapter_stats.samples_learned,
                "accuracy": adapter_stats.accuracy,
                "status": adapter_stats.status.value,
                "last_update": (
                    adapter_stats.last_update.isoformat() if adapter_stats.last_update else None
                ),
            },
            "prediction_stats": {
                "total_predictions": total_predictions,
                "online_predictions": self._online_predictions,
                "fallback_predictions": self._fallback_predictions,
                "fallback_rate": fallback_rate,
            },
            "model_ready": self.adapter.is_ready,
            "has_fallback": self._fallback_model is not None,
            "preprocessing_enabled": self.enable_preprocessing,
        }

    def reset(self) -> None:
        """Reset the pipeline and model."""
        self.adapter.reset()
        self._fallback_predictions = 0
        self._online_predictions = 0

        if self.enable_preprocessing and RIVER_AVAILABLE:
            for name in self.feature_names:
                self._running_stats[name] = river_stats.Mean()

        logger.info("Online learning pipeline reset")


# Module-level instances
_online_learning_adapter: Optional[RiverSklearnAdapter] = None
_online_learning_pipeline: Optional[OnlineLearningPipeline] = None


def get_online_learning_adapter(
    model_type: ModelType = ModelType.CLASSIFIER,
    n_models: int = RIVER_N_MODELS,
    feature_names: Optional[List[str]] = None,
) -> RiverSklearnAdapter:
    """
    Get the global online learning adapter instance.

    Args:
        model_type: Type of model (classifier or regressor)
        n_models: Number of trees in ensemble
        feature_names: List of feature names

    Returns:
        Initialized RiverSklearnAdapter
    """
    global _online_learning_adapter

    if _online_learning_adapter is None:
        _online_learning_adapter = RiverSklearnAdapter(
            model_type=model_type,
            n_models=n_models,
            feature_names=feature_names,
        )

    return _online_learning_adapter


def get_online_learning_pipeline(
    feature_names: Optional[List[str]] = None,
    model_type: ModelType = ModelType.CLASSIFIER,
) -> OnlineLearningPipeline:
    """
    Get the global online learning pipeline instance.

    Args:
        feature_names: List of feature names
        model_type: Type of model (classifier or regressor)

    Returns:
        Initialized OnlineLearningPipeline
    """
    global _online_learning_pipeline

    if _online_learning_pipeline is None:
        _online_learning_pipeline = OnlineLearningPipeline(
            feature_names=feature_names,
            model_type=model_type,
        )

    return _online_learning_pipeline


def learn_from_feedback_event(
    features: Dict[str, Any],
    outcome: Any,
    decision_id: Optional[str] = None,
) -> LearningResult:
    """
    Convenience function to learn from a feedback event.

    Args:
        features: Feature dict from the feedback event
        outcome: Actual outcome (target value)
        decision_id: Optional decision ID for logging

    Returns:
        LearningResult with update status
    """
    pipeline = get_online_learning_pipeline()
    return pipeline.learn_from_feedback(features, outcome, decision_id)


# Export key classes and functions
__all__ = [
    # Enums
    "ModelType",
    "LearningStatus",
    # Data Classes
    "LearningStats",
    "PredictionResult",
    "LearningResult",
    # Main Classes
    "RiverSklearnAdapter",
    "OnlineLearningPipeline",
    # Availability Flags
    "RIVER_AVAILABLE",
    "NUMPY_AVAILABLE",
    # Configuration
    "RIVER_MODEL_TYPE",
    "RIVER_N_MODELS",
    "RIVER_SEED",
    "MIN_SAMPLES_FOR_PREDICTION",
    "ENABLE_COLD_START_FALLBACK",
    # Convenience Functions
    "get_online_learning_adapter",
    "get_online_learning_pipeline",
    "learn_from_feedback_event",
]
