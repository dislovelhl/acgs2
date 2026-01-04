"""
Comprehensive tests for expired JWT token handling.

This test suite verifies that all policy validation endpoints properly reject
expired JWT tokens with appropriate error messages and status codes.
"""

from datetime import timedelta

from fastapi.testclient import TestClient


class TestExpiredTokenRejection:
    """Test that all endpoints properly reject expired JWT tokens."""

    def test_validate_endpoint_rejects_expired_token(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify /api/policy/validate rejects expired JWT tokens with 401."""
        response = test_client.post(
            "/api/policy/validate",
            headers=expired_auth_headers,
            json={
                "resources": [
                    {
                        "path": "test.py",
                        "type": "code",
                        "content": "print('hello')",
                    }
                ]
            },
        )
        assert response.status_code == 401
        assert "detail" in response.json()
        # Verify error message indicates authentication failure
        assert "Could not validate credentials" in response.json()["detail"]

    def test_list_policies_endpoint_rejects_expired_token(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify /api/policy/policies rejects expired JWT tokens with 401."""
        response = test_client.get("/api/policy/policies", headers=expired_auth_headers)
        assert response.status_code == 401
        assert "detail" in response.json()
        assert "Could not validate credentials" in response.json()["detail"]

    def test_get_policy_endpoint_rejects_expired_token(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify /api/policy/policies/{id} rejects expired JWT tokens with 401."""
        response = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=expired_auth_headers
        )
        assert response.status_code == 401
        assert "detail" in response.json()
        assert "Could not validate credentials" in response.json()["detail"]

    def test_health_endpoint_rejects_expired_token(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify /api/policy/health rejects expired JWT tokens with 401."""
        response = test_client.get("/api/policy/health", headers=expired_auth_headers)
        assert response.status_code == 401
        assert "detail" in response.json()
        assert "Could not validate credentials" in response.json()["detail"]


class TestExpiredTokenVariations:
    """Test various expired token scenarios."""

    def test_recently_expired_token(self, test_client: TestClient, create_jwt_token):
        """Verify token that expired 1 second ago is rejected."""
        # Create token that expired 1 second ago
        expired_token = create_jwt_token(
            user_id="test-user",
            tenant_id="test-tenant",
            expires_delta=timedelta(seconds=-1),
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_long_expired_token(self, test_client: TestClient, create_jwt_token):
        """Verify token that expired days ago is rejected."""
        # Create token that expired 30 days ago
        expired_token = create_jwt_token(
            user_id="test-user",
            tenant_id="test-tenant",
            expires_delta=timedelta(days=-30),
        )
        headers = {"Authorization": f"Bearer {expired_token}"}

        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401
        assert "Could not validate credentials" in response.json()["detail"]

    def test_expired_token_does_not_leak_system_info(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify expired token error doesn't leak system information."""
        response = test_client.get("/api/policy/health", headers=expired_auth_headers)
        assert response.status_code == 401

        data = response.json()
        # Should only return generic error, not system information
        assert "opa_available" not in data
        assert "builtin_policies" not in data
        assert "status" not in data or data.get("status") != "healthy"
        assert "audit_context" not in data

    def test_expired_token_same_error_as_invalid_token(
        self, test_client: TestClient, expired_auth_headers: dict, malformed_auth_headers: dict
    ):
        """Verify expired and invalid tokens return same generic error."""
        # Get response for expired token
        expired_response = test_client.get("/api/policy/health", headers=expired_auth_headers)

        # Get response for malformed token
        malformed_response = test_client.get(
            "/api/policy/health", headers=malformed_auth_headers
        )

        # Both should return 401
        assert expired_response.status_code == 401
        assert malformed_response.status_code == 401

        # Both should return the same generic error message
        # (to avoid leaking information about token validity vs expiration)
        assert expired_response.json()["detail"] == malformed_response.json()["detail"]


class TestExpiredTokenWithValidData:
    """Test that expired tokens are rejected even with valid request data."""

    def test_expired_token_with_valid_validation_request(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify valid validation data doesn't bypass expired token check."""
        response = test_client.post(
            "/api/policy/validate",
            headers=expired_auth_headers,
            json={
                "resources": [
                    {
                        "path": "main.py",
                        "type": "code",
                        "content": "import os\nprint('valid code')",
                        "metadata": {"language": "python"},
                    }
                ],
                "options": {"severity_threshold": "medium", "fail_fast": False},
            },
        )
        assert response.status_code == 401
        # Should not process the validation at all
        assert "passed" not in response.json()
        assert "violations" not in response.json()

    def test_expired_token_with_valid_policy_id(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify valid policy ID doesn't bypass expired token check."""
        response = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=expired_auth_headers
        )
        assert response.status_code == 401
        # Should not return policy data
        assert "policy" not in response.json()

    def test_expired_token_with_valid_query_params(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify valid query parameters don't bypass expired token check."""
        response = test_client.get(
            "/api/policy/policies?resource_type=kubernetes&enabled_only=true",
            headers=expired_auth_headers,
        )
        assert response.status_code == 401
        # Should not return policy list
        assert "policies" not in response.json()


class TestExpiredTokenCrossEndpoint:
    """Test expired token behavior consistency across all endpoints."""

    def test_expired_token_rejected_by_all_endpoints(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify all policy endpoints consistently reject expired tokens."""
        endpoints = [
            ("POST", "/api/policy/validate", {"resources": [{"path": "test.py"}]}),
            ("GET", "/api/policy/policies", None),
            ("GET", "/api/policy/policies/acgs2-security-001", None),
            ("GET", "/api/policy/health", None),
        ]

        for method, url, json_data in endpoints:
            if method == "POST":
                response = test_client.post(url, headers=expired_auth_headers, json=json_data)
            else:
                response = test_client.get(url, headers=expired_auth_headers)

            # All should return 401
            assert (
                response.status_code == 401
            ), f"{method} {url} should reject expired token with 401"

            # All should have error detail
            assert "detail" in response.json()

            # All should return same generic error message
            assert "Could not validate credentials" in response.json()["detail"]

    def test_expired_token_vs_valid_token_different_behavior(
        self, test_client: TestClient, expired_auth_headers: dict, auth_headers: dict
    ):
        """Verify expired vs valid tokens produce different results."""
        # Expired token should fail
        expired_response = test_client.get("/api/policy/health", headers=expired_auth_headers)
        assert expired_response.status_code == 401

        # Valid token should succeed
        valid_response = test_client.get("/api/policy/health", headers=auth_headers)
        assert valid_response.status_code == 200

        # Valid response should include system information
        assert "status" in valid_response.json()
        assert valid_response.json()["status"] == "healthy"


class TestExpiredTokenSecurityConsiderations:
    """Test security-related aspects of expired token handling."""

    def test_expired_token_no_audit_context_in_error(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify expired token errors don't include audit context."""
        response = test_client.get("/api/policy/health", headers=expired_auth_headers)
        assert response.status_code == 401

        # Error response should not include audit context
        assert "audit_context" not in response.json()

        # Should only include error detail
        assert "detail" in response.json()

    def test_expired_token_prevents_policy_enumeration(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify expired tokens can't be used to enumerate policies."""
        # Try to get list of policies with expired token
        response = test_client.get("/api/policy/policies", headers=expired_auth_headers)
        assert response.status_code == 401

        # Should not return any policy information
        assert "policies" not in response.json()
        assert "total" not in response.json()

    def test_expired_token_prevents_policy_validation(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify expired tokens can't be used to validate policies."""
        response = test_client.post(
            "/api/policy/validate",
            headers=expired_auth_headers,
            json={
                "resources": [
                    {
                        "path": "test.py",
                        "type": "code",
                        "content": "import os; os.system('ls')",  # Potentially sensitive code
                    }
                ]
            },
        )
        assert response.status_code == 401

        # Should not return validation results
        assert "passed" not in response.json()
        assert "violations" not in response.json()
        assert "summary" not in response.json()

    def test_expired_token_prevents_system_reconnaissance(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify expired tokens can't be used for system reconnaissance."""
        response = test_client.get("/api/policy/health", headers=expired_auth_headers)
        assert response.status_code == 401

        data = response.json()
        # Should not reveal system health information
        assert "opa_available" not in data
        assert "builtin_policies" not in data
        assert "opa_url" not in data
        assert "demo_mode" not in data

    def test_multiple_expired_token_requests_consistent(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify multiple requests with expired token are consistently rejected."""
        for _ in range(5):
            response = test_client.get("/api/policy/health", headers=expired_auth_headers)
            assert response.status_code == 401
            assert "Could not validate credentials" in response.json()["detail"]
