"""
Governance prediction API endpoints
"""

from typing import Optional
from fastapi import APIRouter, HTTPException

from ..core.engine import ml_engine
from ..core.models import (
    PredictRequest,
    PredictResponse,
    GovernanceRequest,
    GovernanceResponse
)

router = APIRouter(prefix="/governance", tags=["governance"])


@router.post("/predict", response_model=PredictResponse)
async def predict_governance(request: PredictRequest):
    """
    Get governance decision for content

    Uses ML models to analyze content and context, returning an appropriate governance decision.
    Supports A/B testing for model evaluation.
    """
    try:
        # Convert to internal request format
        governance_request = GovernanceRequest(
            request_id=f"req-{hash(request.content + str(request.context))}",
            content=request.content,
            context=request.context,
            user_id=request.user_id,
            metadata={"use_ab_test": request.use_ab_test}
        )

        # Make prediction
        response = await ml_engine.predict(
            governance_request,
            use_ab_test=request.use_ab_test
        )

        # Convert to API response format
        api_response = PredictResponse(
            decision=response.decision,
            confidence=response.confidence,
            reasoning=response.reasoning,
            model_version=response.model_version,
            processing_time_ms=response.processing_time_ms,
            ab_test_info=response.metadata.get("ab_test") if hasattr(response, 'metadata') else None
        )

        return api_response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Governance prediction failed: {str(e)}"
        )


@router.get("/status")
async def get_governance_status():
    """
    Get current governance system status

    Returns information about active models, A/B tests, and system metrics.
    """
    try:
        return {
            "active_models": ml_engine.active_versions,
            "ab_tests": [
                {
                    "test_id": ab_test.test_id,
                    "name": ab_test.name,
                    "status": ab_test.status,
                    "traffic_split": ab_test.traffic_split
                }
                for ab_test in ml_engine.ab_tests.values()
            ],
            "metrics": ml_engine.metrics,
            "timestamp": "2024-01-01T00:00:00Z"  # Would be dynamic
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get governance status: {str(e)}"
        )


@router.get("/models/active")
async def get_active_models():
    """
    Get information about currently active models

    Returns details about the models currently being used for predictions.
    """
    try:
        active_models = {}
        for model_type, version_id in ml_engine.active_versions.items():
            # Would fetch model metadata from storage
            active_models[model_type.value] = {
                "version_id": version_id,
                "status": "active",
                "last_updated": "2024-01-01T00:00:00Z"  # Would be dynamic
            }

        return {"active_models": active_models}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get active models: {str(e)}"
        )
