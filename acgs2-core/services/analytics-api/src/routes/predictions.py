"""Constitutional Hash: cdd01ef066bc6cf2
Predictions Route - GET /predictions endpoint with violation forecasts

Provides time-series forecasting for governance violations including:
- Prophet-based violation count predictions for 30 days
- Confidence intervals (lower/upper bounds)
- Trend direction analysis
"""

import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Add analytics-engine to path for importing ViolationPredictor
ANALYTICS_ENGINE_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / "analytics-engine" / "src"
)
if str(ANALYTICS_ENGINE_PATH) not in sys.path:
    sys.path.insert(0, str(ANALYTICS_ENGINE_PATH))

try:
    from predictor import ForecastPoint, ViolationForecast, ViolationPredictor
except ImportError:
    ForecastPoint = None
    ViolationForecast = None
    ViolationPredictor = None

try:
    import pandas as pd
except ImportError:
    pd = None

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predictions", tags=["predictions"])


class PredictionPoint(BaseModel):
    """Model representing a single prediction point"""

    date: str = Field(description="Forecast date in YYYY-MM-DD format")
    predicted_value: float = Field(
        ge=0.0,
        description="Predicted violation count",
    )
    lower_bound: float = Field(
        ge=0.0,
        description="Lower bound of prediction interval (95% confidence)",
    )
    upper_bound: float = Field(
        ge=0.0,
        description="Upper bound of prediction interval (95% confidence)",
    )
    trend: float = Field(
        default=0.0,
        description="Trend component of the forecast",
    )


class PredictionSummary(BaseModel):
    """Summary statistics for the forecast"""

    status: str = Field(description="Forecast status: 'success' or 'error'")
    mean_predicted_violations: Optional[float] = Field(
        default=None,
        description="Mean predicted daily violations over forecast period",
    )
    max_predicted_violations: Optional[float] = Field(
        default=None,
        description="Maximum predicted daily violations",
    )
    min_predicted_violations: Optional[float] = Field(
        default=None,
        description="Minimum predicted daily violations",
    )
    total_predicted_violations: Optional[float] = Field(
        default=None,
        description="Total predicted violations over forecast period",
    )
    trend_direction: Optional[str] = Field(
        default=None,
        description="Overall trend: 'increasing', 'decreasing', or 'stable'",
    )
    reason: Optional[str] = Field(
        default=None,
        description="Reason for error if status is 'error'",
    )


class PredictionsResponse(BaseModel):
    """Response model for violation predictions"""

    forecast_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when forecast was generated",
    )
    historical_days: int = Field(
        default=0,
        description="Number of historical days used for training",
    )
    forecast_days: int = Field(
        default=30,
        description="Number of days in the forecast",
    )
    model_trained: bool = Field(
        default=False,
        description="Whether the prediction model was successfully trained",
    )
    predictions: List[PredictionPoint] = Field(
        default_factory=list,
        description="List of prediction points",
    )
    summary: PredictionSummary = Field(
        default_factory=lambda: PredictionSummary(status="pending"),
        description="Summary statistics for the forecast",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if forecast failed",
    )


class PredictionsErrorResponse(BaseModel):
    """Error response model"""

    error: str = Field(description="Error message")
    detail: Optional[str] = Field(default=None, description="Detailed error information")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of error",
    )


# Module-level predictor instance
_violation_predictor: Optional[ViolationPredictor] = None


def get_violation_predictor() -> Optional[ViolationPredictor]:
    """
    Get or create the ViolationPredictor instance.

    Returns:
        ViolationPredictor instance or None if not available
    """
    global _violation_predictor

    if _violation_predictor is not None:
        return _violation_predictor

    if ViolationPredictor is None:
        logger.warning("ViolationPredictor not available. Ensure analytics-engine is in the path.")
        return None

    _violation_predictor = ViolationPredictor(
        growth="linear",
        seasonality_mode="additive",
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
    )

    return _violation_predictor


def get_sample_historical_data(days: int = 30) -> List[Dict[str, Any]]:
    """
    Get sample historical violation data for prediction.

    In production, this would fetch real data from Kafka/Redis.
    Returns sample data for demonstration and testing.

    Args:
        days: Number of historical days to generate

    Returns:
        List of dictionaries with date and violation_count
    """
    # Sample historical data for testing
    # In production, this would be fetched from Redis cache
    # populated by the analytics-engine Kafka consumer
    import random

    random.seed(42)  # For reproducible sample data

    base_date = datetime.now(timezone.utc) - timedelta(days=days)
    data = []

    for i in range(days):
        date = base_date + timedelta(days=i)
        # Simulate violation pattern with some weekly seasonality
        base_violations = 5 + (i % 7) * 0.5  # Weekly pattern
        noise = random.uniform(-2, 2)
        violations = max(0, base_violations + noise)

        data.append(
            {
                "ds": date.strftime("%Y-%m-%d"),
                "y": violations,
            }
        )

    return data


