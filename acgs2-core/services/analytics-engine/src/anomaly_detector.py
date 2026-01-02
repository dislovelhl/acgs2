"""
Anomaly Detector - IsolationForest-based anomaly detection for governance metrics

Detects unusual patterns in governance data such as sudden spikes in violations,
unusual user activity, or abnormal policy changes using IsolationForest algorithm.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
except ImportError:
    IsolationForest = None
    StandardScaler = None

logger = logging.getLogger(__name__)


class DetectedAnomaly(BaseModel):
    """Model representing a detected anomaly in governance data"""

    anomaly_id: str
    timestamp: datetime
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


class AnomalyDetectionResult(BaseModel):
    """Result of anomaly detection analysis"""

    analysis_timestamp: datetime
    total_records_analyzed: int
    anomalies_detected: int
    contamination_rate: float
    anomalies: List[DetectedAnomaly]
    model_trained: bool


class AnomalyDetector:
    """
    IsolationForest-based anomaly detector for governance metrics.

    Detects unusual patterns in governance data by analyzing:
    - Violation counts
    - User activity
    - Policy changes
    - Event volumes

    Uses scikit-learn's IsolationForest with configurable contamination rate.
    """

    DEFAULT_FEATURES = ["violation_count", "user_count", "policy_changes"]
    SEVERITY_THRESHOLDS = {
        "critical": -0.5,
        "high": -0.3,
        "medium": -0.1,
        "low": 0.0,
    }

    def __init__(
        self,
        contamination: float = 0.1,
        n_estimators: int = 100,
        random_state: int = 42,
        n_jobs: int = -1,
        features: Optional[List[str]] = None,
    ):
        """
        Initialize the anomaly detector.

        Args:
            contamination: Expected proportion of anomalies (0.0 to 0.5)
            n_estimators: Number of base estimators in the ensemble
            random_state: Random seed for reproducibility
            n_jobs: Number of CPU cores to use (-1 for all)
            features: List of feature columns to use for detection
        """
        if IsolationForest is None:
            logger.warning("scikit-learn not available. Install with: pip install scikit-learn")

        self.contamination = max(0.01, min(0.5, contamination))
        self.n_estimators = n_estimators
        self.random_state = random_state
        self.n_jobs = n_jobs
        self.features = features or self.DEFAULT_FEATURES

        self._model: Optional[IsolationForest] = None
        self._scaler: Optional[StandardScaler] = None
        self._is_fitted = False
        self._last_training_time: Optional[datetime] = None

    @property
    def is_fitted(self) -> bool:
        """Check if the model has been trained"""
        return self._is_fitted

    def _check_sklearn_available(self) -> bool:
        """Check if scikit-learn is available"""
        if IsolationForest is None or StandardScaler is None:
            logger.error("scikit-learn is not installed. " "Install with: pip install scikit-learn")
            return False
        return True

    def _initialize_model(self) -> None:
        """Initialize the IsolationForest model"""
        if not self._check_sklearn_available():
            return

        self._model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        )
        self._scaler = StandardScaler()

    def _validate_data(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Validate and prepare data for anomaly detection.

        Args:
            df: Input DataFrame with governance metrics

        Returns:
            Validated DataFrame with required features, or None if invalid
        """
        if df.empty:
            logger.warning("Empty DataFrame provided, cannot perform anomaly detection")
            return None

        # Check for required features
        missing_features = [f for f in self.features if f not in df.columns]
        if missing_features:
            logger.warning(
                f"Missing features for anomaly detection: {missing_features}. "
                f"Available columns: {list(df.columns)}"
            )
            # Try to use available features
            available_features = [f for f in self.features if f in df.columns]
            if not available_features:
                logger.error("No valid features found for anomaly detection")
                return None
            self.features = available_features

        # Extract feature columns
        feature_df = df[self.features].copy()

        # Handle missing values
        if feature_df.isnull().any().any():
            logger.warning("Missing values detected, filling with column means")
            feature_df = feature_df.fillna(feature_df.mean())

        # Check for zero variance columns
        zero_var_cols = feature_df.columns[feature_df.std() == 0].tolist()
        if zero_var_cols:
            logger.warning(
                f"Zero variance columns detected: {zero_var_cols}. "
                "Adding small noise for numerical stability."
            )
            for col in zero_var_cols:
                feature_df[col] = feature_df[col] + np.random.normal(0, 0.001, len(feature_df))

        return feature_df

    def fit(self, df: pd.DataFrame) -> bool:
        """
        Train the anomaly detection model on governance data.

        Args:
            df: DataFrame with governance metrics (from prepare_for_anomaly_detection)

        Returns:
            True if training successful, False otherwise
        """
        if not self._check_sklearn_available():
            return False

        feature_df = self._validate_data(df)
        if feature_df is None:
            return False

        if len(feature_df) < 5:
            logger.warning(
                f"Insufficient data for anomaly detection: {len(feature_df)} records. "
                "Need at least 5 records."
            )
            return False

        try:
            self._initialize_model()

            # Scale features for better model performance
            scaled_features = self._scaler.fit_transform(feature_df)

            # Fit the IsolationForest model
            self._model.fit(scaled_features)

            self._is_fitted = True
            self._last_training_time = datetime.now(timezone.utc)

            logger.info(
                f"Anomaly detection model trained on {len(feature_df)} records "
                f"with contamination={self.contamination}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to train anomaly detection model: {e}")
            self._is_fitted = False
            return False

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Predict anomalies in new data.

        Args:
            df: DataFrame with governance metrics

        Returns:
            Array of predictions: -1 for anomaly, 1 for normal
        """
        if not self._is_fitted:
            logger.warning("Model not fitted. Call fit() first or use fit_predict()")
            return np.array([])

        feature_df = self._validate_data(df)
        if feature_df is None:
            return np.array([])

        try:
            scaled_features = self._scaler.transform(feature_df)
            predictions = self._model.predict(scaled_features)
            return predictions
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return np.array([])

    def decision_function(self, df: pd.DataFrame) -> np.ndarray:
        """
        Get anomaly scores for data points.

        Lower scores indicate more anomalous points.
        Scores range approximately from -1 (most anomalous) to 1 (most normal).

        Args:
            df: DataFrame with governance metrics

        Returns:
            Array of anomaly scores
        """
        if not self._is_fitted:
            logger.warning("Model not fitted. Call fit() first.")
            return np.array([])

        feature_df = self._validate_data(df)
        if feature_df is None:
            return np.array([])

        try:
            scaled_features = self._scaler.transform(feature_df)
            scores = self._model.decision_function(scaled_features)
            return scores
        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            return np.array([])

    def fit_predict(self, df: pd.DataFrame) -> np.ndarray:
        """
        Train the model and predict anomalies in one step.

        Args:
            df: DataFrame with governance metrics

        Returns:
            Array of predictions: -1 for anomaly, 1 for normal
        """
        if self.fit(df):
            return self.predict(df)
        return np.array([])

    def _score_to_severity(self, score: float) -> str:
        """
        Convert anomaly score to severity label.

        Args:
            score: Anomaly score from decision_function

        Returns:
            Severity label: 'critical', 'high', 'medium', 'low'
        """
        if score <= self.SEVERITY_THRESHOLDS["critical"]:
            return "critical"
        elif score <= self.SEVERITY_THRESHOLDS["high"]:
            return "high"
        elif score <= self.SEVERITY_THRESHOLDS["medium"]:
            return "medium"
        return "low"

    def _generate_anomaly_description(
        self,
        metrics: Dict[str, Any],
        severity: str,
    ) -> str:
        """
        Generate a human-readable description of the anomaly.

        Args:
            metrics: Dictionary of metric values
            severity: Severity label

        Returns:
            Human-readable description
        """
        descriptions = []

        if "violation_count" in metrics:
            v_count = metrics["violation_count"]
            if v_count > 0:
                descriptions.append(f"Unusual violation count ({v_count})")

        if "user_count" in metrics:
            u_count = metrics["user_count"]
            if u_count > 0:
                descriptions.append(f"Unusual user activity ({u_count} users)")

        if "policy_changes" in metrics:
            p_changes = metrics["policy_changes"]
            if p_changes > 0:
                descriptions.append(f"Unusual policy changes ({p_changes})")

        if descriptions:
            return f"{severity.capitalize()} anomaly: " + "; ".join(descriptions)
        return f"{severity.capitalize()} anomaly detected in governance metrics"

    def detect_anomalies(
        self,
        df: pd.DataFrame,
        include_dates: bool = True,
    ) -> AnomalyDetectionResult:
        """
        Detect anomalies and return structured results.

        Args:
            df: DataFrame with governance metrics (should include 'date' column)
            include_dates: Whether to use date column for anomaly timestamps

        Returns:
            AnomalyDetectionResult with detected anomalies
        """
        now = datetime.now(timezone.utc)

        # Handle empty data
        if df.empty:
            logger.warning("Empty DataFrame, returning empty result")
            return AnomalyDetectionResult(
                analysis_timestamp=now,
                total_records_analyzed=0,
                anomalies_detected=0,
                contamination_rate=self.contamination,
                anomalies=[],
                model_trained=False,
            )

        # Train the model if not already fitted
        if not self._is_fitted:
            if not self.fit(df):
                return AnomalyDetectionResult(
                    analysis_timestamp=now,
                    total_records_analyzed=len(df),
                    anomalies_detected=0,
                    contamination_rate=self.contamination,
                    anomalies=[],
                    model_trained=False,
                )

        # Get predictions and scores
        predictions = self.predict(df)
        scores = self.decision_function(df)

        if len(predictions) == 0:
            return AnomalyDetectionResult(
                analysis_timestamp=now,
                total_records_analyzed=len(df),
                anomalies_detected=0,
                contamination_rate=self.contamination,
                anomalies=[],
                model_trained=self._is_fitted,
            )

        # Find anomalies (prediction == -1)
        anomaly_indices = np.where(predictions == -1)[0]
        detected_anomalies: List[DetectedAnomaly] = []

        for i, idx in enumerate(anomaly_indices):
            # Get timestamp from date column if available
            if include_dates and "date" in df.columns:
                ts = pd.to_datetime(df.iloc[idx]["date"])
                if pd.notna(ts):
                    timestamp = ts.to_pydatetime()
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                else:
                    timestamp = now
            else:
                timestamp = now

            # Get the anomaly score
            score = float(scores[idx])
            severity = self._score_to_severity(score)

            # Get affected metrics
            metrics = {}
            for feature in self.features:
                if feature in df.columns:
                    value = df.iloc[idx][feature]
                    if pd.notna(value):
                        metrics[feature] = (
                            int(value) if isinstance(value, (np.integer, int)) else float(value)
                        )

            # Generate description
            description = self._generate_anomaly_description(metrics, severity)

            anomaly = DetectedAnomaly(
                anomaly_id=f"anomaly-{timestamp.strftime('%Y%m%d')}-{i:03d}",
                timestamp=timestamp,
                severity_score=score,
                severity_label=severity,
                affected_metrics=metrics,
                description=description,
            )
            detected_anomalies.append(anomaly)

        # Sort by severity (most severe first)
        detected_anomalies.sort(key=lambda a: a.severity_score)

        logger.info(f"Detected {len(detected_anomalies)} anomalies in {len(df)} records")

        return AnomalyDetectionResult(
            analysis_timestamp=now,
            total_records_analyzed=len(df),
            anomalies_detected=len(detected_anomalies),
            contamination_rate=self.contamination,
            anomalies=detected_anomalies,
            model_trained=self._is_fitted,
        )

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current model state.

        Returns:
            Dictionary with model configuration and status
        """
        return {
            "is_fitted": self._is_fitted,
            "contamination": self.contamination,
            "n_estimators": self.n_estimators,
            "features": self.features,
            "last_training_time": (
                self._last_training_time.isoformat() if self._last_training_time else None
            ),
            "sklearn_available": IsolationForest is not None,
        }
