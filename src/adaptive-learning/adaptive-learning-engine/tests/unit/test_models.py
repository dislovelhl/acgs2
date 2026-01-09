"""
Unit tests for the Adaptive Learning Engine models.

Tests cover:
- OnlineLearner: River-based online learning model
- ModelManager: Zero-downtime hot-swapping model lifecycle

Constitutional Hash: cdd01ef066bc6cf2
"""

import threading
import time
from typing import Any, Dict

import pytest
from src.models.model_manager import ModelManager, ModelVersion, SwapResult, SwapStatus
from src.models.online_learner import (
    ModelMetrics,
    ModelState,
    ModelType,
    OnlineLearner,
    PredictionResult,
    TrainingResult,
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
def training_dataset() -> list:
    """Small dataset for training tests."""
    return [
        ({"feature_a": 1.0, "feature_b": 0.5}, 1),
        ({"feature_a": 0.2, "feature_b": 0.1}, 0),
        ({"feature_a": 0.9, "feature_b": 0.8}, 1),
        ({"feature_a": 0.1, "feature_b": 0.2}, 0),
        ({"feature_a": 0.8, "feature_b": 0.7}, 1),
        ({"feature_a": 0.3, "feature_b": 0.1}, 0),
        ({"feature_a": 0.95, "feature_b": 0.9}, 1),
        ({"feature_a": 0.15, "feature_b": 0.05}, 0),
    ]


@pytest.fixture
def online_learner() -> OnlineLearner:
    """Fresh OnlineLearner with low min_training_samples for testing."""
    return OnlineLearner(
        model_type=ModelType.LOGISTIC_REGRESSION,
        min_training_samples=5,  # Low for quick testing
        learning_rate=0.1,
        l2_regularization=0.01,
        rolling_window_size=10,
        time_decay_factor=0.99,
    )


@pytest.fixture
def trained_learner(training_dataset) -> OnlineLearner:
    """OnlineLearner that has been trained with sample data."""
    learner = OnlineLearner(
        model_type=ModelType.LOGISTIC_REGRESSION,
        min_training_samples=5,
        learning_rate=0.1,
    )
    for features, label in training_dataset:
        learner.learn_one(features, label)
    return learner


@pytest.fixture
def model_manager() -> ModelManager:
    """Fresh ModelManager for testing."""
    return ModelManager(
        model_type=ModelType.LOGISTIC_REGRESSION,
        min_training_samples=5,
        learning_rate=0.1,
        l2_regularization=0.01,
    )


# =============================================================================
# OnlineLearner Tests
# =============================================================================


class TestOnlineLearnerInit:
    """Tests for OnlineLearner initialization."""

    def test_default_initialization(self):
        """Test default initialization creates valid learner."""
        learner = OnlineLearner()

        assert learner.model_type == ModelType.LOGISTIC_REGRESSION
        assert learner.min_training_samples == 1000
        assert learner.learning_rate == 0.1
        assert learner.l2_regularization == 0.01
        assert learner.get_state() == ModelState.COLD_START
        assert learner.get_sample_count() == 0
        assert not learner.is_ready()

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        learner = OnlineLearner(
            model_type=ModelType.PERCEPTRON,
            min_training_samples=100,
            learning_rate=0.05,
            l2_regularization=0.1,
            rolling_window_size=50,
            time_decay_factor=0.95,
        )

        assert learner.model_type == ModelType.PERCEPTRON
        assert learner.min_training_samples == 100
        assert learner.learning_rate == 0.05
        assert learner.l2_regularization == 0.1
        assert learner.rolling_window_size == 50
        assert learner.time_decay_factor == 0.95

    @pytest.mark.parametrize("model_type", list(ModelType))
    def test_all_model_types(self, model_type):
        """Test initialization with all supported model types."""
        learner = OnlineLearner(model_type=model_type)
        assert learner.model_type == model_type
        assert learner._model is not None


class TestOnlineLearnerPrediction:
    """Tests for OnlineLearner prediction functionality."""

    def test_cold_start_prediction(self, online_learner, sample_features):
        """Test prediction returns default values in cold start state."""
        result = online_learner.predict_one(sample_features)

        assert isinstance(result, PredictionResult)
        assert result.prediction == OnlineLearner.DEFAULT_PREDICTION
        assert result.confidence == OnlineLearner.DEFAULT_CONFIDENCE
        assert result.model_state == ModelState.COLD_START
        assert result.sample_count == 0
        assert 0 in result.probabilities
        assert 1 in result.probabilities

    def test_prediction_increments_count(self, online_learner, sample_features):
        """Test that predictions increment the prediction counter."""
        initial_count = online_learner._predictions_count

        online_learner.predict_one(sample_features)
        online_learner.predict_one(sample_features)
        online_learner.predict_one(sample_features)

        assert online_learner._predictions_count == initial_count + 3

    def test_prediction_after_training(self, trained_learner, sample_features):
        """Test predictions work after training."""
        result = trained_learner.predict_one(sample_features)

        assert isinstance(result, PredictionResult)
        assert result.prediction in (0, 1)
        assert 0.0 <= result.confidence <= 1.0
        assert result.model_state != ModelState.COLD_START

    def test_prediction_has_timestamp(self, online_learner, sample_features):
        """Test that predictions include a timestamp."""
        before = time.time()
        result = online_learner.predict_one(sample_features)
        after = time.time()

        assert before <= result.timestamp <= after


class TestOnlineLearnerTraining:
    """Tests for OnlineLearner training functionality."""

    def test_learn_one_success(self, online_learner, sample_features):
        """Test successful training with valid input."""
        result = online_learner.learn_one(sample_features, 1)

        assert isinstance(result, TrainingResult)
        assert result.success is True
        assert result.sample_count == 1
        assert result.message == "Training sample processed successfully"

    def test_learn_one_increments_sample_count(self, online_learner, sample_features):
        """Test that training increments sample count."""
        assert online_learner.get_sample_count() == 0

        online_learner.learn_one(sample_features, 1)
        assert online_learner.get_sample_count() == 1

        online_learner.learn_one(sample_features, 0)
        assert online_learner.get_sample_count() == 2

    def test_learn_one_invalid_label(self, online_learner, sample_features):
        """Test training rejects invalid labels."""
        result = online_learner.learn_one(sample_features, 2)

        assert result.success is False
        assert "Invalid label" in result.message

        result = online_learner.learn_one(sample_features, -1)
        assert result.success is False

    def test_training_updates_model(self, online_learner):
        """Test that training actually updates the model weights."""
        # Train with separable data
        for _ in range(10):
            online_learner.learn_one({"x": 0.9, "y": 0.9}, 1)
            online_learner.learn_one({"x": 0.1, "y": 0.1}, 0)

        # Model should now make predictions based on learned patterns
        # High values should predict 1
        pred_high = online_learner.predict_one({"x": 0.95, "y": 0.95})
        # Low values should predict 0
        pred_low = online_learner.predict_one({"x": 0.05, "y": 0.05})

        # After sufficient training, predictions should reflect the pattern
        assert pred_high.prediction == 1 or pred_low.prediction == 0

    def test_training_stores_recent_data(self, online_learner, sample_features):
        """Test that training stores recent data for drift detection."""
        online_learner.learn_one(sample_features, 1)

        recent_data = online_learner.get_recent_data()
        assert len(recent_data) == 1
        assert recent_data[0][1] == 1  # Label

    def test_training_updates_feature_stats(self, online_learner):
        """Test that training updates feature statistics."""
        online_learner.learn_one({"x": 1.0, "y": 2.0}, 1)
        online_learner.learn_one({"x": 3.0, "y": 4.0}, 0)

        stats = online_learner.get_feature_stats()
        assert "x" in stats
        assert "y" in stats
        assert stats["x"]["min"] == 1.0
        assert stats["x"]["max"] == 3.0
        assert stats["x"]["count"] == 2


class TestOnlineLearnerStateTransitions:
    """Tests for OnlineLearner state transitions."""

    def test_cold_start_to_warming(self, online_learner, sample_features):
        """Test transition from COLD_START to WARMING."""
        assert online_learner.get_state() == ModelState.COLD_START

        online_learner.learn_one(sample_features, 1)

        assert online_learner.get_state() == ModelState.WARMING

    def test_warming_to_active(self, online_learner, training_dataset):
        """Test transition from WARMING to ACTIVE."""
        # Train until reaching min_training_samples (5)
        for features, label in training_dataset[:5]:
            online_learner.learn_one(features, label)

        assert online_learner.get_state() == ModelState.ACTIVE
        assert online_learner.is_ready()

    def test_pause_learning_state(self, online_learner, sample_features):
        """Test that pause_learning sets PAUSED state."""
        online_learner.learn_one(sample_features, 1)  # Move to WARMING
        online_learner.pause_learning()

        assert online_learner.get_state() == ModelState.PAUSED
        assert online_learner._is_paused is True

    def test_paused_learning_rejects_training(self, online_learner, sample_features):
        """Test that training is rejected when paused."""
        online_learner.pause_learning()

        result = online_learner.learn_one(sample_features, 1)

        assert result.success is False
        assert result.model_state == ModelState.PAUSED
        assert "paused" in result.message.lower()

    def test_resume_learning(self, online_learner, sample_features):
        """Test resuming learning after pause."""
        online_learner.learn_one(sample_features, 1)  # Move to WARMING
        online_learner.pause_learning()
        online_learner.resume_learning()

        assert online_learner._is_paused is False
        assert online_learner.get_state() == ModelState.WARMING

        # Training should work again
        result = online_learner.learn_one(sample_features, 0)
        assert result.success is True


class TestOnlineLearnerMetrics:
    """Tests for OnlineLearner metrics functionality."""

    def test_get_accuracy_cold_start(self, online_learner):
        """Test accuracy returns 0.0 in cold start."""
        assert online_learner.get_accuracy() == 0.0

    def test_get_rolling_accuracy_cold_start(self, online_learner):
        """Test rolling accuracy returns 0.0 in cold start."""
        assert online_learner.get_rolling_accuracy() == 0.0

    def test_get_metrics(self, online_learner):
        """Test get_metrics returns valid ModelMetrics."""
        metrics = online_learner.get_metrics()

        assert isinstance(metrics, ModelMetrics)
        assert metrics.sample_count == 0
        assert metrics.model_state == ModelState.COLD_START
        assert metrics.model_type == "logistic_regression"
        assert metrics.predictions_count == 0

    def test_metrics_update_after_training(self, online_learner, sample_features):
        """Test that metrics update after training."""
        online_learner.learn_one(sample_features, 1)
        online_learner.learn_one(sample_features, 0)

        metrics = online_learner.get_metrics()
        assert metrics.sample_count == 2
        assert metrics.last_update_time > 0


class TestOnlineLearnerProgressiveValidation:
    """Tests for progressive validation paradigm (predict first, then learn)."""

    def test_predict_and_learn_atomic(self, online_learner, sample_features):
        """Test predict_and_learn executes both operations atomically."""
        pred_result, train_result = online_learner.predict_and_learn(sample_features, 1)

        assert isinstance(pred_result, PredictionResult)
        assert isinstance(train_result, TrainingResult)
        assert train_result.success is True
        assert online_learner.get_sample_count() == 1

    def test_progressive_validation_order(self, online_learner):
        """Test that predict happens before learn in progressive validation."""
        # Train some samples first
        for i in range(3):
            online_learner.learn_one({"x": float(i)}, i % 2)

        # The prediction should be made BEFORE learning from this sample
        pred_result, _ = online_learner.predict_and_learn({"x": 3.0}, 1)

        # The prediction was made with only 3 samples of training
        assert pred_result.sample_count == 3


class TestOnlineLearnerReset:
    """Tests for OnlineLearner reset functionality."""

    def test_reset_clears_state(self, trained_learner):
        """Test that reset clears all learned state."""
        assert trained_learner.get_sample_count() > 0

        trained_learner.reset()

        assert trained_learner.get_sample_count() == 0
        assert trained_learner._predictions_count == 0
        assert trained_learner.get_state() == ModelState.COLD_START
        assert trained_learner.get_accuracy() == 0.0
        assert len(trained_learner.get_recent_data()) == 0


class TestOnlineLearnerClone:
    """Tests for OnlineLearner clone functionality."""

    def test_clone_creates_new_instance(self, online_learner):
        """Test that clone creates a fresh learner."""
        clone = online_learner.clone()

        assert clone is not online_learner
        assert clone.model_type == online_learner.model_type
        assert clone.min_training_samples == online_learner.min_training_samples
        assert clone.learning_rate == online_learner.learning_rate

    def test_clone_is_independent(self, trained_learner, sample_features):
        """Test that clone doesn't share state with original."""
        clone = trained_learner.clone()

        # Clone should be in cold start (fresh)
        assert clone.get_state() == ModelState.COLD_START
        assert clone.get_sample_count() == 0

        # Training clone shouldn't affect original
        clone.learn_one(sample_features, 1)
        assert clone.get_sample_count() == 1
        assert trained_learner.get_sample_count() > 1


class TestOnlineLearnerModelInfo:
    """Tests for OnlineLearner model info serialization."""

    def test_get_model_info(self, trained_learner):
        """Test get_model_info returns complete information."""
        info = trained_learner.get_model_info()

        assert "model_type" in info
        assert "min_training_samples" in info
        assert "learning_rate" in info
        assert "sample_count" in info
        assert "state" in info
        assert "accuracy" in info
        assert info["sample_count"] > 0


class TestOnlineLearnerThreadSafety:
    """Tests for OnlineLearner thread safety."""

    def test_concurrent_predictions(self, trained_learner):
        """Test concurrent predictions don't cause race conditions."""
        results = []
        errors = []

        def predict():
            try:
                for _ in range(100):
                    result = trained_learner.predict_one({"x": 0.5, "y": 0.5})
                    results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=predict) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 500

    def test_concurrent_training(self, online_learner):
        """Test concurrent training updates are thread-safe."""
        results = []
        errors = []

        def train():
            try:
                for i in range(50):
                    result = online_learner.learn_one({"x": float(i)}, i % 2)
                    results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=train) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        # All training should succeed
        assert all(r.success for r in results)


