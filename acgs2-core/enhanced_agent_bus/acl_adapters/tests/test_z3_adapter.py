"""
ACGS-2 Z3 Adapter Tests
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest

from ..z3_adapter import (
    Z3Adapter,
    Z3AdapterConfig,
    Z3Request,
    Z3Response,
    check_satisfiability,
    prove_property,
    CONSTITUTIONAL_HASH,
)


class TestZ3Request:
    """Tests for Z3Request dataclass."""

    def test_auto_trace_id(self):
        """Trace ID is auto-generated if not provided."""
        request = Z3Request(formula="(assert (> x 0))")
        assert request.trace_id is not None
        assert len(request.trace_id) == 16

    def test_explicit_trace_id(self):
        """Explicit trace ID is preserved."""
        request = Z3Request(formula="(assert true)", trace_id="custom123")
        assert request.trace_id == "custom123"

    def test_default_options(self):
        """Default options are set correctly."""
        request = Z3Request(formula="(assert true)")
        assert request.get_model is True
        assert request.get_proof is False
        assert request.get_unsat_core is False


class TestZ3Response:
    """Tests for Z3Response dataclass."""

    def test_is_sat(self):
        """is_sat property works correctly."""
        sat_response = Z3Response(result="sat")
        unsat_response = Z3Response(result="unsat")
        unknown_response = Z3Response(result="unknown")

        assert sat_response.is_sat is True
        assert unsat_response.is_sat is False
        assert unknown_response.is_sat is False

    def test_is_unsat(self):
        """is_unsat property works correctly."""
        sat_response = Z3Response(result="sat")
        unsat_response = Z3Response(result="unsat")

        assert sat_response.is_unsat is False
        assert unsat_response.is_unsat is True

    def test_is_unknown(self):
        """is_unknown property works correctly."""
        unknown_response = Z3Response(result="unknown")
        sat_response = Z3Response(result="sat")

        assert unknown_response.is_unknown is True
        assert sat_response.is_unknown is False

    def test_serialization(self):
        """to_dict serializes correctly."""
        response = Z3Response(
            result="sat",
            model={"x": "1"},
            statistics={"time": 0.5},
            trace_id="test123",
        )
        data = response.to_dict()

        assert data["result"] == "sat"
        assert data["model"] == {"x": "1"}
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH


class TestZ3AdapterConfig:
    """Tests for Z3AdapterConfig."""

    def test_default_config(self):
        """Default config values are reasonable."""
        config = Z3AdapterConfig()

        assert config.z3_timeout_ms == 30000
        assert config.memory_limit_mb == 1024
        assert config.cache_enabled is True
        assert config.cache_ttl_s == 3600  # Longer for deterministic results
        assert config.max_retries == 1  # Low retries for deterministic


class TestZ3Adapter:
    """Tests for Z3Adapter."""

    def test_initialization(self):
        """Adapter initializes correctly."""
        adapter = Z3Adapter()

        assert adapter.name == "z3"
        assert adapter.constitutional_hash == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_fallback_response(self):
        """Fallback returns unknown result."""
        adapter = Z3Adapter()
        request = Z3Request(formula="(assert true)", trace_id="fallback_test")

        fallback = adapter._get_fallback_response(request)

        assert fallback is not None
        assert fallback.result == "unknown"
        assert fallback.trace_id == "fallback_test"

    def test_cache_key_generation(self):
        """Cache key is generated from formula and assertions."""
        adapter = Z3Adapter()

        req1 = Z3Request(formula="(assert (> x 0))")
        req2 = Z3Request(formula="(assert (> x 0))")
        req3 = Z3Request(formula="(assert (> x 1))")

        key1 = adapter._get_cache_key(req1)
        key2 = adapter._get_cache_key(req2)
        key3 = adapter._get_cache_key(req3)

        assert key1 == key2  # Same formula = same key
        assert key1 != key3  # Different formula = different key

    def test_response_validation(self):
        """Response validation accepts valid results."""
        adapter = Z3Adapter()

        assert adapter._validate_response(Z3Response(result="sat")) is True
        assert adapter._validate_response(Z3Response(result="unsat")) is True
        assert adapter._validate_response(Z3Response(result="unknown")) is True
        assert adapter._validate_response(Z3Response(result="invalid")) is False


class TestZ3AdapterWithZ3:
    """Tests that require Z3 to be installed."""

    @pytest.fixture
    def z3_available(self):
        """Check if Z3 is available."""
        try:
            import z3  # noqa: F401
            return True
        except ImportError:
            return False

    @pytest.mark.asyncio
    async def test_simple_sat(self, z3_available):
        """Simple satisfiability check."""
        if not z3_available:
            pytest.skip("Z3 not available")

        adapter = Z3Adapter()
        request = Z3Request(
            formula="(declare-const x Int) (assert (> x 0))",
            get_model=True,
        )

        result = await adapter.call(request)

        assert result.success is True
        assert result.data.is_sat is True
        assert result.data.model is not None

    @pytest.mark.asyncio
    async def test_simple_unsat(self, z3_available):
        """Simple unsatisfiability check."""
        if not z3_available:
            pytest.skip("Z3 not available")

        adapter = Z3Adapter()
        request = Z3Request(
            formula="(declare-const x Int) (assert (and (> x 0) (< x 0)))",
        )

        result = await adapter.call(request)

        assert result.success is True
        assert result.data.is_unsat is True

    @pytest.mark.asyncio
    async def test_fallback_when_z3_unavailable(self):
        """Falls back gracefully when Z3 unavailable."""
        adapter = Z3Adapter()
        adapter._z3_available = False  # Simulate Z3 not available

        request = Z3Request(formula="(assert true)")
        result = await adapter.call(request)

        # Should get unknown result from fallback
        assert result.success is True
        assert result.data.is_unknown is True


class TestZ3ConvenienceFunctions:
    """Tests for convenience functions."""

    @pytest.fixture
    def z3_available(self):
        """Check if Z3 is available."""
        try:
            import z3  # noqa: F401
            return True
        except ImportError:
            return False

    @pytest.mark.asyncio
    async def test_check_satisfiability(self, z3_available):
        """check_satisfiability convenience function."""
        if not z3_available:
            pytest.skip("Z3 not available")

        result = await check_satisfiability(
            "(declare-const x Int) (assert (= x 42))"
        )

        assert result.success is True
        assert result.data.is_sat is True

    @pytest.mark.asyncio
    async def test_prove_property(self, z3_available):
        """prove_property convenience function."""
        if not z3_available:
            pytest.skip("Z3 not available")

        # Property: x > 0 implies x >= 1 (for integers)
        result = await prove_property(
            "(=> (> x 0) (>= x 1))",
            context_assertions=["(declare-const x Int)"],
        )

        assert result.success is True
        # Should be unsat (negation is unsatisfiable = property holds)
        assert result.data.is_unsat is True
