"""
Online Learner Pipeline Builder.
Constitutional Hash: cdd01ef066bc6cf2
"""

import logging
from river import compose, linear_model, optim, preprocessing
from .enums import ModelType

logger = logging.getLogger(__name__)


class PipelineBuilder:
    """Helper class to build River model pipelines for the OnlineLearner."""

    @staticmethod
    def build_pipeline(
        model_type: ModelType,
        learning_rate: float,
        l2_regularization: float,
    ) -> compose.Pipeline:
        """Build the River model pipeline with preprocessing.

        Args:
            model_type: Type of online learning model to use.
            learning_rate: Learning rate for the optimizer.
            l2_regularization: L2 regularization strength.

        Returns:
            Composed pipeline with preprocessing and model.
        """
        # Select the base model based on configuration
        if model_type == ModelType.LOGISTIC_REGRESSION:
            model = linear_model.LogisticRegression(
                optimizer=optim.SGD(learning_rate),
                l2=l2_regularization,
            )

        elif model_type == ModelType.PERCEPTRON:
            model = linear_model.Perceptron(l2=l2_regularization)

        elif model_type == ModelType.PA_CLASSIFIER:
            # Passive-Aggressive Classifier
            model = linear_model.PAClassifier(C=learning_rate)

        else:
            # Default to logistic regression
            logger.warning(f"Unknown model type {model_type}, defaulting to Logistic Regression")
            model = linear_model.LogisticRegression(
                optimizer=optim.SGD(learning_rate),
                l2=l2_regularization,
            )

        # Feature preprocessing: Online StandardScaler
        pipeline = compose.Pipeline(
            ("scaler", preprocessing.StandardScaler()),
            ("model", model),
        )

        return pipeline
