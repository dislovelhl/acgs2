"""Advanced ACL Adapters Tests - Coverage Enhancement

Constitutional Hash: cdd01ef066bc6cf2

Tests for HTTP/Z3 integration paths, error handling, caching, circuit breaker
to improve coverage from 28-33% to >90%.

Uses pytest-mock for external deps."""

import asyncio
import time
from unittest.mock import patch

import pytest

from ...acl_adapters.base import (
    AdapterCircuitOpenError,
    AdapterState,
    AdapterTimeoutError,
    RateLimitExceededError,
    SimpleCircuitBreaker,
    TokenBucketRateLimiter,
)
from ...acl_adapters.opa_adapter import (
    OPAAdapter,
    OPAAdapterConfig,
    OPARequest,
    OPAResponse,
)
from ...acl_adapters.z3_adapter import Z3Adapter, Z3AdapterConfig, Z3Request, Z3Response


class TestSimpleCircuitBreaker:
    """Test the SimpleCircuitBreaker implementation."""

    def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in closed state."""
        cb = SimpleCircuitBreaker()
        assert cb.state == AdapterState.CLOSED
        assert cb.time_until_recovery == 0.0

    def test_circuit_breaker_failure_threshold(self):
        """Test circuit opens after failure threshold."""
        cb = SimpleCircuitBreaker(failure_threshold=2)

        # First failure - should stay closed
        cb.record_failure()
        assert cb.state == AdapterState.CLOSED

        # Second failure - should open
        cb.record_failure()
        assert cb.state == AdapterState.OPEN

    def test_circuit_breaker_recovery(self):
        """Test circuit recovery after timeout."""
        cb = SimpleCircuitBreaker(recovery_timeout_s=0.1)  # Fast recovery for test

        # Open circuit
        cb.record_failure()
        cb.record_failure()
        assert cb.state == AdapterState.OPEN

        # Wait for recovery
        time.sleep(0.15)
        assert cb.state == AdapterState.HALF_OPEN

    def test_circuit_breaker_half_open_success(self):
        """Test successful recovery from half-open state."""
        cb = SimpleCircuitBreaker()

        # Force half-open state
        cb._state = AdapterState.HALF_OPEN
        cb._half_open_calls = 0

        # Record success
        cb.record_success()
        assert cb.state == AdapterState.CLOSED

    def test_circuit_breaker_half_open_failure(self):
        """Test failed recovery from half-open state."""
        cb = SimpleCircuitBreaker()

        # Force half-open state
        cb._state = AdapterState.HALF_OPEN

        # Record failure - should reopen
        cb.record_failure()
        assert cb.state == AdapterState.OPEN


class TestTokenBucketRateLimiter:
    """Test the TokenBucketRateLimiter implementation."""

    @pytest.mark.asyncio
    async def test_rate_limiter_basic_functionality(self):
        """Test basic rate limiter functionality."""
        limiter = TokenBucketRateLimiter(rate_per_second=10, burst=5)

        # Should allow burst requests
        for _ in range(5):
            assert await limiter.acquire()

        # Should deny additional requests
        assert not await limiter.acquire()

    @pytest.mark.asyncio
    async def test_rate_limiter_token_replenishment(self):
        """Test token replenishment over time."""
        limiter = TokenBucketRateLimiter(rate_per_second=2, burst=1)

        # Use initial token
        assert await limiter.acquire()
        assert not await limiter.acquire()

        # Wait for token replenishment
        await asyncio.sleep(0.6)  # Should replenish ~1.2 tokens
        assert await limiter.acquire()


class TestOPAAdapter:
    """Test OPA adapter functionality."""

    @pytest.fixture
    def opa_adapter(self):
        """Create OPA adapter for testing."""
        config = OPAAdapterConfig(
            opa_url="http://localhost:8181", fail_closed=True, cache_enabled=True
        )
        return OPAAdapter("test-opa", config)

    def test_opa_adapter_initialization(self, opa_adapter):
        """Test OPA adapter initialization."""
        assert opa_adapter.name == "test-opa"
        assert opa_adapter.opa_config.fail_closed is True
        assert opa_adapter.opa_config.cache_enabled is True

    def test_opa_request_creation(self):
        """Test OPA request creation."""
        request = OPARequest(input={"user": "alice", "action": "read", "resource": "document"})

        assert request.input["user"] == "alice"
        assert request.trace_id is not None
        assert len(request.trace_id) == 16

    def test_opa_response_creation(self):
        """Test OPA response creation."""
        response = OPAResponse(allow=True, result={"decision": "allow"}, decision_id="test-123")

        assert response.allow is True
        assert response.result["decision"] == "allow"
        assert response.decision_id == "test-123"

    @pytest.mark.asyncio
    async def test_opa_adapter_cache_key_generation(self, opa_adapter):
        """Test cache key generation."""
        request = OPARequest(input={"test": "data"})

        # Mock the _execute method to avoid actual OPA calls
        with patch.object(opa_adapter, "_execute", return_value=OPAResponse(allow=True)):
            with patch.object(opa_adapter, "_validate_response", return_value=True):
                result = await opa_adapter.call(request)
                assert result.success

                # Check cache key was generated
                cache_key = opa_adapter._get_cache_key(request)
                assert isinstance(cache_key, str)
                assert len(cache_key) > 0

    @pytest.mark.asyncio
    async def test_opa_adapter_fail_closed_behavior(self, opa_adapter):
        """Test fail-closed behavior on errors."""
        request = OPARequest(input={"test": "data"})

        # Mock timeout error
        with patch.object(opa_adapter, "_execute_with_timeout", side_effect=asyncio.TimeoutError):
            result = await opa_adapter.call(request)

            # Should fail closed (deny)
            assert result.success is False
            assert result.data is not None
            assert result.data.allow is False

    @pytest.mark.asyncio
    async def test_opa_adapter_circuit_breaker_integration(self, opa_adapter):
        """Test circuit breaker integration."""
        request = OPARequest(input={"test": "data"})

        # Mock failures to trip circuit breaker
        with patch.object(
            opa_adapter, "_execute_with_timeout", side_effect=Exception("Test error")
        ):
            with patch.object(opa_adapter, "_validate_response", return_value=False):
                # Trigger circuit breaker
                for _ in range(6):  # More than failure threshold
                    await opa_adapter.call(request)

                assert opa_adapter.circuit_breaker.state == AdapterState.OPEN

    @pytest.mark.asyncio
    async def test_opa_adapter_rate_limiting(self, opa_adapter):
        """Test rate limiting."""
        request = OPARequest(input={"test": "data"})

        # Exhaust rate limit
        opa_adapter.config.rate_limit_per_second = 0  # No rate limit for test
        opa_adapter.rate_limiter._tokens = 0  # Force rate limit

        result = await opa_adapter.call(request)
        assert result.success is False
        assert isinstance(result.error, RateLimitExceededError)


class TestZ3Adapter:
    """Test Z3 adapter functionality."""

    @pytest.fixture
    def z3_adapter(self):
        """Create Z3 adapter for testing."""
        config = Z3AdapterConfig(cache_enabled=True, cache_ttl_s=3600)
        return Z3Adapter("test-z3", config)

    def test_z3_adapter_initialization(self, z3_adapter):
        """Test Z3 adapter initialization."""
        assert z3_adapter.name == "test-z3"
        assert z3_adapter.z3_config.cache_enabled is True
        assert z3_adapter.z3_config.cache_ttl_s == 3600

    def test_z3_request_creation(self):
        """Test Z3 request creation."""
        request = Z3Request(
            formula="(declare-const x Int) (= x 42)", assertions=["(assert (= x 42))"]
        )

        assert request.formula == "(declare-const x Int) (= x 42)"
        assert request.assertions == ["(assert (= x 42))"]
        assert request.trace_id is not None

    def test_z3_response_properties(self):
        """Test Z3 response properties."""
        response = Z3Response(result="sat", model={"x": 42})

        assert response.is_sat is True
        assert response.is_unsat is False
        assert response.is_unknown is False
        assert response.model["x"] == 42

    @pytest.mark.asyncio
    async def test_z3_adapter_without_z3_library(self, z3_adapter):
        """Test Z3 adapter behavior when Z3 library is not available."""
        # Mock Z3 as unavailable
        with patch.object(z3_adapter, "_check_z3_available", return_value=False):
            z3_adapter._z3_available = False

            request = Z3Request(formula="(assert true)")
            result = await z3_adapter.call(request)

            # Should use fallback response
            assert result.success is True
            assert result.from_fallback is True

    @pytest.mark.asyncio
    async def test_z3_adapter_caching(self, z3_adapter):
        """Test Z3 adapter caching behavior."""
        request = Z3Request(formula="(assert true)")

        # Mock successful execution
        mock_response = Z3Response(result="sat")
        with patch.object(z3_adapter, "_execute", return_value=mock_response):
            with patch.object(z3_adapter, "_validate_response", return_value=True):
                # First call
                result1 = await z3_adapter.call(request)
                assert result1.success
                assert not result1.from_cache

                # Second call should be from cache
                result2 = await z3_adapter.call(request)
                assert result2.success
                assert result2.from_cache

    @pytest.mark.asyncio
    async def test_z3_adapter_timeout_handling(self, z3_adapter):
        """Test timeout handling."""
        request = Z3Request(formula="(assert true)")

        # Mock timeout
        with patch.object(z3_adapter, "_execute_with_timeout", side_effect=asyncio.TimeoutError):
            result = await z3_adapter.call(request)

            assert result.success is False
            assert isinstance(result.error, AdapterTimeoutError)

    @pytest.mark.asyncio
    async def test_z3_adapter_metrics(self, z3_adapter):
        """Test metrics collection."""
        request = Z3Request(formula="(assert true)")

        # Mock successful call
        mock_response = Z3Response(result="sat")
        with patch.object(z3_adapter, "_execute", return_value=mock_response):
            with patch.object(z3_adapter, "_validate_response", return_value=True):
                await z3_adapter.call(request)

                metrics = z3_adapter.get_metrics()
                assert metrics["total_calls"] == 1
                assert metrics["successful_calls"] == 1
                assert metrics["success_rate"] == 1.0


class TestAdapterIntegration:
    """Integration tests for adapter functionality."""

    @pytest.mark.asyncio
    async def test_adapter_health_check(self):
        """Test adapter health check functionality."""
        adapter = OPAAdapter("test-health")

        health = adapter.get_health()
        assert "healthy" in health
        assert "state" in health
        assert "timestamp" in health
        assert health["state"] == "closed"

    @pytest.mark.asyncio
    async def test_adapter_metrics_reset(self):
        """Test adapter metrics and reset functionality."""
        adapter = OPAAdapter("test-metrics")

        # Initial state
        metrics = adapter.get_metrics()
        assert metrics["total_calls"] == 0

        # Reset circuit breaker
        adapter.reset_circuit_breaker()
        assert adapter.circuit_breaker.state == AdapterState.CLOSED

        # Clear cache
        adapter.clear_cache()
        assert len(adapter._cache) == 0

    @pytest.mark.asyncio
    async def test_adapter_fallback_responses(self):
        """Test fallback response functionality."""
        adapter = OPAAdapter("test-fallback")

        # Mock circuit open and no fallback
        adapter.circuit_breaker._state = AdapterState.OPEN
        adapter.config.fallback_enabled = False

        request = OPARequest(input={"test": "data"})
        result = await adapter.call(request)

        assert result.success is False
        assert isinstance(result.error, AdapterCircuitOpenError)

    @pytest.mark.asyncio
    async def test_adapter_retry_logic(self):
        """Test retry logic with exponential backoff."""
        adapter = OPAAdapter("test-retry")
        adapter.config.max_retries = 2

        request = OPARequest(input={"test": "data"})

        # Mock failures then success
        call_count = 0

        async def mock_execute(req):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return OPAResponse(allow=True)

        with patch.object(adapter, "_execute", side_effect=mock_execute):
            with patch.object(adapter, "_validate_response", return_value=True):
                result = await adapter.call(request)

                assert result.success
                assert result.retry_count == 2
                assert call_count == 3
