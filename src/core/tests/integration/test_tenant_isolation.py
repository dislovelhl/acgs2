"""
Integration Tests: Cross-Tenant Isolation Verification
Constitutional Hash: cdd01ef066bc6cf2

Integration tests that verify:
- Cross-tenant access blocked (Tenant A cannot access Tenant B resources)
- Audit logs scoped correctly (Tenant A can only see their own logs)
- Middleware tenant context isolation
- Kubernetes namespace isolation (mocked)
- require_tenant_scope enforcement
- Concurrent multi-tenant request handling

Test Requirements:
- These tests use in-memory stores for unit-level integration
- For full integration with real Redis/K8s, set appropriate env vars
"""

import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from fastapi import Depends, FastAPI, HTTPException, Request  # noqa: E402, I001
from fastapi.testclient import TestClient  # noqa: E402
from src.core.shared.acgs_logging.audit_logger import (  # noqa: E402
    CONSTITUTIONAL_HASH,
    AuditAction,
    AuditLogConfig,
    AuditQueryParams,
    AuditSeverity,
    TenantAuditLogger,
)
from src.core.shared.security.tenant_context import (  # noqa: E402
    TenantContextConfig,
    TenantContextMiddleware,
    TenantValidationError,
    get_tenant_id,
    require_tenant_scope,
    validate_tenant_id,
)

# ============================================================================
# Test Constants
# ============================================================================

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"
TENANT_C = "tenant-gamma"
UNKNOWN_TENANT = "unknown-tenant"


# ============================================================================
# Mock Resource Storage (simulates database with tenant-scoped data)
# ============================================================================


@dataclass
class MockResource:
    """Mock resource with tenant ownership."""

    id: str
    tenant_id: str
    name: str
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TenantScopedResourceStore:
    """
    In-memory resource store with strict tenant isolation.

    Simulates a database that enforces tenant-scoped access.
    """

    def __init__(self):
        self._resources: Dict[str, Dict[str, MockResource]] = {}

    def create(self, tenant_id: str, resource: MockResource) -> MockResource:
        """Create a resource for a tenant."""
        if tenant_id not in self._resources:
            self._resources[tenant_id] = {}
        self._resources[tenant_id][resource.id] = resource
        return resource

    def get(self, tenant_id: str, resource_id: str) -> Optional[MockResource]:
        """Get a resource by ID within tenant scope."""
        return self._resources.get(tenant_id, {}).get(resource_id)

    def list(self, tenant_id: str) -> List[MockResource]:
        """List all resources for a tenant."""
        return list(self._resources.get(tenant_id, {}).values())

    def delete(self, tenant_id: str, resource_id: str) -> bool:
        """Delete a resource within tenant scope."""
        if tenant_id in self._resources and resource_id in self._resources[tenant_id]:
            del self._resources[tenant_id][resource_id]
            return True
        return False

    def get_by_id_any_tenant(self, resource_id: str) -> Optional[MockResource]:
        """
        Get resource by ID regardless of tenant (for testing cross-tenant access).

        This simulates what would happen if tenant scope wasn't enforced.
        """
        for tenant_resources in self._resources.values():
            if resource_id in tenant_resources:
                return tenant_resources[resource_id]
        return None

    def clear(self):
        """Clear all resources."""
        self._resources.clear()


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def resource_store():
    """Provide a fresh resource store for each test."""
    store = TenantScopedResourceStore()
    yield store
    store.clear()


@pytest.fixture
def audit_logger():
    """Provide a TenantAuditLogger with in-memory store."""
    config = AuditLogConfig(
        use_redis=False,
        audit_enabled=True,
        enable_redaction=True,
        fail_open=True,
    )
    logger = TenantAuditLogger(config=config)
    return logger


@pytest.fixture
def tenant_config():
    """Provide TenantContextConfig for middleware."""
    return TenantContextConfig(
        enabled=True,
        required=True,
        exempt_paths=["/health", "/docs", "/openapi.json"],
        echo_header=True,
    )


