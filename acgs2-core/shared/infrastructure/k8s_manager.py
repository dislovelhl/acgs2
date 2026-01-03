"""
Kubernetes namespace and resource quota manager
"""

import logging

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    K8S_AVAILABLE = True
except ImportError:
    K8S_AVAILABLE = False

logger = logging.getLogger(__name__)


class K8sManager:
    """
    Manages Kubernetes resources for tenant isolation.
    """

    def __init__(self):
        if K8S_AVAILABLE:
            try:
                config.load_incluster_config()
            except Exception:
                try:
                    config.load_kube_config()
                except Exception:
                    logger.warning("Kubernetes config not found, running in mock mode")

            self.core_v1 = client.CoreV1Api()
        else:
            logger.warning("kubernetes package not installed, running in mock mode")

    def create_tenant_namespace(self, tenant_id: str) -> bool:
        """Create an isolated namespace for a tenant"""
        if not K8S_AVAILABLE:
            logger.info(f"[MOCK] Created namespace for tenant {tenant_id}")
            return True

        ns_name = f"tenant-{tenant_id}"
        namespace = client.V1Namespace(
            metadata=client.V1ObjectMeta(
                name=ns_name, labels={"tenant-id": tenant_id, "managed-by": "acgs2"}
            )
        )

        try:
            self.core_v1.create_namespace(namespace)
            logger.info(f"Created namespace {ns_name}")
            return True
        except client.exceptions.ApiException as e:
            if e.status == 409:  # Already exists
                return True
            logger.error(f"Failed to create namespace {ns_name}: {e}")
            return False

    def apply_resource_quota(self, tenant_id: str, cpu: str, memory: str, storage: str) -> bool:
        """Apply resource limits to a tenant namespace"""
        if not K8S_AVAILABLE:
            logger.info(
                f"[MOCK] Applied quota to tenant {tenant_id}: CPU={cpu}, Mem={memory}, Storage={storage}"
            )
            return True

        ns_name = f"tenant-{tenant_id}"
        quota_name = "tenant-quota"

        quota = client.V1ResourceQuota(
            metadata=client.V1ObjectMeta(name=quota_name),
            spec=client.V1ResourceQuotaSpec(
                hard={
                    "requests.cpu": cpu,
                    "limits.cpu": cpu,
                    "requests.memory": memory,
                    "limits.memory": memory,
                    "requests.storage": storage,
                    "persistentvolumeclaims": "10",
                }
            ),
        )

        try:
            try:
                self.core_v1.create_namespaced_resource_quota(ns_name, quota)
                logger.info(f"Created resource quota for {ns_name}")
            except client.exceptions.ApiException as e:
                if e.status == 409:
                    self.core_v1.replace_namespaced_resource_quota(quota_name, ns_name, quota)
                    logger.info(f"Updated resource quota for {ns_name}")
                else:
                    raise
            return True
        except Exception as e:
            logger.error(f"Failed to apply resource quota to {ns_name}: {e}")
            return False
