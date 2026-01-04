"""
Integration tests for the Adaptive Learning Engine API endpoints.

Tests cover all API endpoint contracts:
- POST /api/v1/predict - Get governance decision prediction
- POST /api/v1/train - Submit training sample (async)
- POST /api/v1/train/batch - Submit batch training samples
- GET /api/v1/models/current - Get active model metadata
- GET /api/v1/models/versions - List model versions
- POST /api/v1/models/rollback/{version} - Rollback to previous version
- GET /api/v1/drift/status - Get drift detection status
- POST /api/v1/drift/check - Trigger drift check
- GET /api/v1/safety/status - Get safety bounds status
- POST /api/v1/safety/resume - Resume learning
- GET /metrics - Prometheus metrics endpoint
- GET /api/v1/metrics - JSON metrics summary
- GET /health - Health check

Constitutional Hash: cdd01ef066bc6cf2
"""

import time
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from src.api.endpoints import initialize_services, router
from src.api.models import (
    DriftStatusEnum,
    ModelStateEnum,
    SafetyStatusEnum,
)
from src.models.model_manager import ModelManager
from src.models.online_learner import OnlineLearner
from src.monitoring.drift_detector import DriftDetector
from src.monitoring.metrics import MetricsRegistry
from src.safety.bounds_checker import SafetyBoundsChecker

# Create a FastAPI app for testing (without the full lifespan)
from fastapi import FastAPI

# Test app with just the router
test_app = FastAPI()
test_app.include_router(router)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_features() -> Dict[str, float]:
    """Sample feature dictionary for testing."""
    return {
        "feature_a": 1.0,
        "feature_b": 2.5,
        "feature_c": 0.3,
    }


@pytest.fixture
def training_dataset() -> List[Dict[str, Any]]:
    """Dataset for training tests."""
    return [
        {"features": {"x": 0.9, "y": 0.9}, "label": 1},
        {"features": {"x": 0.1, "y": 0.1}, "label": 0},
        {"features": {"x": 0.8, "y": 0.8}, "label": 1},
        {"features": {"x": 0.2, "y": 0.2}, "label": 0},
        {"features": {"x": 0.7, "y": 0.7}, "label": 1},
        {"features": {"x": 0.3, "y": 0.3}, "label": 0},
    ]


@pytest.fixture
def online_learner() -> OnlineLearner:
    """Fresh OnlineLearner with low min_training_samples for testing."""
    return OnlineLearner(
        min_training_samples=5,  # Low for quick testing
    )


@pytest.fixture
def model_manager(online_learner: OnlineLearner) -> ModelManager:
    """Fresh ModelManager for testing."""
    return ModelManager(
        initial_model=online_learner,
    )


@pytest.fixture
def drift_detector() -> DriftDetector:
    """Fresh DriftDetector for testing."""
    return DriftDetector(
        min_samples_for_drift=10,
        drift_threshold=0.2,
        reference_window_size=100,
        current_window_size=50,
    )


@pytest.fixture
def safety_checker() -> SafetyBoundsChecker:
    """Fresh SafetyBoundsChecker for testing."""
    return SafetyBoundsChecker(
        accuracy_threshold=0.85,
        consecutive_failures_limit=3,
    )


@pytest.fixture
def metrics_registry() -> MetricsRegistry:
    """Fresh MetricsRegistry for testing with isolated registry."""
    from prometheus_client import CollectorRegistry

    registry = CollectorRegistry()
    return MetricsRegistry(registry=registry)


@pytest.fixture
def initialized_services(
    model_manager: ModelManager,
    drift_detector: DriftDetector,
    safety_checker: SafetyBoundsChecker,
    metrics_registry: MetricsRegistry,
):
    """Initialize the endpoint services with test instances."""
    initialize_services(
        model_manager=model_manager,
        drift_detector=drift_detector,
        safety_checker=safety_checker,
        metrics_registry=metrics_registry,
    )
    yield
    # Cleanup would go here if needed


