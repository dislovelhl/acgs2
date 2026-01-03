"""
ACGS-2 Configuration Package
Constitutional Hash: cdd01ef066bc6cf2

Configuration models and utilities for multi-tenant isolation.
"""

from shared.config.settings import (
    DatabaseSettings,
    RedisSettings,
    Settings,
    settings,
)
from shared.config.tenant_config import (
    TenantConfig,
    TenantQuotaConfig,
    TenantQuotaRegistry,
    create_tenant_config,
    get_default_tenant_quotas,
    get_tenant_quota_registry,
)

__all__ = [
    # Settings
    "Settings",
    "settings",
    "RedisSettings",
    "DatabaseSettings",
    # Tenant config
    "TenantConfig",
    "TenantQuotaConfig",
    "TenantQuotaRegistry",
    "create_tenant_config",
    "get_default_tenant_quotas",
    "get_tenant_quota_registry",
]
