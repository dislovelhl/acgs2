"""
ACGS-2 OPA Adapter Tests
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest

from ..opa_adapter import (
    CONSTITUTIONAL_HASH,
    OPAAdapter,
    OPAAdapterConfig,
    OPARequest,
    OPAResponse,
    check_agent_permission,
    check_constitutional_compliance,
    evaluate_maci_role,
)


class TestOPARequest:
    """Tests for OPARequest dataclass."""

    def test_auto_trace_id(self):
        """Trace ID is auto-generated from input."""
        request = OPARequest(input={"action": "read"})
        assert request.trace_id is not None
        assert len(request.trace_id) == 16

    def test_explicit_trace_id(self):
        """Explicit trace ID is preserved."""
        request = OPARequest(input={"action": "read"}, trace_id="custom123")
        assert request.trace_id == "custom123"

    def test_default_options(self):
        """Default options are set correctly."""
        request = OPARequest(input={})
        assert request.explain is False
        assert request.pretty is False
        assert request.metrics is True


class TestOPAResponse:
    """Tests for OPAResponse dataclass."""

    def test_serialization(self):
        """to_dict serializes correctly."""
        response = OPAResponse(
            allow=True,
            result={"allow": True, "reason": "permitted"},
            decision_id="dec123",
            trace_id="test123",
        )
        data = response.to_dict()

        assert data["allow"] is True
        assert data["result"]["reason"] == "permitted"
        assert data["decision_id"] == "dec123"
        assert data["constitutional_hash"] == CONSTITUTIONAL_HASH


class TestOPAAdapterConfig:
    """Tests for OPAAdapterConfig."""

    def test_default_config(self):
        """Default config values are correct."""
        config = OPAAdapterConfig()

        assert config.opa_url == "http://localhost:8181"
        assert config.fail_closed is True  # Security default
        assert config.timeout_ms == 1000  # Fast timeout
        assert config.circuit_failure_threshold == 3  # Fast circuit open

    def test_fail_closed_default(self):
        """Fail-closed is the default security mode."""
        config = OPAAdapterConfig()
        assert config.fail_closed is True


class TestOPAAdapter:
    """Tests for OPAAdapter."""

    def test_initialization(self):
        """Adapter initializes correctly."""
        adapter = OPAAdapter()

        assert adapter.name == "opa"
        assert adapter.constitutional_hash == CONSTITUTIONAL_HASH
        assert adapter.opa_config.fail_closed is True

    @pytest.mark.asyncio
    async def test_fallback_fail_closed(self):
        """Fallback denies in fail-closed mode."""
        config = OPAAdapterConfig(fail_closed=True)
        adapter = OPAAdapter(config=config)
        request = OPARequest(input={"action": "test"})

        fallback = adapter._get_fallback_response(request)

        assert fallback is not None
        assert fallback.allow is False
        assert fallback.result["fallback"] is True

    @pytest.mark.asyncio
    async def test_fallback_fail_open(self):
        """No fallback in fail-open mode."""
        config = OPAAdapterConfig(fail_closed=False)
        adapter = OPAAdapter(config=config)
        request = OPARequest(input={"action": "test"})

        fallback = adapter._get_fallback_response(request)

        assert fallback is None

    def test_cache_key_generation(self):
        """Cache key includes policy path and input."""
        adapter = OPAAdapter()

        req1 = OPARequest(input={"a": 1})
        req2 = OPARequest(input={"a": 1})
        req3 = OPARequest(input={"a": 2})

        key1 = adapter._get_cache_key(req1)
        key2 = adapter._get_cache_key(req2)
        key3 = adapter._get_cache_key(req3)

        assert key1 == key2  # Same input = same key
        assert key1 != key3  # Different input = different key

    def test_cache_key_includes_policy_path(self):
        """Different policy paths produce different cache keys."""
        adapter = OPAAdapter()

        req1 = OPARequest(input={"a": 1}, policy_path="path/a")
        req2 = OPARequest(input={"a": 1}, policy_path="path/b")

        key1 = adapter._get_cache_key(req1)
        key2 = adapter._get_cache_key(req2)

        assert key1 != key2

    def test_response_validation(self):
        """Response validation checks allow is boolean."""
        adapter = OPAAdapter()

        assert adapter._validate_response(OPAResponse(allow=True)) is True
        assert adapter._validate_response(OPAResponse(allow=False)) is True

    @pytest.mark.asyncio
    async def test_simulate_opa_fail_closed(self):
        """Simulated OPA response denies in fail-closed mode."""
        config = OPAAdapterConfig(fail_closed=True)
        adapter = OPAAdapter(config=config)
        request = OPARequest(input={"action": "test"})

        response = adapter._simulate_opa_response(request)

        assert response.allow is False
        assert response.result["simulated"] is True

    @pytest.mark.asyncio
    async def test_simulate_opa_fail_open(self):
        """Simulated OPA response allows in fail-open mode."""
        config = OPAAdapterConfig(fail_closed=False)
        adapter = OPAAdapter(config=config)
        request = OPARequest(input={"action": "test"})

        response = adapter._simulate_opa_response(request)

        assert response.allow is True
        assert response.result["simulated"] is True

    @pytest.mark.asyncio
    async def test_parse_opa_response_bool_result(self):
        """Parse OPA response with boolean result."""
        adapter = OPAAdapter()
        request = OPARequest(input={}, trace_id="test")

        response = adapter._parse_opa_response({"result": True}, request)
        assert response.allow is True

        response = adapter._parse_opa_response({"result": False}, request)
        assert response.allow is False

    @pytest.mark.asyncio
    async def test_parse_opa_response_dict_result(self):
        """Parse OPA response with dict result."""
        adapter = OPAAdapter()
        request = OPARequest(input={}, trace_id="test")

        response = adapter._parse_opa_response(
            {"result": {"allow": True, "reason": "permitted"}},
            request,
        )
        assert response.allow is True

        response = adapter._parse_opa_response(
            {"result": {"allowed": False}},  # Alternative key
            request,
        )
        assert response.allow is False


class TestOPAConvenienceFunctions:
    """Tests for OPA convenience functions."""

    @pytest.mark.asyncio
    async def test_check_constitutional_compliance_structure(self):
        """check_constitutional_compliance builds correct request."""
        # Create mock adapter that captures requests
        adapter = OPAAdapter()
        captured_requests = []

        original_call = adapter.call

        async def capture_call(request):
            captured_requests.append(request)
            return await original_call(request)

        adapter.call = capture_call

        await check_constitutional_compliance(
            action="read",
            resource="sensitive_data",
            context={"user_role": "admin"},
            adapter=adapter,
        )

        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert req.input["action"] == "read"
        assert req.input["resource"] == "sensitive_data"
        assert req.input["user_role"] == "admin"
        assert req.input["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_check_agent_permission_structure(self):
        """check_agent_permission builds correct request."""
        adapter = OPAAdapter()
        captured_requests = []

        original_call = adapter.call

        async def capture_call(request):
            captured_requests.append(request)
            return await original_call(request)

        adapter.call = capture_call

        await check_agent_permission(
            agent_id="agent-123",
            permission="execute",
            target="service-abc",
            adapter=adapter,
        )

        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert req.input["agent_id"] == "agent-123"
        assert req.input["permission"] == "execute"
        assert req.input["target"] == "service-abc"
        assert req.policy_path == "acgs2/agent/permissions"

    @pytest.mark.asyncio
    async def test_evaluate_maci_role_structure(self):
        """evaluate_maci_role builds correct request with explanation."""
        adapter = OPAAdapter()
        captured_requests = []

        original_call = adapter.call

        async def capture_call(request):
            captured_requests.append(request)
            return await original_call(request)

        adapter.call = capture_call

        await evaluate_maci_role(
            agent_role="executive",
            action="propose",
            target_role="judicial",
            adapter=adapter,
        )

        assert len(captured_requests) == 1
        req = captured_requests[0]
        assert req.input["agent_role"] == "executive"
        assert req.input["action"] == "propose"
        assert req.input["target_role"] == "judicial"
        assert req.explain is True  # Always explain role decisions
        assert req.policy_path == "acgs2/maci/role_separation"


class TestOPAFailClosedBehavior:
    """Tests for fail-closed security behavior."""

    @pytest.mark.asyncio
    async def test_circuit_open_denies_in_fail_closed(self):
        """When circuit is open, fail-closed mode denies."""
        config = OPAAdapterConfig(
            fail_closed=True,
            circuit_failure_threshold=1,
        )
        adapter = OPAAdapter(config=config)

        # Force circuit open
        adapter.circuit_breaker._state = adapter.circuit_breaker._state.__class__.OPEN
        adapter.circuit_breaker._failure_count = 10

        result = await adapter.call(OPARequest(input={"action": "test"}))

        assert result.success is True  # Fallback succeeded
        assert result.from_fallback is True
        assert result.data.allow is False  # Denied

    @pytest.mark.asyncio
    async def test_metrics_include_fail_closed(self):
        """Metrics show correct constitutional hash."""
        adapter = OPAAdapter()

        metrics = adapter.get_metrics()

        assert metrics["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert "adapter_name" in metrics
