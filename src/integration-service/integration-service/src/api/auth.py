"""
ACGS-2 Integration Service - Authentication Module

This module imports and re-exports authentication functions from the shared
security module for use in integration-service API endpoints.
"""

from src.core.shared.security.auth import (
    AuthenticationMiddleware,
    TokenResponse,
    UserClaims,
    create_access_token,
    create_test_token,
    get_current_user,
    get_current_user_optional,
    require_permission,
    require_role,
    require_tenant_access,
    security,
    verify_token,
)

# Re-export all authentication components
__all__ = [
    # Models
    "UserClaims",
    "TokenResponse",
    # Core functions
    "create_access_token",
    "verify_token",
    # Dependencies
    "get_current_user",
    "get_current_user_optional",
    "require_role",
    "require_permission",
    "require_tenant_access",
    # Middleware
    "AuthenticationMiddleware",
    # Utilities
    "create_test_token",
    # Security scheme
    "security",
]
