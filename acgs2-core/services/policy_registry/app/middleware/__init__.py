"""
ACGS-2 Policy Registry Middleware
Constitutional Hash: cdd01ef066bc6cf2
"""

from .rbac import (
    CONSTITUTIONAL_HASH,
    ROLE_PERMISSIONS,
    AccessDecision,
    Permission,
    RBACConfig,
    RBACMiddleware,
    Role,
    Scope,
    TokenClaims,
    configure_rbac,
    get_claims,
    get_rbac_middleware,
    require_permission,
    require_role,
    require_tenant_access,
)

__all__ = [
    "CONSTITUTIONAL_HASH",
    "Role",
    "Permission",
    "Scope",
    "ROLE_PERMISSIONS",
    "TokenClaims",
    "AccessDecision",
    "RBACConfig",
    "RBACMiddleware",
    "get_rbac_middleware",
    "configure_rbac",
    "require_permission",
    "require_role",
    "require_tenant_access",
    "get_claims",
]
