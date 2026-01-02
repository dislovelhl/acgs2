# ACGS-2 Adaptive Learning Engine - Models Module
"""River online learning model implementations and model manager for hot-swapping."""

from src.models.model_manager import (
    ModelManager,
    ModelVersion,
    SwapResult,
    SwapStatus,
)
from src.models.online_learner import (
    ModelMetrics,
    ModelState,
    ModelType,
    OnlineLearner,
    PredictionResult,
    TrainingResult,
)

__all__ = [
    # Model Manager
    "ModelManager",
    "ModelVersion",
    "SwapResult",
    "SwapStatus",
    # Online Learner
    "OnlineLearner",
    "ModelType",
    "ModelState",
    "PredictionResult",
    "TrainingResult",
    "ModelMetrics",
]
