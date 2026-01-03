"""
Feedback submission API endpoints
"""

from fastapi import APIRouter, HTTPException

from ..core.engine import ml_engine
from ..core.models import FeedbackRequest, FeedbackSubmission

router = APIRouter(prefix="/feedback", tags=["feedback"])


@router.post("/submit", response_model=dict)
async def submit_feedback(request: FeedbackRequest):
    """
    Submit user feedback on governance decision

    Feedback is used to improve ML models through online learning and batch retraining.
    """
    try:
        # Convert to internal feedback format
        feedback = FeedbackSubmission(
            request_id=request.request_id,
            user_id="api_user",  # Would come from authentication
            feedback_type=request.feedback_type,
            correct_decision=request.correct_decision,
            rationale=request.rationale,
            severity=request.severity,
            metadata={"source": "api"}
        )

        # Submit feedback
        success = await ml_engine.submit_feedback(feedback)

        if not success:
            raise HTTPException(
                status_code=400,
                detail="Failed to process feedback submission"
            )

        return {
            "status": "feedback_received",
            "request_id": request.request_id,
            "message": "Thank you for your feedback. It will be used to improve our governance models."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Feedback submission failed: {str(e)}"
        )


@router.get("/stats")
async def get_feedback_stats():
    """
    Get feedback statistics

    Returns aggregated statistics about user feedback submissions.
    """
    try:
        # Would query feedback database/cache
        return {
            "total_feedback": ml_engine.metrics.get("feedback_received", 0),
            "feedback_types": {
                "correct": 0,
                "incorrect": 0,
                "escalated": 0,
                "overridden": 0
            },
            "processing_status": "active",
            "last_updated": "2024-01-01T00:00:00Z"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get feedback stats: {str(e)}"
        )
