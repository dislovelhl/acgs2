"""
ML Governance Engine - Random Forest scoring with online learning and feedback loops
"""

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import mlflow
import mlflow.sklearn
import numpy as np
import pandas as pd
import structlog
from evidently import ColumnMapping
from evidently.metrics import DataDriftTable
from evidently.report import Report
from river import tree
from sklearn.ensemble import RandomForestClassifier

from .models import (
    ABTest,
    DriftDetectionResult,
    FeatureVector,
    FeedbackSubmission,
    GovernanceDecision,
    GovernanceRequest,
    GovernanceResponse,
    ModelStatus,
    ModelType,
    ModelVersion,
)

logger = structlog.get_logger()


class MLGovernanceEngine:
    """Core ML engine for adaptive governance"""

    def __init__(
        self,
        redis_client=None,
        mlflow_tracking_uri: str = "sqlite:///mlflow.db",
        model_dir: str = "/tmp/ml_models"
    ):
        """
        Initialize the ML governance engine

        Args:
            redis_client: Redis client for caching and persistence
            mlflow_tracking_uri: MLflow tracking URI
            model_dir: Directory to store trained models
        """
        self.redis = redis_client
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)

        # MLflow setup
        mlflow.set_tracking_uri(mlflow_tracking_uri)

        # Model storage
        self.models: Dict[str, Any] = {}
        self.online_learners: Dict[str, Any] = {}
        self.active_versions: Dict[ModelType, str] = {}
        self.ab_tests: Dict[str, ABTest] = {}

        # Metrics tracking
        self.metrics = {
            "predictions": 0,
            "feedback_received": 0,
            "drift_checks": 0
        }

        # Initialize with baseline models
        self._initialize_baseline_models()

    def _initialize_baseline_models(self):
        """Initialize baseline models for cold start"""
        logger.info("Initializing baseline ML models")

        # Create baseline Random Forest model
        baseline_model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            n_jobs=-1
        )

        # Create baseline online learner (River)
        online_learner = tree.HoeffdingTreeClassifier()

        # Generate synthetic training data for initial model
        synthetic_data = self._generate_synthetic_training_data(1000)
        if synthetic_data:
            X, y = synthetic_data
            baseline_model.fit(X, y)

            # Save baseline model
            model_version = ModelVersion(
                version_id="baseline-v1.0",
                model_type=ModelType.RANDOM_FOREST,
                status=ModelStatus.ACTIVE,
                training_samples=len(X),
                created_at=datetime.now(timezone.utc)
            )

            self._save_model("baseline-v1.0", baseline_model, model_version)
            self.active_versions[ModelType.RANDOM_FOREST] = "baseline-v1.0"

        # Initialize online learner
        self.online_learners["online-v1.0"] = online_learner
        self.active_versions[ModelType.ONLINE_LEARNER] = "online-v1.0"

    def _generate_synthetic_training_data(self, n_samples: int) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        """Generate synthetic training data for model initialization"""
        try:
            np.random.seed(42)

            # Generate synthetic features
            features = []
            labels = []

            for _ in range(n_samples):
                # Create realistic feature vector
                intent_confidence = np.random.beta(2, 2)  # Beta distribution for confidence
                intent_class = np.random.choice(["helpful", "harmful", "neutral"])
                content_length = np.random.poisson(200)  # Poisson for content length
                time_of_day = np.random.randint(0, 24)
                day_of_week = np.random.randint(0, 7)
                risk_score = np.random.beta(1, 3)  # Low risk bias

                # Determine label based on features
                is_helpful = intent_class == "helpful" and intent_confidence > 0.7
                is_harmful = intent_class == "harmful" or risk_score > 0.8
                is_business_hours = 9 <= time_of_day <= 17 and day_of_week < 5

                if is_harmful:
                    decision = GovernanceDecision.DENY
                elif is_helpful and is_business_hours and risk_score < 0.3:
                    decision = GovernanceDecision.ALLOW
                elif intent_confidence > 0.8:
                    decision = GovernanceDecision.ALLOW
                else:
                    decision = GovernanceDecision.MONITOR

                # Convert to feature vector
                feature_vector = np.array([
                    intent_confidence,
                    1.0 if intent_class == "helpful" else 0.0,
                    1.0 if intent_class == "harmful" else 0.0,
                    content_length / 1000.0,
                    np.random.random(),  # has_urls
                    np.random.random(),  # has_email
                    np.random.random(),  # has_code
                    risk_score,  # toxicity_score
                    0.5,  # user_history_score
                    time_of_day / 24.0,
                    day_of_week / 7.0,
                    1.0 if is_business_hours else 0.0,
                    np.random.randint(0, 5),  # policy_match_count
                    np.random.randint(0, 2),  # policy_deny_count
                    np.random.randint(2, 8),  # policy_allow_count
                    risk_score,  # risk_level
                    np.random.randint(0, 3),  # compliance_flags
                    risk_score  # sensitivity_score
                ])

                features.append(feature_vector)
                labels.append(decision.value)

            X = np.array(features)
            y = np.array(labels)

            logger.info(f"Generated {n_samples} synthetic training samples")
            return X, y

        except Exception as e:
            logger.error("Failed to generate synthetic training data", error=str(e))
            return None

    async def predict(
        self,
        request: GovernanceRequest,
        use_ab_test: bool = False
    ) -> GovernanceResponse:
        """
        Make governance prediction using ML models

        Args:
            request: Governance request
            use_ab_test: Whether to use A/B testing

        Returns:
            Governance response with decision and confidence
        """
        start_time = datetime.now(timezone.utc)

        try:
            # Extract features from request
            features = self._extract_features(request)

            # Determine which model to use
            model_version, is_ab_test = self._select_model(use_ab_test)

            # Make prediction
            decision, confidence, reasoning = await self._make_prediction(
                features, model_version, request
            )

            # Track metrics
            self.metrics["predictions"] += 1

            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            response = GovernanceResponse(
                request_id=request.request_id,
                decision=decision,
                confidence=confidence,
                reasoning=reasoning,
                model_version=model_version,
                features=features,
                processing_time_ms=processing_time
            )

            # Log prediction for potential feedback
            await self._log_prediction(request, response, is_ab_test)

            logger.info(
                "Governance prediction made",
                request_id=request.request_id,
                decision=decision.value,
                confidence=confidence,
                model_version=model_version,
                processing_time_ms=processing_time
            )

            return response

        except Exception as e:
            logger.error(
                "Prediction failed",
                request_id=request.request_id,
                error=str(e)
            )
            # Fallback to conservative decision
            return GovernanceResponse(
                request_id=request.request_id,
                decision=GovernanceDecision.MONITOR,
                confidence=0.5,
                reasoning="Prediction failed, using conservative fallback",
                model_version="fallback",
                features=self._extract_features(request),
                processing_time_ms=(datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            )

    async def submit_feedback(self, feedback: FeedbackSubmission) -> bool:
        """
        Submit user feedback for model improvement

        Args:
            feedback: User feedback submission

        Returns:
            True if feedback was processed successfully
        """
        try:
            # Store feedback for batch retraining
            await self._store_feedback(feedback)

            # Update online learners immediately
            await self._update_online_learners(feedback)

            # Track metrics
            self.metrics["feedback_received"] += 1

            logger.info(
                "Feedback submitted",
                request_id=feedback.request_id,
                feedback_type=feedback.feedback_type.value,
                user_id=feedback.user_id
            )

            return True

        except Exception as e:
            logger.error(
                "Feedback submission failed",
                request_id=feedback.request_id,
                error=str(e)
            )
            return False

    async def check_drift(self, model_version: str) -> Optional[DriftDetectionResult]:
        """Check for model drift using recent data"""
        try:
            # Get recent predictions and feedback
            recent_data = await self._get_recent_data(hours=24)

            if not recent_data:
                return None

            # Use Evidently for drift detection
            reference_data = recent_data.get("reference", pd.DataFrame())
            current_data = recent_data.get("current", pd.DataFrame())

            if reference_data.empty or current_data.empty:
                return DriftDetectionResult(
                    check_id=f"drift-{datetime.now(timezone.utc).isoformat()}",
                    model_version=model_version,
                    drift_detected=False,
                    drift_score=0.0,
                    threshold=0.1,
                    details={"reason": "Insufficient data for drift detection"}
                )

            # Configure drift detection
            column_mapping = ColumnMapping(
                target="decision",
                prediction="prediction",
                numerical_features=["confidence", "feature_0", "feature_1"],
                categorical_features=[]
            )

            report = Report(metrics=[DataDriftTable()])
            report.run(reference_data=reference_data, current_data=current_data, column_mapping=column_mapping)

            # Extract drift score (simplified)
            drift_score = 0.0  # Would extract from report

            drift_detected = drift_score > 0.1  # Configurable threshold

            result = DriftDetectionResult(
                check_id=f"drift-{datetime.now(timezone.utc).isoformat()}",
                model_version=model_version,
                drift_detected=drift_detected,
                drift_score=drift_score,
                threshold=0.1,
                details={"report": "drift_analysis_report"}  # Would include actual report
            )

            self.metrics["drift_checks"] += 1

            if drift_detected:
                logger.warning(
                    "Model drift detected",
                    model_version=model_version,
                    drift_score=drift_score
                )

            return result

        except Exception as e:
            logger.error("Drift detection failed", error=str(e))
            return None

    def _extract_features(self, request: GovernanceRequest) -> FeatureVector:
        """Extract feature vector from governance request"""
        # This would integrate with intent classification and content analysis
        # For now, return a basic feature vector
        content = request.content
        context = request.context

        return FeatureVector(
            intent_confidence=context.get("intent_confidence", 0.5),
            intent_class=context.get("intent_class", "neutral"),
            intent_is_helpful=context.get("intent_class") == "helpful",
            intent_is_harmful=context.get("intent_class") == "harmful",
            content_length=len(content),
            content_has_urls="http" in content.lower(),
            content_has_email="@" in content,
            content_has_code="```" in content or "def " in content,
            content_toxicity_score=context.get("toxicity_score", 0.0),
            user_history_score=context.get("user_history_score", 0.5),
            time_of_day=datetime.now().hour,
            day_of_week=datetime.now().weekday(),
            is_business_hours=9 <= datetime.now().hour <= 17,
            policy_match_count=context.get("policy_matches", 0),
            policy_deny_count=context.get("policy_denies", 0),
            policy_allow_count=context.get("policy_allows", 0),
            risk_level=context.get("risk_level", "medium"),
            compliance_flags=context.get("compliance_flags", []),
            sensitivity_score=context.get("sensitivity_score", 0.0)
        )

    def _select_model(self, use_ab_test: bool = False) -> Tuple[str, bool]:
        """Select which model version to use"""
        if use_ab_test:
            # Check if request should use A/B test
            for ab_test in self.ab_tests.values():
                if ab_test.status == "active":
                    # Simple random selection based on traffic split
                    if np.random.random() < ab_test.traffic_split:
                        return ab_test.candidate_version, True
                    else:
                        return ab_test.champion_version, True

        # Use active model
        model_version = self.active_versions.get(ModelType.RANDOM_FOREST, "baseline-v1.0")
        return model_version, False

    async def _make_prediction(
        self,
        features: FeatureVector,
        model_version: str,
        request: GovernanceRequest
    ) -> Tuple[GovernanceDecision, float, str]:
        """Make prediction using specified model version"""
        try:
            # Get model
            model = self.models.get(model_version)
            if not model:
                logger.warning(f"Model {model_version} not found, using baseline")
                model = self.models.get("baseline-v1.0")

            if not model:
                # Fallback decision
                return GovernanceDecision.MONITOR, 0.5, "Using conservative fallback due to model unavailability"

            # Convert features to array
            X = features.to_numpy_array().reshape(1, -1)

            # Make prediction
            prediction_proba = model.predict_proba(X)[0]
            prediction = model.predict(X)[0]

            # Convert to GovernanceDecision
            decision = GovernanceDecision(prediction)

            # Get confidence (max probability)
            confidence = float(np.max(prediction_proba))

            # Generate reasoning
            reasoning = self._generate_reasoning(features, decision, confidence)

            return decision, confidence, reasoning

        except Exception as e:
            logger.error(f"Prediction failed for model {model_version}", error=str(e))
            return GovernanceDecision.MONITOR, 0.5, f"Prediction error: {str(e)}"

    def _generate_reasoning(
        self,
        features: FeatureVector,
        decision: GovernanceDecision,
        confidence: float
    ) -> str:
        """Generate human-readable reasoning for the decision"""
        reasons = []

        if features.intent_is_harmful:
            reasons.append("Content classified as potentially harmful")
        elif features.intent_is_helpful and features.intent_confidence > 0.8:
            reasons.append("High-confidence helpful intent detected")

        if features.content_toxicity_score > 0.7:
            reasons.append("High toxicity score detected")

        if not features.is_business_hours:
            reasons.append("Request made outside business hours")

        if features.risk_level == "high":
            reasons.append("High risk level assessment")

        if not reasons:
            reasons.append("Decision based on ML model analysis")

        reasoning = f"{decision.value.title()} decision with {confidence:.1%} confidence. "
        reasoning += "Reasons: " + "; ".join(reasons)

        return reasoning

    async def _store_feedback(self, feedback: FeedbackSubmission):
        """Store feedback for batch retraining"""
        # Store in Redis for immediate access
        if self.redis:
            feedback_key = f"feedback:{feedback.request_id}"
            await self.redis.set(
                feedback_key,
                feedback.json(),
                ex=86400 * 30  # 30 days
            )

        # Would also store in database for long-term analysis

    async def _update_online_learners(self, feedback: FeedbackSubmission):
        """Update online learners with new feedback"""
        try:
            # Get the original prediction
            prediction_data = await self._get_prediction(feedback.request_id)
            if not prediction_data:
                return

            # Extract features and correct label
            features = prediction_data["features"]
            correct_decision = feedback.correct_decision or prediction_data["decision"]

            # Update online learners
            for learner_name, learner in self.online_learners.items():
                if hasattr(learner, 'learn_one'):
                    # River-style online learning
                    learner.learn_one(features, correct_decision.value)

            logger.info("Updated online learners with feedback", request_id=feedback.request_id)

        except Exception as e:
            logger.error("Failed to update online learners", error=str(e))

    async def _get_prediction(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get stored prediction data"""
        if self.redis:
            prediction_key = f"prediction:{request_id}"
            prediction_data = await self.redis.get(prediction_key)
            if prediction_data:
                return json.loads(prediction_data)
        return None

    async def _log_prediction(
        self,
        request: GovernanceRequest,
        response: GovernanceResponse,
        is_ab_test: bool
    ):
        """Log prediction for feedback and analysis"""
        prediction_data = {
            "request_id": request.request_id,
            "features": response.features.dict(),
            "decision": response.decision.value,
            "confidence": response.confidence,
            "model_version": response.model_version,
            "ab_test": is_ab_test,
            "timestamp": response.timestamp.isoformat()
        }

        if self.redis:
            prediction_key = f"prediction:{request.request_id}"
            await self.redis.set(
                prediction_key,
                json.dumps(prediction_data),
                ex=86400 * 7  # 7 days
            )

    def _save_model(self, version_id: str, model: Any, metadata: ModelVersion):
        """Save trained model"""
        try:
            model_path = self.model_dir / f"{version_id}.pkl"
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)

            self.models[version_id] = model

            # Log to MLflow
            with mlflow.start_run(run_name=f"model_{version_id}"):
                mlflow.sklearn.log_model(model, "model")
                mlflow.log_param("version_id", version_id)
                mlflow.log_param("model_type", metadata.model_type.value)
                mlflow.log_metric("accuracy", metadata.accuracy)
                mlflow.log_metric("training_samples", metadata.training_samples)

            logger.info("Model saved", version_id=version_id, path=str(model_path))

        except Exception as e:
            logger.error("Failed to save model", version_id=version_id, error=str(e))

    async def _get_recent_data(self, hours: int) -> Optional[Dict[str, pd.DataFrame]]:
        """Get recent prediction data for drift detection"""
        # This would query recent predictions from database/cache
        # For now, return None (drift detection disabled)
        return None