def create_test_app(
    resource_store: TenantScopedResourceStore,
    audit_logger: TenantAuditLogger,
    tenant_config: TenantContextConfig,
) -> FastAPI:
    """Create a FastAPI test application with tenant isolation."""
    app = FastAPI()

    # Add tenant context middleware
    app.add_middleware(TenantContextMiddleware, config=tenant_config)

    # Store instances in app state for access in routes
    app.state.resource_store = resource_store
    app.state.audit_logger = audit_logger

    @app.get("/health")
    async def health():
        return {"status": "healthy", "tenant_isolation_enabled": True}

    @app.post("/api/resources")
    async def create_resource(
        request: Request,
        tenant_id: str = Depends(get_tenant_id),
    ):
        """Create a resource (tenant-scoped)."""
        body = await request.json()
        resource = MockResource(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            name=body.get("name", "unnamed"),
            data=body.get("data", {}),
        )
        request.app.state.resource_store.create(tenant_id, resource)

        # Log audit entry
        await request.app.state.audit_logger.log(
            tenant_id=tenant_id,
            action=AuditAction.CREATE,
            resource_type="resource",
            resource_id=resource.id,
            details={"name": resource.name},
        )

        return {
            "id": resource.id,
            "tenant_id": resource.tenant_id,
            "name": resource.name,
        }

    @app.get("/api/resources")
    async def list_resources(
        request: Request,
        tenant_id: str = Depends(get_tenant_id),
    ):
        """List resources (tenant-scoped)."""
        resources = request.app.state.resource_store.list(tenant_id)

        # Log audit entry
        await request.app.state.audit_logger.log(
            tenant_id=tenant_id,
            action=AuditAction.LIST,
            resource_type="resource",
            details={"count": len(resources)},
        )

        return {
            "tenant_id": tenant_id,
            "resources": [
                {"id": r.id, "name": r.name, "tenant_id": r.tenant_id} for r in resources
            ],
        }

    @app.get("/api/resources/{resource_id}")
    async def get_resource(
        request: Request,
        resource_id: str,
        tenant_id: str = Depends(get_tenant_id),
    ):
        """Get a specific resource (enforces tenant scope)."""
        # First check if resource exists at all (for testing)
        resource = request.app.state.resource_store.get(tenant_id, resource_id)

        if not resource:
            # Check if resource exists for another tenant (for cross-tenant test)
            other_resource = request.app.state.resource_store.get_by_id_any_tenant(resource_id)
            if other_resource:
                # Resource exists but belongs to different tenant
                # Log attempted cross-tenant access
                await request.app.state.audit_logger.log(
                    tenant_id=tenant_id,
                    action=AuditAction.ACCESS_DENIED,
                    resource_type="resource",
                    resource_id=resource_id,
                    severity=AuditSeverity.WARNING,
                    outcome="failure",
                    details={
                        "reason": "cross_tenant_access_attempt",
                        "target_tenant": other_resource.tenant_id,
                    },
                )
                # Return 403 Forbidden for cross-tenant access
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Forbidden",
                        "message": "Access denied: resource belongs to a different tenant",
                        "code": "CROSS_TENANT_ACCESS_DENIED",
                        "constitutional_hash": CONSTITUTIONAL_HASH,
                    },
                )

            # Resource not found at all
            raise HTTPException(status_code=404, detail="Resource not found")

        # Log successful access
        await request.app.state.audit_logger.log(
            tenant_id=tenant_id,
            action=AuditAction.READ,
            resource_type="resource",
            resource_id=resource_id,
        )

        return {
            "id": resource.id,
            "tenant_id": resource.tenant_id,
            "name": resource.name,
            "data": resource.data,
        }

    @app.get("/api/audit-logs")
    async def get_audit_logs(
        request: Request,
        tenant_id: str = Depends(get_tenant_id),
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        limit: int = 100,
    ):
        """Get audit logs (tenant-scoped only)."""
        params = AuditQueryParams(
            action=AuditAction(action) if action else None,
            resource_type=resource_type,
            limit=limit,
        )

        result = await request.app.state.audit_logger.query(
            requesting_tenant_id=tenant_id,
            query=params,
        )

        return {
            "tenant_id": tenant_id,
            "total_count": result.total_count,
            "entries": [
                {
                    "id": e.id,
                    "tenant_id": e.tenant_id,
                    "action": e.action,
                    "resource_type": e.resource_type,
                    "resource_id": e.resource_id,
                    "timestamp": e.timestamp,
                }
                for e in result.entries
            ],
            "has_more": result.has_more,
            "constitutional_hash": result.constitutional_hash,
        }

    @app.post("/api/cross-tenant-verify/{target_tenant_id}")
    async def verify_cross_tenant_access(
        target_tenant_id: str,
        tenant_id: str = Depends(get_tenant_id),
    ):
        """
        Test endpoint to verify cross-tenant access prevention.

        This intentionally attempts to access another tenant's scope
        and should always fail.
        """
        # Use require_tenant_scope to enforce tenant boundary
        require_tenant_scope(tenant_id, target_tenant_id)

        # If we reach here, tenant IDs matched (same tenant)
        return {"verified": True, "tenant_id": tenant_id}

    return app


