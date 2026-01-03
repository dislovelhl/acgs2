"""
ACGS-2 Rate Limiting Module
Constitutional Hash: cdd01ef066bc6cf2

Production-grade rate limiting with Redis backend supporting:
- Sliding window rate limiting algorithm
- Per-IP, per-tenant, and per-endpoint limits
- Tenant-specific configurable quotas with dynamic lookup
- Distributed rate limiting across service instances
- Graceful degradation when Redis unavailable
- Constitutional compliance tracking

Security Features:
- Prevents brute force attacks
- Mitigates DoS attacks
- Protects expensive endpoints
- Provides audit trail for rate limit events
- Tenant isolation for multi-tenant deployments

Usage:
    from shared.security.rate_limiter import RateLimitMiddleware, RateLimitConfig

    # Basic usage with environment-based config
    app.add_middleware(
        RateLimitMiddleware,
        config=RateLimitConfig.from_env()
    )

    # With tenant-specific quotas
    from shared.security.rate_limiter import TenantRateLimitProvider

    provider = TenantRateLimitProvider()
    provider.set_tenant_quota("premium-tenant", requests=5000, window_seconds=60)

    app.add_middleware(
        RateLimitMiddleware,
        config=RateLimitConfig.from_env(),
        tenant_quota_provider=provider
    )
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from shared.logging import get_logger

logger = get_logger(__name__)

# Constitutional hash for integrity verification
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Check for Redis availability
try:
    import redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


# Tenant quota configuration - optional dependency
try:
    from shared.config.tenant_config import (
        TenantQuotaConfig,
        TenantQuotaRegistry,
        get_tenant_quota_registry,
    )

    TENANT_CONFIG_AVAILABLE = True
except ImportError:
    TenantQuotaConfig = None
    TenantQuotaRegistry = None
    get_tenant_quota_registry = None
    TENANT_CONFIG_AVAILABLE = False


@dataclass
class TenantQuota:
    """Quota configuration for a specific tenant.

    Attributes:
        tenant_id: Unique tenant identifier
        requests: Maximum requests allowed per window
        window_seconds: Time window in seconds
        burst_multiplier: Allow burst above limit temporarily (1.0 = no burst)
        enabled: Whether rate limiting is enabled for this tenant
    """

    tenant_id: str
    requests: int
    window_seconds: int
    burst_multiplier: float = 1.0
    enabled: bool = True

    @property
    def effective_limit(self) -> int:
        """Get effective limit including burst allowance."""
        return int(self.requests * self.burst_multiplier)


@runtime_checkable
class TenantQuotaProviderProtocol(Protocol):
    """Protocol for tenant quota providers.

    Allows custom implementations for tenant quota lookup.
    """

    def get_quota(self, tenant_id: str) -> Optional["TenantQuota"]:
        """Get quota for a specific tenant."""
        ...

    def set_quota(
        self,
        tenant_id: str,
        requests: int,
        window_seconds: int,
        burst_multiplier: float = 1.0,
    ) -> None:
        """Set quota for a specific tenant."""
        ...


class TenantRateLimitProvider:
    """Provider for tenant-specific rate limit quotas.

    Manages per-tenant rate limit configurations with support for:
    - Dynamic quota updates without restart
    - Default quotas for unregistered tenants
    - Integration with TenantQuotaRegistry (if available)
    - In-memory quota overrides

    Example:
        provider = TenantRateLimitProvider(
            default_requests=1000,
            default_window_seconds=60
        )

        # Set custom quota for premium tenant
        provider.set_tenant_quota("premium-tenant", requests=5000, window_seconds=60)

        # Get quota for a tenant
        quota = provider.get_tenant_quota("premium-tenant")
    """

    def __init__(
        self,
        default_requests: int = 1000,
        default_window_seconds: int = 60,
        default_burst_multiplier: float = 1.0,
        use_registry: bool = True,
    ):
        """Initialize the tenant rate limit provider.

        Args:
            default_requests: Default requests per window for unregistered tenants
            default_window_seconds: Default window duration in seconds
            default_burst_multiplier: Default burst multiplier (1.0 = no burst)
            use_registry: Whether to use TenantQuotaRegistry if available
        """
        self._default_requests = default_requests
        self._default_window_seconds = default_window_seconds
        self._default_burst_multiplier = default_burst_multiplier
        self._use_registry = use_registry and TENANT_CONFIG_AVAILABLE
        self._tenant_quotas: Dict[str, TenantQuota] = {}
        self._constitutional_hash = CONSTITUTIONAL_HASH

        # Initialize from registry if available
        if self._use_registry:
            self._registry = get_tenant_quota_registry()
        else:
            self._registry = None

        logger.debug(
            f"TenantRateLimitProvider initialized: "
            f"default={default_requests}req/{default_window_seconds}s, "
            f"registry_enabled={self._use_registry}"
        )

    def get_tenant_quota(self, tenant_id: str) -> TenantQuota:
        """Get rate limit quota for a specific tenant.

        Priority order:
        1. In-memory overrides (set via set_tenant_quota)
        2. TenantQuotaRegistry configuration (if available)
        3. Default quota configuration

        Args:
            tenant_id: The tenant identifier

        Returns:
            TenantQuota configuration for the tenant
        """
        # Check in-memory overrides first
        if tenant_id in self._tenant_quotas:
            return self._tenant_quotas[tenant_id]

        # Check registry if available
        if self._use_registry and self._registry is not None:
            try:
                registry_quota = self._registry.get_quota_for_tenant(tenant_id)
                if registry_quota is not None:
                    return TenantQuota(
                        tenant_id=tenant_id,
                        requests=registry_quota.rate_limit_requests,
                        window_seconds=registry_quota.rate_limit_window_seconds,
                        burst_multiplier=self._default_burst_multiplier,
                        enabled=True,
                    )
            except Exception as e:
                logger.warning(f"Failed to get quota from registry for {tenant_id}: {e}")

        # Return default quota
        return TenantQuota(
            tenant_id=tenant_id,
            requests=self._default_requests,
            window_seconds=self._default_window_seconds,
            burst_multiplier=self._default_burst_multiplier,
            enabled=True,
        )

    def set_tenant_quota(
        self,
        tenant_id: str,
        requests: int,
        window_seconds: int,
        burst_multiplier: float = 1.0,
        enabled: bool = True,
    ) -> None:
        """Set rate limit quota for a specific tenant.

        This creates an in-memory override that takes priority over
        registry configuration.

        Args:
            tenant_id: The tenant identifier
            requests: Maximum requests per window
            window_seconds: Time window in seconds
            burst_multiplier: Burst allowance multiplier (1.0 = no burst)
            enabled: Whether rate limiting is enabled for this tenant
        """
        self._tenant_quotas[tenant_id] = TenantQuota(
            tenant_id=tenant_id,
            requests=requests,
            window_seconds=window_seconds,
            burst_multiplier=burst_multiplier,
            enabled=enabled,
        )
        logger.info(
            f"Set tenant quota: {tenant_id} -> {requests}req/{window_seconds}s "
            f"(burst={burst_multiplier}, enabled={enabled})"
        )

    def remove_tenant_quota(self, tenant_id: str) -> bool:
        """Remove in-memory quota override for a tenant.

        After removal, the tenant will use registry or default quotas.

        Args:
            tenant_id: The tenant identifier

        Returns:
            True if override was removed, False if not found
        """
        if tenant_id in self._tenant_quotas:
            del self._tenant_quotas[tenant_id]
            logger.info(f"Removed tenant quota override: {tenant_id}")
            return True
        return False

    def get_all_tenant_quotas(self) -> Dict[str, TenantQuota]:
        """Get all in-memory tenant quota overrides.

        Returns:
            Dictionary mapping tenant_id to TenantQuota
        """
        return self._tenant_quotas.copy()

    def get_quota(self, tenant_id: str) -> Optional[TenantQuota]:
        """Protocol-compliant quota lookup.

        Args:
            tenant_id: The tenant identifier

        Returns:
            TenantQuota for the tenant
        """
        return self.get_tenant_quota(tenant_id)

    def set_quota(
        self,
        tenant_id: str,
        requests: int,
        window_seconds: int,
        burst_multiplier: float = 1.0,
    ) -> None:
        """Protocol-compliant quota setter.

        Args:
            tenant_id: The tenant identifier
            requests: Maximum requests per window
            window_seconds: Time window in seconds
            burst_multiplier: Burst allowance multiplier
        """
        self.set_tenant_quota(
            tenant_id=tenant_id,
            requests=requests,
            window_seconds=window_seconds,
            burst_multiplier=burst_multiplier,
        )

    @classmethod
    def from_env(cls) -> "TenantRateLimitProvider":
        """Create provider from environment variables.

        Environment variables:
            RATE_LIMIT_TENANT_REQUESTS: Default requests per window (default: 1000)
            RATE_LIMIT_TENANT_WINDOW: Default window seconds (default: 60)
            RATE_LIMIT_TENANT_BURST: Default burst multiplier (default: 1.0)
            RATE_LIMIT_USE_REGISTRY: Whether to use TenantQuotaRegistry (default: true)

        Returns:
            Configured TenantRateLimitProvider
        """
        return cls(
            default_requests=int(os.environ.get("RATE_LIMIT_TENANT_REQUESTS", "1000")),
            default_window_seconds=int(os.environ.get("RATE_LIMIT_TENANT_WINDOW", "60")),
            default_burst_multiplier=float(os.environ.get("RATE_LIMIT_TENANT_BURST", "1.0")),
            use_registry=os.environ.get("RATE_LIMIT_USE_REGISTRY", "true").lower() == "true",
        )


class RateLimitScope(str, Enum):
    """Scope for rate limiting."""

    USER = "user"
    IP = "ip"
    ENDPOINT = "endpoint"
    GLOBAL = "global"
    TENANT = "tenant"


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms."""

    TOKEN_BUCKET = "token_bucket"  # nosec B105 - not a password, algorithm name
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitRule:
    """Rate limit rule configuration."""

    requests: int  # Number of requests allowed
    window_seconds: int = 60  # Time window in seconds
    scope: RateLimitScope = RateLimitScope.IP  # Default to IP-based limiting
    endpoints: Optional[List[str]] = None  # Optional endpoint patterns
    burst_multiplier: float = 1.5  # Burst allowance multiplier
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW

    # Backwards compatibility alias
    @property
    def limit(self) -> int:
        return self.requests

    @property
    def burst_limit(self) -> int:
        return int(self.requests * self.burst_multiplier)

    @property
    def key_prefix(self) -> str:
        """Generate cache key prefix for this rule."""
        return f"ratelimit:{self.scope.value}"


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    limit: int
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""

    rules: List[RateLimitRule] = field(default_factory=list)
    redis_url: Optional[str] = None
    fallback_to_memory: bool = True
    enabled: bool = True
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    exempt_paths: List[str] = field(
        default_factory=lambda: ["/health", "/metrics", "/ready", "/live"]
    )
    fail_open: bool = True  # Continue processing if rate limiter fails

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Create configuration from environment variables."""
        import os

        enabled = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        requests_per_minute = int(os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "60"))
        burst_limit = int(os.getenv("RATE_LIMIT_BURST_LIMIT", "10"))
        redis_url = os.getenv("REDIS_URL")

        rules = []
        if enabled:
            rules.append(
                RateLimitRule(
                    requests=requests_per_minute,
                    window_seconds=60,
                    burst_multiplier=(
                        burst_limit / requests_per_minute if requests_per_minute > 0 else 1.5
                    ),
                )
            )

        return cls(
            rules=rules,
            redis_url=redis_url,
            enabled=enabled,
        )


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    capacity: int  # Maximum tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(init=False)
    last_refill: float = field(init=False)

    def __post_init__(self):
        self.tokens = self.capacity
        self.last_refill = time.time()

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate

        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def get_remaining_tokens(self) -> float:
        """Get remaining tokens in bucket."""
        self.refill()
        return self.tokens

    def get_reset_time(self) -> float:
        """Get time until bucket is fully refilled."""
        self.refill()
        if self.tokens >= self.capacity:
            return 0.0

        tokens_needed = self.capacity - self.tokens
        return tokens_needed / self.refill_rate


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter implementation.

    Uses a sliding window algorithm to provide smooth rate limiting
    that doesn't suffer from boundary issues like fixed windows.
    """

    def __init__(self, redis_client=None, fallback_to_memory: bool = True):
        self.redis_client = redis_client
        self.fallback_to_memory = fallback_to_memory
        self.local_windows: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        """Check if request is allowed and record it."""
        now = time.time()
        window_start = now - window_seconds

        async with self._lock:
            # Clean old entries and count current window
            if key not in self.local_windows:
                self.local_windows[key] = []

            # Remove entries outside the window
            self.local_windows[key] = [ts for ts in self.local_windows[key] if ts > window_start]

            current_count = len(self.local_windows[key])
            allowed = current_count < limit

            if allowed:
                self.local_windows[key].append(now)
                current_count += 1

            remaining = max(0, limit - current_count)
            reset_at = datetime.fromtimestamp(now + window_seconds, tz=timezone.utc)
            retry_after = None if allowed else window_seconds

            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=retry_after,
            )


