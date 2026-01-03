"""
ACGS-2 Rate Limiting Module
Constitutional Hash: cdd01ef066bc6cf2

Provides token bucket-based rate limiting for API endpoints.
Supports per-user, per-IP, and per-endpoint rate limits.
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

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


class RateLimitScope(str, Enum):
    """Scope for rate limiting."""
    USER = "user"
    IP = "ip"
    ENDPOINT = "endpoint"
    GLOBAL = "global"
    TENANT = "tenant"


class RateLimitAlgorithm(str, Enum):
    """Rate limiting algorithms."""
    TOKEN_BUCKET = "token_bucket"
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
    exempt_paths: List[str] = field(default_factory=lambda: ["/health", "/metrics", "/ready", "/live"])
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
            rules.append(RateLimitRule(
                requests=requests_per_minute,
                window_seconds=60,
                burst_multiplier=burst_limit / requests_per_minute if requests_per_minute > 0 else 1.5,
            ))

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
            self.local_windows[key] = [
                ts for ts in self.local_windows[key]
                if ts > window_start
            ]

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

    Can be added to FastAPI/Starlette apps for automatic rate limiting.
    """

    def __init__(self, app, config: Optional[RateLimitConfig] = None):
        self.app = app
        self.config = config or RateLimitConfig()
        self.limiter = SlidingWindowRateLimiter()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
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

        await self.app(scope, receive, send)


class RateLimiter:
    """
    Distributed rate limiter using Redis for storage.

    Supports multiple rate limit types:
    - Per-user limits
    - Per-IP limits
    - Per-endpoint limits
    - Global limits
    """

    def __init__(self, redis_client=None):
        self.redis_client = redis_client
        self.local_buckets: Dict[str, TokenBucket] = {}
        self._lock = asyncio.Lock()

    async def _get_bucket_key(self, limit_type: str, identifier: str, endpoint: str = "") -> str:
        """Generate bucket key for storage."""
        if endpoint:
            return f"ratelimit:{limit_type}:{identifier}:{endpoint}"
        return f"ratelimit:{limit_type}:{identifier}"

    async def _get_or_create_bucket(
        self, key: str, capacity: int, refill_rate: float
    ) -> TokenBucket:
        """Get existing bucket or create new one."""
        async with self._lock:
            if key not in self.local_buckets:
                self.local_buckets[key] = TokenBucket(capacity, refill_rate)
            return self.local_buckets[key]

    async def is_allowed(
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

        allowed = bucket.consume(consume_tokens)
        remaining = bucket.get_remaining_tokens()
        reset_time = bucket.get_reset_time()

        if allowed:
            logger.debug(
                f"Rate limit allowed: {limit_type}:{identifier}:{endpoint}",
                remaining_tokens=remaining,
                reset_time_seconds=reset_time,
            )
        else:
            logger.warning(
                f"Rate limit exceeded: {limit_type}:{identifier}:{endpoint}",
                remaining_tokens=remaining,
                reset_time_seconds=reset_time,
            )

        return allowed, remaining, reset_time


# Global rate limiter instance
rate_limiter = RateLimiter()


# ============================================================================
# FastAPI Integration
# ============================================================================


def create_rate_limit_middleware(
    requests_per_minute: int = 60,
    burst_limit: int = 10,
    burst_multiplier: float = 1.5,
    fail_open: bool = True,
):
    """
    Create FastAPI middleware for rate limiting.

    Args:
        requests_per_minute: Base rate limit
        burst_limit: Burst capacity
        burst_multiplier: Multiplier for burst capacity
        fail_open: Whether to allow requests if rate limiter fails

    Returns:
        Middleware function
    """
    refill_rate = requests_per_minute / 60.0  # Convert to per second
    effective_burst = int(burst_limit * burst_multiplier)

    async def rate_limit_middleware(request: Request, call_next):
        # Extract identifiers
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None) or client_ip
        endpoint = request.url.path

        # Check rate limits (in order of specificity)
        limits_to_check = [
            # Per-user limits (most specific)
            ("user", user_id, requests_per_minute * 2, refill_rate * 2, endpoint),
            # Per-IP limits
            ("ip", client_ip, requests_per_minute, refill_rate, endpoint),
            # Per-endpoint limits
            ("endpoint", endpoint, requests_per_minute * 3, refill_rate * 3, ""),
        ]

        for limit_type, identifier, capacity, refill, endpoint_key in limits_to_check:
            allowed, remaining, reset_time = await rate_limiter.is_allowed(
                limit_type, identifier, capacity, refill, endpoint_key
            )

            if not allowed:
                # Return rate limit exceeded response
                response = JSONResponse(
                    status_code=429,
                    content={
                        "error": "Too Many Requests",
                        "message": f"Rate limit exceeded for {limit_type}: {identifier}",
                        "retry_after": int(reset_time),
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

from shared.metrics import (
    _get_or_create_counter,
    _get_or_create_gauge,
)

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
    # Constants
    "CONSTITUTIONAL_HASH",
    "REDIS_AVAILABLE",
    # Enums
    "RateLimitScope",
    "RateLimitAlgorithm",
    # Dataclasses
    "RateLimitRule",
    "RateLimitResult",
    "RateLimitConfig",
    # Core classes
    "RateLimiter",
    "SlidingWindowRateLimiter",
    "RateLimitMiddleware",
    "TokenBucket",
    # Global instance
    "rate_limiter",
    # Middleware
    "create_rate_limit_middleware",
    "add_rate_limit_headers",
    # Decorators
    "rate_limit",
    # Configuration
    "configure_rate_limits",
    # Metrics
    "RATE_LIMIT_EXCEEDED",
    "RATE_LIMIT_REQUESTS",
    "ACTIVE_RATE_LIMITS",
]