# ============================================================================
# Cross-Tenant Access Prevention Tests
# ============================================================================


class TestCrossTenantAccessPrevention:
    """Integration tests for cross-tenant access prevention."""

    @pytest.mark.integration
    def test_resource_access_blocked_across_tenants(
        self, resource_store, audit_logger, tenant_config
    ):
        """Test that Tenant A cannot access Tenant B's resources."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Tenant A creates a resource
        response = client.post(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_A},
            json={"name": "tenant-a-resource"},
        )
        assert response.status_code == 200
        resource_id = response.json()["id"]

        # Tenant A can access their own resource
        response = client.get(
            f"/api/resources/{resource_id}",
            headers={"X-Tenant-ID": TENANT_A},
        )
        assert response.status_code == 200
        assert response.json()["tenant_id"] == TENANT_A

        # Tenant B cannot access Tenant A's resource
        response = client.get(
            f"/api/resources/{resource_id}",
            headers={"X-Tenant-ID": TENANT_B},
        )
        assert response.status_code == 403
        body = response.json()
        assert body["detail"]["code"] == "CROSS_TENANT_ACCESS_DENIED"
        assert body["detail"]["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.integration
    def test_resource_list_only_shows_tenant_resources(
        self, resource_store, audit_logger, tenant_config
    ):
        """Test that listing resources only shows the requesting tenant's resources."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Create resources for Tenant A
        for i in range(3):
            client.post(
                "/api/resources",
                headers={"X-Tenant-ID": TENANT_A},
                json={"name": f"tenant-a-resource-{i}"},
            )

        # Create resources for Tenant B
        for i in range(5):
            client.post(
                "/api/resources",
                headers={"X-Tenant-ID": TENANT_B},
                json={"name": f"tenant-b-resource-{i}"},
            )

        # Tenant A should only see their 3 resources
        response = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_A},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["resources"]) == 3
        for resource in data["resources"]:
            assert resource["tenant_id"] == TENANT_A

        # Tenant B should only see their 5 resources
        response = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_B},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["resources"]) == 5
        for resource in data["resources"]:
            assert resource["tenant_id"] == TENANT_B

    @pytest.mark.integration
    def test_require_tenant_scope_blocks_cross_access(
        self, resource_store, audit_logger, tenant_config
    ):
        """Test require_tenant_scope function blocks cross-tenant access."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Same tenant - should succeed
        response = client.post(
            f"/api/cross-tenant-verify/{TENANT_A}",
            headers={"X-Tenant-ID": TENANT_A},
        )
        assert response.status_code == 200
        assert response.json()["verified"] is True

        # Different tenant - should fail with 403
        response = client.post(
            f"/api/cross-tenant-verify/{TENANT_B}",
            headers={"X-Tenant-ID": TENANT_A},
        )
        assert response.status_code == 403
        assert "CROSS_TENANT_ACCESS_DENIED" in response.json()["detail"]["code"]

    @pytest.mark.integration
    def test_cross_tenant_access_logged_in_audit(self, resource_store, audit_logger, tenant_config):
        """Test that cross-tenant access attempts are logged."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Tenant A creates a resource
        response = client.post(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_A},
            json={"name": "sensitive-resource"},
        )
        resource_id = response.json()["id"]

        # Tenant B attempts to access it (should fail)
        response = client.get(
            f"/api/resources/{resource_id}",
            headers={"X-Tenant-ID": TENANT_B},
        )
        assert response.status_code == 403

        # Check audit log for the access denial
        response = client.get(
            "/api/audit-logs",
            headers={"X-Tenant-ID": TENANT_B},
            params={"action": "access_denied"},
        )
        assert response.status_code == 200
        data = response.json()

        # Should have at least one access denied entry
        assert data["total_count"] >= 1
        access_denied_entries = [e for e in data["entries"] if e["action"] == "access_denied"]
        assert len(access_denied_entries) >= 1

        # Entry should be for Tenant B (the one who made the request)
        for entry in access_denied_entries:
            assert entry["tenant_id"] == TENANT_B

    @pytest.mark.integration
    def test_multiple_tenants_isolated(self, resource_store, audit_logger, tenant_config):
        """Test isolation between multiple tenants."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        tenants = [TENANT_A, TENANT_B, TENANT_C]
        created_resources: Dict[str, List[str]] = {t: [] for t in tenants}

        # Each tenant creates resources
        for tenant in tenants:
            for i in range(2):
                response = client.post(
                    "/api/resources",
                    headers={"X-Tenant-ID": tenant},
                    json={"name": f"{tenant}-resource-{i}"},
                )
                assert response.status_code == 200
                created_resources[tenant].append(response.json()["id"])

        # Each tenant can only access their own resources
        for tenant in tenants:
            other_tenants = [t for t in tenants if t != tenant]

            # Can access own resources
            for resource_id in created_resources[tenant]:
                response = client.get(
                    f"/api/resources/{resource_id}",
                    headers={"X-Tenant-ID": tenant},
                )
                assert response.status_code == 200

            # Cannot access other tenants' resources
            for other_tenant in other_tenants:
                for resource_id in created_resources[other_tenant]:
                    response = client.get(
                        f"/api/resources/{resource_id}",
                        headers={"X-Tenant-ID": tenant},
                    )
                    assert response.status_code == 403


# ============================================================================
# Audit Log Tenant Scoping Tests
# ============================================================================


class TestAuditLogTenantScoping:
    """Integration tests for tenant-scoped audit logs."""

    @pytest.mark.integration
    def test_audit_logs_only_show_own_tenant_entries(
        self, resource_store, audit_logger, tenant_config
    ):
        """Test that audit log queries only return the requesting tenant's entries."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Tenant A performs actions
        client.post(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_A},
            json={"name": "tenant-a-resource"},
        )

        # Tenant B performs actions
        client.post(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_B},
            json={"name": "tenant-b-resource"},
        )

        # Tenant A can only see their audit logs
        response = client.get(
            "/api/audit-logs",
            headers={"X-Tenant-ID": TENANT_A},
        )
        assert response.status_code == 200
        data = response.json()

        # All entries should belong to Tenant A
        assert data["tenant_id"] == TENANT_A
        for entry in data["entries"]:
            assert entry["tenant_id"] == TENANT_A

        # Tenant B can only see their audit logs
        response = client.get(
            "/api/audit-logs",
            headers={"X-Tenant-ID": TENANT_B},
        )
        assert response.status_code == 200
        data = response.json()

        # All entries should belong to Tenant B
        assert data["tenant_id"] == TENANT_B
        for entry in data["entries"]:
            assert entry["tenant_id"] == TENANT_B

    @pytest.mark.integration
    def test_audit_log_cannot_query_other_tenant(self, resource_store, audit_logger, tenant_config):
        """Test that audit log API enforces tenant scope."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Tenant A creates resources
        for i in range(5):
            client.post(
                "/api/resources",
                headers={"X-Tenant-ID": TENANT_A},
                json={"name": f"resource-{i}"},
            )

        # Tenant B queries - should see zero entries (no access to Tenant A's logs)
        response = client.get(
            "/api/audit-logs",
            headers={"X-Tenant-ID": TENANT_B},
        )
        assert response.status_code == 200
        data = response.json()

        # Tenant B should have no entries (they haven't done anything yet)
        # All entries belong to Tenant B (empty in this case)
        for entry in data["entries"]:
            assert entry["tenant_id"] == TENANT_B

        # Tenant A's entries are NOT visible to Tenant B
        tenant_a_entries = [e for e in data["entries"] if e["tenant_id"] == TENANT_A]
        assert len(tenant_a_entries) == 0

    @pytest.mark.integration
    def test_audit_log_filter_respects_tenant_scope(
        self, resource_store, audit_logger, tenant_config
    ):
        """Test that audit log filters work within tenant scope."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Tenant A creates resources
        for i in range(3):
            client.post(
                "/api/resources",
                headers={"X-Tenant-ID": TENANT_A},
                json={"name": f"resource-{i}"},
            )

        # Tenant A reads a resource
        client.get(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_A},
        )

        # Query with filter
        response = client.get(
            "/api/audit-logs",
            headers={"X-Tenant-ID": TENANT_A},
            params={"action": "create"},
        )
        assert response.status_code == 200
        data = response.json()

        # Should only see create actions for Tenant A
        for entry in data["entries"]:
            assert entry["tenant_id"] == TENANT_A
            assert entry["action"] == "create"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_audit_logger_direct_query_isolation(self, audit_logger):
        """Test TenantAuditLogger.query() method enforces tenant scope."""
        # Log entries for different tenants
        await audit_logger.log(
            tenant_id=TENANT_A,
            action=AuditAction.CREATE,
            resource_type="policy",
            resource_id="policy-1",
        )

        await audit_logger.log(
            tenant_id=TENANT_B,
            action=AuditAction.CREATE,
            resource_type="policy",
            resource_id="policy-2",
        )

        # Query as Tenant A
        result_a = await audit_logger.query(requesting_tenant_id=TENANT_A)
        assert result_a.tenant_id == TENANT_A
        for entry in result_a.entries:
            assert entry.tenant_id == TENANT_A

        # Query as Tenant B
        result_b = await audit_logger.query(requesting_tenant_id=TENANT_B)
        assert result_b.tenant_id == TENANT_B
        for entry in result_b.entries:
            assert entry.tenant_id == TENANT_B

        # Tenant A cannot see Tenant B's entries
        tenant_b_entries_in_a = [e for e in result_a.entries if e.tenant_id == TENANT_B]
        assert len(tenant_b_entries_in_a) == 0


