"""
ACGS-2 ACL Base Adapter Tests
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
from dataclasses import dataclass
from typing import Optional

import pytest

from ..base import (
    CONSTITUTIONAL_HASH,
    ACLAdapter,
    AdapterCircuitOpenError,
    AdapterConfig,
    AdapterState,
    AdapterTimeoutError,
    RateLimitExceededError,
    SimpleCircuitBreaker,
    TokenBucketRateLimiter,
)


# Test adapter implementation
@dataclass
class MockRequest:
    value: str
    should_fail: bool = False
    delay_ms: int = 0


@dataclass
class MockResponse:
    result: str
    constitutional_hash: str = CONSTITUTIONAL_HASH


class MockableAdapter(ACLAdapter[MockRequest, MockResponse]):
    """Testable adapter implementation."""

    def __init__(
        self, name: str = "test", config: AdapterConfig = None, provide_fallback: bool = True
    ):
        super().__init__(name, config or AdapterConfig())
        self.execute_count = 0
        self.provide_fallback = provide_fallback

    async def _execute(self, request: MockRequest) -> MockResponse:
        self.execute_count += 1

        if request.delay_ms > 0:
            await asyncio.sleep(request.delay_ms / 1000.0)

        if request.should_fail:
            raise Exception("Simulated failure")

        return MockResponse(result=f"processed:{request.value}")

    def _validate_response(self, response: MockResponse) -> bool:
        return response.result.startswith("processed:")

    def _get_cache_key(self, request: MockRequest) -> str:
        return f"test:{request.value}"

    def _get_fallback_response(self, request: MockRequest) -> Optional[MockResponse]:
        if self.provide_fallback:
            return MockResponse(result=f"processed:fallback:{request.value}")
        return None


class TestSimpleCircuitBreaker:
    """Tests for SimpleCircuitBreaker."""

    def test_initial_state_closed(self):
        """Circuit breaker starts in CLOSED state."""
        cb = SimpleCircuitBreaker()
        assert cb.state == AdapterState.CLOSED

    def test_opens_after_failures(self):
        """Circuit opens after failure threshold."""
        cb = SimpleCircuitBreaker(failure_threshold=3)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == AdapterState.OPEN

    def test_success_resets_failure_count(self):
        """Success decrements failure count."""
        cb = SimpleCircuitBreaker(failure_threshold=5)

        cb.record_failure()
        cb.record_failure()
        cb.record_success()

        assert cb._failure_count == 1

    def test_half_open_on_recovery(self):
        """Circuit transitions to HALF_OPEN after recovery timeout."""
        cb = SimpleCircuitBreaker(failure_threshold=1, recovery_timeout_s=0.1)

        cb.record_failure()
        assert cb.state == AdapterState.OPEN

        # Wait for recovery
        import time

        time.sleep(0.15)

        assert cb.state == AdapterState.HALF_OPEN

    def test_half_open_success_closes(self):
        """Successful calls in HALF_OPEN close the circuit."""
        cb = SimpleCircuitBreaker(
            failure_threshold=1, recovery_timeout_s=0.01, half_open_max_calls=2
        )

        cb.record_failure()
        import time

        time.sleep(0.02)
        assert cb.state == AdapterState.HALF_OPEN

        cb.record_success()
        cb.record_success()

        assert cb.state == AdapterState.CLOSED

    def test_half_open_failure_reopens(self):
        """Any failure in HALF_OPEN reopens the circuit."""
        cb = SimpleCircuitBreaker(failure_threshold=1, recovery_timeout_s=0.01)

        cb.record_failure()
        import time

        time.sleep(0.02)
        assert cb.state == AdapterState.HALF_OPEN

        cb.record_failure()
        assert cb.state == AdapterState.OPEN

    def test_reset(self):
        """Reset returns circuit to CLOSED state."""
        cb = SimpleCircuitBreaker(failure_threshold=1)
        cb.record_failure()
        assert cb.state == AdapterState.OPEN

        cb.reset()
        assert cb.state == AdapterState.CLOSED


class TestTokenBucketRateLimiter:
    """Tests for TokenBucketRateLimiter."""

    @pytest.mark.asyncio
    async def test_allows_within_limit(self):
        """Allows requests within rate limit."""
        limiter = TokenBucketRateLimiter(rate_per_second=10.0, burst=5)

        for _ in range(5):
            assert await limiter.acquire() is True

    @pytest.mark.asyncio
    async def test_blocks_over_limit(self):
        """Blocks requests over rate limit."""
        limiter = TokenBucketRateLimiter(rate_per_second=1.0, burst=2)

        assert await limiter.acquire() is True
        assert await limiter.acquire() is True
        assert await limiter.acquire() is False

    @pytest.mark.asyncio
    async def test_replenishes_tokens(self):
        """Tokens replenish over time."""
        limiter = TokenBucketRateLimiter(rate_per_second=100.0, burst=1)

        assert await limiter.acquire() is True
        assert await limiter.acquire() is False

        await asyncio.sleep(0.02)  # Should replenish ~2 tokens

        assert await limiter.acquire() is True


class TestACLAdapterBase:
    """Tests for ACLAdapter base class."""

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Successful call returns result."""
        adapter = MockableAdapter()
        request = MockRequest(value="test123")

        result = await adapter.call(request)

        assert result.success is True
        assert result.data.result == "processed:test123"
        assert result.from_cache is False
        assert result.from_fallback is False

    @pytest.mark.asyncio
    async def test_caching(self):
        """Responses are cached."""
        config = AdapterConfig(cache_enabled=True, cache_ttl_s=60)
        adapter = MockableAdapter(config=config)
        request = MockRequest(value="cached")

        # First call - not cached
        result1 = await adapter.call(request)
        assert result1.from_cache is False
        assert adapter.execute_count == 1

        # Second call - cached
        result2 = await adapter.call(request)
        assert result2.from_cache is True
        assert result2.data.result == result1.data.result
        assert adapter.execute_count == 1  # No additional execution

    @pytest.mark.asyncio
    async def test_cache_bypass_on_different_request(self):
        """Different requests bypass cache."""
        adapter = MockableAdapter()

        await adapter.call(MockRequest(value="a"))
        await adapter.call(MockRequest(value="b"))

        assert adapter.execute_count == 2

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Timeout errors are handled correctly."""
        config = AdapterConfig(timeout_ms=50, max_retries=0, fallback_enabled=False)
        adapter = MockableAdapter(config=config, provide_fallback=False)
        request = MockRequest(value="slow", delay_ms=100)

        result = await adapter.call(request)

        assert result.success is False
        assert isinstance(result.error, AdapterTimeoutError)

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Failures trigger retries."""
        config = AdapterConfig(max_retries=2, retry_base_delay_ms=10, fallback_enabled=False)
        adapter = MockableAdapter(config=config, provide_fallback=False)
        request = MockRequest(value="fail", should_fail=True)

        result = await adapter.call(request)

        assert result.success is False
        assert adapter.execute_count == 3  # Initial + 2 retries
        assert result.retry_count == 2

    @pytest.mark.asyncio
    async def test_fallback_on_circuit_open(self):
        """Fallback is used when circuit is open."""
        config = AdapterConfig(
            circuit_failure_threshold=1,
            fallback_enabled=True,
            max_retries=0,
        )
        adapter = MockableAdapter(config=config)

        # Trigger circuit open
        await adapter.call(MockRequest(value="fail", should_fail=True))

        # Next call should use fallback
        result = await adapter.call(MockRequest(value="test"))

        assert result.success is True
        assert result.from_fallback is True
        assert result.data.result == "processed:fallback:test"

    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Rate limiting blocks excessive requests."""
        config = AdapterConfig(rate_limit_per_second=1.0, rate_limit_burst=1)
        adapter = MockableAdapter(config=config)

        # First request succeeds
        result1 = await adapter.call(MockRequest(value="1"))
        assert result1.success is True

        # Second request should be rate limited
        result2 = await adapter.call(MockRequest(value="2"))
        assert result2.success is False
        assert isinstance(result2.error, RateLimitExceededError)

    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Metrics are collected correctly."""
        config = AdapterConfig(fallback_enabled=False)
        adapter = MockableAdapter(config=config, provide_fallback=False)

        await adapter.call(MockRequest(value="success"))
        await adapter.call(MockRequest(value="fail", should_fail=True))
        await adapter.call(MockRequest(value="success"))  # Cached

        metrics = adapter.get_metrics()

        assert metrics["total_calls"] == 3
        # successful_calls counts only actual executions, not cache hits
        assert metrics["successful_calls"] == 1
        assert metrics["failed_calls"] == 1
        assert metrics["cache_hits"] == 1
        assert metrics["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Health check returns correct status."""
        adapter = MockableAdapter()

        health = adapter.get_health()

        assert health["healthy"] is True
        assert health["state"] == "closed"
        assert health["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_constitutional_hash_in_result(self):
        """Constitutional hash is included in results."""
        adapter = MockableAdapter()
        result = await adapter.call(MockRequest(value="test"))

        assert result.constitutional_hash == CONSTITUTIONAL_HASH


class TestExceptionSerialization:
    """Tests for exception serialization."""

    def test_timeout_error_serialization(self):
        """AdapterTimeoutError serializes correctly."""
        error = AdapterTimeoutError("test_adapter", 5000)
        data = error.to_dict()

        assert data["error"] == "AdapterTimeoutError"
        assert data["adapter"] == "test_adapter"
        assert data["timeout_ms"] == 5000
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_circuit_open_error_serialization(self):
        """AdapterCircuitOpenError serializes correctly."""
        error = AdapterCircuitOpenError("test_adapter", 30.0)
        data = error.to_dict()

        assert data["error"] == "AdapterCircuitOpenError"
        assert data["adapter"] == "test_adapter"
        assert data["recovery_time_s"] == 30.0
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH

    def test_rate_limit_error_serialization(self):
        """RateLimitExceededError serializes correctly."""
        error = RateLimitExceededError("test_adapter", 100.0)
        data = error.to_dict()

        assert data["error"] == "RateLimitExceededError"
        assert data["adapter"] == "test_adapter"
        assert data["limit_per_second"] == 100.0
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH
