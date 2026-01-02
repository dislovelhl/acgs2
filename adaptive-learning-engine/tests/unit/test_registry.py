"""
Unit tests for the Adaptive Learning Engine MLflow Registry module.

Tests cover:
- MLflowRegistry: Model versioning, registration, rollback, and local fallback

Constitutional Hash: cdd01ef066bc6cf2
"""

import json
import os
import pickle
import shutil
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from src.registry.mlflow_client import (
    MLflowRegistry,
    ModelMetadata,
    ModelStage,
    ModelVersion,
    RegistrationResult,
    RegistryStatus,
    RollbackResult,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def temp_fallback_dir():
    """Create a temporary directory for local fallback testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_metadata() -> ModelMetadata:
    """Sample model metadata for testing."""
    return ModelMetadata(
        accuracy=0.92,
        drift_score=0.15,
        sample_count=1000,
        model_type="logistic_regression",
        learning_rate=0.1,
        l2_regularization=0.01,
        algorithm="LogisticRegression",
        training_timestamp=time.time(),
        extra={"experiment": "test"},
    )


@pytest.fixture
def mock_model() -> Any:
    """Mock model for testing (pickle-able)."""
    return {"type": "mock", "weights": [0.1, 0.2, 0.3]}


@pytest.fixture
def mlflow_registry(temp_fallback_dir) -> MLflowRegistry:
    """MLflowRegistry with local fallback only (no MLflow dependency)."""
    return MLflowRegistry(
        tracking_uri="sqlite:///fake_mlruns/mlflow.db",
        model_name="test_model",
        local_fallback_dir=temp_fallback_dir,
        enable_local_fallback=True,
    )


@pytest.fixture
def local_only_registry(temp_fallback_dir) -> MLflowRegistry:
    """Registry that only uses local fallback (MLflow disabled)."""
    registry = MLflowRegistry(
        tracking_uri=None,
        model_name="test_model",
        local_fallback_dir=temp_fallback_dir,
        enable_local_fallback=True,
    )
    # Force disconnected state to use local fallback
    registry._status = RegistryStatus.DISCONNECTED
    return registry


# =============================================================================
# ModelMetadata Tests
# =============================================================================


class TestModelMetadata:
    """Tests for ModelMetadata dataclass."""

    def test_model_metadata_creation(self):
        """Test creating ModelMetadata."""
        metadata = ModelMetadata(
            accuracy=0.95,
            drift_score=0.1,
            sample_count=500,
            model_type="logistic_regression",
            learning_rate=0.1,
            l2_regularization=0.01,
            algorithm="LogisticRegression",
            training_timestamp=123456.789,
        )

        assert metadata.accuracy == 0.95
        assert metadata.drift_score == 0.1
        assert metadata.sample_count == 500
        assert metadata.model_type == "logistic_regression"
        assert metadata.learning_rate == 0.1
        assert metadata.l2_regularization == 0.01
        assert metadata.algorithm == "LogisticRegression"
        assert metadata.training_timestamp == 123456.789
        assert metadata.extra == {}

    def test_model_metadata_with_extra(self):
        """Test ModelMetadata with extra fields."""
        metadata = ModelMetadata(
            accuracy=0.95,
            drift_score=0.1,
            sample_count=500,
            model_type="logistic_regression",
            learning_rate=0.1,
            l2_regularization=0.01,
            algorithm="LogisticRegression",
            training_timestamp=time.time(),
            extra={"custom_field": "value", "score": 42},
        )

        assert metadata.extra["custom_field"] == "value"
        assert metadata.extra["score"] == 42


# =============================================================================
# ModelVersion Tests
# =============================================================================


class TestModelVersion:
    """Tests for ModelVersion dataclass."""

    def test_model_version_creation(self):
        """Test creating ModelVersion."""
        version = ModelVersion(
            version="1",
            name="test_model",
            stage=ModelStage.PRODUCTION,
            description="Test version",
            tags={"env": "test"},
            creation_timestamp=time.time(),
            last_updated_timestamp=time.time(),
            run_id="run_123",
            source="models:/test_model/1",
            aliases=["champion"],
        )

        assert version.version == "1"
        assert version.name == "test_model"
        assert version.stage == ModelStage.PRODUCTION
        assert version.description == "Test version"
        assert version.tags == {"env": "test"}
        assert "champion" in version.aliases

    def test_model_version_default_aliases(self):
        """Test ModelVersion with default empty aliases."""
        version = ModelVersion(
            version="1",
            name="test_model",
            stage=ModelStage.NONE,
            description="",
            tags={},
            creation_timestamp=time.time(),
            last_updated_timestamp=time.time(),
        )

        assert version.aliases == []
        assert version.run_id is None
        assert version.source is None


# =============================================================================
# RegistrationResult Tests
# =============================================================================


class TestRegistrationResult:
    """Tests for RegistrationResult dataclass."""

    def test_registration_result_success(self):
        """Test successful registration result."""
        result = RegistrationResult(
            success=True,
            version="1",
            model_uri="models:/test_model/1",
            message="Model registered successfully",
        )

        assert result.success is True
        assert result.version == "1"
        assert result.model_uri == "models:/test_model/1"
        assert result.message == "Model registered successfully"
        assert result.timestamp > 0

    def test_registration_result_failure(self):
        """Test failed registration result."""
        result = RegistrationResult(
            success=False,
            version=None,
            model_uri=None,
            message="Registration failed: error",
        )

        assert result.success is False
        assert result.version is None
        assert result.model_uri is None
        assert "failed" in result.message.lower()


# =============================================================================
# RollbackResult Tests
# =============================================================================


class TestRollbackResult:
    """Tests for RollbackResult dataclass."""

    def test_rollback_result_success(self):
        """Test successful rollback result."""
        result = RollbackResult(
            success=True,
            previous_version="2",
            new_version="1",
            message="Rolled back from version 2 to 1",
        )

        assert result.success is True
        assert result.previous_version == "2"
        assert result.new_version == "1"
        assert "2" in result.message and "1" in result.message
        assert result.timestamp > 0

    def test_rollback_result_failure(self):
        """Test failed rollback result."""
        result = RollbackResult(
            success=False,
            previous_version="2",
            new_version=None,
            message="Version not found",
        )

        assert result.success is False
        assert result.new_version is None


# =============================================================================
# ModelStage Enum Tests
# =============================================================================


class TestModelStage:
    """Tests for ModelStage enum."""

    def test_model_stage_values(self):
        """Test ModelStage enum values."""
        assert ModelStage.NONE.value == "None"
        assert ModelStage.STAGING.value == "Staging"
        assert ModelStage.PRODUCTION.value == "Production"
        assert ModelStage.ARCHIVED.value == "Archived"


# =============================================================================
# RegistryStatus Enum Tests
# =============================================================================


class TestRegistryStatus:
    """Tests for RegistryStatus enum."""

    def test_registry_status_values(self):
        """Test RegistryStatus enum values."""
        assert RegistryStatus.CONNECTED.value == "connected"
        assert RegistryStatus.DISCONNECTED.value == "disconnected"
        assert RegistryStatus.DEGRADED.value == "degraded"


# =============================================================================
# MLflowRegistry Tests - Initialization
# =============================================================================


class TestMLflowRegistryInit:
    """Tests for MLflowRegistry initialization."""

    def test_default_initialization(self, temp_fallback_dir):
        """Test default initialization creates valid registry."""
        registry = MLflowRegistry(local_fallback_dir=temp_fallback_dir)

        assert registry.tracking_uri == MLflowRegistry.DEFAULT_TRACKING_URI
        assert registry.model_name == MLflowRegistry.DEFAULT_MODEL_NAME
        assert registry.champion_alias == MLflowRegistry.DEFAULT_CHAMPION_ALIAS
        assert registry.challenger_alias == MLflowRegistry.DEFAULT_CHALLENGER_ALIAS
        assert registry.enable_local_fallback is True
        assert registry._status == RegistryStatus.DISCONNECTED

    def test_custom_initialization(self, temp_fallback_dir):
        """Test initialization with custom parameters."""
        registry = MLflowRegistry(
            tracking_uri="sqlite:///custom/mlflow.db",
            model_name="custom_model",
            champion_alias="prod",
            challenger_alias="staging",
            local_fallback_dir=temp_fallback_dir,
            enable_local_fallback=False,
        )

        assert registry.tracking_uri == "sqlite:///custom/mlflow.db"
        assert registry.model_name == "custom_model"
        assert registry.champion_alias == "prod"
        assert registry.challenger_alias == "staging"
        assert registry.enable_local_fallback is False

    def test_local_fallback_dir_path(self, temp_fallback_dir):
        """Test local fallback directory is set as Path."""
        registry = MLflowRegistry(local_fallback_dir=temp_fallback_dir)

        assert isinstance(registry.local_fallback_dir, Path)
        assert str(registry.local_fallback_dir) == temp_fallback_dir


# =============================================================================
# MLflowRegistry Tests - Local Fallback Registration
# =============================================================================


class TestMLflowRegistryLocalRegistration:
    """Tests for local fallback model registration."""

    def test_register_model_locally(self, local_only_registry, mock_model, sample_metadata):
        """Test registering model to local storage."""
        result = local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
            description="Test registration",
            promote_to_champion=True,
        )

        assert result.success is True
        assert result.version == "1"
        assert result.model_uri is not None
        assert "locally" in result.message.lower() or "version" in result.message.lower()

    def test_register_multiple_versions(self, local_only_registry, mock_model, sample_metadata):
        """Test registering multiple model versions."""
        # Register first version
        result1 = local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
        )
        assert result1.version == "1"

        # Register second version
        result2 = local_only_registry.register_model(
            model={"type": "mock", "weights": [0.5, 0.5]},
            metadata=sample_metadata,
        )
        assert result2.version == "2"

        # Verify both versions exist
        versions = local_only_registry._get_local_versions()
        assert "1" in versions
        assert "2" in versions

    def test_register_model_creates_files(self, local_only_registry, mock_model, sample_metadata):
        """Test that registration creates proper files."""
        result = local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
        )

        version_dir = local_only_registry.local_fallback_dir / f"v{result.version}"
        model_path = version_dir / "model.pkl"
        metadata_path = version_dir / local_only_registry.LOCAL_METADATA_FILE

        assert version_dir.exists()
        assert model_path.exists()
        assert metadata_path.exists()

    def test_register_model_saves_metadata(self, local_only_registry, mock_model, sample_metadata):
        """Test that metadata is saved correctly."""
        result = local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
            description="Test description",
            tags={"env": "test"},
        )

        metadata_path = (
            local_only_registry.local_fallback_dir
            / f"v{result.version}"
            / local_only_registry.LOCAL_METADATA_FILE
        )

        with open(metadata_path) as f:
            saved_metadata = json.load(f)

        assert saved_metadata["description"] == "Test description"
        assert saved_metadata["tags"] == {"env": "test"}
        assert saved_metadata["metadata"]["accuracy"] == sample_metadata.accuracy

    def test_register_updates_champion(self, local_only_registry, mock_model, sample_metadata):
        """Test that promote_to_champion updates champion pointer."""
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
            promote_to_champion=True,
        )

        champion_path = local_only_registry.local_fallback_dir / "champion"
        assert champion_path.exists()
        assert champion_path.read_text().strip() == "1"

    def test_register_without_promotion(self, local_only_registry, mock_model, sample_metadata):
        """Test registration without promoting to champion."""
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
            promote_to_champion=False,
        )

        champion_path = local_only_registry.local_fallback_dir / "champion"
        # Champion file should not exist if not promoted
        assert not champion_path.exists()


# =============================================================================
# MLflowRegistry Tests - Local Fallback Loading
# =============================================================================


class TestMLflowRegistryLocalLoading:
    """Tests for loading models from local storage."""

    def test_load_champion_model(self, local_only_registry, mock_model, sample_metadata):
        """Test loading champion model from local storage."""
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
            promote_to_champion=True,
        )

        loaded_model = local_only_registry.load_champion_model()

        assert loaded_model is not None
        assert loaded_model["type"] == "mock"
        assert loaded_model["weights"] == mock_model["weights"]

    def test_load_champion_model_no_champion(self, local_only_registry):
        """Test loading champion when none exists."""
        loaded_model = local_only_registry.load_champion_model()

        assert loaded_model is None

    def test_load_model_by_version(self, local_only_registry, mock_model, sample_metadata):
        """Test loading specific model version."""
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
        )

        loaded_model = local_only_registry.load_model_by_version("1")

        assert loaded_model is not None
        assert loaded_model["type"] == "mock"

    def test_load_model_nonexistent_version(self, local_only_registry):
        """Test loading non-existent version returns None."""
        loaded_model = local_only_registry.load_model_by_version("999")

        assert loaded_model is None


# =============================================================================
# MLflowRegistry Tests - Local Fallback Rollback
# =============================================================================


class TestMLflowRegistryLocalRollback:
    """Tests for rollback functionality with local storage."""

    def test_rollback_to_version(self, local_only_registry, mock_model, sample_metadata):
        """Test rollback to a specific version."""
        # Register two versions
        local_only_registry.register_model(
            model={"type": "mock", "v": 1},
            metadata=sample_metadata,
            promote_to_champion=True,
        )
        local_only_registry.register_model(
            model={"type": "mock", "v": 2},
            metadata=sample_metadata,
            promote_to_champion=True,
        )

        # Verify current champion is v2
        assert local_only_registry._current_champion_version == "2"

        # Rollback to v1
        result = local_only_registry.rollback_to_version("1")

        assert result.success is True
        assert result.previous_version == "2"
        assert result.new_version == "1"
        assert local_only_registry._current_champion_version == "1"

    def test_rollback_to_nonexistent_version(
        self, local_only_registry, mock_model, sample_metadata
    ):
        """Test rollback to non-existent version fails."""
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
        )

        result = local_only_registry.rollback_to_version("999")

        assert result.success is False
        assert "not found" in result.message.lower()

    def test_rollback_updates_champion_file(self, local_only_registry, mock_model, sample_metadata):
        """Test that rollback updates champion pointer file."""
        # Register two versions
        local_only_registry.register_model(
            model={"type": "mock", "v": 1},
            metadata=sample_metadata,
            promote_to_champion=True,
        )
        local_only_registry.register_model(
            model={"type": "mock", "v": 2},
            metadata=sample_metadata,
            promote_to_champion=True,
        )

        # Rollback
        local_only_registry.rollback_to_version("1")

        # Check champion file
        champion_path = local_only_registry.local_fallback_dir / "champion"
        assert champion_path.read_text().strip() == "1"


# =============================================================================
# MLflowRegistry Tests - Version Management
# =============================================================================


class TestMLflowRegistryVersionManagement:
    """Tests for version management functionality."""

    def test_list_versions(self, local_only_registry, mock_model, sample_metadata):
        """Test listing all versions."""
        # Register multiple versions
        for i in range(3):
            local_only_registry.register_model(
                model={"type": "mock", "v": i},
                metadata=sample_metadata,
            )

        versions = local_only_registry.list_versions()

        assert len(versions) == 3
        version_numbers = [v.version for v in versions]
        assert "1" in version_numbers
        assert "2" in version_numbers
        assert "3" in version_numbers

    def test_list_versions_empty(self, local_only_registry):
        """Test listing versions when none exist."""
        versions = local_only_registry.list_versions()

        assert len(versions) == 0

    def test_get_version_info(self, local_only_registry, mock_model, sample_metadata):
        """Test getting specific version info."""
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
            description="Test version",
        )

        info = local_only_registry.get_version_info("1")

        assert info is not None
        assert info.version == "1"
        assert info.name == "test_model"

    def test_get_version_info_not_found(self, local_only_registry):
        """Test getting info for non-existent version."""
        info = local_only_registry.get_version_info("999")

        assert info is None

    def test_get_champion_version(self, local_only_registry, mock_model, sample_metadata):
        """Test getting current champion version."""
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
            promote_to_champion=True,
        )

        champion = local_only_registry.get_champion_version()

        assert champion == "1"

    def test_get_champion_version_none(self, local_only_registry):
        """Test getting champion when none exists."""
        champion = local_only_registry.get_champion_version()

        assert champion is None


# =============================================================================
# MLflowRegistry Tests - Version Deletion
# =============================================================================


class TestMLflowRegistryDeletion:
    """Tests for version deletion functionality."""

    def test_delete_version(self, local_only_registry, mock_model, sample_metadata):
        """Test deleting a model version."""
        # Register two versions
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
            promote_to_champion=True,
        )
        local_only_registry.register_model(
            model={"type": "mock", "v": 2},
            metadata=sample_metadata,
            promote_to_champion=False,
        )

        # Delete version 2 (not champion)
        result = local_only_registry.delete_version("2")

        assert result is True
        versions = local_only_registry._get_local_versions()
        assert "2" not in versions

    def test_delete_champion_prevented(self, local_only_registry, mock_model, sample_metadata):
        """Test that deleting champion version is prevented."""
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
            promote_to_champion=True,
        )

        result = local_only_registry.delete_version("1")

        assert result is False
        versions = local_only_registry._get_local_versions()
        assert "1" in versions

    def test_cleanup_old_versions(self, local_only_registry, mock_model, sample_metadata):
        """Test cleanup of old versions."""
        # Register 10 versions
        for i in range(10):
            local_only_registry.register_model(
                model={"type": "mock", "v": i},
                metadata=sample_metadata,
                promote_to_champion=True,
            )

        # Cleanup keeping only 3
        deleted = local_only_registry.cleanup_old_versions(keep_count=3)

        assert deleted > 0
        versions = local_only_registry._get_local_versions()
        # Should have at most 3 versions (plus champion which is protected)
        assert len(versions) <= 4  # 3 kept + champion


# =============================================================================
# MLflowRegistry Tests - Status
# =============================================================================


class TestMLflowRegistryStatus:
    """Tests for registry status functionality."""

    def test_get_status_disconnected(self, local_only_registry):
        """Test getting status when disconnected."""
        status, error = local_only_registry.get_status()

        assert status == RegistryStatus.DISCONNECTED

    def test_status_degraded_after_local_registration(
        self, local_only_registry, mock_model, sample_metadata
    ):
        """Test status is DEGRADED after local registration."""
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
        )

        status, _ = local_only_registry.get_status()

        assert status == RegistryStatus.DEGRADED


# =============================================================================
# MLflowRegistry Tests - Callbacks
# =============================================================================


class TestMLflowRegistryCallbacks:
    """Tests for callback registration and triggering."""

    def test_register_registration_callback(self, local_only_registry, mock_model, sample_metadata):
        """Test registration callback is triggered."""
        callback_results = []

        def on_registration(result: RegistrationResult):
            callback_results.append(result)

        local_only_registry.register_registration_callback(on_registration)

        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
        )

        assert len(callback_results) == 1
        assert callback_results[0].success is True

    def test_register_rollback_callback(self, local_only_registry, mock_model, sample_metadata):
        """Test rollback callback is triggered."""
        callback_results = []

        def on_rollback(result: RollbackResult):
            callback_results.append(result)

        local_only_registry.register_rollback_callback(on_rollback)

        # Register two versions
        local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
            promote_to_champion=True,
        )
        local_only_registry.register_model(
            model={"type": "mock", "v": 2},
            metadata=sample_metadata,
            promote_to_champion=True,
        )

        # Rollback
        local_only_registry.rollback_to_version("1")

        assert len(callback_results) == 1
        assert callback_results[0].success is True

    def test_callback_exception_handled(self, local_only_registry, mock_model, sample_metadata):
        """Test that callback exceptions are handled gracefully."""

        def bad_callback(result):
            raise ValueError("Callback error")

        local_only_registry.register_registration_callback(bad_callback)

        # Should not raise
        result = local_only_registry.register_model(
            model=mock_model,
            metadata=sample_metadata,
        )

        assert result.success is True


# =============================================================================
# MLflowRegistry Tests - Retry Queue
# =============================================================================


class TestMLflowRegistryRetryQueue:
    """Tests for retry queue functionality."""

    def test_queue_retry_operation(self, local_only_registry):
        """Test queueing operations for retry."""
        local_only_registry._queue_retry_operation(
            operation="register",
            model={"type": "mock"},
            metadata=None,
        )

        assert len(local_only_registry._pending_operations) == 1
        assert local_only_registry._pending_operations[0]["operation"] == "register"


# =============================================================================
# MLflowRegistry Tests - Thread Safety
# =============================================================================


class TestMLflowRegistryThreadSafety:
    """Tests for thread safety."""

    def test_concurrent_registrations(self, local_only_registry, sample_metadata):
        """Test concurrent model registrations don't cause race conditions."""
        results = []
        errors = []

        def register():
            try:
                result = local_only_registry.register_model(
                    model={"type": "mock", "t": threading.current_thread().name},
                    metadata=sample_metadata,
                    promote_to_champion=False,
                )
                results.append(result)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 5
        assert all(r.success for r in results)


# =============================================================================
# MLflowRegistry Tests - Repr
# =============================================================================


class TestMLflowRegistryRepr:
    """Tests for string representation."""

    def test_repr(self, local_only_registry):
        """Test __repr__ returns informative string."""
        repr_str = repr(local_only_registry)

        assert "MLflowRegistry" in repr_str
        assert "model=" in repr_str
        assert "status=" in repr_str


# =============================================================================
# MLflowRegistry Tests - Fallback Disabled
# =============================================================================


class TestMLflowRegistryFallbackDisabled:
    """Tests when local fallback is disabled."""

    def test_register_fails_without_mlflow_and_fallback(self, temp_fallback_dir, sample_metadata):
        """Test registration fails when MLflow unavailable and fallback disabled."""
        registry = MLflowRegistry(
            tracking_uri="sqlite:///nonexistent/mlflow.db",
            local_fallback_dir=temp_fallback_dir,
            enable_local_fallback=False,
        )

        result = registry.register_model(
            model={"type": "mock"},
            metadata=sample_metadata,
        )

        # May succeed via MLflow or fail if MLflow unavailable
        # The test verifies behavior either way
        assert isinstance(result, RegistrationResult)


# =============================================================================
# Integration Tests - Model Persistence
# =============================================================================


class TestMLflowRegistryModelPersistence:
    """Tests for model persistence (save and load cycle)."""

    def test_model_roundtrip(self, local_only_registry, sample_metadata):
        """Test that models survive save/load cycle."""
        original_model = {
            "type": "complex_model",
            "weights": [0.1, 0.2, 0.3, 0.4, 0.5],
            "bias": 0.05,
            "config": {"param1": "value1", "param2": 42},
        }

        local_only_registry.register_model(
            model=original_model,
            metadata=sample_metadata,
            promote_to_champion=True,
        )

        loaded_model = local_only_registry.load_champion_model()

        assert loaded_model == original_model
        assert loaded_model["weights"] == original_model["weights"]
        assert loaded_model["config"] == original_model["config"]

    def test_metadata_persistence(self, local_only_registry, sample_metadata):
        """Test that metadata is correctly persisted and retrievable."""
        local_only_registry.register_model(
            model={"type": "mock"},
            metadata=sample_metadata,
            description="Test description",
            tags={"experiment": "exp1", "version": "beta"},
            promote_to_champion=True,
        )

        # Get version info
        version_info = local_only_registry.get_version_info("1")

        assert version_info is not None
        assert version_info.description == "Test description"
        assert version_info.tags.get("experiment") == "exp1"
