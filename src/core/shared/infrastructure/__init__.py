"""
ACGS-2 Infrastructure Module
Constitutional Hash: cdd01ef066bc6cf2

Infrastructure management components for multi-tenant isolation.
"""

from src.core.shared.infrastructure.k8s_manager import (
    K8S_AVAILABLE,
    K8sConfig,
    K8sOperationResult,
    K8sOperationStatus,
    K8sResourceManager,
    create_tenant_resources,
    delete_tenant_resources,
    get_k8s_resource_manager,
)

__all__ = [
    "K8sResourceManager",
    "K8sConfig",
    "K8sOperationResult",
    "K8sOperationStatus",
    "K8S_AVAILABLE",
    "get_k8s_resource_manager",
    "create_tenant_resources",
    "delete_tenant_resources",
]
