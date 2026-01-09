"""Constitutional Hash: cdd01ef066bc6cf2
Anomalies Route - GET /anomalies endpoint with detected outliers

Provides anomaly detection results for governance metrics including:
- Detected unusual patterns in violations, user activity, or policy changes
- Severity scores and labels for each anomaly
- Affected metrics details
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Add analytics-engine to path for importing AnomalyDetector
ANALYTICS_ENGINE_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "analytics-engine" / "src"
)
if str(ANALYTICS_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(ANALYTICS_ENGINE_PATH))

try:
    from anomaly_detector import (
        AnomalyDetectionResult,
        AnomalyDetector,
        DetectedAnomaly,
    )
except ImportError:
    AnomalyDetectionResult = None
    AnomalyDetector = None
    DetectedAnomaly = None

try:
    import pandas as pd
except ImportError:
    pd = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


class AnomalyItem(BaseModel):
    """Model representing a single detected anomaly"""

    anomaly_id: str = Field(description="Unique identifier for the anomaly")
    timestamp: datetime = Field(description="When the anomaly was detected")
    severity_score: float = Field(
        ge=-1.0,
        le=1.0,
        description="Anomaly score: lower values = more anomalous, range [-1, 1]",
    )
    severity_label: str = Field(
        description="Human-readable severity: 'critical', 'high', 'medium', 'low'"
    )
    affected_metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metrics that contributed to the anomaly detection",
    )
    description: str = Field(
        default="",
        description="Human-readable description of the anomaly",
    )


class AnomaliesResponse(BaseModel):
    """Response model for anomaly detection results"""

    analysis_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when analysis was performed",
    )
    total_records_analyzed: int = Field(
        default=0,
        description="Number of records analyzed for anomalies",
    )
    anomalies_detected: int = Field(
        default=0,
        description="Number of anomalies detected",
    )
    contamination_rate: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Expected proportion of anomalies in the data",
    )
    anomalies: List[AnomalyItem] = Field(
        default_factory=list,
        description="List of detected anomalies",
    )
    model_trained: bool = Field(
        default=False,
        description="Whether the detection model was successfully trained",
    )


class AnomaliesErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of error",
    )


# Module-level anomaly detector instance
_anomaly_detector: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> Optional[AnomalyDetector]:
    """
    Get or create the AnomalyDetector instance.

    Returns:
        AnomalyDetector instance or None if not available
    """
    global _anomaly_detector

    if _anomaly_detector is not None:
        return _anomaly_detector

    if AnomalyDetector is None:
        logger.warning("AnomalyDetector not available. Ensure analytics-engine is in the path.")
        return None

    _anomaly_detector = AnomalyDetector(
        contamination=0.1,
        n_estimators=100,
        random_state=42,
    )

    return _anomaly_detector


def get_sample_governance_metrics() -> List[Dict[str, Any]]:
    """
    Get sample governance metrics data for anomaly detection.

    In production, this would fetch real data from Kafka/Redis.
    Returns sample data for demonstration and testing.

    Returns:
        List of dictionaries with governance metrics
    """
    # Sample governance metrics data for testing
    # In production, this would be fetched from Redis cache
    # populated by the analytics-engine Kafka consumer
    return [
        {"date": "2025-01-01", "violation_count": 5, "user_count": 20, "policy_changes": 1},
        {"date": "2025-01-02", "violation_count": 3, "user_count": 18, "policy_changes": 0},
        {"date": "2025-01-03", "violation_count": 7, "user_count": 22, "policy_changes": 2},
        {"date": "2025-01-04", "violation_count": 4, "user_count": 19, "policy_changes": 0},
        {"date": "2025-01-05", "violation_count": 6, "user_count": 21, "policy_changes": 1},
        {"date": "2025-01-06", "violation_count": 50, "user_count": 85, "policy_changes": 8},
        {"date": "2025-01-07", "violation_count": 8, "user_count": 25, "policy_changes": 2},
        {"date": "2025-01-08", "violation_count": 5, "user_count": 20, "policy_changes": 1},
        {"date": "2025-01-09", "violation_count": 4, "user_count": 18, "policy_changes": 0},
        {"date": "2025-01-10", "violation_count": 45, "user_count": 78, "policy_changes": 7},
    ]


def _convert_to_response(result: AnomalyDetectionResult) -> AnomaliesResponse:
    """
    Convert AnomalyDetectionResult to AnomaliesResponse.

    Args:
        result: AnomalyDetectionResult from the detector

    Returns:
        AnomaliesResponse for the API
    """
    anomaly_items = [
        AnomalyItem(
            anomaly_id=a.anomaly_id,
            timestamp=a.timestamp,
            severity_score=a.severity_score,
            severity_label=a.severity_label,
            affected_metrics=a.affected_metrics,
            description=a.description,
        )
        for a in result.anomalies
    ]

    return AnomaliesResponse(
        analysis_timestamp=result.analysis_timestamp,
        total_records_analyzed=result.total_records_analyzed,
        anomalies_detected=result.anomalies_detected,
        contamination_rate=result.contamination_rate,
        anomalies=anomaly_items,
        model_trained=result.model_trained,
    )


@router.get(
    "",
    response_model=AnomaliesResponse,
    responses={
        200: {"description": "Successfully detected anomalies"},
        500: {"description": "Internal server error"},
        503: {"description": "Anomaly detection service temporarily unavailable"},
    },
    summary="Get detected anomalies in governance metrics",
    description=(
        "Detects unusual patterns in governance data including spikes in violations, "
        "unusual user activity, or abnormal policy changes using IsolationForest algorithm."
    ),
)
async def get_anomalies(
    severity: Optional[str] = Query(
        default=None,
        description="Filter by severity level",
        enum=["critical", "high", "medium", "low"],
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of anomalies to return",
    ),
    time_range: str = Query(
        default="last_7_days",
        description="Time range for anomaly detection",
        enum=["last_24_hours", "last_7_days", "last_30_days", "all_time"],
    ),
) -> AnomaliesResponse:
    """
    Get detected anomalies in governance metrics.

    Uses IsolationForest algorithm to detect unusual patterns in:
    - Violation counts
    - User activity
    - Policy changes

    Args:
        severity: Filter anomalies by severity level
        limit: Maximum number of anomalies to return
        time_range: Time range for data analysis

    Returns:
        AnomaliesResponse with detected anomalies

    Raises:
        HTTPException: If anomaly detection fails
    """
    now = datetime.now(timezone.utc)

    # Check if pandas is available
    if pd is None:
        logger.warning("pandas not available, returning fallback response")
        return AnomaliesResponse(
            analysis_timestamp=now,
            total_records_analyzed=0,
            anomalies_detected=0,
            contamination_rate=0.1,
            anomalies=[],
            model_trained=False,
        )

    detector = get_anomaly_detector()

    # Get governance data (sample data for now, Redis integration in future)
    governance_data = get_sample_governance_metrics()

    # Check if detector is available
    if detector is None:
        logger.warning("AnomalyDetector not available, returning fallback response")
        # Return a fallback response when detector is not available
        return AnomaliesResponse(
            analysis_timestamp=now,
            total_records_analyzed=len(governance_data),
            anomalies_detected=0,
            contamination_rate=0.1,
            anomalies=[],
            model_trained=False,
        )

    try:
        # Convert to DataFrame for the detector
        df = pd.DataFrame(governance_data)

        # Detect anomalies
        result = detector.detect_anomalies(df)

        # Convert to response model
        response = _convert_to_response(result)

        # Apply severity filter if specified
        if severity:
            response.anomalies = [a for a in response.anomalies if a.severity_label == severity]
            response.anomalies_detected = len(response.anomalies)

        # Apply limit
        response.anomalies = response.anomalies[:limit]

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to detect anomalies: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to detect anomalies. Please try again later.",
        ) from None


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get anomaly detector status",
    description="Returns the current status and configuration of the anomaly detector.",
)
async def get_anomalies_status() -> Dict[str, Any]:
    """
    Get the status of the anomaly detector.

    Returns:
        Dictionary with detector status and configuration
    """
    detector = get_anomaly_detector()

    if detector is None:
        return {
            "status": "unavailable",
            "message": "AnomalyDetector module not loaded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    info = detector.get_model_info()
    info["status"] = "available" if info.get("sklearn_available") else "not_configured"
    info["timestamp"] = datetime.now(timezone.utc).isoformat()

    return info