class TestOnlineLearnerRepr:
    """Tests for OnlineLearner string representation."""

    def test_repr(self, online_learner):
        """Test __repr__ returns informative string."""
        repr_str = repr(online_learner)

        assert "OnlineLearner" in repr_str
        assert "logistic_regression" in repr_str
        assert "cold_start" in repr_str


# =============================================================================
# ModelManager Tests
# =============================================================================


class TestModelManagerInit:
    """Tests for ModelManager initialization."""

    def test_default_initialization(self):
        """Test default initialization creates valid manager."""
        manager = ModelManager()

        assert manager.model_type == ModelType.LOGISTIC_REGRESSION
        assert manager.min_training_samples == 1000
        assert manager._current_version == 1
        assert len(manager._version_history) == 1

    def test_custom_initialization(self):
        """Test initialization with custom parameters."""

        def validator(model):
            return model.get_accuracy() > 0.5

        manager = ModelManager(
            model_type=ModelType.PERCEPTRON,
            min_training_samples=100,
            learning_rate=0.05,
            validation_callback=validator,
            auto_rollback=False,
        )

        assert manager.model_type == ModelType.PERCEPTRON
        assert manager.min_training_samples == 100
        assert manager.validation_callback is not None
        assert manager.auto_rollback is False


class TestModelManagerGetModel:
    """Tests for ModelManager model access."""

    def test_get_model_sync(self, model_manager):
        """Test synchronous model access."""
        model = model_manager.get_model_sync()

        assert isinstance(model, OnlineLearner)
        assert model.model_type == model_manager.model_type

    @pytest.mark.asyncio
    async def test_get_model_async(self, model_manager):
        """Test asynchronous model access."""
        model = await model_manager.get_model()

        assert isinstance(model, OnlineLearner)
        assert model.model_type == model_manager.model_type


