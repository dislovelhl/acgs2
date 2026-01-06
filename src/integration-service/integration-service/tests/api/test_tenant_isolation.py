"""
Comprehensive tenant isolation tests for policy check API endpoints.

These tests verify that tenant isolation is properly enforced across all policy
validation endpoints. Users should only be able to access policies appropriate
for their tenant.

Current Implementation Status:
- ✅ Tenant context is captured in audit logs and responses
- ✅ Each request is tracked with the correct tenant_id
- ⚠️  Policy filtering by tenant is not yet implemented (all users see all policies)

Note: Some tests are marked as expected behaviors for future implementation
when tenant-based policy filtering is added to the system.
"""

import pytest
from fastapi.testclient import TestClient

# ============================================================================
# Tenant Context Tracking Tests
# ============================================================================


class TestTenantContextTracking:
    """Verify that tenant context is properly tracked in all requests."""

    def test_different_tenants_have_different_audit_context(
        self,
        test_client: TestClient,
        auth_headers: dict,
        admin_auth_headers: dict,
        limited_auth_headers: dict,
    ):
        """Verify each tenant has its own audit context in responses."""
        # Test user from test-tenant-456
        response1 = test_client.get("/api/policy/health", headers=auth_headers)
        assert response1.status_code == 200
        audit1 = response1.json()["audit_context"]
        assert audit1["user_id"] == "test-user-123"
        assert audit1["tenant_id"] == "test-tenant-456"

        # Admin user from admin-tenant-000
        response2 = test_client.get("/api/policy/health", headers=admin_auth_headers)
        assert response2.status_code == 200
        audit2 = response2.json()["audit_context"]
        assert audit2["user_id"] == "admin-user-789"
        assert audit2["tenant_id"] == "admin-tenant-000"

        # Limited user from limited-tenant-111
        response3 = test_client.get("/api/policy/health", headers=limited_auth_headers)
        assert response3.status_code == 200
        audit3 = response3.json()["audit_context"]
        assert audit3["user_id"] == "limited-user-999"
        assert audit3["tenant_id"] == "limited-tenant-111"

        # Verify all tenants are different
        tenants = {audit1["tenant_id"], audit2["tenant_id"], audit3["tenant_id"]}
        assert len(tenants) == 3, "Each user should have a unique tenant"

    def test_tenant_context_consistent_across_endpoints(
        self,
        test_client: TestClient,
        auth_headers: dict,
    ):
        """Verify the same tenant context is used across all endpoints."""
        expected_user = "test-user-123"
        expected_tenant = "test-tenant-456"

        # Validate endpoint
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
        assert response1.json()["audit_context"]["tenant_id"] == expected_tenant
        assert response1.json()["audit_context"]["user_id"] == expected_user

        # List policies endpoint
        response2 = test_client.get("/api/policy/policies", headers=auth_headers)
        assert response2.status_code == 200
        assert response2.json()["audit_context"]["tenant_id"] == expected_tenant
        assert response2.json()["audit_context"]["user_id"] == expected_user

        # Get policy endpoint
        response3 = test_client.get("/api/policy/policies/acgs2-security-001", headers=auth_headers)
        assert response3.status_code == 200
        assert response3.json()["audit_context"]["tenant_id"] == expected_tenant
        assert response3.json()["audit_context"]["user_id"] == expected_user

        # Health endpoint
        response4 = test_client.get("/api/policy/health", headers=auth_headers)
        assert response4.status_code == 200
        assert response4.json()["audit_context"]["tenant_id"] == expected_tenant
        assert response4.json()["audit_context"]["user_id"] == expected_user


# ============================================================================
# Policy Access Tests - Current Behavior
# ============================================================================


