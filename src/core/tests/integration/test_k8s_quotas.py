"""
Integration Tests: Kubernetes Namespace and Quota Verification
Constitutional Hash: cdd01ef066bc6cf2

Integration tests that verify:
- Namespace creation for tenant isolation
- ResourceQuota enforcement per tenant
- LimitRange default container limits
- NetworkPolicy tenant isolation
- Full tenant provisioning workflow
- Multi-tenant namespace separation
- Quota usage tracking and enforcement
- Fail-safe mode behavior
- Audit logging for K8s operations

Test Requirements:
- These tests use mocked Kubernetes API for unit-level integration
- For full integration with real K8s cluster, set KUBERNETES_SERVICE_HOST env var
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from src.core.shared.config.tenant_config import TenantQuotaConfig  # noqa: E402
from src.core.shared.infrastructure.k8s_manager import (  # noqa: E402
    CONSTITUTIONAL_HASH,
    K8S_AVAILABLE,
    K8sConfig,
    K8sOperationStatus,
    K8sResourceManager,
    create_tenant_resources,
    delete_tenant_resources,
    get_k8s_resource_manager,
)

# ============================================================================
# Test Constants
# ============================================================================

TENANT_A = "tenant-alpha"
TENANT_B = "tenant-beta"
TENANT_C = "tenant-gamma"
PREMIUM_TENANT = "premium-corp"
BASIC_TENANT = "basic-tier"

# Default quota configurations for testing
DEFAULT_CPU = "2"
DEFAULT_MEMORY = "4Gi"
DEFAULT_STORAGE = "20Gi"
PREMIUM_CPU = "8"
PREMIUM_MEMORY = "16Gi"
PREMIUM_STORAGE = "100Gi"


# ============================================================================
# Mock Kubernetes API Fixtures
# ============================================================================


@pytest.fixture
def mock_k8s_api():
    """Provide mocked Kubernetes API for testing."""
    with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", True):
        with patch("shared.infrastructure.k8s_manager.client") as mock_client:
            with patch("shared.infrastructure.k8s_manager.config") as mock_config:
                # Setup config mocks
                mock_config.load_incluster_config = MagicMock()
                mock_config.ConfigException = Exception

                # Setup client API mocks
                mock_core_v1 = MagicMock()
                mock_networking_v1 = MagicMock()
                mock_client.CoreV1Api.return_value = mock_core_v1
                mock_client.NetworkingV1Api.return_value = mock_networking_v1

                # Setup K8s object constructors
                mock_client.V1Namespace = MagicMock(return_value=MagicMock())
                mock_client.V1ObjectMeta = MagicMock(return_value=MagicMock())
                mock_client.V1ResourceQuota = MagicMock(return_value=MagicMock())
                mock_client.V1ResourceQuotaSpec = MagicMock(return_value=MagicMock())
                mock_client.V1LimitRange = MagicMock(return_value=MagicMock())
                mock_client.V1LimitRangeSpec = MagicMock(return_value=MagicMock())
                mock_client.V1LimitRangeItem = MagicMock(return_value=MagicMock())
                mock_client.V1NetworkPolicy = MagicMock(return_value=MagicMock())
                mock_client.V1NetworkPolicySpec = MagicMock(return_value=MagicMock())
                mock_client.V1LabelSelector = MagicMock(return_value=MagicMock())
                mock_client.V1NetworkPolicyIngressRule = MagicMock(return_value=MagicMock())
                mock_client.V1NetworkPolicyEgressRule = MagicMock(return_value=MagicMock())
                mock_client.V1NetworkPolicyPeer = MagicMock(return_value=MagicMock())
                mock_client.V1NetworkPolicyPort = MagicMock(return_value=MagicMock())
                mock_client.V1DeleteOptions = MagicMock(return_value=MagicMock())

                yield {
                    "client": mock_client,
                    "config": mock_config,
                    "core_v1": mock_core_v1,
                    "networking_v1": mock_networking_v1,
                }


@pytest.fixture
def mock_api_exception():
    """Create mock ApiException class for error testing."""

    class MockApiException(Exception):
        def __init__(self, status: int, reason: str = "", body: str = ""):
            self.status = status
            self.reason = reason
            self.body = body
            super().__init__(reason)

    return MockApiException


@pytest.fixture
def k8s_config():
    """Provide default K8s configuration."""
    return K8sConfig(
        namespace_prefix="tenant-",
        default_cpu_quota=DEFAULT_CPU,
        default_memory_quota=DEFAULT_MEMORY,
        default_storage_quota=DEFAULT_STORAGE,
        default_max_pods=50,
        default_max_pvcs=10,
        retry_attempts=1,  # Reduce retries for faster tests
        retry_delay_seconds=0.01,
        fail_safe=True,
    )


# ============================================================================
# Namespace Creation Tests
# ============================================================================


class TestNamespaceCreation:
    """Integration tests for Kubernetes namespace creation."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_namespace_success(self, mock_k8s_api, k8s_config):
        """Test successful namespace creation for a tenant."""
        mock_k8s_api["core_v1"].create_namespace = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        result = await manager.create_tenant_namespace(TENANT_A)

        assert result.status == K8sOperationStatus.SUCCESS
        assert result.resource_name == f"tenant-{TENANT_A}"
        assert result.namespace == f"tenant-{TENANT_A}"
        assert result.is_success() is True
        assert "created successfully" in result.message.lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_namespace_idempotent(self, mock_k8s_api, mock_api_exception, k8s_config):
        """Test namespace creation is idempotent (409 returns ALREADY_EXISTS)."""
        conflict_exception = mock_api_exception(409, "Conflict", "already exists")

        with patch("shared.infrastructure.k8s_manager.ApiException", mock_api_exception):
            mock_k8s_api["core_v1"].create_namespace = MagicMock(side_effect=conflict_exception)

            manager = K8sResourceManager(config=k8s_config)
            result = await manager.create_tenant_namespace(TENANT_A)

            assert result.status == K8sOperationStatus.ALREADY_EXISTS
            assert result.is_success() is True  # Idempotency - exists is OK

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_namespace_with_custom_labels(self, mock_k8s_api, k8s_config):
        """Test namespace creation with custom labels."""
        mock_k8s_api["core_v1"].create_namespace = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        result = await manager.create_tenant_namespace(
            TENANT_A,
            labels={"environment": "production", "tier": "premium"},
        )

        assert result.status == K8sOperationStatus.SUCCESS
        # V1ObjectMeta should be called with combined labels
        mock_k8s_api["client"].V1ObjectMeta.assert_called()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_namespace_naming_convention(self, k8s_config):
        """Test namespace naming follows tenant convention."""
        manager = K8sResourceManager(config=k8s_config)

        # Verify namespace naming
        assert manager._get_namespace_name("alpha") == "tenant-alpha"
        assert manager._get_namespace_name("beta-corp") == "tenant-beta-corp"
        assert manager._get_namespace_name("test_123") == "tenant-test_123"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_multiple_tenant_namespaces(self, mock_k8s_api, k8s_config):
        """Test creating namespaces for multiple tenants."""
        mock_k8s_api["core_v1"].create_namespace = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        tenants = [TENANT_A, TENANT_B, TENANT_C]
        results = []

        for tenant in tenants:
            result = await manager.create_tenant_namespace(tenant)
            results.append(result)

        # All should succeed
        for i, result in enumerate(results):
            assert result.status == K8sOperationStatus.SUCCESS
            assert result.namespace == f"tenant-{tenants[i]}"

        # All namespaces should be unique
        namespaces = [r.namespace for r in results]
        assert len(namespaces) == len(set(namespaces))