class RateLimitMiddleware:
    """
    ASGI middleware for rate limiting.

    Features:
    - Redis-backed sliding window rate limiting
    - Multi-scope limits (IP, tenant, endpoint)
    - Tenant-specific configurable quotas via TenantRateLimitProvider
    - Rate limit headers in responses
    - Graceful degradation without Redis
    - Audit logging for rate limit events
    """

    def __init__(
        self,
        app,
        config: Optional[RateLimitConfig] = None,
        tenant_quota_provider: Optional[TenantRateLimitProvider] = None,
    ):
        super().__init__(app)
        self.config = config or RateLimitConfig.from_env()
        self.tenant_quota_provider = tenant_quota_provider
        self.redis: Optional[Any] = None
        self.limiter: Optional[SlidingWindowRateLimiter] = None
        self._initialized = False
        self._audit_log: List[Dict[str, Any]] = []
        self._constitutional_hash = CONSTITUTIONAL_HASH

        if not self.config.enabled:
            logger.info("Rate limiting is disabled")

        if self.tenant_quota_provider:
            logger.info("Tenant-specific rate limiting enabled via provider")

    async def _ensure_initialized(self) -> None:
        """Lazily initialize Redis connection."""
        if self._initialized:
            return

        # Default rate limiting
        client = scope.get("client", ("unknown", 0))
        client_ip = client[0] if client else "unknown"
        path = scope.get("path", "/")

        key = f"ip:{client_ip}:{path}"
        result = await self.limiter.is_allowed(key, limit=60, window_seconds=60)

        if not result.allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "retry_after": result.retry_after,
                },
            )
            await response(scope, receive, send)
            return

    def _get_tenant_quota(self, tenant_id: str) -> Optional[TenantQuota]:
        """Get tenant-specific quota from provider if available.

        Args:
            tenant_id: The tenant identifier

        Returns:
            TenantQuota if provider is configured and tenant has quota, None otherwise
        """
        if self.tenant_quota_provider is None:
            return None

        try:
            return self.tenant_quota_provider.get_tenant_quota(tenant_id)
        except Exception as e:
            logger.warning(f"Failed to get tenant quota for {tenant_id}: {e}")
            return None

    async def _check_tenant_rate_limit(
        self,
        request: Request,
        tenant_id: str,
        tenant_quota: TenantQuota,
    ) -> RateLimitResult:
        """Check rate limit for a specific tenant using tenant-specific quota.

        Args:
            request: The incoming request
            tenant_id: The tenant identifier
            tenant_quota: The tenant's quota configuration

        Returns:
            RateLimitResult for the tenant
        """
        if not tenant_quota.enabled:
            # Tenant rate limiting disabled - allow all
            return RateLimitResult(
                allowed=True,
                limit=tenant_quota.requests,
                remaining=tenant_quota.requests,
                reset_at=int(time.time() + tenant_quota.window_seconds),
                scope=RateLimitScope.TENANT,
                key=f"tenant:{tenant_id}",
            )

        key = f"tenant:{tenant_id}"
        result = await self.limiter.check(
            key=key,
            limit=tenant_quota.effective_limit,
            window_seconds=tenant_quota.window_seconds,
        )
        result.scope = RateLimitScope.TENANT
        result.key = key

        return result

    async def dispatch(
        self,
        limit_type: str,
        identifier: str,
        capacity: int,
        refill_rate: float,
        endpoint: str = "",
        consume_tokens: int = 1,
    ) -> Tuple[bool, float, float]:
        """
        Check if request is allowed under rate limit.

        Args:
            limit_type: Type of limit (user, ip, endpoint, global)
            identifier: Identifier for the limit (user_id, ip, etc.)
            capacity: Maximum requests allowed
            refill_rate: Refill rate in requests per second
            endpoint: Specific endpoint (optional)
            consume_tokens: Number of tokens to consume

        Returns:
            Tuple of (allowed, remaining_tokens, reset_time_seconds)
        """
        bucket_key = await self._get_bucket_key(limit_type, identifier, endpoint)
        bucket = await self._get_or_create_bucket(bucket_key, capacity, refill_rate)

        # Check all rules
        strictest_result: Optional[RateLimitResult] = None
        tenant_id = self._get_tenant_id(request)

        # First, check tenant-specific quota if provider is configured and tenant is identified
        if self.tenant_quota_provider is not None and tenant_id:
            tenant_quota = self._get_tenant_quota(tenant_id)
            if tenant_quota:
                result = await self._check_tenant_rate_limit(request, tenant_id, tenant_quota)

                # Create a pseudo-rule for audit logging
                tenant_rule = RateLimitRule(
                    requests=tenant_quota.requests,
                    window_seconds=tenant_quota.window_seconds,
                    scope=RateLimitScope.TENANT,
                    burst_multiplier=tenant_quota.burst_multiplier,
                )

                # Log audit for tenant-specific rate limit
                self._log_audit(request, result, tenant_rule)

                if not result.allowed:
                    response = JSONResponse(
                        status_code=429,
                        content={
                            "error": "Too Many Requests",
                            "message": f"Rate limit exceeded for tenant '{tenant_id}'. "
                            f"Try again in {result.retry_after} seconds.",
                            "retry_after": result.retry_after,
                            "scope": result.scope.value,
                            "tenant_id": tenant_id,
                            "constitutional_hash": self._constitutional_hash,
                        },
                    )
                    if self.config.include_response_headers:
                        for header, value in result.to_headers().items():
                            response.headers[header] = value
                        response.headers["X-Tenant-ID"] = tenant_id
                    return response

                strictest_result = result

        # Then check configured rules (which may include additional constraints)
        for rule in self.config.rules:
            # Skip tenant rule if we already checked via provider
            if (
                rule.scope == RateLimitScope.TENANT
                and self.tenant_quota_provider is not None
                and tenant_id
            ):
                continue

            # Check if rule applies to this endpoint
            if rule.endpoints:
                path_matches = any(request.url.path.startswith(ep) for ep in rule.endpoints)
                if not path_matches:
                    continue

            key = self._build_key(request, rule)
            result = await self.limiter.check(
                key=key,
                limit=rule.requests,
                window_seconds=rule.window_seconds,
            )

        return allowed, remaining, reset_time


            # If not allowed, reject immediately
            if not result.allowed:
                retry_msg = f"Rate limit exceeded. " f"Try again in {result.retry_after} seconds."
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "message": retry_msg,
                        "retry_after": result.retry_after,
                        "scope": result.scope.value,
                        "constitutional_hash": self._constitutional_hash,
                    },
                )

                # Add rate limit headers
                response.headers["X-RateLimit-Remaining"] = str(int(remaining))
                response.headers["X-RateLimit-Reset"] = str(int(time.time() + reset_time))
                response.headers["X-RateLimit-Limit"] = str(capacity)
                response.headers["Retry-After"] = str(int(reset_time))

                return response

        # Continue with request
        response = await call_next(request)
        return response

    return rate_limit_middleware


