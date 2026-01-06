"""
Online Learner Enums.
Constitutional Hash: cdd01ef066bc6cf2
"""

from enum import Enum


class ModelType(Enum):
    """Supported online learning model types."""

    LOGISTIC_REGRESSION = "logistic_regression"
    PERCEPTRON = "perceptron"
    PA_CLASSIFIER = "pa_classifier"


class ModelState(Enum):
    """Current state of the online learner."""

    COLD_START = "cold_start"
    WARMING = "warming"
    ACTIVE = "active"
    PAUSED = "paused"