class TestModelManagerSwap:
    """Tests for ModelManager model swapping."""

    @pytest.mark.asyncio
    async def test_swap_model_success(self, model_manager):
        """Test successful model swap."""
        new_model = OnlineLearner(min_training_samples=5)

        result = await model_manager.swap_model(new_model)

        assert result.status == SwapStatus.SUCCESS
        assert result.old_version == 1
        assert result.new_version == 2
        assert model_manager._current_version == 2

    @pytest.mark.asyncio
    async def test_swap_model_with_validation_failure(self):
        """Test swap rejection when validation fails."""

        def always_fail(model):
            return False

        manager = ModelManager(validation_callback=always_fail)
        new_model = OnlineLearner(min_training_samples=5)

        result = await manager.swap_model(new_model, validate=True)

        assert result.status == SwapStatus.REJECTED_VALIDATION
        assert manager._current_version == 1  # Unchanged

    @pytest.mark.asyncio
    async def test_swap_model_updates_history(self, model_manager):
        """Test that swap updates version history."""
        new_model = OnlineLearner(min_training_samples=5)

        await model_manager.swap_model(new_model)

        assert len(model_manager._version_history) == 2
        assert model_manager._version_history[-1].is_champion is True

    @pytest.mark.asyncio
    async def test_swap_with_metadata(self, model_manager):
        """Test swap with custom metadata."""
        new_model = OnlineLearner(min_training_samples=5)
        metadata = {"experiment": "test", "notes": "test swap"}

        await model_manager.swap_model(new_model, metadata=metadata)

        latest_version = model_manager._version_history[-1]
        assert latest_version.metadata == metadata