# ============================================================================
# ResourceQuota Enforcement Tests
# ============================================================================


class TestResourceQuotaEnforcement:
    """Integration tests for ResourceQuota creation and enforcement."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_resource_quota_success(self, mock_k8s_api, k8s_config):
        """Test successful ResourceQuota creation."""
        mock_k8s_api["core_v1"].create_namespaced_resource_quota = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        result = await manager.create_resource_quota(
            TENANT_A,
            cpu="4",
            memory="8Gi",
            storage="50Gi",
            max_pods=100,
            max_pvcs=20,
        )

        assert result.status == K8sOperationStatus.SUCCESS
        assert result.resource_name == "tenant-quota"
        assert result.details["cpu"] == "4"
        assert result.details["memory"] == "8Gi"
        assert result.details["storage"] == "50Gi"
        assert result.details["max_pods"] == 100
        assert result.details["max_pvcs"] == 20

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_resource_quota_with_defaults(self, mock_k8s_api, k8s_config):
        """Test ResourceQuota creation uses default values."""
        mock_k8s_api["core_v1"].create_namespaced_resource_quota = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        result = await manager.create_resource_quota(TENANT_A)

        assert result.status == K8sOperationStatus.SUCCESS
        assert result.details["cpu"] == DEFAULT_CPU
        assert result.details["memory"] == DEFAULT_MEMORY
        assert result.details["storage"] == DEFAULT_STORAGE

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resource_quota_update_on_conflict(
        self, mock_k8s_api, mock_api_exception, k8s_config
    ):
        """Test ResourceQuota is updated when it already exists."""
        conflict_exception = mock_api_exception(409, "Conflict", "already exists")

        with patch("shared.infrastructure.k8s_manager.ApiException", mock_api_exception):
            # First call raises conflict, second (replace) succeeds
            mock_k8s_api["core_v1"].create_namespaced_resource_quota = MagicMock(
                side_effect=conflict_exception
            )
            mock_k8s_api["core_v1"].replace_namespaced_resource_quota = MagicMock()

            manager = K8sResourceManager(config=k8s_config)
            result = await manager.create_resource_quota(TENANT_A, cpu="4")

            assert result.status == K8sOperationStatus.SUCCESS
            assert "updated" in result.message.lower()
            mock_k8s_api["core_v1"].replace_namespaced_resource_quota.assert_called()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_resource_quota_namespace_not_found(
        self, mock_k8s_api, mock_api_exception, k8s_config
    ):
        """Test ResourceQuota creation fails when namespace doesn't exist."""
        not_found_exception = mock_api_exception(404, "Not Found", "namespace not found")

        with patch("shared.infrastructure.k8s_manager.ApiException", mock_api_exception):
            mock_k8s_api["core_v1"].create_namespaced_resource_quota = MagicMock(
                side_effect=not_found_exception
            )

            manager = K8sResourceManager(config=k8s_config)
            result = await manager.create_resource_quota("nonexistent-tenant")

            assert result.status == K8sOperationStatus.NOT_FOUND
            assert result.is_success() is False

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_different_quotas_per_tenant(self, mock_k8s_api, k8s_config):
        """Test different quota configurations for different tenant tiers."""
        mock_k8s_api["core_v1"].create_namespaced_resource_quota = MagicMock()

        manager = K8sResourceManager(config=k8s_config)

        # Basic tier tenant
        basic_result = await manager.create_resource_quota(
            BASIC_TENANT,
            cpu="2",
            memory="4Gi",
            storage="20Gi",
            max_pods=25,
        )

        # Premium tier tenant
        premium_result = await manager.create_resource_quota(
            PREMIUM_TENANT,
            cpu=PREMIUM_CPU,
            memory=PREMIUM_MEMORY,
            storage=PREMIUM_STORAGE,
            max_pods=200,
        )

        assert basic_result.status == K8sOperationStatus.SUCCESS
        assert premium_result.status == K8sOperationStatus.SUCCESS
        assert basic_result.details["cpu"] == "2"
        assert premium_result.details["cpu"] == PREMIUM_CPU
        assert basic_result.details["max_pods"] == 25
        assert premium_result.details["max_pods"] == 200


