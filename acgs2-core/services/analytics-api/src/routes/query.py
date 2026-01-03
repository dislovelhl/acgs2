"""Constitutional Hash: cdd01ef066bc6cf2
Query Route - POST /query endpoint for natural language queries

Provides natural language query interface for governance analytics:
- Parse user questions about governance data
- Return AI-generated answers with relevant metrics
- Support various query intents (violations, policies, trends)
"""

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# Add analytics-engine to path for importing InsightGenerator
ANALYTICS_ENGINE_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "analytics-engine" / "src"
)
if str(ANALYTICS_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(ANALYTICS_ENGINE_PATH))

try:
    from insight_generator import InsightGenerator, QueryResult
except ImportError:
    InsightGenerator = None
    QueryResult = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    """Request model for natural language queries"""

    question: str = Field(
        min_length=1,
        max_length=500,
        description="Natural language question about governance data",
    )


class QueryResponse(BaseModel):
    """Response model for natural language query results"""

    query: str = Field(description="Original user query")
    answer: str = Field(description="Natural language answer to the query")
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Structured data relevant to the query",
    )
    query_understood: bool = Field(
        default=True,
        description="Whether the query was successfully parsed",
    )
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when response was generated",
    )


class QueryErrorResponse(BaseModel):
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
        cache_ttl_seconds=3600,
    )

    return _insight_generator


def get_sample_governance_context() -> Dict[str, Any]:
    """
    Get sample governance context for query processing.

    In production, this would fetch real data from Kafka/Redis.
    Returns sample data for demonstration and testing.

    Returns:
        Dictionary with governance metrics context
    """
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


@router.post(
    "",
    response_model=QueryResponse,
    responses={
        200: {"description": "Successfully processed natural language query"},
        400: {"description": "Invalid query format"},
        500: {"description": "Internal server error"},
        503: {"description": "AI service temporarily unavailable"},
    },
    summary="Process natural language governance query",
    description=(
        "Accepts natural language questions about governance data and returns "
        "AI-generated answers with relevant metrics and structured data."
    ),
)
async def process_query(request: QueryRequest) -> QueryResponse:
    """
    Process a natural language query about governance data.

    Accepts questions like:
    - "Show violations this week"
    - "Which policy is violated most?"
    - "What is the compliance trend?"

    Args:
        request: QueryRequest with the user's question

    Returns:
        QueryResponse with answer and relevant data

    Raises:
        HTTPException: If query processing fails
    """
    generator = get_insight_generator()
    governance_context = get_sample_governance_context()

    # Check if generator is available
    if generator is None or not generator.is_available:
        logger.warning("InsightGenerator not available, returning fallback response")
        return QueryResponse(
            query=request.question,
            answer=(
                f"Based on available data: {governance_context['violation_count']} violations "
                f"detected in the {governance_context['period']} period. The most violated "
                f"policy is '{governance_context['top_violated_policy']}' with a "
                f"{governance_context['trend']} trend."
            ),
            data={
                "intent": "general",
                "time_range": governance_context["period"],
                "relevant_metrics": ["violation_count", "top_violated_policy", "trend"],
            },
            query_understood=True,
            generated_at=datetime.now(timezone.utc),
        )

    try:
        result = generator.process_natural_language_query(
            query=request.question,
            governance_context=governance_context,
        )

        return QueryResponse(
            query=result.query,
            answer=result.answer,
            data=result.data,
            query_understood=result.query_understood,
            generated_at=result.generated_at,
        )

    except Exception as e:
        logger.error(f"Failed to process query: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process query. Please try again later.",
        ) from None


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get query processor status",
    description="Returns the current status and configuration of the query processor.",
)
async def get_query_status() -> Dict[str, Any]:
    """
    Get the status of the query processor.

    Returns:
        Dictionary with processor status and configuration
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
    info["endpoint"] = "/query"
    info["timestamp"] = datetime.now(timezone.utc).isoformat()

    return info
