"""Constitutional Hash: cdd01ef066bc6cf2
Insights Route - GET /insights endpoint with AI-generated governance summaries

Provides AI-powered governance insights including:
- Executive summaries of governance trends
- Business impact analysis
- Recommended actions for compliance improvement
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Add analytics-engine to path for importing InsightGenerator
ANALYTICS_ENGINE_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "analytics-engine" / "src"
)
if str(ANALYTICS_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(ANALYTICS_ENGINE_PATH))

try:
    from insight_generator import GovernanceInsight, InsightGenerator
except ImportError:
    GovernanceInsight = None
    InsightGenerator = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["insights"])


class InsightResponse(BaseModel):
    """Response model for governance insights"""

    summary: str = Field(description="One-sentence executive summary of governance trends")
    business_impact: str = Field(description="Analysis of business implications and risks")
    recommended_action: str = Field(
        description="Actionable recommendation for governance improvement"
    )
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score for the insight (0-1)",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when insight was generated",
    )
    model_used: Optional[str] = Field(
        default=None,
        description="AI model used for generation",
    )
    cached: bool = Field(
        default=False,
        description="Whether the insight was served from cache",
    )


class InsightErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of error",
    )


# Module-level insight generator instance
_insight_generator: Optional[InsightGenerator] = None


def get_insight_generator() -> Optional[InsightGenerator]:
    """
    Get or create the InsightGenerator instance.

    Returns:
        InsightGenerator instance or None if not available
    """
    global _insight_generator

    if _insight_generator is not None:
        return _insight_generator

    if InsightGenerator is None:
        logger.warning("InsightGenerator not available. Ensure analytics-engine is in the path.")
        return None

    _insight_generator = InsightGenerator(
        cache_enabled=True,
        cache_ttl_seconds=3600,  # 1 hour cache
    )

    return _insight_generator


def get_sample_governance_data() -> Dict[str, Any]:
    """
    Get sample governance data for insight generation.

    In production, this would fetch real data from Kafka/Redis.
    Returns sample data for demonstration and testing.

    Returns:
        Dictionary with governance metrics
    """
    # Sample governance data for testing
    # In production, this would be fetched from Redis cache
    # populated by the analytics-engine Kafka consumer
    return {
        "violation_count": 12,
        "top_violated_policy": "data-access-policy",
        "trend": "increasing",
        "total_events": 1547,
        "unique_users": 89,
        "severity_distribution": {
            "low": 3,
            "medium": 5,
            "high": 3,
            "critical": 1,
        },
        "period": "last_7_days",
    }


@router.get(
    "",
    response_model=InsightResponse,
    responses={
        200: {"description": "Successfully generated governance insight"},
        500: {"description": "Internal server error"},
        503: {"description": "AI service temporarily unavailable"},
    },
    summary="Get AI-generated governance insights",
    description=(
        "Generates AI-powered insights from governance data including "
        "executive summaries, business impact analysis, and recommended actions."
    ),
)
async def get_insights(
    refresh: bool = Query(
        default=False,
        description="Force refresh of cached insights",
    ),
    time_range: str = Query(
        default="last_7_days",
        description="Time range for governance data analysis",
        enum=["last_24_hours", "last_7_days", "last_30_days", "all_time"],
    ),
) -> InsightResponse:
    """
    Get AI-generated governance insights.

    Returns AI-powered analysis of governance data including:
    - Executive summary of current governance state
    - Business impact assessment
    - Recommended actions for improvement

    Args:
        refresh: Force refresh of cached insights
        time_range: Time range for data analysis

    Returns:
        InsightResponse with generated insight data

    Raises:
        HTTPException: If insight generation fails
    """
    generator = get_insight_generator()

    # Get governance data (sample data for now, Redis integration in future)
    governance_data = get_sample_governance_data()
    governance_data["period"] = time_range

    # Check if generator is available
    if generator is None or not generator.is_available:
        logger.warning("InsightGenerator not available, returning fallback response")
        # Return a fallback response when AI is not available
        return InsightResponse(
            summary=(
                f"Governance analysis for {time_range}: "
                f"{governance_data['violation_count']} violations detected, "
                f"trend is {governance_data['trend']}."
            ),
            business_impact=(
                f"The {governance_data['top_violated_policy']} policy has the most violations. "
                f"{governance_data['unique_users']} unique users triggered governance events."
            ),
            recommended_action=(
                "Review the most frequently violated policies and consider "
                "implementing additional training or automated controls."
            ),
            confidence=0.5,  # Lower confidence for non-AI response
            generated_at=datetime.now(timezone.utc),
            model_used="fallback",
            cached=False,
        )

    # Clear cache if refresh requested
    if refresh:
        generator.clear_cache()

    # Generate insight using the InsightGenerator
    try:
        result = generator.generate_insight(governance_data)

        if result.error_message:
            logger.warning(f"Insight generation error: {result.error_message}")
            # Return fallback if AI failed but don't raise error
            return InsightResponse(
                summary=(
                    f"Governance analysis for {time_range}: "
                    f"{governance_data['violation_count']} violations detected, "
                    f"trend is {governance_data['trend']}."
                ),
                business_impact=(
                    f"The {governance_data['top_violated_policy']} policy has the most violations. "
                    f"{governance_data['unique_users']} unique users triggered governance events."
                ),
                recommended_action=(
                    "Review the most frequently violated policies and consider "
                    "implementing additional training or automated controls."
                ),
                confidence=0.5,
                generated_at=datetime.now(timezone.utc),
                model_used="fallback",
                cached=False,
            )

        if result.insight is None:
            logger.error("Insight generation returned None")
            raise HTTPException(
                status_code=503,
                detail="AI insights temporarily unavailable.",
            )

        return InsightResponse(
            summary=result.insight.summary,
            business_impact=result.insight.business_impact,
            recommended_action=result.insight.recommended_action,
            confidence=result.insight.confidence,
            generated_at=result.generation_timestamp,
            model_used=result.model_used,
            cached=result.cached,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate insight: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate governance insights. Please try again later.",
        ) from None


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get insight generator status",
    description="Returns the current status and configuration of the insight generator.",
)
async def get_insights_status() -> Dict[str, Any]:
    """
    Get the status of the insight generator.

    Returns:
        Dictionary with generator status and configuration
    """
    generator = get_insight_generator()

    if generator is None:
        return {
            "status": "unavailable",
            "message": "InsightGenerator module not loaded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    info = generator.get_generator_info()
    info["status"] = "available" if info.get("is_available") else "not_configured"
    info["timestamp"] = datetime.now(timezone.utc).isoformat()

    return info
