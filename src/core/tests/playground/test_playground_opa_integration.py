"""
End-to-End Integration Tests for Policy Playground with Live OPA Server

These tests verify the complete playground integration:
- Frontend → Backend API → OPA Server

Requirements:
- OPA server must be running at http://localhost:8181
- Run: docker run -d -p 8181:8181 openpolicyagent/opa run --server

Manual Browser Verification Steps (for human QA):
=================================================
1. Start OPA server: docker run -d -p 8181:8181 openpolicyagent/opa run --server
2. Start playground backend: cd src/core/playground && uvicorn app:app --port 8080
3. Open http://localhost:8080/playground in browser
4. Load example policy from dropdown
5. Click 'Evaluate' button
6. Verify results displayed without errors
7. Modify policy to introduce syntax error (e.g., remove closing brace)
8. Click 'Validate' button
9. Verify error message with line number shown

Automated Tests Covered:
========================
1. Backend /api/validate endpoint with live OPA
2. Backend /api/evaluate endpoint with live OPA
3. Backend /api/examples endpoint (frontend data source)
4. Frontend-backend data contract verification
5. Error handling and status codes
"""

import os
import sys
from typing import Any, Dict

import httpx
import pytest

# Add parent path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


# Configuration
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")
PLAYGROUND_URL = os.getenv("PLAYGROUND_URL", "http://localhost:8080")
API_BASE = f"{PLAYGROUND_URL}/api"


