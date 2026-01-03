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

Kafka Integration:
- FeedbackKafkaConsumer subscribes to governance.feedback.v1 topic
- Consumer group 'river-learner' ensures single processing of events
- Events are fed to OnlineLearningPipeline for incremental model updates
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

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

# Optional Kafka support
try:
    from aiokafka import AIOKafkaConsumer

    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    AIOKafkaConsumer = None

logger = logging.getLogger(__name__)

# Configuration from environment
RIVER_MODEL_TYPE = os.getenv("RIVER_MODEL_TYPE", "classifier")
RIVER_N_MODELS = int(os.getenv("RIVER_N_MODELS", "10"))
RIVER_SEED = int(os.getenv("RIVER_SEED", "42"))
MIN_SAMPLES_FOR_PREDICTION = int(os.getenv("MIN_SAMPLES_FOR_PREDICTION", "500"))
ENABLE_COLD_START_FALLBACK = os.getenv("ENABLE_COLD_START_FALLBACK", "true").lower() == "true"

# Kafka configuration from environment
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
KAFKA_TOPIC_FEEDBACK = os.getenv("KAFKA_TOPIC_FEEDBACK", "governance.feedback.v1")
KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "river-learner")
KAFKA_AUTO_OFFSET_RESET = os.getenv("KAFKA_AUTO_OFFSET_RESET", "earliest")
KAFKA_MAX_POLL_RECORDS = int(os.getenv("KAFKA_MAX_POLL_RECORDS", "100"))


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


@dataclass
class ConsumerStats:
    """Statistics for Kafka consumer."""

    messages_received: int = 0
    messages_processed: int = 0
    messages_failed: int = 0
    samples_learned: int = 0
    last_offset: int = 0
    last_message_at: Optional[datetime] = None
    consumer_lag: int = 0
    status: str = "stopped"