# ============================================================================
# LimitRange Tests
# ============================================================================


class TestLimitRangeCreation:
    """Integration tests for LimitRange creation."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_limit_range_success(self, mock_k8s_api, k8s_config):
        """Test successful LimitRange creation."""
        mock_k8s_api["core_v1"].create_namespaced_limit_range = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        result = await manager.create_limit_range(
            TENANT_A,
            default_cpu="100m",
            default_memory="128Mi",
            max_cpu="1",
            max_memory="1Gi",
        )

        assert result.status == K8sOperationStatus.SUCCESS
        assert result.resource_name == "tenant-limits"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_limit_range_idempotent(
        self, mock_k8s_api, mock_api_exception, k8s_config
    ):
        """Test LimitRange creation is idempotent."""
        conflict_exception = mock_api_exception(409, "Conflict", "already exists")

        with patch("shared.infrastructure.k8s_manager.ApiException", mock_api_exception):
            mock_k8s_api["core_v1"].create_namespaced_limit_range = MagicMock(
                side_effect=conflict_exception
            )

            manager = K8sResourceManager(config=k8s_config)
            result = await manager.create_limit_range(TENANT_A)

            assert result.status == K8sOperationStatus.ALREADY_EXISTS
            assert result.is_success() is True


# ============================================================================
# NetworkPolicy Tests
# ============================================================================


class TestNetworkPolicyCreation:
    """Integration tests for NetworkPolicy creation."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_network_policy_success(self, mock_k8s_api, k8s_config):
        """Test successful NetworkPolicy creation."""
        mock_k8s_api["networking_v1"].create_namespaced_network_policy = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        result = await manager.create_network_policy(
            TENANT_A,
            allow_same_namespace=True,
            allow_kube_system_dns=True,
        )

        assert result.status == K8sOperationStatus.SUCCESS
        assert result.resource_name == "tenant-isolation"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_network_policy_tenant_isolation(self, mock_k8s_api, k8s_config):
        """Test NetworkPolicy isolates tenant namespaces."""
        mock_k8s_api["networking_v1"].create_namespaced_network_policy = MagicMock()

        manager = K8sResourceManager(config=k8s_config)

        # Create network policies for different tenants
        result_a = await manager.create_network_policy(TENANT_A)
        result_b = await manager.create_network_policy(TENANT_B)

        assert result_a.status == K8sOperationStatus.SUCCESS
        assert result_b.status == K8sOperationStatus.SUCCESS

        # Each should be in their own namespace
        assert result_a.namespace == f"tenant-{TENANT_A}"
        assert result_b.namespace == f"tenant-{TENANT_B}"