# ============================================================================
# Middleware Tenant Context Tests
# ============================================================================


class TestMiddlewareTenantContext:
    """Integration tests for tenant context middleware."""

    @pytest.mark.integration
    def test_missing_tenant_id_returns_400(self, resource_store, audit_logger, tenant_config):
        """Test requests without X-Tenant-ID return 400."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        response = client.get("/api/resources")
        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "MISSING_TENANT_ID"

    @pytest.mark.integration
    def test_invalid_tenant_id_returns_400(self, resource_store, audit_logger, tenant_config):
        """Test requests with invalid X-Tenant-ID return 400."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Invalid characters
        response = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": "tenant<script>alert(1)</script>"},
        )
        assert response.status_code == 400
        body = response.json()
        assert body["code"] == "INVALID_TENANT_ID"

        # Path traversal attempt
        response = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": "../../../etc/passwd"},
        )
        assert response.status_code == 400

    @pytest.mark.integration
    def test_exempt_paths_accessible_without_tenant(
        self, resource_store, audit_logger, tenant_config
    ):
        """Test exempt paths don't require tenant ID."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Health endpoint should work without tenant ID
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["tenant_isolation_enabled"] is True

    @pytest.mark.integration
    def test_tenant_id_echoed_in_response(self, resource_store, audit_logger, tenant_config):
        """Test X-Tenant-ID is echoed back in response headers."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        response = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_A},
        )
        assert response.status_code == 200
        assert response.headers.get("X-Tenant-ID") == TENANT_A


