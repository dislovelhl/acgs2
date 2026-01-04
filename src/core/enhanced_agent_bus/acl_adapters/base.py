"""
ACGS-2 ACL Adapter Base Classes
Constitutional Hash: cdd01ef066bc6cf2

Provides the abstract base class for all Anti-Corruption Layer adapters
with built-in circuit breaker, rate limiting, timeout, and retry logic.
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Generic, Optional, TypeVar

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)

# Generic types for request/response
T = TypeVar("T")  # Request type
R = TypeVar("R")  # Response type


class AdapterState(Enum):
    """Adapter circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Rejecting calls
    HALF_OPEN = "half_open"  # Testing recovery


class AdapterTimeoutError(Exception):
    """Raised when adapter operation times out."""

    def __init__(self, adapter_name: str, timeout_ms: int):
        self.adapter_name = adapter_name
        self.timeout_ms = timeout_ms
        self.constitutional_hash = CONSTITUTIONAL_HASH
        super().__init__(
            f"[{CONSTITUTIONAL_HASH}] Adapter '{adapter_name}' timed out after {timeout_ms}ms"
        )

    def to_dict(self) -> dict:
        return {
            "error": "AdapterTimeoutError",
            "adapter": self.adapter_name,
            "timeout_ms": self.timeout_ms,
            "constitutional_hash": self.constitutional_hash,
        }


class AdapterCircuitOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, adapter_name: str, recovery_time_s: float):
        self.adapter_name = adapter_name
        self.recovery_time_s = recovery_time_s
        self.constitutional_hash = CONSTITUTIONAL_HASH
        super().__init__(
            f"[{CONSTITUTIONAL_HASH}] Adapter '{adapter_name}' circuit is open, "
            f"recovery in {recovery_time_s:.1f}s"
        )

    def to_dict(self) -> dict:
        return {
            "error": "AdapterCircuitOpenError",
            "adapter": self.adapter_name,
            "recovery_time_s": self.recovery_time_s,
            "constitutional_hash": self.constitutional_hash,
        }


class RateLimitExceededError(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, adapter_name: str, limit_per_second: float):
        self.adapter_name = adapter_name
        self.limit_per_second = limit_per_second
        self.constitutional_hash = CONSTITUTIONAL_HASH
        super().__init__(
            f"[{CONSTITUTIONAL_HASH}] Adapter '{adapter_name}' rate limit exceeded "
            f"({limit_per_second}/s)"
        )

    def to_dict(self) -> dict:
        return {
            "error": "RateLimitExceededError",
            "adapter": self.adapter_name,
            "limit_per_second": self.limit_per_second,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class AdapterConfig:
    """Configuration for ACL adapters."""

    # Timeout settings
    timeout_ms: int = 5000  # 5 second default
    connect_timeout_ms: int = 1000  # 1 second connect timeout

    # Retry settings
    max_retries: int = 3
    retry_base_delay_ms: int = 100
    retry_max_delay_ms: int = 5000
    retry_exponential_base: float = 2.0

    # Circuit breaker settings
    circuit_failure_threshold: int = 5
    circuit_recovery_timeout_s: float = 30.0
    circuit_half_open_max_calls: int = 3

    # Rate limiting
    rate_limit_per_second: float = 100.0
    rate_limit_burst: int = 10

    # Caching
    cache_enabled: bool = True
    cache_ttl_s: int = 300  # 5 minute default

    # Graceful degradation
    fallback_enabled: bool = True


@dataclass
class AdapterResult(Generic[R]):
    """Result wrapper for adapter calls."""

    success: bool
    data: Optional[R] = None
    error: Optional[Exception] = None
    latency_ms: float = 0.0
    from_cache: bool = False
    from_fallback: bool = False
    retry_count: int = 0
    constitutional_hash: str = field(default=CONSTITUTIONAL_HASH)

    def to_dict(self) -> dict:
        result = {
            "success": self.success,
            "latency_ms": self.latency_ms,
            "from_cache": self.from_cache,
            "from_fallback": self.from_fallback,
            "retry_count": self.retry_count,
            "constitutional_hash": self.constitutional_hash,
        }
        if self.error:
            result["error"] = str(self.error)
            if hasattr(self.error, "to_dict"):
                result["error_details"] = self.error.to_dict()
        return result


class SimpleCircuitBreaker:
    """
    Simple circuit breaker implementation for ACL adapters.

    Uses 3-state FSM: CLOSED -> OPEN -> HALF_OPEN -> CLOSED
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_s: float = 30.0,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout_s = recovery_timeout_s
        self.half_open_max_calls = half_open_max_calls

        self._state = AdapterState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._half_open_calls = 0

    @property
    def state(self) -> AdapterState:
        """Get current circuit state, checking for recovery."""
        if self._state == AdapterState.OPEN:
            if self._last_failure_time is not None:
                elapsed = time.monotonic() - self._last_failure_time
                if elapsed >= self.recovery_timeout_s:
                    self._state = AdapterState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(
                        f"[{CONSTITUTIONAL_HASH}] Circuit breaker transitioning to HALF_OPEN"
                    )
        return self._state

    @property
    def time_until_recovery(self) -> float:
        """Seconds until recovery attempt."""
        if self._state != AdapterState.OPEN or self._last_failure_time is None:
            return 0.0
        elapsed = time.monotonic() - self._last_failure_time
        return max(0.0, self.recovery_timeout_s - elapsed)

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == AdapterState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_max_calls:
                self._state = AdapterState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"[{CONSTITUTIONAL_HASH}] Circuit breaker recovered to CLOSED")
        elif self._state == AdapterState.CLOSED:
            # Decrement failure count on success (sliding window effect)
            self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed call."""
        self._last_failure_time = time.monotonic()
        self._success_count = 0

        if self._state == AdapterState.HALF_OPEN:
            # Any failure in half-open returns to open
            self._state = AdapterState.OPEN
            logger.warning(f"[{CONSTITUTIONAL_HASH}] Circuit breaker reopened from HALF_OPEN")
        elif self._state == AdapterState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = AdapterState.OPEN
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] Circuit breaker opened after "
                    f"{self._failure_count} failures"
                )

    def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        self._state = AdapterState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0


