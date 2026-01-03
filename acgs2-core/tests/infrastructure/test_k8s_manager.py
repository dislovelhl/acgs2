"""
Tests for Kubernetes Resource Manager
Constitutional Hash: cdd01ef066bc6cf2

Tests verify:
- K8sConfig configuration from defaults and environment
- K8sOperationResult status handling
- K8sResourceManager namespace operations
- Resource quota creation and management
- LimitRange creation
- NetworkPolicy creation
- Full tenant provisioning workflow
- Fail-safe mode behavior
- Audit logging
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from shared.infrastructure.k8s_manager import (
    CONSTITUTIONAL_HASH,
    K8S_AVAILABLE,
    K8sConfig,
    K8sOperationResult,
    K8sOperationStatus,
    K8sResourceManager,
    create_tenant_resources,
    delete_tenant_resources,
    get_k8s_resource_manager,
)


class TestK8sOperationStatus:
    """Test K8sOperationStatus enum."""

    def test_all_statuses_exist(self):
        """Test all expected statuses are defined."""
        assert K8sOperationStatus.SUCCESS == "success"
        assert K8sOperationStatus.ALREADY_EXISTS == "already_exists"
        assert K8sOperationStatus.NOT_FOUND == "not_found"
        assert K8sOperationStatus.ERROR == "error"
        assert K8sOperationStatus.UNAVAILABLE == "unavailable"

    def test_status_values_are_strings(self):
        """Test status values are strings."""
        for status in K8sOperationStatus:
            assert isinstance(status.value, str)


class TestK8sOperationResult:
    """Test K8sOperationResult dataclass."""

    def test_success_result(self):
        """Test successful result properties."""
        result = K8sOperationResult(
            status=K8sOperationStatus.SUCCESS,
            resource_name="tenant-namespace",
            namespace="tenant-test",
            message="Namespace created successfully",
        )
        assert result.is_success() is True
        assert result.status == K8sOperationStatus.SUCCESS
        assert result.resource_name == "tenant-namespace"
        assert result.namespace == "tenant-test"
        assert result.message == "Namespace created successfully"

    def test_already_exists_is_success(self):
        """Test that ALREADY_EXISTS is treated as success (idempotency)."""
        result = K8sOperationResult(
            status=K8sOperationStatus.ALREADY_EXISTS,
            resource_name="tenant-namespace",
        )
        assert result.is_success() is True

    def test_error_result(self):
        """Test error result is not success."""
        result = K8sOperationResult(
            status=K8sOperationStatus.ERROR,
            resource_name="tenant-namespace",
            message="Failed to create",
        )
        assert result.is_success() is False

    def test_not_found_result(self):
        """Test not found result is not success."""
        result = K8sOperationResult(
            status=K8sOperationStatus.NOT_FOUND,
            resource_name="tenant-namespace",
        )
        assert result.is_success() is False

    def test_unavailable_result(self):
        """Test unavailable result is not success."""
        result = K8sOperationResult(
            status=K8sOperationStatus.UNAVAILABLE,
            resource_name="tenant-namespace",
        )
        assert result.is_success() is False

    def test_result_with_details(self):
        """Test result with additional details."""
        result = K8sOperationResult(
            status=K8sOperationStatus.SUCCESS,
            resource_name="tenant-quota",
            details={"cpu": "2", "memory": "4Gi"},
        )
        assert result.details["cpu"] == "2"
        assert result.details["memory"] == "4Gi"

    def test_timestamp_auto_generated(self):
        """Test timestamp is automatically generated."""
        result = K8sOperationResult(
            status=K8sOperationStatus.SUCCESS,
            resource_name="test",
        )
        assert result.timestamp is not None
        assert isinstance(result.timestamp, str)


class TestK8sConfig:
    """Test K8sConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = K8sConfig()
        assert config.namespace_prefix == "tenant-"
        assert config.default_cpu_quota == "2"
        assert config.default_memory_quota == "4Gi"
        assert config.default_storage_quota == "20Gi"
        assert config.default_max_pods == 50
        assert config.default_max_pvcs == 10
        assert config.retry_attempts == 3
        assert config.retry_delay_seconds == 1.0
        assert config.fail_safe is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = K8sConfig(
            namespace_prefix="custom-",
            default_cpu_quota="4",
            default_memory_quota="8Gi",
            default_storage_quota="50Gi",
            default_max_pods=100,
            default_max_pvcs=20,
            retry_attempts=5,
            retry_delay_seconds=2.0,
            fail_safe=False,
        )
        assert config.namespace_prefix == "custom-"
        assert config.default_cpu_quota == "4"
        assert config.default_memory_quota == "8Gi"
        assert config.default_storage_quota == "50Gi"
        assert config.default_max_pods == 100
        assert config.default_max_pvcs == 20
        assert config.retry_attempts == 5
        assert config.retry_delay_seconds == 2.0
        assert config.fail_safe is False

    def test_from_env_defaults(self, monkeypatch):
        """Test from_env with no environment variables set."""
        # Clear relevant env vars
        for key in [
            "K8S_NAMESPACE_PREFIX",
            "TENANT_DEFAULT_CPU_QUOTA",
            "TENANT_DEFAULT_MEMORY_QUOTA",
            "TENANT_DEFAULT_STORAGE_QUOTA",
            "TENANT_DEFAULT_MAX_PODS",
            "TENANT_DEFAULT_MAX_PVCS",
            "K8S_RETRY_ATTEMPTS",
            "K8S_RETRY_DELAY",
            "K8S_FAIL_SAFE",
        ]:
            monkeypatch.delenv(key, raising=False)

        config = K8sConfig.from_env()
        assert config.namespace_prefix == "tenant-"
        assert config.default_cpu_quota == "2"
        assert config.default_memory_quota == "4Gi"

    def test_from_env_custom(self, monkeypatch):
        """Test from_env with custom environment variables."""
        monkeypatch.setenv("K8S_NAMESPACE_PREFIX", "myapp-")
        monkeypatch.setenv("TENANT_DEFAULT_CPU_QUOTA", "8")
        monkeypatch.setenv("TENANT_DEFAULT_MEMORY_QUOTA", "16Gi")
        monkeypatch.setenv("TENANT_DEFAULT_STORAGE_QUOTA", "100Gi")
        monkeypatch.setenv("TENANT_DEFAULT_MAX_PODS", "200")
        monkeypatch.setenv("TENANT_DEFAULT_MAX_PVCS", "50")
        monkeypatch.setenv("K8S_RETRY_ATTEMPTS", "10")
        monkeypatch.setenv("K8S_RETRY_DELAY", "5.0")
        monkeypatch.setenv("K8S_FAIL_SAFE", "false")

        config = K8sConfig.from_env()
        assert config.namespace_prefix == "myapp-"
        assert config.default_cpu_quota == "8"
        assert config.default_memory_quota == "16Gi"
        assert config.default_storage_quota == "100Gi"
        assert config.default_max_pods == 200
        assert config.default_max_pvcs == 50
        assert config.retry_attempts == 10
        assert config.retry_delay_seconds == 5.0
        assert config.fail_safe is False

    def test_fail_safe_true_value(self, monkeypatch):
        """Test fail_safe with 'true' value."""
        monkeypatch.setenv("K8S_FAIL_SAFE", "true")
        config = K8sConfig.from_env()
        assert config.fail_safe is True


