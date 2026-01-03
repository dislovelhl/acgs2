"""
ACGS-2 Enhanced Agent Bus API
FastAPI application for the Enhanced Agent Bus service
"""

import asyncio
import logging
from typing import Any, Dict, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .drift_monitoring import DriftSeverity, DriftStatus, get_drift_detector
from .feedback_handler import (
    FeedbackEvent,
    FeedbackResponse,
    get_feedback_handler,
)

# A/B testing imports for model promotion
try:
    from .ab_testing import PromotionStatus

    AB_TESTING_AVAILABLE = True
except ImportError:
    AB_TESTING_AVAILABLE = False
    PromotionStatus = None

# Adaptive governance imports
try:
    from .adaptive_governance import get_adaptive_governance

    ADAPTIVE_GOVERNANCE_AVAILABLE = True
except ImportError:
    ADAPTIVE_GOVERNANCE_AVAILABLE = False
    get_adaptive_governance = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="ACGS-2 Enhanced Agent Bus API",
    description="API for the ACGS-2 Enhanced Agent Bus with Constitutional Compliance",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global agent bus instance - simplified for development
agent_bus = None


# Request/Response Models
class MessageRequest(BaseModel):
    """Request model for sending messages"""

    content: str = Field(..., description="Message content")
    message_type: str = Field(default="user_request", description="Type of message")
    priority: str = Field(default="normal", description="Message priority")
    sender: str = Field(..., description="Sender identifier")
    recipient: Optional[str] = Field(default=None, description="Recipient identifier")
    tenant_id: Optional[str] = Field(default=None, description="Tenant identifier")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class MessageResponse(BaseModel):
    """Response model for message operations"""

    message_id: str
    status: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    service: str
    version: str
    agent_bus_status: str


class FeatureDriftResponse(BaseModel):
    """Drift result for a single feature"""

    feature_name: str
    drift_detected: bool
    drift_score: float
    stattest: str
    threshold: float
    psi_value: Optional[float] = None


class DriftReportResponse(BaseModel):
    """Response model for drift monitoring reports"""

    timestamp: str
    status: str
    dataset_drift: bool
    drift_severity: str
    drift_share: float
    total_features: int
    drifted_features: int
    feature_results: list[FeatureDriftResponse]
    reference_samples: int
    current_samples: int
    error_message: Optional[str] = None
    recommendations: list[str]


class PromoteCandidateRequest(BaseModel):
    """Request model for model promotion"""

    force: bool = Field(
        default=False,
        description="Bypass validation checks and force promotion",
    )


class CohortMetricsResponse(BaseModel):
    """Metrics for a single A/B test cohort"""

    cohort: str
    request_count: int
    correct_predictions: int
    total_predictions: int
    accuracy: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    errors: int
    error_rate: float


class MetricsComparisonResponse(BaseModel):
    """Response model for metrics comparison"""

    result: str
    accuracy_delta: float
    latency_delta_ms: float
    sample_size_champion: int
    sample_size_candidate: int
    is_significant: bool
    candidate_is_better: bool
    recommendation: str
    compared_at: str
    champion_metrics: CohortMetricsResponse
    candidate_metrics: CohortMetricsResponse