class TestCurrentPolicyAccessBehavior:
    """
    Test current policy access behavior.

    Note: These tests document that the current implementation does NOT
    enforce tenant-based policy filtering. All authenticated users can
    see all policies regardless of tenant.
    """

    def test_all_tenants_see_same_policies_currently(
        self,
        test_client: TestClient,
        auth_headers: dict,
        admin_auth_headers: dict,
        limited_auth_headers: dict,
    ):
        """
        Document that all tenants currently see the same policies.

        This is the CURRENT behavior. In a tenant-isolated system,
        different tenants should see different policies.
        """
        # Get policies for test-tenant-456
        response1 = test_client.get("/api/policy/policies", headers=auth_headers)
        assert response1.status_code == 200
        policies1 = {p["id"] for p in response1.json()["policies"]}

        # Get policies for admin-tenant-000
        response2 = test_client.get("/api/policy/policies", headers=admin_auth_headers)
        assert response2.status_code == 200
        policies2 = {p["id"] for p in response2.json()["policies"]}

        # Get policies for limited-tenant-111
        response3 = test_client.get("/api/policy/policies", headers=limited_auth_headers)
        assert response3.status_code == 200
        policies3 = {p["id"] for p in response3.json()["policies"]}

        # Currently, all tenants see the same policies (6 demo policies)
        assert policies1 == policies2 == policies3
        assert len(policies1) == 6, "All tenants see the same 6 demo policies"

    def test_any_tenant_can_access_any_policy_currently(
        self,
        test_client: TestClient,
        auth_headers: dict,
        admin_auth_headers: dict,
        limited_auth_headers: dict,
    ):
        """
        Document that any tenant can currently access any policy by ID.

        This is the CURRENT behavior. In a tenant-isolated system,
        users should only access policies belonging to their tenant.
        """
        policy_id = "acgs2-security-001"

        # Test tenant can access the policy
        response1 = test_client.get(f"/api/policy/policies/{policy_id}", headers=auth_headers)
        assert response1.status_code == 200
        assert response1.json()["policy"]["id"] == policy_id
        assert response1.json()["audit_context"]["tenant_id"] == "test-tenant-456"

        # Admin tenant can access the same policy
        response2 = test_client.get(f"/api/policy/policies/{policy_id}", headers=admin_auth_headers)
        assert response2.status_code == 200
        assert response2.json()["policy"]["id"] == policy_id
        assert response2.json()["audit_context"]["tenant_id"] == "admin-tenant-000"

        # Limited tenant can access the same policy
        response3 = test_client.get(
            f"/api/policy/policies/{policy_id}", headers=limited_auth_headers
        )
        assert response3.status_code == 200
        assert response3.json()["policy"]["id"] == policy_id
        assert response3.json()["audit_context"]["tenant_id"] == "limited-tenant-111"

    def test_validation_works_for_all_tenants_currently(
        self,
        test_client: TestClient,
        auth_headers: dict,
        admin_auth_headers: dict,
        limited_auth_headers: dict,
    ):
        """
        Document that validation works the same for all tenants.

        This is the CURRENT behavior. In a tenant-isolated system,
        validation might use different policy sets per tenant.
        """
        validation_request = {
            "resources": [
                {
                    "path": "test.py",
                    "type": "code",
                    "content": "password = 'secret123'",  # Will trigger hardcoded secret violation
                }
            ]
        }

        # Test tenant validation
        response1 = test_client.post(
            "/api/policy/validate", headers=auth_headers, json=validation_request
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Admin tenant validation
        response2 = test_client.post(
            "/api/policy/validate", headers=admin_auth_headers, json=validation_request
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # Limited tenant validation
        response3 = test_client.post(
            "/api/policy/validate", headers=limited_auth_headers, json=validation_request
        )
        assert response3.status_code == 200
        data3 = response3.json()

        # All tenants get the same validation results
        assert data1["passed"] == data2["passed"] == data3["passed"]
        assert len(data1["violations"]) == len(data2["violations"]) == len(data3["violations"])

        # But each has their own audit context
        assert data1["audit_context"]["tenant_id"] == "test-tenant-456"
        assert data2["audit_context"]["tenant_id"] == "admin-tenant-000"
        assert data3["audit_context"]["tenant_id"] == "limited-tenant-111"


# ============================================================================
# Expected Tenant Isolation Behavior (For Future Implementation)
# ============================================================================


class TestExpectedTenantIsolationBehavior:
    """
    Tests documenting expected tenant isolation behavior.

    These tests describe how tenant isolation SHOULD work when
    tenant-based policy filtering is implemented. Currently marked
    with documentation to explain the gap.
    """

    def test_tenant_cannot_access_other_tenant_policy_documentation(self):
        """
        Document expected behavior: Users should only access their tenant's policies.

        Expected Future Behavior:
        - Each tenant should have their own set of policies
        - GET /api/policy/policies/{policy_id} should return 404 if policy
          doesn't belong to the requesting tenant
        - Even if a user knows a policy ID from another tenant, they should
          not be able to access it

        Current Behavior:
        - All policies are accessible to all authenticated users
        - No tenant-based filtering is applied

        Implementation Needed:
        - Add tenant_id field to PolicyInfo model
        - Store tenant association with policies in OPA or database
        - Filter policies by tenant_id in list_policies endpoint
        - Verify tenant access in get_policy endpoint
        """
        pass  # Documentation test

    def test_policy_list_should_be_filtered_by_tenant_documentation(self):
        """
        Document expected behavior: Policy lists should be tenant-specific.

        Expected Future Behavior:
        - GET /api/policy/policies should only return policies belonging
          to the requesting user's tenant
        - Different tenants should see different policy lists
        - Policy count should vary by tenant

        Current Behavior:
        - All tenants see the same 6 demo policies
        - No filtering is applied

        Implementation Needed:
        - Add tenant_id to policy storage
        - Filter policies by current_user.tenant_id in list_policies
        - Update DEMO_POLICIES to include tenant_id field
        """
        pass  # Documentation test

    def test_validation_should_use_tenant_policies_documentation(self):
        """
        Document expected behavior: Validation should use tenant-specific policies.

        Expected Future Behavior:
        - POST /api/policy/validate should only evaluate against policies
          belonging to the requesting user's tenant
        - Different tenants might get different validation results for the
          same resource if they have different policies enabled

        Current Behavior:
        - All tenants use the same built-in validation rules
        - Validation results are identical across tenants

        Implementation Needed:
        - Pass tenant_id to evaluate_policies_with_opa
        - Filter OPA policy evaluation by tenant
        - Filter built-in checks by tenant (if tenant-specific)
        """
        pass  # Documentation test


# ============================================================================
# Security Tests - Verify No Unauthorized Access
# ============================================================================


class TestTenantSecurityBoundaries:
    """Verify security boundaries are enforced at the authentication level."""

    def test_unauthenticated_user_cannot_bypass_tenant_isolation(
        self,
        test_client: TestClient,
    ):
        """Verify unauthenticated users cannot access any tenant's policies."""
        # Cannot list policies
        response1 = test_client.get("/api/policy/policies")
        assert response1.status_code == 401

        # Cannot get specific policy
        response2 = test_client.get("/api/policy/policies/acgs2-security-001")
        assert response2.status_code == 401

        # Cannot validate
        response3 = test_client.post(
            "/api/policy/validate",
            json={"resources": [{"path": "test.py", "content": "test"}]},
        )
        assert response3.status_code == 401

        # Cannot check health
        response4 = test_client.get("/api/policy/health")
        assert response4.status_code == 401

    def test_invalid_token_cannot_access_any_tenant(
        self,
        test_client: TestClient,
        malformed_auth_headers: dict,
    ):
        """Verify invalid tokens cannot access any tenant's resources."""
        # Cannot list policies
        response1 = test_client.get("/api/policy/policies", headers=malformed_auth_headers)
        assert response1.status_code == 401

        # Cannot get specific policy
        response2 = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=malformed_auth_headers
        )
        assert response2.status_code == 401

        # Cannot validate
        response3 = test_client.post(
            "/api/policy/validate",
            headers=malformed_auth_headers,
            json={"resources": [{"path": "test.py", "content": "test"}]},
        )
        assert response3.status_code == 401

    def test_expired_token_cannot_access_any_tenant(
        self,
        test_client: TestClient,
        expired_auth_headers: dict,
    ):
        """Verify expired tokens cannot access any tenant's resources."""
        # Cannot list policies
        response1 = test_client.get("/api/policy/policies", headers=expired_auth_headers)
        assert response1.status_code == 401

        # Cannot get specific policy
        response2 = test_client.get(
            "/api/policy/policies/acgs2-security-001", headers=expired_auth_headers
        )
        assert response2.status_code == 401


# ============================================================================
# Audit Trail Tests
# ============================================================================


class TestTenantAuditTrail:
    """Verify tenant information is properly logged for audit purposes."""

    def test_all_requests_log_tenant_context(
        self,
        test_client: TestClient,
        auth_headers: dict,
        admin_auth_headers: dict,
    ):
        """
        Verify tenant context is included in all successful responses.

        This ensures that audit trails can track which tenant made each request,
        even though tenant-based filtering isn't yet implemented.
        """
        endpoints = [
            ("GET", "/api/policy/policies", None),
            ("GET", "/api/policy/policies/acgs2-security-001", None),
            (
                "POST",
                "/api/policy/validate",
                {"resources": [{"path": "test.py", "content": "test"}]},
            ),
            ("GET", "/api/policy/health", None),
        ]

        for method, url, json_data in endpoints:
            # Test with regular user
            if method == "POST":
                response = test_client.post(url, headers=auth_headers, json=json_data)
            else:
                response = test_client.get(url, headers=auth_headers)

            assert response.status_code == 200
            assert "audit_context" in response.json()
            assert response.json()["audit_context"]["tenant_id"] == "test-tenant-456"
            assert response.json()["audit_context"]["user_id"] == "test-user-123"

            # Test with admin user
            if method == "POST":
                response = test_client.post(url, headers=admin_auth_headers, json=json_data)
            else:
                response = test_client.get(url, headers=admin_auth_headers)

            assert response.status_code == 200
            assert "audit_context" in response.json()
            assert response.json()["audit_context"]["tenant_id"] == "admin-tenant-000"
            assert response.json()["audit_context"]["user_id"] == "admin-user-789"

    def test_request_id_unique_per_request_per_tenant(
        self,
        test_client: TestClient,
        auth_headers: dict,
    ):
        """Verify each request gets a unique request_id for audit tracking."""
        request_ids = set()

        # Make 5 requests from the same tenant
        for _ in range(5):
            response = test_client.get("/api/policy/health", headers=auth_headers)
            assert response.status_code == 200
            request_id = response.json()["audit_context"]["request_id"]
            request_ids.add(request_id)

        # All request IDs should be unique
        assert len(request_ids) == 5

    def test_timestamp_recorded_for_each_tenant_request(
        self,
        test_client: TestClient,
        auth_headers: dict,
    ):
        """Verify timestamp is recorded for audit trail."""
        from datetime import datetime

        response = test_client.get("/api/policy/health", headers=auth_headers)
        assert response.status_code == 200

        audit_ctx = response.json()["audit_context"]
        assert "timestamp" in audit_ctx

        # Verify timestamp is valid ISO format
        timestamp = audit_ctx["timestamp"]
        try:
            parsed_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            assert parsed_dt is not None
        except ValueError:
            pytest.fail(f"Timestamp {timestamp} is not valid ISO format")
