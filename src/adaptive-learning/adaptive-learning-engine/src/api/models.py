"""
Adaptive Learning Engine - API Models
Constitutional Hash: cdd01ef066bc6cf2

Pydantic request/response models for the Adaptive Learning Engine FastAPI endpoints.
Follows patterns from acgs2-core/enhanced_agent_bus/api.py.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ============================================================================
# Enums for API
# ============================================================================


class ModelStateEnum(str, Enum):
    """Model state representation for API responses."""

    COLD_START = "cold_start"
    WARMING = "warming"
    ACTIVE = "active"
    PAUSED = "paused"


class DriftStatusEnum(str, Enum):
    """Drift detection status for API responses."""

    NO_DRIFT = "no_drift"
    DRIFT_DETECTED = "drift_detected"
    INSUFFICIENT_DATA = "insufficient_data"
    DISABLED = "disabled"
    ERROR = "error"


class SafetyStatusEnum(str, Enum):
    """Safety bounds status for API responses."""

    OK = "ok"
    WARNING = "warning"
    PAUSED = "paused"
    CRITICAL = "critical"


class ModelStageEnum(str, Enum):
    """Model lifecycle stage for API responses."""

    NONE = "None"
    STAGING = "Staging"
    PRODUCTION = "Production"
    ARCHIVED = "Archived"


# ============================================================================
# Request Models
# ============================================================================


class PredictionRequest(BaseModel):
    """Request model for making predictions.

    Features should be a dictionary of numeric values representing
    the governance decision context.
    """

    features: Dict[str, float] = Field(
        ...,
        description="Feature dictionary with numeric values for prediction",
        examples=[{"feature_1": 0.5, "feature_2": 1.0, "feature_3": -0.3}],
    )
    include_probabilities: bool = Field(
        default=True,
        description="Include probability distribution in response",
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Optional tenant identifier for multi-tenant isolation",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Optional request identifier for tracing",
    )


class TrainingRequest(BaseModel):
    """Request model for submitting training samples.

    Follows the progressive validation paradigm: predict first, then learn.
    This endpoint is for submitting outcomes after predictions are made.
    """

    features: Dict[str, float] = Field(
        ...,
        description="Feature dictionary with numeric values",
        examples=[{"feature_1": 0.5, "feature_2": 1.0, "feature_3": -0.3}],
    )
    label: int = Field(
        ...,
        ge=0,
        le=1,
        description="Target label (0 or 1) for binary classification",
    )
    sample_weight: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Optional weight for time-weighted learning (recent samples weighted higher)",
    )
    tenant_id: Optional[str] = Field(
        default=None,
        description="Optional tenant identifier for multi-tenant isolation",
    )
    prediction_id: Optional[str] = Field(
        default=None,
        description="Optional ID linking this training sample to a previous prediction",
    )
    timestamp: Optional[float] = Field(
        default=None,
        description="Optional timestamp of the original event (for replay/backfill)",
    )


class BatchTrainingRequest(BaseModel):
    """Request model for batch training submissions."""

    samples: List[TrainingRequest] = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="List of training samples to process",
    )
    async_processing: bool = Field(
        default=True,
        description="Whether to process samples asynchronously",
    )


class RollbackRequest(BaseModel):
    """Request model for model version rollback."""

    version: str = Field(
        ...,
        description="Model version to rollback to (e.g., '1', '2', or 'previous')",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for rollback (logged for audit)",
    )


class DriftCheckRequest(BaseModel):
    """Request model for triggering a manual drift check."""

    force: bool = Field(
        default=False,
        description="Force drift check even if below minimum data threshold",
    )


# ============================================================================
# Response Models
# ============================================================================


class PredictionResponse(BaseModel):
    """Response model for predictions.

    Returns the prediction along with confidence scores and model metadata.
    """

    prediction: int = Field(
        ...,
        description="Predicted class (0 or 1)",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the prediction (0.0 to 1.0)",
    )
    probabilities: Optional[Dict[int, float]] = Field(
        default=None,
        description="Probability distribution over classes",
    )
    model_state: ModelStateEnum = Field(
        ...,
        description="Current state of the model",
    )
    sample_count: int = Field(
        ...,
        ge=0,
        description="Total training samples the model has seen",
    )
    prediction_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for this prediction (for linking to training)",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of the prediction",
    )
    latency_ms: Optional[float] = Field(
        default=None,
        description="Prediction latency in milliseconds",
    )


class TrainingResponse(BaseModel):
    """Response model for training submissions."""

    success: bool = Field(
        ...,
        description="Whether the training sample was processed successfully",
    )
    sample_count: int = Field(
        ...,
        ge=0,
        description="Total training samples processed by the model",
    )
    current_accuracy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Current model accuracy after training",
    )
    model_state: ModelStateEnum = Field(
        ...,
        description="Current state of the model",
    )
    message: str = Field(
        ...,
        description="Human-readable status message",
    )
    training_id: Optional[str] = Field(
        default=None,
        description="Unique identifier for this training update",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of the training update",
    )


class BatchTrainingResponse(BaseModel):
    """Response model for batch training submissions."""

    accepted: int = Field(
        ...,
        ge=0,
        description="Number of samples accepted for processing",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of samples submitted",
    )
    sample_count: int = Field(
        ...,
        ge=0,
        description="Total training samples processed by the model",
    )
    current_accuracy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Current model accuracy after batch training",
    )
    model_state: ModelStateEnum = Field(
        ...,
        description="Current state of the model",
    )
    message: str = Field(
        ...,
        description="Human-readable status message",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of the batch training",
    )


class ModelInfoResponse(BaseModel):
    """Response model for model metadata."""

    model_type: str = Field(
        ...,
        description="Type of the model (e.g., 'logistic_regression')",
    )
    model_state: ModelStateEnum = Field(
        ...,
        description="Current state of the model",
    )
    version: Optional[str] = Field(
        default=None,
        description="Current model version from registry",
    )
    sample_count: int = Field(
        ...,
        ge=0,
        description="Total training samples processed",
    )
    predictions_count: int = Field(
        ...,
        ge=0,
        description="Total predictions made",
    )
    accuracy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Cumulative accuracy",
    )
    rolling_accuracy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Rolling window accuracy (recent performance)",
    )
    learning_rate: float = Field(
        ...,
        description="Current learning rate",
    )
    is_ready: bool = Field(
        ...,
        description="Whether model is ready for production predictions",
    )
    is_paused: bool = Field(
        ...,
        description="Whether learning is paused due to safety bounds",
    )
    last_update_time: Optional[str] = Field(
        default=None,
        description="Timestamp of last training update",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Current timestamp",
    )


class ModelVersionInfo(BaseModel):
    """Information about a specific model version."""

    version: str = Field(
        ...,
        description="Model version identifier",
    )
    stage: ModelStageEnum = Field(
        ...,
        description="Model lifecycle stage",
    )
    accuracy: Optional[float] = Field(
        default=None,
        description="Accuracy at time of registration",
    )
    drift_score: Optional[float] = Field(
        default=None,
        description="Drift score at time of registration",
    )
    sample_count: Optional[int] = Field(
        default=None,
        description="Sample count at time of registration",
    )
    created_at: Optional[str] = Field(
        default=None,
        description="Creation timestamp",
    )
    aliases: List[str] = Field(
        default_factory=list,
        description="Aliases assigned to this version (e.g., 'champion')",
    )


class ModelVersionListResponse(BaseModel):
    """Response model for listing model versions."""

    versions: List[ModelVersionInfo] = Field(
        default_factory=list,
        description="List of model versions",
    )
    current_version: Optional[str] = Field(
        default=None,
        description="Currently active model version",
    )
    champion_version: Optional[str] = Field(
        default=None,
        description="Version with 'champion' alias",
    )
    total_versions: int = Field(
        default=0,
        description="Total number of versions",
    )


class RollbackResponse(BaseModel):
    """Response model for model rollback operations."""

    success: bool = Field(
        ...,
        description="Whether rollback was successful",
    )
    previous_version: Optional[str] = Field(
        default=None,
        description="Version before rollback",
    )
    new_version: Optional[str] = Field(
        default=None,
        description="Version after rollback (active version)",
    )
    message: str = Field(
        ...,
        description="Human-readable status message",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of the rollback",
    )


class DriftStatusResponse(BaseModel):
    """Response model for drift detection status."""

    status: DriftStatusEnum = Field(
        ...,
        description="Current drift status",
    )
    drift_detected: bool = Field(
        ...,
        description="Whether drift is currently detected",
    )
    drift_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Current drift score (share of drifted columns)",
    )
    drift_threshold: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Configured drift threshold",
    )
    reference_size: int = Field(
        ...,
        ge=0,
        description="Number of samples in reference dataset",
    )
    current_size: int = Field(
        ...,
        ge=0,
        description="Number of samples in current window",
    )
    total_checks: int = Field(
        default=0,
        ge=0,
        description="Total drift checks performed",
    )
    drift_detections: int = Field(
        default=0,
        ge=0,
        description="Total times drift was detected",
    )
    consecutive_drift_count: int = Field(
        default=0,
        ge=0,
        description="Consecutive drift detections (resets on no-drift)",
    )
    columns_drifted: Optional[Dict[str, bool]] = Field(
        default=None,
        description="Per-column drift status",
    )
    last_check_time: Optional[str] = Field(
        default=None,
        description="Timestamp of last drift check",
    )
    last_drift_time: Optional[str] = Field(
        default=None,
        description="Timestamp of last drift detection",
    )
    message: str = Field(
        default="",
        description="Human-readable status message",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Current timestamp",
    )


class SafetyStatusResponse(BaseModel):
    """Response model for safety bounds status."""

    status: SafetyStatusEnum = Field(
        ...,
        description="Current safety status",
    )
    current_accuracy: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Current model accuracy",
    )
    accuracy_threshold: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Configured accuracy threshold",
    )
    consecutive_failures: int = Field(
        default=0,
        ge=0,
        description="Consecutive safety check failures",
    )
    failures_limit: int = Field(
        ...,
        ge=1,
        description="Consecutive failures before pausing learning",
    )
    total_checks: int = Field(
        default=0,
        ge=0,
        description="Total safety checks performed",
    )
    passed_checks: int = Field(
        default=0,
        ge=0,
        description="Total safety checks passed",
    )
    is_learning_paused: bool = Field(
        ...,
        description="Whether learning is currently paused",
    )
    last_check_time: Optional[str] = Field(
        default=None,
        description="Timestamp of last safety check",
    )
    message: str = Field(
        default="",
        description="Human-readable status message",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Current timestamp",
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(
        ...,
        description="Overall health status ('healthy' or 'unhealthy')",
    )
    service: str = Field(
        default="adaptive-learning-engine",
        description="Service name",
    )
    version: str = Field(
        default="1.0.0",
        description="Service version",
    )
    model_status: ModelStateEnum = Field(
        ...,
        description="Current model state",
    )
    drift_status: DriftStatusEnum = Field(
        ...,
        description="Current drift detection status",
    )
    safety_status: SafetyStatusEnum = Field(
        ...,
        description="Current safety bounds status",
    )
    uptime_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Service uptime in seconds",
    )
    sample_count: int = Field(
        default=0,
        ge=0,
        description="Total training samples processed",
    )
    predictions_count: int = Field(
        default=0,
        ge=0,
        description="Total predictions made",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Current timestamp",
    )


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str = Field(
        ...,
        description="Error type or code",
    )
    detail: str = Field(
        ...,
        description="Human-readable error message",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request identifier for tracing",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Timestamp of the error",
    )


class MetricsResponse(BaseModel):
    """Response model for service metrics summary."""

    predictions_total: int = Field(
        default=0,
        ge=0,
        description="Total predictions made",
    )
    training_samples_total: int = Field(
        default=0,
        ge=0,
        description="Total training samples processed",
    )
    model_accuracy: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Current model accuracy",
    )
    drift_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Current drift score",
    )
    safety_violations: int = Field(
        default=0,
        ge=0,
        description="Total safety violations",
    )
    model_swaps: int = Field(
        default=0,
        ge=0,
        description="Total model swaps performed",
    )
    rollbacks: int = Field(
        default=0,
        ge=0,
        description="Total rollbacks performed",
    )
    uptime_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Service uptime in seconds",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Current timestamp",
    )


# ============================================================================
# WebSocket Models (for real-time updates)
# ============================================================================


class WebSocketMessage(BaseModel):
    """Model for WebSocket messages."""

    event: str = Field(
        ...,
        description="Event type (e.g., 'prediction', 'training', 'drift_alert')",
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Event payload",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Event timestamp",
    )


# ============================================================================
# Export all models
# ============================================================================

__all__ = [
    # Enums
    "ModelStateEnum",
    "DriftStatusEnum",
    "SafetyStatusEnum",
    "ModelStageEnum",
    # Request models
    "PredictionRequest",
    "TrainingRequest",
    "BatchTrainingRequest",
    "RollbackRequest",
    "DriftCheckRequest",
    # Response models
    "PredictionResponse",
    "TrainingResponse",
    "BatchTrainingResponse",
    "ModelInfoResponse",
    "ModelVersionInfo",
    "ModelVersionListResponse",
    "RollbackResponse",
    "DriftStatusResponse",
    "SafetyStatusResponse",
    "HealthResponse",
    "ErrorResponse",
    "MetricsResponse",
    # WebSocket models
    "WebSocketMessage",
]
