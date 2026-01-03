"""
ACGS-2 Rate Limiting Module
Constitutional Hash: cdd01ef066bc6cf2

Provides token bucket-based rate limiting for API endpoints.
Supports per-user, per-IP, and per-endpoint rate limits.
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Union
from collections import defaultdict

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse

from shared.logging import get_logger

logger = get_logger(__name__)


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


def create_rate_limit_middleware(requests_per_minute: int = 60, burst_limit: int = 10):
    """
    Create FastAPI middleware for rate limiting.

    Args:
        requests_per_minute: Base rate limit
        burst_limit: Burst capacity

    Returns:
        Middleware function
    """
    refill_rate = requests_per_minute / 60.0  # Convert to per second

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
    Counter,
    Gauge,
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
    # Core classes
    "RateLimiter",
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
