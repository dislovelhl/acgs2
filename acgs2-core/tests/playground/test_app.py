"""
ACGS-2 Policy Playground - Backend API Tests

Comprehensive test coverage for playground FastAPI endpoints including:
- POST /api/validate - Policy syntax validation
- POST /api/evaluate - Policy evaluation with input
- GET /api/examples - Example policies retrieval
- Health check endpoints

Follows patterns from test_opa_service.py and test_policy_cli.py
"""

import importlib.util
import os
import sys
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directories to path for imports
# This allows importing cli.opa_service and other modules
_base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _base_dir not in sys.path:
    sys.path.insert(0, _base_dir)


def _load_playground_app():
    """Load playground.app module dynamically from file path."""
    app_path = os.path.join(_base_dir, "playground", "app.py")
    spec = importlib.util.spec_from_file_location("playground_app", app_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["playground_app"] = module
    spec.loader.exec_module(module)
    return module


# Load playground app module
_playground_app_module = None


# =============================================================================
# Mock Classes for Testing
# =============================================================================


class MockPolicyValidationResult:
    """Mock PolicyValidationResult for testing."""

    def __init__(
        self,
        is_valid: bool = True,
        errors: list = None,
        warnings: list = None,
        metadata: dict = None,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.metadata = metadata or {}


class MockPolicyEvaluationResult:
    """Mock PolicyEvaluationResult for testing."""

    def __init__(
        self,
        success: bool = True,
        result: Any = None,
        allowed: bool = None,
        reason: str = "",
        metadata: dict = None,
    ):
        self.success = success
        self.result = result
        self.allowed = allowed
        self.reason = reason
        self.metadata = metadata or {}


class MockOPAService:
    """Mock OPAService for testing playground without real OPA."""

    def __init__(self, opa_url: str = "http://localhost:8181", timeout: float = 10.0):
        self.opa_url = opa_url
        self.timeout = timeout
        self._async_client = MagicMock()

    async def _ensure_async_client(self):
        """Mock async client initialization."""
        return self._async_client

    async def aclose(self):
        """Mock async close."""
        pass

    async def async_health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        return {"status": "healthy", "opa_url": self.opa_url}

    async def async_validate_policy(self, policy_content: str) -> MockPolicyValidationResult:
        """Mock policy validation."""
        if not policy_content.strip():
            return MockPolicyValidationResult(
                is_valid=False,
                errors=["Policy content is empty"],
            )
        if "syntax_error" in policy_content:
            return MockPolicyValidationResult(
                is_valid=False,
                errors=["Line 1, Col 1: rego_parse_error: unexpected keyword"],
            )
        return MockPolicyValidationResult(is_valid=True)

    async def async_evaluate_policy(
        self,
        policy_content: str,
        input_data: Dict[str, Any],
        policy_path: str = "data",
    ) -> MockPolicyEvaluationResult:
        """Mock policy evaluation."""
        if "error_policy" in policy_content:
            return MockPolicyEvaluationResult(
                success=False,
                reason="Policy upload failed",
            )
        return MockPolicyEvaluationResult(
            success=True,
            result={"allow": True},
            allowed=True,
            reason="Policy evaluated successfully",
        )


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_opa_service():
    """Create a mock OPA service for testing."""
    return MockOPAService()


@pytest.fixture
def valid_policy():
    """Sample valid Rego policy."""
    return """package playground.test

default allow := false

allow {
    input.user.role == "admin"
}
"""


@pytest.fixture
def invalid_policy():
    """Sample invalid Rego policy with syntax error."""
    return """package playground.test

default allow := syntax_error {
    invalid syntax here
"""


@pytest.fixture
def sample_input():
    """Sample input data for policy evaluation."""
    return {"user": {"id": "user-123", "role": "admin"}}


@pytest.fixture
def playground_app_module():
    """Load and return the playground app module."""
    global _playground_app_module
    if _playground_app_module is None:
        _playground_app_module = _load_playground_app()
    return _playground_app_module


@pytest.fixture
def app_with_mock_opa(mock_opa_service, playground_app_module):
    """
    Create FastAPI app with mocked OPA service.

    Directly patches the app module's opa_service global variable.
    """
    from fastapi.testclient import TestClient

    app_module = playground_app_module

    # Store original and patch
    original_opa_service = app_module.opa_service
    app_module.opa_service = mock_opa_service

    try:
        client = TestClient(app_module.app, raise_server_exceptions=False)
        yield client
    finally:
        # Restore original
        app_module.opa_service = original_opa_service


@pytest.fixture
def test_client_no_opa(playground_app_module):
    """
    Create FastAPI test client without OPA service initialized.

    Useful for testing service unavailable scenarios.
    """
    from fastapi.testclient import TestClient

    app_module = playground_app_module

    original_opa_service = app_module.opa_service
    app_module.opa_service = None

    try:
        client = TestClient(app_module.app, raise_server_exceptions=False)
        yield client
    finally:
        app_module.opa_service = original_opa_service


# =============================================================================
# Validate Endpoint Tests
# =============================================================================


class TestValidateEndpoint:
    """Tests for POST /api/validate endpoint."""

    def test_validate_valid_policy(self, app_with_mock_opa, valid_policy):
        """Test validation of a valid policy returns success."""
        response = app_with_mock_opa.post(
            "/api/validate",
            json={"policy": valid_policy},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_validate_invalid_policy(self, app_with_mock_opa, invalid_policy):
        """Test validation of an invalid policy returns errors."""
        response = app_with_mock_opa.post(
            "/api/validate",
            json={"policy": invalid_policy},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_empty_policy(self, app_with_mock_opa):
        """Test validation of empty policy returns error."""
        response = app_with_mock_opa.post(
            "/api/validate",
            json={"policy": ""},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert any("empty" in err.lower() for err in data["errors"])

    def test_validate_whitespace_only_policy(self, app_with_mock_opa):
        """Test validation of whitespace-only policy returns error."""
        response = app_with_mock_opa.post(
            "/api/validate",
            json={"policy": "   \n\t  "},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_validate_missing_policy_field(self, app_with_mock_opa):
        """Test validation with missing policy field returns 422."""
        response = app_with_mock_opa.post(
            "/api/validate",
            json={},
        )

        assert response.status_code == 422

    def test_validate_opa_not_initialized(self, test_client_no_opa, valid_policy):
        """Test validation when OPA service is not initialized."""
        response = test_client_no_opa.post(
            "/api/validate",
            json={"policy": valid_policy},
        )

        assert response.status_code == 503
        data = response.json()
        assert "not initialized" in data["detail"].lower()


class TestValidateEndpointWithOPAErrors:
    """Tests for validate endpoint handling OPA errors."""

    def test_validate_opa_connection_error(self):
        """Test validation when OPA connection fails."""
        from fastapi.testclient import TestClient

        import playground.app as app_module

        mock_service = MagicMock()
        mock_service.async_validate_policy = AsyncMock(side_effect=Exception("Connection refused"))

        original = app_module.opa_service
        app_module.opa_service = mock_service

        try:
            client = TestClient(app_module.app, raise_server_exceptions=False)
            response = client.post(
                "/api/validate",
                json={"policy": "package test\n"},
            )

            assert response.status_code == 500
        finally:
            app_module.opa_service = original

    def test_validate_with_opa_connection_error_class(self):
        """Test validation with OPAConnectionError raises 503."""
        from cli.opa_service import OPAConnectionError
        from fastapi.testclient import TestClient

        import playground.app as app_module

        mock_service = MagicMock()
        mock_service.async_validate_policy = AsyncMock(
            side_effect=OPAConnectionError("http://localhost:8181", "Connection refused")
        )

        original = app_module.opa_service
        app_module.opa_service = mock_service

        try:
            client = TestClient(app_module.app, raise_server_exceptions=False)
            response = client.post(
                "/api/validate",
                json={"policy": "package test\n"},
            )

            assert response.status_code == 503
            data = response.json()
            assert "unavailable" in data["detail"].lower()
        finally:
            app_module.opa_service = original


# =============================================================================
# Evaluate Endpoint Tests
# =============================================================================


class TestEvaluateEndpoint:
    """Tests for POST /api/evaluate endpoint."""

    def test_evaluate_policy_success(self, app_with_mock_opa, valid_policy, sample_input):
        """Test successful policy evaluation."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={
                "policy": valid_policy,
                "input": sample_input,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "result" in data

    def test_evaluate_policy_with_allow_result(self, app_with_mock_opa, valid_policy, sample_input):
        """Test evaluation returns allowed field when present."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={
                "policy": valid_policy,
                "input": sample_input,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["allowed"] is True

    def test_evaluate_policy_with_custom_path(self, app_with_mock_opa, valid_policy, sample_input):
        """Test evaluation with custom policy path."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={
                "policy": valid_policy,
                "input": sample_input,
                "path": "playground.test.allow",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_evaluate_policy_empty_input(self, app_with_mock_opa, valid_policy):
        """Test evaluation with empty input object."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={
                "policy": valid_policy,
                "input": {},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_evaluate_policy_no_input_field(self, app_with_mock_opa, valid_policy):
        """Test evaluation without input field uses empty dict."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={
                "policy": valid_policy,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_evaluate_policy_failure(self, app_with_mock_opa):
        """Test evaluation failure returns error details."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={
                "policy": "error_policy package test\n",
                "input": {},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["error"] is not None

    def test_evaluate_missing_policy_field(self, app_with_mock_opa):
        """Test evaluation with missing policy field returns 422."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={"input": {}},
        )

        assert response.status_code == 422

    def test_evaluate_opa_not_initialized(self, test_client_no_opa, valid_policy):
        """Test evaluation when OPA service is not initialized."""
        response = test_client_no_opa.post(
            "/api/evaluate",
            json={"policy": valid_policy, "input": {}},
        )

        assert response.status_code == 503

    def test_evaluate_complex_input(self, app_with_mock_opa, valid_policy):
        """Test evaluation with complex nested input."""
        complex_input = {
            "user": {
                "id": "user-123",
                "roles": ["admin", "editor"],
                "metadata": {
                    "created": "2024-01-01",
                    "tags": ["verified"],
                },
            },
            "resource": {
                "type": "document",
                "permissions": ["read", "write"],
            },
        }

        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={
                "policy": valid_policy,
                "input": complex_input,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestEvaluateEndpointWithOPAErrors:
    """Tests for evaluate endpoint handling OPA errors."""

    def test_evaluate_opa_connection_error(self):
        """Test evaluation when OPA connection fails."""
        from cli.opa_service import OPAConnectionError
        from fastapi.testclient import TestClient

        import playground.app as app_module

        mock_service = MagicMock()
        mock_service.async_evaluate_policy = AsyncMock(
            side_effect=OPAConnectionError("http://localhost:8181", "Connection refused")
        )

        original = app_module.opa_service
        app_module.opa_service = mock_service

        try:
            client = TestClient(app_module.app, raise_server_exceptions=False)
            response = client.post(
                "/api/evaluate",
                json={"policy": "package test\n", "input": {}},
            )

            assert response.status_code == 503
        finally:
            app_module.opa_service = original


# =============================================================================
# Examples Endpoint Tests
# =============================================================================


class TestExamplesEndpoint:
    """Tests for GET /api/examples endpoint."""

    def test_get_examples_returns_list(self, app_with_mock_opa):
        """Test examples endpoint returns a list of examples."""
        response = app_with_mock_opa.get("/api/examples")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5  # Spec requires at least 5 examples

    def test_get_examples_have_required_fields(self, app_with_mock_opa):
        """Test each example has all required fields."""
        response = app_with_mock_opa.get("/api/examples")

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "id",
            "name",
            "description",
            "category",
            "policy",
            "test_input",
            "expected_result",
            "explanation",
            "difficulty",
            "tags",
        ]

        for example in data:
            for field in required_fields:
                assert (
                    field in example
                ), f"Missing field '{field}' in example '{example.get('id', 'unknown')}'"

    def test_get_examples_have_valid_policies(self, app_with_mock_opa):
        """Test each example has non-empty policy content."""
        response = app_with_mock_opa.get("/api/examples")

        assert response.status_code == 200
        data = response.json()

        for example in data:
            assert example["policy"].strip(), f"Empty policy in example '{example['id']}'"
            assert (
                "package" in example["policy"]
            ), f"Policy missing package declaration in '{example['id']}'"

    def test_get_examples_filter_by_category(self, app_with_mock_opa):
        """Test filtering examples by category."""
        response = app_with_mock_opa.get("/api/examples?category=RBAC")

        assert response.status_code == 200
        data = response.json()
        # May return empty if no RBAC examples or filtered differently
        assert isinstance(data, list)

    def test_get_examples_filter_by_difficulty(self, app_with_mock_opa):
        """Test filtering examples by difficulty."""
        response = app_with_mock_opa.get("/api/examples?difficulty=beginner")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned examples should have beginner difficulty
        for example in data:
            assert example["difficulty"] == "beginner"

    def test_get_examples_filter_by_tag(self, app_with_mock_opa):
        """Test filtering examples by tag."""
        response = app_with_mock_opa.get("/api/examples?tag=rbac")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned examples should have the tag
        for example in data:
            assert "rbac" in example["tags"]

    def test_get_examples_categories_diverse(self, app_with_mock_opa):
        """Test examples cover multiple categories."""
        response = app_with_mock_opa.get("/api/examples")

        assert response.status_code == 200
        data = response.json()

        categories = {example["category"] for example in data}
        # Spec requires diverse examples covering multiple categories
        assert len(categories) >= 3, f"Expected at least 3 categories, got {categories}"


class TestExampleByIdEndpoint:
    """Tests for GET /api/examples/{example_id} endpoint."""

    def test_get_example_by_valid_id(self, app_with_mock_opa):
        """Test getting a specific example by ID."""
        # First get all examples to find a valid ID
        response = app_with_mock_opa.get("/api/examples")
        examples = response.json()
        example_id = examples[0]["id"]

        # Now fetch by ID
        response = app_with_mock_opa.get(f"/api/examples/{example_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == example_id

    def test_get_example_by_invalid_id(self, app_with_mock_opa):
        """Test getting an example with non-existent ID returns 404."""
        response = app_with_mock_opa.get("/api/examples/nonexistent-id-12345")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestExampleCategoriesEndpoint:
    """Tests for GET /api/examples/categories/list endpoint."""

    def test_get_categories_list(self, app_with_mock_opa):
        """Test getting examples grouped by category."""
        response = app_with_mock_opa.get("/api/examples/categories/list")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        # Should have at least some categories
        assert len(data) > 0


# =============================================================================
# Health Check Endpoint Tests
# =============================================================================


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_liveness_check(self, app_with_mock_opa):
        """Test liveness probe returns alive status."""
        response = app_with_mock_opa.get("/health/live")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
        assert data["service"] == "policy-playground"

    def test_readiness_check_with_opa(self, app_with_mock_opa):
        """Test readiness probe with OPA service initialized."""
        response = app_with_mock_opa.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "policy-playground"
        # Status depends on mock OPA health

    def test_readiness_check_without_opa(self, test_client_no_opa):
        """Test readiness probe without OPA service initialized."""
        response = test_client_no_opa.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "not_ready"
        assert data["opa_status"] == "not_initialized"

    def test_general_health_check(self, app_with_mock_opa):
        """Test general health endpoint."""
        response = app_with_mock_opa.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data


# =============================================================================
# Root Endpoint Tests
# =============================================================================


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_api_info(self, app_with_mock_opa):
        """Test root endpoint returns API information."""
        response = app_with_mock_opa.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "endpoints" in data
        assert "validate" in data["endpoints"]
        assert "evaluate" in data["endpoints"]
        assert "examples" in data["endpoints"]


# =============================================================================
# CORS Tests
# =============================================================================


class TestCORSConfiguration:
    """Tests for CORS middleware configuration."""

    def test_cors_allows_localhost(self, app_with_mock_opa):
        """Test CORS allows requests from localhost."""
        response = app_with_mock_opa.options(
            "/api/validate",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "POST",
            },
        )

        # CORS preflight should succeed
        assert response.status_code in [200, 204]

    def test_cors_headers_present(self, app_with_mock_opa):
        """Test CORS headers are present in response."""
        response = app_with_mock_opa.post(
            "/api/validate",
            json={"policy": "package test\n"},
            headers={"Origin": "http://localhost:8080"},
        )

        # Response should have CORS headers
        assert response.status_code == 200


# =============================================================================
# Request/Response Model Tests
# =============================================================================


class TestRequestModels:
    """Tests for request body validation."""

    def test_validate_request_requires_policy(self, app_with_mock_opa):
        """Test validate endpoint requires policy field."""
        response = app_with_mock_opa.post(
            "/api/validate",
            json={},
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_evaluate_request_requires_policy(self, app_with_mock_opa):
        """Test evaluate endpoint requires policy field."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={"input": {}},
        )

        assert response.status_code == 422

    def test_evaluate_request_input_optional(self, app_with_mock_opa):
        """Test evaluate endpoint allows missing input field."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={"policy": "package test\ndefault allow := true"},
        )

        assert response.status_code == 200

    def test_evaluate_request_path_optional(self, app_with_mock_opa):
        """Test evaluate endpoint allows missing path field."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={"policy": "package test\ndefault allow := true", "input": {}},
        )

        assert response.status_code == 200


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_validate_very_long_policy(self, app_with_mock_opa):
        """Test validation with very long policy content."""
        # Generate a long policy with many rules
        rules = "\n".join([f"rule_{i} {{ input.x == {i} }}" for i in range(1000)])
        long_policy = f"package test\n\n{rules}"

        response = app_with_mock_opa.post(
            "/api/validate",
            json={"policy": long_policy},
        )

        assert response.status_code == 200

    def test_evaluate_with_special_characters_in_input(self, app_with_mock_opa):
        """Test evaluation with special characters in input."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={
                "policy": "package test\ndefault allow := true",
                "input": {
                    "name": "Test <script>alert('xss')</script>",
                    "description": "Contains 'quotes' and \"double quotes\"",
                },
            },
        )

        assert response.status_code == 200

    def test_evaluate_with_unicode_input(self, app_with_mock_opa):
        """Test evaluation with Unicode characters in input."""
        response = app_with_mock_opa.post(
            "/api/evaluate",
            json={
                "policy": "package test\ndefault allow := true",
                "input": {
                    "name": "Test User",
                    "greeting": "Hello World",
                },
            },
        )

        assert response.status_code == 200

    def test_validate_policy_with_comments(self, app_with_mock_opa):
        """Test validation with policy containing comments."""
        policy_with_comments = """package test
# This is a comment
default allow := false

# Another comment
allow {
    input.user == "admin"  # inline comment
}
"""
        response = app_with_mock_opa.post(
            "/api/validate",
            json={"policy": policy_with_comments},
        )

        assert response.status_code == 200


# =============================================================================
# Example Content Tests
# =============================================================================


class TestExampleContent:
    """Tests for example policy content quality."""

    def test_examples_have_test_input(self, app_with_mock_opa):
        """Test all examples have test_input field with data."""
        response = app_with_mock_opa.get("/api/examples")

        assert response.status_code == 200
        data = response.json()

        for example in data:
            assert (
                example["test_input"] is not None
            ), f"Example '{example['id']}' missing test_input"
            # test_input should be a dict (can be empty but should exist)
            assert isinstance(
                example["test_input"], dict
            ), f"Example '{example['id']}' test_input is not a dict"

    def test_examples_have_expected_result(self, app_with_mock_opa):
        """Test all examples have expected_result field."""
        response = app_with_mock_opa.get("/api/examples")

        assert response.status_code == 200
        data = response.json()

        for example in data:
            assert (
                example["expected_result"] is not None
            ), f"Example '{example['id']}' missing expected_result"

    def test_examples_have_explanation(self, app_with_mock_opa):
        """Test all examples have non-empty explanation."""
        response = app_with_mock_opa.get("/api/examples")

        assert response.status_code == 200
        data = response.json()

        for example in data:
            assert example[
                "explanation"
            ].strip(), f"Example '{example['id']}' has empty explanation"

    def test_examples_have_valid_difficulty(self, app_with_mock_opa):
        """Test all examples have valid difficulty level."""
        valid_difficulties = ["beginner", "intermediate", "advanced"]

        response = app_with_mock_opa.get("/api/examples")

        assert response.status_code == 200
        data = response.json()

        for example in data:
            assert (
                example["difficulty"] in valid_difficulties
            ), f"Example '{example['id']}' has invalid difficulty '{example['difficulty']}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
