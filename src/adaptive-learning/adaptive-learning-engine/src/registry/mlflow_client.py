"""
Adaptive Learning Engine - MLflow Registry Client
Constitutional Hash: cdd01ef066bc6cf2

MLflow integration for model versioning, rollback, and lifecycle management.
Provides resilient model persistence with fallback to local storage.
"""

import asyncio
import json
import logging
import os
import pickle
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    from src.core.shared.security.deserialization import safe_pickle_load
except ImportError:
    safe_pickle_load = None

logger = logging.getLogger(__name__)


class ModelStage(Enum):
    """MLflow model lifecycle stages."""

    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


class RegistryStatus(Enum):
    """Status of the MLflow registry connection."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"  # Using local fallback


@dataclass
class ModelVersion:
    """Information about a registered model version."""

    version: str
    name: str
    stage: ModelStage
    description: str
    tags: Dict[str, str]
    creation_timestamp: float
    last_updated_timestamp: float
    run_id: Optional[str] = None
    source: Optional[str] = None
    aliases: List[str] = field(default_factory=list)


@dataclass
class RegistrationResult:
    """Result from model registration."""

    success: bool
    version: Optional[str]
    model_uri: Optional[str]
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class RollbackResult:
    """Result from model rollback."""

    success: bool
    previous_version: Optional[str]
    new_version: Optional[str]
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ModelMetadata:
    """Metadata logged with model versions."""

    accuracy: float
    drift_score: float
    sample_count: int
    model_type: str
    learning_rate: float
    l2_regularization: float
    algorithm: str
    training_timestamp: float
    extra: Dict[str, Any] = field(default_factory=dict)


class MLflowRegistry:
    """MLflow model registry client for versioning and rollback.

    Provides resilient model persistence with:
    - MLflow registry for production model management
    - Local disk fallback when MLflow is unavailable
    - Automatic retry for failed registry operations
    - Champion/challenger alias management
    - Version history tracking

    Example usage:
        registry = MLflowRegistry()

        # Register a new model version
        result = registry.register_model(
            model=learner.model,
            metadata=ModelMetadata(
                accuracy=0.92,
                drift_score=0.15,
                sample_count=1000,
                model_type="logistic_regression",
                learning_rate=0.1,
                l2_regularization=0.01,
                algorithm="LogisticRegression",
                training_timestamp=time.time(),
            ),
        )

        # Load the champion model
        model = registry.load_champion_model()

        # Rollback to a previous version
        result = registry.rollback_to_version("2")
    """

    # Default paths
    DEFAULT_TRACKING_URI = "sqlite:///mlruns/mlflow.db"
    DEFAULT_MODEL_NAME = "governance_model"
    DEFAULT_CHAMPION_ALIAS = "champion"
    DEFAULT_CHALLENGER_ALIAS = "challenger"

    # Local fallback paths
    LOCAL_FALLBACK_DIR = "model_cache"
    LOCAL_METADATA_FILE = "metadata.json"

    # Retry settings
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 1.0

    def __init__(
        self,
        tracking_uri: Optional[str] = None,
        model_name: Optional[str] = None,
        champion_alias: Optional[str] = None,
        challenger_alias: Optional[str] = None,
        local_fallback_dir: Optional[str] = None,
        enable_local_fallback: bool = True,
    ) -> None:
        """Initialize the MLflow registry client.

        Args:
            tracking_uri: MLflow tracking URI. Defaults to sqlite:///mlruns/mlflow.db.
            model_name: Name of the registered model. Defaults to "governance_model".
            champion_alias: Alias for the production model. Defaults to "champion".
            challenger_alias: Alias for the candidate model. Defaults to "challenger".
            local_fallback_dir: Directory for local model cache. Defaults to "model_cache".
            enable_local_fallback: Whether to enable local disk fallback.
        """
        self.tracking_uri = tracking_uri or self.DEFAULT_TRACKING_URI
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.champion_alias = champion_alias or self.DEFAULT_CHAMPION_ALIAS
        self.challenger_alias = challenger_alias or self.DEFAULT_CHALLENGER_ALIAS
        self.local_fallback_dir = Path(local_fallback_dir or self.LOCAL_FALLBACK_DIR)
        self.enable_local_fallback = enable_local_fallback

        # Thread safety
        self._lock = threading.RLock()

        # Connection status
        self._status = RegistryStatus.DISCONNECTED
        self._last_error: Optional[str] = None
        self._last_successful_connection: Optional[float] = None

        # Version tracking (in-memory cache)
        self._version_cache: Dict[str, ModelVersion] = {}
        self._current_champion_version: Optional[str] = None

        # MLflow client (lazy initialization)
        self._mlflow_client: Optional[Any] = None
        self._mlflow_initialized = False

        # Callbacks for registry events
        self._on_registration_callbacks: List[Callable[[RegistrationResult], None]] = []
        self._on_rollback_callbacks: List[Callable[[RollbackResult], None]] = []

        # Pending operations queue for retry
        self._pending_operations: List[Dict[str, Any]] = []
        self._retry_lock = threading.Lock()

        logger.info(
            "MLflowRegistry initialized",
            extra={
                "tracking_uri": self.tracking_uri,
                "model_name": self.model_name,
                "champion_alias": self.champion_alias,
                "enable_local_fallback": self.enable_local_fallback,
            },
        )

    def _initialize_mlflow(self) -> bool:
        """Initialize MLflow connection.

        Returns:
            True if initialization successful, False otherwise.
        """
        if self._mlflow_initialized:
            return self._status == RegistryStatus.CONNECTED

        try:
            import mlflow
            from mlflow.tracking import MlflowClient

            # Set tracking URI
            mlflow.set_tracking_uri(self.tracking_uri)

            # Create the MLflow client
            self._mlflow_client = MlflowClient()

            # Test connection by trying to list registered models
            # This will create tables if using SQLite
            try:
                # Try to get the registered model (may not exist yet)
                self._mlflow_client.search_registered_models(max_results=1)
            except Exception:
                # Model doesn't exist yet, that's fine
                pass

            self._status = RegistryStatus.CONNECTED
            self._last_successful_connection = time.time()
            self._mlflow_initialized = True

            logger.info("MLflow connection established", extra={"tracking_uri": self.tracking_uri})
            return True

        except ImportError as e:
            logger.error(f"MLflow not installed: {e}")
            self._status = RegistryStatus.DISCONNECTED
            self._last_error = f"MLflow not installed: {e}"
            return False

        except Exception as e:
            logger.error(f"Failed to initialize MLflow: {e}")
            self._status = RegistryStatus.DISCONNECTED
            self._last_error = str(e)

            if self.enable_local_fallback:
                self._status = RegistryStatus.DEGRADED
                logger.warning("Falling back to local model storage")

            return False

    def _ensure_local_fallback_dir(self) -> Path:
        """Ensure local fallback directory exists.

        Returns:
            Path to the fallback directory.
        """
        self.local_fallback_dir.mkdir(parents=True, exist_ok=True)
        return self.local_fallback_dir

    def register_model(
        self,
        model: Any,
        metadata: ModelMetadata,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        promote_to_champion: bool = True,
    ) -> RegistrationResult:
        """Register a new model version in the registry.

        Args:
            model: The model object to register (River pipeline or pickled object).
            metadata: Metadata to log with the model version.
            description: Optional description for this version.
            tags: Optional tags for this version.
            promote_to_champion: Whether to promote this version to champion.

        Returns:
            RegistrationResult with success status and version info.
        """
        with self._lock:
            timestamp = time.time()

            # Try MLflow registration first
            if self._initialize_mlflow() and self._status == RegistryStatus.CONNECTED:
                result = self._register_with_mlflow(
                    model=model,
                    metadata=metadata,
                    description=description,
                    tags=tags,
                    promote_to_champion=promote_to_champion,
                )

                if result.success:
                    # Notify callbacks
                    for callback in self._on_registration_callbacks:
                        try:
                            callback(result)
                        except Exception as e:
                            logger.warning(f"Registration callback error: {e}")

                    return result

                # MLflow failed, fall through to local fallback
                logger.warning("MLflow registration failed, using local fallback")

            # Use local fallback
            if self.enable_local_fallback:
                result = self._register_locally(
                    model=model,
                    metadata=metadata,
                    description=description,
                    tags=tags,
                    promote_to_champion=promote_to_champion,
                )

                # Queue for retry with MLflow
                self._queue_retry_operation(
                    operation="register",
                    model=model,
                    metadata=metadata,
                    description=description,
                    tags=tags,
                    promote_to_champion=promote_to_champion,
                )

                # Notify callbacks
                for callback in self._on_registration_callbacks:
                    try:
                        callback(result)
                    except Exception as e:
                        logger.warning(f"Registration callback error: {e}")

                return result

            return RegistrationResult(
                success=False,
                version=None,
                model_uri=None,
                message="MLflow unavailable and local fallback disabled",
                timestamp=timestamp,
            )

    def _register_with_mlflow(
        self,
        model: Any,
        metadata: ModelMetadata,
        description: Optional[str],
        tags: Optional[Dict[str, str]],
        promote_to_champion: bool,
    ) -> RegistrationResult:
        """Register model with MLflow registry.

        Args:
            model: Model to register.
            metadata: Model metadata.
            description: Version description.
            tags: Version tags.
            promote_to_champion: Whether to set champion alias.

        Returns:
            RegistrationResult with MLflow version info.
        """
        import mlflow

        timestamp = time.time()

        try:
            # Start a new MLflow run
            with mlflow.start_run() as run:
                # Log parameters
                mlflow.log_param("algorithm", metadata.algorithm)
                mlflow.log_param("model_type", metadata.model_type)
                mlflow.log_param("learning_rate", metadata.learning_rate)
                mlflow.log_param("l2_regularization", metadata.l2_regularization)

                # Log metrics
                mlflow.log_metric("accuracy", metadata.accuracy)
                mlflow.log_metric("drift_score", metadata.drift_score)
                mlflow.log_metric("sample_count", metadata.sample_count)
                mlflow.log_metric("training_timestamp", metadata.training_timestamp)

                # Log extra metrics
                for key, value in metadata.extra.items():
                    if isinstance(value, (int, float)):
                        mlflow.log_metric(key, value)
                    else:
                        mlflow.log_param(key, str(value))

                # Log tags
                if tags:
                    mlflow.set_tags(tags)

                # Save model as artifact
                # Create a temporary directory for the model
                with tempfile.TemporaryDirectory() as tmpdir:
                    model_path = os.path.join(tmpdir, "model.pkl")
                    with open(model_path, "wb") as f:
                        pickle.dump(model, f)

                    # Log the model artifact
                    mlflow.log_artifact(model_path, artifact_path="model")

                model_uri = f"runs:/{run.info.run_id}/model"

            # Register the model
            try:
                result = mlflow.register_model(model_uri, self.model_name)
                version = result.version
            except Exception:
                # Model might not be registered yet, create it

                try:
                    self._mlflow_client.create_registered_model(
                        name=self.model_name,
                        description=description or "Governance online learning model",
                    )
                    result = mlflow.register_model(model_uri, self.model_name)
                    version = result.version
                except Exception:
                    # Model already exists, retry registration
                    result = mlflow.register_model(model_uri, self.model_name)
                    version = result.version

            # Update description if provided
            if description:
                self._mlflow_client.update_model_version(
                    name=self.model_name,
                    version=version,
                    description=description,
                )

            # Promote to production and set champion alias
            if promote_to_champion:
                # Transition to Production stage
                self._mlflow_client.transition_model_version_stage(
                    name=self.model_name,
                    version=version,
                    stage="Production",
                    archive_existing_versions=True,
                )

                # Set champion alias
                try:
                    self._mlflow_client.set_registered_model_alias(
                        name=self.model_name,
                        alias=self.champion_alias,
                        version=version,
                    )
                except Exception as alias_error:
                    # Alias API might not be available in older MLflow versions
                    logger.warning(f"Could not set alias (older MLflow?): {alias_error}")

                self._current_champion_version = version

            # Update version cache
            self._version_cache[version] = ModelVersion(
                version=version,
                name=self.model_name,
                stage=ModelStage.PRODUCTION if promote_to_champion else ModelStage.NONE,
                description=description or "",
                tags=tags or {},
                creation_timestamp=timestamp,
                last_updated_timestamp=timestamp,
                run_id=run.info.run_id,
                source=model_uri,
                aliases=[self.champion_alias] if promote_to_champion else [],
            )

            logger.info(
                "Model registered with MLflow",
                extra={
                    "version": version,
                    "accuracy": metadata.accuracy,
                    "promoted": promote_to_champion,
                },
            )

            return RegistrationResult(
                success=True,
                version=version,
                model_uri=model_uri,
                message=f"Model registered as version {version}",
                timestamp=timestamp,
            )

        except Exception as e:
            logger.error(f"MLflow registration failed: {e}")
            return RegistrationResult(
                success=False,
                version=None,
                model_uri=None,
                message=f"MLflow registration failed: {e}",
                timestamp=timestamp,
            )

    def _register_locally(
        self,
        model: Any,
        metadata: ModelMetadata,
        description: Optional[str],
        tags: Optional[Dict[str, str]],
        promote_to_champion: bool,
    ) -> RegistrationResult:
        """Register model to local disk as fallback.

        Args:
            model: Model to save.
            metadata: Model metadata.
            description: Version description.
            tags: Version tags.
            promote_to_champion: Whether to mark as champion.

        Returns:
            RegistrationResult with local version info.
        """
        timestamp = time.time()

        try:
            fallback_dir = self._ensure_local_fallback_dir()

            # Generate version number
            existing_versions = self._get_local_versions()
            version = str(max([0] + [int(v) for v in existing_versions]) + 1)

            # Create version directory
            version_dir = fallback_dir / f"v{version}"
            version_dir.mkdir(parents=True, exist_ok=True)

            # Save model
            model_path = version_dir / "model.pkl"
            with open(model_path, "wb") as f:
                pickle.dump(model, f)

            # Save metadata
            metadata_dict = {
                "version": version,
                "name": self.model_name,
                "stage": (
                    ModelStage.PRODUCTION.value if promote_to_champion else ModelStage.NONE.value
                ),
                "description": description or "",
                "tags": tags or {},
                "creation_timestamp": timestamp,
                "last_updated_timestamp": timestamp,
                "is_champion": promote_to_champion,
                "metadata": {
                    "accuracy": metadata.accuracy,
                    "drift_score": metadata.drift_score,
                    "sample_count": metadata.sample_count,
                    "model_type": metadata.model_type,
                    "learning_rate": metadata.learning_rate,
                    "l2_regularization": metadata.l2_regularization,
                    "algorithm": metadata.algorithm,
                    "training_timestamp": metadata.training_timestamp,
                    "extra": metadata.extra,
                },
            }

            metadata_path = version_dir / self.LOCAL_METADATA_FILE
            with open(metadata_path, "w") as f:
                json.dump(metadata_dict, f, indent=2)

            # Update champion pointer if needed
            if promote_to_champion:
                champion_path = fallback_dir / "champion"
                champion_path.write_text(version)
                self._current_champion_version = version

            # Update version cache
            self._version_cache[version] = ModelVersion(
                version=version,
                name=self.model_name,
                stage=ModelStage.PRODUCTION if promote_to_champion else ModelStage.NONE,
                description=description or "",
                tags=tags or {},
                creation_timestamp=timestamp,
                last_updated_timestamp=timestamp,
                source=str(model_path),
                aliases=[self.champion_alias] if promote_to_champion else [],
            )

            self._status = RegistryStatus.DEGRADED

            logger.info(
                "Model saved to local fallback",
                extra={
                    "version": version,
                    "path": str(version_dir),
                    "promoted": promote_to_champion,
                },
            )

            return RegistrationResult(
                success=True,
                version=version,
                model_uri=str(model_path),
                message=f"Model saved locally as version {version} (MLflow unavailable)",
                timestamp=timestamp,
            )

        except Exception as e:
            logger.error(f"Local registration failed: {e}")
            return RegistrationResult(
                success=False,
                version=None,
                model_uri=None,
                message=f"Local registration failed: {e}",
                timestamp=timestamp,
            )

    def _get_local_versions(self) -> List[str]:
        """Get list of locally stored version numbers.

        Returns:
            List of version strings.
        """
        if not self.local_fallback_dir.exists():
            return []

        versions = []
        for path in self.local_fallback_dir.iterdir():
            if path.is_dir() and path.name.startswith("v"):
                try:
                    version = path.name[1:]  # Remove 'v' prefix
                    int(version)  # Validate it's a number
                    versions.append(version)
                except ValueError:
                    pass
        return versions

    def load_champion_model(self) -> Optional[Any]:
        """Load the current champion model.

        Returns:
            The loaded model object, or None if no champion exists.
        """
        with self._lock:
            # Try MLflow first
            if self._initialize_mlflow() and self._status == RegistryStatus.CONNECTED:
                model = self._load_from_mlflow_alias(self.champion_alias)
                if model is not None:
                    return model

            # Try local fallback
            if self.enable_local_fallback:
                return self._load_local_champion()

            return None

    def load_model_by_version(self, version: str) -> Optional[Any]:
        """Load a specific model version.

        Args:
            version: Version number to load.

        Returns:
            The loaded model object, or None if version doesn't exist.
        """
        with self._lock:
            # Try MLflow first
            if self._initialize_mlflow() and self._status == RegistryStatus.CONNECTED:
                model = self._load_from_mlflow_version(version)
                if model is not None:
                    return model

            # Try local fallback
            if self.enable_local_fallback:
                return self._load_local_version(version)

            return None

    def _load_from_mlflow_alias(self, alias: str) -> Optional[Any]:
        """Load model from MLflow by alias.

        Args:
            alias: Model alias (e.g., "champion").

        Returns:
            Loaded model or None.
        """
        try:
            import mlflow

            model_uri = f"models:/{self.model_name}@{alias}"
            model_path = mlflow.artifacts.download_artifacts(artifact_uri=f"{model_uri}/model.pkl")

            with open(model_path, "rb") as f:
                if safe_pickle_load:
                    model = safe_pickle_load(f)
                else:
                    model = pickle.load(f)

            return model

        except Exception as e:
            logger.warning(f"Failed to load model by alias {alias}: {e}")
            return None

    def _load_from_mlflow_version(self, version: str) -> Optional[Any]:
        """Load model from MLflow by version.

        Args:
            version: Model version number.

        Returns:
            Loaded model or None.
        """
        try:
            import mlflow

            model_uri = f"models:/{self.model_name}/{version}"
            model_path = mlflow.artifacts.download_artifacts(artifact_uri=f"{model_uri}/model.pkl")

            with open(model_path, "rb") as f:
                if safe_pickle_load:
                    model = safe_pickle_load(f)
                else:
                    model = pickle.load(f)

            return model

        except Exception as e:
            logger.warning(f"Failed to load model version {version}: {e}")
            return None

    def _load_local_champion(self) -> Optional[Any]:
        """Load champion model from local storage.

        Returns:
            Loaded model or None.
        """
        try:
            champion_path = self.local_fallback_dir / "champion"
            if not champion_path.exists():
                return None

            version = champion_path.read_text().strip()
            return self._load_local_version(version)

        except Exception as e:
            logger.warning(f"Failed to load local champion: {e}")
            return None

    def _load_local_version(self, version: str) -> Optional[Any]:
        """Load model from local storage by version.

        Args:
            version: Version number.

        Returns:
            Loaded model or None.
        """
        try:
            version_dir = self.local_fallback_dir / f"v{version}"
            model_path = version_dir / "model.pkl"

            if not model_path.exists():
                return None

            with open(model_path, "rb") as f:
                if safe_pickle_load:
                    model = safe_pickle_load(f)
                else:
                    model = pickle.load(f)

            return model

        except Exception as e:
            logger.warning(f"Failed to load local version {version}: {e}")
            return None

    def rollback_to_version(self, version: str) -> RollbackResult:
        """Rollback to a specific model version.

        Args:
            version: Version number to rollback to.

        Returns:
            RollbackResult with status and version info.
        """
        with self._lock:
            timestamp = time.time()
            previous_version = self._current_champion_version

            # Check if version exists
            if not self._version_exists(version):
                available_versions = self.list_versions()
                version_list = [v.version for v in available_versions]
                return RollbackResult(
                    success=False,
                    previous_version=previous_version,
                    new_version=None,
                    message=f"Version {version} not found. Available versions: {version_list}",
                    timestamp=timestamp,
                )

            # Try MLflow rollback first
            if self._initialize_mlflow() and self._status == RegistryStatus.CONNECTED:
                result = self._rollback_mlflow(version, previous_version)
                if result.success:
                    # Notify callbacks
                    for callback in self._on_rollback_callbacks:
                        try:
                            callback(result)
                        except Exception as e:
                            logger.warning(f"Rollback callback error: {e}")
                    return result

            # Try local rollback
            if self.enable_local_fallback:
                result = self._rollback_local(version, previous_version)
                # Notify callbacks
                for callback in self._on_rollback_callbacks:
                    try:
                        callback(result)
                    except Exception as e:
                        logger.warning(f"Rollback callback error: {e}")
                return result

            return RollbackResult(
                success=False,
                previous_version=previous_version,
                new_version=None,
                message="Registry unavailable and local fallback disabled",
                timestamp=timestamp,
            )

    def _rollback_mlflow(self, version: str, previous_version: Optional[str]) -> RollbackResult:
        """Rollback using MLflow registry.

        Args:
            version: Target version.
            previous_version: Current champion version.

        Returns:
            RollbackResult.
        """
        timestamp = time.time()

        try:
            # Transition target version to Production
            self._mlflow_client.transition_model_version_stage(
                name=self.model_name,
                version=version,
                stage="Production",
                archive_existing_versions=True,
            )

            # Update champion alias
            try:
                self._mlflow_client.set_registered_model_alias(
                    name=self.model_name,
                    alias=self.champion_alias,
                    version=version,
                )
            except Exception as alias_error:
                logger.warning(f"Could not set alias: {alias_error}")

            self._current_champion_version = version

            logger.info(
                "Model rolled back via MLflow",
                extra={
                    "previous_version": previous_version,
                    "new_version": version,
                },
            )

            return RollbackResult(
                success=True,
                previous_version=previous_version,
                new_version=version,
                message=f"Rolled back from version {previous_version} to {version}",
                timestamp=timestamp,
            )

        except Exception as e:
            logger.error(f"MLflow rollback failed: {e}")
            return RollbackResult(
                success=False,
                previous_version=previous_version,
                new_version=None,
                message=f"MLflow rollback failed: {e}",
                timestamp=timestamp,
            )

    def _rollback_local(self, version: str, previous_version: Optional[str]) -> RollbackResult:
        """Rollback using local storage.

        Args:
            version: Target version.
            previous_version: Current champion version.

        Returns:
            RollbackResult.
        """
        timestamp = time.time()

        try:
            # Update champion pointer
            champion_path = self.local_fallback_dir / "champion"
            champion_path.write_text(version)
            self._current_champion_version = version

            # Update version cache
            if version in self._version_cache:
                self._version_cache[version].stage = ModelStage.PRODUCTION
                self._version_cache[version].aliases = [self.champion_alias]

            if previous_version and previous_version in self._version_cache:
                self._version_cache[previous_version].stage = ModelStage.ARCHIVED
                if self.champion_alias in self._version_cache[previous_version].aliases:
                    self._version_cache[previous_version].aliases.remove(self.champion_alias)

            logger.info(
                "Model rolled back via local storage",
                extra={
                    "previous_version": previous_version,
                    "new_version": version,
                },
            )

            return RollbackResult(
                success=True,
                previous_version=previous_version,
                new_version=version,
                message=f"Rolled back from version {previous_version} to {version} (local)",
                timestamp=timestamp,
            )

        except Exception as e:
            logger.error(f"Local rollback failed: {e}")
            return RollbackResult(
                success=False,
                previous_version=previous_version,
                new_version=None,
                message=f"Local rollback failed: {e}",
                timestamp=timestamp,
            )

    def _version_exists(self, version: str) -> bool:
        """Check if a version exists in registry or local storage.

        Args:
            version: Version to check.

        Returns:
            True if version exists.
        """
        # Check cache first
        if version in self._version_cache:
            return True

        # Check MLflow
        if self._status == RegistryStatus.CONNECTED:
            try:
                self._mlflow_client.get_model_version(self.model_name, version)
                return True
            except Exception:
                pass

        # Check local
        version_dir = self.local_fallback_dir / f"v{version}"
        return version_dir.exists()

    def list_versions(self) -> List[ModelVersion]:
        """List all model versions.

        Returns:
            List of ModelVersion objects.
        """
        with self._lock:
            versions = []

            # Get from MLflow
            if self._initialize_mlflow() and self._status == RegistryStatus.CONNECTED:
                try:
                    mlflow_versions = self._mlflow_client.search_model_versions(
                        f"name='{self.model_name}'"
                    )
                    for mv in mlflow_versions:
                        version = ModelVersion(
                            version=mv.version,
                            name=mv.name,
                            stage=ModelStage(mv.current_stage),
                            description=mv.description or "",
                            tags=mv.tags or {},
                            creation_timestamp=mv.creation_timestamp / 1000.0,
                            last_updated_timestamp=mv.last_updated_timestamp / 1000.0,
                            run_id=mv.run_id,
                            source=mv.source,
                            aliases=(
                                list(mv.aliases) if hasattr(mv, "aliases") and mv.aliases else []
                            ),
                        )
                        versions.append(version)
                        self._version_cache[version.version] = version
                except Exception as e:
                    logger.warning(f"Could not list MLflow versions: {e}")

            # Get from local storage
            if self.enable_local_fallback:
                for local_version in self._get_local_versions():
                    if local_version not in [v.version for v in versions]:
                        version_dir = self.local_fallback_dir / f"v{local_version}"
                        metadata_path = version_dir / self.LOCAL_METADATA_FILE

                        try:
                            with open(metadata_path) as f:
                                metadata = json.load(f)

                            version = ModelVersion(
                                version=local_version,
                                name=self.model_name,
                                stage=ModelStage(metadata.get("stage", "None")),
                                description=metadata.get("description", ""),
                                tags=metadata.get("tags", {}),
                                creation_timestamp=metadata.get("creation_timestamp", 0),
                                last_updated_timestamp=metadata.get("last_updated_timestamp", 0),
                                source=str(version_dir / "model.pkl"),
                                aliases=(
                                    [self.champion_alias] if metadata.get("is_champion") else []
                                ),
                            )
                            versions.append(version)
                        except Exception as e:
                            logger.warning(f"Error processing version {version_num}: {e}")

            # Sort by version number
            versions.sort(key=lambda v: int(v.version), reverse=True)
            return versions

    def get_version_info(self, version: str) -> Optional[ModelVersion]:
        """Get information about a specific version.

        Args:
            version: Version number.

        Returns:
            ModelVersion object or None if not found.
        """
        with self._lock:
            # Check cache
            if version in self._version_cache:
                return self._version_cache[version]

            # Refresh from registry
            versions = self.list_versions()
            for v in versions:
                if v.version == version:
                    return v

            return None

    def get_champion_version(self) -> Optional[str]:
        """Get the current champion version.

        Returns:
            Version string or None.
        """
        with self._lock:
            if self._current_champion_version:
                return self._current_champion_version

            # Try to find from versions list
            versions = self.list_versions()
            for v in versions:
                if self.champion_alias in v.aliases or v.stage == ModelStage.PRODUCTION:
                    self._current_champion_version = v.version
                    return v.version

            return None

    def get_status(self) -> Tuple[RegistryStatus, Optional[str]]:
        """Get registry connection status.

        Returns:
            Tuple of (status, error_message).
        """
        return self._status, self._last_error

    def _queue_retry_operation(self, operation: str, **kwargs: Any) -> None:
        """Queue an operation for async retry.

        Args:
            operation: Operation type (e.g., "register").
            **kwargs: Operation arguments.
        """
        with self._retry_lock:
            self._pending_operations.append(
                {
                    "operation": operation,
                    "timestamp": time.time(),
                    "attempts": 0,
                    "kwargs": kwargs,
                }
            )

    async def retry_pending_operations(self) -> int:
        """Retry pending operations asynchronously.

        Returns:
            Number of successful retries.
        """
        successful = 0

        with self._retry_lock:
            pending = list(self._pending_operations)
            self._pending_operations.clear()

        for op in pending:
            if op["attempts"] >= self.MAX_RETRY_ATTEMPTS:
                logger.warning(f"Giving up on operation after {op['attempts']} attempts")
                continue

            op["attempts"] += 1

            # Re-initialize MLflow
            if self._initialize_mlflow() and self._status == RegistryStatus.CONNECTED:
                if op["operation"] == "register":
                    result = self._register_with_mlflow(**op["kwargs"])
                    if result.success:
                        successful += 1
                        logger.info("Retry successful for registration")
                        continue

            # Re-queue for later
            with self._retry_lock:
                self._pending_operations.append(op)

            await asyncio.sleep(self.RETRY_DELAY_SECONDS)

        return successful

    def register_registration_callback(
        self, callback: Callable[[RegistrationResult], None]
    ) -> None:
        """Register a callback for model registration events.

        Args:
            callback: Function to call on registration.
        """
        self._on_registration_callbacks.append(callback)

    def register_rollback_callback(self, callback: Callable[[RollbackResult], None]) -> None:
        """Register a callback for rollback events.

        Args:
            callback: Function to call on rollback.
        """
        self._on_rollback_callbacks.append(callback)

    def delete_version(self, version: str) -> bool:
        """Delete a model version.

        Args:
            version: Version to delete.

        Returns:
            True if deletion successful.
        """
        with self._lock:
            # Prevent deleting champion
            if version == self._current_champion_version:
                logger.error("Cannot delete current champion version")
                return False

            success = False

            # Delete from MLflow
            if self._status == RegistryStatus.CONNECTED:
                try:
                    self._mlflow_client.delete_model_version(self.model_name, version)
                    success = True
                except Exception as e:
                    logger.warning(f"Could not delete from MLflow: {e}")

            # Delete from local
            if self.enable_local_fallback:
                version_dir = self.local_fallback_dir / f"v{version}"
                if version_dir.exists():
                    shutil.rmtree(version_dir)
                    success = True

            # Remove from cache
            self._version_cache.pop(version, None)

            return success

    def cleanup_old_versions(self, keep_count: int = 5) -> int:
        """Clean up old model versions, keeping the most recent.

        Args:
            keep_count: Number of versions to keep.

        Returns:
            Number of versions deleted.
        """
        with self._lock:
            versions = self.list_versions()
            deleted = 0

            # Keep the first N versions (already sorted newest first)
            for version in versions[keep_count:]:
                if version.version == self._current_champion_version:
                    continue  # Never delete champion

                if self.delete_version(version.version):
                    deleted += 1

            return deleted

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"MLflowRegistry("
            f"model={self.model_name}, "
            f"status={self._status.value}, "
            f"champion={self._current_champion_version})"
        )
