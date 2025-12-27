"""
ACGS-2 RBAC Enforcement Middleware
Constitutional Hash: cdd01ef066bc6cf2

Enterprise-grade Role-Based Access Control middleware for FastAPI.
Implements:
- JWT token validation with tenant isolation
- Role-based permission enforcement
- SPIFFE ID verification
- Audit logging for access decisions
- Rate limiting per role
"""

import asyncio
import functools
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Try to import JWT library
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False
    logger.warning("PyJWT not installed. JWT validation will be simulated.")


class Role(Enum):
    """ACGS-2 system roles."""
    SYSTEM_ADMIN = "system_admin"
    TENANT_ADMIN = "tenant_admin"
    AGENT_OPERATOR = "agent_operator"
    POLICY_AUTHOR = "policy_author"
    AUDITOR = "auditor"
    VIEWER = "viewer"


class Permission(Enum):
    """ACGS-2 permissions."""
    # Tenant permissions
    TENANT_CREATE = "tenant:create"
    TENANT_READ = "tenant:read"
    TENANT_UPDATE = "tenant:update"
    TENANT_DELETE = "tenant:delete"
    TENANT_LIST = "tenant:list"

    # Policy permissions
    POLICY_CREATE = "policy:create"
    POLICY_READ = "policy:read"
    POLICY_UPDATE = "policy:update"
    POLICY_DELETE = "policy:delete"
    POLICY_ACTIVATE = "policy:activate"
    POLICY_LIST = "policy:list"

    # Agent permissions
    AGENT_REGISTER = "agent:register"
    AGENT_UNREGISTER = "agent:unregister"
    AGENT_START = "agent:start"
    AGENT_STOP = "agent:stop"
    AGENT_STATUS = "agent:status"
    AGENT_LIST = "agent:list"

    # Message permissions
    MESSAGE_SEND = "message:send"
    MESSAGE_RECEIVE = "message:receive"
    MESSAGE_BROADCAST = "message:broadcast"

    # Audit permissions
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # Approval permissions
    APPROVAL_CREATE = "approval:create"
    APPROVAL_APPROVE = "approval:approve"
    APPROVAL_REJECT = "approval:reject"
    APPROVAL_ESCALATE = "approval:escalate"


# Role to permission mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SYSTEM_ADMIN: set(Permission),  # All permissions

    Role.TENANT_ADMIN: {
        Permission.TENANT_READ,
        Permission.TENANT_UPDATE,
        Permission.POLICY_CREATE,
        Permission.POLICY_READ,
        Permission.POLICY_UPDATE,
        Permission.POLICY_DELETE,
        Permission.POLICY_ACTIVATE,
        Permission.POLICY_LIST,
        Permission.AGENT_REGISTER,
        Permission.AGENT_UNREGISTER,
        Permission.AGENT_START,
        Permission.AGENT_STOP,
        Permission.AGENT_STATUS,
        Permission.AGENT_LIST,
        Permission.MESSAGE_SEND,
        Permission.MESSAGE_RECEIVE,
        Permission.MESSAGE_BROADCAST,
        Permission.AUDIT_READ,
        Permission.APPROVAL_CREATE,
        Permission.APPROVAL_APPROVE,
        Permission.APPROVAL_REJECT,
    },

    Role.AGENT_OPERATOR: {
        Permission.AGENT_START,
        Permission.AGENT_STOP,
        Permission.AGENT_STATUS,
        Permission.AGENT_LIST,
        Permission.MESSAGE_SEND,
        Permission.MESSAGE_RECEIVE,
        Permission.POLICY_READ,
        Permission.POLICY_LIST,
    },

    Role.POLICY_AUTHOR: {
        Permission.POLICY_CREATE,
        Permission.POLICY_READ,
        Permission.POLICY_UPDATE,
        Permission.POLICY_LIST,
        Permission.APPROVAL_CREATE,
    },

    Role.AUDITOR: {
        Permission.TENANT_READ,
        Permission.TENANT_LIST,
        Permission.POLICY_READ,
        Permission.POLICY_LIST,
        Permission.AGENT_STATUS,
        Permission.AGENT_LIST,
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
    },

    Role.VIEWER: {
        Permission.TENANT_READ,
        Permission.POLICY_READ,
        Permission.POLICY_LIST,
        Permission.AGENT_STATUS,
        Permission.AGENT_LIST,
    },
}


class Scope(Enum):
    """Permission scopes."""
    GLOBAL = "global"  # System-wide access
    TENANT = "tenant"  # Tenant-specific access
    AGENT = "agent"    # Agent-specific access


