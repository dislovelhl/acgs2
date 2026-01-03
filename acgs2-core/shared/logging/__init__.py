"""
ACGS-2 Logging Module
Constitutional Hash: cdd01ef066bc6cf2

Centralized logging utilities for the ACGS-2 platform:
- Tenant-scoped audit logging with access controls
- Structured logging for compliance and security
- Audit trail for multi-tenant operations
"""

from .audit_logger import (
    AUDIT_LOGGER_AVAILABLE,
    AuditAction,
    AuditEntry,
    AuditLogConfig,
    AuditLogStore,
    AuditQueryParams,
    AuditQueryResult,
    AuditSeverity,
    InMemoryAuditStore,
    RedisAuditStore,
    TenantAuditLogger,
    create_tenant_audit_logger,
    get_tenant_audit_logger,
)

__all__ = [
    # Main logger
    "TenantAuditLogger",
    "create_tenant_audit_logger",
    "get_tenant_audit_logger",
    # Configuration
    "AuditLogConfig",
    # Audit entries
    "AuditEntry",
    "AuditAction",
    "AuditSeverity",
    # Query
    "AuditQueryParams",
    "AuditQueryResult",
    # Storage backends
    "AuditLogStore",
    "InMemoryAuditStore",
    "RedisAuditStore",
    # Feature flags
    "AUDIT_LOGGER_AVAILABLE",
]
