"""
Comprehensive authentication tests for policy check API endpoints.

Tests verify that all policy validation endpoints properly enforce JWT authentication,
handle invalid tokens, and include audit context in responses.
"""

import pytest
from fastapi.testclient import TestClient

# ============================================================================
# Test /api/policy/validate Endpoint Authentication
# ============================================================================


class TestValidatePoliciesAuthentication:
    """Test authentication for POST /api/policy/validate endpoint."""

    def test_validate_without_auth_returns_401(self, test_client: TestClient):
        """Verify validation endpoint rejects requests without authentication."""
        response = test_client.post(
            "/api/policy/validate",
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

    def test_validate_with_malformed_token_returns_401(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify validation endpoint rejects malformed JWT tokens."""
        response = test_client.post(
            "/api/policy/validate",
            headers=malformed_auth_headers,
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

    def test_validate_with_expired_token_returns_401(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify validation endpoint rejects expired JWT tokens."""
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

    def test_validate_with_valid_auth_succeeds(self, test_client: TestClient, auth_headers: dict):
        """Verify validation endpoint accepts valid JWT tokens."""
        response = test_client.post(
            "/api/policy/validate",
            headers=auth_headers,
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
        assert response.status_code == 200
        data = response.json()
        assert "passed" in data
        assert "violations" in data
        assert "summary" in data

    def test_validate_includes_audit_context(self, test_client: TestClient, auth_headers: dict):
        """Verify validation response includes authenticated user audit context."""
        response = test_client.post(
            "/api/policy/validate",
            headers=auth_headers,
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
        assert response.status_code == 200
        data = response.json()

        # Verify audit context is present
        assert "audit_context" in data
        audit_ctx = data["audit_context"]
        assert "user_id" in audit_ctx
        assert "tenant_id" in audit_ctx
        assert "timestamp" in audit_ctx
        assert "request_id" in audit_ctx

        # Verify audit context has expected values from test token
        assert audit_ctx["user_id"] == "test-user-123"
        assert audit_ctx["tenant_id"] == "test-tenant-456"

    def test_validate_with_admin_user(
        self, test_client: TestClient, admin_auth_headers: dict
    ):
        """Verify validation works with admin user credentials."""
        response = test_client.post(
            "/api/policy/validate",
            headers=admin_auth_headers,
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
        assert response.status_code == 200
        data = response.json()

        # Verify admin user audit context
        assert data["audit_context"]["user_id"] == "admin-user-789"
        assert data["audit_context"]["tenant_id"] == "admin-tenant-000"

    def test_validate_with_different_tenants(
        self, test_client: TestClient, auth_headers: dict, admin_auth_headers: dict
    ):
        """Verify different tenants can validate policies with their credentials."""
        # Test user validation
        response1 = test_client.post(
            "/api/policy/validate",
            headers=auth_headers,
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
        assert response1.status_code == 200
        tenant1 = response1.json()["audit_context"]["tenant_id"]

        # Admin user validation
        response2 = test_client.post(
            "/api/policy/validate",
            headers=admin_auth_headers,
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
        assert response2.status_code == 200
        tenant2 = response2.json()["audit_context"]["tenant_id"]

        # Verify tenants are different
        assert tenant1 != tenant2
        assert tenant1 == "test-tenant-456"
        assert tenant2 == "admin-tenant-000"


# ============================================================================
# Test /api/policy/policies Endpoint Authentication
# ============================================================================


class TestListPoliciesAuthentication:
    """Test authentication for GET /api/policy/policies endpoint."""

    def test_list_without_auth_returns_401(self, test_client: TestClient):
        """Verify list policies endpoint rejects requests without authentication."""
        response = test_client.get("/api/policy/policies")
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_list_with_malformed_token_returns_401(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify list policies endpoint rejects malformed JWT tokens."""
        response = test_client.get("/api/policy/policies", headers=malformed_auth_headers)
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_list_with_expired_token_returns_401(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify list policies endpoint rejects expired JWT tokens."""
        response = test_client.get("/api/policy/policies", headers=expired_auth_headers)
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_list_with_valid_auth_succeeds(self, test_client: TestClient, auth_headers: dict):
        """Verify list policies endpoint accepts valid JWT tokens."""
        response = test_client.get("/api/policy/policies", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert "total" in data
        assert isinstance(data["policies"], list)

    def test_list_includes_audit_context(self, test_client: TestClient, auth_headers: dict):
        """Verify list policies response includes authenticated user audit context."""
        response = test_client.get("/api/policy/policies", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Verify audit context is present
        assert "audit_context" in data
        audit_ctx = data["audit_context"]
        assert "user_id" in audit_ctx
        assert "tenant_id" in audit_ctx
        assert "timestamp" in audit_ctx
        assert "request_id" in audit_ctx

        # Verify audit context has expected values from test token
        assert audit_ctx["user_id"] == "test-user-123"
        assert audit_ctx["tenant_id"] == "test-tenant-456"

    def test_list_with_admin_user(self, test_client: TestClient, admin_auth_headers: dict):
        """Verify list policies works with admin user credentials."""
        response = test_client.get("/api/policy/policies", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Verify admin user audit context
        assert data["audit_context"]["user_id"] == "admin-user-789"
        assert data["audit_context"]["tenant_id"] == "admin-tenant-000"

    def test_list_with_resource_type_filter(
        self, test_client: TestClient, auth_headers: dict
    ):
        """Verify list policies with resource_type filter and authentication."""
        response = test_client.get(
            "/api/policy/policies?resource_type=kubernetes", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify policies are filtered
        assert "policies" in data
        # All returned policies should include 'kubernetes' in resource_types
        for policy in data["policies"]:
            assert "kubernetes" in policy["resource_types"]

        # Verify audit context is present
        assert data["audit_context"]["user_id"] == "test-user-123"

    def test_list_with_enabled_only_filter(
        self, test_client: TestClient, auth_headers: dict
    ):
        """Verify list policies with enabled_only filter and authentication."""
        response = test_client.get(
            "/api/policy/policies?enabled_only=true", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify all policies are enabled
        for policy in data["policies"]:
            assert policy["enabled"] is True

        # Verify audit context is present
        assert data["audit_context"]["user_id"] == "test-user-123"


# ============================================================================
# Test /api/policy/policies/{policy_id} Endpoint Authentication
# ============================================================================


class TestGetPolicyAuthentication:
    """Test authentication for GET /api/policy/policies/{policy_id} endpoint."""

    def test_get_without_auth_returns_401(self, test_client: TestClient):
        """Verify get policy endpoint rejects requests without authentication."""
        response = test_client.get("/api/policy/policies/acgs2-security-001")
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_get_with_malformed_token_returns_401(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify get policy endpoint rejects malformed JWT tokens."""
        response = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=malformed_auth_headers
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_get_with_expired_token_returns_401(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify get policy endpoint rejects expired JWT tokens."""
        response = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=expired_auth_headers
        )
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_get_with_valid_auth_succeeds(self, test_client: TestClient, auth_headers: dict):
        """Verify get policy endpoint accepts valid JWT tokens."""
        response = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "policy" in data
        assert data["policy"]["id"] == "acgs2-security-001"

    def test_get_includes_audit_context(self, test_client: TestClient, auth_headers: dict):
        """Verify get policy response includes authenticated user audit context."""
        response = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify audit context is present
        assert "audit_context" in data
        audit_ctx = data["audit_context"]
        assert "user_id" in audit_ctx
        assert "tenant_id" in audit_ctx
        assert "timestamp" in audit_ctx
        assert "request_id" in audit_ctx

        # Verify audit context has expected values from test token
        assert audit_ctx["user_id"] == "test-user-123"
        assert audit_ctx["tenant_id"] == "test-tenant-456"

    def test_get_with_admin_user(self, test_client: TestClient, admin_auth_headers: dict):
        """Verify get policy works with admin user credentials."""
        response = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=admin_auth_headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify admin user audit context
        assert data["audit_context"]["user_id"] == "admin-user-789"
        assert data["audit_context"]["tenant_id"] == "admin-tenant-000"

    def test_get_nonexistent_policy_with_auth_returns_404(
        self, test_client: TestClient, auth_headers: dict
    ):
        """Verify getting non-existent policy with auth returns 404, not 401."""
        response = test_client.get(
            "/api/policy/policies/nonexistent-policy-id", headers=auth_headers
        )
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "Policy not found" in data["detail"]

    def test_get_all_demo_policies_with_auth(
        self, test_client: TestClient, auth_headers: dict
    ):
        """Verify all demo policies can be retrieved with authentication."""
        demo_policy_ids = [
            "acgs2-security-001",
            "acgs2-security-002",
            "acgs2-k8s-001",
            "acgs2-k8s-002",
            "acgs2-terraform-001",
            "acgs2-docker-001",
        ]

        for policy_id in demo_policy_ids:
            response = test_client.get(
                f"/api/policy/policies/{policy_id}", headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["policy"]["id"] == policy_id
            assert data["audit_context"]["user_id"] == "test-user-123"


# ============================================================================
# Test /api/policy/health Endpoint Authentication
# ============================================================================


class TestPolicyHealthAuthentication:
    """Test authentication for GET /api/policy/health endpoint."""

    def test_health_without_auth_returns_401(self, test_client: TestClient):
        """Verify health endpoint rejects requests without authentication."""
        response = test_client.get("/api/policy/health")
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_health_with_malformed_token_returns_401(
        self, test_client: TestClient, malformed_auth_headers: dict
    ):
        """Verify health endpoint rejects malformed JWT tokens."""
        response = test_client.get("/api/policy/health", headers=malformed_auth_headers)
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_health_with_expired_token_returns_401(
        self, test_client: TestClient, expired_auth_headers: dict
    ):
        """Verify health endpoint rejects expired JWT tokens."""
        response = test_client.get("/api/policy/health", headers=expired_auth_headers)
        assert response.status_code == 401
        assert "detail" in response.json()

    def test_health_with_valid_auth_succeeds(self, test_client: TestClient, auth_headers: dict):
        """Verify health endpoint accepts valid JWT tokens."""
        response = test_client.get("/api/policy/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "opa_available" in data
        assert "builtin_policies" in data

    def test_health_includes_audit_context(self, test_client: TestClient, auth_headers: dict):
        """Verify health response includes authenticated user audit context."""
        response = test_client.get("/api/policy/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Verify audit context is present
        assert "audit_context" in data
        audit_ctx = data["audit_context"]
        assert "user_id" in audit_ctx
        assert "tenant_id" in audit_ctx
        assert "timestamp" in audit_ctx
        assert "request_id" in audit_ctx

        # Verify audit context has expected values from test token
        assert audit_ctx["user_id"] == "test-user-123"
        assert audit_ctx["tenant_id"] == "test-tenant-456"

    def test_health_with_admin_user(self, test_client: TestClient, admin_auth_headers: dict):
        """Verify health endpoint works with admin user credentials."""
        response = test_client.get("/api/policy/health", headers=admin_auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Verify admin user audit context
        assert data["audit_context"]["user_id"] == "admin-user-789"
        assert data["audit_context"]["tenant_id"] == "admin-tenant-000"

    def test_health_prevents_reconnaissance_without_auth(self, test_client: TestClient):
        """Verify health endpoint prevents system reconnaissance by requiring auth."""
        # Unauthenticated request should not reveal system information
        response = test_client.get("/api/policy/health")
        assert response.status_code == 401

        # Should not include any system information in error response
        data = response.json()
        assert "opa_available" not in data
        assert "builtin_policies" not in data
        assert "status" not in data or data.get("status") != "healthy"


# ============================================================================
# Cross-Endpoint Authentication Tests
# ============================================================================


class TestCrossEndpointAuthentication:
    """Test authentication scenarios across multiple endpoints."""

    def test_all_endpoints_require_authentication(self, test_client: TestClient):
        """Verify all policy endpoints require authentication."""
        endpoints = [
            ("POST", "/api/policy/validate", {"resources": [{"path": "test.py"}]}),
            ("GET", "/api/policy/policies", None),
            ("GET", "/api/policy/policies/acgs2-security-001", None),
            ("GET", "/api/policy/health", None),
        ]

        for method, url, json_data in endpoints:
            if method == "POST":
                response = test_client.post(url, json=json_data)
            else:
                response = test_client.get(url)

            assert response.status_code == 401, f"{method} {url} should require authentication"
            assert "detail" in response.json()

    def test_same_token_works_across_endpoints(
        self, test_client: TestClient, auth_headers: dict
    ):
        """Verify the same JWT token works across all policy endpoints."""
        # Validate endpoint
        response1 = test_client.post(
            "/api/policy/validate",
            headers=auth_headers,
            json={"resources": [{"path": "test.py", "content": "print('hello')"}]},
        )
        assert response1.status_code == 200

        # List policies endpoint
        response2 = test_client.get("/api/policy/policies", headers=auth_headers)
        assert response2.status_code == 200

        # Get policy endpoint
        response3 = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=auth_headers
        )
        assert response3.status_code == 200

        # Health endpoint
        response4 = test_client.get("/api/policy/health", headers=auth_headers)
        assert response4.status_code == 200

        # Verify all responses have the same user/tenant in audit context
        audit_contexts = [
            response1.json()["audit_context"],
            response2.json()["audit_context"],
            response3.json()["audit_context"],
            response4.json()["audit_context"],
        ]

        for audit_ctx in audit_contexts:
            assert audit_ctx["user_id"] == "test-user-123"
            assert audit_ctx["tenant_id"] == "test-tenant-456"

    def test_tenant_isolation_in_audit_context(
        self,
        test_client: TestClient,
        auth_headers: dict,
        admin_auth_headers: dict,
        limited_auth_headers: dict,
    ):
        """Verify tenant isolation is properly tracked in audit context."""
        headers_list = [
            (auth_headers, "test-user-123", "test-tenant-456"),
            (admin_auth_headers, "admin-user-789", "admin-tenant-000"),
            (limited_auth_headers, "limited-user-999", "limited-tenant-111"),
        ]

        for headers, expected_user, expected_tenant in headers_list:
            response = test_client.get("/api/policy/health", headers=headers)
            assert response.status_code == 200

            audit_ctx = response.json()["audit_context"]
            assert audit_ctx["user_id"] == expected_user
            assert audit_ctx["tenant_id"] == expected_tenant

    def test_invalid_bearer_format_returns_401(self, test_client: TestClient):
        """Verify endpoints reject invalid Bearer token format."""
        invalid_formats = [
            {"Authorization": "token-without-bearer"},
            {"Authorization": "bearer lowercase-bearer"},
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": ""},  # Empty header
        ]

        for headers in invalid_formats:
            response = test_client.get("/api/policy/health", headers=headers)
            assert response.status_code == 401

    def test_missing_authorization_header_returns_401(self, test_client: TestClient):
        """Verify endpoints reject requests with missing Authorization header."""
        # Request with other headers but no Authorization
        headers = {"Content-Type": "application/json"}
        response = test_client.get("/api/policy/health", headers=headers)
        assert response.status_code == 401


# ============================================================================
# Audit Context Validation Tests
# ============================================================================


class TestAuditContextValidation:
    """Test audit context structure and content across endpoints."""

    def test_audit_context_structure(self, test_client: TestClient, auth_headers: dict):
        """Verify audit context has required fields with correct types."""
        response = test_client.get("/api/policy/health", headers=auth_headers)
        assert response.status_code == 200

        audit_ctx = response.json()["audit_context"]

        # Verify required fields exist
        assert "user_id" in audit_ctx
        assert "tenant_id" in audit_ctx
        assert "timestamp" in audit_ctx
        assert "request_id" in audit_ctx

        # Verify field types
        assert isinstance(audit_ctx["user_id"], str)
        assert isinstance(audit_ctx["tenant_id"], str)
        assert isinstance(audit_ctx["timestamp"], str)
        assert isinstance(audit_ctx["request_id"], str)

        # Verify non-empty values
        assert len(audit_ctx["user_id"]) > 0
        assert len(audit_ctx["tenant_id"]) > 0
        assert len(audit_ctx["timestamp"]) > 0
        assert len(audit_ctx["request_id"]) > 0

    def test_request_id_is_unique(self, test_client: TestClient, auth_headers: dict):
        """Verify each request gets a unique request_id in audit context."""
        request_ids = set()

        for _ in range(5):
            response = test_client.get("/api/policy/health", headers=auth_headers)
            assert response.status_code == 200
            request_id = response.json()["audit_context"]["request_id"]
            request_ids.add(request_id)

        # All request IDs should be unique
        assert len(request_ids) == 5

    def test_timestamp_is_valid_iso_format(
        self, test_client: TestClient, auth_headers: dict
    ):
        """Verify audit context timestamp is in valid ISO format."""
        from datetime import datetime

        response = test_client.get("/api/policy/health", headers=auth_headers)
        assert response.status_code == 200

        timestamp = response.json()["audit_context"]["timestamp"]

        # Should be able to parse as ISO format datetime
        try:
            parsed_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            assert parsed_dt is not None
        except ValueError:
            pytest.fail(f"Timestamp {timestamp} is not valid ISO format")