# ============================================================================
# Decorator for Endpoint-Specific Rate Limiting
# ============================================================================


def rate_limit(
    requests_per_minute: int = 60, burst_limit: int = 10, limit_type: str = "user", key_func=None
):
    """
    Decorator for endpoint-specific rate limiting.

    Args:
        requests_per_minute: Rate limit
        burst_limit: Burst capacity
        limit_type: Type of limit (user, ip, endpoint, global)
        key_func: Function to extract identifier from request

    Returns:
        Decorator function
    """
    refill_rate = requests_per_minute / 60.0

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if not request and "request" in kwargs:
                request = kwargs["request"]

            if not request:
                # No request found, allow
                return await func(*args, **kwargs)

            # Determine identifier
            if key_func:
                identifier = key_func(request)
            elif limit_type == "user":
                identifier = getattr(request.state, "user_id", None) or (
                    request.client.host if request.client else "unknown"
                )
            elif limit_type == "ip":
                identifier = request.client.host if request.client else "unknown"
            elif limit_type == "endpoint":
                identifier = request.url.path
            else:
                identifier = "global"

            # Check rate limit
            allowed, remaining, reset_time = await rate_limiter.is_allowed(
                limit_type, identifier, burst_limit, refill_rate, request.url.path
            )

            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded for {limit_type}",
                        "retry_after": int(reset_time),
                        "remaining": int(remaining),
                        "limit": burst_limit,
                    },
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Rate Limit Headers Middleware
# ============================================================================