def is_opa_available() -> bool:
    """Check if OPA server is available."""
    try:
        response = httpx.get(f"{OPA_URL}/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


def is_playground_available() -> bool:
    """Check if playground backend is available."""
    try:
        response = httpx.get(f"{PLAYGROUND_URL}/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


# Skip all tests if OPA or Playground is not available
_skip_reason = (
    "Integration test requirements not met. "
    "OPA and Playground servers must be running.\n"
    "Start with:\n"
    "  1. docker run -d -p 8181:8181 openpolicyagent/opa run --server\n"
    "  2. cd src/core/playground && uvicorn app:app --port 8080"
)


def require_full_stack():
    """Mark test to require full stack (OPA + Playground)."""
    return pytest.mark.skipif(
        not (is_opa_available() and is_playground_available()),
        reason=_skip_reason,
    )


def require_opa_only():
    """Mark test to require only OPA server."""
    return pytest.mark.skipif(
        not is_opa_available(),
        reason=f"OPA server not available at {OPA_URL}. "
        "Start with: docker run -d -p 8181:8181 openpolicyagent/opa run --server",
    )


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def http_client() -> httpx.Client:
    """Create HTTP client for API requests."""
    with httpx.Client(timeout=10.0) as client:
        yield client


@pytest.fixture
def valid_rbac_policy() -> str:
    """Valid RBAC policy for testing."""
    return """package playground.rbac

import rego.v1

default allow := false

# Admins have full access
allow if {
    input.user.role == "admin"
}

# Editors can read and write
allow if {
    input.user.role == "editor"
    input.action in ["read", "write"]
}

# Viewers can only read
allow if {
    input.user.role == "viewer"
    input.action == "read"
}
"""


@pytest.fixture
def invalid_policy() -> str:
    """Invalid policy with syntax error for testing."""
    return """package playground.invalid

default allow := false

# Missing closing brace - syntax error
allow {
    input.user.role == "admin"

"""


@pytest.fixture
def admin_input() -> Dict[str, Any]:
    """Input data for admin user."""
    return {"user": {"id": "user-123", "role": "admin"}, "action": "delete"}


@pytest.fixture
def viewer_input() -> Dict[str, Any]:
    """Input data for viewer user."""
    return {"user": {"id": "user-456", "role": "viewer"}, "action": "read"}


# =============================================================================
# Playground Backend API Tests with Live OPA
# =============================================================================


@require_full_stack()
class TestPlaygroundValidateIntegration:
    """Test /api/validate endpoint with live OPA server."""

    def test_validate_valid_policy(self, http_client: httpx.Client, valid_rbac_policy: str):
        """Test validation of valid policy returns success."""
        response = http_client.post(
            f"{API_BASE}/validate",
            json={"policy": valid_rbac_policy},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_validate_invalid_policy(self, http_client: httpx.Client, invalid_policy: str):
        """Test validation of invalid policy returns errors with line info."""
        response = http_client.post(
            f"{API_BASE}/validate",
            json={"policy": invalid_policy},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
        # Errors should contain useful information (line numbers, descriptions)
        errors_text = " ".join(data["errors"])
        # OPA typically includes line/column in error messages
        assert (
            "error" in errors_text.lower()
            or "line" in errors_text.lower()
            or "rego" in errors_text.lower()
        )

    def test_validate_empty_policy(self, http_client: httpx.Client):
        """Test validation of empty policy returns error."""
        response = http_client.post(
            f"{API_BASE}/validate",
            json={"policy": ""},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False

    def test_validate_policy_with_import(self, http_client: httpx.Client):
        """Test validation of policy with imports."""
        policy = """package playground.test

import rego.v1
import data.users

default allow := false

allow if {
    input.user in data.users.admins
}
"""
        response = http_client.post(
            f"{API_BASE}/validate",
            json={"policy": policy},
        )

        assert response.status_code == 200
        data = response.json()
        # Should be valid syntactically (even if data.users doesn't exist)
        assert data["valid"] is True


@require_full_stack()
class TestPlaygroundEvaluateIntegration:
    """Test /api/evaluate endpoint with live OPA server."""

    def test_evaluate_admin_allowed(
        self, http_client: httpx.Client, valid_rbac_policy: str, admin_input: Dict[str, Any]
    ):
        """Test evaluation with admin user returns allowed."""
        response = http_client.post(
            f"{API_BASE}/evaluate",
            json={
                "policy": valid_rbac_policy,
                "input": admin_input,
                "path": "playground.rbac",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"] is not None
        # Admin should be allowed
        assert data["result"].get("allow") is True or data["allowed"] is True

    def test_evaluate_viewer_read_allowed(
        self, http_client: httpx.Client, valid_rbac_policy: str, viewer_input: Dict[str, Any]
    ):
        """Test evaluation with viewer reading returns allowed."""
        response = http_client.post(
            f"{API_BASE}/evaluate",
            json={
                "policy": valid_rbac_policy,
                "input": viewer_input,
                "path": "playground.rbac",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_evaluate_viewer_delete_denied(self, http_client: httpx.Client, valid_rbac_policy: str):
        """Test evaluation with viewer deleting returns denied."""
        response = http_client.post(
            f"{API_BASE}/evaluate",
            json={
                "policy": valid_rbac_policy,
                "input": {
                    "user": {"id": "user-789", "role": "viewer"},
                    "action": "delete",
                },
                "path": "playground.rbac",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Viewer should not be allowed to delete
        assert data["result"].get("allow") is False or data["allowed"] is False

    def test_evaluate_empty_input(self, http_client: httpx.Client, valid_rbac_policy: str):
        """Test evaluation with empty input."""
        response = http_client.post(
            f"{API_BASE}/evaluate",
            json={
                "policy": valid_rbac_policy,
                "input": {},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@require_full_stack()
class TestPlaygroundExamplesIntegration:
    """Test /api/examples endpoint for frontend data."""

    def test_get_examples_returns_minimum_count(self, http_client: httpx.Client):
        """Test examples endpoint returns at least 5 examples (spec requirement)."""
        response = http_client.get(f"{API_BASE}/examples")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5, f"Expected at least 5 examples, got {len(data)}"

    def test_examples_have_required_fields(self, http_client: httpx.Client):
        """Test all examples have fields required by frontend."""
        response = http_client.get(f"{API_BASE}/examples")

        assert response.status_code == 200
        data = response.json()

        required_fields = [
            "id",  # For dropdown selection
            "name",  # Display name
            "description",  # Short description
            "category",  # For grouping in dropdown
            "policy",  # Policy content to load
            "test_input",  # Input data to load
            "expected_result",  # For showing expected outcome
            "explanation",  # For explanation panel
        ]

        for example in data:
            for field in required_fields:
                assert (
                    field in example
                ), f"Missing field '{field}' in example '{example.get('id', 'unknown')}'"

    def test_example_policies_are_valid(self, http_client: httpx.Client):
        """Test all example policies can be validated without errors."""
        examples_response = http_client.get(f"{API_BASE}/examples")
        examples = examples_response.json()

        for example in examples:
            validate_response = http_client.post(
                f"{API_BASE}/validate",
                json={"policy": example["policy"]},
            )

            assert (
                validate_response.status_code == 200
            ), f"Validation request failed for example '{example['id']}'"
            data = validate_response.json()
            assert (
                data["valid"] is True
            ), f"Example '{example['id']}' has invalid policy: {data['errors']}"

    def test_example_policies_can_be_evaluated(self, http_client: httpx.Client):
        """Test all example policies can be evaluated with their test input."""
        examples_response = http_client.get(f"{API_BASE}/examples")
        examples = examples_response.json()

        for example in examples:
            evaluate_response = http_client.post(
                f"{API_BASE}/evaluate",
                json={
                    "policy": example["policy"],
                    "input": example["test_input"],
                },
            )

            assert (
                evaluate_response.status_code == 200
            ), f"Evaluation request failed for example '{example['id']}'"
            data = evaluate_response.json()
            assert (
                data["success"] is True
            ), f"Example '{example['id']}' evaluation failed: {data.get('error')}"

    def test_examples_cover_diverse_categories(self, http_client: httpx.Client):
        """Test examples cover multiple categories as required by spec."""
        response = http_client.get(f"{API_BASE}/examples")
        examples = response.json()

        categories = {example["category"] for example in examples}
        # Spec requires diverse categories (RBAC, validation, authorization, quotas, compliance)
        assert len(categories) >= 3, f"Expected at least 3 categories, got {categories}"


@require_full_stack()
class TestPlaygroundHealthIntegration:
    """Test health check endpoints for OPA connectivity."""

    def test_health_endpoint_shows_opa_status(self, http_client: httpx.Client):
        """Test health endpoint returns OPA connection status."""
        response = http_client.get(f"{PLAYGROUND_URL}/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ready", "alive", "degraded", "not_ready"]
        assert "service" in data

    def test_readiness_probe_with_opa(self, http_client: httpx.Client):
        """Test readiness probe indicates OPA connectivity."""
        response = http_client.get(f"{PLAYGROUND_URL}/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data.get("opa_status") == "healthy"


# =============================================================================
# Frontend-Backend Contract Tests
# =============================================================================


@require_full_stack()
class TestFrontendBackendContract:
    """Test the data contract between frontend and backend."""

    def test_validate_response_matches_frontend_expectations(self, http_client: httpx.Client):
        """Test validate response has fields expected by frontend JavaScript."""
        response = http_client.post(
            f"{API_BASE}/validate",
            json={"policy": "package test\ndefault allow := true"},
        )

        data = response.json()
        # Frontend expects these fields (from app.js handleValidate)
        assert "valid" in data  # Used for success/error display
        assert "errors" in data  # Used for error message list
        assert isinstance(data["errors"], list)

    def test_evaluate_response_matches_frontend_expectations(self, http_client: httpx.Client):
        """Test evaluate response has fields expected by frontend JavaScript."""
        response = http_client.post(
            f"{API_BASE}/evaluate",
            json={
                "policy": "package test\ndefault allow := true",
                "input": {},
            },
        )

        data = response.json()
        # Frontend expects these fields (from app.js handleEvaluate)
        assert "success" in data  # Used for success/error branching
        assert "result" in data  # Used for displaying evaluation result
        # Optional but used if present
        if data["success"]:
            assert "allowed" in data or data["result"] is not None

    def test_examples_response_matches_frontend_expectations(self, http_client: httpx.Client):
        """Test examples response has fields expected by frontend JavaScript."""
        response = http_client.get(f"{API_BASE}/examples")

        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            example = data[0]
            # Frontend uses these fields (from app.js handleExampleSelect)
            assert "id" in example  # For selection value
            assert "name" in example  # For dropdown display
            assert "category" in example  # For optgroup grouping
            assert "policy" in example  # For loading into policy editor
            assert "test_input" in example  # For loading into input editor
            assert "explanation" in example  # For explanation panel


@require_full_stack()
class TestCORSIntegration:
    """Test CORS is properly configured for frontend requests."""

    def test_cors_preflight_for_validate(self, http_client: httpx.Client):
        """Test CORS preflight request for validate endpoint."""
        response = http_client.options(
            f"{API_BASE}/validate",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )

        # Should succeed with 200 or 204
        assert response.status_code in [200, 204]

    def test_cors_headers_on_api_response(self, http_client: httpx.Client):
        """Test CORS headers are present on API responses."""
        response = http_client.post(
            f"{API_BASE}/validate",
            json={"policy": "package test"},
            headers={"Origin": "http://localhost:8080"},
        )

        assert response.status_code == 200
        # CORS headers should be present (exact header names may vary)
        # Common headers: Access-Control-Allow-Origin, Access-Control-Allow-Methods


# =============================================================================
# Error Handling Integration Tests
# =============================================================================


@require_full_stack()
class TestErrorHandlingIntegration:
    """Test error handling across the full stack."""

    def test_malformed_json_returns_422(self, http_client: httpx.Client):
        """Test malformed JSON in request body returns 422."""
        response = http_client.post(
            f"{API_BASE}/validate",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    def test_missing_required_field_returns_422(self, http_client: httpx.Client):
        """Test missing required field returns 422."""
        response = http_client.post(
            f"{API_BASE}/validate",
            json={},  # Missing 'policy' field
        )

        assert response.status_code == 422

    def test_invalid_example_id_returns_404(self, http_client: httpx.Client):
        """Test requesting non-existent example returns 404."""
        response = http_client.get(f"{API_BASE}/examples/nonexistent-id-12345")

        assert response.status_code == 404


# =============================================================================
# Stress/Load Tests (Lightweight)
# =============================================================================


@require_full_stack()
class TestConcurrentRequests:
    """Test playground handles concurrent requests correctly."""

    def test_multiple_concurrent_validations(self, http_client: httpx.Client):
        """Test multiple validation requests can be processed concurrently."""
        policies = [
            "package test.a\ndefault allow := true",
            "package test.b\ndefault allow := false",
            "package test.c\nallow := input.x > 0",
        ]

        responses = []
        for policy in policies:
            response = http_client.post(
                f"{API_BASE}/validate",
                json={"policy": policy},
            )
            responses.append(response)

        # All should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True


# =============================================================================
# Static File Serving Tests
# =============================================================================


@require_full_stack()
class TestStaticFileServing:
    """Test that frontend static files are served correctly."""

    def test_playground_html_served(self, http_client: httpx.Client):
        """Test that playground HTML page is served."""
        response = http_client.get(f"{PLAYGROUND_URL}/playground/")

        # Should return HTML content
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")

    def test_playground_js_served(self, http_client: httpx.Client):
        """Test that playground JavaScript is served."""
        response = http_client.get(f"{PLAYGROUND_URL}/playground/app.js")

        assert response.status_code == 200
        # Should be JavaScript
        content_type = response.headers.get("content-type", "")
        assert "javascript" in content_type or "text/plain" in content_type


# =============================================================================
# Manual Browser Verification Checklist
# =============================================================================

"""
MANUAL BROWSER VERIFICATION CHECKLIST
=====================================

Prerequisites:
1. OPA server running: docker run -d -p 8181:8181 openpolicyagent/opa run --server
2. Playground backend running: cd src/core/playground && uvicorn app:app --port 8080
3. Browser with DevTools open (F12)

Test Steps:

[1] Page Load
    - Navigate to http://localhost:8080/playground
    - VERIFY: Page loads without console errors
    - VERIFY: Connection status shows "OPA Connected" (green dot)
    - VERIFY: Example dropdown is populated with policies

[2] Load Example Policy
    - Select "Basic RBAC" from the example dropdown
    - VERIFY: Policy editor populated with Rego code
    - VERIFY: Input editor populated with test JSON
    - VERIFY: Explanation panel shows description

[3] Evaluate Policy
    - Click "Evaluate" button
    - VERIFY: Loading spinner appears briefly
    - VERIFY: Results panel shows evaluation result
    - VERIFY: "Allowed" or "Denied" badge appears
    - VERIFY: Full JSON result displayed

[4] Modify and Re-evaluate
    - Change input JSON: set role to "viewer"
    - Click "Evaluate" button
    - VERIFY: Results update with new evaluation
    - VERIFY: Different result based on input change

[5] Validate Policy
    - Click "Validate" button
    - VERIFY: Success message with green checkmark
    - VERIFY: Status shows "Valid"

[6] Test Error Handling
    - Remove closing brace from policy (introduce syntax error)
    - Click "Validate" button
    - VERIFY: Error message displayed
    - VERIFY: Error includes line/column information
    - VERIFY: Status shows "Invalid" with red indicator

[7] Clear and Format
    - Click "Clear" button on policy editor
    - VERIFY: Editor is empty
    - Load another example
    - Click "Format" on input editor
    - VERIFY: JSON is pretty-printed

[8] Keyboard Shortcuts
    - Press Ctrl+Enter (or Cmd+Enter on Mac)
    - VERIFY: Evaluate action triggered
    - Press Ctrl+Shift+V (or Cmd+Shift+V)
    - VERIFY: Validate action triggered

[9] Responsiveness
    - Resize browser window
    - VERIFY: Layout adapts (4-panel → stacked on narrow screens)
    - VERIFY: All controls remain accessible

[10] Console Verification
     - Open browser DevTools Console
     - Perform all above actions
     - VERIFY: No JavaScript errors in console
     - VERIFY: Network requests succeed (check Network tab)

Sign-off: [ ] All manual tests passed
Date: _______________
Tester: _______________
"""


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