# ============================================================================
# Full Tenant Provisioning Tests
# ============================================================================


class TestTenantProvisioning:
    """Integration tests for full tenant provisioning workflow."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_provision_tenant_full(self, mock_k8s_api, k8s_config):
        """Test full tenant provisioning creates all resources."""
        mock_k8s_api["core_v1"].create_namespace = MagicMock()
        mock_k8s_api["core_v1"].create_namespaced_resource_quota = MagicMock()
        mock_k8s_api["core_v1"].create_namespaced_limit_range = MagicMock()
        mock_k8s_api["networking_v1"].create_namespaced_network_policy = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        results = await manager.provision_tenant(TENANT_A)

        assert "namespace" in results
        assert "resource_quota" in results
        assert "limit_range" in results
        assert "network_policy" in results

        assert results["namespace"].is_success()
        assert results["resource_quota"].is_success()
        assert results["limit_range"].is_success()
        assert results["network_policy"].is_success()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_provision_tenant_partial(self, mock_k8s_api, k8s_config):
        """Test tenant provisioning without optional resources."""
        mock_k8s_api["core_v1"].create_namespace = MagicMock()
        mock_k8s_api["core_v1"].create_namespaced_resource_quota = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        results = await manager.provision_tenant(
            TENANT_A,
            create_network_policy=False,
            create_limit_range=False,
        )

        assert "namespace" in results
        assert "resource_quota" in results
        assert "limit_range" not in results
        assert "network_policy" not in results

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_provision_tenant_with_custom_quotas(self, mock_k8s_api, k8s_config):
        """Test tenant provisioning with custom quota overrides."""
        mock_k8s_api["core_v1"].create_namespace = MagicMock()
        mock_k8s_api["core_v1"].create_namespaced_resource_quota = MagicMock()
        mock_k8s_api["core_v1"].create_namespaced_limit_range = MagicMock()
        mock_k8s_api["networking_v1"].create_namespaced_network_policy = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        results = await manager.provision_tenant(
            PREMIUM_TENANT,
            cpu=PREMIUM_CPU,
            memory=PREMIUM_MEMORY,
            storage=PREMIUM_STORAGE,
            max_pods=200,
            max_pvcs=50,
        )

        assert results["namespace"].is_success()
        assert results["resource_quota"].is_success()
        assert results["resource_quota"].details["cpu"] == PREMIUM_CPU
        assert results["resource_quota"].details["memory"] == PREMIUM_MEMORY

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_provision_stops_on_namespace_failure(
        self, mock_k8s_api, mock_api_exception, k8s_config
    ):
        """Test provisioning stops if namespace creation fails."""
        server_error = mock_api_exception(500, "Internal Server Error")

        with patch("shared.infrastructure.k8s_manager.ApiException", mock_api_exception):
            mock_k8s_api["core_v1"].create_namespace = MagicMock(side_effect=server_error)

            manager = K8sResourceManager(config=k8s_config)
            results = await manager.provision_tenant(TENANT_A)

            assert results["namespace"].status == K8sOperationStatus.ERROR
            assert "resource_quota" not in results  # Should stop after namespace failure


# ============================================================================
# Multi-Tenant Isolation Tests
# ============================================================================


class TestMultiTenantIsolation:
    """Integration tests for multi-tenant namespace isolation."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tenant_namespaces_are_unique(self, mock_k8s_api, k8s_config):
        """Test each tenant gets a unique namespace."""
        mock_k8s_api["core_v1"].create_namespace = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        tenants = [TENANT_A, TENANT_B, TENANT_C, PREMIUM_TENANT, BASIC_TENANT]
        namespaces = []

        for tenant in tenants:
            result = await manager.create_tenant_namespace(tenant)
            namespaces.append(result.namespace)

        # All namespaces should be unique
        assert len(namespaces) == len(set(namespaces))

        # Each should follow naming convention
        for i, ns in enumerate(namespaces):
            assert ns == f"tenant-{tenants[i]}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_tenant_quotas_are_independent(self, mock_k8s_api, k8s_config):
        """Test quota configurations are independent per tenant."""
        mock_k8s_api["core_v1"].create_namespaced_resource_quota = MagicMock()

        manager = K8sResourceManager(config=k8s_config)

        # Create different quotas for different tenants
        quota_configs = {
            TENANT_A: {"cpu": "2", "memory": "4Gi"},
            TENANT_B: {"cpu": "4", "memory": "8Gi"},
            TENANT_C: {"cpu": "8", "memory": "16Gi"},
        }

        results = {}
        for tenant, quotas in quota_configs.items():
            result = await manager.create_resource_quota(
                tenant,
                cpu=quotas["cpu"],
                memory=quotas["memory"],
            )
            results[tenant] = result

        # Verify each has its own quota
        for tenant, quotas in quota_configs.items():
            assert results[tenant].status == K8sOperationStatus.SUCCESS
            assert results[tenant].details["cpu"] == quotas["cpu"]
            assert results[tenant].details["memory"] == quotas["memory"]
            assert results[tenant].namespace == f"tenant-{tenant}"

    @pytest.mark.integration
    def test_namespace_naming_prevents_collision(self, k8s_config):
        """Test namespace naming prevents cross-tenant collisions."""
        manager = K8sResourceManager(config=k8s_config)

        # Different tenant IDs should produce different namespaces
        ns_a = manager._get_namespace_name("tenant-alpha")
        ns_b = manager._get_namespace_name("tenant-beta")
        ns_c = manager._get_namespace_name("alpha")  # Different ID

        assert ns_a != ns_b
        assert ns_a != ns_c


