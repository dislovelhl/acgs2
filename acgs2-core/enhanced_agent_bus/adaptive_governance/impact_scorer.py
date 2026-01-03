"""
ACGS-2 Impact Scorer
Constitutional Hash: cdd01ef066bc6cf2

Implements ML-based impact assessment for messages and actions with
hybrid rule-based and model-based risk scoring.

This module contains:
- ImpactScorer: Hybrid impact assessment system combining rule-based heuristics
  with ML models (IsolationForest) for risk prediction.

Key Features:
- Asynchronous feature extraction from messages
- Hybrid scoring: ML-based + rule-based fallback
- Confidence estimation for predictions
- MLflow integration for model versioning
- Adaptive model retraining based on feedback
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestRegressor

# MLflow imports for model versioning
try:
    import mlflow

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None

# Import data models from local package
from .models import ImpactFeatures

logger = logging.getLogger(__name__)


class ImpactScorer:
    """ML-based impact assessment system."""

    # MLflow configuration
    MLFLOW_EXPERIMENT_NAME = "governance_impact_scorer"
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    MLFLOW_MODEL_NAME = "governance_impact_scorer"

    def __init__(self, constitutional_hash: str):
        self.constitutional_hash = constitutional_hash

        # ML Models for impact assessment
        self.impact_classifier = RandomForestRegressor(
            n_estimators=50, max_depth=10, random_state=42
        )

        # Feature importance weights (learned over time)
        self.feature_weights = {
            "message_length": 0.1,
            "agent_count": 0.15,
            "tenant_complexity": 0.2,
            "temporal_patterns": 0.1,
            "semantic_similarity": 0.25,
            "historical_precedence": 0.1,
            "resource_utilization": 0.05,
            "network_isolation": 0.05,
        }

        # Training data
        self.training_samples: List[Tuple[ImpactFeatures, float]] = []
        self.model_trained = False

        # MLflow tracking
        self._mlflow_initialized = False
        self._mlflow_experiment_id: Optional[str] = None
        self.model_version: Optional[str] = None
        self._initialize_mlflow()

    def _initialize_mlflow(self) -> None:
        """Initialize MLflow tracking for training runs."""
        if not MLFLOW_AVAILABLE:
            logger.warning("MLflow not available. ImpactScorer training runs will not be tracked.")
            return

        try:
            mlflow.set_tracking_uri(self.MLFLOW_TRACKING_URI)

            # Create or get experiment
            experiment = mlflow.get_experiment_by_name(self.MLFLOW_EXPERIMENT_NAME)
            if experiment is None:
                self._mlflow_experiment_id = mlflow.create_experiment(
                    self.MLFLOW_EXPERIMENT_NAME,
                    tags={
                        "constitutional_hash": self.constitutional_hash,
                        "model_type": "impact_scorer",
                    },
                )
            else:
                self._mlflow_experiment_id = experiment.experiment_id

            self._mlflow_initialized = True
            logger.info(
                f"MLflow initialized for ImpactScorer experiment '{self.MLFLOW_EXPERIMENT_NAME}' "
                f"(id: {self._mlflow_experiment_id})"
            )

        except Exception as e:
            logger.warning(f"Failed to initialize MLflow tracking for ImpactScorer: {e}")
            self._mlflow_initialized = False

    async def assess_impact(self, message: Dict, context: Dict) -> ImpactFeatures:
        """Assess message impact using ML models and contextual analysis."""
        try:
            # Extract raw features
            features = await self._extract_features(message, context)

            # Apply ML-based scoring if model is trained
            if self.model_trained:
                features.risk_score = self._predict_risk_score(features)
                features.confidence_level = self._calculate_confidence(features)
            else:
                # Fallback to rule-based scoring
                features.risk_score = self._rule_based_risk_score(features)
                features.confidence_level = 0.7  # Moderate confidence for rule-based

            return features

        except Exception as e:
            logger.error(f"Error in impact assessment: {e}")
            # Return safe defaults
            return ImpactFeatures(
                message_length=len(str(message.get("content", ""))),
                agent_count=1,
                tenant_complexity=0.5,
                temporal_patterns=[],
                semantic_similarity=0.5,
                historical_precedence=0,
                resource_utilization=0.1,
                network_isolation=1.0,
                risk_score=0.1,  # Conservative default
                confidence_level=0.5,
            )

    async def _extract_features(self, message: Dict, context: Dict) -> ImpactFeatures:
        """Extract comprehensive features for impact assessment."""
        content = str(message.get("content", ""))
        tenant_id = message.get("tenant_id", "default")

        # Basic content features
        message_length = len(content)
        agent_count = len(context.get("active_agents", []))

        # Tenant complexity (based on isolation level, user count, etc.)
        tenant_complexity = await self._calculate_tenant_complexity(tenant_id, context)

        # Temporal patterns (message frequency, time-based risk)
        temporal_patterns = await self._analyze_temporal_patterns(message, context)

        # Semantic analysis (content risk assessment)
        semantic_similarity = await self._analyze_semantic_similarity(content, context)

        # Historical precedence (similar past decisions)
        historical_precedence = await self._check_historical_precedence(message, context)

        # Resource utilization impact
        resource_utilization = await self._assess_resource_impact(message, context)

        # Network isolation (tenant/data isolation strength)
        network_isolation = await self._measure_isolation_strength(tenant_id, context)

        return ImpactFeatures(
            message_length=message_length,
            agent_count=agent_count,
            tenant_complexity=tenant_complexity,
            temporal_patterns=temporal_patterns,
            semantic_similarity=semantic_similarity,
            historical_precedence=historical_precedence,
            resource_utilization=resource_utilization,
            network_isolation=network_isolation,
        )

    async def _calculate_tenant_complexity(self, tenant_id: str, context: Dict) -> float:
        """Calculate tenant complexity score."""
        # Implementation would analyze tenant structure, user roles, etc.
        return 0.5  # Placeholder

    async def _analyze_temporal_patterns(self, message: Dict, context: Dict) -> List[float]:
        """Analyze temporal patterns for risk assessment."""
        # Implementation would analyze message timing patterns
        return [0.1, 0.2, 0.15]  # Placeholder

    async def _analyze_semantic_similarity(self, content: str, context: Dict) -> float:
        """Analyze semantic content for risk assessment."""
        # Implementation would use NLP models for content analysis
        return 0.3  # Placeholder - conservative estimate

    async def _check_historical_precedence(self, message: Dict, context: Dict) -> int:
        """Check historical precedence for similar decisions."""
        # Implementation would query historical decision database
        return 1  # Placeholder

    async def _assess_resource_impact(self, message: Dict, context: Dict) -> float:
        """Assess resource utilization impact."""
        # Implementation would analyze expected resource consumption
        return 0.2  # Placeholder

    async def _measure_isolation_strength(self, tenant_id: str, context: Dict) -> float:
        """Measure network/data isolation strength."""
        # Implementation would check isolation configurations
        return 0.9  # Placeholder - high isolation assumed

    def _predict_risk_score(self, features: ImpactFeatures) -> float:
        """Predict risk score using trained ML model."""
        if not self.model_trained:
            return self._rule_based_risk_score(features)

        try:
            feature_vector = [
                features.message_length,
                features.agent_count,
                features.tenant_complexity,
                np.mean(features.temporal_patterns) if features.temporal_patterns else 0,
                features.semantic_similarity,
                features.historical_precedence,
                features.resource_utilization,
                features.network_isolation,
            ]

            prediction = self.impact_classifier.predict([feature_vector])[0]
            return max(0.0, min(1.0, prediction))

        except Exception as e:
            logger.warning(f"ML prediction failed, using rule-based: {e}")
            return self._rule_based_risk_score(features)

    def _rule_based_risk_score(self, features: ImpactFeatures) -> float:
        """Rule-based risk scoring as fallback."""
        score = 0.0

        # Length-based risk
        if features.message_length > 10000:
            score += 0.3
        elif features.message_length > 1000:
            score += 0.1

        # Agent count risk
        if features.agent_count > 10:
            score += 0.2
        elif features.agent_count > 5:
            score += 0.1

        # Tenant complexity
        score += features.tenant_complexity * 0.2

        # Resource impact
        score += features.resource_utilization * 0.3

        # Semantic risk (conservative estimate)
        score += features.semantic_similarity * 0.2

        return min(1.0, score)

    def _calculate_confidence(self, features: ImpactFeatures) -> float:
        """Calculate confidence level in the assessment."""
        # Base confidence on feature completeness and quality
        confidence = 0.5

        # Boost confidence with more data
        if features.historical_precedence > 0:
            confidence += 0.1
        if len(features.temporal_patterns) > 0:
            confidence += 0.1
        if features.semantic_similarity > 0:
            confidence += 0.2

        return min(1.0, confidence)

    def update_model(self, features: ImpactFeatures, actual_impact: float) -> None:
        """Update ML model with new training data."""
        try:
            self.training_samples.append((features, actual_impact))

            # Retrain periodically
            if len(self.training_samples) >= 100 and len(self.training_samples) % 50 == 0:
                self._retrain_model()

        except Exception as e:
            logger.error(f"Error updating impact scorer model: {e}")

    def _retrain_model(self) -> None:
        """Retrain the impact assessment model and log to MLflow."""
        try:
            if len(self.training_samples) < 50:
                return

            # Prepare training data
            X = []
            y = []
            recent_samples = self.training_samples[-500:]  # Last 500 samples

            for features, actual_impact in recent_samples:
                feature_vector = [
                    features.message_length,
                    features.agent_count,
                    features.tenant_complexity,
                    np.mean(features.temporal_patterns) if features.temporal_patterns else 0,
                    features.semantic_similarity,
                    features.historical_precedence,
                    features.resource_utilization,
                    features.network_isolation,
                ]
                X.append(feature_vector)
                y.append(actual_impact)

            X_array = np.array(X)
            y_array = np.array(y)

            # Log training run to MLflow
            if self._mlflow_initialized and MLFLOW_AVAILABLE:
                self._log_training_run_to_mlflow(X_array, y_array, recent_samples)
            else:
                # Train without MLflow logging
                self.impact_classifier.fit(X_array, y_array)

            self.model_trained = True

            logger.info(f"Retrained impact scorer with {len(X)} samples")

        except Exception as e:
            logger.error(f"Error retraining impact scorer: {e}")

    def _log_training_run_to_mlflow(
        self, X: np.ndarray, y: np.ndarray, recent_samples: List[Tuple[ImpactFeatures, float]]
    ) -> None:
        """Log training run with metrics and model to MLflow."""
        try:
            run_name = (
                f"impact_scorer_retrain_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
            )

            with mlflow.start_run(
                experiment_id=self._mlflow_experiment_id,
                run_name=run_name,
            ) as run:
                # Log training parameters
                mlflow.log_params(
                    {
                        "n_estimators": self.impact_classifier.n_estimators,
                        "max_depth": self.impact_classifier.max_depth,
                        "random_state": self.impact_classifier.random_state,
                        "constitutional_hash": self.constitutional_hash,
                        "n_samples": len(recent_samples),
                        "n_features": X.shape[1],
                    }
                )

                # Log feature weights
                for feature_name, weight in self.feature_weights.items():
                    mlflow.log_param(f"weight_{feature_name}", weight)

                # Train model
                self.impact_classifier.fit(X, y)

                # Calculate training metrics
                y_pred = self.impact_classifier.predict(X)
                mse = float(np.mean((y - y_pred) ** 2))
                mae = float(np.mean(np.abs(y - y_pred)))

                # Avoid division by zero in R2 calculation
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                if ss_tot > 0:
                    r2_score = float(1 - (np.sum((y - y_pred) ** 2) / ss_tot))
                else:
                    r2_score = 0.0

                # Calculate impact distribution metrics
                high_impact_count = sum(1 for _, impact in recent_samples if impact >= 0.7)
                medium_impact_count = sum(1 for _, impact in recent_samples if 0.3 <= impact < 0.7)
                low_impact_count = sum(1 for _, impact in recent_samples if impact < 0.3)

                # Log metrics
                mlflow.log_metrics(
                    {
                        "n_samples": len(recent_samples),
                        "n_features": X.shape[1],
                        "mean_squared_error": mse,
                        "mean_absolute_error": mae,
                        "r2_score": r2_score,
                        "target_mean": float(np.mean(y)),
                        "target_std": float(np.std(y)),
                        "high_impact_rate": high_impact_count / len(recent_samples),
                        "medium_impact_rate": medium_impact_count / len(recent_samples),
                        "low_impact_rate": low_impact_count / len(recent_samples),
                    }
                )

                # Log feature importance
                if hasattr(self.impact_classifier, "feature_importances_"):
                    feature_names = [
                        "message_length",
                        "agent_count",
                        "tenant_complexity",
                        "temporal_mean",
                        "semantic_similarity",
                        "historical_precedence",
                        "resource_utilization",
                        "network_isolation",
                    ]
                    for idx, importance in enumerate(self.impact_classifier.feature_importances_):
                        feature_name = (
                            feature_names[idx] if idx < len(feature_names) else f"feature_{idx}"
                        )
                        mlflow.log_metric(f"importance_{feature_name}", float(importance))

                # Log the trained model
                mlflow.sklearn.log_model(
                    self.impact_classifier,
                    artifact_path="impact_classifier",
                    registered_model_name=self.MLFLOW_MODEL_NAME,
                )

                # Store run info
                self.model_version = run.info.run_id

                logger.info(
                    f"MLflow run logged for ImpactScorer: {run.info.run_id} "
                    f"(MSE: {mse:.4f}, R2: {r2_score:.4f}, samples: {len(recent_samples)})"
                )

        except Exception as e:
            logger.warning(f"Failed to log ImpactScorer training run to MLflow: {e}")
            # Fallback to training without MLflow logging
            self.impact_classifier.fit(X, y)


__all__ = ["ImpactScorer"]
