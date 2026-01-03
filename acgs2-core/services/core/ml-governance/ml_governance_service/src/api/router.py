"""
FastAPI router for ML governance endpoints
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from ..models.impact_scorer import ImpactScorer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1")
scorer = ImpactScorer()


class PredictRequest(BaseModel):
    features: List[float] = Field(..., description="Feature vector for prediction")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PredictResponse(BaseModel):
    decision_id: str
    impact_score: float
    is_high_impact: bool
    timestamp: str


class FeedbackRequest(BaseModel):
    decision_id: str
    feedback_type: str  # thumbs_up, thumbs_down, correction
    actual_outcome: Optional[int] = None
    user_id: str


@router.post("/predict", response_model=PredictResponse)
async def predict_impact(request: PredictRequest):
    """Predict impact score for a governance decision"""
    import numpy as np

    # Convert to numpy array for model
    X = np.array([request.features])

    # Get prediction
    # In a real system, we'd use calibrated probabilities
    probs = scorer.predict_proba(X)
    impact_score = float(probs[0][1])  # Probability of class 1 (high impact)

    decision_id = str(uuid4())
    is_high_impact = impact_score > 0.8  # Default threshold

    logger.info(f"Prediction made: {decision_id} (score: {impact_score:.4f})")

    return PredictResponse(
        decision_id=decision_id,
        impact_score=impact_score,
        is_high_impact=is_high_impact,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest, background_tasks: BackgroundTasks):
    """Submit user feedback for a prediction"""
    logger.info(f"Feedback received for {request.decision_id}: {request.feedback_type}")

    # In a real system, we'd store this in a DB and potentially trigger online learning
    # background_tasks.add_task(process_feedback, request)

    return {"status": "success", "message": "Feedback recorded"}


@router.get("/health")
async def health_check():
    return {"status": "healthy", "model_trained": scorer.is_trained}
