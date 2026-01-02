"""
ACGS-2 MLflow Versioning Module
Constitutional Hash: cdd01ef066bc6cf2

Implements MLflow model versioning with champion/candidate alias management
for governance models. Supports model registration, promotion, and rollback.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# Type checking imports for static analysis
if TYPE_CHECKING:
    from mlflow.tracking import MlflowClient

try:
    import mlflow
    from mlflow.exceptions import MlflowException
    from mlflow.tracking import MlflowClient as MlflowClientClass

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    MlflowException = Exception
    MlflowClientClass = None  # Placeholder for type hints

logger = logging.getLogger(__name__)


# Configuration defaults
DEFAULT_MODEL_NAME = os.getenv("MODEL_REGISTRY_NAME", "governance_impact_scorer")
DEFAULT_CHAMPION_ALIAS = os.getenv("CHAMPION_ALIAS", "champion")
DEFAULT_CANDIDATE_ALIAS = os.getenv("CANDIDATE_ALIAS", "candidate")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")


@dataclass
class ModelVersionInfo:
    """Information about a registered model version."""

    name: str
    version: int
    aliases: List[str]
    run_id: str
    status: str
    creation_timestamp: datetime
    description: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    tags: Optional[Dict[str, str]] = None


@dataclass
class RegistrationResult:
    """Result of a model registration operation."""

    success: bool
    model_name: str
    version: Optional[int] = None
    run_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class RollbackResult:
    """Result of a model rollback operation."""

    success: bool
    previous_version: Optional[int] = None
    new_version: Optional[int] = None
    alias: str = DEFAULT_CHAMPION_ALIAS
    error_message: Optional[str] = None


class MLflowVersionManager:
    """
    Manages MLflow model versioning with alias-based model promotion.

    Uses champion/candidate aliases instead of deprecated stages:
    - champion: Production model serving majority of traffic
    - candidate: Testing model for A/B experiments

    Provides rollback capabilities via alias switching.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        tracking_uri: Optional[str] = None,
        champion_alias: str = DEFAULT_CHAMPION_ALIAS,
        candidate_alias: str = DEFAULT_CANDIDATE_ALIAS,
    ):
        """
        Initialize the MLflow version manager.

        Args:
            model_name: Name for the model registry
            tracking_uri: MLflow tracking server URI
            champion_alias: Alias for production model
            candidate_alias: Alias for candidate/testing model
        """
        self.model_name = model_name
        self.tracking_uri = tracking_uri or MLFLOW_TRACKING_URI
        self.champion_alias = champion_alias
        self.candidate_alias = candidate_alias

        self._client: Optional[MlflowClient] = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Ensure MLflow client is initialized."""
        if not MLFLOW_AVAILABLE:
            raise ImportError("MLflow is not available. Install with: pip install mlflow")

        if not self._initialized:
            mlflow.set_tracking_uri(self.tracking_uri)
            self._client = MlflowClientClass(self.tracking_uri)
            self._initialized = True
            logger.info(f"MLflow client initialized with tracking URI: {self.tracking_uri}")

    @property
    def client(self) -> MlflowClient:
        """Get the MLflow client, initializing if needed."""
        self._ensure_initialized()
        return self._client

    def register_model(
        self,
        model: Any,
        run_id: Optional[str] = None,
        metrics: Optional[Dict[str, float]] = None,
        params: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        artifact_path: str = "model",
    ) -> RegistrationResult:
        """
        Register a trained model with MLflow.

        Args:
            model: Trained sklearn model to register
            run_id: Existing run ID to use (creates new run if None)
            metrics: Metrics to log with the model
            params: Parameters to log with the model
            tags: Tags to associate with the run
            description: Description for the model version
            artifact_path: Path for storing model artifacts

        Returns:
            RegistrationResult with version info or error
        """
        try:
            self._ensure_initialized()

            # Create or use existing run
            if run_id is None:
                run = mlflow.start_run(run_name=f"{self.model_name}_training")
                run_id = run.info.run_id
                should_end_run = True
            else:
                should_end_run = False

            try:
                # Log parameters if provided
                if params:
                    mlflow.log_params(params)

                # Log metrics if provided
                if metrics:
                    mlflow.log_metrics(metrics)

                # Log tags if provided
                if tags:
                    mlflow.set_tags(tags)

                # Log the model
                mlflow.sklearn.log_model(model, artifact_path)

                # Register in model registry
                model_uri = f"runs:/{run_id}/{artifact_path}"

                # Ensure registered model exists
                self._ensure_registered_model_exists()

                # Create model version
                model_version = self.client.create_model_version(
                    name=self.model_name,
                    source=model_uri,
                    run_id=run_id,
                    description=description,
                )

                logger.info(
                    f"Registered model {self.model_name} version {model_version.version} "
                    f"from run {run_id}"
                )

                return RegistrationResult(
                    success=True,
                    model_name=self.model_name,
                    version=int(model_version.version),
                    run_id=run_id,
                )

            finally:
                if should_end_run:
                    mlflow.end_run()

        except MlflowException as e:
            logger.error(f"MLflow error during model registration: {e}")
            return RegistrationResult(
                success=False,
                model_name=self.model_name,
                error_message=str(e),
            )
        except Exception as e:
            logger.error(f"Unexpected error during model registration: {e}")
            return RegistrationResult(
                success=False,
                model_name=self.model_name,
                error_message=str(e),
            )

    def _ensure_registered_model_exists(self) -> None:
        """Ensure the registered model exists in the registry."""
        try:
            self.client.get_registered_model(self.model_name)
        except MlflowException:
            # Model doesn't exist, create it
            self.client.create_registered_model(
                name=self.model_name,
                description="ACGS-2 governance model for adaptive decision making",
            )
            logger.info(f"Created registered model: {self.model_name}")

    def set_alias(
        self,
        version: int,
        alias: str,
    ) -> bool:
        """
        Set an alias for a model version.

        Args:
            version: Model version number
            alias: Alias to set (e.g., 'champion', 'candidate')

        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_initialized()

            self.client.set_registered_model_alias(
                name=self.model_name,
                alias=alias,
                version=str(version),
            )

            logger.info(f"Set alias '{alias}' to {self.model_name} version {version}")
            return True

        except MlflowException as e:
            logger.error(f"Failed to set alias '{alias}': {e}")
            return False

    def promote_to_champion(self, version: int) -> bool:
        """
        Promote a model version to champion (production).

        Args:
            version: Model version to promote

        Returns:
            True if successful, False otherwise
        """
        return self.set_alias(version, self.champion_alias)

    def promote_to_candidate(self, version: int) -> bool:
        """
        Set a model version as candidate for A/B testing.

        Args:
            version: Model version to set as candidate

        Returns:
            True if successful, False otherwise
        """
        return self.set_alias(version, self.candidate_alias)

    def promote_candidate_to_champion(self) -> bool:
        """
        Promote the current candidate to champion.

        Returns:
            True if successful, False otherwise
        """
        try:
            candidate_info = self.get_version_by_alias(self.candidate_alias)
            if candidate_info is None:
                logger.error("No candidate model version found")
                return False

            return self.promote_to_champion(candidate_info.version)

        except Exception as e:
            logger.error(f"Failed to promote candidate to champion: {e}")
            return False

    def get_version_by_alias(self, alias: str) -> Optional[ModelVersionInfo]:
        """
        Get model version info by alias.

        Args:
            alias: Alias to look up (e.g., 'champion', 'candidate')

        Returns:
            ModelVersionInfo if found, None otherwise
        """
        try:
            self._ensure_initialized()

            version = self.client.get_model_version_by_alias(
                name=self.model_name,
                alias=alias,
            )

            return self._version_to_info(version)

        except MlflowException:
            logger.debug(f"No model version found for alias '{alias}'")
            return None

    def get_champion_model(self) -> Optional[Any]:
        """
        Load the champion (production) model.

        Returns:
            Loaded sklearn model or None if not found
        """
        return self.load_model_by_alias(self.champion_alias)

    def get_candidate_model(self) -> Optional[Any]:
        """
        Load the candidate (testing) model.

        Returns:
            Loaded sklearn model or None if not found
        """
        return self.load_model_by_alias(self.candidate_alias)

    def load_model_by_alias(self, alias: str) -> Optional[Any]:
        """
        Load a model by alias.

        Args:
            alias: Alias to load (e.g., 'champion', 'candidate')

        Returns:
            Loaded sklearn model or None if not found
        """
        try:
            self._ensure_initialized()

            model_uri = f"models:/{self.model_name}@{alias}"
            model = mlflow.sklearn.load_model(model_uri)

            logger.info(f"Loaded model from {model_uri}")
            return model

        except MlflowException as e:
            logger.warning(f"Failed to load model by alias '{alias}': {e}")
            return None

    def load_model_by_version(self, version: int) -> Optional[Any]:
        """
        Load a model by version number.

        Args:
            version: Model version number

        Returns:
            Loaded sklearn model or None if not found
        """
        try:
            self._ensure_initialized()

            model_uri = f"models:/{self.model_name}/{version}"
            model = mlflow.sklearn.load_model(model_uri)

            logger.info(f"Loaded model from {model_uri}")
            return model

        except MlflowException as e:
            logger.warning(f"Failed to load model version {version}: {e}")
            return None

    def rollback(
        self,
        to_version: Optional[int] = None,
        alias: str = DEFAULT_CHAMPION_ALIAS,
    ) -> RollbackResult:
        """
        Rollback to a previous model version.

        If to_version is not specified, rolls back to the previous version
        before the current alias.

        Args:
            to_version: Specific version to rollback to (None for auto-detect)
            alias: Alias to rollback (default: champion)

        Returns:
            RollbackResult with rollback details
        """
        try:
            self._ensure_initialized()

            # Get current version for the alias
            current_info = self.get_version_by_alias(alias)
            current_version = current_info.version if current_info else None

            if to_version is None:
                # Auto-detect previous version
                if current_version is None:
                    return RollbackResult(
                        success=False,
                        alias=alias,
                        error_message=f"No current version found for alias '{alias}'",
                    )

                # Find the previous version
                versions = self.list_versions()
                valid_versions = [
                    v.version
                    for v in versions
                    if v.version < current_version and v.status != "DELETED_REGISTRATION"
                ]

                if not valid_versions:
                    return RollbackResult(
                        success=False,
                        previous_version=current_version,
                        alias=alias,
                        error_message="No previous version available for rollback",
                    )

                to_version = max(valid_versions)

            # Perform rollback
            success = self.set_alias(to_version, alias)

            if success:
                logger.info(f"Rolled back {alias} from version {current_version} to {to_version}")
                return RollbackResult(
                    success=True,
                    previous_version=current_version,
                    new_version=to_version,
                    alias=alias,
                )
            else:
                return RollbackResult(
                    success=False,
                    previous_version=current_version,
                    new_version=to_version,
                    alias=alias,
                    error_message="Failed to set alias during rollback",
                )

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return RollbackResult(
                success=False,
                alias=alias,
                error_message=str(e),
            )

    def list_versions(self) -> List[ModelVersionInfo]:
        """
        List all versions of the model.

        Returns:
            List of ModelVersionInfo for all versions
        """
        try:
            self._ensure_initialized()

            # Search for all versions of this model
            versions = self.client.search_model_versions(filter_string=f"name='{self.model_name}'")

            return [self._version_to_info(v) for v in versions]

        except MlflowException as e:
            logger.error(f"Failed to list model versions: {e}")
            return []

    def _version_to_info(self, version) -> ModelVersionInfo:
        """Convert MLflow ModelVersion to ModelVersionInfo."""
        # Get aliases for this version
        aliases = []
        try:
            # Check if this version has champion alias
            champion_version = self.get_version_by_alias(self.champion_alias)
            if champion_version and champion_version.version == int(version.version):
                aliases.append(self.champion_alias)

            # Check if this version has candidate alias
            candidate_version = self.get_version_by_alias(self.candidate_alias)
            if candidate_version and candidate_version.version == int(version.version):
                aliases.append(self.candidate_alias)
        except Exception:
            pass  # Ignore alias lookup errors in conversion

        # Get metrics from the associated run
        metrics = None
        if version.run_id:
            try:
                run = self.client.get_run(version.run_id)
                metrics = run.data.metrics
            except Exception:
                pass  # Metrics retrieval is optional

        creation_time = datetime.fromtimestamp(version.creation_timestamp / 1000, tz=timezone.utc)

        return ModelVersionInfo(
            name=version.name,
            version=int(version.version),
            aliases=aliases,
            run_id=version.run_id or "",
            status=version.status,
            creation_timestamp=creation_time,
            description=version.description,
            metrics=metrics,
            tags=dict(version.tags) if version.tags else None,
        )

    def delete_alias(self, alias: str) -> bool:
        """
        Delete an alias from the model registry.

        Args:
            alias: Alias to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self._ensure_initialized()

            self.client.delete_registered_model_alias(
                name=self.model_name,
                alias=alias,
            )

            logger.info(f"Deleted alias '{alias}' from {self.model_name}")
            return True

        except MlflowException as e:
            logger.error(f"Failed to delete alias '{alias}': {e}")
            return False

    def get_model_metrics(self, version: int) -> Optional[Dict[str, float]]:
        """
        Get metrics for a specific model version.

        Args:
            version: Model version number

        Returns:
            Dictionary of metrics or None if not found
        """
        try:
            self._ensure_initialized()

            model_version = self.client.get_model_version(
                name=self.model_name,
                version=str(version),
            )

            if model_version.run_id:
                run = self.client.get_run(model_version.run_id)
                return run.data.metrics

            return None

        except MlflowException as e:
            logger.error(f"Failed to get metrics for version {version}: {e}")
            return None


# Module-level convenience functions

_version_manager: Optional[MLflowVersionManager] = None


def get_version_manager(
    model_name: str = DEFAULT_MODEL_NAME,
    tracking_uri: Optional[str] = None,
) -> MLflowVersionManager:
    """
    Get the global MLflow version manager instance.

    Args:
        model_name: Model registry name
        tracking_uri: MLflow tracking server URI

    Returns:
        Initialized MLflowVersionManager
    """
    global _version_manager

    if _version_manager is None:
        _version_manager = MLflowVersionManager(
            model_name=model_name,
            tracking_uri=tracking_uri,
        )

    return _version_manager


def register_model(
    model: Any,
    metrics: Optional[Dict[str, float]] = None,
    params: Optional[Dict[str, Any]] = None,
    description: Optional[str] = None,
) -> RegistrationResult:
    """
    Register a model using the global version manager.

    Args:
        model: Trained sklearn model
        metrics: Metrics to log
        params: Parameters to log
        description: Model description

    Returns:
        RegistrationResult with version info
    """
    manager = get_version_manager()
    return manager.register_model(
        model=model,
        metrics=metrics,
        params=params,
        description=description,
    )


def load_champion_model() -> Optional[Any]:
    """Load the champion (production) model."""
    manager = get_version_manager()
    return manager.get_champion_model()


def load_candidate_model() -> Optional[Any]:
    """Load the candidate (testing) model."""
    manager = get_version_manager()
    return manager.get_candidate_model()


def rollback_champion(to_version: Optional[int] = None) -> RollbackResult:
    """
    Rollback the champion model to a previous version.

    Args:
        to_version: Specific version to rollback to (None for auto-detect)

    Returns:
        RollbackResult with rollback details
    """
    manager = get_version_manager()
    return manager.rollback(to_version=to_version, alias=manager.champion_alias)


# Export key classes and functions
__all__ = [
    "MLflowVersionManager",
    "ModelVersionInfo",
    "RegistrationResult",
    "RollbackResult",
    "get_version_manager",
    "register_model",
    "load_champion_model",
    "load_candidate_model",
    "rollback_champion",
]
