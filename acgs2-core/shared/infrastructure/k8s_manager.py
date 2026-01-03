"""
ACGS-2 Kubernetes Resource Manager
Constitutional Hash: cdd01ef066bc6cf2

Kubernetes namespace and resource quota management for multi-tenant isolation.
Provides tenant-specific namespace creation, resource quota enforcement,
and cluster resource management.

Security Features:
- Namespace-based tenant isolation
- Resource quota enforcement (CPU, memory, storage)
- RBAC-compatible operations
- Idempotent operations for high availability
- Fail-safe degradation when cluster unavailable

Usage:
    from shared.infrastructure.k8s_manager import K8sResourceManager

    manager = K8sResourceManager()
    await manager.create_tenant_namespace("tenant-id", quotas=tenant_config.quotas)
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional

# Constitutional hash for validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)

# Kubernetes client - optional dependency
try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    K8S_AVAILABLE = True
except ImportError:
    client = None
    config = None
    ApiException = Exception
    K8S_AVAILABLE = False


class K8sOperationStatus(str, Enum):
    """Status of Kubernetes operations."""

    SUCCESS = "success"
    ALREADY_EXISTS = "already_exists"
    NOT_FOUND = "not_found"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class K8sOperationResult:
    """Result of a Kubernetes operation."""

    status: K8sOperationStatus
    resource_name: str
    namespace: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def is_success(self) -> bool:
        """Check if operation was successful (including already_exists for idempotency)."""
        return self.status in (K8sOperationStatus.SUCCESS, K8sOperationStatus.ALREADY_EXISTS)


@dataclass
class K8sConfig:
    """
    Kubernetes connection configuration.

    Attributes:
        namespace_prefix: Prefix for tenant namespace names
        default_cpu_quota: Default CPU quota for tenants
        default_memory_quota: Default memory quota for tenants
        default_storage_quota: Default storage quota for tenants
        default_max_pods: Default maximum pods per tenant namespace
        default_max_pvcs: Default maximum PVCs per tenant namespace
        retry_attempts: Number of retry attempts for transient failures
        retry_delay_seconds: Delay between retry attempts
        fail_safe: Allow operations to proceed when cluster unavailable
    """

    namespace_prefix: str = "tenant-"
    default_cpu_quota: str = "2"
    default_memory_quota: str = "4Gi"
    default_storage_quota: str = "20Gi"
    default_max_pods: int = 50
    default_max_pvcs: int = 10
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    fail_safe: bool = True

    @classmethod
    def from_env(cls) -> "K8sConfig":
        """Create configuration from environment variables."""
        return cls(
            namespace_prefix=os.environ.get("K8S_NAMESPACE_PREFIX", "tenant-"),
            default_cpu_quota=os.environ.get("TENANT_DEFAULT_CPU_QUOTA", "2"),
            default_memory_quota=os.environ.get("TENANT_DEFAULT_MEMORY_QUOTA", "4Gi"),
            default_storage_quota=os.environ.get("TENANT_DEFAULT_STORAGE_QUOTA", "20Gi"),
            default_max_pods=int(os.environ.get("TENANT_DEFAULT_MAX_PODS", "50")),
            default_max_pvcs=int(os.environ.get("TENANT_DEFAULT_MAX_PVCS", "10")),
            retry_attempts=int(os.environ.get("K8S_RETRY_ATTEMPTS", "3")),
            retry_delay_seconds=float(os.environ.get("K8S_RETRY_DELAY", "1.0")),
            fail_safe=os.environ.get("K8S_FAIL_SAFE", "true").lower() == "true",
        )


class K8sResourceManager:
    """
    Kubernetes resource manager for multi-tenant isolation.

    Manages namespace creation, resource quotas, and tenant isolation
    at the Kubernetes cluster level. Supports both in-cluster and
    local kubeconfig authentication.

    Features:
    - Namespace-based tenant isolation
    - ResourceQuota enforcement per tenant
    - LimitRange for default container limits
    - NetworkPolicy templates for network isolation
    - Idempotent operations for high availability
    - Graceful degradation when cluster unavailable
    """

    def __init__(self, config: Optional[K8sConfig] = None):
        """
        Initialize the Kubernetes resource manager.

        Args:
            config: Optional K8sConfig instance. If None, loads from environment.
        """
        self.config = config or K8sConfig.from_env()
        self._core_v1: Optional[Any] = None
        self._networking_v1: Optional[Any] = None
        self._initialized = False
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._audit_log: List[Dict[str, Any]] = []

    def _ensure_initialized(self) -> bool:
        """
        Lazily initialize Kubernetes client.

        Returns:
            True if initialization successful, False otherwise.
        """
        if self._initialized:
            return self._core_v1 is not None

        if not K8S_AVAILABLE:
            logger.warning("Kubernetes client not available. Install with: pip install kubernetes")
            self._initialized = True
            return False

        try:
            # Try in-cluster config first (for pod-based deployments)
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            except config.ConfigException:
                # Fall back to local kubeconfig
                config.load_kube_config()
                logger.info("Loaded local kubeconfig configuration")

            self._core_v1 = client.CoreV1Api()
            self._networking_v1 = client.NetworkingV1Api()
            self._initialized = True
            return True

        except Exception as e:
            logger.warning(f"Failed to initialize Kubernetes client: {e}")
            self._initialized = True
            return False

    def _get_namespace_name(self, tenant_id: str) -> str:
        """Generate Kubernetes namespace name for a tenant."""
        return f"{self.config.namespace_prefix}{tenant_id}"

    def _log_audit(
        self,
        operation: str,
        tenant_id: str,
        result: K8sOperationResult,
    ) -> None:
        """Log Kubernetes operation for auditing."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "operation": operation,
            "tenant_id": tenant_id,
            "namespace": result.namespace,
            "resource_name": result.resource_name,
            "status": result.status.value,
            "message": result.message,
            "constitutional_hash": self._constitutional_hash,
        }

        self._audit_log.append(entry)

        # Keep bounded
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]

        if result.status == K8sOperationStatus.ERROR:
            logger.error(f"K8s operation failed: {entry}")
        else:
            logger.info(f"K8s operation: {operation} - {result.status.value}")

    async def _retry_operation(self, operation_func, *args, **kwargs) -> Any:
        """Execute operation with retry logic for transient failures."""
        last_exception = None

        for attempt in range(self.config.retry_attempts):
            try:
                # Run sync K8s operations in executor to avoid blocking
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: operation_func(*args, **kwargs))
                return result
            except ApiException as e:
                # Don't retry client errors (4xx)
                if 400 <= e.status < 500:
                    raise
                last_exception = e
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)
            except Exception as e:
                last_exception = e
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)

        raise last_exception

    async def create_tenant_namespace(
        self,
        tenant_id: str,
        labels: Optional[Dict[str, str]] = None,
    ) -> K8sOperationResult:
        """
        Create a Kubernetes namespace for a tenant.

        Args:
            tenant_id: Unique tenant identifier
            labels: Additional labels to apply to the namespace

        Returns:
            K8sOperationResult with operation status
        """
        namespace_name = self._get_namespace_name(tenant_id)

        if not self._ensure_initialized():
            result = K8sOperationResult(
                status=K8sOperationStatus.UNAVAILABLE,
                resource_name=namespace_name,
                namespace=namespace_name,
                message="Kubernetes client not available",
            )
            if self.config.fail_safe:
                self._log_audit("create_namespace", tenant_id, result)
                return result
            raise RuntimeError("Kubernetes client not available")

        # Build namespace labels
        namespace_labels = {
            "tenant-id": tenant_id,
            "managed-by": "acgs2",
            "constitutional-hash": self._constitutional_hash,
        }
        if labels:
            namespace_labels.update(labels)

        namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=namespace_name,
                labels=namespace_labels,
            )
        )

        try:
            await self._retry_operation(self._core_v1.create_namespace, body=namespace)
            result = K8sOperationResult(
                status=K8sOperationStatus.SUCCESS,
                resource_name=namespace_name,
                namespace=namespace_name,
                message=f"Namespace '{namespace_name}' created successfully",
            )
        except ApiException as e:
            if e.status == 409:  # Conflict - already exists
                result = K8sOperationResult(
                    status=K8sOperationStatus.ALREADY_EXISTS,
                    resource_name=namespace_name,
                    namespace=namespace_name,
                    message=f"Namespace '{namespace_name}' already exists",
                )
            else:
                result = K8sOperationResult(
                    status=K8sOperationStatus.ERROR,
                    resource_name=namespace_name,
                    namespace=namespace_name,
                    message=f"Failed to create namespace: {e.reason}",
                    details={"status_code": e.status, "body": str(e.body)[:500]},
                )

        self._log_audit("create_namespace", tenant_id, result)
        return result

    async def create_resource_quota(
        self,
        tenant_id: str,
        cpu: Optional[str] = None,
        memory: Optional[str] = None,
        storage: Optional[str] = None,
        max_pods: Optional[int] = None,
        max_pvcs: Optional[int] = None,
    ) -> K8sOperationResult:
        """
        Create or update a ResourceQuota for a tenant namespace.

        Args:
            tenant_id: Unique tenant identifier
            cpu: CPU quota (e.g., '2' or '2000m')
            memory: Memory quota (e.g., '4Gi')
            storage: Storage quota (e.g., '20Gi')
            max_pods: Maximum number of pods
            max_pvcs: Maximum number of PersistentVolumeClaims

        Returns:
            K8sOperationResult with operation status
        """
        namespace_name = self._get_namespace_name(tenant_id)
        quota_name = "tenant-quota"

        if not self._ensure_initialized():
            result = K8sOperationResult(
                status=K8sOperationStatus.UNAVAILABLE,
                resource_name=quota_name,
                namespace=namespace_name,
                message="Kubernetes client not available",
            )
            if self.config.fail_safe:
                self._log_audit("create_resource_quota", tenant_id, result)
                return result
            raise RuntimeError("Kubernetes client not available")

        # Use defaults if not specified
        cpu = cpu or self.config.default_cpu_quota
        memory = memory or self.config.default_memory_quota
        storage = storage or self.config.default_storage_quota
        max_pods = max_pods if max_pods is not None else self.config.default_max_pods
        max_pvcs = max_pvcs if max_pvcs is not None else self.config.default_max_pvcs

        quota = client.V1ResourceQuota(
            metadata=client.V1ObjectMeta(
                name=quota_name,
                labels={
                    "tenant-id": tenant_id,
                    "managed-by": "acgs2",
                },
            ),
            spec=client.V1ResourceQuotaSpec(
                hard={
                    "requests.cpu": cpu,
                    "requests.memory": memory,
                    "limits.cpu": cpu,
                    "limits.memory": memory,
                    "persistentvolumeclaims": str(max_pvcs),
                    "requests.storage": storage,
                    "pods": str(max_pods),
                }
            ),
        )

        try:
            await self._retry_operation(
                self._core_v1.create_namespaced_resource_quota,
                namespace=namespace_name,
                body=quota,
            )
            result = K8sOperationResult(
                status=K8sOperationStatus.SUCCESS,
                resource_name=quota_name,
                namespace=namespace_name,
                message=f"ResourceQuota '{quota_name}' created successfully",
                details={
                    "cpu": cpu,
                    "memory": memory,
                    "storage": storage,
                    "max_pods": max_pods,
                    "max_pvcs": max_pvcs,
                },
            )
        except ApiException as e:
            if e.status == 409:  # Conflict - already exists, try to update
                try:
                    await self._retry_operation(
                        self._core_v1.replace_namespaced_resource_quota,
                        name=quota_name,
                        namespace=namespace_name,
                        body=quota,
                    )
                    result = K8sOperationResult(
                        status=K8sOperationStatus.SUCCESS,
                        resource_name=quota_name,
                        namespace=namespace_name,
                        message=f"ResourceQuota '{quota_name}' updated successfully",
                        details={
                            "cpu": cpu,
                            "memory": memory,
                            "storage": storage,
                            "max_pods": max_pods,
                            "max_pvcs": max_pvcs,
                        },
                    )
                except ApiException as update_error:
                    result = K8sOperationResult(
                        status=K8sOperationStatus.ERROR,
                        resource_name=quota_name,
                        namespace=namespace_name,
                        message=f"Failed to update ResourceQuota: {update_error.reason}",
                        details={"status_code": update_error.status},
                    )
            elif e.status == 404:  # Namespace not found
                result = K8sOperationResult(
                    status=K8sOperationStatus.NOT_FOUND,
                    resource_name=quota_name,
                    namespace=namespace_name,
                    message=f"Namespace '{namespace_name}' not found",
                )
            else:
                result = K8sOperationResult(
                    status=K8sOperationStatus.ERROR,
                    resource_name=quota_name,
                    namespace=namespace_name,
                    message=f"Failed to create ResourceQuota: {e.reason}",
                    details={"status_code": e.status},
                )

        self._log_audit("create_resource_quota", tenant_id, result)
        return result

    async def create_limit_range(
        self,
        tenant_id: str,
        default_cpu: str = "100m",
        default_memory: str = "128Mi",
        max_cpu: str = "1",
        max_memory: str = "1Gi",
    ) -> K8sOperationResult:
        """
        Create a LimitRange for default container limits in tenant namespace.

        Args:
            tenant_id: Unique tenant identifier
            default_cpu: Default CPU request/limit for containers
            default_memory: Default memory request/limit for containers
            max_cpu: Maximum CPU limit for containers
            max_memory: Maximum memory limit for containers

        Returns:
            K8sOperationResult with operation status
        """
        namespace_name = self._get_namespace_name(tenant_id)
        limit_range_name = "tenant-limits"

        if not self._ensure_initialized():
            result = K8sOperationResult(
                status=K8sOperationStatus.UNAVAILABLE,
                resource_name=limit_range_name,
                namespace=namespace_name,
                message="Kubernetes client not available",
            )
            if self.config.fail_safe:
                self._log_audit("create_limit_range", tenant_id, result)
                return result
            raise RuntimeError("Kubernetes client not available")

        limit_range = client.V1LimitRange(
            metadata=client.V1ObjectMeta(
                name=limit_range_name,
                labels={
                    "tenant-id": tenant_id,
                    "managed-by": "acgs2",
                },
            ),
            spec=client.V1LimitRangeSpec(
                limits=[
                    client.V1LimitRangeItem(
                        type="Container",
                        default={"cpu": default_cpu, "memory": default_memory},
                        default_request={"cpu": default_cpu, "memory": default_memory},
                        max={"cpu": max_cpu, "memory": max_memory},
                    )
                ]
            ),
        )

        try:
            await self._retry_operation(
                self._core_v1.create_namespaced_limit_range,
                namespace=namespace_name,
                body=limit_range,
            )
            result = K8sOperationResult(
                status=K8sOperationStatus.SUCCESS,
                resource_name=limit_range_name,
                namespace=namespace_name,
                message=f"LimitRange '{limit_range_name}' created successfully",
            )
        except ApiException as e:
            if e.status == 409:
                result = K8sOperationResult(
                    status=K8sOperationStatus.ALREADY_EXISTS,
                    resource_name=limit_range_name,
                    namespace=namespace_name,
                    message=f"LimitRange '{limit_range_name}' already exists",
                )
            elif e.status == 404:
                result = K8sOperationResult(
                    status=K8sOperationStatus.NOT_FOUND,
                    resource_name=limit_range_name,
                    namespace=namespace_name,
                    message=f"Namespace '{namespace_name}' not found",
                )
            else:
                result = K8sOperationResult(
                    status=K8sOperationStatus.ERROR,
                    resource_name=limit_range_name,
                    namespace=namespace_name,
                    message=f"Failed to create LimitRange: {e.reason}",
                )

        self._log_audit("create_limit_range", tenant_id, result)
        return result

    async def create_network_policy(
        self,
        tenant_id: str,
        allow_same_namespace: bool = True,
        allow_kube_system_dns: bool = True,
    ) -> K8sOperationResult:
        """
        Create a NetworkPolicy for tenant namespace isolation.

        Args:
            tenant_id: Unique tenant identifier
            allow_same_namespace: Allow traffic within the same namespace
            allow_kube_system_dns: Allow DNS traffic to kube-system

        Returns:
            K8sOperationResult with operation status
        """
        namespace_name = self._get_namespace_name(tenant_id)
        policy_name = "tenant-isolation"

        if not self._ensure_initialized():
            result = K8sOperationResult(
                status=K8sOperationStatus.UNAVAILABLE,
                resource_name=policy_name,
                namespace=namespace_name,
                message="Kubernetes client not available",
            )
            if self.config.fail_safe:
                self._log_audit("create_network_policy", tenant_id, result)
                return result
            raise RuntimeError("Kubernetes client not available")

        ingress_rules = []
        egress_rules = []

        # Allow traffic from same namespace
        if allow_same_namespace:
            ingress_rules.append(
                client.V1NetworkPolicyIngressRule(
                    from_=[
                        client.V1NetworkPolicyPeer(
                            namespace_selector=client.V1LabelSelector(
                                match_labels={"tenant-id": tenant_id}
                            )
                        )
                    ]
                )
            )
            egress_rules.append(
                client.V1NetworkPolicyEgressRule(
                    to=[
                        client.V1NetworkPolicyPeer(
                            namespace_selector=client.V1LabelSelector(
                                match_labels={"tenant-id": tenant_id}
                            )
                        )
                    ]
                )
            )

        # Allow DNS to kube-system
        if allow_kube_system_dns:
            egress_rules.append(
                client.V1NetworkPolicyEgressRule(
                    to=[
                        client.V1NetworkPolicyPeer(
                            namespace_selector=client.V1LabelSelector(
                                match_labels={"kubernetes.io/metadata.name": "kube-system"}
                            )
                        )
                    ],
                    ports=[
                        client.V1NetworkPolicyPort(port=53, protocol="UDP"),
                        client.V1NetworkPolicyPort(port=53, protocol="TCP"),
                    ],
                )
            )

        network_policy = client.V1NetworkPolicy(
            metadata=client.V1ObjectMeta(
                name=policy_name,
                labels={
                    "tenant-id": tenant_id,
                    "managed-by": "acgs2",
                },
            ),
            spec=client.V1NetworkPolicySpec(
                pod_selector=client.V1LabelSelector(),  # Apply to all pods
                policy_types=["Ingress", "Egress"],
                ingress=ingress_rules if ingress_rules else None,
                egress=egress_rules if egress_rules else None,
            ),
        )

        try:
            await self._retry_operation(
                self._networking_v1.create_namespaced_network_policy,
                namespace=namespace_name,
                body=network_policy,
            )
            result = K8sOperationResult(
                status=K8sOperationStatus.SUCCESS,
                resource_name=policy_name,
                namespace=namespace_name,
                message=f"NetworkPolicy '{policy_name}' created successfully",
            )
        except ApiException as e:
            if e.status == 409:
                result = K8sOperationResult(
                    status=K8sOperationStatus.ALREADY_EXISTS,
                    resource_name=policy_name,
                    namespace=namespace_name,
                    message=f"NetworkPolicy '{policy_name}' already exists",
                )
            elif e.status == 404:
                result = K8sOperationResult(
                    status=K8sOperationStatus.NOT_FOUND,
                    resource_name=policy_name,
                    namespace=namespace_name,
                    message=f"Namespace '{namespace_name}' not found",
                )
            else:
                result = K8sOperationResult(
                    status=K8sOperationStatus.ERROR,
                    resource_name=policy_name,
                    namespace=namespace_name,
                    message=f"Failed to create NetworkPolicy: {e.reason}",
                )

        self._log_audit("create_network_policy", tenant_id, result)
        return result

    async def provision_tenant(
        self,
        tenant_id: str,
        cpu: Optional[str] = None,
        memory: Optional[str] = None,
        storage: Optional[str] = None,
        max_pods: Optional[int] = None,
        max_pvcs: Optional[int] = None,
        create_network_policy: bool = True,
        create_limit_range: bool = True,
    ) -> Dict[str, K8sOperationResult]:
        """
        Provision complete Kubernetes resources for a tenant.

        Creates namespace, resource quota, limit range, and network policy
        in a single operation with proper error handling.

        Args:
            tenant_id: Unique tenant identifier
            cpu: CPU quota override
            memory: Memory quota override
            storage: Storage quota override
            max_pods: Maximum pods override
            max_pvcs: Maximum PVCs override
            create_network_policy: Whether to create network isolation policy
            create_limit_range: Whether to create default container limits

        Returns:
            Dictionary of resource names to their operation results
        """
        results = {}

        # Step 1: Create namespace
        namespace_result = await self.create_tenant_namespace(tenant_id)
        results["namespace"] = namespace_result

        if not namespace_result.is_success():
            return results

        # Step 2: Create resource quota
        quota_result = await self.create_resource_quota(
            tenant_id,
            cpu=cpu,
            memory=memory,
            storage=storage,
            max_pods=max_pods,
            max_pvcs=max_pvcs,
        )
        results["resource_quota"] = quota_result

        # Step 3: Create limit range (optional)
        if create_limit_range:
            limit_result = await self.create_limit_range(tenant_id)
            results["limit_range"] = limit_result

        # Step 4: Create network policy (optional)
        if create_network_policy:
            policy_result = await self.create_network_policy(tenant_id)
            results["network_policy"] = policy_result

        return results

    async def delete_tenant_namespace(
        self,
        tenant_id: str,
        grace_period_seconds: int = 30,
    ) -> K8sOperationResult:
        """
        Delete a tenant namespace and all its resources.

        Args:
            tenant_id: Unique tenant identifier
            grace_period_seconds: Grace period for pod termination

        Returns:
            K8sOperationResult with operation status
        """
        namespace_name = self._get_namespace_name(tenant_id)

        if not self._ensure_initialized():
            result = K8sOperationResult(
                status=K8sOperationStatus.UNAVAILABLE,
                resource_name=namespace_name,
                namespace=namespace_name,
                message="Kubernetes client not available",
            )
            if self.config.fail_safe:
                self._log_audit("delete_namespace", tenant_id, result)
                return result
            raise RuntimeError("Kubernetes client not available")

        try:
            delete_options = client.V1DeleteOptions(
                grace_period_seconds=grace_period_seconds,
                propagation_policy="Foreground",
            )
            await self._retry_operation(
                self._core_v1.delete_namespace,
                name=namespace_name,
                body=delete_options,
            )
            result = K8sOperationResult(
                status=K8sOperationStatus.SUCCESS,
                resource_name=namespace_name,
                namespace=namespace_name,
                message=f"Namespace '{namespace_name}' deletion initiated",
            )
        except ApiException as e:
            if e.status == 404:
                result = K8sOperationResult(
                    status=K8sOperationStatus.NOT_FOUND,
                    resource_name=namespace_name,
                    namespace=namespace_name,
                    message=f"Namespace '{namespace_name}' not found",
                )
            else:
                result = K8sOperationResult(
                    status=K8sOperationStatus.ERROR,
                    resource_name=namespace_name,
                    namespace=namespace_name,
                    message=f"Failed to delete namespace: {e.reason}",
                )

        self._log_audit("delete_namespace", tenant_id, result)
        return result

    async def get_tenant_quota_usage(
        self,
        tenant_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get current resource usage for a tenant namespace.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            Dictionary with quota usage details or None if unavailable
        """
        namespace_name = self._get_namespace_name(tenant_id)

        if not self._ensure_initialized():
            return None

        try:
            quotas = await self._retry_operation(
                self._core_v1.list_namespaced_resource_quota,
                namespace=namespace_name,
            )

            if not quotas.items:
                return None

            quota = quotas.items[0]
            return {
                "namespace": namespace_name,
                "hard": quota.status.hard if quota.status else {},
                "used": quota.status.used if quota.status else {},
                "name": quota.metadata.name,
            }
        except ApiException:
            return None

    async def namespace_exists(self, tenant_id: str) -> bool:
        """
        Check if a tenant namespace exists.

        Args:
            tenant_id: Unique tenant identifier

        Returns:
            True if namespace exists, False otherwise
        """
        namespace_name = self._get_namespace_name(tenant_id)

        if not self._ensure_initialized():
            return False

        try:
            await self._retry_operation(self._core_v1.read_namespace, name=namespace_name)
            return True
        except ApiException as e:
            if e.status == 404:
                return False
            raise

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get Kubernetes operation audit log."""
        return self._audit_log[-limit:]


@lru_cache()
def get_k8s_resource_manager() -> K8sResourceManager:
    """
    Get the global Kubernetes resource manager instance.

    Uses lru_cache for consistency with FastAPI dependency injection patterns.
    """
    return K8sResourceManager()


# Convenience functions for common operations


async def create_tenant_resources(
    tenant_id: str,
    cpu: Optional[str] = None,
    memory: Optional[str] = None,
    storage: Optional[str] = None,
) -> Dict[str, K8sOperationResult]:
    """
    Convenience function to provision all tenant resources.

    Args:
        tenant_id: Unique tenant identifier
        cpu: CPU quota override
        memory: Memory quota override
        storage: Storage quota override

    Returns:
        Dictionary of resource names to their operation results
    """
    manager = get_k8s_resource_manager()
    return await manager.provision_tenant(
        tenant_id,
        cpu=cpu,
        memory=memory,
        storage=storage,
    )


async def delete_tenant_resources(tenant_id: str) -> K8sOperationResult:
    """
    Convenience function to delete all tenant resources.

    Args:
        tenant_id: Unique tenant identifier

    Returns:
        K8sOperationResult with operation status
    """
    manager = get_k8s_resource_manager()
    return await manager.delete_tenant_namespace(tenant_id)


__all__ = [
    "K8sResourceManager",
    "K8sConfig",
    "K8sOperationResult",
    "K8sOperationStatus",
    "K8S_AVAILABLE",
    "CONSTITUTIONAL_HASH",
    "get_k8s_resource_manager",
    "create_tenant_resources",
    "delete_tenant_resources",
]