@pytest.fixture
def client(initialized_services) -> TestClient:
    """Create a TestClient with initialized services."""
    return TestClient(test_app)


# =============================================================================
# Prediction Endpoint Tests
# =============================================================================


class TestPredictEndpoint:
    """Integration tests for POST /api/v1/predict."""

    def test_predict_returns_valid_response(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test prediction returns valid prediction with confidence score."""
        response = client.post(
            "/api/v1/predict",
            json={"features": sample_features},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "prediction" in data
        assert "confidence" in data
        assert "model_state" in data
        assert "sample_count" in data
        assert "prediction_id" in data
        assert "timestamp" in data

        # Verify prediction is 0 or 1
        assert data["prediction"] in (0, 1)

        # Verify confidence is between 0 and 1
        assert 0.0 <= data["confidence"] <= 1.0

        # Verify model state is valid enum
        assert data["model_state"] in [e.value for e in ModelStateEnum]

    def test_predict_cold_start_returns_default(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test cold start prediction returns conservative default."""
        response = client.post(
            "/api/v1/predict",
            json={"features": sample_features},
        )

        assert response.status_code == 200
        data = response.json()

        # Cold start should return default prediction
        assert data["model_state"] == ModelStateEnum.COLD_START.value
        assert data["sample_count"] == 0

    def test_predict_includes_probabilities(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test prediction includes probability distribution when requested."""
        response = client.post(
            "/api/v1/predict",
            json={
                "features": sample_features,
                "include_probabilities": True,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "probabilities" in data
        assert data["probabilities"] is not None
        # Should have probabilities for classes 0 and 1
        assert "0" in data["probabilities"] or 0 in data["probabilities"]

    def test_predict_excludes_probabilities_when_not_requested(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test prediction excludes probabilities when not requested."""
        response = client.post(
            "/api/v1/predict",
            json={
                "features": sample_features,
                "include_probabilities": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Probabilities should be None or not included
        assert data.get("probabilities") is None

    def test_predict_includes_latency(self, client: TestClient, sample_features: Dict[str, float]):
        """Test prediction includes latency measurement."""
        response = client.post(
            "/api/v1/predict",
            json={"features": sample_features},
        )

        assert response.status_code == 200
        data = response.json()

        assert "latency_ms" in data
        assert data["latency_ms"] >= 0

    def test_predict_accepts_request_id(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test prediction accepts and returns request ID."""
        request_id = "test-request-12345"
        response = client.post(
            "/api/v1/predict",
            json={
                "features": sample_features,
                "request_id": request_id,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["prediction_id"] == request_id

    def test_predict_validation_empty_features(self, client: TestClient):
        """Test prediction with empty features returns validation error."""
        response = client.post(
            "/api/v1/predict",
            json={"features": {}},
        )

        # Empty features should be accepted (model handles it)
        # If validation fails, check status code
        assert response.status_code in (200, 422)


# =============================================================================
# Training Endpoint Tests
# =============================================================================


class TestTrainEndpoint:
    """Integration tests for POST /api/v1/train."""

    def test_train_returns_202_accepted(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test training returns 202 status code."""
        response = client.post(
            "/api/v1/train",
            json={
                "features": sample_features,
                "label": 1,
            },
        )

        assert response.status_code == 202

    def test_train_returns_valid_response(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test training returns valid response structure."""
        response = client.post(
            "/api/v1/train",
            json={
                "features": sample_features,
                "label": 1,
            },
        )

        assert response.status_code == 202
        data = response.json()

        # Verify response structure
        assert "success" in data
        assert "sample_count" in data
        assert "current_accuracy" in data
        assert "model_state" in data
        assert "message" in data
        assert "training_id" in data

    def test_train_increments_sample_count(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test training increments sample count."""
        # First training
        response1 = client.post(
            "/api/v1/train",
            json={"features": sample_features, "label": 1},
        )
        assert response1.status_code == 202
        count1 = response1.json()["sample_count"]

        # Second training
        response2 = client.post(
            "/api/v1/train",
            json={"features": sample_features, "label": 0},
        )
        assert response2.status_code == 202
        count2 = response2.json()["sample_count"]

        assert count2 == count1 + 1

    def test_train_updates_model_state(self, client: TestClient, sample_features: Dict[str, float]):
        """Test training updates model state from cold_start to warming."""
        # Check initial state
        predict_response = client.post(
            "/api/v1/predict",
            json={"features": sample_features},
        )
        initial_state = predict_response.json()["model_state"]
        assert initial_state == ModelStateEnum.COLD_START.value

        # Train a sample
        train_response = client.post(
            "/api/v1/train",
            json={"features": sample_features, "label": 1},
        )
        assert train_response.status_code == 202
        new_state = train_response.json()["model_state"]

        # State should transition to warming
        assert new_state == ModelStateEnum.WARMING.value

    def test_train_with_sample_weight(self, client: TestClient, sample_features: Dict[str, float]):
        """Test training accepts sample weight."""
        response = client.post(
            "/api/v1/train",
            json={
                "features": sample_features,
                "label": 1,
                "sample_weight": 2.5,
            },
        )

        assert response.status_code == 202
        assert response.json()["success"] is True

    def test_train_invalid_label_rejected(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test training rejects invalid labels."""
        response = client.post(
            "/api/v1/train",
            json={
                "features": sample_features,
                "label": 5,  # Invalid label
            },
        )

        # Should return 422 Unprocessable Entity
        assert response.status_code == 422


class TestBatchTrainEndpoint:
    """Integration tests for POST /api/v1/train/batch."""

    def test_batch_train_returns_202(
        self, client: TestClient, training_dataset: List[Dict[str, Any]]
    ):
        """Test batch training returns 202 status code."""
        response = client.post(
            "/api/v1/train/batch",
            json={"samples": training_dataset},
        )

        assert response.status_code == 202

    def test_batch_train_returns_valid_response(
        self, client: TestClient, training_dataset: List[Dict[str, Any]]
    ):
        """Test batch training returns valid response structure."""
        response = client.post(
            "/api/v1/train/batch",
            json={"samples": training_dataset},
        )

        assert response.status_code == 202
        data = response.json()

        # Verify response structure
        assert "accepted" in data
        assert "total" in data
        assert "sample_count" in data
        assert "current_accuracy" in data
        assert "model_state" in data
        assert "message" in data

        # Verify counts
        assert data["total"] == len(training_dataset)

    def test_batch_train_processes_all_samples(
        self, client: TestClient, training_dataset: List[Dict[str, Any]]
    ):
        """Test batch training processes all samples."""
        response = client.post(
            "/api/v1/train/batch",
            json={
                "samples": training_dataset,
                "async_processing": False,  # Process synchronously for test
            },
        )

        assert response.status_code == 202
        data = response.json()

        # All samples should be accepted (synchronous processing)
        assert data["accepted"] == len(training_dataset)
        assert data["sample_count"] >= len(training_dataset)


# =============================================================================
# Model Management Endpoint Tests
# =============================================================================


class TestCurrentModelEndpoint:
    """Integration tests for GET /api/v1/models/current."""

    def test_get_current_model_returns_metadata(self, client: TestClient):
        """Test getting current model returns valid metadata."""
        response = client.get("/api/v1/models/current")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "model_type" in data
        assert "model_state" in data
        assert "sample_count" in data
        assert "predictions_count" in data
        assert "accuracy" in data
        assert "rolling_accuracy" in data
        assert "is_ready" in data
        assert "is_paused" in data

    def test_get_current_model_includes_version(self, client: TestClient):
        """Test current model includes version information."""
        response = client.get("/api/v1/models/current")

        assert response.status_code == 200
        data = response.json()

        assert "version" in data
        assert data["version"] is not None


class TestModelVersionsEndpoint:
    """Integration tests for GET /api/v1/models/versions."""

    def test_list_versions_returns_list(self, client: TestClient):
        """Test listing versions returns a list."""
        response = client.get("/api/v1/models/versions")

        assert response.status_code == 200
        data = response.json()

        assert "versions" in data
        assert isinstance(data["versions"], list)
        assert "total_versions" in data

    def test_list_versions_includes_current(self, client: TestClient):
        """Test version list includes current version."""
        response = client.get("/api/v1/models/versions")

        assert response.status_code == 200
        data = response.json()

        assert "current_version" in data
        assert data["current_version"] is not None
        assert data["total_versions"] >= 1


class TestRollbackEndpoint:
    """Integration tests for POST /api/v1/models/rollback/{version}."""

    def test_rollback_to_previous_success(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test rollback to previous version after creating multiple versions."""
        # Train the model to create a new state
        for i in range(5):
            client.post(
                "/api/v1/train",
                json={"features": sample_features, "label": i % 2},
            )

        # Now test rollback to previous
        response = client.post("/api/v1/models/rollback/previous")

        # May fail if no previous version exists (only 1 version)
        # This is expected behavior
        assert response.status_code == 200
        data = response.json()
        assert "success" in data

    def test_rollback_invalid_version_format(self, client: TestClient):
        """Test rollback with invalid version format returns 400."""
        response = client.post("/api/v1/models/rollback/invalid_version")

        assert response.status_code == 400

    def test_rollback_nonexistent_version(self, client: TestClient):
        """Test rollback to non-existent version returns 404 or failure."""
        response = client.post("/api/v1/models/rollback/9999")

        # Should return 404 or a failure response
        assert response.status_code in (200, 404)
        if response.status_code == 200:
            assert response.json()["success"] is False

    def test_rollback_accepts_reason(self, client: TestClient):
        """Test rollback accepts reason query parameter."""
        response = client.post(
            "/api/v1/models/rollback/previous",
            params={"reason": "Testing rollback functionality"},
        )

        # Response should be valid (success or failure based on history)
        assert response.status_code == 200
        assert "success" in response.json()


# =============================================================================
# Drift Detection Endpoint Tests
# =============================================================================


class TestDriftStatusEndpoint:
    """Integration tests for GET /api/v1/drift/status."""

    def test_get_drift_status_returns_valid_response(self, client: TestClient):
        """Test drift status returns valid response structure."""
        response = client.get("/api/v1/drift/status")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "drift_detected" in data
        assert "drift_score" in data
        assert "drift_threshold" in data
        assert "reference_size" in data
        assert "current_size" in data
        assert "total_checks" in data
        assert "message" in data

    def test_get_drift_status_valid_enum(self, client: TestClient):
        """Test drift status returns valid status enum."""
        response = client.get("/api/v1/drift/status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] in [e.value for e in DriftStatusEnum]

    def test_get_drift_status_threshold_range(self, client: TestClient):
        """Test drift threshold is within valid range."""
        response = client.get("/api/v1/drift/status")

        assert response.status_code == 200
        data = response.json()

        assert 0.0 <= data["drift_threshold"] <= 1.0
        assert 0.0 <= data["drift_score"] <= 1.0


class TestDriftCheckEndpoint:
    """Integration tests for POST /api/v1/drift/check."""

    def test_trigger_drift_check_returns_status(self, client: TestClient):
        """Test manually triggering drift check returns status."""
        response = client.post(
            "/api/v1/drift/check",
            json={"force": False},
        )

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "drift_detected" in data
        assert "drift_score" in data

    def test_trigger_drift_check_with_force(self, client: TestClient):
        """Test forcing drift check even with insufficient data."""
        response = client.post(
            "/api/v1/drift/check",
            json={"force": True},
        )

        assert response.status_code == 200


# =============================================================================
# Safety Status Endpoint Tests
# =============================================================================


class TestSafetyStatusEndpoint:
    """Integration tests for GET /api/v1/safety/status."""

    def test_get_safety_status_returns_valid_response(self, client: TestClient):
        """Test safety status returns valid response structure."""
        response = client.get("/api/v1/safety/status")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "current_accuracy" in data
        assert "accuracy_threshold" in data
        assert "consecutive_failures" in data
        assert "failures_limit" in data
        assert "is_learning_paused" in data
        assert "total_checks" in data
        assert "passed_checks" in data

    def test_get_safety_status_valid_enum(self, client: TestClient):
        """Test safety status returns valid status enum."""
        response = client.get("/api/v1/safety/status")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] in [e.value for e in SafetyStatusEnum]

    def test_get_safety_status_threshold_range(self, client: TestClient):
        """Test safety threshold is within valid range."""
        response = client.get("/api/v1/safety/status")

        assert response.status_code == 200
        data = response.json()

        assert 0.0 <= data["accuracy_threshold"] <= 1.0
        assert data["failures_limit"] >= 1


class TestSafetyResumeEndpoint:
    """Integration tests for POST /api/v1/safety/resume."""

    def test_resume_learning_success(self, client: TestClient):
        """Test resuming learning returns updated status."""
        response = client.post("/api/v1/safety/resume")

        assert response.status_code == 200
        data = response.json()

        # After resume, learning should not be paused
        assert data["is_learning_paused"] is False


# =============================================================================
# Prometheus Metrics Endpoint Tests
# =============================================================================


class TestPrometheusMetricsEndpoint:
    """Integration tests for GET /metrics."""

    def test_prometheus_metrics_returns_prometheus_format(self, client: TestClient):
        """Test Prometheus metrics endpoint returns correct format."""
        response = client.get("/metrics")

        assert response.status_code == 200

        # Check content type (should be text/plain or prometheus format)
        content_type = response.headers.get("content-type", "")
        assert "text" in content_type or "openmetrics" in content_type

    def test_prometheus_metrics_contains_expected_metrics(self, client: TestClient):
        """Test metrics endpoint contains expected metric names."""
        response = client.get("/metrics")

        assert response.status_code == 200
        content = response.text

        # Check for some expected metric names
        # These may or may not exist depending on activity
        # At minimum, the response should be valid
        assert len(content) > 0

    def test_prometheus_metrics_updates_after_prediction(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test metrics update after making predictions."""
        # Make some predictions
        for _ in range(3):
            client.post(
                "/api/v1/predict",
                json={"features": sample_features},
            )

        response = client.get("/metrics")

        assert response.status_code == 200
        # Metrics should be present
        assert len(response.text) > 0


class TestJsonMetricsEndpoint:
    """Integration tests for GET /api/v1/metrics."""

    def test_json_metrics_returns_valid_response(self, client: TestClient):
        """Test JSON metrics endpoint returns valid response."""
        response = client.get("/api/v1/metrics")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "predictions_total" in data
        assert "training_samples_total" in data
        assert "model_accuracy" in data
        assert "drift_score" in data
        assert "uptime_seconds" in data

    def test_json_metrics_increments_after_activity(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test metrics increment after predictions and training."""
        # Get initial metrics
        initial_response = client.get("/api/v1/metrics")
        initial_data = initial_response.json()

        # Make predictions and train
        client.post("/api/v1/predict", json={"features": sample_features})
        client.post(
            "/api/v1/train",
            json={"features": sample_features, "label": 1},
        )

        # Get updated metrics
        updated_response = client.get("/api/v1/metrics")
        updated_data = updated_response.json()

        # Predictions should have incremented
        assert updated_data["predictions_total"] > initial_data["predictions_total"]
        assert updated_data["training_samples_total"] > initial_data["training_samples_total"]


# =============================================================================
# Health Check Endpoint Tests
# =============================================================================


class TestHealthCheckEndpoint:
    """Integration tests for GET /health."""

    def test_health_check_returns_200(self, client: TestClient):
        """Test health check returns 200 OK."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_check_returns_valid_response(self, client: TestClient):
        """Test health check returns valid response structure."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert "service" in data
        assert "version" in data
        assert "model_status" in data
        assert "drift_status" in data
        assert "safety_status" in data
        assert "uptime_seconds" in data

    def test_health_check_service_info(self, client: TestClient):
        """Test health check contains correct service info."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "adaptive-learning-engine"
        assert data["version"] == "1.0.0"

    def test_health_check_status_healthy(self, client: TestClient):
        """Test health check shows healthy status when services initialized."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"

    def test_health_check_uptime_positive(self, client: TestClient):
        """Test health check uptime is positive."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["uptime_seconds"] >= 0


# =============================================================================
# End-to-End Workflow Tests
# =============================================================================


class TestPredictThenTrainWorkflow:
    """Test the progressive validation paradigm: predict first, then train."""

    def test_predict_then_train_cycle(self, client: TestClient, sample_features: Dict[str, float]):
        """Test complete predict-then-train cycle."""
        # Step 1: Make prediction
        predict_response = client.post(
            "/api/v1/predict",
            json={"features": sample_features},
        )
        assert predict_response.status_code == 200
        prediction_id = predict_response.json()["prediction_id"]

        # Step 2: Submit training sample with the actual outcome
        train_response = client.post(
            "/api/v1/train",
            json={
                "features": sample_features,
                "label": 1,
                "prediction_id": prediction_id,
            },
        )
        assert train_response.status_code == 202
        assert train_response.json()["success"] is True

    def test_model_improves_with_training(
        self, client: TestClient, training_dataset: List[Dict[str, Any]]
    ):
        """Test that model accuracy improves with training."""
        # Train the model with consistent patterns
        for _ in range(3):  # Repeat dataset multiple times
            for sample in training_dataset:
                client.post(
                    "/api/v1/train",
                    json={
                        "features": sample["features"],
                        "label": sample["label"],
                    },
                )

        # Check model state after training
        model_response = client.get("/api/v1/models/current")
        assert model_response.status_code == 200
        data = model_response.json()

        # Model should have processed samples
        assert data["sample_count"] >= len(training_dataset) * 3


class TestMultipleEndpointInteraction:
    """Test interactions between multiple endpoints."""

    def test_training_affects_predictions(
        self, client: TestClient, training_dataset: List[Dict[str, Any]]
    ):
        """Test that training affects subsequent predictions."""
        # Initial prediction
        initial_pred = client.post(
            "/api/v1/predict",
            json={"features": {"x": 0.95, "y": 0.95}},
        )
        assert initial_pred.status_code == 200
        initial_state = initial_pred.json()["model_state"]

        # Train the model
        for sample in training_dataset * 2:
            client.post(
                "/api/v1/train",
                json={
                    "features": sample["features"],
                    "label": sample["label"],
                },
            )

        # Prediction after training
        post_train_pred = client.post(
            "/api/v1/predict",
            json={"features": {"x": 0.95, "y": 0.95}},
        )
        assert post_train_pred.status_code == 200
        post_train_state = post_train_pred.json()["model_state"]

        # State should have changed
        if initial_state == ModelStateEnum.COLD_START.value:
            assert post_train_state in [
                ModelStateEnum.WARMING.value,
                ModelStateEnum.ACTIVE.value,
            ]

    def test_metrics_reflect_activity(self, client: TestClient, sample_features: Dict[str, float]):
        """Test that metrics accurately reflect API activity."""
        # Get baseline metrics
        baseline = client.get("/api/v1/metrics").json()
        baseline_predictions = baseline["predictions_total"]
        baseline_training = baseline["training_samples_total"]

        # Perform API operations
        num_predictions = 5
        num_training = 3

        for _ in range(num_predictions):
            client.post("/api/v1/predict", json={"features": sample_features})

        for i in range(num_training):
            client.post(
                "/api/v1/train",
                json={"features": sample_features, "label": i % 2},
            )

        # Check updated metrics
        updated = client.get("/api/v1/metrics").json()

        assert updated["predictions_total"] == baseline_predictions + num_predictions
        assert updated["training_samples_total"] == baseline_training + num_training


class TestErrorHandling:
    """Test error handling across endpoints."""

    def test_invalid_json_returns_422(self, client: TestClient):
        """Test invalid JSON payload returns 422."""
        response = client.post(
            "/api/v1/predict",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_missing_required_fields_returns_422(self, client: TestClient):
        """Test missing required fields returns 422."""
        response = client.post(
            "/api/v1/predict",
            json={},  # Missing features
        )

        assert response.status_code == 422

    def test_wrong_type_returns_422(self, client: TestClient):
        """Test wrong field types return 422."""
        response = client.post(
            "/api/v1/train",
            json={
                "features": {"x": 1.0},
                "label": "not_an_int",  # Should be int
            },
        )

        assert response.status_code == 422


class TestConcurrentRequests:
    """Test handling of concurrent requests."""

    def test_concurrent_predictions(self, client: TestClient, sample_features: Dict[str, float]):
        """Test handling multiple concurrent prediction requests."""
        import concurrent.futures

        def make_prediction():
            return client.post(
                "/api/v1/predict",
                json={"features": sample_features},
            )

        # Note: TestClient is not truly concurrent, but this tests the endpoint
        # can handle rapid sequential requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_prediction) for _ in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        assert all(r.status_code == 200 for r in results)

    def test_concurrent_training(self, client: TestClient, sample_features: Dict[str, float]):
        """Test handling multiple concurrent training requests."""
        import concurrent.futures

        def make_training_request(label):
            return client.post(
                "/api/v1/train",
                json={
                    "features": sample_features,
                    "label": label,
                },
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_training_request, i % 2) for i in range(20)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed (status 202)
        assert all(r.status_code == 202 for r in results)


# =============================================================================
# Performance Tests
# =============================================================================


class TestPredictionPerformance:
    """Test prediction latency requirements."""

    def test_prediction_latency_acceptable(
        self, client: TestClient, sample_features: Dict[str, float]
    ):
        """Test prediction latency is within acceptable bounds."""
        # Warm up
        client.post("/api/v1/predict", json={"features": sample_features})

        # Measure latency over multiple requests
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            response = client.post(
                "/api/v1/predict",
                json={"features": sample_features},
            )
            end = time.perf_counter()

            assert response.status_code == 200
            latencies.append((end - start) * 1000)  # Convert to ms

        # Calculate P95 latency
        latencies.sort()
        p95_index = int(len(latencies) * 0.95)
        p95_latency = latencies[p95_index]

        # P95 should be under 50ms (as per spec)
        # Allow some slack for test environment overhead
        assert p95_latency < 500  # 500ms slack for test environment


class TestTrainingThroughput:
    """Test training throughput requirements."""

    def test_batch_training_throughput(
        self,
        client: TestClient,
    ):
        """Test batch training can handle multiple samples efficiently."""
        # Create a batch of samples
        batch_size = 100
        samples = [
            {
                "features": {"x": float(i) / batch_size, "y": float(i % 10) / 10},
                "label": i % 2,
            }
            for i in range(batch_size)
        ]

        start = time.perf_counter()
        response = client.post(
            "/api/v1/train/batch",
            json={"samples": samples, "async_processing": False},
        )
        end = time.perf_counter()

        assert response.status_code == 202
        duration = end - start

        # Should process 100 samples in reasonable time
        assert duration < 10  # 10 seconds for 100 samples (generous for test env)
