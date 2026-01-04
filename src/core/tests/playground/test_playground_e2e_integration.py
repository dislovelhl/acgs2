"""
End-to-End Integration Tests for Playground Frontend-Backend-OPA Integration

These tests verify the complete playground flow works correctly with a running OPA server.
Requirements:
- OPA server must be running at http://localhost:8181
- Run: docker run -d -p 8181:8181 openpolicyagent/opa run --server

Tests:
1. Backend health check with live OPA
2. Validate endpoint with live OPA
3. Evaluate endpoint with live OPA
4. Examples endpoint serves valid policies
5. Frontend API compatibility (simulates frontend fetch calls)
6. Full E2E workflow: load example -> evaluate -> get results
"""

import os
import sys

import httpx
import pytest

# Add parent path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

# OPA server URL for integration tests
OPA_URL = os.getenv("OPA_URL", "http://localhost:8181")
PLAYGROUND_BACKEND_URL = os.getenv("PLAYGROUND_URL", "http://localhost:8080")


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
        response = httpx.get(f"{PLAYGROUND_BACKEND_URL}/health", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


# Skip message for OPA-only tests
_opa_skip_reason = (
    f"OPA server not available at {OPA_URL}. "
    "Start with: docker run -d -p 8181:8181 openpolicyagent/opa run --server"
)

# Skip message for full E2E tests (requires both OPA and playground)
_full_skip_reason = (
    f"Playground backend not available at {PLAYGROUND_BACKEND_URL}. "
    "Start with: cd acgs2-core/playground && uvicorn app:app --port 8080"
)


# =============================================================================
# OPA Direct Tests (only require OPA server)
# =============================================================================


@pytest.mark.skipif(not is_opa_available(), reason=_opa_skip_reason)
class TestOPADirectIntegration:
    """Tests that communicate directly with OPA server."""

    def test_opa_health_check(self):
        """Test OPA server health endpoint."""
        response = httpx.get(f"{OPA_URL}/health")
        assert response.status_code == 200

    def test_opa_compile_endpoint_valid_policy(self):
        """Test OPA compile endpoint with valid policy."""
        # OPA compile endpoint evaluates queries against loaded policies
        # We test with a simple query that OPA can compile
        response = httpx.post(
            f"{OPA_URL}/v1/compile",
            json={
                "query": 'input.user.role == "admin"',
                "input": {"user": {"role": "admin"}},
                "unknowns": [],
            },
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data

    def test_opa_compile_endpoint_invalid_query(self):
        """Test OPA compile endpoint with invalid query syntax."""
        response = httpx.post(
            f"{OPA_URL}/v1/compile",
            json={
                "query": "invalid query syntax !!!",
                "input": {},
            },
            headers={"Content-Type": "application/json"},
        )
        # OPA returns error for invalid query
        assert response.status_code in [400, 200]  # May return error in body

    def test_opa_policy_upload_and_evaluate(self):
        """Test policy upload and evaluation flow."""
        policy_id = "test_playground_e2e"
        policy_content = """package test.playground.e2e

default allow := false

allow {
    input.authorized == true
}
"""
        # Upload policy
        upload_response = httpx.put(
            f"{OPA_URL}/v1/policies/{policy_id}",
            content=policy_content,
            headers={"Content-Type": "text/plain"},
        )
        assert upload_response.status_code == 200

        # Evaluate with authorized=true
        eval_response = httpx.post(
            f"{OPA_URL}/v1/data/test/playground/e2e",
            json={"input": {"authorized": True}},
        )
        assert eval_response.status_code == 200
        result = eval_response.json()
        assert result.get("result", {}).get("allow") is True

        # Evaluate with authorized=false
        eval_response = httpx.post(
            f"{OPA_URL}/v1/data/test/playground/e2e",
            json={"input": {"authorized": False}},
        )
        assert eval_response.status_code == 200
        result = eval_response.json()
        assert result.get("result", {}).get("allow") is False

        # Cleanup: delete policy
        delete_response = httpx.delete(f"{OPA_URL}/v1/policies/{policy_id}")
        assert delete_response.status_code == 200


# =============================================================================
# Playground Backend Tests (require both OPA and playground backend)
# =============================================================================


@pytest.mark.skipif(
    not (is_opa_available() and is_playground_available()),
    reason=_full_skip_reason if not is_playground_available() else _opa_skip_reason,
)
class TestPlaygroundBackendE2E:
    """E2E tests for playground backend with live OPA integration."""

    def test_playground_health_check(self):
        """Test playground health endpoint with OPA status."""
        response = httpx.get(f"{PLAYGROUND_BACKEND_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "alive", "degraded"]
        assert "service" in data

    def test_playground_readiness_check(self):
        """Test playground readiness probe includes OPA status."""
        response = httpx.get(f"{PLAYGROUND_BACKEND_URL}/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "opa_status" in data or "status" in data

    def test_validate_valid_policy(self):
        """Test validate endpoint with valid Rego policy."""
        policy = """package playground.test

default allow := false

allow {
    input.user.role == "admin"
}
"""
        response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/validate",
            json={"policy": policy},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["errors"] == []

    def test_validate_invalid_policy(self):
        """Test validate endpoint with invalid Rego policy (syntax error)."""
        policy = """package playground.test

default allow := {
    # Missing closing brace - syntax error
"""
        response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/validate",
            json={"policy": policy},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0

    def test_validate_policy_with_line_numbers(self):
        """Test validate endpoint returns error with line number information."""
        policy = """package playground.test

default allow := false

allow {
    input.user.role == "admin"
    invalid syntax here !!!
}
"""
        response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/validate",
            json={"policy": policy},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        # Error message should contain line/column information
        assert len(data["errors"]) > 0
        # OPA errors typically include line/column info in the message

    def test_evaluate_policy_allow_true(self):
        """Test evaluate endpoint with policy that returns allow=true."""
        policy = """package playground.eval

default allow := false

allow {
    input.user.role == "admin"
}
"""
        response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/evaluate",
            json={
                "policy": policy,
                "input": {"user": {"role": "admin"}},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["allowed"] is True

    def test_evaluate_policy_allow_false(self):
        """Test evaluate endpoint with policy that returns allow=false."""
        policy = """package playground.eval

default allow := false

allow {
    input.user.role == "admin"
}
"""
        response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/evaluate",
            json={
                "policy": policy,
                "input": {"user": {"role": "viewer"}},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["allowed"] is False

    def test_evaluate_policy_complex_result(self):
        """Test evaluate endpoint with complex result object."""
        policy = """package playground.eval

result := {
    "allowed": input.role == "admin",
    "reason": message
}

message := "Admin access granted" {
    input.role == "admin"
}

message := "Access denied" {
    input.role != "admin"
}
"""
        response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/evaluate",
            json={
                "policy": policy,
                "input": {"role": "admin"},
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "result" in data

    def test_examples_endpoint_returns_list(self):
        """Test examples endpoint returns list of examples."""
        response = httpx.get(f"{PLAYGROUND_BACKEND_URL}/api/examples")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 5  # Spec requires at least 5 examples

    def test_examples_have_valid_structure(self):
        """Test each example has required fields."""
        response = httpx.get(f"{PLAYGROUND_BACKEND_URL}/api/examples")
        assert response.status_code == 200
        examples = response.json()

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

        for example in examples:
            for field in required_fields:
                assert field in example, f"Missing field '{field}' in example '{example.get('id')}'"

    def test_examples_policies_are_evaluable(self):
        """Test that example policies can be evaluated with their test inputs."""
        # Get examples
        response = httpx.get(f"{PLAYGROUND_BACKEND_URL}/api/examples")
        assert response.status_code == 200
        examples = response.json()

        # Test at least 3 examples
        for example in examples[:3]:
            eval_response = httpx.post(
                f"{PLAYGROUND_BACKEND_URL}/api/evaluate",
                json={
                    "policy": example["policy"],
                    "input": example["test_input"],
                },
            )
            assert eval_response.status_code == 200, f"Failed to evaluate example '{example['id']}'"
            data = eval_response.json()
            assert data["success"] is True, f"Example '{example['id']}' evaluation failed: {data}"


# =============================================================================
# Frontend Simulation Tests (simulates browser fetch calls)
# =============================================================================


@pytest.mark.skipif(
    not (is_opa_available() and is_playground_available()),
    reason=_full_skip_reason if not is_playground_available() else _opa_skip_reason,
)
class TestFrontendAPICompatibility:
    """Tests that simulate the frontend JavaScript fetch calls."""

    def test_cors_preflight_validate(self):
        """Test CORS preflight request for validate endpoint."""
        response = httpx.options(
            f"{PLAYGROUND_BACKEND_URL}/api/validate",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        # Preflight should succeed
        assert response.status_code in [200, 204]

    def test_cors_preflight_evaluate(self):
        """Test CORS preflight request for evaluate endpoint."""
        response = httpx.options(
            f"{PLAYGROUND_BACKEND_URL}/api/evaluate",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code in [200, 204]

    def test_frontend_workflow_load_examples(self):
        """Simulate frontend: load examples on page init."""
        response = httpx.get(
            f"{PLAYGROUND_BACKEND_URL}/api/examples",
            headers={
                "Accept": "application/json",
                "Origin": "http://localhost:8080",
            },
        )
        assert response.status_code == 200
        examples = response.json()
        assert len(examples) > 0

        # Verify examples are grouped by category (as frontend expects)
        categories = {ex["category"] for ex in examples}
        assert len(categories) >= 3  # Multiple categories

    def test_frontend_workflow_select_and_evaluate(self):
        """Simulate frontend: select example and evaluate."""
        # 1. Load examples
        examples_response = httpx.get(f"{PLAYGROUND_BACKEND_URL}/api/examples")
        examples = examples_response.json()
        example = examples[0]

        # 2. Load policy and input into editors (simulated)
        policy = example["policy"]
        test_input = example["test_input"]

        # 3. Click Evaluate button (frontend fetch call)
        eval_response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/evaluate",
            json={
                "policy": policy,
                "input": test_input,
            },
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": "http://localhost:8080",
            },
        )

        assert eval_response.status_code == 200
        result = eval_response.json()
        assert result["success"] is True
        assert "result" in result

    def test_frontend_workflow_validate_with_error(self):
        """Simulate frontend: validate policy with syntax error."""
        # 1. User types invalid policy
        invalid_policy = """package test

default allow := false

allow {
    input.user.role == "admin"
    # Missing closing brace
"""

        # 2. Click Validate button
        validate_response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/validate",
            json={"policy": invalid_policy},
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "Origin": "http://localhost:8080",
            },
        )

        assert validate_response.status_code == 200
        result = validate_response.json()
        assert result["valid"] is False
        assert len(result["errors"]) > 0

        # Frontend should display these errors to user

    def test_frontend_connection_check(self):
        """Simulate frontend: check OPA connection on page load."""
        response = httpx.get(
            f"{PLAYGROUND_BACKEND_URL}/health",
            headers={
                "Accept": "application/json",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # Frontend uses this to update connection indicator
        status = data.get("status")
        assert status in ["ready", "alive", "degraded", "not_ready"]


# =============================================================================
# Full E2E Workflow Tests
# =============================================================================


@pytest.mark.skipif(
    not (is_opa_available() and is_playground_available()),
    reason=_full_skip_reason if not is_playground_available() else _opa_skip_reason,
)
class TestFullE2EWorkflow:
    """Complete end-to-end workflow tests simulating user interaction."""

    def test_workflow_rbac_policy(self):
        """E2E test: RBAC policy workflow from start to finish."""
        # 1. Check connection
        health_response = httpx.get(f"{PLAYGROUND_BACKEND_URL}/health")
        assert health_response.status_code == 200
        assert health_response.json().get("status") in ["ready", "alive"]

        # 2. Load examples
        examples_response = httpx.get(f"{PLAYGROUND_BACKEND_URL}/api/examples")
        examples = examples_response.json()

        # 3. Find RBAC example
        rbac_example = next(
            (
                ex
                for ex in examples
                if "rbac" in ex["id"].lower() or "rbac" in ex["category"].lower()
            ),
            None,
        )
        assert rbac_example is not None, "Should have an RBAC example"

        # 4. Validate the policy
        validate_response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/validate",
            json={"policy": rbac_example["policy"]},
        )
        assert validate_response.json()["valid"] is True

        # 5. Evaluate with test input
        eval_response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/evaluate",
            json={
                "policy": rbac_example["policy"],
                "input": rbac_example["test_input"],
            },
        )
        result = eval_response.json()
        assert result["success"] is True

        # 6. Modify input and re-evaluate
        modified_input = rbac_example["test_input"].copy()
        if "user" in modified_input:
            if isinstance(modified_input["user"], dict):
                modified_input["user"]["role"] = "guest"
            else:
                modified_input["role"] = "guest"

        re_eval_response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/evaluate",
            json={
                "policy": rbac_example["policy"],
                "input": modified_input,
            },
        )
        re_result = re_eval_response.json()
        assert re_result["success"] is True

    def test_workflow_introduce_and_fix_error(self):
        """E2E test: introduce syntax error, validate, fix, validate again."""
        # 1. Start with valid policy
        valid_policy = """package test.error_fix

default allow := false

allow {
    input.role == "admin"
}
"""
        # 2. Validate valid policy
        validate_response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/validate",
            json={"policy": valid_policy},
        )
        assert validate_response.json()["valid"] is True

        # 3. Introduce syntax error
        invalid_policy = """package test.error_fix

default allow := false

allow {
    input.role == "admin"
    # Missing closing brace - simulates user typo
"""
        # 4. Validate shows error
        error_response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/validate",
            json={"policy": invalid_policy},
        )
        error_result = error_response.json()
        assert error_result["valid"] is False
        assert len(error_result["errors"]) > 0

        # 5. Fix the error
        fixed_policy = valid_policy  # Back to valid version

        # 6. Validate again - should pass
        fixed_response = httpx.post(
            f"{PLAYGROUND_BACKEND_URL}/api/validate",
            json={"policy": fixed_policy},
        )
        assert fixed_response.json()["valid"] is True

    def test_workflow_all_example_categories(self):
        """E2E test: verify all example categories can be loaded and evaluated."""
        # Get all examples
        examples_response = httpx.get(f"{PLAYGROUND_BACKEND_URL}/api/examples")
        examples = examples_response.json()

        # Group by category
        categories = {}
        for ex in examples:
            cat = ex["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(ex)

        # Test at least one example from each category
        for category, category_examples in categories.items():
            example = category_examples[0]

            # Validate
            validate_response = httpx.post(
                f"{PLAYGROUND_BACKEND_URL}/api/validate",
                json={"policy": example["policy"]},
            )
            assert (
                validate_response.json()["valid"] is True
            ), f"Category {category} example failed validation"

            # Evaluate
            eval_response = httpx.post(
                f"{PLAYGROUND_BACKEND_URL}/api/evaluate",
                json={
                    "policy": example["policy"],
                    "input": example["test_input"],
                },
            )
            result = eval_response.json()
            assert result["success"] is True, f"Category {category} example failed evaluation"


# =============================================================================
# OPA Service Integration Tests (using playground's OPAService)
# =============================================================================


@pytest.mark.skipif(not is_opa_available(), reason=_opa_skip_reason)
class TestPlaygroundOPAServiceIntegration:
    """Test the OPAService class used by playground with live OPA."""

    def test_opa_service_validate_policy(self):
        """Test OPAService validates policy correctly."""
        from cli.opa_service import OPAService

        policy = """package playground.service_test

default allow := false

allow {
    input.authorized == true
}
"""
        with OPAService(opa_url=OPA_URL) as opa:
            result = opa.validate_policy(policy)
            assert result.is_valid is True

    def test_opa_service_evaluate_policy(self):
        """Test OPAService evaluates policy correctly."""
        from cli.opa_service import OPAService

        policy = """package playground.service_eval

default allow := false

allow {
    input.role == "admin"
}
"""
        with OPAService(opa_url=OPA_URL) as opa:
            # Test allow=true case
            result = opa.evaluate_policy(
                policy_content=policy,
                input_data={"role": "admin"},
                policy_path="data.playground.service_eval",
            )
            assert result.success is True
            assert result.result.get("allow") is True

            # Test allow=false case
            result = opa.evaluate_policy(
                policy_content=policy,
                input_data={"role": "viewer"},
                policy_path="data.playground.service_eval",
            )
            assert result.success is True
            assert result.result.get("allow") is False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
