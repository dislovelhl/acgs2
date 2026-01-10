"""Constitutional Hash: cdd01ef066bc6cf2
Violation Predictor - Prophet time-series forecasting for governance violation predictions

Uses Facebook Prophet to forecast future policy violation counts based on historical
governance event data. Provides 30-day forecasts with confidence intervals.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

try:
    from prophet import Prophet
except ImportError:
    Prophet = None

logger = logging.getLogger(__name__)


class ForecastPoint(BaseModel):
    """Model representing a single forecast point in the time series"""

    date: datetime
    predicted_value: float = Field(
        ge=0.0,
        description="Predicted violation count (yhat)",
    )
    lower_bound: float = Field(
        ge=0.0,
        description="Lower bound of prediction interval (yhat_lower)",
    )
    upper_bound: float = Field(
        ge=0.0,
        description="Upper bound of prediction interval (yhat_upper)",
    )
    trend: float = Field(
        default=0.0,
        description="Trend component of the forecast",
    )


class ViolationForecast(BaseModel):
    """Result of violation forecasting analysis"""

    forecast_timestamp: datetime
    historical_days: int
    forecast_days: int
    forecast_points: List[ForecastPoint]
    model_trained: bool
    error_message: Optional[str] = None
    summary: Dict[str, Any] = Field(default_factory=dict)


class ViolationPredictor:
    """
    Prophet-based time-series forecaster for governance violations.

    Forecasts future violation counts based on historical patterns,
    accounting for weekly and yearly seasonality in governance data.

    Usage:
        predictor = ViolationPredictor()
        df = data_processor.prepare_for_prophet(events_df)
        forecast = predictor.forecast(df, periods=30)
    """

    MIN_HISTORICAL_DAYS = 14
    DEFAULT_FORECAST_DAYS = 30

    def __init__(
        self,
        growth: str = "linear",
        seasonality_mode: str = "additive",
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True,
        daily_seasonality: bool = False,
        uncertainty_samples: int = 1000,
    ):
        """
        Initialize the violation predictor.

        Args:
            growth: Growth model ('linear' or 'logistic')
            seasonality_mode: Seasonality mode ('additive' or 'multiplicative')
            yearly_seasonality: Enable yearly seasonality
            weekly_seasonality: Enable weekly seasonality
            daily_seasonality: Enable daily seasonality
            uncertainty_samples: Number of samples for uncertainty intervals
        """
        if Prophet is None:
            logger.warning("Prophet not available. Install with: pip install prophet")

        self.growth = growth
        self.seasonality_mode = seasonality_mode
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.uncertainty_samples = uncertainty_samples

        self._model: Optional[Prophet] = None
        self._is_fitted = False
        self._last_training_time: Optional[datetime] = None
        self._training_data: Optional[pd.DataFrame] = None

    @property
    def is_fitted(self) -> bool:
        """Check if the model has been trained"""
        return self._is_fitted

    def _check_prophet_available(self) -> bool:
        """Check if Prophet is available"""
        if Prophet is None:
            logger.error("Prophet is not installed. Install with: pip install prophet")
            return False
        return True

    def _initialize_model(self) -> None:
        """Initialize the Prophet model with configured parameters"""
        if not self._check_prophet_available():
            return

        self._model = Prophet(
            growth=self.growth,
            seasonality_mode=self.seasonality_mode,
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality,
            uncertainty_samples=self.uncertainty_samples,
        )

    def _validate_data(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Validate and prepare DataFrame for Prophet.

        Prophet requires columns named 'ds' (datetime) and 'y' (value).

        Args:
            df: Input DataFrame with governance metrics

        Returns:
            Validated DataFrame with 'ds' and 'y' columns, or None if invalid
        """
        if df.empty:
            logger.warning("Empty DataFrame provided, cannot perform forecasting")
            return None

        # Check for required Prophet columns
        if "ds" not in df.columns:
            logger.error(
                "DataFrame must have 'ds' column for dates. "
                "Use data_processor.prepare_for_prophet() to prepare data."
            )
            return None

        if "y" not in df.columns:
            logger.error(
                "DataFrame must have 'y' column for values. "
                "Use data_processor.prepare_for_prophet() to prepare data."
            )
            return None

        # Create a copy and ensure proper types
        prophet_df = df[["ds", "y"]].copy()
        prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
        prophet_df["y"] = pd.to_numeric(prophet_df["y"], errors="coerce")

        # Handle missing values
        if prophet_df["y"].isnull().any():
            logger.warning("Missing values in 'y' column, filling with 0")
            prophet_df["y"] = prophet_df["y"].fillna(0)

        # Ensure non-negative values
        prophet_df["y"] = prophet_df["y"].clip(lower=0)

        # Check for sufficient historical data
        unique_days = prophet_df["ds"].nunique()
        if unique_days < self.MIN_HISTORICAL_DAYS:
            logger.warning(
                f"Insufficient historical data: {unique_days} days. "
                f"Need at least {self.MIN_HISTORICAL_DAYS} days for reliable forecasting."
            )
            return None

        # Sort by date
        prophet_df = prophet_df.sort_values("ds").reset_index(drop=True)

        return prophet_df

    def fit(self, df: pd.DataFrame) -> bool:
        """
        Train the Prophet model on historical violation data.

        Args:
            df: DataFrame with 'ds' and 'y' columns (from prepare_for_prophet)

        Returns:
            True if training successful, False otherwise
        """
        if not self._check_prophet_available():
            return False

        validated_df = self._validate_data(df)
        if validated_df is None:
            return False

        try:
            self._initialize_model()

            # Suppress Prophet logging during fitting
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self._model.fit(validated_df)

            self._is_fitted = True
            self._last_training_time = datetime.now(timezone.utc)
            self._training_data = validated_df.copy()

            logger.info(f"Prophet model trained on {len(validated_df)} days of data")
            return True

        except Exception as e:
            logger.error(f"Failed to train Prophet model: {e}")
            self._is_fitted = False
            return False

    def predict(self, periods: int = 30) -> pd.DataFrame:
        """
        Generate predictions for future periods.

        Args:
            periods: Number of days to forecast into the future

        Returns:
            DataFrame with forecast including ds, yhat, yhat_lower, yhat_upper
        """
        if not self._is_fitted:
            logger.warning("Model not fitted. Call fit() first.")
            return pd.DataFrame(columns=["ds", "yhat", "yhat_lower", "yhat_upper", "trend"])

        try:
            # Create future DataFrame
            future = self._model.make_future_dataframe(periods=periods)

            # Generate forecast
            import warnings

            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                forecast = self._model.predict(future)

            # Select relevant columns
            result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper", "trend"]].copy()

            # Ensure non-negative predictions
            result["yhat"] = result["yhat"].clip(lower=0)
            result["yhat_lower"] = result["yhat_lower"].clip(lower=0)
            result["yhat_upper"] = result["yhat_upper"].clip(lower=0)

            return result

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return pd.DataFrame(columns=["ds", "yhat", "yhat_lower", "yhat_upper", "trend"])

    def forecast(
        self,
        df: pd.DataFrame,
        periods: int = 30,
    ) -> ViolationForecast:
        """
        Train and generate violation forecasts in one step.

        Args:
            df: DataFrame with 'ds' and 'y' columns (from prepare_for_prophet)
            periods: Number of days to forecast

        Returns:
            ViolationForecast with forecast points and summary
        """
        now = datetime.now(timezone.utc)

        # Handle empty data
        if df.empty:
            return ViolationForecast(
                forecast_timestamp=now,
                historical_days=0,
                forecast_days=periods,
                forecast_points=[],
                model_trained=False,
                error_message="No historical data provided for forecasting",
                summary={"status": "error", "reason": "no_data"},
            )

        # Check for Prophet availability
        if not self._check_prophet_available():
            return ViolationForecast(
                forecast_timestamp=now,
                historical_days=len(df),
                forecast_days=periods,
                forecast_points=[],
                model_trained=False,
                error_message="Prophet library not installed. Install with: pip install prophet",
                summary={"status": "error", "reason": "prophet_not_available"},
            )

        # Validate data
        validated_df = self._validate_data(df)
        if validated_df is None:
            unique_days = df["ds"].nunique() if "ds" in df.columns else 0
            return ViolationForecast(
                forecast_timestamp=now,
                historical_days=unique_days,
                forecast_days=periods,
                forecast_points=[],
                model_trained=False,
                error_message=(
                    f"Insufficient data for predictions. "
                    f"Collect at least {self.MIN_HISTORICAL_DAYS} days of governance events."
                ),
                summary={
                    "status": "error",
                    "reason": "insufficient_data",
                    "days_available": unique_days,
                    "days_required": self.MIN_HISTORICAL_DAYS,
                },
            )

        # Train the model
        if not self.fit(validated_df):
            return ViolationForecast(
                forecast_timestamp=now,
                historical_days=len(validated_df),
                forecast_days=periods,
                forecast_points=[],
                model_trained=False,
                error_message="Failed to train forecasting model",
                summary={"status": "error", "reason": "training_failed"},
            )

        # Generate predictions
        forecast_df = self.predict(periods=periods)

        if forecast_df.empty:
            return ViolationForecast(
                forecast_timestamp=now,
                historical_days=len(validated_df),
                forecast_days=periods,
                forecast_points=[],
                model_trained=True,
                error_message="Failed to generate predictions",
                summary={"status": "error", "reason": "prediction_failed"},
            )

        # Filter to only future dates
        last_historical_date = validated_df["ds"].max()
        future_forecast = forecast_df[forecast_df["ds"] > last_historical_date]

        # Convert to ForecastPoint models
        forecast_points: List[ForecastPoint] = []
        for _, row in future_forecast.iterrows():
            point = ForecastPoint(
                date=row["ds"].to_pydatetime().replace(tzinfo=timezone.utc),
                predicted_value=float(row["yhat"]),
                lower_bound=float(row["yhat_lower"]),
                upper_bound=float(row["yhat_upper"]),
                trend=float(row["trend"]) if pd.notna(row["trend"]) else 0.0,
            )
            forecast_points.append(point)

        # Calculate summary statistics
        if forecast_points:
            predictions = [p.predicted_value for p in forecast_points]
            summary = {
                "status": "success",
                "mean_predicted_violations": float(np.mean(predictions)),
                "max_predicted_violations": float(np.max(predictions)),
                "min_predicted_violations": float(np.min(predictions)),
                "total_predicted_violations": float(np.sum(predictions)),
                "trend_direction": (
                    "increasing"
                    if predictions[-1] > predictions[0]
                    else "decreasing" if predictions[-1] < predictions[0] else "stable"
                ),
            }
        else:
            summary = {"status": "success", "note": "no_future_points"}

        logger.info(f"Generated {len(forecast_points)} forecast points for {periods} days ahead")

        return ViolationForecast(
            forecast_timestamp=now,
            historical_days=len(validated_df),
            forecast_days=periods,
            forecast_points=forecast_points,
            model_trained=True,
            error_message=None,
            summary=summary,
        )

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model state.

        Returns:
            Dictionary with model configuration and status
        """
        return {
            "is_fitted": self._is_fitted,
            "growth": self.growth,
            "seasonality_mode": self.seasonality_mode,
            "yearly_seasonality": self.yearly_seasonality,
            "weekly_seasonality": self.weekly_seasonality,
            "daily_seasonality": self.daily_seasonality,
            "min_historical_days": self.MIN_HISTORICAL_DAYS,
            "last_training_time": (
                self._last_training_time.isoformat() if self._last_training_time else None
            ),
            "training_data_points": (
                len(self._training_data) if self._training_data is not None else 0
            ),
            "prophet_available": Prophet is not None,
        }

    def get_forecast_as_dict(
        self,
        forecast: ViolationForecast,
    ) -> Dict[str, Any]:
        """
        Convert ViolationForecast to a dictionary suitable for API responses.

        Args:
            forecast: ViolationForecast object

        Returns:
            Dictionary representation for JSON serialization
        """
        return {
            "forecast_timestamp": forecast.forecast_timestamp.isoformat(),
            "historical_days": forecast.historical_days,
            "forecast_days": forecast.forecast_days,
            "model_trained": forecast.model_trained,
            "error_message": forecast.error_message,
            "summary": forecast.summary,
            "forecast": [
                {
                    "date": point.date.strftime("%Y-%m-%d"),
                    "predicted_value": round(point.predicted_value, 2),
                    "lower_bound": round(point.lower_bound, 2),
                    "upper_bound": round(point.upper_bound, 2),
                    "trend": round(point.trend, 2),
                }
                for point in forecast.forecast_points
            ],
        }