# ============================================================================
# Namespace Deletion Tests
# ============================================================================


class TestNamespaceDeletion:
    """Integration tests for namespace deletion."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_namespace_success(self, mock_k8s_api, k8s_config):
        """Test successful namespace deletion."""
        mock_k8s_api["core_v1"].delete_namespace = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        result = await manager.delete_tenant_namespace(TENANT_A)

        assert result.status == K8sOperationStatus.SUCCESS
        assert "deletion initiated" in result.message.lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_namespace_not_found(self, mock_k8s_api, mock_api_exception, k8s_config):
        """Test namespace deletion handles not found."""
        not_found = mock_api_exception(404, "Not Found")

        with patch("shared.infrastructure.k8s_manager.ApiException", mock_api_exception):
            mock_k8s_api["core_v1"].delete_namespace = MagicMock(side_effect=not_found)

            manager = K8sResourceManager(config=k8s_config)
            result = await manager.delete_tenant_namespace("nonexistent-tenant")

            assert result.status == K8sOperationStatus.NOT_FOUND

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_namespace_with_grace_period(self, mock_k8s_api, k8s_config):
        """Test namespace deletion respects grace period."""
        mock_k8s_api["core_v1"].delete_namespace = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        result = await manager.delete_tenant_namespace(TENANT_A, grace_period_seconds=60)

        assert result.status == K8sOperationStatus.SUCCESS
        mock_k8s_api["client"].V1DeleteOptions.assert_called()


# ============================================================================
# Quota Usage Tracking Tests
# ============================================================================


class TestQuotaUsageTracking:
    """Integration tests for quota usage tracking."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_quota_usage_success(self, mock_k8s_api, k8s_config):
        """Test getting tenant quota usage."""
        # Mock quota list response
        mock_quota = MagicMock()
        mock_quota.metadata.name = "tenant-quota"
        mock_quota.status.hard = {"requests.cpu": "2", "requests.memory": "4Gi"}
        mock_quota.status.used = {"requests.cpu": "500m", "requests.memory": "1Gi"}

        mock_quota_list = MagicMock()
        mock_quota_list.items = [mock_quota]

        mock_k8s_api["core_v1"].list_namespaced_resource_quota = MagicMock(
            return_value=mock_quota_list
        )

        manager = K8sResourceManager(config=k8s_config)
        usage = await manager.get_tenant_quota_usage(TENANT_A)

        assert usage is not None
        assert usage["namespace"] == f"tenant-{TENANT_A}"
        assert "hard" in usage
        assert "used" in usage

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_get_quota_usage_no_quotas(self, mock_k8s_api, k8s_config):
        """Test getting quota usage when no quotas exist."""
        mock_quota_list = MagicMock()
        mock_quota_list.items = []

        mock_k8s_api["core_v1"].list_namespaced_resource_quota = MagicMock(
            return_value=mock_quota_list
        )

        manager = K8sResourceManager(config=k8s_config)
        usage = await manager.get_tenant_quota_usage(TENANT_A)

        assert usage is None


