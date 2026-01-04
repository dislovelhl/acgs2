"""
ACGS-2 Configuration Package
Constitutional Hash: cdd01ef066bc6cf2

Configuration models and utilities for multi-tenant isolation.
"""

from .unified import (
    AuditSettings,
    AWSSettings,
    BundleSettings,
    MACISettings,
    OPASettings,
    QualitySettings,
    RedisSettings,
    SearchPlatformSettings,
    SecuritySettings,
    ServiceSettings,
    Settings,
    TelemetrySettings,
    VaultSettings,
    VotingSettings,
    get_settings,
    settings,
)
from .tenant_config import (
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
    "get_settings",
    "RedisSettings",
    "SecuritySettings",
    "OPASettings",
    "AuditSettings",
    "BundleSettings",
    "ServiceSettings",
    "TelemetrySettings",
    "AWSSettings",
    "SearchPlatformSettings",
    "QualitySettings",
    "MACISettings",
    "VaultSettings",
    "VotingSettings",
    # Tenant config
    "TenantConfig",
    "TenantQuotaConfig",
    "TenantQuotaRegistry",
    "create_tenant_config",
    "get_default_tenant_quotas",
    "get_tenant_quota_registry",
]