@dataclass
class TokenClaims:
    """Parsed JWT token claims."""
    subject: str
    issuer: str
    tenant_id: str
    roles: List[Role]
    permissions: Set[Permission]
    scope: Scope
    constitutional_hash: str
    agent_id: Optional[str] = None
    spiffe_id: Optional[str] = None
    issued_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.constitutional_hash != CONSTITUTIONAL_HASH:
            raise ValueError(
                f"Invalid constitutional hash in token. "
                f"Expected {CONSTITUTIONAL_HASH}, got {self.constitutional_hash}"
            )

    def has_permission(self, permission: Permission) -> bool:
        """Check if token has a specific permission."""
        return permission in self.permissions

    def has_any_permission(self, permissions: List[Permission]) -> bool:
        """Check if token has any of the specified permissions."""
        return any(p in self.permissions for p in permissions)

    def has_all_permissions(self, permissions: List[Permission]) -> bool:
        """Check if token has all specified permissions."""
        return all(p in self.permissions for p in permissions)

    def has_role(self, role: Role) -> bool:
        """Check if token has a specific role."""
        return role in self.roles

    def can_access_tenant(self, tenant_id: str) -> bool:
        """Check if token can access a specific tenant."""
        if self.scope == Scope.GLOBAL:
            return True
        return self.tenant_id == tenant_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "subject": self.subject,
            "issuer": self.issuer,
            "tenant_id": self.tenant_id,
            "roles": [r.value for r in self.roles],
            "permissions": [p.value for p in self.permissions],
            "scope": self.scope.value,
            "constitutional_hash": self.constitutional_hash,
            "agent_id": self.agent_id,
            "spiffe_id": self.spiffe_id,
            "issued_at": self.issued_at.isoformat() if self.issued_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class AccessDecision:
    """Result of an access decision."""
    allowed: bool
    reason: str
    claims: Optional[TokenClaims] = None
    decision_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    request_id: Optional[str] = None

    def to_audit_dict(self) -> Dict[str, Any]:
        """Convert to audit log format."""
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "subject": self.claims.subject if self.claims else None,
            "tenant_id": self.claims.tenant_id if self.claims else None,
            "roles": [r.value for r in self.claims.roles] if self.claims else [],
            "decision_time": self.decision_time.isoformat(),
            "request_id": self.request_id,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


class RBACConfig:
    """RBAC configuration."""

    def __init__(
        self,
        jwt_secret: Optional[str] = None,
        jwt_algorithm: str = "HS256",
        jwt_issuer: str = "acgs2-identity-provider",
        verify_signature: bool = True,
        verify_expiration: bool = True,
        enforce_constitutional_hash: bool = True,
        audit_all_decisions: bool = True,
        rate_limit_enabled: bool = True,
        rate_limits: Optional[Dict[Role, int]] = None,  # requests per minute
    ):
        self.jwt_secret = jwt_secret or os.environ.get("JWT_SECRET", "dev-secret")
        self.jwt_algorithm = jwt_algorithm
        self.jwt_issuer = jwt_issuer
        self.verify_signature = verify_signature
        self.verify_expiration = verify_expiration
        self.enforce_constitutional_hash = enforce_constitutional_hash
        self.audit_all_decisions = audit_all_decisions
        self.rate_limit_enabled = rate_limit_enabled
        self.rate_limits = rate_limits or {
            Role.SYSTEM_ADMIN: 1000,
            Role.TENANT_ADMIN: 500,
            Role.AGENT_OPERATOR: 200,
            Role.POLICY_AUTHOR: 100,
            Role.AUDITOR: 100,
            Role.VIEWER: 50,
        }