class TestK8sResourceManagerInitialization:
    """Test K8sResourceManager initialization."""

    def test_manager_creation_with_defaults(self):
        """Test manager can be created with default config."""
        manager = K8sResourceManager()
        assert manager is not None
        assert manager.config is not None
        assert manager._initialized is False

    def test_manager_creation_with_custom_config(self):
        """Test manager can be created with custom config."""
        config = K8sConfig(namespace_prefix="custom-")
        manager = K8sResourceManager(config=config)
        assert manager.config.namespace_prefix == "custom-"

    def test_namespace_name_generation(self):
        """Test namespace name generation from tenant ID."""
        config = K8sConfig(namespace_prefix="acgs-")
        manager = K8sResourceManager(config=config)
        name = manager._get_namespace_name("tenant123")
        assert name == "acgs-tenant123"

    def test_constitutional_hash_set(self):
        """Test constitutional hash is set on manager."""
        manager = K8sResourceManager()
        assert manager._constitutional_hash == CONSTITUTIONAL_HASH


class TestK8sResourceManagerWithMockedClient:
    """Test K8sResourceManager with mocked Kubernetes API."""

    @pytest.fixture
    def mock_k8s_client(self):
        """Create mock Kubernetes client."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", True):
            with patch("shared.infrastructure.k8s_manager.client") as mock_client:
                with patch("shared.infrastructure.k8s_manager.config") as mock_config:
                    # Setup config mocks
                    mock_config.load_incluster_config = MagicMock()
                    mock_config.ConfigException = Exception

                    # Setup client mocks
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

    @pytest.mark.asyncio
    async def test_create_tenant_namespace_success(self, mock_k8s_client):
        """Test successful namespace creation."""
        mock_k8s_client["core_v1"].create_namespace = MagicMock()

        manager = K8sResourceManager()
        result = await manager.create_tenant_namespace("test-tenant")

        assert result.status == K8sOperationStatus.SUCCESS
        assert result.resource_name == "tenant-test-tenant"
        assert result.is_success() is True

    @pytest.mark.asyncio
    async def test_create_tenant_namespace_already_exists(self, mock_k8s_client):
        """Test namespace creation when already exists."""
        # Create mock ApiException for conflict
        mock_exception = MagicMock()
        mock_exception.status = 409
        mock_exception.reason = "Conflict"
        mock_exception.body = "already exists"

        with patch("shared.infrastructure.k8s_manager.ApiException", type(mock_exception)):
            mock_k8s_client["core_v1"].create_namespace = MagicMock(side_effect=mock_exception)

            manager = K8sResourceManager()
            result = await manager.create_tenant_namespace("test-tenant")

            assert result.status == K8sOperationStatus.ALREADY_EXISTS
            assert result.is_success() is True

    @pytest.mark.asyncio
    async def test_create_resource_quota_success(self, mock_k8s_client):
        """Test successful resource quota creation."""
        mock_k8s_client["core_v1"].create_namespaced_resource_quota = MagicMock()

        manager = K8sResourceManager()
        result = await manager.create_resource_quota(
            "test-tenant",
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

    @pytest.mark.asyncio
    async def test_create_resource_quota_with_defaults(self, mock_k8s_client):
        """Test resource quota creation with default values."""
        mock_k8s_client["core_v1"].create_namespaced_resource_quota = MagicMock()

        config = K8sConfig(
            default_cpu_quota="2",
            default_memory_quota="4Gi",
            default_storage_quota="20Gi",
        )
        manager = K8sResourceManager(config=config)
        result = await manager.create_resource_quota("test-tenant")

        assert result.status == K8sOperationStatus.SUCCESS
        assert result.details["cpu"] == "2"
        assert result.details["memory"] == "4Gi"
        assert result.details["storage"] == "20Gi"

    @pytest.mark.asyncio
    async def test_create_limit_range_success(self, mock_k8s_client):
        """Test successful LimitRange creation."""
        mock_k8s_client["core_v1"].create_namespaced_limit_range = MagicMock()

        manager = K8sResourceManager()
        result = await manager.create_limit_range(
            "test-tenant",
            default_cpu="200m",
            default_memory="256Mi",
            max_cpu="2",
            max_memory="2Gi",
        )

        assert result.status == K8sOperationStatus.SUCCESS
        assert result.resource_name == "tenant-limits"

    @pytest.mark.asyncio
    async def test_create_network_policy_success(self, mock_k8s_client):
        """Test successful NetworkPolicy creation."""
        mock_k8s_client["networking_v1"].create_namespaced_network_policy = MagicMock()

        manager = K8sResourceManager()
        result = await manager.create_network_policy(
            "test-tenant",
            allow_same_namespace=True,
            allow_kube_system_dns=True,
        )

        assert result.status == K8sOperationStatus.SUCCESS
        assert result.resource_name == "tenant-isolation"

    @pytest.mark.asyncio
    async def test_provision_tenant_full(self, mock_k8s_client):
        """Test full tenant provisioning."""
        mock_k8s_client["core_v1"].create_namespace = MagicMock()
        mock_k8s_client["core_v1"].create_namespaced_resource_quota = MagicMock()
        mock_k8s_client["core_v1"].create_namespaced_limit_range = MagicMock()
        mock_k8s_client["networking_v1"].create_namespaced_network_policy = MagicMock()

        manager = K8sResourceManager()
        results = await manager.provision_tenant("test-tenant")

        assert "namespace" in results
        assert "resource_quota" in results
        assert "limit_range" in results
        assert "network_policy" in results

        assert results["namespace"].is_success()
        assert results["resource_quota"].is_success()
        assert results["limit_range"].is_success()
        assert results["network_policy"].is_success()

    @pytest.mark.asyncio
    async def test_provision_tenant_partial(self, mock_k8s_client):
        """Test tenant provisioning without optional resources."""
        mock_k8s_client["core_v1"].create_namespace = MagicMock()
        mock_k8s_client["core_v1"].create_namespaced_resource_quota = MagicMock()

        manager = K8sResourceManager()
        results = await manager.provision_tenant(
            "test-tenant",
            create_network_policy=False,
            create_limit_range=False,
        )

        assert "namespace" in results
        assert "resource_quota" in results
        assert "limit_range" not in results
        assert "network_policy" not in results

    @pytest.mark.asyncio
    async def test_delete_tenant_namespace_success(self, mock_k8s_client):
        """Test successful namespace deletion."""
        mock_k8s_client["core_v1"].delete_namespace = MagicMock()

        manager = K8sResourceManager()
        result = await manager.delete_tenant_namespace("test-tenant")

        assert result.status == K8sOperationStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_namespace_exists_true(self, mock_k8s_client):
        """Test namespace exists check returns True."""
        mock_k8s_client["core_v1"].read_namespace = MagicMock()

        manager = K8sResourceManager()
        exists = await manager.namespace_exists("test-tenant")

        assert exists is True

    @pytest.mark.asyncio
    async def test_namespace_exists_false(self, mock_k8s_client):
        """Test namespace exists check returns False for not found."""
        mock_exception = MagicMock()
        mock_exception.status = 404

        with patch("shared.infrastructure.k8s_manager.ApiException", type(mock_exception)):
            mock_k8s_client["core_v1"].read_namespace = MagicMock(side_effect=mock_exception)

            manager = K8sResourceManager()
            exists = await manager.namespace_exists("nonexistent-tenant")

            assert exists is False


class TestK8sResourceManagerUnavailable:
    """Test K8sResourceManager when Kubernetes is unavailable."""

    @pytest.mark.asyncio
    async def test_create_namespace_unavailable_fail_safe(self):
        """Test namespace creation returns unavailable in fail-safe mode."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=True)
            manager = K8sResourceManager(config=config)
            result = await manager.create_tenant_namespace("test-tenant")

            assert result.status == K8sOperationStatus.UNAVAILABLE
            assert "not available" in result.message.lower()

    @pytest.mark.asyncio
    async def test_create_namespace_unavailable_strict(self):
        """Test namespace creation raises error in strict mode."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=False)
            manager = K8sResourceManager(config=config)

            with pytest.raises(RuntimeError, match="not available"):
                await manager.create_tenant_namespace("test-tenant")

    @pytest.mark.asyncio
    async def test_create_resource_quota_unavailable_fail_safe(self):
        """Test resource quota creation returns unavailable in fail-safe mode."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=True)
            manager = K8sResourceManager(config=config)
            result = await manager.create_resource_quota("test-tenant")

            assert result.status == K8sOperationStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_create_limit_range_unavailable_fail_safe(self):
        """Test LimitRange creation returns unavailable in fail-safe mode."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=True)
            manager = K8sResourceManager(config=config)
            result = await manager.create_limit_range("test-tenant")

            assert result.status == K8sOperationStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_create_network_policy_unavailable_fail_safe(self):
        """Test NetworkPolicy creation returns unavailable in fail-safe mode."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=True)
            manager = K8sResourceManager(config=config)
            result = await manager.create_network_policy("test-tenant")

            assert result.status == K8sOperationStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_delete_namespace_unavailable_fail_safe(self):
        """Test namespace deletion returns unavailable in fail-safe mode."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=True)
            manager = K8sResourceManager(config=config)
            result = await manager.delete_tenant_namespace("test-tenant")

            assert result.status == K8sOperationStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_get_quota_usage_unavailable(self):
        """Test quota usage returns None when unavailable."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            manager = K8sResourceManager()
            usage = await manager.get_tenant_quota_usage("test-tenant")

            assert usage is None

    @pytest.mark.asyncio
    async def test_namespace_exists_unavailable(self):
        """Test namespace exists returns False when unavailable."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            manager = K8sResourceManager()
            exists = await manager.namespace_exists("test-tenant")

            assert exists is False


class TestK8sResourceManagerAuditLog:
    """Test K8sResourceManager audit logging."""

    @pytest.mark.asyncio
    async def test_audit_log_populated(self):
        """Test audit log is populated after operations."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=True)
            manager = K8sResourceManager(config=config)
            await manager.create_tenant_namespace("test-tenant")

            log = manager.get_audit_log()
            assert len(log) > 0
            assert log[-1]["operation"] == "create_namespace"
            assert log[-1]["tenant_id"] == "test-tenant"

    @pytest.mark.asyncio
    async def test_audit_log_contains_constitutional_hash(self):
        """Test audit log entries contain constitutional hash."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            config = K8sConfig(fail_safe=True)
            manager = K8sResourceManager(config=config)
            await manager.create_tenant_namespace("test-tenant")

            log = manager.get_audit_log()
            assert log[-1]["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_audit_log_limit(self):
        """Test audit log respects limit parameter."""
        manager = K8sResourceManager()
        # Manually populate audit log
        for i in range(10):
            manager._audit_log.append({"index": i})

        log = manager.get_audit_log(limit=5)
        assert len(log) == 5
        # Should return last 5 entries
        assert log[0]["index"] == 5


class TestK8sManagerConvenienceFunctions:
    """Test convenience functions."""

    def test_get_k8s_resource_manager_singleton(self):
        """Test get_k8s_resource_manager returns consistent instance."""
        # Clear cache for test isolation
        get_k8s_resource_manager.cache_clear()

        manager1 = get_k8s_resource_manager()
        manager2 = get_k8s_resource_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_create_tenant_resources_function(self):
        """Test create_tenant_resources convenience function."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            # Clear cache before test
            get_k8s_resource_manager.cache_clear()

            results = await create_tenant_resources(
                "test-tenant",
                cpu="2",
                memory="4Gi",
                storage="20Gi",
            )

            assert "namespace" in results

    @pytest.mark.asyncio
    async def test_delete_tenant_resources_function(self):
        """Test delete_tenant_resources convenience function."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", False):
            # Clear cache before test
            get_k8s_resource_manager.cache_clear()

            result = await delete_tenant_resources("test-tenant")

            assert result.status == K8sOperationStatus.UNAVAILABLE


class TestConstitutionalCompliance:
    """Test constitutional hash compliance."""

    def test_constitutional_hash_present(self):
        """Constitutional hash should be exported."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_k8s_available_exported(self):
        """K8S_AVAILABLE should be exported."""
        assert isinstance(K8S_AVAILABLE, bool)


