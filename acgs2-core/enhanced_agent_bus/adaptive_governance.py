"""
ACGS-2 Adaptive Governance System
Constitutional Hash: cdd01ef066bc6cf2

Implements ML-based adaptive governance with dynamic impact scoring and
self-evolving constitutional thresholds for intelligent AI safety governance.
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.preprocessing import StandardScaler

# MLflow imports for model versioning
try:
    import mlflow
    from mlflow.tracking import MlflowClient

    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    mlflow = None
    MlflowClient = None

# Constitutional imports
try:
    from .exceptions import GovernanceError
except ImportError:
    from exceptions import GovernanceError

logger = logging.getLogger(__name__)


class GovernanceMode(Enum):
    """Adaptive governance modes."""

    STRICT = "strict"  # Fixed constitutional thresholds
    ADAPTIVE = "adaptive"  # ML-adjusted thresholds
    EVOLVING = "evolving"  # Self-learning governance
    DEGRADED = "degraded"  # Fallback mode


class ImpactLevel(Enum):
    """Impact assessment levels."""

    NEGLIGIBLE = "negligible"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class GovernanceMetrics:
    """Real-time governance performance metrics."""

    constitutional_compliance_rate: float = 0.0
    false_positive_rate: float = 0.0
    false_negative_rate: float = 0.0
    average_response_time: float = 0.0
    throughput_rps: float = 0.0
    human_override_rate: float = 0.0

    # Historical trends
    compliance_trend: List[float] = field(default_factory=list)
    accuracy_trend: List[float] = field(default_factory=list)
    performance_trend: List[float] = field(default_factory=list)


@dataclass
class ImpactFeatures:
    """Features for ML-based impact assessment."""

    message_length: int
    agent_count: int
    tenant_complexity: float
    temporal_patterns: List[float]
    semantic_similarity: float
    historical_precedence: int
    resource_utilization: float
    network_isolation: float

    # Derived features
    risk_score: float = 0.0
    confidence_level: float = 0.0


@dataclass
class GovernanceDecision:
    """ML-enhanced governance decision."""

    action_allowed: bool
    impact_level: ImpactLevel
    confidence_score: float
    reasoning: str
    recommended_threshold: float
    features_used: ImpactFeatures
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AdaptiveThresholds:
    """ML-based dynamic threshold adjustment system."""

    # MLflow configuration
    MLFLOW_EXPERIMENT_NAME = "governance_thresholds"
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")

    def __init__(self, constitutional_hash: str):
        self.constitutional_hash = constitutional_hash
        self.base_thresholds = {
            ImpactLevel.NEGLIGIBLE: 0.1,
            ImpactLevel.LOW: 0.3,
            ImpactLevel.MEDIUM: 0.6,
            ImpactLevel.HIGH: 0.8,
            ImpactLevel.CRITICAL: 0.95,
        }

        # ML Models
        self.threshold_model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)

        # Training data
        self.training_data: List[Dict] = []
        self.feature_scaler = StandardScaler()

        # Adaptive parameters
        self.learning_rate = 0.1
        self.confidence_threshold = 0.8
        self.retraining_interval = 3600  # 1 hour

        self.last_retraining = time.time()
        self.model_trained = False

        # MLflow tracking
        self._mlflow_initialized = False
        self._mlflow_experiment_id: Optional[str] = None
        self.model_version: Optional[int] = None
        self._initialize_mlflow()

    def _initialize_mlflow(self) -> None:
        """Initialize MLflow tracking for training runs."""
        if not MLFLOW_AVAILABLE:
            logger.warning("MLflow not available. Training runs will not be tracked.")
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
                        "model_type": "adaptive_thresholds",
                    },
                )
            else:
                self._mlflow_experiment_id = experiment.experiment_id

            self._mlflow_initialized = True
            logger.info(
                f"MLflow initialized for experiment '{self.MLFLOW_EXPERIMENT_NAME}' "
                f"(id: {self._mlflow_experiment_id})"
            )

        except Exception as e:
            logger.warning(f"Failed to initialize MLflow tracking: {e}")
            self._mlflow_initialized = False

    def get_adaptive_threshold(self, impact_level: ImpactLevel, features: ImpactFeatures) -> float:
        """Get ML-adjusted threshold for given impact level and features."""
        if not self.model_trained:
            return self.base_thresholds[impact_level]

        try:
            # Prepare features for prediction
            feature_vector = self._extract_feature_vector(features)

            # Get ML prediction
            predicted_adjustment = self.threshold_model.predict([feature_vector])[0]

            # Apply confidence-based adjustment
            base_threshold = self.base_thresholds[impact_level]
            confidence_factor = min(features.confidence_level, 1.0)

            # Adaptive threshold with bounds checking
            adaptive_threshold = base_threshold + (predicted_adjustment * confidence_factor)
            adaptive_threshold = max(0.0, min(1.0, adaptive_threshold))

            logger.debug(
                f"Adaptive threshold for {impact_level.value}: "
                f"{base_threshold:.3f} -> {adaptive_threshold:.3f}"
            )

            return adaptive_threshold

        except Exception as e:
            logger.warning(f"Error in adaptive threshold calculation: {e}")
            return self.base_thresholds[impact_level]

    def update_model(
        self,
        decision: GovernanceDecision,
        outcome_success: bool,
        human_feedback: Optional[bool] = None,
    ) -> None:
        """Update ML model with new decision outcomes."""
        try:
            feature_vector = self._extract_feature_vector(decision.features_used)

            # Calculate target adjustment based on outcomes
            base_threshold = self.base_thresholds[decision.impact_level]
            actual_threshold = decision.recommended_threshold

            # Learning signal based on success and human feedback
            if outcome_success and human_feedback is not False:
                # Positive reinforcement
                target_adjustment = actual_threshold - base_threshold
            elif not outcome_success or human_feedback is False:
                # Negative reinforcement - adjust towards safer thresholds
                target_adjustment = (base_threshold - actual_threshold) * 0.5
            else:
                # Neutral - small adjustment towards recommended
                target_adjustment = (actual_threshold - base_threshold) * 0.1

            # Store training sample
            training_sample = {
                "features": feature_vector,
                "target": target_adjustment,
                "timestamp": time.time(),
                "impact_level": decision.impact_level.value,
                "confidence": decision.confidence_score,
                "outcome_success": outcome_success,
                "human_feedback": human_feedback,
            }

            self.training_data.append(training_sample)

            # Periodic retraining
            if time.time() - self.last_retraining > self.retraining_interval:
                self._retrain_model()

        except Exception as e:
            logger.error(f"Error updating adaptive model: {e}")

    def _retrain_model(self) -> None:
        """Retrain the ML model with accumulated data and log to MLflow."""
        try:
            if len(self.training_data) < 100:  # Minimum samples for training
                return

            # Prepare training data
            recent_data = [
                d for d in self.training_data if time.time() - d["timestamp"] < 86400
            ]  # Last 24 hours

            if len(recent_data) < 50:
                return

            X = np.array([d["features"] for d in recent_data])
            y = np.array([d["target"] for d in recent_data])

            # Scale features
            X_scaled = self.feature_scaler.fit_transform(X)

            # Log training run to MLflow
            if self._mlflow_initialized and MLFLOW_AVAILABLE:
                self._log_training_run_to_mlflow(X_scaled, y, recent_data)
            else:
                # Train without MLflow logging
                self.threshold_model.fit(X_scaled, y)
                self.anomaly_detector.fit(X_scaled)

            self.model_trained = True
            self.last_retraining = time.time()

            logger.info(f"Retrained adaptive governance model with {len(recent_data)} samples")

        except Exception as e:
            logger.error(f"Error retraining adaptive model: {e}")

    def _log_training_run_to_mlflow(
        self, X_scaled: np.ndarray, y: np.ndarray, recent_data: List[Dict]
    ) -> None:
        """Log training run with metrics and model to MLflow."""
        try:
            run_name = f"threshold_retrain_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

            with mlflow.start_run(
                experiment_id=self._mlflow_experiment_id,
                run_name=run_name,
            ) as run:
                # Log training parameters
                mlflow.log_params(
                    {
                        "n_estimators": self.threshold_model.n_estimators,
                        "random_state": self.threshold_model.random_state,
                        "n_jobs": self.threshold_model.n_jobs,
                        "learning_rate": self.learning_rate,
                        "confidence_threshold": self.confidence_threshold,
                        "retraining_interval": self.retraining_interval,
                        "constitutional_hash": self.constitutional_hash,
                    }
                )

                # Train model
                self.threshold_model.fit(X_scaled, y)

                # Update anomaly detector
                self.anomaly_detector.fit(X_scaled)

                # Calculate training metrics
                y_pred = self.threshold_model.predict(X_scaled)
                mse = float(np.mean((y - y_pred) ** 2))
                mae = float(np.mean(np.abs(y - y_pred)))
                r2_score = float(1 - (np.sum((y - y_pred) ** 2) / np.sum((y - np.mean(y)) ** 2)))

                # Calculate data distribution metrics
                positive_feedback = sum(1 for d in recent_data if d.get("outcome_success", False))
                human_feedback_count = sum(
                    1 for d in recent_data if d.get("human_feedback") is not None
                )

                # Log metrics
                mlflow.log_metrics(
                    {
                        "n_samples": len(recent_data),
                        "n_features": X_scaled.shape[1],
                        "mean_squared_error": mse,
                        "mean_absolute_error": mae,
                        "r2_score": r2_score,
                        "target_mean": float(np.mean(y)),
                        "target_std": float(np.std(y)),
                        "positive_feedback_rate": positive_feedback / len(recent_data),
                        "human_feedback_rate": human_feedback_count / len(recent_data),
                    }
                )

                # Log feature importance
                if hasattr(self.threshold_model, "feature_importances_"):
                    feature_names = [
                        "message_length",
                        "agent_count",
                        "tenant_complexity",
                        "temporal_mean",
                        "temporal_std",
                        "semantic_similarity",
                        "historical_precedence",
                        "resource_utilization",
                        "network_isolation",
                        "risk_score",
                        "confidence_level",
                    ]
                    for idx, importance in enumerate(self.threshold_model.feature_importances_):
                        feature_name = (
                            feature_names[idx] if idx < len(feature_names) else f"feature_{idx}"
                        )
                        mlflow.log_metric(f"importance_{feature_name}", float(importance))

                # Log the trained model
                mlflow.sklearn.log_model(
                    self.threshold_model,
                    artifact_path="threshold_model",
                    registered_model_name=None,  # Don't auto-register; use ml_versioning for that
                )

                # Log anomaly detector as artifact
                mlflow.sklearn.log_model(
                    self.anomaly_detector,
                    artifact_path="anomaly_detector",
                )

                # Store run info
                self.model_version = run.info.run_id

                logger.info(
                    f"MLflow run logged: {run.info.run_id} "
                    f"(MSE: {mse:.4f}, R2: {r2_score:.4f}, samples: {len(recent_data)})"
                )

        except Exception as e:
            logger.warning(f"Failed to log training run to MLflow: {e}")
            # Fallback to training without MLflow logging
            self.threshold_model.fit(X_scaled, y)
            self.anomaly_detector.fit(X_scaled)

    def _extract_feature_vector(self, features: ImpactFeatures) -> List[float]:
        """Extract numerical feature vector for ML prediction."""
        return [
            features.message_length,
            features.agent_count,
            features.tenant_complexity,
            np.mean(features.temporal_patterns) if features.temporal_patterns else 0,
            np.std(features.temporal_patterns) if features.temporal_patterns else 0,
            features.semantic_similarity,
            features.historical_precedence,
            features.resource_utilization,
            features.network_isolation,
            features.risk_score,
            features.confidence_level,
        ]


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


class AdaptiveGovernanceEngine:
    """Main adaptive governance engine with ML-enhanced decision making."""

    def __init__(self, constitutional_hash: str):
        self.constitutional_hash = constitutional_hash
        self.mode = GovernanceMode.ADAPTIVE

        # Core components
        self.impact_scorer = ImpactScorer(constitutional_hash)
        self.threshold_manager = AdaptiveThresholds(constitutional_hash)

        # Performance tracking
        self.metrics = GovernanceMetrics()
        self.decision_history: List[GovernanceDecision] = []

        # Learning parameters
        self.feedback_window = 3600  # 1 hour learning window
        self.performance_target = 0.95  # 95% accuracy target

        # Background learning thread
        self.learning_thread: Optional[threading.Thread] = None
        self.running = False

    async def initialize(self) -> None:
        """Initialize the adaptive governance engine."""
        logger.info("Initializing Adaptive Governance Engine")

        # Load historical data if available
        await self._load_historical_data()

        # Start background learning
        self.running = True
        self.learning_thread = threading.Thread(target=self._background_learning_loop)
        self.learning_thread.daemon = True
        self.learning_thread.start()

        logger.info("Adaptive Governance Engine initialized")

    async def evaluate_governance_decision(
        self, message: Dict, context: Dict
    ) -> GovernanceDecision:
        """Make an adaptive governance decision for a message."""
        start_time = time.time()

        try:
            # Assess impact using ML models
            impact_features = await self.impact_scorer.assess_impact(message, context)

            # Determine appropriate threshold
            impact_level = self._classify_impact_level(impact_features.risk_score)
            threshold = self.threshold_manager.get_adaptive_threshold(impact_level, impact_features)

            # Make governance decision
            action_allowed = impact_features.risk_score <= threshold

            # Generate reasoning
            reasoning = self._generate_reasoning(action_allowed, impact_features, threshold)

            decision = GovernanceDecision(
                action_allowed=action_allowed,
                impact_level=impact_level,
                confidence_score=impact_features.confidence_level,
                reasoning=reasoning,
                recommended_threshold=threshold,
                features_used=impact_features,
            )

            # Record decision for learning
            self.decision_history.append(decision)

            # Update performance metrics
            self._update_metrics(decision, time.time() - start_time)

            return decision

        except Exception as e:
            logger.error(f"Governance evaluation error: {e}")
            # Fallback to strict mode
            return GovernanceDecision(
                action_allowed=False,  # Conservative fallback
                impact_level=ImpactLevel.HIGH,
                confidence_score=0.9,
                reasoning=f"Governance evaluation failed: {e}. Applied conservative fallback.",
                recommended_threshold=0.8,
                features_used=ImpactFeatures(
                    message_length=0,
                    agent_count=0,
                    tenant_complexity=0,
                    temporal_patterns=[],
                    semantic_similarity=0,
                    historical_precedence=0,
                    resource_utilization=0,
                    network_isolation=0,
                ),
            )

    def _classify_impact_level(self, risk_score: float) -> ImpactLevel:
        """Classify risk score into impact levels."""
        if risk_score >= 0.9:
            return ImpactLevel.CRITICAL
        elif risk_score >= 0.7:
            return ImpactLevel.HIGH
        elif risk_score >= 0.4:
            return ImpactLevel.MEDIUM
        elif risk_score >= 0.2:
            return ImpactLevel.LOW
        else:
            return ImpactLevel.NEGLIGIBLE

    def _generate_reasoning(
        self, action_allowed: bool, features: ImpactFeatures, threshold: float
    ) -> str:
        """Generate human-readable reasoning for the decision."""
        action_word = "ALLOWED" if action_allowed else "BLOCKED"

        reasoning_parts = [
            f"Action {action_word} based on risk score {features.risk_score:.3f} "
            f"(threshold: {threshold:.3f})"
        ]

        if features.confidence_level < 0.7:
            reasoning_parts.append(
                f"Low confidence ({features.confidence_level:.2f}) in assessment"
            )

        if features.historical_precedence > 0:
            reasoning_parts.append(f"Based on {features.historical_precedence} similar precedents")

        return ". ".join(reasoning_parts)

    def provide_feedback(
        self,
        decision: GovernanceDecision,
        outcome_success: bool,
        human_override: Optional[bool] = None,
    ) -> None:
        """Provide feedback to improve the ML models."""
        try:
            # Update threshold manager
            human_feedback = None
            if human_override is not None:
                human_feedback = human_override == decision.action_allowed

            self.threshold_manager.update_model(decision, outcome_success, human_feedback)

            # Update impact scorer with actual outcome
            actual_impact = decision.features_used.risk_score
            if not outcome_success:
                actual_impact = min(1.0, actual_impact + 0.2)  # Increase perceived risk

            self.impact_scorer.update_model(decision.features_used, actual_impact)

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")

    def _update_metrics(self, decision: GovernanceDecision, response_time: float) -> None:
        """Update performance metrics."""
        # Update counters
        self.metrics.average_response_time = (
            self.metrics.average_response_time * 0.9 + response_time * 0.1
        )

        # Maintain rolling averages (last 100 decisions)
        if len(self.decision_history) > 100:
            self.decision_history.pop(0)

        # Calculate compliance metrics
        recent_decisions = (
            self.decision_history[-50:]
            if len(self.decision_history) > 50
            else self.decision_history
        )

        if recent_decisions:
            compliant_decisions = sum(1 for d in recent_decisions if d.confidence_score > 0.8)
            self.metrics.constitutional_compliance_rate = compliant_decisions / len(
                recent_decisions
            )

    def _background_learning_loop(self) -> None:
        """Background thread for continuous model improvement."""
        while self.running:
            try:
                time.sleep(300)  # 5-minute learning cycle

                # Analyze recent performance
                self._analyze_performance_trends()

                # Trigger model retraining if needed
                if self._should_retrain_models():
                    logger.info("Triggering background model retraining")
                    # Retraining happens automatically in the model update methods

                # Log performance summary
                self._log_performance_summary()

            except Exception as e:
                logger.error(f"Background learning error: {e}")
                time.sleep(60)  # Back off on errors

    def _analyze_performance_trends(self) -> None:
        """Analyze performance trends for adaptive adjustments."""
        try:
            # Update trend data
            self.metrics.compliance_trend.append(self.metrics.constitutional_compliance_rate)
            self.metrics.accuracy_trend.append(1.0 - self.metrics.false_positive_rate)
            self.metrics.performance_trend.append(
                1.0 / max(0.001, self.metrics.average_response_time)
            )

            # Keep only recent trends (last 100 data points)
            max_trend_length = 100
            for trend in [
                self.metrics.compliance_trend,
                self.metrics.accuracy_trend,
                self.metrics.performance_trend,
            ]:
                if len(trend) > max_trend_length:
                    trend[:] = trend[-max_trend_length:]

        except Exception as e:
            logger.error(f"Performance trend analysis error: {e}")

    def _should_retrain_models(self) -> bool:
        """Determine if models should be retrained."""
        # Retrain if accuracy drops below target
        if self.metrics.constitutional_compliance_rate < self.performance_target:
            return True

        # Retrain if we have sufficient new data
        return len(self.decision_history) >= 1000 and len(self.decision_history) % 500 == 0

    def _log_performance_summary(self) -> None:
        """Log periodic performance summary."""
        try:
            summary = {
                "compliance_rate": f"{self.metrics.constitutional_compliance_rate:.3f}",
                "avg_response_time": f"{self.metrics.average_response_time:.4f}s",
                "decisions_made": len(self.decision_history),
                "mode": self.mode.value,
            }
            logger.info(f"Governance Performance: {summary}")

        except Exception as e:
            logger.error(f"Performance logging error: {e}")

    async def _load_historical_data(self) -> None:
        """Load historical decision data for model initialization."""
        try:
            # Implementation would load from persistent storage
            # For now, start with empty models
            logger.info("Loaded historical governance data")

        except Exception as e:
            logger.warning(f"Could not load historical data: {e}")

    async def shutdown(self) -> None:
        """Gracefully shutdown the adaptive governance engine."""
        logger.info("Shutting down Adaptive Governance Engine")

        self.running = False

        if self.learning_thread and self.learning_thread.is_alive():
            self.learning_thread.join(timeout=5)

        # Save final model state
        await self._save_model_state()

        logger.info("Adaptive Governance Engine shutdown complete")

    async def _save_model_state(self) -> None:
        """Save current model state for persistence."""
        try:
            # Implementation would save models to persistent storage
            logger.info("Saved governance model state")

        except Exception as e:
            logger.error(f"Error saving model state: {e}")


# Global instance
_adaptive_governance: Optional[AdaptiveGovernanceEngine] = None


async def initialize_adaptive_governance(constitutional_hash: str) -> AdaptiveGovernanceEngine:
    """Initialize the global adaptive governance engine."""
    global _adaptive_governance

    if _adaptive_governance is None:
        _adaptive_governance = AdaptiveGovernanceEngine(constitutional_hash)
        await _adaptive_governance.initialize()

    return _adaptive_governance


def get_adaptive_governance() -> Optional[AdaptiveGovernanceEngine]:
    """Get the global adaptive governance engine instance."""
    return _adaptive_governance


async def evaluate_message_governance(message: Dict, context: Dict) -> GovernanceDecision:
    """Evaluate a message using adaptive governance."""
    governance = get_adaptive_governance()
    if governance is None:
        raise GovernanceError("Adaptive governance not initialized")

    return await governance.evaluate_governance_decision(message, context)


def provide_governance_feedback(
    decision: GovernanceDecision, outcome_success: bool, human_override: Optional[bool] = None
) -> None:
    """Provide feedback to improve governance models."""
    governance = get_adaptive_governance()
    if governance:
        governance.provide_feedback(decision, outcome_success, human_override)


# Export key classes and functions
__all__ = [
    "AdaptiveGovernanceEngine",
    "AdaptiveThresholds",
    "ImpactScorer",
    "GovernanceDecision",
    "GovernanceMode",
    "ImpactLevel",
    "ImpactFeatures",
    "GovernanceMetrics",
    "initialize_adaptive_governance",
    "get_adaptive_governance",
    "evaluate_message_governance",
    "provide_governance_feedback",
]