class FeedbackKafkaConsumer:
    """
    Kafka consumer for feedback events to feed the online learning pipeline.

    Subscribes to the governance.feedback.v1 topic and feeds feedback events
    to the OnlineLearningPipeline for incremental model updates using River.

    Usage:
        pipeline = OnlineLearningPipeline(feature_names=["f1", "f2"])
        consumer = FeedbackKafkaConsumer(pipeline)

        # Start consuming in background
        await consumer.start()

        # Consumer runs continuously, call stop to shutdown
        await consumer.stop()
    """

    def __init__(
        self,
        pipeline: Optional[OnlineLearningPipeline] = None,
        bootstrap_servers: Optional[str] = None,
        topic: Optional[str] = None,
        group_id: Optional[str] = None,
        auto_offset_reset: str = KAFKA_AUTO_OFFSET_RESET,
        max_poll_records: int = KAFKA_MAX_POLL_RECORDS,
        on_message_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """
        Initialize the Kafka consumer for feedback events.

        Args:
            pipeline: OnlineLearningPipeline to feed feedback to (creates default if None)
            bootstrap_servers: Kafka bootstrap servers (defaults to KAFKA_BOOTSTRAP env var)
            topic: Kafka topic to consume from (defaults to KAFKA_TOPIC_FEEDBACK env var)
            group_id: Consumer group ID (defaults to KAFKA_CONSUMER_GROUP env var)
            auto_offset_reset: Where to start reading when no offset exists (earliest/latest)
            max_poll_records: Maximum records to poll in a single call
            on_message_callback: Optional callback for each message (for custom processing)
        """
        self.bootstrap_servers = bootstrap_servers or KAFKA_BOOTSTRAP
        self.topic = topic or KAFKA_TOPIC_FEEDBACK
        self.group_id = group_id or KAFKA_CONSUMER_GROUP
        self.auto_offset_reset = auto_offset_reset
        self.max_poll_records = max_poll_records
        self.on_message_callback = on_message_callback

        # Initialize or get pipeline
        self._pipeline = pipeline
        self._consumer: Optional[Any] = None
        self._running = False
        self._consume_task: Optional[asyncio.Task[None]] = None
        self._lock = asyncio.Lock()

        # Statistics tracking
        self._stats = ConsumerStats()

    def _check_dependencies(self) -> bool:
        """Check that required dependencies are available."""
        if not KAFKA_AVAILABLE:
            logger.error(
                "aiokafka not installed. FeedbackKafkaConsumer unavailable. "
                "Install with: pip install aiokafka"
            )
            return False

        if not RIVER_AVAILABLE:
            logger.error(
                "River not installed. FeedbackKafkaConsumer requires River for online learning. "
                "Install with: pip install river"
            )
            return False

        return True

    async def start(self) -> bool:
        """
        Start the Kafka consumer.

        Returns:
            True if consumer started successfully, False otherwise
        """
        if not self._check_dependencies():
            return False

        async with self._lock:
            if self._running:
                logger.debug("FeedbackKafkaConsumer already running")
                return True

            try:
                # Initialize pipeline if not provided
                if self._pipeline is None:
                    self._pipeline = get_online_learning_pipeline()

                # Create consumer
                self._consumer = AIOKafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    auto_offset_reset=self.auto_offset_reset,
                    max_poll_records=self.max_poll_records,
                    value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                    key_deserializer=lambda k: k.decode("utf-8") if k else None,
                    enable_auto_commit=True,
                    auto_commit_interval_ms=5000,
                )

                await self._consumer.start()
                self._running = True
                self._stats.status = "running"

                # Start consume loop in background
                self._consume_task = asyncio.create_task(self._consume_loop())

                logger.info(
                    f"FeedbackKafkaConsumer started: "
                    f"servers={self._sanitize_bootstrap(self.bootstrap_servers)}, "
                    f"topic={self.topic}, group_id={self.group_id}"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to start FeedbackKafkaConsumer: {self._sanitize_error(e)}")
                self._consumer = None
                self._stats.status = "error"
                return False

    async def stop(self) -> None:
        """Stop the Kafka consumer and clean up resources."""
        async with self._lock:
            if not self._running:
                return

            self._running = False
            self._stats.status = "stopping"

            # Cancel consume task
            if self._consume_task:
                self._consume_task.cancel()
                try:
                    await self._consume_task
                except asyncio.CancelledError:
                    pass
                self._consume_task = None

            # Stop consumer
            if self._consumer:
                try:
                    await self._consumer.stop()
                    logger.info("FeedbackKafkaConsumer stopped")
                except Exception as e:
                    logger.warning(
                        f"Error stopping FeedbackKafkaConsumer: {self._sanitize_error(e)}"
                    )
                finally:
                    self._consumer = None

            self._stats.status = "stopped"

    async def _consume_loop(self) -> None:
        """Main consume loop for processing feedback events."""
        logger.info(f"Starting consume loop for topic {self.topic}")

        try:
            async for msg in self._consumer:
                if not self._running:
                    break

                try:
                    await self._process_message(msg)
                except Exception as e:
                    logger.error(f"Error processing message: {self._sanitize_error(e)}")
                    self._stats.messages_failed += 1

        except asyncio.CancelledError:
            logger.info("Consume loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Consume loop error: {self._sanitize_error(e)}")
            self._stats.status = "error"

    async def _process_message(self, msg: Any) -> None:
        """
        Process a single Kafka message.

        Args:
            msg: Kafka message with value containing feedback event
        """
        self._stats.messages_received += 1
        self._stats.last_offset = msg.offset
        self._stats.last_message_at = datetime.now(timezone.utc)

        try:
            # Parse feedback event from message
            event_data = msg.value

            # Call custom callback if provided
            if self.on_message_callback:
                self.on_message_callback(event_data)

            # Extract features and outcome for learning
            features = event_data.get("features")
            outcome = self._extract_outcome(event_data)
            decision_id = event_data.get("decision_id")

            if features and outcome is not None:
                # Feed to online learning pipeline
                result = self._pipeline.learn_from_feedback(
                    features=features,
                    outcome=outcome,
                    decision_id=decision_id,
                )

                if result.success:
                    self._stats.samples_learned += 1
                    logger.debug(
                        f"Learned from feedback for decision {decision_id}, "
                        f"total samples: {result.total_samples}"
                    )
                else:
                    logger.warning(
                        f"Failed to learn from feedback for decision {decision_id}: "
                        f"{result.error_message}"
                    )

            self._stats.messages_processed += 1

        except Exception as e:
            logger.error(f"Error processing feedback message: {self._sanitize_error(e)}")
            self._stats.messages_failed += 1
            raise

    def _extract_outcome(self, event_data: Dict[str, Any]) -> Optional[Any]:
        """
        Extract the outcome/target value from a feedback event.

        Args:
            event_data: Feedback event dictionary

        Returns:
            Outcome value for learning, or None if not available
        """
        # Try actual_impact first (float)
        actual_impact = event_data.get("actual_impact")
        if actual_impact is not None:
            return float(actual_impact)

        # Try outcome status (categorical)
        outcome = event_data.get("outcome")
        if outcome:
            # Map outcome status to numeric for classifier
            outcome_map = {
                "success": 1,
                "failure": 0,
                "partial": 0.5,
                "unknown": None,
            }
            return outcome_map.get(outcome)

        # Try feedback type (binary)
        feedback_type = event_data.get("feedback_type")
        if feedback_type:
            # Map feedback type to binary for classifier
            feedback_map = {
                "positive": 1,
                "negative": 0,
                "neutral": 0.5,
                "correction": None,  # Correction needs special handling
            }
            return feedback_map.get(feedback_type)

        return None

    def _sanitize_error(self, error: Exception) -> str:
        """Strip sensitive metadata from error messages."""
        error_msg = str(error)
        # Remove potential bootstrap server details if they contain secrets
        error_msg = re.sub(r"bootstrap_servers='[^']+'", "bootstrap_servers='REDACTED'", error_msg)
        error_msg = re.sub(r"password='[^']+'", "password='REDACTED'", error_msg)
        return error_msg

    def _sanitize_bootstrap(self, servers: str) -> str:
        """Sanitize bootstrap servers for logging (show host, hide port details)."""
        parts = servers.split(",")
        sanitized = []
        for part in parts:
            host = part.split(":")[0] if ":" in part else part
            sanitized.append(f"{host}:****")
        return ",".join(sanitized)

    def get_stats(self) -> ConsumerStats:
        """
        Get current consumer statistics.

        Returns:
            ConsumerStats with current metrics
        """
        # Update consumer lag if possible
        if self._pipeline:
            pipeline_stats = self._pipeline.get_stats()
            self._stats.samples_learned = pipeline_stats.get("learning_stats", {}).get(
                "samples_learned", 0
            )

        return self._stats

    @property
    def is_running(self) -> bool:
        """Check if the consumer is running."""
        return self._running

    @property
    def pipeline(self) -> Optional[OnlineLearningPipeline]:
        """Get the online learning pipeline."""
        return self._pipeline


# Module-level instances
_online_learning_adapter: Optional[RiverSklearnAdapter] = None
_online_learning_pipeline: Optional[OnlineLearningPipeline] = None
_feedback_kafka_consumer: Optional[FeedbackKafkaConsumer] = None


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


async def get_feedback_kafka_consumer(
    pipeline: Optional[OnlineLearningPipeline] = None,
) -> FeedbackKafkaConsumer:
    """
    Get or create the global FeedbackKafkaConsumer instance.

    Args:
        pipeline: Optional OnlineLearningPipeline to use

    Returns:
        Initialized FeedbackKafkaConsumer
    """
    global _feedback_kafka_consumer

    if _feedback_kafka_consumer is None:
        _feedback_kafka_consumer = FeedbackKafkaConsumer(pipeline=pipeline)

    return _feedback_kafka_consumer


async def start_feedback_consumer(
    pipeline: Optional[OnlineLearningPipeline] = None,
) -> bool:
    """
    Start the global feedback Kafka consumer.

    Args:
        pipeline: Optional OnlineLearningPipeline to use

    Returns:
        True if consumer started successfully, False otherwise
    """
    consumer = await get_feedback_kafka_consumer(pipeline)
    return await consumer.start()


async def stop_feedback_consumer() -> None:
    """Stop the global feedback Kafka consumer."""
    global _feedback_kafka_consumer

    if _feedback_kafka_consumer is not None:
        await _feedback_kafka_consumer.stop()
        _feedback_kafka_consumer = None


def get_consumer_stats() -> Optional[ConsumerStats]:
    """
    Get statistics from the global feedback consumer.

    Returns:
        ConsumerStats if consumer exists, None otherwise
    """
    if _feedback_kafka_consumer is not None:
        return _feedback_kafka_consumer.get_stats()
    return None


# Export key classes and functions
__all__ = [
    # Enums
    "ModelType",
    "LearningStatus",
    # Data Classes
    "LearningStats",
    "PredictionResult",
    "LearningResult",
    "ConsumerStats",
    # Main Classes
    "RiverSklearnAdapter",
    "OnlineLearningPipeline",
    "FeedbackKafkaConsumer",
    # Availability Flags
    "RIVER_AVAILABLE",
    "NUMPY_AVAILABLE",
    "KAFKA_AVAILABLE",
    # Configuration
    "RIVER_MODEL_TYPE",
    "RIVER_N_MODELS",
    "RIVER_SEED",
    "MIN_SAMPLES_FOR_PREDICTION",
    "ENABLE_COLD_START_FALLBACK",
    "KAFKA_BOOTSTRAP",
    "KAFKA_TOPIC_FEEDBACK",
    "KAFKA_CONSUMER_GROUP",
    # Convenience Functions
    "get_online_learning_adapter",
    "get_online_learning_pipeline",
    "learn_from_feedback_event",
    "get_feedback_kafka_consumer",
    "start_feedback_consumer",
    "stop_feedback_consumer",
    "get_consumer_stats",
]