class TestK8sManagerWithLabels:
    """Test namespace creation with custom labels."""

    @pytest.fixture
    def mock_k8s_client(self):
        """Create mock Kubernetes client."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", True):
            with patch("shared.infrastructure.k8s_manager.client") as mock_client:
                with patch("shared.infrastructure.k8s_manager.config") as mock_config:
                    mock_config.load_incluster_config = MagicMock()
                    mock_config.ConfigException = Exception

                    mock_core_v1 = MagicMock()
                    mock_client.CoreV1Api.return_value = mock_core_v1

                    mock_client.V1Namespace = MagicMock(return_value=MagicMock())
                    mock_client.V1ObjectMeta = MagicMock(return_value=MagicMock())

                    yield {
                        "client": mock_client,
                        "core_v1": mock_core_v1,
                    }

    @pytest.mark.asyncio
    async def test_create_namespace_with_custom_labels(self, mock_k8s_client):
        """Test namespace creation with custom labels."""
        mock_k8s_client["core_v1"].create_namespace = MagicMock()

        manager = K8sResourceManager()
        result = await manager.create_tenant_namespace(
            "test-tenant",
            labels={"environment": "production", "team": "platform"},
        )

        assert result.status == K8sOperationStatus.SUCCESS
        # Verify V1ObjectMeta was called with labels
        mock_k8s_client["client"].V1ObjectMeta.assert_called()


class TestK8sManagerErrorHandling:
    """Test error handling in K8s manager."""

    @pytest.fixture
    def mock_k8s_client_with_errors(self):
        """Create mock Kubernetes client that raises errors."""
        with patch("shared.infrastructure.k8s_manager.K8S_AVAILABLE", True):
            with patch("shared.infrastructure.k8s_manager.client") as mock_client:
                with patch("shared.infrastructure.k8s_manager.config") as mock_config:
                    mock_config.load_incluster_config = MagicMock()
                    mock_config.ConfigException = Exception

                    mock_core_v1 = MagicMock()
                    mock_networking_v1 = MagicMock()
                    mock_client.CoreV1Api.return_value = mock_core_v1
                    mock_client.NetworkingV1Api.return_value = mock_networking_v1

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
                    mock_client.V1DeleteOptions = MagicMock(return_value=MagicMock())

                    yield {
                        "client": mock_client,
                        "core_v1": mock_core_v1,
                        "networking_v1": mock_networking_v1,
                    }

    @pytest.mark.asyncio
    async def test_create_namespace_generic_error(self, mock_k8s_client_with_errors):
        """Test namespace creation handles generic API errors."""
        mock_exception = MagicMock()
        mock_exception.status = 500
        mock_exception.reason = "Internal Server Error"
        mock_exception.body = "server error"

        with patch("shared.infrastructure.k8s_manager.ApiException", type(mock_exception)):
            mock_k8s_client_with_errors["core_v1"].create_namespace = MagicMock(
                side_effect=mock_exception
            )

            config = K8sConfig(retry_attempts=1)
            manager = K8sResourceManager(config=config)
            result = await manager.create_tenant_namespace("test-tenant")

            assert result.status == K8sOperationStatus.ERROR
            assert "500" in str(result.details.get("status_code", ""))

    @pytest.mark.asyncio
    async def test_create_resource_quota_not_found(self, mock_k8s_client_with_errors):
        """Test resource quota creation handles namespace not found."""
        mock_exception = MagicMock()
        mock_exception.status = 404
        mock_exception.reason = "Not Found"
        mock_exception.body = "namespace not found"

        with patch("shared.infrastructure.k8s_manager.ApiException", type(mock_exception)):
            mock_k8s_client_with_errors["core_v1"].create_namespaced_resource_quota = MagicMock(
                side_effect=mock_exception
            )

            config = K8sConfig(retry_attempts=1)
            manager = K8sResourceManager(config=config)
            result = await manager.create_resource_quota("nonexistent-tenant")

            assert result.status == K8sOperationStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_namespace_not_found(self, mock_k8s_client_with_errors):
        """Test namespace deletion handles not found."""
        mock_exception = MagicMock()
        mock_exception.status = 404
        mock_exception.reason = "Not Found"

        with patch("shared.infrastructure.k8s_manager.ApiException", type(mock_exception)):
            mock_k8s_client_with_errors["core_v1"].delete_namespace = MagicMock(
                side_effect=mock_exception
            )

            config = K8sConfig(retry_attempts=1)
            manager = K8sResourceManager(config=config)
            result = await manager.delete_tenant_namespace("nonexistent-tenant")

            assert result.status == K8sOperationStatus.NOT_FOUND


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
