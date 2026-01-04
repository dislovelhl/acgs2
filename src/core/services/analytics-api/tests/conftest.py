"""
Pytest configuration and fixtures for analytics-api tests.

Constitutional Hash: cdd01ef066bc6cf2

Provides shared fixtures for testing analytics-api endpoints including:
- FastAPI TestClient setup
- Sample governance data
- Mock analytics-engine components
"""

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List

import pytest

# Ensure analytics-engine and analytics-api are importable
SERVICES_PATH = Path(__file__).parent.parent.parent.parent
ANALYTICS_ENGINE_PATH = SERVICES_PATH / "analytics-engine" / "src"
ANALYTICS_API_PATH = Path(__file__).parent.parent / "src"

for path in [str(ANALYTICS_ENGINE_PATH), str(ANALYTICS_API_PATH)]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Import FastAPI test utilities
try:
    from fastapi.testclient import TestClient

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    TestClient = None


@pytest.fixture(scope="session")
def api_client() -> Generator:
    """
    Create a FastAPI TestClient for the analytics-api application.

    Yields:
        TestClient instance for making test requests
    """
    if not FASTAPI_AVAILABLE:
        pytest.skip("FastAPI test client not available")

    from main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_governance_data() -> Dict[str, Any]:
    """
    Provide sample governance data for testing insights.

    Returns:
        Dictionary with governance metrics
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


@pytest.fixture
def sample_governance_metrics() -> List[Dict[str, Any]]:
    """
    Provide sample governance metrics for anomaly detection testing.

    Returns:
        List of dictionaries with governance metrics
    """
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


@pytest.fixture
def sample_historical_violations() -> List[Dict[str, Any]]:
    """
    Provide sample historical violation data for prediction testing.

    Returns:
        List of dictionaries with 'ds' and 'y' columns for Prophet
    """
    from datetime import timedelta

    base_date = datetime.now(timezone.utc) - timedelta(days=30)
    data = []

    for i in range(30):
        date = base_date + timedelta(days=i)
        # Simulate violation pattern with weekly seasonality
        base_violations = 5 + (i % 7) * 0.5
        noise = (i % 3) - 1  # Deterministic "noise"
        violations = max(0, base_violations + noise)

        data.append(
            {
                "ds": date.strftime("%Y-%m-%d"),
                "y": violations,
            }
        )

    return data


@pytest.fixture
def sample_query_questions() -> List[str]:
    """
    Provide sample natural language queries for testing.

    Returns:
        List of sample query strings
    """
    return [
        "Show violations this week",
        "Which policy is violated most?",
        "What is the compliance trend?",
        "How many users are affected?",
        "What are the top risk areas?",
    ]


@pytest.fixture
def expected_insight_fields() -> List[str]:
    """
    List of expected fields in insight response.

    Returns:
        List of field names
    """
    return [
        "summary",
        "business_impact",
        "recommended_action",
        "confidence",
        "generated_at",
    ]


@pytest.fixture
def expected_anomaly_fields() -> List[str]:
    """
    List of expected fields in anomaly response.

    Returns:
        List of field names
    """
    return [
        "analysis_timestamp",
        "total_records_analyzed",
        "anomalies_detected",
        "contamination_rate",
        "anomalies",
        "model_trained",
    ]


@pytest.fixture
def expected_prediction_fields() -> List[str]:
    """
    List of expected fields in prediction response.

    Returns:
        List of field names
    """
    return [
        "forecast_timestamp",
        "historical_days",
        "forecast_days",
        "model_trained",
        "predictions",
        "summary",
    ]


@pytest.fixture
def expected_query_fields() -> List[str]:
    """
    List of expected fields in query response.

    Returns:
        List of field names
    """
    return [
        "query",
        "answer",
        "data",
        "query_understood",
        "generated_at",
    ]