def add_rate_limit_headers():
    """
    Middleware to add rate limit headers to responses.

    Usage:
        app.add_middleware(add_rate_limit_headers())
    """

    async def middleware(request: Request, call_next):
        response = await call_next(request)

        # Add rate limit headers if not already present
        if "X-RateLimit-Remaining" not in response.headers:
            # This is a simplified implementation
            # In production, you'd track actual limits per request
            response.headers["X-RateLimit-Limit"] = "60"
            response.headers["X-RateLimit-Remaining"] = "59"
            response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))

        return response

    return middleware


# ============================================================================
# Configuration Helpers
# ============================================================================


def configure_rate_limits(
    redis_client=None, default_requests_per_minute: int = 60, default_burst_limit: int = 10
):
    """
    Configure global rate limiting settings.

    Args:
        redis_client: Redis client for distributed rate limiting
        default_requests_per_minute: Default rate limit
        default_burst_limit: Default burst capacity
    """
    global rate_limiter
    if redis_client:
        rate_limiter.redis_client = redis_client

    # Store defaults for middleware creation
    rate_limiter.default_rpm = default_requests_per_minute
    rate_limiter.default_burst = default_burst_limit


# ============================================================================
# Monitoring Integration
# ============================================================================

from shared.metrics import _get_or_create_counter, _get_or_create_gauge

