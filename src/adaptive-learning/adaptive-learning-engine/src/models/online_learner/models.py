"""
Online Learner Models.
Constitutional Hash: cdd01ef066bc6cf2
"""

import time
from dataclasses import dataclass, field
from typing import Dict

from .enums import ModelState


@dataclass
class PredictionResult:
    """Result from a single prediction."""

    prediction: int
    confidence: float
    probabilities: Dict[int, float]
    model_state: ModelState
    sample_count: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class TrainingResult:
    """Result from a single training update."""

    success: bool
    sample_count: int
    current_accuracy: float
    model_state: ModelState
    message: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class ModelMetrics:
    """Current metrics for the online learner."""

    accuracy: float
    sample_count: int
    model_state: ModelState
    recent_accuracy: float
    last_update_time: float
    predictions_count: int
    model_type: str
