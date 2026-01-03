"""
Adaptive Learning Engine - FastAPI Endpoints
Constitutional Hash: cdd01ef066bc6cf2

FastAPI router with endpoints for prediction, training, drift monitoring, and rollback.
Follows patterns from acgs2-core/enhanced_agent_bus/api.py.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from starlette.responses import Response

from src.api.models import (
    BatchTrainingRequest,
    BatchTrainingResponse,
    DriftCheckRequest,
    DriftStatusEnum,
    DriftStatusResponse,
    ErrorResponse,
    HealthResponse,
    MetricsResponse,
    ModelInfoResponse,
    ModelStateEnum,
    ModelVersionInfo,
    ModelVersionListResponse,
    PredictionRequest,
    PredictionResponse,
    RollbackResponse,
    SafetyStatusEnum,
    SafetyStatusResponse,
    TrainingRequest,
    TrainingResponse,
)
from src.models.model_manager import ModelManager, SwapStatus
from src.models.online_learner import ModelState
from src.monitoring.drift_detector import DriftDetector, DriftStatus
from src.monitoring.metrics import MetricsRegistry, get_metrics_registry
from src.safety.bounds_checker import SafetyBoundsChecker, SafetyStatus

logger = logging.getLogger(__name__)

# Create router with prefix
router = APIRouter()

# Global state - will be initialized by main.py
_model_manager: Optional[ModelManager] = None
_drift_detector: Optional[DriftDetector] = None
_safety_checker: Optional[SafetyBoundsChecker] = None
_metrics_registry: Optional[MetricsRegistry] = None
_start_time: float = time.time()


def initialize_services(
    model_manager: ModelManager,
    drift_detector: DriftDetector,
    safety_checker: SafetyBoundsChecker,
    metrics_registry: Optional[MetricsRegistry] = None,
) -> None:
    """Initialize global service instances.

    Called by main.py during startup to inject dependencies.

    Args:
        model_manager: The ModelManager instance.
        drift_detector: The DriftDetector instance.
        safety_checker: The SafetyBoundsChecker instance.
        metrics_registry: Optional custom MetricsRegistry.
    """
    global _model_manager, _drift_detector, _safety_checker, _metrics_registry, _start_time
    _model_manager = model_manager
    _drift_detector = drift_detector
    _safety_checker = safety_checker
    _metrics_registry = metrics_registry or get_metrics_registry()
    _start_time = time.time()
    logger.info("Endpoint services initialized")


# Dependency injection functions
async def get_model_manager() -> ModelManager:
    """Dependency to get the model manager."""
    if _model_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Model manager not initialized",
        )
    return _model_manager


async def get_drift_detector() -> DriftDetector:
    """Dependency to get the drift detector."""
    if _drift_detector is None:
        raise HTTPException(
            status_code=503,
            detail="Drift detector not initialized",
        )
    return _drift_detector


async def get_safety_checker() -> SafetyBoundsChecker:
    """Dependency to get the safety bounds checker."""
    if _safety_checker is None:
        raise HTTPException(
            status_code=503,
            detail="Safety bounds checker not initialized",
        )
    return _safety_checker


async def get_metrics() -> MetricsRegistry:
    """Dependency to get the metrics registry."""
    if _metrics_registry is None:
        return get_metrics_registry()
    return _metrics_registry


def _convert_model_state(state: ModelState) -> ModelStateEnum:
    """Convert internal ModelState to API enum."""
    mapping = {
        ModelState.COLD_START: ModelStateEnum.COLD_START,
        ModelState.WARMING: ModelStateEnum.WARMING,
        ModelState.ACTIVE: ModelStateEnum.ACTIVE,
        ModelState.PAUSED: ModelStateEnum.PAUSED,
    }
    return mapping.get(state, ModelStateEnum.COLD_START)


def _convert_drift_status(status: DriftStatus) -> DriftStatusEnum:
    """Convert internal DriftStatus to API enum."""
    mapping = {
        DriftStatus.NO_DRIFT: DriftStatusEnum.NO_DRIFT,
        DriftStatus.DRIFT_DETECTED: DriftStatusEnum.DRIFT_DETECTED,
        DriftStatus.INSUFFICIENT_DATA: DriftStatusEnum.INSUFFICIENT_DATA,
        DriftStatus.DISABLED: DriftStatusEnum.DISABLED,
        DriftStatus.ERROR: DriftStatusEnum.ERROR,
    }
    return mapping.get(status, DriftStatusEnum.ERROR)


def _convert_safety_status(status: SafetyStatus) -> SafetyStatusEnum:
    """Convert internal SafetyStatus to API enum."""
    mapping = {
        SafetyStatus.OK: SafetyStatusEnum.OK,
        SafetyStatus.WARNING: SafetyStatusEnum.WARNING,
        SafetyStatus.PAUSED: SafetyStatusEnum.PAUSED,
        SafetyStatus.CRITICAL: SafetyStatusEnum.CRITICAL,
    }
    return mapping.get(status, SafetyStatusEnum.OK)


# ============================================================================
# Prediction Endpoints
# ============================================================================


@router.post(
    "/api/v1/predict",
    response_model=PredictionResponse,
    responses={
        500: {"model": ErrorResponse, "description": "Prediction error"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Get governance decision prediction",
    description="Make a prediction using the current online learning model.",
)
async def predict(
    request: PredictionRequest,
    manager: ModelManager = Depends(get_model_manager),
    metrics: MetricsRegistry = Depends(get_metrics),
) -> PredictionResponse:
    """Get governance decision prediction.

    Uses the current champion model to make a prediction based on features.
    Returns prediction, confidence, and model state information.
    """
    start_time = time.perf_counter()
    prediction_id = request.request_id or str(uuid.uuid4())

    try:
        # Get prediction from model
        model = await manager.get_model()
        result = model.predict_one(request.features)

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Record metrics
        metrics.record_prediction(
            latency_seconds=latency_ms / 1000,
            model_version=str(manager._current_version),
            success=True,
        )

        return PredictionResponse(
            prediction=result.prediction,
            confidence=result.confidence,
            probabilities=result.probabilities if request.include_probabilities else None,
            model_state=_convert_model_state(result.model_state),
            sample_count=result.sample_count,
            prediction_id=prediction_id,
            latency_ms=latency_ms,
        )

    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        metrics.record_error(error_type="prediction_error", endpoint="/api/v1/predict")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction error: {str(e)}",
        ) from e


# ============================================================================
# Training Endpoints
# ============================================================================


@router.post(
    "/api/v1/train",
    response_model=TrainingResponse,
    status_code=202,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Submit training sample",
    description="Submit a training sample for online learning (async processing).",
)
async def train(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
    manager: ModelManager = Depends(get_model_manager),
    drift_detector: DriftDetector = Depends(get_drift_detector),
    safety_checker: SafetyBoundsChecker = Depends(get_safety_checker),
    metrics: MetricsRegistry = Depends(get_metrics),
) -> TrainingResponse:
    """Submit training sample for online learning.

    Follows the progressive validation paradigm: predict first, then learn.
    Training is processed asynchronously via background tasks.
    """
    training_id = str(uuid.uuid4())
    start_time = time.perf_counter()

    try:
        # Check if learning is allowed
        if not safety_checker.is_learning_allowed():
            return TrainingResponse(
                success=False,
                sample_count=manager.get_model_sync().get_sample_count(),
                current_accuracy=manager.get_model_sync().get_accuracy(),
                model_state=ModelStateEnum.PAUSED,
                message="Learning is paused due to safety bounds violation",
                training_id=training_id,
            )

        # Get current model and train
        model = await manager.get_model()
        result = model.learn_one(
            x=request.features,
            y=request.label,
            sample_weight=request.sample_weight,
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Record metrics
        metrics.record_training(
            latency_seconds=latency_ms / 1000,
            model_version=str(manager._current_version),
        )

        # Add data to drift detector in background
        async def add_to_drift_detector() -> None:
            drift_detector.add_data_point(
                features=request.features,
                label=request.label,
                prediction=None,
            )

        background_tasks.add_task(add_to_drift_detector)

        return TrainingResponse(
            success=result.success,
            sample_count=result.sample_count,
            current_accuracy=result.current_accuracy,
            model_state=_convert_model_state(result.model_state),
            message=result.message,
            training_id=training_id,
        )

    except Exception as e:
        logger.error(f"Training error: {e}", exc_info=True)
        metrics.record_error(error_type="training_error", endpoint="/api/v1/train")
        raise HTTPException(
            status_code=500,
            detail=f"Training error: {str(e)}",
        ) from e


@router.post(
    "/api/v1/train/batch",
    response_model=BatchTrainingResponse,
    status_code=202,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Submit batch training samples",
    description="Submit multiple training samples for processing.",
)
async def train_batch(
    request: BatchTrainingRequest,
    background_tasks: BackgroundTasks,
    manager: ModelManager = Depends(get_model_manager),
    drift_detector: DriftDetector = Depends(get_drift_detector),
    safety_checker: SafetyBoundsChecker = Depends(get_safety_checker),
    metrics: MetricsRegistry = Depends(get_metrics),
) -> BatchTrainingResponse:
    """Submit batch training samples.

    Processes multiple training samples. If async_processing is True,
    samples are processed in background tasks.
    """
    start_time = time.perf_counter()
    accepted = 0
    total = len(request.samples)

    try:
        # Check if learning is allowed
        if not safety_checker.is_learning_allowed():
            return BatchTrainingResponse(
                accepted=0,
                total=total,
                sample_count=manager.get_model_sync().get_sample_count(),
                current_accuracy=manager.get_model_sync().get_accuracy(),
                model_state=ModelStateEnum.PAUSED,
                message="Learning is paused due to safety bounds violation",
            )

        model = await manager.get_model()

        # Process samples
        async def process_samples() -> None:
            nonlocal accepted
            for sample in request.samples:
                result = model.learn_one(
                    x=sample.features,
                    y=sample.label,
                    sample_weight=sample.sample_weight,
                )
                if result.success:
                    accepted += 1
                    drift_detector.add_data_point(
                        features=sample.features,
                        label=sample.label,
                    )

        if request.async_processing:
            # Queue for background processing
            background_tasks.add_task(process_samples)
            accepted = total  # Assume all will be accepted for async
        else:
            # Process synchronously
            await process_samples()

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Record batch metrics
        metrics.record_training(
            latency_seconds=latency_ms / 1000,
            model_version=str(manager._current_version),
            batch_size=accepted,
        )

        return BatchTrainingResponse(
            accepted=accepted,
            total=total,
            sample_count=model.get_sample_count(),
            current_accuracy=model.get_accuracy(),
            model_state=_convert_model_state(model.get_state()),
            message=f"Processed {accepted}/{total} samples"
            + (" (async)" if request.async_processing else ""),
        )

    except Exception as e:
        logger.error(f"Batch training error: {e}", exc_info=True)
        metrics.record_error(error_type="batch_training_error", endpoint="/api/v1/train/batch")
        raise HTTPException(
            status_code=500,
            detail=f"Batch training error: {str(e)}",
        ) from e


# ============================================================================
# Model Management Endpoints
# ============================================================================


@router.get(
    "/api/v1/models/current",
    response_model=ModelInfoResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Get active model metadata",
    description="Get information about the currently active model.",
)
async def get_current_model(
    manager: ModelManager = Depends(get_model_manager),
) -> ModelInfoResponse:
    """Get active model metadata.

    Returns information about the current champion model including
    state, accuracy, sample count, and version.
    """
    try:
        model = await manager.get_model()
        metrics = model.get_metrics()
        model_info = model.get_model_info()

        return ModelInfoResponse(
            model_type=metrics.model_type,
            model_state=_convert_model_state(metrics.model_state),
            version=str(manager._current_version),
            sample_count=metrics.sample_count,
            predictions_count=metrics.predictions_count,
            accuracy=metrics.accuracy,
            rolling_accuracy=metrics.recent_accuracy,
            learning_rate=model_info.get("learning_rate", 0.1),
            is_ready=model.is_ready(),
            is_paused=model_info.get("is_paused", False),
            last_update_time=(
                datetime.fromtimestamp(metrics.last_update_time, tz=timezone.utc).isoformat()
                if metrics.last_update_time
                else None
            ),
        )

    except Exception as e:
        logger.error(f"Error getting model info: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting model info: {str(e)}",
        ) from e


@router.get(
    "/api/v1/models/versions",
    response_model=ModelVersionListResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="List model versions",
    description="Get list of available model versions for rollback.",
)
async def list_model_versions(
    manager: ModelManager = Depends(get_model_manager),
) -> ModelVersionListResponse:
    """List available model versions.

    Returns all model versions in history that can be used for rollback.
    """
    try:
        version_history = manager.get_version_history()
        available_versions = manager.get_available_versions()

        versions = [
            ModelVersionInfo(
                version=str(v.get("version", "")),
                stage="Production" if v.get("is_champion") else "Archived",
                accuracy=v.get("accuracy"),
                drift_score=v.get("metadata", {}).get("drift_score"),
                sample_count=v.get("sample_count"),
                created_at=(
                    datetime.fromtimestamp(v.get("created_at", 0), tz=timezone.utc).isoformat()
                    if v.get("created_at")
                    else None
                ),
                aliases=["champion"] if v.get("is_champion") else [],
            )
            for v in version_history
        ]

        champion_version = None
        for v in version_history:
            if v.get("is_champion"):
                champion_version = str(v.get("version", ""))
                break

        return ModelVersionListResponse(
            versions=versions,
            current_version=str(manager._current_version),
            champion_version=champion_version,
            total_versions=len(available_versions),
        )

    except Exception as e:
        logger.error(f"Error listing model versions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing model versions: {str(e)}",
        ) from e


@router.post(
    "/api/v1/models/rollback/{version}",
    response_model=RollbackResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Version not found"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Rollback to previous version",
    description="Rollback the model to a specific version.",
)
async def rollback_model(
    version: str,
    reason: Optional[str] = Query(default=None, description="Reason for rollback"),
    manager: ModelManager = Depends(get_model_manager),
    metrics: MetricsRegistry = Depends(get_metrics),
) -> RollbackResponse:
    """Rollback to a previous model version.

    Restores a previous model version and makes it the active model.
    Predictions immediately use the rolled-back model.
    """
    try:
        previous_version = manager._current_version

        # Handle "previous" as a special case
        if version.lower() == "previous":
            result = await manager.rollback_to_previous()
        else:
            try:
                version_int = int(version)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid version format: {version}. Use an integer or 'previous'.",
                ) from exc
            result = await manager.rollback_to_version(version_int)

        if result.status == SwapStatus.SUCCESS:
            metrics.record_rollback()
            logger.info(
                f"Model rolled back from v{previous_version} to v{result.new_version}",
                extra={"reason": reason},
            )
            return RollbackResponse(
                success=True,
                previous_version=str(previous_version),
                new_version=str(result.new_version),
                message=result.message,
            )
        else:
            # Check if version not found
            available_versions = manager.get_available_versions()
            if version.lower() != "previous" and int(version) not in available_versions:
                raise HTTPException(
                    status_code=404,
                    detail=f"Version {version} not found. Available: {available_versions}",
                )

            return RollbackResponse(
                success=False,
                previous_version=str(previous_version),
                new_version=None,
                message=result.message,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rollback error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Rollback error: {str(e)}",
        ) from e


# ============================================================================
# Drift Detection Endpoints
# ============================================================================


@router.get(
    "/api/v1/drift/status",
    response_model=DriftStatusResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Get drift detection status",
    description="Get current drift detection status and metrics.",
)
async def get_drift_status(
    detector: DriftDetector = Depends(get_drift_detector),
) -> DriftStatusResponse:
    """Get drift detection status.

    Returns the current drift status including drift score, threshold,
    and data sizes for reference and current windows.
    """
    try:
        result = detector.get_status()
        drift_metrics = detector.get_metrics()

        return DriftStatusResponse(
            status=_convert_drift_status(result.status),
            drift_detected=result.drift_detected,
            drift_score=result.drift_score,
            drift_threshold=result.drift_threshold,
            reference_size=result.reference_size,
            current_size=result.current_size,
            total_checks=drift_metrics.total_checks,
            drift_detections=drift_metrics.drift_detections,
            consecutive_drift_count=drift_metrics.consecutive_drift_count,
            columns_drifted=result.columns_drifted if result.columns_drifted else None,
            last_check_time=(
                datetime.fromtimestamp(drift_metrics.last_check_time, tz=timezone.utc).isoformat()
                if drift_metrics.last_check_time
                else None
            ),
            last_drift_time=(
                datetime.fromtimestamp(drift_metrics.last_drift_time, tz=timezone.utc).isoformat()
                if drift_metrics.last_drift_time
                else None
            ),
            message=result.message,
        )

    except Exception as e:
        logger.error(f"Error getting drift status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting drift status: {str(e)}",
        ) from e


@router.post(
    "/api/v1/drift/check",
    response_model=DriftStatusResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Trigger drift check",
    description="Manually trigger a drift detection check.",
)
async def trigger_drift_check(
    request: DriftCheckRequest,
    detector: DriftDetector = Depends(get_drift_detector),
    metrics: MetricsRegistry = Depends(get_metrics),
) -> DriftStatusResponse:
    """Manually trigger a drift detection check.

    Runs a drift detection check comparing reference and current data.
    Use force=True to check even with insufficient data.
    """
    try:
        start_time = time.perf_counter()

        result = await detector.check_drift_async()

        latency_seconds = time.perf_counter() - start_time
        metrics.record_drift_check(
            latency_seconds=latency_seconds,
            drift_detected=result.drift_detected,
            drift_score=result.drift_score,
        )

        drift_metrics = detector.get_metrics()

        return DriftStatusResponse(
            status=_convert_drift_status(result.status),
            drift_detected=result.drift_detected,
            drift_score=result.drift_score,
            drift_threshold=result.drift_threshold,
            reference_size=result.reference_size,
            current_size=result.current_size,
            total_checks=drift_metrics.total_checks,
            drift_detections=drift_metrics.drift_detections,
            consecutive_drift_count=drift_metrics.consecutive_drift_count,
            columns_drifted=result.columns_drifted if result.columns_drifted else None,
            last_check_time=datetime.now(timezone.utc).isoformat(),
            last_drift_time=(
                datetime.fromtimestamp(drift_metrics.last_drift_time, tz=timezone.utc).isoformat()
                if drift_metrics.last_drift_time
                else None
            ),
            message=result.message,
        )

    except Exception as e:
        logger.error(f"Error running drift check: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error running drift check: {str(e)}",
        ) from e


# ============================================================================
# Safety Status Endpoints
# ============================================================================


@router.get(
    "/api/v1/safety/status",
    response_model=SafetyStatusResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Get safety bounds status",
    description="Get current safety bounds checking status.",
)
async def get_safety_status(
    checker: SafetyBoundsChecker = Depends(get_safety_checker),
    manager: ModelManager = Depends(get_model_manager),
) -> SafetyStatusResponse:
    """Get safety bounds status.

    Returns the current safety status including accuracy threshold,
    consecutive failures, and whether learning is paused.
    """
    try:
        safety_metrics = checker.get_metrics()
        config = checker.get_config()
        model = await manager.get_model()

        return SafetyStatusResponse(
            status=_convert_safety_status(safety_metrics.current_status),
            current_accuracy=model.get_accuracy(),
            accuracy_threshold=config["accuracy_threshold"],
            consecutive_failures=safety_metrics.consecutive_failures,
            failures_limit=config["consecutive_failures_limit"],
            total_checks=safety_metrics.total_checks,
            passed_checks=safety_metrics.passed_checks,
            is_learning_paused=not checker.is_learning_allowed(),
            last_check_time=(
                datetime.fromtimestamp(safety_metrics.last_check_time, tz=timezone.utc).isoformat()
                if safety_metrics.last_check_time
                else None
            ),
            message=f"Status: {safety_metrics.current_status.value}",
        )

    except Exception as e:
        logger.error(f"Error getting safety status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting safety status: {str(e)}",
        ) from e


@router.post(
    "/api/v1/safety/resume",
    response_model=SafetyStatusResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Resume learning after manual intervention",
    description="Force resume learning after safety bounds violation.",
)
async def resume_learning(
    checker: SafetyBoundsChecker = Depends(get_safety_checker),
    manager: ModelManager = Depends(get_model_manager),
) -> SafetyStatusResponse:
    """Force resume learning after manual intervention.

    Resets the consecutive failure counter and resumes learning.
    Should only be called after manual review of the safety violation.
    """
    try:
        checker.force_resume()
        manager.resume_learning()

        return await get_safety_status(checker, manager)

    except Exception as e:
        logger.error(f"Error resuming learning: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error resuming learning: {str(e)}",
        ) from e


# ============================================================================
# Metrics Endpoints
# ============================================================================


@router.get(
    "/metrics",
    summary="Prometheus metrics",
    description="Prometheus metrics endpoint for scraping.",
)
async def prometheus_metrics(
    metrics: MetricsRegistry = Depends(get_metrics),
) -> Response:
    """Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format for scraping.
    """
    try:
        output = metrics.generate_metrics()
        return Response(
            content=output,
            media_type=metrics.get_content_type(),
        )
    except Exception as e:
        logger.error(f"Error generating metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating metrics: {str(e)}",
        ) from e


@router.get(
    "/api/v1/metrics",
    response_model=MetricsResponse,
    responses={
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
    summary="Get metrics summary",
    description="Get a summary of service metrics as JSON.",
)
async def get_metrics_summary(
    metrics_registry: MetricsRegistry = Depends(get_metrics),
    manager: ModelManager = Depends(get_model_manager),
    detector: DriftDetector = Depends(get_drift_detector),
) -> MetricsResponse:
    """Get metrics summary.

    Returns a JSON summary of key service metrics.
    """
    try:
        snapshot = metrics_registry.get_snapshot()
        model = await manager.get_model()
        drift_metrics = detector.get_metrics()

        return MetricsResponse(
            predictions_total=snapshot.predictions_total,
            training_samples_total=snapshot.training_samples_total,
            model_accuracy=model.get_accuracy(),
            drift_score=drift_metrics.current_drift_score,
            safety_violations=snapshot.safety_violations,
            model_swaps=manager.get_swap_metrics()["total_swaps"],
            rollbacks=manager.get_swap_metrics().get("successful_swaps", 0),
            uptime_seconds=time.time() - _start_time,
        )

    except Exception as e:
        logger.error(f"Error getting metrics summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error getting metrics summary: {str(e)}",
        ) from e


# ============================================================================
# Health Check Endpoints
# ============================================================================


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Service health check endpoint.",
)
async def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns overall service health status including model, drift, and safety states.
    """
    try:
        # Get component statuses
        model_status = ModelStateEnum.COLD_START
        drift_status = DriftStatusEnum.DISABLED
        safety_status = SafetyStatusEnum.OK
        sample_count = 0
        predictions_count = 0

        if _model_manager is not None:
            model = await _model_manager.get_model()
            model_status = _convert_model_state(model.get_state())
            sample_count = model.get_sample_count()
            metrics = model.get_metrics()
            predictions_count = metrics.predictions_count

        if _drift_detector is not None:
            drift_result = _drift_detector.get_status()
            drift_status = _convert_drift_status(drift_result.status)

        if _safety_checker is not None:
            safety_result = _safety_checker.get_status()
            safety_status = _convert_safety_status(safety_result)

        # Determine overall health
        is_healthy = (
            _model_manager is not None
            and _drift_detector is not None
            and _safety_checker is not None
        )
        overall_status = "healthy" if is_healthy else "unhealthy"

        return HealthResponse(
            status=overall_status,
            service="adaptive-learning-engine",
            version="1.0.0",
            model_status=model_status,
            drift_status=drift_status,
            safety_status=safety_status,
            uptime_seconds=time.time() - _start_time,
            sample_count=sample_count,
            predictions_count=predictions_count,
        )

    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return HealthResponse(
            status="unhealthy",
            service="adaptive-learning-engine",
            version="1.0.0",
            model_status=ModelStateEnum.COLD_START,
            drift_status=DriftStatusEnum.ERROR,
            safety_status=SafetyStatusEnum.CRITICAL,
            uptime_seconds=time.time() - _start_time,
            sample_count=0,
            predictions_count=0,
        )


# Export router and initialization function
__all__ = ["router", "initialize_services"]
