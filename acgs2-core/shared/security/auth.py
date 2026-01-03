"""
ACGS-2 Authentication and Authorization Module
Constitutional Hash: cdd01ef066bc6cf2

Provides JWT-based authentication and role-based authorization for all services.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from shared.config import settings
from shared.logging import get_logger

logger = get_logger(__name__)

# Security schemes
security = HTTPBearer(auto_error=False)


class UserClaims(BaseModel):
    """JWT user claims model."""

    sub: str  # User ID
    tenant_id: str
    roles: List[str]
    permissions: List[str]
    exp: int
    iat: int
    iss: str = "acgs2"


class TokenResponse(BaseModel):
    """Token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    tenant_id: str


def create_access_token(
    user_id: str,
    tenant_id: str,
    roles: List[str] = None,
    permissions: List[str] = None,
    expires_delta: timedelta = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User identifier
        tenant_id: Tenant identifier
        roles: List of user roles
        permissions: List of user permissions
        expires_delta: Token expiration time

    Returns:
        JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(hours=1)

    expire = datetime.utcnow() + expires_delta

    to_encode = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "roles": roles or [],
        "permissions": permissions or [],
        "exp": expire,
        "iat": datetime.utcnow(),
        "iss": "acgs2",
    }

    if not settings.security.jwt_secret:
        raise ValueError("JWT_SECRET not configured")

    encoded_jwt = jwt.encode(
        to_encode, settings.security.jwt_secret.get_secret_value(), algorithm="HS256"
    )

    return encoded_jwt


def verify_token(token: str) -> UserClaims:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string

    Returns:
        UserClaims object

    Raises:
        HTTPException: If token is invalid
    """
    try:
        if not settings.security.jwt_secret:
            raise HTTPException(status_code=500, detail="JWT secret not configured")

        payload = jwt.decode(
            token, settings.security.jwt_secret.get_secret_value(), algorithms=["HS256"]
        )

        # Validate issuer
        if payload.get("iss") != "acgs2":
            raise HTTPException(status_code=401, detail="Invalid token issuer")

        return UserClaims(**payload)

    except JWTError as e:
        logger.warning("JWT verification failed", error=str(e))
        raise HTTPException(status_code=401, detail="Invalid authentication token") from e
    except Exception as e:
        logger.error("Token verification error", error=str(e))
        raise HTTPException(status_code=401, detail="Authentication failed") from e


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserClaims:
    """
    FastAPI dependency to get current authenticated user.

    Args:
        credentials: HTTP Bearer token credentials

    Returns:
        UserClaims for authenticated user

    Raises:
        HTTPException: If authentication fails
    """
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token(credentials.credentials)


async def get_current_user_optional(
    request: Request, credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Optional[UserClaims]:
    """
    Optional authentication - returns None if no token provided.

    Args:
        request: FastAPI request
        credentials: HTTP Bearer token credentials

    Returns:
        UserClaims if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        return verify_token(credentials.credentials)
    except HTTPException:
        return None


def require_role(required_role: str):
    """
    Create a dependency that requires a specific role.

    Args:
        required_role: Role that user must have

    Returns:
        Dependency function
    """

    async def role_checker(user: UserClaims = Depends(get_current_user)) -> UserClaims:
        if required_role not in user.roles:
            raise HTTPException(status_code=403, detail=f"Role '{required_role}' required")
        return user

    return role_checker


def require_permission(required_permission: str):
    """
    Create a dependency that requires a specific permission.

    Args:
        required_permission: Permission that user must have

    Returns:
        Dependency function
    """

    async def permission_checker(user: UserClaims = Depends(get_current_user)) -> UserClaims:
        if required_permission not in user.permissions:
            raise HTTPException(
                status_code=403, detail=f"Permission '{required_permission}' required"
            )
        return user

    return permission_checker


def require_tenant_access(tenant_id: str = None):
    """
    Create a dependency that ensures user has access to specified tenant.

    Args:
        tenant_id: Specific tenant ID to check (optional)

    Returns:
        Dependency function
    """

    async def tenant_checker(
        user: UserClaims = Depends(get_current_user), request: Request = None
    ) -> UserClaims:
        # If specific tenant_id provided, check it
        if tenant_id and user.tenant_id != tenant_id:
            raise HTTPException(status_code=403, detail="Access denied for this tenant")

        # If no specific tenant but request has tenant context, check it
        if request and hasattr(request.state, "tenant_id"):
            if user.tenant_id != request.state.tenant_id:
                raise HTTPException(status_code=403, detail="Tenant access denied")

        return user

    return tenant_checker


# ============================================================================
# FastAPI Middleware for Authentication
# ============================================================================

try:
    from fastapi.middleware.base import BaseHTTPMiddleware
except ImportError:
    # Fallback for older FastAPI versions
    from starlette.middleware.base import BaseHTTPMiddleware


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for automatic authentication.

    Adds user information to request state if token is present.
    """

    async def dispatch(self, request: Request, call_next):
        # Try to authenticate user
        user = await get_current_user_optional(request)

        if user:
            # Add user to request state
            request.state.user = user
            request.state.user_id = user.sub
            request.state.tenant_id = user.tenant_id
            request.state.user_roles = user.roles
            request.state.user_permissions = user.permissions

        # Continue with request
        response = await call_next(request)
        return response


# ============================================================================
# Utility Functions
# ============================================================================


def create_test_token(
    user_id: str = "test-user",
    tenant_id: str = "test-tenant",
    roles: List[str] = None,
    permissions: List[str] = None,
) -> str:
    """
    Create a test JWT token for testing purposes.

    Args:
        user_id: Test user ID
        tenant_id: Test tenant ID
        roles: Test user roles
        permissions: Test user permissions

    Returns:
        JWT token string
    """
    return create_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        roles=roles or ["user"],
        permissions=permissions or ["read"],
        expires_delta=timedelta(hours=24),  # Longer for testing
    )


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
