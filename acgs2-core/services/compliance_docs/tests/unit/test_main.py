"""
Unit tests for compliance-docs-service main application
"""

import pytest
from fastapi.testclient import TestClient

from src.main import app


class TestMainApplication:
    """Test cases for the main FastAPI application"""

    def test_health_endpoint(self, test_client: TestClient):
        """Test health check endpoint returns correct response"""
        response = test_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["service"] == "compliance-docs-service"
        assert "timestamp" in data

    def test_readiness_endpoint(self, test_client: TestClient):
        """Test readiness check endpoint returns correct response"""
        response = test_client.get("/ready")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "ready"
        assert data["service"] == "compliance-docs-service"
        assert "timestamp" in data

    def test_root_endpoint(self, test_client: TestClient):
        """Test root endpoint returns service information"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "compliance-docs-service"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data
        assert "health" in data["endpoints"]
        assert "ready" in data["endpoints"]
        assert "api" in data["endpoints"]

    def test_invalid_endpoint(self, test_client: TestClient):
        """Test that invalid endpoints return 404"""
        response = test_client.get("/invalid-endpoint")

        assert response.status_code == 404