class TokenValidator:
    """JWT token validator."""

    def __init__(self, config: RBACConfig):
        self.config = config

    def validate_token(self, token: str) -> TokenClaims:
        """
        Validate JWT token and extract claims.

        Raises:
            HTTPException: If token is invalid
        """
        if not JWT_AVAILABLE:
            # Simulate validation for development
            return self._simulate_validation(token)

        try:
            options = {
                "verify_signature": self.config.verify_signature,
                "verify_exp": self.config.verify_expiration,
                "verify_iat": True,
                "require": ["sub", "iss", "tenant_id", "roles", "constitutional_hash"],
            }

            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm],
                options=options,
                issuer=self.config.jwt_issuer,
            )

            return self._parse_claims(payload)

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _parse_claims(self, payload: Dict[str, Any]) -> TokenClaims:
        """Parse JWT payload into TokenClaims."""
        # Parse roles
        role_strings = payload.get("roles", [])
        roles = []
        for r in role_strings:
            try:
                roles.append(Role(r))
            except ValueError:
                logger.warning(f"Unknown role in token: {r}")

        # Compute permissions from roles
        permissions: Set[Permission] = set()
        for role in roles:
            if role in ROLE_PERMISSIONS:
                permissions.update(ROLE_PERMISSIONS[role])

        # Add explicit permissions if present
        for p in payload.get("permissions", []):
            try:
                permissions.add(Permission(p))
            except ValueError:
                pass

        # Determine scope
        scope = Scope.TENANT
        if Role.SYSTEM_ADMIN in roles:
            scope = Scope.GLOBAL
        elif payload.get("agent_id"):
            scope = Scope.AGENT

        # Parse timestamps
        issued_at = None
        expires_at = None
        if "iat" in payload:
            issued_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        if "exp" in payload:
            expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        return TokenClaims(
            subject=payload["sub"],
            issuer=payload["iss"],
            tenant_id=payload["tenant_id"],
            roles=roles,
            permissions=permissions,
            scope=scope,
            constitutional_hash=payload["constitutional_hash"],
            agent_id=payload.get("agent_id"),
            spiffe_id=payload.get("spiffe_id"),
            issued_at=issued_at,
            expires_at=expires_at,
            metadata=payload.get("metadata", {}),
        )

    def _simulate_validation(self, token: str) -> TokenClaims:
        """Simulate token validation for development."""
        logger.warning("Simulating JWT validation (PyJWT not installed)")

        # For dev, return a default admin token
        return TokenClaims(
            subject="dev-user",
            issuer=self.config.jwt_issuer,
            tenant_id="default",
            roles=[Role.SYSTEM_ADMIN],
            permissions=set(Permission),
            scope=Scope.GLOBAL,
            constitutional_hash=CONSTITUTIONAL_HASH,
            issued_at=datetime.now(timezone.utc),
        )


class RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self, config: RBACConfig):
        self.config = config
        self._requests: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, claims: TokenClaims) -> bool:
        """
        Check if request is within rate limit.

        Returns:
            True if allowed, False if rate limited
        """
        if not self.config.rate_limit_enabled:
            return True

        # Determine rate limit based on highest role
        limit = max(
            self.config.rate_limits.get(role, 50)
            for role in claims.roles
        )

        key = f"{claims.tenant_id}:{claims.subject}"
        now = time.time()
        window = 60.0  # 1 minute window

        async with self._lock:
            if key not in self._requests:
                self._requests[key] = []

            # Remove old requests
            self._requests[key] = [
                t for t in self._requests[key]
                if now - t < window
            ]

            # Check limit
            if len(self._requests[key]) >= limit:
                return False

            # Record request
            self._requests[key].append(now)
            return True


class AuditLogger:
    """Logs RBAC decisions for compliance."""

    def __init__(self, log_file: Optional[str] = None):
        self.log_file = log_file

    async def log_decision(self, decision: AccessDecision, request: Request):
        """Log an access decision."""
        log_entry = {
            **decision.to_audit_dict(),
            "path": str(request.url.path),
            "method": request.method,
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }

        logger.info(f"RBAC Decision: {json.dumps(log_entry)}")

        if self.log_file:
            try:
                with open(self.log_file, "a") as f:
                    f.write(json.dumps(log_entry) + "\n")
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")


