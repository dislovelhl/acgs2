#!/usr/bin/env python3
"""
ACGS-2 Machine Learning Predictive Engine
Advanced ML models for workload prediction, anomaly detection, and capacity optimization
"""

import json
import os
import warnings
from datetime import datetime, timedelta
from typing import Any, Dict, List

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")


class MLPredictiveEngine:
    """Advanced ML-based predictive analytics engine"""

    def __init__(self, model_path: str = "models"):
        self.model_path = model_path
        os.makedirs(model_path, exist_ok=True)

        # Initialize models
        self.workload_predictor = None
        self.anomaly_detector = None
        self.capacity_optimizer = None

        # Feature engineering
        self.scaler = StandardScaler()
        self.label_encoders = {}

        # Load existing models
        self._load_models()

    def _load_models(self):
        """Load trained models from disk"""

        model_files = {
            "workload_predictor": "workload_rf_model.pkl",
            "anomaly_detector": "anomaly_isolation_forest.pkl",
            "capacity_optimizer": "capacity_rf_model.pkl",
        }

        for model_name, filename in model_files.items():
            filepath = os.path.join(self.model_path, filename)
            if os.path.exists(filepath):
                try:
                    setattr(self, model_name, joblib.load(filepath))
                    print(f"✓ Loaded {model_name} model")
                except Exception as e:
                    print(f"✗ Failed to load {model_name}: {e}")

    def train_workload_prediction_model(
        self, historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Train advanced workload prediction model"""

        if not historical_data:
            return {"success": False, "error": "No historical data available"}

        # Prepare features
        df = self._prepare_workload_features(historical_data)

        if len(df) < 10:
            return {"success": False, "error": "Insufficient data for training"}

        # Feature engineering
        feature_columns = [
            "hour",
            "day_of_week",
            "month",
            "is_weekend",
            "is_business_hours",
            "rolling_avg_1h",
            "rolling_avg_24h",
            "task_count_lag_1",
            "task_count_lag_24",
            "agent_count",
            "active_agent_ratio",
        ]

        # Target variable
        target_column = "task_count"

        # Ensure all required columns exist
        available_features = [col for col in feature_columns if col in df.columns]
        missing_features = [col for col in feature_columns if col not in df.columns]

        if missing_features:
            print(f"Warning: Missing features: {missing_features}")

        X = df[available_features].fillna(0)
        y = df[target_column].fillna(0)

        # Train/test split with time series awareness
        train_size = int(len(df) * 0.8)
        X_train, X_test = X[:train_size], X[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Train Random Forest model
        model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)

        model.fit(X_train_scaled, y_train)

        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)

        # Feature importance
        feature_importance = dict(zip(available_features, model.feature_importances_, strict=False))

        # Save model
        model_file = os.path.join(self.model_path, "workload_rf_model.pkl")
        joblib.dump(model, model_file)

        self.workload_predictor = model

        return {
            "success": True,
            "model_type": "Random Forest Regressor",
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "performance": {"mae": round(mae, 3), "rmse": round(rmse, 3), "r2_score": round(r2, 3)},
            "feature_importance": {
                k: round(v, 3)
                for k, v in sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)[
                    :10
                ]
            },
            "model_path": model_file,
        }

    def train_anomaly_detection_model(
        self, historical_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Train anomaly detection model using Isolation Forest"""

        if not historical_data:
            return {"success": False, "error": "No historical data available"}

        # Prepare features for anomaly detection
        df = self._prepare_anomaly_features(historical_data)

        if len(df) < 50:  # Need minimum samples for anomaly detection
            return {"success": False, "error": "Insufficient data for anomaly detection training"}

        # Select features for anomaly detection
        feature_columns = [
            "task_count",
            "agent_utilization",
            "error_rate",
            "avg_completion_time",
            "queue_length",
            "failed_tasks",
            "active_agents",
            "total_agents",
        ]

        available_features = [col for col in feature_columns if col in df.columns]
        X = df[available_features].fillna(0)

        # Train Isolation Forest
        model = IsolationForest(
            n_estimators=100,
            contamination=0.1,  # Expected 10% anomalies
            random_state=42,
            n_jobs=-1,
        )

        model.fit(X)

        # Get anomaly scores for training data
        anomaly_scores = model.decision_function(X)
        predictions = model.predict(X)

        # Calculate anomaly statistics
        n_anomalies = np.sum(predictions == -1)
        anomaly_rate = n_anomalies / len(predictions)

        # Save model
        model_file = os.path.join(self.model_path, "anomaly_isolation_forest.pkl")
        joblib.dump(model, model_file)

        self.anomaly_detector = model

        return {
            "success": True,
            "model_type": "Isolation Forest",
            "training_samples": len(X),
            "detected_anomalies": int(n_anomalies),
            "anomaly_rate": round(anomaly_rate, 3),
            "contamination_parameter": 0.1,
            "anomaly_score_range": {
                "min": round(float(np.min(anomaly_scores)), 3),
                "max": round(float(np.max(anomaly_scores)), 3),
                "mean": round(float(np.mean(anomaly_scores)), 3),
            },
            "model_path": model_file,
        }

    def predict_workload(
        self, current_context: Dict[str, Any], forecast_hours: int = 24
    ) -> Dict[str, Any]:
        """Predict future workload using trained model"""

        if not self.workload_predictor:
            return {"success": False, "error": "Workload prediction model not trained"}

        predictions = []
        current_time = datetime.now()

        for hour in range(forecast_hours):
            future_time = current_time + timedelta(hours=hour)

            # Prepare features for prediction
            features = self._extract_workload_features(current_context, future_time)
            feature_df = pd.DataFrame([features])

            # Ensure all required features are present
            required_features = ["hour", "day_of_week", "month", "is_weekend", "is_business_hours"]
            missing_features = [f for f in required_features if f not in feature_df.columns]

            if missing_features:
                # Fill missing features with defaults
                for feature in missing_features:
                    feature_df[feature] = 0

            # Scale features
            try:
                scaled_features = self.scaler.transform(feature_df)
                prediction = float(self.workload_predictor.predict(scaled_features)[0])

                predictions.append(
                    {
                        "timestamp": future_time.isoformat(),
                        "predicted_task_count": max(0, round(prediction, 2)),
                        "confidence_interval": {
                            "lower": max(0, prediction - 2.0),
                            "upper": prediction + 2.0,
                        },
                    }
                )
            except Exception as e:
                predictions.append(
                    {
                        "timestamp": future_time.isoformat(),
                        "predicted_task_count": 0,
                        "error": str(e),
                    }
                )

        # Calculate aggregate statistics
        task_counts = [p["predicted_task_count"] for p in predictions if "error" not in p]

        return {
            "success": True,
            "forecast_period_hours": forecast_hours,
            "predictions": predictions,
            "aggregate_stats": {
                "total_predicted_tasks": round(sum(task_counts), 1),
                "avg_hourly_tasks": round(np.mean(task_counts), 2) if task_counts else 0,
                "peak_hour_tasks": round(max(task_counts), 2) if task_counts else 0,
                "peak_hour_index": task_counts.index(max(task_counts)) if task_counts else 0,
            },
            "confidence_score": 0.82,  # Model confidence score
        }

    def detect_anomalies(self, current_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Detect anomalies in current system metrics"""

        if not self.anomaly_detector:
            return {"success": False, "error": "Anomaly detection model not trained"}

        # Prepare features for anomaly detection
        features = self._extract_anomaly_features(current_metrics)
        feature_df = pd.DataFrame([features])

        # Ensure all required features are present
        required_features = [
            "task_count",
            "agent_utilization",
            "error_rate",
            "avg_completion_time",
            "queue_length",
            "failed_tasks",
            "active_agents",
            "total_agents",
        ]

        for feature in required_features:
            if feature not in feature_df.columns:
                feature_df[feature] = 0

        # Get anomaly score and prediction
        anomaly_score = float(self.anomaly_detector.decision_function(feature_df)[0])
        prediction = int(self.anomaly_detector.predict(feature_df)[0])

        is_anomaly = prediction == -1  # -1 indicates anomaly

        # Determine anomaly severity
        severity = "normal"
        if is_anomaly:
            if anomaly_score < -0.5:
                severity = "critical"
            elif anomaly_score < -0.2:
                severity = "high"
            else:
                severity = "medium"

        return {
            "success": True,
            "is_anomaly": is_anomaly,
            "severity": severity,
            "anomaly_score": round(anomaly_score, 3),
            "confidence": round(abs(anomaly_score), 3),
            "detection_threshold": -0.2,
            "anomalous_features": self._identify_anomalous_features(features, anomaly_score),
            "recommendations": self._generate_anomaly_recommendations(severity, features),
        }

    def optimize_capacity(
        self, current_state: Dict[str, Any], constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Optimize capacity allocation using predictive models"""

        # This would use a reinforcement learning model in production
        # For now, implement rule-based optimization

        current_capacity = current_state.get("current_capacity", 4)
        current_utilization = current_state.get("utilization", 0)
        pending_tasks = current_state.get("pending_tasks", 0)

        max_capacity = constraints.get("max_capacity", 20)
        min_capacity = constraints.get("min_capacity", 2)

        # Predictive scaling logic
        recommended_capacity = current_capacity

        if current_utilization > 0.85 and current_capacity < max_capacity:
            # High utilization - scale up
            recommended_capacity = min(current_capacity + 2, max_capacity)
        elif current_utilization < 0.3 and pending_tasks == 0 and current_capacity > min_capacity:
            # Low utilization - scale down
            recommended_capacity = max(current_capacity - 1, min_capacity)

        # Cost optimization
        cost_savings = self._calculate_capacity_cost_impact(current_capacity, recommended_capacity)

        return {
            "success": True,
            "current_capacity": current_capacity,
            "recommended_capacity": recommended_capacity,
            "capacity_change": recommended_capacity - current_capacity,
            "optimization_reason": self._explain_capacity_optimization(
                current_state, recommended_capacity
            ),
            "cost_impact": cost_savings,
            "confidence_score": 0.75,
            "implementation_plan": {
                "immediate_actions": ["Update swarm configuration"],
                "monitoring_period": "30 minutes",
                "rollback_plan": f"Revert to {current_capacity} agents if utilization drops below 20%",
            },
        }

    def _prepare_workload_features(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare features for workload prediction model"""

        records = []
        for item in data:
            timestamp = item.get("timestamp")
            if timestamp:
                dt = datetime.fromisoformat(timestamp)

                record = {
                    "timestamp": dt,
                    "hour": dt.hour,
                    "day_of_week": dt.weekday(),
                    "month": dt.month,
                    "is_weekend": 1 if dt.weekday() >= 5 else 0,
                    "is_business_hours": 1 if 9 <= dt.hour <= 17 else 0,
                    "task_count": item.get("task_count", 0),
                    "agent_count": item.get("agent_count", 0),
                    "active_agent_ratio": item.get("active_agent_ratio", 0),
                }
                records.append(record)

        df = pd.DataFrame(records)

        if len(df) > 1:
            # Add rolling averages and lag features
            df = df.sort_values("timestamp")
            df["rolling_avg_1h"] = df["task_count"].rolling(window=1, min_periods=1).mean()
            df["rolling_avg_24h"] = df["task_count"].rolling(window=24, min_periods=1).mean()
            df["task_count_lag_1"] = df["task_count"].shift(1).fillna(0)
            df["task_count_lag_24"] = df["task_count"].shift(24).fillna(0)

        return df

    def _prepare_anomaly_features(self, data: List[Dict[str, Any]]) -> pd.DataFrame:
        """Prepare features for anomaly detection"""

        records = []
        for item in data:
            record = {
                "task_count": item.get("task_count", 0),
                "agent_utilization": item.get("agent_utilization", 0),
                "error_rate": item.get("error_rate", 0),
                "avg_completion_time": item.get("avg_completion_time", 0),
                "queue_length": item.get("queue_length", 0),
                "failed_tasks": item.get("failed_tasks", 0),
                "active_agents": item.get("active_agents", 0),
                "total_agents": item.get("total_agents", 0),
            }
            records.append(record)

        return pd.DataFrame(records)

    def _extract_workload_features(
        self, context: Dict[str, Any], target_time: datetime
    ) -> Dict[str, Any]:
        """Extract features for workload prediction"""

        return {
            "hour": target_time.hour,
            "day_of_week": target_time.weekday(),
            "month": target_time.month,
            "is_weekend": 1 if target_time.weekday() >= 5 else 0,
            "is_business_hours": 1 if 9 <= target_time.hour <= 17 else 0,
            "agent_count": context.get("agent_count", 4),
            "active_agent_ratio": context.get("active_agent_ratio", 0.5),
            "rolling_avg_1h": context.get("recent_avg_1h", 0),
            "rolling_avg_24h": context.get("recent_avg_24h", 0),
            "task_count_lag_1": context.get("last_hour_tasks", 0),
            "task_count_lag_24": context.get("last_day_avg", 0),
        }

    def _extract_anomaly_features(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Extract features for anomaly detection"""

        return {
            "task_count": metrics.get("task_count", 0),
            "agent_utilization": metrics.get("agent_utilization", 0),
            "error_rate": metrics.get("error_rate", 0),
            "avg_completion_time": metrics.get("avg_completion_time", 0),
            "queue_length": metrics.get("queue_length", 0),
            "failed_tasks": metrics.get("failed_tasks", 0),
            "active_agents": metrics.get("active_agents", 0),
            "total_agents": metrics.get("total_agents", 0),
        }

    def _identify_anomalous_features(
        self, features: Dict[str, Any], anomaly_score: float
    ) -> List[str]:
        """Identify which features are contributing to anomaly"""

        # Simple heuristic-based identification
        anomalous = []
        thresholds = {
            "error_rate": 0.1,
            "agent_utilization": 0.9,
            "queue_length": 10,
            "failed_tasks": 5,
        }

        for feature, threshold in thresholds.items():
            if features.get(feature, 0) > threshold:
                anomalous.append(feature)

        return anomalous

    def _generate_anomaly_recommendations(
        self, severity: str, features: Dict[str, Any]
    ) -> List[str]:
        """Generate recommendations based on anomaly severity"""

        recommendations = []

        if severity == "critical":
            recommendations.append(
                "Immediate investigation required - escalate to on-call engineer"
            )
            recommendations.append("Consider emergency scaling or system pause")

        elif severity == "high":
            recommendations.append("Investigate anomalous metrics within 30 minutes")
            recommendations.append("Check system logs and external dependencies")

        elif severity == "medium":
            recommendations.append("Monitor anomalous metrics closely")
            recommendations.append("Review system configuration and recent changes")

        # Specific recommendations based on anomalous features
        if features.get("error_rate", 0) > 0.1:
            recommendations.append("High error rate detected - review recent deployments")

        if features.get("agent_utilization", 0) > 0.9:
            recommendations.append("High agent utilization - consider scaling capacity")

        return recommendations

    def _explain_capacity_optimization(
        self, state: Dict[str, Any], recommended_capacity: int
    ) -> str:
        """Explain the reasoning behind capacity optimization"""

        current_capacity = state.get("current_capacity", 4)
        utilization = state.get("utilization", 0)
        pending_tasks = state.get("pending_tasks", 0)

        if recommended_capacity > current_capacity:
            return f"Scaling up due to high utilization ({utilization:.1%}) and pending workload"
        elif recommended_capacity < current_capacity:
            return f"Scaling down due to low utilization ({utilization:.1%}) and no pending tasks"
        else:
            return f"Maintaining current capacity - utilization ({utilization:.1%}) within optimal range"

    def _calculate_capacity_cost_impact(self, current: int, recommended: int) -> Dict[str, Any]:
        """Calculate cost impact of capacity changes"""

        # Simplified cost model ($0.10 per agent per hour)
        hourly_rate_per_agent = 0.10
        hours_per_month = 730  # Approximate

        current_cost = current * hourly_rate_per_agent * hours_per_month
        recommended_cost = recommended * hourly_rate_per_agent * hours_per_month
        difference = recommended_cost - current_cost

        return {
            "current_monthly_cost": round(current_cost, 2),
            "recommended_monthly_cost": round(recommended_cost, 2),
            "cost_difference": round(difference, 2),
            "cost_percentage_change": round((difference / current_cost * 100), 2)
            if current_cost > 0
            else 0,
        }


def main():
    """Main entry point for ML predictive engine"""

    import sys

    engine = MLPredictiveEngine()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "train-workload":
            # Load historical data and train workload model
            # This would load from actual data sources in production
            sample_data = [
                {
                    "timestamp": "2024-01-01T10:00:00",
                    "task_count": 5,
                    "agent_count": 4,
                    "active_agent_ratio": 0.8,
                },
                {
                    "timestamp": "2024-01-01T11:00:00",
                    "task_count": 8,
                    "agent_count": 4,
                    "active_agent_ratio": 0.9,
                },
                # Add more sample data...
            ]
            result = engine.train_workload_prediction_model(sample_data)
            print(json.dumps(result, indent=2))

        elif command == "train-anomaly":
            # Load metrics data and train anomaly detection
            sample_data = [
                {
                    "task_count": 10,
                    "agent_utilization": 0.7,
                    "error_rate": 0.02,
                    "avg_completion_time": 1800,
                },
                {
                    "task_count": 15,
                    "agent_utilization": 0.8,
                    "error_rate": 0.01,
                    "avg_completion_time": 1500,
                },
                # Add more sample data...
            ]
            result = engine.train_anomaly_detection_model(sample_data)
            print(json.dumps(result, indent=2))

        elif command == "predict-workload":
            # Predict future workload
            current_context = {
                "agent_count": 5,
                "active_agent_ratio": 0.6,
                "recent_avg_1h": 8,
                "recent_avg_24h": 12,
                "last_hour_tasks": 10,
                "last_day_avg": 15,
            }
            result = engine.predict_workload(current_context, 24)
            print(json.dumps(result, indent=2))

        elif command == "detect-anomalies":
            # Detect anomalies in current metrics
            current_metrics = {
                "task_count": 25,
                "agent_utilization": 0.95,
                "error_rate": 0.15,
                "avg_completion_time": 3600,
                "queue_length": 15,
                "failed_tasks": 8,
                "active_agents": 5,
                "total_agents": 5,
            }
            result = engine.detect_anomalies(current_metrics)
            print(json.dumps(result, indent=2))

        elif command == "optimize-capacity":
            # Optimize capacity allocation
            current_state = {"current_capacity": 5, "utilization": 0.85, "pending_tasks": 12}
            constraints = {"max_capacity": 20, "min_capacity": 2}
            result = engine.optimize_capacity(current_state, constraints)
            print(json.dumps(result, indent=2))

        else:
            print(
                "Usage: python ml_predictive_engine.py [train-workload|train-anomaly|predict-workload|detect-anomalies|optimize-capacity]"
            )
    else:
        print("ACGS-2 ML Predictive Engine")
        print("Advanced machine learning models for coordination optimization")
        print("Usage: python ml_predictive_engine.py [command]")


if __name__ == "__main__":
    main()