class PromoteCandidateResponse(BaseModel):
    """Response model for model promotion"""

    status: str = Field(
        ..., description="Promotion status (ready, not_ready, blocked, promoted, error)"
    )
    previous_champion_version: Optional[int] = Field(
        default=None, description="Previous champion model version"
    )
    new_champion_version: Optional[int] = Field(
        default=None, description="New champion model version after promotion"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if promotion failed"
    )
    promoted_at: Optional[str] = Field(
        default=None, description="ISO timestamp when promotion occurred"
    )
    comparison: Optional[MetricsComparisonResponse] = Field(
        default=None, description="Metrics comparison between champion and candidate"
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the agent bus on startup"""
    global agent_bus
    try:
        logger.info("Initializing Enhanced Agent Bus (simplified for development)...")
        # Simplified initialization for development
        agent_bus = {"status": "initialized", "services": ["redis", "kafka", "opa"]}
        logger.info("Enhanced Agent Bus initialized successfully (dev mode)")
    except Exception as e:
        logger.error(f"Failed to initialize agent bus: {e}")
        raise


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    global agent_bus
    logger.info("Enhanced Agent Bus stopped (dev mode)")


# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    agent_bus_status = "healthy" if agent_bus else "unhealthy"

    return HealthResponse(
        status="healthy" if agent_bus_status == "healthy" else "unhealthy",
        service="enhanced-agent-bus",
        version="1.0.0",
        agent_bus_status=agent_bus_status,
    )


@app.post("/messages", response_model=MessageResponse)
async def send_message(request: MessageRequest, background_tasks: BackgroundTasks):
    """Send a message to the agent bus"""
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        import uuid
        from datetime import datetime, timezone

        # Create simplified message response
        message_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)

        # Simulate async processing
        async def process_message(msg_id: str, content: str):
            logger.info(f"Processing message {msg_id}: {content[:50]}...")
            await asyncio.sleep(0.1)  # Simulate processing time
            logger.info(f"Message {msg_id} processed successfully")

        background_tasks.add_task(process_message, message_id, request.content)

        return MessageResponse(
            message_id=message_id,
            status="accepted",
            timestamp=timestamp.isoformat(),
            details={"message_type": request.message_type},
        )

    except Exception as e:
        logger.error(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@app.get("/messages/{message_id}")
async def get_message_status(message_id: str):
    """Get message status"""
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Simplified response for development
        return {
            "message_id": message_id,
            "status": "processed",
            "timestamp": "2024-01-01T00:00:00Z",
            "details": {"note": "Development mode - simplified response"},
        }
    except Exception as e:
        logger.error(f"Error getting message status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@app.get("/stats")
async def get_stats():
    """Get agent bus statistics"""
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Simplified stats for development
        return {
            "total_messages": 42,
            "active_connections": 3,
            "uptime_seconds": 3600,
            "note": "Development mode - mock statistics",
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@app.post("/policies/validate")
async def validate_policy(policy_data: Dict[str, Any]):
    """Validate a policy against constitutional requirements"""
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Simplified validation for development
        return {
            "valid": True,
            "policy_hash": "dev-placeholder-hash",
            "validation_timestamp": "2024-01-01T00:00:00Z",
            "note": "Development mode - simplified validation",
        }
    except Exception as e:
        logger.error(f"Error validating policy: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@app.post("/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(request: FeedbackEvent, background_tasks: BackgroundTasks):
    """
    Submit user feedback for a governance decision.

    Accepts feedback (thumbs up/down, outcome confirmation) on governance decisions
    made by the model. Feedback is stored for continuous learning and model improvement.
    """
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Get the feedback handler and store the feedback
        handler = get_feedback_handler()
        response = handler.store_feedback(request)

        logger.info(
            f"Feedback submitted: decision_id={request.decision_id}, "
            f"feedback_type={request.feedback_type.value}, "
            f"feedback_id={response.feedback_id}"
        )

        return response

    except ValueError as e:
        logger.warning(f"Invalid feedback data: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from None
    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@app.get("/monitoring/drift/latest", response_model=DriftReportResponse)
async def get_latest_drift_report():
    """
    Get the most recent drift monitoring report.

    Returns the latest drift detection results including:
    - Dataset-level drift status
    - Per-feature drift scores (using PSI method)
    - Drift severity classification
    - Recommendations for action

    If no drift detection has been run yet, returns a report with
    status indicating no data is available.
    """
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    try:
        # Get the drift detector instance
        detector = get_drift_detector()
        report = detector.get_last_report()

        if report is None:
            # No drift report available - return empty status report
            from datetime import datetime, timezone

            return DriftReportResponse(
                timestamp=datetime.now(timezone.utc).isoformat(),
                status=DriftStatus.NO_REFERENCE.value,
                dataset_drift=False,
                drift_severity=DriftSeverity.NONE.value,
                drift_share=0.0,
                total_features=0,
                drifted_features=0,
                feature_results=[],
                reference_samples=0,
                current_samples=0,
                error_message="No drift detection has been run yet",
                recommendations=[
                    "Run drift detection with current production data",
                    "Ensure reference baseline data is loaded",
                ],
            )

        # Convert drift report to API response model
        feature_results = [
            FeatureDriftResponse(
                feature_name=f.feature_name,
                drift_detected=f.drift_detected,
                drift_score=f.drift_score,
                stattest=f.stattest,
                threshold=f.threshold,
                psi_value=f.psi_value,
            )
            for f in report.feature_results
        ]

        return DriftReportResponse(
            timestamp=report.timestamp.isoformat(),
            status=report.status.value,
            dataset_drift=report.dataset_drift,
            drift_severity=report.drift_severity.value,
            drift_share=report.drift_share,
            total_features=report.total_features,
            drifted_features=report.drifted_features,
            feature_results=feature_results,
            reference_samples=report.reference_samples,
            current_samples=report.current_samples,
            error_message=report.error_message,
            recommendations=report.recommendations,
        )

    except Exception as e:
        logger.error(f"Error retrieving drift report: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


@app.post("/models/promote-candidate", response_model=PromoteCandidateResponse)
async def promote_candidate_model(request: PromoteCandidateRequest = None):
    """
    Promote the candidate model to champion.

    This endpoint validates that the candidate model meets promotion criteria
    before promoting. Uses MLflow alias switching for zero-downtime promotion.

    The promotion will be blocked unless:
    - Both champion and candidate have sufficient samples (AB_TEST_MIN_SAMPLES)
    - Candidate shows statistically significant improvement over champion
    - Or the `force` flag is set to bypass validation

    Returns:
        PromoteCandidateResponse with promotion status, version info, and metrics comparison
    """
    if not agent_bus:
        raise HTTPException(status_code=503, detail="Agent bus not initialized")

    if not ADAPTIVE_GOVERNANCE_AVAILABLE or get_adaptive_governance is None:
        raise HTTPException(
            status_code=503,
            detail="Adaptive governance not available",
        )

    if not AB_TESTING_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="A/B testing module not available",
        )

    try:
        # Get the adaptive governance engine
        governance = get_adaptive_governance()
        if governance is None:
            raise HTTPException(
                status_code=503,
                detail="Adaptive governance engine not initialized",
            )

        # Parse force flag from request (default to False if request is None)
        force = False
        if request is not None:
            force = request.force

        # Attempt to promote the candidate model
        result = governance.promote_candidate_model(force=force)

        if result is None:
            raise HTTPException(
                status_code=503,
                detail="A/B testing router not available in governance engine",
            )

        # Build comparison response if available
        comparison_response = None
        if result.comparison is not None:
            # Convert cohort metrics to response model
            champion_metrics = result.comparison.champion_metrics
            candidate_metrics = result.comparison.candidate_metrics

            champion_response = CohortMetricsResponse(
                cohort=champion_metrics.cohort.value,
                request_count=champion_metrics.request_count,
                correct_predictions=champion_metrics.correct_predictions,
                total_predictions=champion_metrics.total_predictions,
                accuracy=champion_metrics.accuracy,
                avg_latency_ms=champion_metrics.avg_latency_ms,
                min_latency_ms=(
                    champion_metrics.min_latency_ms
                    if champion_metrics.min_latency_ms != float("inf")
                    else 0.0
                ),
                max_latency_ms=champion_metrics.max_latency_ms,
                p50_latency_ms=champion_metrics.p50_latency_ms,
                p95_latency_ms=champion_metrics.p95_latency_ms,
                p99_latency_ms=champion_metrics.p99_latency_ms,
                errors=champion_metrics.errors,
                error_rate=(
                    champion_metrics.errors / champion_metrics.request_count
                    if champion_metrics.request_count > 0
                    else 0.0
                ),
            )

            candidate_response = CohortMetricsResponse(
                cohort=candidate_metrics.cohort.value,
                request_count=candidate_metrics.request_count,
                correct_predictions=candidate_metrics.correct_predictions,
                total_predictions=candidate_metrics.total_predictions,
                accuracy=candidate_metrics.accuracy,
                avg_latency_ms=candidate_metrics.avg_latency_ms,
                min_latency_ms=(
                    candidate_metrics.min_latency_ms
                    if candidate_metrics.min_latency_ms != float("inf")
                    else 0.0
                ),
                max_latency_ms=candidate_metrics.max_latency_ms,
                p50_latency_ms=candidate_metrics.p50_latency_ms,
                p95_latency_ms=candidate_metrics.p95_latency_ms,
                p99_latency_ms=candidate_metrics.p99_latency_ms,
                errors=candidate_metrics.errors,
                error_rate=(
                    candidate_metrics.errors / candidate_metrics.request_count
                    if candidate_metrics.request_count > 0
                    else 0.0
                ),
            )

            comparison_response = MetricsComparisonResponse(
                result=result.comparison.result.value,
                accuracy_delta=result.comparison.accuracy_delta,
                latency_delta_ms=result.comparison.latency_delta_ms,
                sample_size_champion=result.comparison.sample_size_champion,
                sample_size_candidate=result.comparison.sample_size_candidate,
                is_significant=result.comparison.is_significant,
                candidate_is_better=result.comparison.candidate_is_better,
                recommendation=result.comparison.recommendation,
                compared_at=result.comparison.compared_at.isoformat(),
                champion_metrics=champion_response,
                candidate_metrics=candidate_response,
            )

        # Build and return response
        response = PromoteCandidateResponse(
            status=result.status.value,
            previous_champion_version=result.previous_champion_version,
            new_champion_version=result.new_champion_version,
            error_message=result.error_message,
            promoted_at=result.promoted_at.isoformat() if result.promoted_at else None,
            comparison=comparison_response,
        )

        logger.info(
            f"Model promotion request: status={result.status.value}, "
            f"force={force}, "
            f"previous_version={result.previous_champion_version}, "
            f"new_version={result.new_champion_version}"
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error promoting candidate model: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,  # Disable reload to avoid import issues in containers
        log_level="info",
    )
