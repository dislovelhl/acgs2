"""
Core ML models and data structures for adaptive governance
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import numpy as np


class GovernanceDecision(str, Enum):
    """Possible governance decisions"""
    ALLOW = "allow"
    DENY = "deny"
    ESCALATE = "escalate"
    MONITOR = "monitor"


class ModelType(str, Enum):
    """Types of ML models used"""
    RANDOM_FOREST = "random_forest"
    ONLINE_LEARNER = "online_learner"
    ENSEMBLE = "ensemble"


class ModelStatus(str, Enum):
    """Model lifecycle status"""
    TRAINING = "training"
    ACTIVE = "active"
    CANDIDATE = "candidate"
    RETIRED = "retired"
    FAILED = "failed"


class FeedbackType(str, Enum):
    """Types of user feedback"""
    CORRECT = "correct"
    INCORRECT = "incorrect"
    ESCALATED = "escalated"
    OVERRIDDEN = "overridden"


class FeatureVector(BaseModel):
    """Feature vector for ML model input"""

    # Intent classification features
    intent_confidence: float = Field(..., description="Intent classification confidence score")
    intent_class: str = Field(..., description="Intent classification result")
    intent_is_helpful: bool = Field(default=False, description="Whether intent is classified as helpful")
    intent_is_harmful: bool = Field(default=False, description="Whether intent is classified as harmful")

    # Content analysis features
    content_length: int = Field(..., description="Length of content in characters")
    content_has_urls: bool = Field(default=False, description="Whether content contains URLs")
    content_has_email: bool = Field(default=False, description="Whether content contains email addresses")
    content_has_code: bool = Field(default=False, description="Whether content contains code-like patterns")
    content_toxicity_score: float = Field(default=0.0, description="Content toxicity score (0-1)")

    # Context features
    user_history_score: float = Field(default=0.5, description="User historical compliance score")
    time_of_day: int = Field(..., description="Hour of day (0-23)")
    day_of_week: int = Field(..., description="Day of week (0-6)")
    is_business_hours: bool = Field(default=True, description="Whether request is during business hours")

    # Policy evaluation features
    policy_match_count: int = Field(default=0, description="Number of policies that matched")
    policy_deny_count: int = Field(default=0, description="Number of policies that denied")
    policy_allow_count: int = Field(default=0, description="Number of policies that allowed")

    # Risk assessment features
    risk_level: str = Field(default="low", description="Overall risk level assessment")
    compliance_flags: List[str] = Field(default_factory=list, description="Active compliance flags")
    sensitivity_score: float = Field(default=0.0, description="Content sensitivity score")

    def to_numpy_array(self) -> np.ndarray:
        """Convert to numpy array for ML model input"""
        return np.array([
            self.intent_confidence,
            1.0 if self.intent_is_helpful else 0.0,
            1.0 if self.intent_is_harmful else 0.0,
            self.content_length / 1000.0,  # Normalize
            1.0 if self.content_has_urls else 0.0,
            1.0 if self.content_has_email else 0.0,
            1.0 if self.content_has_code else 0.0,
            self.content_toxicity_score,
            self.user_history_score,
            self.time_of_day / 24.0,  # Normalize
            self.day_of_week / 7.0,   # Normalize
            1.0 if self.is_business_hours else 0.0,
            self.policy_match_count / 10.0,  # Normalize
            self.policy_deny_count / 10.0,   # Normalize
            self.policy_allow_count / 10.0,  # Normalize
            {"low": 0.0, "medium": 0.5, "high": 1.0}.get(self.risk_level, 0.5),
            len(self.compliance_flags) / 5.0,  # Normalize
            self.sensitivity_score
        ])


class GovernanceRequest(BaseModel):
    """Request for governance decision"""

    request_id: str = Field(..., description="Unique request identifier")
    content: str = Field(..., description="Content to be governed")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    user_id: Optional[str] = Field(None, description="User identifier")
    session_id: Optional[str] = Field(None, description="Session identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Request timestamp")


class GovernanceResponse(BaseModel):
    """Response from governance system"""

    request_id: str = Field(..., description="Request identifier")
    decision: GovernanceDecision = Field(..., description="Governance decision")
    confidence: float = Field(..., description="Decision confidence score")
    reasoning: str = Field(..., description="Decision reasoning")
    model_version: str = Field(..., description="Model version used")
    features: FeatureVector = Field(..., description="Feature vector used")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Response timestamp")


class FeedbackSubmission(BaseModel):
    """User feedback on governance decision"""

    request_id: str = Field(..., description="Original request identifier")
    user_id: str = Field(..., description="User providing feedback")
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    correct_decision: Optional[GovernanceDecision] = Field(None, description="What the correct decision should have been")
    rationale: str = Field(..., description="Feedback rationale")
    severity: str = Field(default="medium", description="Feedback severity (low/medium/high)")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional feedback metadata")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Feedback timestamp")


class ModelVersion(BaseModel):
    """ML model version information"""

    version_id: str = Field(..., description="Unique model version identifier")
    model_type: ModelType = Field(..., description="Type of ML model")
    status: ModelStatus = Field(..., description="Model status")
    accuracy: float = Field(default=0.0, description="Model accuracy score")
    precision: float = Field(default=0.0, description="Model precision score")
    recall: float = Field(default=0.0, description="Model recall score")
    f1_score: float = Field(default=0.0, description="Model F1 score")
    training_samples: int = Field(default=0, description="Number of training samples")
    validation_samples: int = Field(default=0, description="Number of validation samples")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Model creation timestamp")
    deployed_at: Optional[datetime] = Field(None, description="Model deployment timestamp")
    retired_at: Optional[datetime] = Field(None, description="Model retirement timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Model metadata")


class ABTest(BaseModel):
    """A/B test configuration"""

    test_id: str = Field(..., description="Unique A/B test identifier")
    name: str = Field(..., description="Test name")
    champion_version: str = Field(..., description="Champion model version")
    candidate_version: str = Field(..., description="Candidate model version")
    traffic_split: float = Field(default=0.1, description="Traffic percentage to candidate (0.0-1.0)")
    start_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Test start date")
    end_date: Optional[datetime] = Field(None, description="Test end date")
    status: str = Field(default="active", description="Test status")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Test metrics")


class DriftDetectionResult(BaseModel):
    """Drift detection result"""

    check_id: str = Field(..., description="Unique drift check identifier")
    model_version: str = Field(..., description="Model version checked")
    drift_detected: bool = Field(..., description="Whether drift was detected")
    drift_score: float = Field(..., description="Drift score (higher = more drift)")
    threshold: float = Field(..., description="Drift detection threshold")
    features_affected: List[str] = Field(default_factory=list, description="Features showing drift")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Check timestamp")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed drift analysis")


# API Request/Response models
class PredictRequest(BaseModel):
    """Request for governance prediction"""

    content: str = Field(..., description="Content to evaluate")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    user_id: Optional[str] = Field(None, description="User identifier")
    use_ab_test: bool = Field(default=False, description="Whether to use A/B testing")


class PredictResponse(BaseModel):
    """Response from governance prediction"""

    decision: GovernanceDecision = Field(..., description="Governance decision")
    confidence: float = Field(..., description="Decision confidence")
    reasoning: str = Field(..., description="Decision reasoning")
    model_version: str = Field(..., description="Model version used")
    processing_time_ms: float = Field(..., description="Processing time")
    ab_test_info: Optional[Dict[str, Any]] = Field(None, description="A/B test information")


class FeedbackRequest(BaseModel):
    """Request to submit feedback"""

    request_id: str = Field(..., description="Original request identifier")
    feedback_type: FeedbackType = Field(..., description="Type of feedback")
    correct_decision: Optional[GovernanceDecision] = Field(None, description="Correct decision")
    rationale: str = Field(..., description="Feedback rationale")
    severity: str = Field(default="medium", description="Feedback severity")


class ModelMetrics(BaseModel):
    """Model performance metrics"""

    version_id: str = Field(..., description="Model version")
    accuracy: float = Field(..., description="Accuracy score")
    precision: float = Field(..., description="Precision score")
    recall: float = Field(..., description="Recall score")
    f1_score: float = Field(..., description="F1 score")
    total_predictions: int = Field(..., description="Total predictions made")
    feedback_count: int = Field(..., description="Number of feedback submissions")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")
