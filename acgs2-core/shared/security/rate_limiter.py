"""
ACGS-2 API Rate Limiting Middleware
Constitutional Hash: cdd01ef066bc6cf2

Production-grade rate limiting with Redis backend supporting:
- Sliding window rate limiting algorithm
- Per-IP, per-tenant, and per-endpoint limits
- Distributed rate limiting across service instances
- Graceful degradation when Redis unavailable
- Constitutional compliance tracking

Security Features:
- Prevents brute force attacks
- Mitigates DoS attacks
- Protects expensive endpoints
- Provides audit trail for rate limit events

Usage:
    from shared.security.rate_limiter import RateLimitMiddleware, RateLimitConfig

    app.add_middleware(
        RateLimitMiddleware,
        config=RateLimitConfig.from_env()
    )
"""

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse

# Constitutional hash for validation
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)

# Redis client - optional dependency
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    try:
        import aioredis
        REDIS_AVAILABLE = True
    except ImportError:
        aioredis = None
        REDIS_AVAILABLE = False


class RateLimitScope(str, Enum):
    """Scope for rate limiting."""
    IP = "ip"
    TENANT = "tenant"
    ENDPOINT = "endpoint"
    USER = "user"
    GLOBAL = "global"


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithm."""
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitRule:
    """
    A rate limiting rule.

    Attributes:
        requests: Maximum requests allowed
        window_seconds: Time window in seconds
        scope: Scope of the limit
        endpoints: Optional list of endpoint patterns to apply to
        burst_multiplier: Allow burst above limit temporarily
    """
    requests: int
    window_seconds: int
    scope: RateLimitScope = RateLimitScope.IP
    endpoints: Optional[List[str]] = None
    burst_multiplier: float = 1.0

    @property
    def key_prefix(self) -> str:
        return f"ratelimit:{self.scope.value}"


@dataclass
class RateLimitConfig:
    """
    Rate limiter configuration.

    Attributes:
        redis_url: Redis connection URL
        enabled: Whether rate limiting is enabled
        rules: List of rate limit rules
        algorithm: Rate limiting algorithm
        fail_open: Allow requests when Redis unavailable
        include_response_headers: Add rate limit headers to responses
        exempt_paths: Paths exempt from rate limiting
        key_prefix: Redis key prefix
    """
    redis_url: str = "redis://localhost:6379/0"
    enabled: bool = True
    rules: List[RateLimitRule] = field(default_factory=list)
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    fail_open: bool = True  # Allow when Redis down
    include_response_headers: bool = True
    exempt_paths: List[str] = field(default_factory=lambda: [
        "/health",
        "/healthz",
        "/ready",
        "/readyz",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    ])
    key_prefix: str = "acgs2:ratelimit"
    audit_enabled: bool = True

    @classmethod
    def from_env(cls) -> "RateLimitConfig":
        """Create configuration from environment variables."""
        # Parse rules from environment
        rules = []

        # Default IP-based rule
        ip_limit = int(os.environ.get("RATE_LIMIT_IP_REQUESTS", "100"))
        ip_window = int(os.environ.get("RATE_LIMIT_IP_WINDOW", "60"))
        if ip_limit > 0:
            rules.append(RateLimitRule(
                requests=ip_limit,
                window_seconds=ip_window,
                scope=RateLimitScope.IP,
            ))

        # Tenant-based rule
        tenant_limit = int(os.environ.get("RATE_LIMIT_TENANT_REQUESTS", "1000"))
        tenant_window = int(os.environ.get("RATE_LIMIT_TENANT_WINDOW", "60"))
        if tenant_limit > 0:
            rules.append(RateLimitRule(
                requests=tenant_limit,
                window_seconds=tenant_window,
                scope=RateLimitScope.TENANT,
            ))

        # Global fallback rule
        global_limit = int(os.environ.get("RATE_LIMIT_GLOBAL_REQUESTS", "10000"))
        global_window = int(os.environ.get("RATE_LIMIT_GLOBAL_WINDOW", "60"))
        if global_limit > 0:
            rules.append(RateLimitRule(
                requests=global_limit,
                window_seconds=global_window,
                scope=RateLimitScope.GLOBAL,
            ))

        return cls(
            redis_url=os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            enabled=os.environ.get("RATE_LIMIT_ENABLED", "true").lower() == "true",
            rules=rules,
            fail_open=os.environ.get("RATE_LIMIT_FAIL_OPEN", "true").lower() == "true",
            include_response_headers=os.environ.get(
                "RATE_LIMIT_HEADERS", "true"
            ).lower() == "true",
            audit_enabled=os.environ.get(
                "RATE_LIMIT_AUDIT", "true"
            ).lower() == "true",
        )


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    limit: int
    remaining: int
    reset_at: int  # Unix timestamp
    retry_after: Optional[int] = None
    scope: RateLimitScope = RateLimitScope.IP
    key: str = ""

    def to_headers(self) -> Dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(self.reset_at),
            "X-RateLimit-Scope": self.scope.value,
        }
        if self.retry_after is not None:
            headers["Retry-After"] = str(self.retry_after)
        return headers


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter using Redis sorted sets.

    This implementation uses Redis sorted sets to track request timestamps,
    providing accurate sliding window rate limiting.
    """

    def __init__(
        self,
        redis_client: Optional[Any],
        key_prefix: str = "ratelimit",
    ):
        self.redis = redis_client
        self.key_prefix = key_prefix
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """
        Check if request is allowed under the rate limit.

        Args:
            key: Rate limit key (e.g., "ip:192.168.1.1")
            limit: Maximum requests allowed
            window_seconds: Time window in seconds

        Returns:
            RateLimitResult with allowed status and metadata
        """
        now = time.time()
        window_start = now - window_seconds

        redis_key = f"{self.key_prefix}:{key}"

        if self.redis is None:
            # Fallback: always allow when Redis unavailable
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_at=int(now + window_seconds),
                scope=RateLimitScope.IP,
                key=key,
            )

        try:
            pipe = self.redis.pipeline()

            # Remove expired entries
            pipe.zremrangebyscore(redis_key, 0, window_start)

            # Count current requests in window
            pipe.zcard(redis_key)

            # Add current request
            pipe.zadd(redis_key, {str(now): now})

            # Set expiry on key
            pipe.expire(redis_key, window_seconds + 1)

            results = await pipe.execute()

            # results[1] is the count before adding current request
            current_count = results[1]

            allowed = current_count < limit
            remaining = max(0, limit - current_count - 1)

            # Calculate reset time
            if current_count > 0:
                # Get oldest entry to calculate reset
                oldest = await self.redis.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    reset_at = int(oldest_time + window_seconds)
                else:
                    reset_at = int(now + window_seconds)
            else:
                reset_at = int(now + window_seconds)

            return RateLimitResult(
                allowed=allowed,
                limit=limit,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=reset_at - int(now) if not allowed else None,
                key=key,
            )

        except Exception as e:
            logger.warning(f"Rate limit check failed for {key}: {e}")
            # Fail open
            return RateLimitResult(
                allowed=True,
                limit=limit,
                remaining=limit,
                reset_at=int(now + window_seconds),
                key=key,
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI/Starlette middleware for rate limiting.

    Features:
    - Redis-backed sliding window rate limiting
    - Multi-scope limits (IP, tenant, endpoint)
    - Rate limit headers in responses
    - Graceful degradation without Redis
    - Audit logging for rate limit events
    """

    def __init__(
        self,
        app,
        config: Optional[RateLimitConfig] = None,
    ):
        super().__init__(app)
        self.config = config or RateLimitConfig.from_env()
        self.redis: Optional[Any] = None
        self.limiter: Optional[SlidingWindowRateLimiter] = None
        self._initialized = False
        self._audit_log: List[Dict[str, Any]] = []
        self._constitutional_hash = CONSTITUTIONAL_HASH

        if not self.config.enabled:
            logger.info("Rate limiting is disabled")

    async def _ensure_initialized(self) -> None:
        """Lazily initialize Redis connection."""
        if self._initialized:
            return

        if REDIS_AVAILABLE and self.config.enabled:
            try:
                self.redis = await aioredis.from_url(
                    self.config.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                self.limiter = SlidingWindowRateLimiter(
                    self.redis,
                    self.config.key_prefix,
                )
                logger.info(
                    f"Rate limiter initialized with Redis: {self.config.redis_url}"
                )
            except Exception as e:
                logger.warning(f"Failed to connect to Redis for rate limiting: {e}")
                self.limiter = SlidingWindowRateLimiter(None, self.config.key_prefix)
        else:
            self.limiter = SlidingWindowRateLimiter(None, self.config.key_prefix)

        self._initialized = True

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check X-Forwarded-For header (common for reverse proxies)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take the first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct client
        client = request.client
        if client:
            return client.host

        return "unknown"

    def _get_tenant_id(self, request: Request) -> Optional[str]:
        """Extract tenant ID from request."""
        # Check header
        tenant_id = request.headers.get("X-Tenant-ID")
        if tenant_id:
            return tenant_id

        # Check query parameter
        tenant_id = request.query_params.get("tenant_id")
        if tenant_id:
            return tenant_id

        return None

    def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request (requires auth middleware to set)."""
        return getattr(request.state, "user_id", None)

    def _is_exempt(self, path: str) -> bool:
        """Check if path is exempt from rate limiting."""
        for exempt_path in self.config.exempt_paths:
            if path.startswith(exempt_path):
                return True
        return False

    def _build_key(
        self,
        request: Request,
        rule: RateLimitRule,
    ) -> str:
        """Build rate limit key based on scope."""
        if rule.scope == RateLimitScope.IP:
            return f"ip:{self._get_client_ip(request)}"

        elif rule.scope == RateLimitScope.TENANT:
            tenant_id = self._get_tenant_id(request)
            if tenant_id:
                return f"tenant:{tenant_id}"
            # Fall back to IP if no tenant
            return f"ip:{self._get_client_ip(request)}"

        elif rule.scope == RateLimitScope.USER:
            user_id = self._get_user_id(request)
            if user_id:
                return f"user:{user_id}"
            return f"ip:{self._get_client_ip(request)}"

        elif rule.scope == RateLimitScope.ENDPOINT:
            ip = self._get_client_ip(request)
            path_hash = hashlib.md5(request.url.path.encode()).hexdigest()[:8]
            return f"endpoint:{ip}:{path_hash}"

        elif rule.scope == RateLimitScope.GLOBAL:
            return "global"

        return f"ip:{self._get_client_ip(request)}"

    def _log_audit(
        self,
        request: Request,
        result: RateLimitResult,
        rule: RateLimitRule,
    ) -> None:
        """Log rate limit event for auditing."""
        if not self.config.audit_enabled:
            return

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": request.url.path,
            "method": request.method,
            "client_ip": self._get_client_ip(request),
            "tenant_id": self._get_tenant_id(request),
            "scope": rule.scope.value,
            "key": result.key,
            "allowed": result.allowed,
            "limit": result.limit,
            "remaining": result.remaining,
            "constitutional_hash": self._constitutional_hash,
        }

        self._audit_log.append(entry)

        # Keep bounded
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-5000:]

        if not result.allowed:
            logger.warning(
                f"Rate limit exceeded: {entry['path']} from {entry['client_ip']} "
                f"[scope={rule.scope.value}, key={result.key}]"
            )

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request through rate limiting."""
        # Skip if disabled
        if not self.config.enabled:
            return await call_next(request)

        # Skip exempt paths
        if self._is_exempt(request.url.path):
            return await call_next(request)

        # Ensure initialized
        await self._ensure_initialized()

        # Check all rules
        strictest_result: Optional[RateLimitResult] = None

        for rule in self.config.rules:
            # Check if rule applies to this endpoint
            if rule.endpoints:
                path_matches = any(
                    request.url.path.startswith(ep)
                    for ep in rule.endpoints
                )
                if not path_matches:
                    continue

            key = self._build_key(request, rule)
            result = await self.limiter.check(
                key=key,
                limit=rule.requests,
                window_seconds=rule.window_seconds,
            )
            result.scope = rule.scope

            # Track the strictest (most restrictive) result
            if strictest_result is None or not result.allowed:
                strictest_result = result

            # Log audit
            self._log_audit(request, result, rule)

            # If not allowed, reject immediately
            if not result.allowed:
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded. Try again in {result.retry_after} seconds.",
                        "retry_after": result.retry_after,
                        "scope": result.scope.value,
                        "constitutional_hash": self._constitutional_hash,
                    },
                )
                if self.config.include_response_headers:
                    for header, value in result.to_headers().items():
                        response.headers[header] = value
                return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        if strictest_result and self.config.include_response_headers:
            for header, value in strictest_result.to_headers().items():
                response.headers[header] = value

        return response

    def get_audit_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get rate limit audit log."""
        return self._audit_log[-limit:]


def create_rate_limit_middleware(
    requests_per_minute: int = 100,
    burst_multiplier: float = 1.5,
) -> Callable:
    """
    Factory function to create rate limit middleware with common defaults.

    Args:
        requests_per_minute: Base rate limit per IP
        burst_multiplier: Allow burst above limit

    Returns:
        Configured RateLimitMiddleware class
    """
    config = RateLimitConfig(
        rules=[
            RateLimitRule(
                requests=requests_per_minute,
                window_seconds=60,
                scope=RateLimitScope.IP,
                burst_multiplier=burst_multiplier,
            ),
        ],
    )

    def middleware_factory(app):
        return RateLimitMiddleware(app, config=config)

    return middleware_factory


__all__ = [
    "RateLimitMiddleware",
    "RateLimitConfig",
    "RateLimitRule",
    "RateLimitResult",
    "RateLimitScope",
    "RateLimitAlgorithm",
    "SlidingWindowRateLimiter",
    "create_rate_limit_middleware",
    "CONSTITUTIONAL_HASH",
    "REDIS_AVAILABLE",
]