# ============================================================================
# Concurrent Multi-Tenant Tests
# ============================================================================


class TestConcurrentMultiTenant:
    """Integration tests for concurrent multi-tenant handling."""

    @pytest.mark.integration
    def test_sequential_requests_maintain_isolation(
        self, resource_store, audit_logger, tenant_config
    ):
        """Test sequential requests from different tenants maintain isolation."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Interleave operations from different tenants
        operations = [
            (TENANT_A, "create", {"name": "a-1"}),
            (TENANT_B, "create", {"name": "b-1"}),
            (TENANT_A, "list", None),
            (TENANT_B, "list", None),
            (TENANT_A, "create", {"name": "a-2"}),
            (TENANT_B, "create", {"name": "b-2"}),
        ]

        for tenant, op, data in operations:
            if op == "create":
                response = client.post(
                    "/api/resources",
                    headers={"X-Tenant-ID": tenant},
                    json=data,
                )
                assert response.status_code == 200
                assert response.json()["tenant_id"] == tenant
            elif op == "list":
                response = client.get(
                    "/api/resources",
                    headers={"X-Tenant-ID": tenant},
                )
                assert response.status_code == 200
                for r in response.json()["resources"]:
                    assert r["tenant_id"] == tenant

        # Final verification - each tenant sees only their resources
        response_a = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_A},
        )
        response_b = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_B},
        )

        assert len(response_a.json()["resources"]) == 2
        assert len(response_b.json()["resources"]) == 2


# ============================================================================
# Kubernetes Namespace Isolation Tests (Mocked)
# ============================================================================


class TestKubernetesNamespaceIsolation:
    """Integration tests for Kubernetes namespace isolation (mocked)."""

    @pytest.mark.integration
    def test_namespace_naming_convention(self):
        """Test namespace naming follows tenant convention."""
        from src.core.shared.infrastructure.k8s_manager import K8sConfig, K8sResourceManager

        config = K8sConfig(namespace_prefix="tenant-")
        manager = K8sResourceManager(config=config)

        # Verify namespace naming
        assert manager._get_namespace_name("alpha") == "tenant-alpha"
        assert manager._get_namespace_name("beta-corp") == "tenant-beta-corp"
        assert manager._get_namespace_name("test123") == "tenant-test123"

    @pytest.mark.integration
    def test_namespace_isolation_concept(self):
        """Test the concept of namespace-based isolation."""
        from src.core.shared.infrastructure.k8s_manager import K8sConfig

        config = K8sConfig(
            namespace_prefix="tenant-",
            default_cpu_quota="2",
            default_memory_quota="4Gi",
        )

        # Each tenant gets their own namespace
        tenant_a_namespace = f"{config.namespace_prefix}{TENANT_A}"
        tenant_b_namespace = f"{config.namespace_prefix}{TENANT_B}"

        # Namespaces are different
        assert tenant_a_namespace != tenant_b_namespace
        assert tenant_a_namespace == f"tenant-{TENANT_A}"
        assert tenant_b_namespace == f"tenant-{TENANT_B}"


# ============================================================================
# Constitutional Compliance Tests
# ============================================================================


class TestConstitutionalCompliance:
    """Test constitutional hash compliance in tenant isolation."""

    @pytest.mark.integration
    def test_constitutional_hash_in_access_denied_response(
        self, resource_store, audit_logger, tenant_config
    ):
        """Test 403 response includes constitutional hash."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Create resource as Tenant A
        response = client.post(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_A},
            json={"name": "protected-resource"},
        )
        resource_id = response.json()["id"]

        # Tenant B tries to access it
        response = client.get(
            f"/api/resources/{resource_id}",
            headers={"X-Tenant-ID": TENANT_B},
        )
        assert response.status_code == 403
        assert response.json()["detail"]["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.integration
    def test_constitutional_hash_in_audit_log_response(
        self, resource_store, audit_logger, tenant_config
    ):
        """Test audit log response includes constitutional hash."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        # Create some activity
        client.post(
            "/api/resources",
            headers={"X-Tenant-ID": TENANT_A},
            json={"name": "test-resource"},
        )

        # Query audit logs
        response = client.get(
            "/api/audit-logs",
            headers={"X-Tenant-ID": TENANT_A},
        )
        assert response.status_code == 200
        assert response.json()["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.integration
    def test_constitutional_hash_consistent(self):
        """Test constitutional hash is consistent across components."""
        from src.core.shared.acgs_logging.audit_logger import CONSTITUTIONAL_HASH as AUDIT_HASH
        from src.core.shared.security.tenant_context import CONSTITUTIONAL_HASH as TENANT_HASH

        assert AUDIT_HASH == "cdd01ef066bc6cf2"
        assert TENANT_HASH == "cdd01ef066bc6cf2"
        assert AUDIT_HASH == TENANT_HASH


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================


class TestEdgeCasesAndErrors:
    """Test edge cases and error handling in tenant isolation."""

    @pytest.mark.integration
    def test_empty_tenant_id_rejected(self, resource_store, audit_logger, tenant_config):
        """Test empty tenant ID is rejected."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        response = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": ""},
        )
        assert response.status_code == 400

    @pytest.mark.integration
    def test_whitespace_only_tenant_id_rejected(self, resource_store, audit_logger, tenant_config):
        """Test whitespace-only tenant ID is rejected."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        response = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": "   "},
        )
        assert response.status_code == 400

    @pytest.mark.integration
    def test_very_long_tenant_id_rejected(self, resource_store, audit_logger, tenant_config):
        """Test very long tenant ID is rejected."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        long_tenant_id = "a" * 100  # Exceeds max length of 64
        response = client.get(
            "/api/resources",
            headers={"X-Tenant-ID": long_tenant_id},
        )
        assert response.status_code == 400

    @pytest.mark.integration
    def test_sql_injection_tenant_id_rejected(self, resource_store, audit_logger, tenant_config):
        """Test SQL injection attempt in tenant ID is rejected."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        injection_attempts = [
            "tenant'; DROP TABLE users; --",
            "tenant' OR '1'='1",
            'tenant"; DELETE FROM audit;--',
        ]

        for attempt in injection_attempts:
            response = client.get(
                "/api/resources",
                headers={"X-Tenant-ID": attempt},
            )
            assert response.status_code == 400

    @pytest.mark.integration
    def test_nonexistent_resource_returns_404(self, resource_store, audit_logger, tenant_config):
        """Test accessing nonexistent resource returns 404, not 403."""
        app = create_test_app(resource_store, audit_logger, tenant_config)
        client = TestClient(app)

        fake_id = str(uuid.uuid4())
        response = client.get(
            f"/api/resources/{fake_id}",
            headers={"X-Tenant-ID": TENANT_A},
        )
        # Should be 404, not 403 (resource doesn't exist at all)
        assert response.status_code == 404


# ============================================================================
# Tenant Validation Unit Tests
# ============================================================================


class TestTenantValidation:
    """Unit tests for tenant ID validation functions."""

    @pytest.mark.integration
    def test_valid_tenant_ids(self):
        """Test valid tenant IDs pass validation."""
        valid_ids = [
            "a",
            "ab",
            "tenant-1",
            "my-tenant-123",
            "UPPERCASE",
            "mixed_Case123",
            "tenant_with_underscore",
        ]

        for tenant_id in valid_ids:
            assert validate_tenant_id(tenant_id) is True

    @pytest.mark.integration
    def test_invalid_tenant_ids(self):
        """Test invalid tenant IDs fail validation."""
        invalid_ids = [
            "",  # Empty
            " ",  # Whitespace
            "-tenant",  # Starts with hyphen
            "tenant-",  # Ends with hyphen
            "_tenant",  # Starts with underscore
            "tenant_",  # Ends with underscore
            "a" * 65,  # Too long
            "tenant/id",  # Contains slash
            "tenant\\id",  # Contains backslash
            "../etc/passwd",  # Path traversal
            "tenant<script>",  # XSS attempt
            "tenant;drop",  # SQL injection
        ]

        for tenant_id in invalid_ids:
            with pytest.raises(TenantValidationError):
                validate_tenant_id(tenant_id)


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