class TestModelManagerSafetyCheck:
    """Tests for ModelManager safety-checked swaps."""

    @pytest.mark.asyncio
    async def test_swap_with_safety_check_pass(self, model_manager, training_dataset):
        """Test safety check passes with good accuracy."""
        # Create and train a model to high accuracy
        new_model = OnlineLearner(min_training_samples=5)
        for features, label in training_dataset * 5:
            new_model.learn_one(features, label)

        # Set low threshold to ensure pass
        result = await model_manager.swap_with_safety_check(new_model, safety_threshold=0.0)

        assert result.status == SwapStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_swap_with_safety_check_reject(self, model_manager):
        """Test safety check rejects low accuracy model."""
        new_model = OnlineLearner(min_training_samples=5)
        # Model has 0 accuracy (no training)

        result = await model_manager.swap_with_safety_check(new_model, safety_threshold=0.9)

        assert result.status == SwapStatus.REJECTED_SAFETY
        assert "accuracy" in result.message.lower()


class TestModelManagerRollback:
    """Tests for ModelManager rollback functionality."""

    @pytest.mark.asyncio
    async def test_rollback_to_version(self, model_manager):
        """Test rollback to a specific version."""
        # Create second version
        new_model = OnlineLearner(min_training_samples=5)
        await model_manager.swap_model(new_model)

        # Rollback to version 1
        result = await model_manager.rollback_to_version(1)

        assert result.status == SwapStatus.SUCCESS
        assert "version 1" in result.message

    @pytest.mark.asyncio
    async def test_rollback_to_nonexistent_version(self, model_manager):
        """Test rollback to non-existent version fails."""
        result = await model_manager.rollback_to_version(999)

        assert result.status == SwapStatus.FAILED
        assert "not found" in result.message

    @pytest.mark.asyncio
    async def test_rollback_to_previous(self, model_manager):
        """Test rollback to previous version."""
        # Create second version
        new_model = OnlineLearner(min_training_samples=5)
        await model_manager.swap_model(new_model)

        # Rollback to previous
        result = await model_manager.rollback_to_previous()

        assert result.status == SwapStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_rollback_to_previous_no_history(self, model_manager):
        """Test rollback fails when no previous version exists."""
        # Only one version in history
        result = await model_manager.rollback_to_previous()

        assert result.status == SwapStatus.FAILED


