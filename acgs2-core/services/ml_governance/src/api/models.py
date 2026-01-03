"""
Model management and monitoring API endpoints
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from ..core.engine import ml_engine
from ..core.models import DriftDetectionResult, ModelMetrics

router = APIRouter(prefix="/models", tags=["models"])


@router.get("/metrics", response_model=List[ModelMetrics])
async def get_model_metrics():
    """
    Get performance metrics for all active models

    Returns accuracy, precision, recall, and other metrics for each model version.
    """
    try:
        # Would fetch metrics from MLflow or internal storage
        metrics = []
        for model_type, version_id in ml_engine.active_versions.items():
            metrics.append(ModelMetrics(
                version_id=version_id,
                accuracy=0.85,  # Would be dynamic
                precision=0.82,
                recall=0.88,
                f1_score=0.85,
                total_predictions=ml_engine.metrics.get("predictions", 0),
                feedback_count=ml_engine.metrics.get("feedback_received", 0)
            ))

        return metrics

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get model metrics: {str(e)}"
        )


@router.post("/drift-check", response_model=Optional[DriftDetectionResult])
async def check_model_drift(model_version: Optional[str] = None):
    """
    Check for model drift in the specified model version

    If no version is specified, checks the currently active model.
    Returns drift detection results if drift is detected.
    """
    try:
        if not model_version:
            # Use active Random Forest model
            model_version = ml_engine.active_versions.get("random_forest", "baseline-v1.0")

        drift_result = await ml_engine.check_drift(model_version)

        return drift_result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Drift check failed: {str(e)}"
        )


@router.get("/drift-history")
async def get_drift_history(
    model_version: Optional[str] = None,
    limit: int = 10
):
    """
    Get drift detection history for a model version

    Returns recent drift checks and their results.
    """
    try:
        # Would query drift history from database
        return {
            "model_version": model_version or "baseline-v1.0",
            "drift_checks": [],
            "total_checks": ml_engine.metrics.get("drift_checks", 0),
            "last_check": "2024-01-01T00:00:00Z"
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get drift history: {str(e)}"
        )


@router.get("/ab-tests")
async def get_ab_tests():
    """
    Get information about active A/B tests

    Returns details about ongoing model comparison experiments.
    """
    try:
        ab_tests = []
        for ab_test in ml_engine.ab_tests.values():
            ab_tests.append({
                "test_id": ab_test.test_id,
                "name": ab_test.name,
                "champion_version": ab_test.champion_version,
                "candidate_version": ab_test.candidate_version,
                "traffic_split": ab_test.traffic_split,
                "status": ab_test.status,
                "start_date": ab_test.start_date.isoformat()
            })

        return {"ab_tests": ab_tests, "total": len(ab_tests)}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get A/B tests: {str(e)}"
        )


@router.get("/online-learning-status")
async def get_online_learning_status():
    """
    Get status of online learning systems

    Returns information about online learners and their performance.
    """
    try:
        online_status = {}
        for learner_name in ml_engine.online_learners.keys():
            online_status[learner_name] = {
                "status": "active",
                "updates_processed": ml_engine.metrics.get("feedback_received", 0),
                "last_update": "2024-01-01T00:00:00Z"
            }

        return {
            "online_learners": online_status,
            "total_learners": len(online_status),
            "learning_active": True
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get online learning status: {str(e)}"
        )
