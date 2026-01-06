"""
Standardized test configuration for ml-governance-service
"""

import pytest
from fastapi.testclient import TestClient
from src.core.services.ml_governance.src.main import app


@pytest.fixture
def test_client():
    """FastAPI test client fixture"""
    return TestClient(app)
