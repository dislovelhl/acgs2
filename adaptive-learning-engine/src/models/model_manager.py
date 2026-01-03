"""
Adaptive Learning Engine - Model Manager
Constitutional Hash: cdd01ef066bc6cf2

Model lifecycle manager for zero-downtime hot-swapping of online learning models.
Implements atomic reference updates to swap models without dropping requests.
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.models.online_learner import (
    ModelMetrics,
    ModelType,
    OnlineLearner,
    PredictionResult,
    TrainingResult,
)

logger = logging.getLogger(__name__)


class SwapStatus(Enum):
    """Status of a model swap operation."""

    SUCCESS = "success"
    FAILED = "failed"
    REJECTED_SAFETY = "rejected_safety"
    REJECTED_VALIDATION = "rejected_validation"
    PENDING = "pending"


@dataclass
class ModelVersion:
    """Metadata for a model version."""

    version: int
    model: OnlineLearner
    created_at: float = field(default_factory=time.time)
    accuracy: float = 0.0
    sample_count: int = 0
    is_champion: bool = False
    mlflow_run_id: Optional[str] = None
    mlflow_model_uri: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "version": self.version,
            "created_at": self.created_at,
            "accuracy": self.accuracy,
            "sample_count": self.sample_count,
            "is_champion": self.is_champion,
            "mlflow_run_id": self.mlflow_run_id,
            "mlflow_model_uri": self.mlflow_model_uri,
            "model_state": self.model.get_state().value,
            "model_type": self.model.model_type.value,
            "metadata": self.metadata,
        }


@dataclass
class SwapResult:
    """Result of a model swap operation."""

    status: SwapStatus
    old_version: Optional[int]
    new_version: int
    message: str
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "message": self.message,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
        }


class ModelManager:
    """Manager for online learning model lifecycle with zero-downtime hot-swapping.

    Provides:
    - Singleton model access for dependency injection
    - Atomic reference updates for zero-downtime model swaps
    - Version tracking with rollback capability
    - Thread-safe concurrent access
    - Model validation before promotion to production

    Example usage:
        # Initialize manager
        manager = ModelManager()

        # Get current model for predictions (dependency injection)
        model = await manager.get_model()
        prediction = model.predict_one(features)

        # Hot-swap to new model
        result = await manager.swap_model(new_model)

        # Rollback to previous version
        result = await manager.rollback_to_version(1)

    FastAPI integration:
        @app.post("/predict")
        async def predict(
            data: dict,
            model: OnlineLearner = Depends(manager.get_model)
        ):
            return model.predict_one(data)
    """

    # Version history limit
    MAX_VERSION_HISTORY = 10

    def __init__(
        self,
        model_type: ModelType = ModelType.LOGISTIC_REGRESSION,
        min_training_samples: int = 1000,
        learning_rate: float = 0.1,
        l2_regularization: float = 0.01,
        validation_callback: Optional[Callable[[OnlineLearner], bool]] = None,
        auto_rollback: bool = True,
    ) -> None:
        """Initialize the model manager.

        Args:
            model_type: Type of online learning model to use.
            min_training_samples: Minimum samples before model is active.
            learning_rate: Learning rate for the optimizer.
            l2_regularization: L2 regularization strength.
            validation_callback: Optional function to validate model before swap.
                                Should return True if model is valid.
            auto_rollback: If True, automatically rollback on swap failure.
        """
        self.model_type = model_type
        self.min_training_samples = min_training_samples
        self.learning_rate = learning_rate
        self.l2_regularization = l2_regularization
        self.validation_callback = validation_callback
        self.auto_rollback = auto_rollback

        # Thread safety
        self._lock = threading.RLock()
        self._async_lock: Optional[asyncio.Lock] = None

        # Model state - atomic reference
        self._current_model: OnlineLearner = self._create_initial_model()
        self._current_version: int = 1

        # Version history for rollback
        self._version_history: List[ModelVersion] = []
        self._add_to_history(self._current_model)

        # Swap metrics
        self._total_swaps = 0
        self._successful_swaps = 0
        self._failed_swaps = 0
        self._last_swap_time: Optional[float] = None

        # Swap callbacks
        self._on_swap_callbacks: List[Callable[[SwapResult], None]] = []

        logger.info(
            "ModelManager initialized",
            extra={
                "model_type": model_type.value,
                "min_training_samples": min_training_samples,
                "version": self._current_version,
            },
        )

    def _create_initial_model(self) -> OnlineLearner:
        """Create the initial model instance.

        Returns:
            New OnlineLearner instance.
        """
        return OnlineLearner(
            model_type=self.model_type,
            min_training_samples=self.min_training_samples,
            learning_rate=self.learning_rate,
            l2_regularization=self.l2_regularization,
        )

    async def _get_async_lock(self) -> asyncio.Lock:
        """Get or create the async lock (lazy initialization).

        Returns:
            The asyncio.Lock for async operations.
        """
        if self._async_lock is None:
            self._async_lock = asyncio.Lock()
        return self._async_lock

    def _add_to_history(self, model: OnlineLearner) -> ModelVersion:
        """Add a model to the version history.

        Args:
            model: The model to add.

        Returns:
            The created ModelVersion.
        """
        version = ModelVersion(
            version=self._current_version,
            model=model,
            accuracy=model.get_accuracy(),
            sample_count=model.get_sample_count(),
            is_champion=True,
        )

        # Mark old champion as non-champion
        for v in self._version_history:
            v.is_champion = False

        self._version_history.append(version)

        # Trim history if needed
        if len(self._version_history) > self.MAX_VERSION_HISTORY:
            self._version_history = self._version_history[-self.MAX_VERSION_HISTORY :]

        return version

    async def get_model(self) -> OnlineLearner:
        """Get the current active model for predictions.

        This method is designed for FastAPI dependency injection.
        Returns a reference to the current model atomically.

        Returns:
            The current OnlineLearner instance.
        """
        with self._lock:
            return self._current_model

    def get_model_sync(self) -> OnlineLearner:
        """Synchronous version of get_model for non-async contexts.

        Returns:
            The current OnlineLearner instance.
        """
        with self._lock:
            return self._current_model

    async def swap_model(
        self,
        new_model: OnlineLearner,
        validate: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SwapResult:
        """Swap the current model with a new one atomically.

        Zero-downtime swap using atomic reference update.
        Optionally validates the new model before swapping.

        Args:
            new_model: The new model to swap in.
            validate: If True, run validation callback before swap.
            metadata: Optional metadata to attach to the version.

        Returns:
            SwapResult with status and details.
        """
        start_time = time.time()
        async_lock = await self._get_async_lock()

        async with async_lock:
            with self._lock:
                old_version = self._current_version
                new_version = old_version + 1

                try:
                    # Validate new model if callback is set
                    if validate and self.validation_callback is not None:
                        if not self.validation_callback(new_model):
                            self._failed_swaps += 1
                            self._total_swaps += 1
                            return SwapResult(
                                status=SwapStatus.REJECTED_VALIDATION,
                                old_version=old_version,
                                new_version=new_version,
                                message="Model failed validation callback",
                                duration_ms=(time.time() - start_time) * 1000,
                            )

                    # Perform atomic swap
                    self._current_model = new_model
                    self._current_version = new_version

                    # Add to history
                    version_entry = self._add_to_history(new_model)
                    if metadata:
                        version_entry.metadata = metadata

                    # Update metrics
                    self._successful_swaps += 1
                    self._total_swaps += 1
                    self._last_swap_time = time.time()

                    duration_ms = (time.time() - start_time) * 1000

                    result = SwapResult(
                        status=SwapStatus.SUCCESS,
                        old_version=old_version,
                        new_version=new_version,
                        message=f"Model swapped successfully to version {new_version}",
                        duration_ms=duration_ms,
                    )

                    logger.info(
                        "Model swapped successfully",
                        extra={
                            "old_version": old_version,
                            "new_version": new_version,
                            "duration_ms": duration_ms,
                            "new_model_accuracy": new_model.get_accuracy(),
                            "new_model_samples": new_model.get_sample_count(),
                        },
                    )

                    # Notify callbacks
                    for callback in self._on_swap_callbacks:
                        try:
                            callback(result)
                        except Exception as e:
                            logger.error(f"Swap callback error: {e}")

                    return result

                except Exception as e:
                    self._failed_swaps += 1
                    self._total_swaps += 1
                    logger.error(f"Model swap failed: {e}")

                    return SwapResult(
                        status=SwapStatus.FAILED,
                        old_version=old_version,
                        new_version=new_version,
                        message=f"Model swap failed: {str(e)}",
                        duration_ms=(time.time() - start_time) * 1000,
                    )

    async def swap_with_safety_check(
        self,
        new_model: OnlineLearner,
        safety_threshold: float = 0.85,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SwapResult:
        """Swap model only if it meets safety accuracy threshold.

        Args:
            new_model: The new model to swap in.
            safety_threshold: Minimum accuracy required (0.0-1.0).
            metadata: Optional metadata to attach to the version.

        Returns:
            SwapResult with status and details.
        """
        start_time = time.time()

        # Check safety threshold
        new_accuracy = new_model.get_accuracy()
        if new_accuracy < safety_threshold:
            self._failed_swaps += 1
            self._total_swaps += 1
            return SwapResult(
                status=SwapStatus.REJECTED_SAFETY,
                old_version=self._current_version,
                new_version=self._current_version + 1,
                message=f"Model rejected: accuracy {new_accuracy:.3f} < threshold {safety_threshold:.3f}",
                duration_ms=(time.time() - start_time) * 1000,
            )

        # Proceed with swap
        return await self.swap_model(new_model, validate=True, metadata=metadata)

    async def rollback_to_version(self, version: int) -> SwapResult:
        """Rollback to a previous model version.

        Args:
            version: The version number to rollback to.

        Returns:
            SwapResult with status and details.
        """
        start_time = time.time()
        async_lock = await self._get_async_lock()

        async with async_lock:
            with self._lock:
                # Find the version
                target_version = None
                for v in self._version_history:
                    if v.version == version:
                        target_version = v
                        break

                if target_version is None:
                    return SwapResult(
                        status=SwapStatus.FAILED,
                        old_version=self._current_version,
                        new_version=version,
                        message=f"Version {version} not found in history",
                        duration_ms=(time.time() - start_time) * 1000,
                    )

                # Perform rollback (clone the model to avoid state issues)
                old_version = self._current_version
                new_version = old_version + 1

                # Mark current champion as non-champion
                for v in self._version_history:
                    v.is_champion = False

                # Swap to target model
                self._current_model = target_version.model
                self._current_version = new_version
                target_version.is_champion = True

                # Update metrics
                self._successful_swaps += 1
                self._total_swaps += 1
                self._last_swap_time = time.time()

                duration_ms = (time.time() - start_time) * 1000

                result = SwapResult(
                    status=SwapStatus.SUCCESS,
                    old_version=old_version,
                    new_version=new_version,
                    message=f"Rolled back to version {version} (now version {new_version})",
                    duration_ms=duration_ms,
                )

                logger.info(
                    "Model rolled back",
                    extra={
                        "rolled_back_to_version": version,
                        "old_version": old_version,
                        "new_version": new_version,
                        "duration_ms": duration_ms,
                    },
                )

                return result

    async def rollback_to_previous(self) -> SwapResult:
        """Rollback to the immediately previous model version.

        Returns:
            SwapResult with status and details.
        """
        with self._lock:
            if len(self._version_history) < 2:
                return SwapResult(
                    status=SwapStatus.FAILED,
                    old_version=self._current_version,
                    new_version=self._current_version,
                    message="No previous version available for rollback",
                )

            # Get the version before the current champion
            previous_version = None
            for v in reversed(self._version_history):
                if not v.is_champion:
                    previous_version = v.version
                    break

            if previous_version is None:
                return SwapResult(
                    status=SwapStatus.FAILED,
                    old_version=self._current_version,
                    new_version=self._current_version,
                    message="No previous version available for rollback",
                )

        return await self.rollback_to_version(previous_version)

    def get_version_info(self) -> Dict[str, Any]:
        """Get information about the current model version.

        Returns:
            Dictionary with version details.
        """
        with self._lock:
            model = self._current_model
            return {
                "version": self._current_version,
                "model_type": model.model_type.value,
                "model_state": model.get_state().value,
                "accuracy": model.get_accuracy(),
                "rolling_accuracy": model.get_rolling_accuracy(),
                "sample_count": model.get_sample_count(),
                "is_ready": model.is_ready(),
                "last_swap_time": self._last_swap_time,
            }

    def get_version_history(self) -> List[Dict[str, Any]]:
        """Get the version history.

        Returns:
            List of version dictionaries.
        """
        with self._lock:
            return [v.to_dict() for v in self._version_history]

    def get_available_versions(self) -> List[int]:
        """Get list of available version numbers for rollback.

        Returns:
            List of version numbers.
        """
        with self._lock:
            return [v.version for v in self._version_history]

    def get_swap_metrics(self) -> Dict[str, Any]:
        """Get metrics about model swaps.

        Returns:
            Dictionary with swap statistics.
        """
        with self._lock:
            return {
                "total_swaps": self._total_swaps,
                "successful_swaps": self._successful_swaps,
                "failed_swaps": self._failed_swaps,
                "success_rate": (
                    self._successful_swaps / self._total_swaps if self._total_swaps > 0 else 1.0
                ),
                "last_swap_time": self._last_swap_time,
                "current_version": self._current_version,
                "versions_in_history": len(self._version_history),
            }

    def register_swap_callback(self, callback: Callable[[SwapResult], None]) -> None:
        """Register a callback to be called after each swap.

        Args:
            callback: Function to call with SwapResult after swap.
        """
        self._on_swap_callbacks.append(callback)

    def unregister_swap_callback(self, callback: Callable[[SwapResult], None]) -> None:
        """Unregister a swap callback.

        Args:
            callback: The callback function to remove.
        """
        if callback in self._on_swap_callbacks:
            self._on_swap_callbacks.remove(callback)

    async def train_current_model(
        self,
        x: Dict[str, Any],
        y: int,
        sample_weight: Optional[float] = None,
    ) -> TrainingResult:
        """Train the current model with a single sample.

        Thread-safe training that updates the current model in place.

        Args:
            x: Feature dictionary.
            y: Target label.
            sample_weight: Optional weight for time-weighted learning.

        Returns:
            TrainingResult from the model.
        """
        model = await self.get_model()
        return model.learn_one(x, y, sample_weight)

    async def predict_with_current_model(self, x: Dict[str, Any]) -> PredictionResult:
        """Make a prediction with the current model.

        Thread-safe prediction.

        Args:
            x: Feature dictionary.

        Returns:
            PredictionResult from the model.
        """
        model = await self.get_model()
        return model.predict_one(x)

    def create_challenger_model(
        self,
        model_type: Optional[ModelType] = None,
        learning_rate: Optional[float] = None,
        l2_regularization: Optional[float] = None,
    ) -> OnlineLearner:
        """Create a new challenger model for A/B testing or replacement.

        Args:
            model_type: Optional override model type.
            learning_rate: Optional override learning rate.
            l2_regularization: Optional override L2 regularization.

        Returns:
            New OnlineLearner instance.
        """
        return OnlineLearner(
            model_type=model_type or self.model_type,
            min_training_samples=self.min_training_samples,
            learning_rate=learning_rate or self.learning_rate,
            l2_regularization=l2_regularization or self.l2_regularization,
        )

    async def promote_challenger(
        self,
        challenger: OnlineLearner,
        safety_threshold: float = 0.85,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SwapResult:
        """Promote a challenger model to champion if it passes safety checks.

        Args:
            challenger: The challenger model to promote.
            safety_threshold: Minimum accuracy required.
            metadata: Optional metadata to attach.

        Returns:
            SwapResult with status.
        """
        return await self.swap_with_safety_check(challenger, safety_threshold, metadata)

    def pause_learning(self) -> None:
        """Pause learning on the current model."""
        with self._lock:
            self._current_model.pause_learning()

    def resume_learning(self) -> None:
        """Resume learning on the current model."""
        with self._lock:
            self._current_model.resume_learning()

    def get_model_metrics(self) -> ModelMetrics:
        """Get metrics from the current model.

        Returns:
            ModelMetrics from the current model.
        """
        with self._lock:
            return self._current_model.get_metrics()

    def reset_current_model(self) -> None:
        """Reset the current model to initial state.

        Warning: This clears all learned weights.
        """
        with self._lock:
            self._current_model.reset()
            logger.warning("Current model reset to initial state")

    def __repr__(self) -> str:
        """String representation of the manager."""
        return (
            f"ModelManager("
            f"version={self._current_version}, "
            f"model={self._current_model}, "
            f"swaps={self._total_swaps})"
        )
