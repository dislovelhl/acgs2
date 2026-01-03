"""
Tests for HITL approvals API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from src.main import app
from src.core.models import ApprovalPriority


@pytest.fixture
def test_client():
    """FastAPI test client fixture"""
    return TestClient(app)


class TestApprovalAPI:
    """Test cases for approval API endpoints"""

    def test_health_endpoint(self, test_client: TestClient):
        """Test health check endpoint"""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "hitl-approvals-service"
        assert "timestamp" in data

    def test_readiness_endpoint(self, test_client: TestClient):
        """Test readiness check endpoint"""
        response = test_client.get("/ready")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ready"
        assert data["service"] == "hitl-approvals-service"
        assert "timestamp" in data

    def test_root_endpoint(self, test_client: TestClient):
        """Test root endpoint"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "hitl-approvals-service"
        assert "api" in data["endpoints"]

    @patch('src.api.approvals.approval_engine')
    def test_create_approval_request_success(self, mock_engine, test_client: TestClient):
        """Test successful approval request creation"""
        mock_engine.create_approval_request = AsyncMock(return_value="test-request-id")

        request_data = {
            "chain_id": "test-chain",
            "title": "Test Approval",
            "description": "Test approval request",
            "requester_id": "user123",
            "priority": "high",
            "context": {"test": "data"}
        }

        response = test_client.post("/api/v1/approvals/", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == "test-request-id"
        assert data["status"] == "created"

    @patch('src.api.approvals.approval_engine')
    def test_create_approval_request_failure(self, mock_engine, test_client: TestClient):
        """Test approval request creation failure"""
        mock_engine.create_approval_request = AsyncMock(return_value=None)

        request_data = {
            "chain_id": "invalid-chain",
            "title": "Test Approval",
            "description": "Test approval request",
            "requester_id": "user123"
        }

        response = test_client.post("/api/v1/approvals/", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "Could not create approval request" in data["detail"]

    @patch('src.api.approvals.approval_engine')
    def test_approve_request_success(self, mock_engine, test_client: TestClient):
        """Test successful approval submission"""
        mock_engine.approve_request = AsyncMock(return_value=True)

        approval_data = {
            "approver_id": "approver123",
            "decision": "approved",
            "rationale": "Looks good to me"
        }

        response = test_client.post("/api/v1/approvals/test-request-id/approve", json=approval_data)

        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == "test-request-id"
        assert data["status"] == "decision_recorded"

    @patch('src.api.approvals.approval_engine')
    def test_approve_request_failure(self, mock_engine, test_client: TestClient):
        """Test approval submission failure"""
        mock_engine.approve_request = AsyncMock(return_value=False)

        approval_data = {
            "approver_id": "approver123",
            "decision": "approved"
        }

        response = test_client.post("/api/v1/approvals/test-request-id/approve", json=approval_data)

        assert response.status_code == 400
        data = response.json()
        assert "Could not submit approval decision" in data["detail"]

    @patch('src.api.approvals.approval_engine')
    def test_get_request_status_success(self, mock_engine, test_client: TestClient):
        """Test successful status retrieval"""
        mock_status = {
            "request": {"id": "test-request", "status": "pending"},
            "chain": {"id": "test-chain", "name": "Test Chain"},
            "current_step": {"name": "Review", "approvers": ["user1"]},
            "time_remaining_minutes": 30,
            "can_approve": False
        }
        mock_engine.get_request_status = AsyncMock(return_value=mock_status)

        response = test_client.get("/api/v1/approvals/test-request-id/status")

        assert response.status_code == 200
        data = response.json()
        assert data["request"]["id"] == "test-request"
        assert data["chain"]["name"] == "Test Chain"

    @patch('src.api.approvals.approval_engine')
    def test_get_request_status_not_found(self, mock_engine, test_client: TestClient):
        """Test status retrieval for non-existent request"""
        mock_engine.get_request_status = AsyncMock(return_value=None)

        response = test_client.get("/api/v1/approvals/non-existent/status")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