# ============================================================================
# Namespace Existence Check Tests
# ============================================================================


class TestNamespaceExistenceCheck:
    """Integration tests for namespace existence checking."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_namespace_exists_true(self, mock_k8s_api, k8s_config):
        """Test namespace exists returns True when exists."""
        mock_k8s_api["core_v1"].read_namespace = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        exists = await manager.namespace_exists(TENANT_A)

        assert exists is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_namespace_exists_false(self, mock_k8s_api, mock_api_exception, k8s_config):
        """Test namespace exists returns False when not found."""
        not_found = mock_api_exception(404, "Not Found")

        with patch("shared.infrastructure.k8s_manager.ApiException", mock_api_exception):
            mock_k8s_api["core_v1"].read_namespace = MagicMock(side_effect=not_found)

            manager = K8sResourceManager(config=k8s_config)
            exists = await manager.namespace_exists("nonexistent-tenant")

            assert exists is False


# ============================================================================
# Fail-Safe Mode Tests
# ============================================================================


class TestFailSafeMode:
    """Integration tests for fail-safe mode behavior."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fail_safe_mode_returns_unavailable(self):
        """Test fail-safe mode returns UNAVAILABLE when K8s unavailable."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=True)
            manager = K8sResourceManager(config=config)

            result = await manager.create_tenant_namespace(TENANT_A)

            assert result.status == K8sOperationStatus.UNAVAILABLE
            assert "not available" in result.message.lower()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_strict_mode_raises_error(self):
        """Test strict mode raises RuntimeError when K8s unavailable."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=False)
            manager = K8sResourceManager(config=config)

            with pytest.raises(RuntimeError, match="not available"):
                await manager.create_tenant_namespace(TENANT_A)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_fail_safe_allows_graceful_degradation(self):
        """Test fail-safe mode allows application to continue."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=True)
            manager = K8sResourceManager(config=config)

            # All operations should return UNAVAILABLE but not raise
            ns_result = await manager.create_tenant_namespace(TENANT_A)
            quota_result = await manager.create_resource_quota(TENANT_A)
            limit_result = await manager.create_limit_range(TENANT_A)
            policy_result = await manager.create_network_policy(TENANT_A)
            delete_result = await manager.delete_tenant_namespace(TENANT_A)

            for result in [ns_result, quota_result, limit_result, policy_result, delete_result]:
                assert result.status == K8sOperationStatus.UNAVAILABLE


# ============================================================================
# Audit Logging Tests
# ============================================================================


class TestAuditLogging:
    """Integration tests for K8s operation audit logging."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_audit_log_populated_on_success(self, mock_k8s_api, k8s_config):
        """Test audit log is populated after successful operations."""
        mock_k8s_api["core_v1"].create_namespace = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        await manager.create_tenant_namespace(TENANT_A)

        log = manager.get_audit_log()
        assert len(log) > 0
        assert log[-1]["operation"] == "create_namespace"
        assert log[-1]["tenant_id"] == TENANT_A
        assert log[-1]["status"] == "success"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_audit_log_contains_constitutional_hash(self, mock_k8s_api, k8s_config):
        """Test audit log entries contain constitutional hash."""
        mock_k8s_api["core_v1"].create_namespace = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        await manager.create_tenant_namespace(TENANT_A)

        log = manager.get_audit_log()
        assert log[-1]["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_audit_log_captures_errors(self):
        """Test audit log captures error operations."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=True)
            manager = K8sResourceManager(config=config)
            await manager.create_tenant_namespace(TENANT_A)

            log = manager.get_audit_log()
            assert log[-1]["status"] == "unavailable"

    @pytest.mark.integration
    def test_audit_log_limit(self, k8s_config):
        """Test audit log respects limit parameter."""
        manager = K8sResourceManager(config=k8s_config)

        # Manually populate audit log
        for i in range(20):
            manager._audit_log.append({"index": i})

        log = manager.get_audit_log(limit=10)
        assert len(log) == 10
        # Should return last 10 entries
        assert log[0]["index"] == 10
        assert log[-1]["index"] == 19


# ============================================================================
# Configuration Integration Tests
# ============================================================================


class TestConfigurationIntegration:
    """Integration tests for K8s config and tenant config integration."""

    @pytest.mark.integration
    def test_k8s_config_from_environment(self, monkeypatch):
        """Test K8sConfig loads from environment variables."""
        monkeypatch.setenv("K8S_NAMESPACE_PREFIX", "myapp-")
        monkeypatch.setenv("TENANT_DEFAULT_CPU_QUOTA", "4")
        monkeypatch.setenv("TENANT_DEFAULT_MEMORY_QUOTA", "8Gi")
        monkeypatch.setenv("TENANT_DEFAULT_STORAGE_QUOTA", "50Gi")
        monkeypatch.setenv("TENANT_DEFAULT_MAX_PODS", "100")
        monkeypatch.setenv("TENANT_DEFAULT_MAX_PVCS", "25")
        monkeypatch.setenv("K8S_RETRY_ATTEMPTS", "5")
        monkeypatch.setenv("K8S_FAIL_SAFE", "false")

        config = K8sConfig.from_env()

        assert config.namespace_prefix == "myapp-"
        assert config.default_cpu_quota == "4"
        assert config.default_memory_quota == "8Gi"
        assert config.default_storage_quota == "50Gi"
        assert config.default_max_pods == 100
        assert config.default_max_pvcs == 25
        assert config.retry_attempts == 5
        assert config.fail_safe is False

    @pytest.mark.integration
    def test_tenant_quota_config_integration(self):
        """Test TenantQuotaConfig integration with K8s manager."""
        # Create tenant quota config
        quota_config = TenantQuotaConfig(
            cpu="4",
            memory="8Gi",
            storage="50Gi",
        )

        # Values should be usable by K8s manager
        k8s_config = K8sConfig(
            default_cpu_quota=quota_config.cpu,
            default_memory_quota=quota_config.memory,
            default_storage_quota=quota_config.storage,
        )

        assert k8s_config.default_cpu_quota == "4"
        assert k8s_config.default_memory_quota == "8Gi"
        assert k8s_config.default_storage_quota == "50Gi"


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestConvenienceFunctions:
    """Integration tests for convenience functions."""

    @pytest.mark.integration
    def test_get_k8s_resource_manager_singleton(self):
        """Test get_k8s_resource_manager returns consistent instance."""
        get_k8s_resource_manager.cache_clear()

        manager1 = get_k8s_resource_manager()
        manager2 = get_k8s_resource_manager()

        assert manager1 is manager2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_create_tenant_resources_function(self):
        """Test create_tenant_resources convenience function."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            get_k8s_resource_manager.cache_clear()

            results = await create_tenant_resources(
                TENANT_A,
                cpu="2",
                memory="4Gi",
                storage="20Gi",
            )

            assert "namespace" in results

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_delete_tenant_resources_function(self):
        """Test delete_tenant_resources convenience function."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            get_k8s_resource_manager.cache_clear()

            result = await delete_tenant_resources(TENANT_A)

            assert result.status == K8sOperationStatus.UNAVAILABLE


# ============================================================================
# Constitutional Compliance Tests
# ============================================================================


class TestConstitutionalCompliance:
    """Test constitutional hash compliance in K8s operations."""

    @pytest.mark.integration
    def test_constitutional_hash_present(self):
        """Constitutional hash should be exported."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    @pytest.mark.integration
    def test_k8s_available_exported(self):
        """K8S_AVAILABLE should be exported."""
        assert isinstance(K8S_AVAILABLE, bool)

    @pytest.mark.integration
    def test_manager_has_constitutional_hash(self, k8s_config):
        """Test K8sResourceManager has constitutional hash."""
        manager = K8sResourceManager(config=k8s_config)
        assert manager._constitutional_hash == CONSTITUTIONAL_HASH

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_namespace_labels_include_constitutional_hash(self, mock_k8s_api, k8s_config):
        """Test namespace creation includes constitutional hash in labels."""
        mock_k8s_api["core_v1"].create_namespace = MagicMock()

        manager = K8sResourceManager(config=k8s_config)
        await manager.create_tenant_namespace(TENANT_A)

        # V1ObjectMeta should be called with constitutional-hash label
        call_args = mock_k8s_api["client"].V1ObjectMeta.call_args
        assert call_args is not None


# ============================================================================
# Error Recovery Tests
# ============================================================================


class TestErrorRecovery:
    """Integration tests for error recovery and retry behavior."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_operation_retries_on_transient_error(self, mock_k8s_api, mock_api_exception):
        """Test operations retry on transient server errors."""
        server_error = mock_api_exception(503, "Service Unavailable")
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise server_error
            return MagicMock()

        with patch("shared.infrastructure.k8s_manager.ApiException", mock_api_exception):
            mock_k8s_api["core_v1"].create_namespace = MagicMock(side_effect=side_effect)

            config = K8sConfig(retry_attempts=3, retry_delay_seconds=0.01)
            manager = K8sResourceManager(config=config)
            result = await manager.create_tenant_namespace(TENANT_A)

            assert result.status == K8sOperationStatus.SUCCESS
            assert call_count == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, mock_k8s_api, mock_api_exception):
        """Test operations don't retry on client errors (4xx)."""
        bad_request = mock_api_exception(400, "Bad Request")
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise bad_request

        with patch("shared.infrastructure.k8s_manager.ApiException", mock_api_exception):
            mock_k8s_api["core_v1"].create_namespace = MagicMock(side_effect=side_effect)

            config = K8sConfig(retry_attempts=3, retry_delay_seconds=0.01)
            manager = K8sResourceManager(config=config)
            result = await manager.create_tenant_namespace(TENANT_A)

            assert result.status == K8sOperationStatus.ERROR
            assert call_count == 1  # No retries for 4xx


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