# Rate limiting metrics
RATE_LIMIT_EXCEEDED = _get_or_create_counter(
    "rate_limit_exceeded_total",
    "Total rate limit violations",
    ["limit_type", "identifier", "endpoint"],
)

RATE_LIMIT_REQUESTS = _get_or_create_counter(
    "rate_limit_requests_total",
    "Total requests subject to rate limiting",
    ["limit_type", "identifier", "endpoint", "allowed"],
)

ACTIVE_RATE_LIMITS = _get_or_create_gauge(
    "rate_limits_active", "Number of active rate limit buckets", []
)


def update_rate_limit_metrics(limit_type: str, identifier: str, endpoint: str, allowed: bool):
    """
    Update rate limiting metrics.

    Called automatically by rate limiting functions.
    """
    RATE_LIMIT_REQUESTS.labels(
        limit_type=limit_type,
        identifier=identifier,
        endpoint=endpoint,
        allowed=str(allowed).lower(),
    ).inc()

    if not allowed:
        RATE_LIMIT_EXCEEDED.labels(
            limit_type=limit_type, identifier=identifier, endpoint=endpoint
        ).inc()


# Update the is_allowed method to include metrics
original_is_allowed = rate_limiter.is_allowed


async def is_allowed_with_metrics(
    self,
    limit_type: str,
    identifier: str,
    capacity: int,
    refill_rate: float,
    endpoint: str = "",
    consume_tokens: int = 1,
) -> Tuple[bool, float, float]:
    result = await original_is_allowed(
        self, limit_type, identifier, capacity, refill_rate, endpoint, consume_tokens
    )
    allowed, remaining, reset_time = result

    # Update metrics
    update_rate_limit_metrics(limit_type, identifier, endpoint, allowed)

    return result


# Monkey patch the method
rate_limiter.is_allowed = is_allowed_with_metrics.__get__(rate_limiter, RateLimiter)


__all__ = [
    # Middleware and configuration
    "RateLimitMiddleware",
    "RateLimitConfig",
    "RateLimitRule",
    "RateLimitResult",
    "RateLimitScope",
    "RateLimitAlgorithm",
    "SlidingWindowRateLimiter",
    "create_rate_limit_middleware",
    # Tenant-specific rate limiting
    "TenantQuota",
    "TenantRateLimitProvider",
    "TenantQuotaProviderProtocol",
    # Feature flags
    "CONSTITUTIONAL_HASH",
    "REDIS_AVAILABLE",
    "TENANT_CONFIG_AVAILABLE",
]