def _convert_forecast_to_response(forecast: ViolationForecast) -> PredictionsResponse:
    """
    Convert ViolationForecast to PredictionsResponse.

    Args:
        forecast: ViolationForecast from the predictor

    Returns:
        PredictionsResponse for the API
    """
    prediction_points = [
        PredictionPoint(
            date=point.date.strftime("%Y-%m-%d"),
            predicted_value=round(point.predicted_value, 2),
            lower_bound=round(point.lower_bound, 2),
            upper_bound=round(point.upper_bound, 2),
            trend=round(point.trend, 2),
        )
        for point in forecast.forecast_points
    ]

    summary_data = forecast.summary
    summary = PredictionSummary(
        status=summary_data.get("status", "unknown"),
        mean_predicted_violations=summary_data.get("mean_predicted_violations"),
        max_predicted_violations=summary_data.get("max_predicted_violations"),
        min_predicted_violations=summary_data.get("min_predicted_violations"),
        total_predicted_violations=summary_data.get("total_predicted_violations"),
        trend_direction=summary_data.get("trend_direction"),
        reason=summary_data.get("reason"),
    )

    return PredictionsResponse(
        forecast_timestamp=forecast.forecast_timestamp,
        historical_days=forecast.historical_days,
        forecast_days=forecast.forecast_days,
        model_trained=forecast.model_trained,
        predictions=prediction_points,
        summary=summary,
        error_message=forecast.error_message,
    )


@router.get(
    "",
    response_model=PredictionsResponse,
    responses={
        200: {"description": "Successfully generated violation predictions"},
        500: {"description": "Internal server error"},
        503: {"description": "Prediction service temporarily unavailable"},
    },
    summary="Get violation forecasts",
    description=(
        "Generates time-series forecasts for governance violations using Prophet. "
        "Provides 30-day predictions with confidence intervals and trend analysis."
    ),
)
async def get_predictions(
    forecast_days: int = Query(
        default=30,
        ge=1,
        le=90,
        description="Number of days to forecast into the future",
    ),
    historical_days: int = Query(
        default=30,
        ge=14,
        le=365,
        description="Number of historical days to use for training (minimum 14)",
    ),
) -> PredictionsResponse:
    """
    Get violation predictions.

    Uses Prophet time-series forecasting to predict future policy violations
    based on historical governance event data.

    Args:
        forecast_days: Number of days to forecast (1-90)
        historical_days: Historical days for training (14-365, minimum 14 required)

    Returns:
        PredictionsResponse with forecast points and summary

    Raises:
        HTTPException: If prediction fails
    """
    now = datetime.now(timezone.utc)

    # Check if pandas is available
    if pd is None:
        logger.warning("pandas not available, returning fallback response")
        return PredictionsResponse(
            forecast_timestamp=now,
            historical_days=0,
            forecast_days=forecast_days,
            model_trained=False,
            predictions=[],
            summary=PredictionSummary(
                status="error",
                reason="pandas_not_available",
            ),
            error_message="pandas library not available for predictions",
        )

    predictor = get_violation_predictor()

    # Get historical data (sample data for now, Redis integration in future)
    historical_data = get_sample_historical_data(days=historical_days)

    # Check if predictor is available
    if predictor is None:
        logger.warning("ViolationPredictor not available, returning fallback response")
        return PredictionsResponse(
            forecast_timestamp=now,
            historical_days=len(historical_data),
            forecast_days=forecast_days,
            model_trained=False,
            predictions=[],
            summary=PredictionSummary(
                status="error",
                reason="predictor_not_available",
            ),
            error_message="Prediction service not available. Prophet may not be installed.",
        )

    try:
        # Convert to DataFrame for the predictor
        df = pd.DataFrame(historical_data)

        # Generate forecast
        forecast = predictor.forecast(df, periods=forecast_days)

        # Convert to response model
        response = _convert_forecast_to_response(forecast)

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate predictions: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to generate violation predictions. Please try again later.",
        ) from None


@router.get(
    "/status",
    response_model=Dict[str, Any],
    summary="Get prediction service status",
    description="Returns the current status and configuration of the violation predictor.",
)
async def get_predictions_status() -> Dict[str, Any]:
    """
    Get the status of the violation predictor.

    Returns:
        Dictionary with predictor status and configuration
    """
    predictor = get_violation_predictor()

    if predictor is None:
        return {
            "status": "unavailable",
            "message": "ViolationPredictor module not loaded",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    info = predictor.get_model_info()
    info["status"] = "available" if info.get("prophet_available") else "not_configured"
    info["timestamp"] = datetime.now(timezone.utc).isoformat()

    return info