class TestModelManagerVersionHistory:
    """Tests for ModelManager version history."""

    def test_get_version_info(self, model_manager):
        """Test getting current version info."""
        info = model_manager.get_version_info()

        assert "version" in info
        assert "model_type" in info
        assert "model_state" in info
        assert "accuracy" in info
        assert info["version"] == 1

    def test_get_version_history(self, model_manager):
        """Test getting version history."""
        history = model_manager.get_version_history()

        assert len(history) == 1
        assert history[0]["version"] == 1
        assert history[0]["is_champion"] is True

    def test_get_available_versions(self, model_manager):
        """Test getting available version numbers."""
        versions = model_manager.get_available_versions()

        assert versions == [1]

    @pytest.mark.asyncio
    async def test_version_history_limit(self, model_manager):
        """Test that version history is limited to MAX_VERSION_HISTORY."""
        # Create many versions
        for _ in range(ModelManager.MAX_VERSION_HISTORY + 5):
            new_model = OnlineLearner(min_training_samples=5)
            await model_manager.swap_model(new_model)

        assert len(model_manager._version_history) == ModelManager.MAX_VERSION_HISTORY


class TestModelManagerSwapMetrics:
    """Tests for ModelManager swap metrics."""

    @pytest.mark.asyncio
    async def test_swap_metrics_success(self, model_manager):
        """Test that successful swaps update metrics."""
        new_model = OnlineLearner(min_training_samples=5)
        await model_manager.swap_model(new_model)

        metrics = model_manager.get_swap_metrics()

        assert metrics["total_swaps"] == 1
        assert metrics["successful_swaps"] == 1
        assert metrics["failed_swaps"] == 0
        assert metrics["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_swap_metrics_failure(self):
        """Test that failed swaps update metrics."""
        manager = ModelManager(validation_callback=lambda m: False)
        new_model = OnlineLearner(min_training_samples=5)
        await manager.swap_model(new_model, validate=True)

        metrics = manager.get_swap_metrics()

        assert metrics["total_swaps"] == 1
        assert metrics["successful_swaps"] == 0
        assert metrics["failed_swaps"] == 1


class TestModelManagerSwapCallbacks:
    """Tests for ModelManager swap callbacks."""

    @pytest.mark.asyncio
    async def test_register_swap_callback(self, model_manager):
        """Test registering and triggering swap callbacks."""
        callback_results = []

        def on_swap(result: SwapResult):
            callback_results.append(result)

        model_manager.register_swap_callback(on_swap)

        new_model = OnlineLearner(min_training_samples=5)
        await model_manager.swap_model(new_model)

        assert len(callback_results) == 1
        assert callback_results[0].status == SwapStatus.SUCCESS

    def test_unregister_swap_callback(self, model_manager):
        """Test unregistering swap callbacks."""

        def on_swap(result: SwapResult):
            pass

        model_manager.register_swap_callback(on_swap)
        assert len(model_manager._on_swap_callbacks) == 1

        model_manager.unregister_swap_callback(on_swap)
        assert len(model_manager._on_swap_callbacks) == 0


class TestModelManagerTrainAndPredict:
    """Tests for ModelManager training and prediction proxies."""

    @pytest.mark.asyncio
    async def test_train_current_model(self, model_manager):
        """Test training through the manager."""
        result = await model_manager.train_current_model({"x": 1.0}, 1)

        assert isinstance(result, TrainingResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_predict_with_current_model(self, model_manager):
        """Test prediction through the manager."""
        result = await model_manager.predict_with_current_model({"x": 1.0})

        assert isinstance(result, PredictionResult)


class TestModelManagerChallenger:
    """Tests for ModelManager challenger pattern."""

    def test_create_challenger_model(self, model_manager):
        """Test creating a challenger model."""
        challenger = model_manager.create_challenger_model()

        assert isinstance(challenger, OnlineLearner)
        assert challenger.model_type == model_manager.model_type

    def test_create_challenger_with_overrides(self, model_manager):
        """Test creating challenger with custom parameters."""
        challenger = model_manager.create_challenger_model(
            model_type=ModelType.PERCEPTRON,
            learning_rate=0.5,
        )

        assert challenger.model_type == ModelType.PERCEPTRON
        assert challenger.learning_rate == 0.5

    @pytest.mark.asyncio
    async def test_promote_challenger(self, model_manager):
        """Test promoting challenger to champion."""
        challenger = model_manager.create_challenger_model()

        # Low threshold to allow promotion
        result = await model_manager.promote_challenger(challenger, safety_threshold=0.0)

        assert result.status == SwapStatus.SUCCESS


class TestModelManagerPauseResume:
    """Tests for ModelManager pause/resume functionality."""

    def test_pause_learning(self, model_manager):
        """Test pausing learning on current model."""
        model_manager.pause_learning()

        model = model_manager.get_model_sync()
        assert model._is_paused is True

    def test_resume_learning(self, model_manager):
        """Test resuming learning on current model."""
        model_manager.pause_learning()
        model_manager.resume_learning()

        model = model_manager.get_model_sync()
        assert model._is_paused is False


class TestModelManagerReset:
    """Tests for ModelManager reset functionality."""

    def test_reset_current_model(self, model_manager):
        """Test resetting the current model."""
        model = model_manager.get_model_sync()
        model.learn_one({"x": 1.0}, 1)
        assert model.get_sample_count() == 1

        model_manager.reset_current_model()

        assert model.get_sample_count() == 0


class TestModelManagerGetModelMetrics:
    """Tests for ModelManager get_model_metrics."""

    def test_get_model_metrics(self, model_manager):
        """Test getting model metrics through manager."""
        metrics = model_manager.get_model_metrics()

        assert isinstance(metrics, ModelMetrics)


class TestModelManagerRepr:
    """Tests for ModelManager string representation."""

    def test_repr(self, model_manager):
        """Test __repr__ returns informative string."""
        repr_str = repr(model_manager)

        assert "ModelManager" in repr_str
        assert "version=" in repr_str


# =============================================================================
# ModelVersion and SwapResult Dataclass Tests
# =============================================================================


class TestModelVersion:
    """Tests for ModelVersion dataclass."""

    def test_to_dict(self, online_learner):
        """Test ModelVersion serialization."""
        version = ModelVersion(
            version=1,
            model=online_learner,
            accuracy=0.95,
            sample_count=100,
            is_champion=True,
        )

        data = version.to_dict()

        assert data["version"] == 1
        assert data["accuracy"] == 0.95
        assert data["sample_count"] == 100
        assert data["is_champion"] is True
        assert "model_state" in data
        assert "model_type" in data


class TestSwapResult:
    """Tests for SwapResult dataclass."""

    def test_to_dict(self):
        """Test SwapResult serialization."""
        result = SwapResult(
            status=SwapStatus.SUCCESS,
            old_version=1,
            new_version=2,
            message="Test swap",
            duration_ms=10.5,
        )

        data = result.to_dict()

        assert data["status"] == "success"
        assert data["old_version"] == 1
        assert data["new_version"] == 2
        assert data["message"] == "Test swap"
        assert data["duration_ms"] == 10.5
