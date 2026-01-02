"""
ACGS-2 Security Module
Constitutional Hash: cdd01ef066bc6cf2

Centralized security utilities for the ACGS-2 platform:
- CORS configuration and validation
- Rate limiting middleware
- Tenant context middleware for multi-tenant isolation
- API key and token management
- Security headers enforcement
"""

from .cors_config import (
    DEFAULT_ORIGINS,
    CORSConfig,
    CORSEnvironment,
    detect_environment,
    get_cors_config,
    get_strict_cors_config,
    validate_origin,
)
from .rate_limiter import (
    REDIS_AVAILABLE,
    RateLimitAlgorithm,
    RateLimitConfig,
    RateLimitMiddleware,
    RateLimitResult,
    RateLimitRule,
    RateLimitScope,
    create_rate_limit_middleware,
)
from .tenant_context import (
    TENANT_ID_MAX_LENGTH,
    TENANT_ID_MIN_LENGTH,
    TENANT_ID_PATTERN,
    TenantContextConfig,
    TenantContextMiddleware,
    TenantValidationError,
    get_current_tenant_id,
    get_optional_tenant_id,
    get_tenant_id,
    require_tenant_scope,
    sanitize_tenant_id,
    validate_tenant_id,
)

__all__ = [
    # CORS
    "CORSConfig",
    "CORSEnvironment",
    "get_cors_config",
    "get_strict_cors_config",
    "detect_environment",
    "validate_origin",
    "DEFAULT_ORIGINS",
    # Rate Limiting
    "RateLimitMiddleware",
    "RateLimitConfig",
    "RateLimitRule",
    "RateLimitResult",
    "RateLimitScope",
    "RateLimitAlgorithm",
    "create_rate_limit_middleware",
    "REDIS_AVAILABLE",
    # Tenant Context
    "TenantContextMiddleware",
    "TenantContextConfig",
    "get_tenant_id",
    "get_optional_tenant_id",
    "get_current_tenant_id",
    "validate_tenant_id",
    "sanitize_tenant_id",
    "require_tenant_scope",
    "TenantValidationError",
    "TENANT_ID_MAX_LENGTH",
    "TENANT_ID_MIN_LENGTH",
    "TENANT_ID_PATTERN",
]
