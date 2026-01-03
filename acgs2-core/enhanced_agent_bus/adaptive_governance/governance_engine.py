"""
ACGS-2 Adaptive Governance Engine
Constitutional Hash: cdd01ef066bc6cf2

Core governance engine implementing ML-based adaptive governance with dynamic
impact scoring, threshold management, and constitutional compliance evaluation.

This module contains:
- AdaptiveGovernanceEngine: Main governance orchestration engine integrating
  impact scoring, threshold management, drift detection, online learning,
  and A/B testing for intelligent AI safety governance.

Key Features:
- Integration with ImpactScorer and AdaptiveThresholds
- Drift detection for model and data distribution monitoring
- Online learning with River ML for continuous adaptation
- A/B testing support for model comparison
- Feedback loop integration for governance improvement
- Constitutional compliance verification
- Thread-safe operation with locking mechanisms
"""

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np

# Constitutional imports
try:
    from ..exceptions import GovernanceError  # noqa: F401
except ImportError:
    from exceptions import GovernanceError  # noqa: F401

# Feedback handler imports
try:
    from ..feedback_handler import (
        FeedbackEvent,
        FeedbackHandler,
        FeedbackType,
        OutcomeStatus,
        get_feedback_handler,
    )

    FEEDBACK_HANDLER_AVAILABLE = True
except ImportError:
    try:
        from feedback_handler import (
            FeedbackEvent,
            FeedbackHandler,
            FeedbackType,
            OutcomeStatus,
            get_feedback_handler,
        )

        FEEDBACK_HANDLER_AVAILABLE = True
    except ImportError:
        FEEDBACK_HANDLER_AVAILABLE = False
        FeedbackEvent = None
        FeedbackHandler = None
        FeedbackType = None
        OutcomeStatus = None
        get_feedback_handler = None

# Drift monitoring imports
try:
    from ..drift_monitoring import (
        DRIFT_CHECK_INTERVAL_HOURS,
        DriftDetector,
        DriftReport,
        DriftSeverity,
        DriftStatus,
        get_drift_detector,
    )

    DRIFT_MONITORING_AVAILABLE = True
except ImportError:
    try:
        from drift_monitoring import (
            DRIFT_CHECK_INTERVAL_HOURS,
            DriftDetector,
            DriftReport,
            DriftSeverity,
            DriftStatus,
            get_drift_detector,
        )

        DRIFT_MONITORING_AVAILABLE = True
    except ImportError:
        DRIFT_MONITORING_AVAILABLE = False
        DRIFT_CHECK_INTERVAL_HOURS = 6
        DriftDetector = None
        DriftReport = None
        DriftSeverity = None
        DriftStatus = None
        get_drift_detector = None

# Online learning imports (River model)
try:
    from ..online_learning import (
        RIVER_AVAILABLE,
        LearningResult,
        LearningStatus,
        ModelType,
        OnlineLearningPipeline,
        PredictionResult,
        get_online_learning_pipeline,
    )

    ONLINE_LEARNING_AVAILABLE = True
except ImportError:
    try:
        from online_learning import (
            RIVER_AVAILABLE,
            LearningResult,
            LearningStatus,
            ModelType,
            OnlineLearningPipeline,
            PredictionResult,
            get_online_learning_pipeline,
        )

        ONLINE_LEARNING_AVAILABLE = True
    except ImportError:
        ONLINE_LEARNING_AVAILABLE = False
        RIVER_AVAILABLE = False
        LearningResult = None
        LearningStatus = None
        ModelType = None
        OnlineLearningPipeline = None
        PredictionResult = None
        get_online_learning_pipeline = None

# A/B testing imports for traffic routing between champion and candidate models
try:
    from ..ab_testing import (
        AB_TEST_SPLIT,
        ABTestRouter,
        CohortType,
        MetricsComparison,
        PromotionResult,
        RoutingResult,
        get_ab_test_router,
    )

    AB_TESTING_AVAILABLE = True
except ImportError:
    try:
        from ab_testing import (
            AB_TEST_SPLIT,
            ABTestRouter,
            CohortType,
            MetricsComparison,
            PromotionResult,
            RoutingResult,
            get_ab_test_router,
        )

        AB_TESTING_AVAILABLE = True
    except ImportError:
        AB_TESTING_AVAILABLE = False
        AB_TEST_SPLIT = 0.1
        ABTestRouter = None
        CohortType = None
        MetricsComparison = None
        PromotionResult = None
        RoutingResult = None
        get_ab_test_router = None