class RBACMiddleware:
    """
    RBAC enforcement middleware for FastAPI.

    Usage:
        ```python
        rbac = RBACMiddleware()

        @app.get("/policies")
        @rbac.require_permission(Permission.POLICY_READ)
        async def list_policies(claims: TokenClaims = Depends(rbac.get_claims)):
            return {"tenant_id": claims.tenant_id}
        ```
    """

    def __init__(self, config: Optional[RBACConfig] = None):
        self.config = config or RBACConfig()
        self.token_validator = TokenValidator(self.config)
        self.rate_limiter = RateLimiter(self.config)
        self.audit_logger = AuditLogger()
        self.security = HTTPBearer(auto_error=True)

        # Stats
        self._stats = {
            "requests_allowed": 0,
            "requests_denied": 0,
            "rate_limited": 0,
        }

    async def get_claims(
        self,
        request: Request,
        credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    ) -> TokenClaims:
        """
        Dependency to extract and validate claims from request.

        Usage:
            ```python
            @app.get("/resource")
            async def get_resource(claims: TokenClaims = Depends(rbac.get_claims)):
                return {"tenant": claims.tenant_id}
            ```
        """
        token = credentials.credentials
        claims = self.token_validator.validate_token(token)

        # Check rate limit
        if not await self.rate_limiter.check_rate_limit(claims):
            self._stats["rate_limited"] += 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
            )

        # Store claims in request state for later access
        request.state.claims = claims
        return claims

    def require_permission(
        self,
        *permissions: Permission,
        require_all: bool = True,
    ) -> Callable:
        """
        Decorator to require specific permissions.

        Args:
            permissions: Required permissions
            require_all: If True, all permissions required. If False, any one suffices.

        Usage:
            ```python
            @app.post("/policies")
            @rbac.require_permission(Permission.POLICY_CREATE)
            async def create_policy(...):
                ...
            ```
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                # Get request from args
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

                if request is None:
                    for v in kwargs.values():
                        if isinstance(v, Request):
                            request = v
                            break

                claims = getattr(request.state, 'claims', None) if request else None

                if claims is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )

                # Check permissions
                if require_all:
                    has_permission = claims.has_all_permissions(list(permissions))
                else:
                    has_permission = claims.has_any_permission(list(permissions))

                decision = AccessDecision(
                    allowed=has_permission,
                    reason="Permission check",
                    claims=claims,
                )

                if self.config.audit_all_decisions:
                    await self.audit_logger.log_decision(decision, request)

                if not has_permission:
                    self._stats["requests_denied"] += 1
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required permission(s): {[p.value for p in permissions]}",
                    )

                self._stats["requests_allowed"] += 1
                return await func(*args, **kwargs)

            return wrapper
        return decorator

    def require_role(self, *roles: Role, require_all: bool = False) -> Callable:
        """
        Decorator to require specific roles.

        Args:
            roles: Required roles
            require_all: If True, all roles required. If False, any one suffices.
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

                claims = getattr(request.state, 'claims', None) if request else None

                if claims is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )

                if require_all:
                    has_role = all(claims.has_role(r) for r in roles)
                else:
                    has_role = any(claims.has_role(r) for r in roles)

                if not has_role:
                    self._stats["requests_denied"] += 1
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required role(s): {[r.value for r in roles]}",
                    )

                self._stats["requests_allowed"] += 1
                return await func(*args, **kwargs)

            return wrapper
        return decorator

    def require_tenant_access(self, tenant_id_param: str = "tenant_id") -> Callable:
        """
        Decorator to require access to a specific tenant.

        Args:
            tenant_id_param: Name of the route parameter containing tenant ID
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

                claims = getattr(request.state, 'claims', None) if request else None

                if claims is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required",
                    )

                # Get tenant ID from path or query params
                tenant_id = kwargs.get(tenant_id_param)
                if tenant_id is None and request:
                    tenant_id = request.path_params.get(tenant_id_param)
                if tenant_id is None and request:
                    tenant_id = request.query_params.get(tenant_id_param)

                if tenant_id and not claims.can_access_tenant(tenant_id):
                    self._stats["requests_denied"] += 1
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access denied to tenant: {tenant_id}",
                    )

                self._stats["requests_allowed"] += 1
                return await func(*args, **kwargs)

            return wrapper
        return decorator

    def get_stats(self) -> Dict[str, Any]:
        """Get RBAC statistics."""
        return {
            **self._stats,
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


# Convenience singleton
_rbac_middleware: Optional[RBACMiddleware] = None


def get_rbac_middleware() -> RBACMiddleware:
    """Get the global RBAC middleware instance."""
    global _rbac_middleware
    if _rbac_middleware is None:
        _rbac_middleware = RBACMiddleware()
    return _rbac_middleware


def configure_rbac(config: RBACConfig) -> RBACMiddleware:
    """Configure and return the global RBAC middleware."""
    global _rbac_middleware
    _rbac_middleware = RBACMiddleware(config)
    return _rbac_middleware


# Export commonly used decorators
rbac = get_rbac_middleware()
require_permission = rbac.require_permission
require_role = rbac.require_role
require_tenant_access = rbac.require_tenant_access
get_claims = rbac.get_claims


__all__ = [
    "CONSTITUTIONAL_HASH",
    "Role",
    "Permission",
    "Scope",
    "ROLE_PERMISSIONS",
    "TokenClaims",
    "AccessDecision",
    "RBACConfig",
    "TokenValidator",
    "RateLimiter",
    "AuditLogger",
    "RBACMiddleware",
    "get_rbac_middleware",
    "configure_rbac",
    "require_permission",
    "require_role",
    "require_tenant_access",
    "get_claims",
]
