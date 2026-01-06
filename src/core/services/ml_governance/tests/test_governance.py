"""
Tests for ML Governance API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from src.core.services.ml_governance.src.main import app


@pytest.fixture
def test_client():
    """FastAPI test client fixture"""
    return TestClient(app)


class TestMLGovernanceAPI:
    """Test cases for ML governance API endpoints"""

    def test_health_endpoint(self, test_client: TestClient):
        """Test health check endpoint"""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "ml-governance-service"
        assert "metrics" in data
        assert "timestamp" in data

    def test_readiness_endpoint(self, test_client: TestClient):
        """Test readiness check endpoint"""
        response = test_client.get("/ready")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ready"
        assert data["service"] == "ml-governance-service"
        assert "active_models" in data

    def test_root_endpoint(self, test_client: TestClient):
        """Test root endpoint"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "ml-governance-service"
        assert "capabilities" in data

    def test_predict_governance_success(self, test_client: TestClient):
        """Test successful governance prediction"""
        request_data = {
            "content": "This is a helpful message about Python programming",
            "context": {"intent_class": "helpful", "intent_confidence": 0.9, "toxicity_score": 0.1},
            "user_id": "test_user",
        }

        response = test_client.post("/api/v1/governance/predict", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "decision" in data
        assert "confidence" in data
        assert "reasoning" in data
        assert "model_version" in data
        assert "processing_time_ms" in data

    def test_predict_governance_minimal(self, test_client: TestClient):
        """Test governance prediction with minimal data"""
        request_data = {"content": "Hello world"}

        response = test_client.post("/api/v1/governance/predict", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "decision" in data
        assert isinstance(data["confidence"], (int, float))
        assert isinstance(data["reasoning"], str)

    def test_submit_feedback_success(self, test_client: TestClient):
        """Test successful feedback submission"""
        feedback_data = {
            "request_id": "test-request-123",
            "feedback_type": "correct",
            "rationale": "This was the right decision",
            "severity": "medium",
        }

        response = test_client.post("/api/v1/feedback/submit", json=feedback_data)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "feedback_received"
        assert data["request_id"] == "test-request-123"
        assert "message" in data

    def test_get_governance_status(self, test_client: TestClient):
        """Test governance status endpoint"""
        response = test_client.get("/api/v1/governance/status")

        assert response.status_code == 200
        data = response.json()

        assert "active_models" in data
        assert "ab_tests" in data
        assert "metrics" in data

    def test_get_model_metrics(self, test_client: TestClient):
        """Test model metrics endpoint"""
        response = test_client.get("/api/v1/models/metrics")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)

    def test_get_ab_tests(self, test_client: TestClient):
        """Test A/B tests endpoint"""
        response = test_client.get("/api/v1/models/ab-tests")

        assert response.status_code == 200
        data = response.json()

        assert "ab_tests" in data
        assert "total" in data

    def test_invalid_predict_request(self, test_client: TestClient):
        """Test prediction with invalid data"""
        response = test_client.post("/api/v1/governance/predict", json={})

        # Should still work with defaults, not return 422
        assert response.status_code in [200, 400]  # Allow fallback behavior