class TokenBucketRateLimiter:
    """Token bucket rate limiter for adapters."""

    def __init__(self, rate_per_second: float, burst: int):
        self.rate_per_second = rate_per_second
        self.burst = burst
        self._tokens = float(burst)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        """Try to acquire a token. Returns True if allowed."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_update
            self._last_update = now

            # Add tokens based on elapsed time
            self._tokens = min(self.burst, self._tokens + elapsed * self.rate_per_second)

            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False


class ACLAdapter(ABC, Generic[T, R]):
    """
    Abstract base class for Anti-Corruption Layer adapters.

    Provides:
    - Circuit breaker protection
    - Rate limiting
    - Timeout management
    - Retry with exponential backoff
    - Caching (optional)
    - Graceful degradation (optional)

    Subclasses must implement:
    - _execute(request): Perform the actual external call
    - _validate_response(response): Check if response is valid
    - _get_cache_key(request): Generate cache key for request
    - _get_fallback_response(request): Provide fallback when circuit open
    """

    def __init__(self, name: str, config: AdapterConfig = None):
        self.name = name
        self.config = config or AdapterConfig()
        self.constitutional_hash = CONSTITUTIONAL_HASH

        # Initialize circuit breaker
        self.circuit_breaker = SimpleCircuitBreaker(
            failure_threshold=self.config.circuit_failure_threshold,
            recovery_timeout_s=self.config.circuit_recovery_timeout_s,
            half_open_max_calls=self.config.circuit_half_open_max_calls,
        )

        # Initialize rate limiter
        self.rate_limiter = TokenBucketRateLimiter(
            rate_per_second=self.config.rate_limit_per_second,
            burst=self.config.rate_limit_burst,
        )

        # Simple in-memory cache
        self._cache: dict[str, tuple[R, float]] = {}

        # Metrics
        self._total_calls = 0
        self._successful_calls = 0
        self._failed_calls = 0
        self._cache_hits = 0
        self._fallback_uses = 0

        logger.info(
            f"[{CONSTITUTIONAL_HASH}] Initialized ACL adapter '{name}' with config: "
            f"timeout={self.config.timeout_ms}ms, retries={self.config.max_retries}"
        )

    @abstractmethod
    async def _execute(self, request: T) -> R:
        """
        Execute the actual external call.

        Must be implemented by subclasses.
        """
        raise NotImplementedError

    @abstractmethod
    def _validate_response(self, response: R) -> bool:
        """
        Validate if response is acceptable.

        Returns True if response is valid, False otherwise.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_cache_key(self, request: T) -> str:
        """
        Generate a cache key for the request.

        Returns string key for caching.
        """
        raise NotImplementedError

    def _get_fallback_response(self, request: T) -> Optional[R]:
        """
        Get fallback response when circuit is open.

        Override in subclasses to provide meaningful fallback.
        Returns None by default (no fallback available).
        """
        return None

    async def call(self, request: T) -> AdapterResult[R]:
        """
        Execute adapter call with all protections.

        Applies in order:
        1. Rate limiting
        2. Cache check
        3. Circuit breaker check
        4. Timeout-wrapped execution with retries
        5. Fallback on failure (if enabled)
        """
        start_time = time.monotonic()
        result = AdapterResult[R](success=False)
        self._total_calls += 1

        try:
            # 1. Check rate limit
            if not await self.rate_limiter.acquire():
                raise RateLimitExceededError(self.name, self.config.rate_limit_per_second)

            # 2. Check cache
            if self.config.cache_enabled:
                cache_key = self._get_cache_key(request)
                cached = self._get_from_cache(cache_key)
                if cached is not None:
                    self._cache_hits += 1
                    result.success = True
                    result.data = cached
                    result.from_cache = True
                    result.latency_ms = (time.monotonic() - start_time) * 1000
                    return result

            # 3. Check circuit breaker
            if self.circuit_breaker.state == AdapterState.OPEN:
                return await self._handle_circuit_open(request, result, start_time)

            # 4. Execute with retries
            for attempt in range(self.config.max_retries + 1):
                try:
                    response = await self._execute_with_timeout(request)

                    if self._validate_response(response):
                        self.circuit_breaker.record_success()
                        self._successful_calls += 1

                        # Cache successful response
                        if self.config.cache_enabled:
                            self._put_in_cache(cache_key, response)

                        result.success = True
                        result.data = response
                        result.retry_count = attempt
                        result.latency_ms = (time.monotonic() - start_time) * 1000
                        return result
                    else:
                        # Invalid response counts as failure
                        self.circuit_breaker.record_failure()
                        result.error = ValueError("Invalid response from adapter")

                except asyncio.TimeoutError:
                    self.circuit_breaker.record_failure()
                    result.error = AdapterTimeoutError(self.name, self.config.timeout_ms)
                    result.retry_count = attempt

                    if attempt < self.config.max_retries:
                        await self._backoff(attempt)
                        continue

                except Exception as e:
                    self.circuit_breaker.record_failure()
                    result.error = e
                    result.retry_count = attempt

                    if attempt < self.config.max_retries:
                        await self._backoff(attempt)
                        continue

            # All retries exhausted
            self._failed_calls += 1
            result.latency_ms = (time.monotonic() - start_time) * 1000

            # 5. Try fallback
            if self.config.fallback_enabled:
                fallback = self._get_fallback_response(request)
                if fallback is not None:
                    self._fallback_uses += 1
                    result.success = True
                    result.data = fallback
                    result.from_fallback = True

            return result

        except (RateLimitExceededError, AdapterCircuitOpenError) as e:
            result.error = e
            result.latency_ms = (time.monotonic() - start_time) * 1000
            self._failed_calls += 1
            return result

    async def _handle_circuit_open(
        self, request: T, result: AdapterResult[R], start_time: float
    ) -> AdapterResult[R]:
        """Handle call when circuit is open."""
        recovery_time = self.circuit_breaker.time_until_recovery

        # Try fallback first
        if self.config.fallback_enabled:
            fallback = self._get_fallback_response(request)
            if fallback is not None:
                self._fallback_uses += 1
                result.success = True
                result.data = fallback
                result.from_fallback = True
                result.latency_ms = (time.monotonic() - start_time) * 1000
                return result

        # No fallback available
        result.error = AdapterCircuitOpenError(self.name, recovery_time)
        result.latency_ms = (time.monotonic() - start_time) * 1000
        self._failed_calls += 1
        return result

    async def _execute_with_timeout(self, request: T) -> R:
        """Execute with timeout wrapper."""
        timeout_s = self.config.timeout_ms / 1000.0
        return await asyncio.wait_for(self._execute(request), timeout=timeout_s)

    async def _backoff(self, attempt: int) -> None:
        """Calculate and apply exponential backoff."""
        delay_ms = min(
            self.config.retry_base_delay_ms * (self.config.retry_exponential_base**attempt),
            self.config.retry_max_delay_ms,
        )
        await asyncio.sleep(delay_ms / 1000.0)

    def _get_from_cache(self, key: str) -> Optional[R]:
        """Get item from cache if not expired."""
        if key in self._cache:
            value, timestamp = self._cache[key]
            if time.monotonic() - timestamp < self.config.cache_ttl_s:
                return value
            else:
                del self._cache[key]
        return None

    def _put_in_cache(self, key: str, value: R) -> None:
        """Put item in cache."""
        self._cache[key] = (value, time.monotonic())

    def clear_cache(self) -> None:
        """Clear the adapter cache."""
        self._cache.clear()

    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker to closed state."""
        self.circuit_breaker.reset()

    def get_metrics(self) -> dict:
        """Get adapter metrics."""
        return {
            "adapter_name": self.name,
            "constitutional_hash": self.constitutional_hash,
            "total_calls": self._total_calls,
            "successful_calls": self._successful_calls,
            "failed_calls": self._failed_calls,
            "cache_hits": self._cache_hits,
            "fallback_uses": self._fallback_uses,
            "circuit_state": self.circuit_breaker.state.value,
            "success_rate": (
                self._successful_calls / self._total_calls if self._total_calls > 0 else 0.0
            ),
            "cache_hit_rate": (
                self._cache_hits / self._total_calls if self._total_calls > 0 else 0.0
            ),
        }

    def get_health(self) -> dict:
        """Get adapter health status."""
        state = self.circuit_breaker.state
        return {
            "adapter_name": self.name,
            "constitutional_hash": self.constitutional_hash,
            "healthy": state == AdapterState.CLOSED,
            "state": state.value,
            "time_until_recovery": self.circuit_breaker.time_until_recovery,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