# Import from our own modules
from .impact_scorer import ImpactScorer
from .models import (
    GovernanceDecision,
    GovernanceMetrics,
    GovernanceMode,
    ImpactFeatures,
    ImpactLevel,
)
from .threshold_manager import AdaptiveThresholds

logger = logging.getLogger(__name__)


class AdaptiveGovernanceEngine:
    """Main adaptive governance engine with ML-enhanced decision making."""

    def __init__(self, constitutional_hash: str):
        self.constitutional_hash = constitutional_hash
        self.mode = GovernanceMode.ADAPTIVE

        # Core components
        self.impact_scorer = ImpactScorer(constitutional_hash)
        self.threshold_manager = AdaptiveThresholds(constitutional_hash)

        # Feedback handler for persistent storage
        self._feedback_handler: Optional[FeedbackHandler] = None
        if FEEDBACK_HANDLER_AVAILABLE:
            try:
                self._feedback_handler = get_feedback_handler()
                self._feedback_handler.initialize_schema()
                logger.info("Feedback handler initialized for governance engine")
            except Exception as e:
                logger.warning(f"Failed to initialize feedback handler: {e}")
                self._feedback_handler = None

        # Performance tracking
        self.metrics = GovernanceMetrics()
        self.decision_history: List[GovernanceDecision] = []

        # Learning parameters
        self.feedback_window = 3600  # 1 hour learning window
        self.performance_target = 0.95  # 95% accuracy target

        # Background learning thread
        self.learning_thread: Optional[threading.Thread] = None
        self.running = False

        # Drift detection configuration
        self._drift_detector: Optional[DriftDetector] = None
        self._last_drift_check: float = 0.0
        self._drift_check_interval: int = DRIFT_CHECK_INTERVAL_HOURS * 3600  # Convert to seconds
        self._latest_drift_report: Optional[DriftReport] = None
        if DRIFT_MONITORING_AVAILABLE:
            try:
                self._drift_detector = get_drift_detector()
                # Try to load reference data on initialization
                if self._drift_detector.load_reference_data():
                    logger.info("Drift detector initialized with reference data")
                else:
                    logger.warning("Drift detector initialized but reference data not loaded")
            except Exception as e:
                logger.warning(f"Failed to initialize drift detector: {e}")
                self._drift_detector = None

        # River online learning model for incremental updates
        # Feature names for the River model must match ImpactFeatures
        self._river_feature_names = [
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
        self.river_model: Optional[OnlineLearningPipeline] = None
        if ONLINE_LEARNING_AVAILABLE and RIVER_AVAILABLE:
            try:
                self.river_model = get_online_learning_pipeline(
                    feature_names=self._river_feature_names,
                    model_type=ModelType.REGRESSOR,  # Regressor for impact scoring
                )
                # Set sklearn model as fallback for cold start
                if self.impact_scorer.model_trained:
                    self.river_model.set_fallback_model(self.impact_scorer.impact_classifier)
                logger.info(
                    f"River online learning model initialized "
                    f"(features: {len(self._river_feature_names)})"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize River model: {e}")
                self.river_model = None
        else:
            if not ONLINE_LEARNING_AVAILABLE:
                logger.warning("Online learning module not available, River model disabled")
            elif not RIVER_AVAILABLE:
                logger.warning("River library not installed, online learning disabled")

        # A/B testing router for traffic routing between champion and candidate models
        # Routes 90% traffic to champion, 10% to candidate (configurable via AB_TEST_SPLIT)
        self._ab_test_router: Optional[ABTestRouter] = None
        if AB_TESTING_AVAILABLE:
            try:
                self._ab_test_router = get_ab_test_router()
                # Set the impact scorer's sklearn model as both champion and candidate initially
                # Candidate will be updated when a new model version is registered
                if self.impact_scorer.model_trained:
                    self._ab_test_router.set_champion_model(
                        self.impact_scorer.impact_classifier, version=1
                    )
                logger.info(
                    f"A/B test router initialized "
                    f"(champion_split={1 - AB_TEST_SPLIT:.0%}, "
                    f"candidate_split={AB_TEST_SPLIT:.0%})"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize A/B test router: {e}")
                self._ab_test_router = None
        else:
            logger.warning("A/B testing module not available, traffic routing disabled")

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
        """Make an adaptive governance decision for a message.

        Traffic is routed between champion and candidate models based on A/B testing
        configuration. By default, 90% of requests go to champion and 10% to candidate.
        The routing is deterministic based on the decision_id hash.
        """
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

            # Generate decision_id first for A/B test routing
            decision_id = f"gov-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"

            # A/B test traffic routing between champion and candidate models
            # Uses hash(decision_id) for deterministic routing (90% champion, 10% candidate)
            cohort_name: Optional[str] = None
            model_version: Optional[int] = None

            if AB_TESTING_AVAILABLE and self._ab_test_router is not None:
                try:
                    # Route request based on decision_id hash
                    routing_result = self._ab_test_router.route(decision_id)
                    cohort_name = routing_result.cohort.value
                    model_version = routing_result.model_version

                    # Record request latency for A/B test metrics
                    latency_ms = (time.time() - start_time) * 1000
                    if routing_result.cohort == CohortType.CANDIDATE:
                        self._ab_test_router._candidate_metrics.record_request(
                            latency_ms=latency_ms,
                            prediction=action_allowed,
                        )
                    else:
                        self._ab_test_router._champion_metrics.record_request(
                            latency_ms=latency_ms,
                            prediction=action_allowed,
                        )

                    logger.debug(
                        f"A/B test routing: decision {decision_id} -> {cohort_name} "
                        f"(version: {model_version})"
                    )
                except Exception as e:
                    logger.warning(f"A/B test routing failed, using default: {e}")

            decision = GovernanceDecision(
                action_allowed=action_allowed,
                impact_level=impact_level,
                confidence_score=impact_features.confidence_level,
                reasoning=reasoning,
                recommended_threshold=threshold,
                features_used=impact_features,
                decision_id=decision_id,
                cohort=cohort_name,
                model_version=model_version,
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
        self, action_allowed: bool, features, threshold: float
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
        """Provide feedback to improve the ML models and store for training."""
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

            # Update River model for incremental online learning
            self._update_river_model(decision, actual_impact)

            # Store feedback event for persistent storage and later training
            self._store_feedback_event(decision, outcome_success, human_override, actual_impact)

        except Exception as e:
            logger.error(f"Error processing feedback: {e}")

    def _store_feedback_event(
        self,
        decision: GovernanceDecision,
        outcome_success: bool,
        human_override: Optional[bool],
        actual_impact: float,
    ) -> None:
        """Store feedback event using the feedback handler for persistent storage."""
        if not FEEDBACK_HANDLER_AVAILABLE or self._feedback_handler is None:
            logger.debug("Feedback handler not available, skipping persistent storage")
            return

        try:
            # Determine feedback type based on outcome and human override
            if human_override is not None:
                feedback_type = FeedbackType.CORRECTION
            elif outcome_success:
                feedback_type = FeedbackType.POSITIVE
            else:
                feedback_type = FeedbackType.NEGATIVE

            # Determine outcome status
            if outcome_success:
                outcome_status = OutcomeStatus.SUCCESS
            else:
                outcome_status = OutcomeStatus.FAILURE

            # Extract features as dict for storage
            features_dict = {
                "message_length": decision.features_used.message_length,
                "agent_count": decision.features_used.agent_count,
                "tenant_complexity": decision.features_used.tenant_complexity,
                "temporal_patterns": decision.features_used.temporal_patterns,
                "semantic_similarity": decision.features_used.semantic_similarity,
                "historical_precedence": decision.features_used.historical_precedence,
                "resource_utilization": decision.features_used.resource_utilization,
                "network_isolation": decision.features_used.network_isolation,
                "risk_score": decision.features_used.risk_score,
                "confidence_level": decision.features_used.confidence_level,
            }

            # Build correction data if human override was provided
            correction_data = None
            if human_override is not None:
                correction_data = {
                    "original_decision": decision.action_allowed,
                    "human_override": human_override,
                    "correction_applied": human_override != decision.action_allowed,
                }

            # Create feedback event
            feedback_event = FeedbackEvent(
                decision_id=decision.decision_id,
                feedback_type=feedback_type,
                outcome=outcome_status,
                features=features_dict,
                actual_impact=actual_impact,
                correction_data=correction_data,
                metadata={
                    "impact_level": decision.impact_level.value,
                    "confidence_score": decision.confidence_score,
                    "recommended_threshold": decision.recommended_threshold,
                    "reasoning": decision.reasoning,
                    "timestamp": decision.timestamp.isoformat(),
                    "constitutional_hash": self.constitutional_hash,
                },
            )

            # Store the feedback event
            response = self._feedback_handler.store_feedback(feedback_event)
            logger.debug(
                f"Stored feedback event {response.feedback_id} for decision {decision.decision_id}"
            )

        except Exception as e:
            logger.warning(f"Failed to store feedback event: {e}")

    def _update_river_model(
        self,
        decision: GovernanceDecision,
        actual_impact: float,
    ) -> None:
        """Update the River model with incremental online learning.

        This enables continuous learning from feedback without requiring
        full batch retraining. The River model uses AdaptiveRandomForest
        which handles concept drift naturally.

        Args:
            decision: The governance decision that was made
            actual_impact: The actual impact score based on outcome
        """
        if not ONLINE_LEARNING_AVAILABLE or self.river_model is None:
            return

        try:
            # Extract features from the decision for River model
            features = decision.features_used
            features_dict = {
                "message_length": float(features.message_length),
                "agent_count": float(features.agent_count),
                "tenant_complexity": float(features.tenant_complexity),
                "temporal_mean": (
                    float(np.mean(features.temporal_patterns))
                    if features.temporal_patterns
                    else 0.0
                ),
                "temporal_std": (
                    float(np.std(features.temporal_patterns)) if features.temporal_patterns else 0.0
                ),
                "semantic_similarity": float(features.semantic_similarity),
                "historical_precedence": float(features.historical_precedence),
                "resource_utilization": float(features.resource_utilization),
                "network_isolation": float(features.network_isolation),
                "risk_score": float(features.risk_score),
                "confidence_level": float(features.confidence_level),
            }

            # Learn from the feedback event incrementally
            result = self.river_model.learn_from_feedback(
                features=features_dict,
                outcome=actual_impact,
                decision_id=decision.decision_id,
            )

            if result.success:
                logger.debug(
                    f"River model updated for decision {decision.decision_id}, "
                    f"total samples: {result.total_samples}"
                )

                # Update sklearn fallback model if River model is now ready
                # but sklearn model wasn't trained yet
                if self.river_model.adapter.is_ready and not self.impact_scorer.model_trained:
                    logger.info(
                        f"River model ready with {result.total_samples} samples, "
                        "can now provide predictions"
                    )
            else:
                logger.warning(
                    f"River model update failed for decision {decision.decision_id}: "
                    f"{result.error_message}"
                )

        except Exception as e:
            logger.warning(f"Failed to update River model: {e}")

    def get_river_model_stats(self) -> Optional[Dict]:
        """Get statistics from the River online learning model.

        Returns:
            Dict with learning stats, or None if River model unavailable
        """
        if not ONLINE_LEARNING_AVAILABLE or self.river_model is None:
            return None

        try:
            return self.river_model.get_stats()
        except Exception as e:
            logger.warning(f"Failed to get River model stats: {e}")
            return None

    def get_ab_test_router(self) -> Optional[ABTestRouter]:
        """Get the A/B test router instance.

        Returns:
            ABTestRouter instance or None if not available
        """
        return self._ab_test_router

    def get_ab_test_metrics(self) -> Optional[Dict]:
        """Get A/B testing metrics for champion and candidate cohorts.

        Returns:
            Dict with metrics summary for both cohorts, or None if not available
        """
        if not AB_TESTING_AVAILABLE or self._ab_test_router is None:
            return None

        try:
            return self._ab_test_router.get_metrics_summary()
        except Exception as e:
            logger.warning(f"Failed to get A/B test metrics: {e}")
            return None

    def get_ab_test_comparison(self) -> Optional[MetricsComparison]:
        """Compare champion and candidate model performance.

        Returns:
            MetricsComparison with statistical analysis, or None if not available
        """
        if not AB_TESTING_AVAILABLE or self._ab_test_router is None:
            return None

        try:
            return self._ab_test_router.compare_metrics()
        except Exception as e:
            logger.warning(f"Failed to compare A/B test metrics: {e}")
            return None

    def promote_candidate_model(self, force: bool = False) -> Optional[PromotionResult]:
        """Promote the candidate model to champion if it performs better.

        Args:
            force: If True, bypass validation checks and promote regardless

        Returns:
            PromotionResult with status and details, or None if not available
        """
        if not AB_TESTING_AVAILABLE or self._ab_test_router is None:
            logger.warning("A/B testing not available, cannot promote candidate")
            return None

        try:
            result = self._ab_test_router.promote_candidate(force=force)
            if result.status.value == "promoted":
                logger.info(
                    f"Candidate model promoted to champion: "
                    f"v{result.previous_champion_version} -> v{result.new_champion_version}"
                )
            return result
        except Exception as e:
            logger.error(f"Failed to promote candidate model: {e}")
            return None

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

                # Scheduled drift detection (every drift_check_interval)
                self._run_scheduled_drift_detection()

                # Log performance summary
                self._log_performance_summary()

            except Exception as e:
                logger.error(f"Background learning error: {e}")
                time.sleep(60)  # Back off on errors

    def _run_scheduled_drift_detection(self) -> None:
        """Run drift detection if the scheduled interval has elapsed."""
        if not DRIFT_MONITORING_AVAILABLE or self._drift_detector is None:
            return

        current_time = time.time()
        time_since_last_check = current_time - self._last_drift_check

        # Check if drift detection is due
        if time_since_last_check < self._drift_check_interval:
            return

        logger.info(
            f"drift_check_interval: Running scheduled drift detection "
            f"(interval: {self._drift_check_interval / 3600:.1f} hours)"
        )

        try:
            # Collect recent decision data for drift analysis
            recent_data = self._collect_drift_data()

            if recent_data is None or len(recent_data) == 0:
                logger.info("drift_check_interval: Insufficient data for drift detection, skipping")
                self._last_drift_check = current_time
                return

            # Run drift detection
            drift_report = self._drift_detector.detect_drift(recent_data)
            self._latest_drift_report = drift_report
            self._last_drift_check = current_time

            # Log drift detection results
            if drift_report.status == DriftStatus.SUCCESS:
                if drift_report.dataset_drift:
                    logger.warning(
                        f"drift_check_interval: Drift detected! "
                        f"Severity: {drift_report.drift_severity.value}, "
                        f"Drifted features: {drift_report.drifted_features}/{drift_report.total_features} "
                        f"({drift_report.drift_share:.1%})"
                    )

                    # Log recommendations
                    for recommendation in drift_report.recommendations:
                        logger.info(f"drift_check_interval: Recommendation - {recommendation}")

                    # Check if retraining should be triggered
                    if self._drift_detector.should_trigger_retraining(drift_report):
                        logger.warning(
                            "drift_check_interval: Drift severity warrants model retraining"
                        )
                else:
                    logger.info(
                        f"drift_check_interval: No significant drift detected. "
                        f"Drift share: {drift_report.drift_share:.1%}"
                    )
            else:
                logger.warning(
                    f"drift_check_interval: Drift detection completed with status: "
                    f"{drift_report.status.value}. {drift_report.error_message or ''}"
                )

        except Exception as e:
            logger.error(f"drift_check_interval: Error during drift detection: {e}")
            # Still update last check time to prevent retry flood
            self._last_drift_check = current_time

    def _collect_drift_data(self):
        """Collect recent decision data for drift analysis."""
        try:
            # Need pandas for DataFrame creation
            try:
                import pandas as pd
            except ImportError:
                logger.warning("pandas not available for drift data collection")
                return None

            # Collect features from recent decisions
            if not self.decision_history:
                return None

            # Extract feature data from decision history
            feature_records = []
            for decision in self.decision_history:
                features = decision.features_used
                record = {
                    "message_length": features.message_length,
                    "agent_count": features.agent_count,
                    "tenant_complexity": features.tenant_complexity,
                    "temporal_mean": (
                        np.mean(features.temporal_patterns) if features.temporal_patterns else 0.0
                    ),
                    "temporal_std": (
                        np.std(features.temporal_patterns) if features.temporal_patterns else 0.0
                    ),
                    "semantic_similarity": features.semantic_similarity,
                    "historical_precedence": features.historical_precedence,
                    "resource_utilization": features.resource_utilization,
                    "network_isolation": features.network_isolation,
                    "risk_score": features.risk_score,
                    "confidence_level": features.confidence_level,
                }
                feature_records.append(record)

            if not feature_records:
                return None

            return pd.DataFrame(feature_records)

        except Exception as e:
            logger.error(f"Error collecting drift data: {e}")
            return None

    def get_latest_drift_report(self) -> Optional[DriftReport]:
        """Get the most recent drift detection report."""
        return self._latest_drift_report

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


__all__ = ["AdaptiveGovernanceEngine"]
