"""
Tests for Agent Wrapper
Constitutional Hash: cdd01ef066bc6cf2
"""

import pytest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from nemo_agent_toolkit.agent_wrapper import (
    ConstitutionalAgentWrapper,
    WrapperConfig,
    ExecutionResult,
    wrap_langchain_agent,
    wrap_llamaindex_agent,
    wrap_crewai_agent,
    constitutional_guardrail,
    NeMoAgentIntegration,
    CONSTITUTIONAL_HASH,
)
from nemo_agent_toolkit.constitutional_guardrails import (
    ConstitutionalGuardrails,
    GuardrailConfig,
    GuardrailResult,
    GuardrailAction,
)


class TestWrapperConfig:
    """Tests for WrapperConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = WrapperConfig()
        assert config.validate_inputs is True
        assert config.validate_outputs is True
        assert config.audit_enabled is True
        assert config.block_on_input_violation is True
        assert config.block_on_output_violation is False
        assert config.redact_output_pii is True
        assert config.constitutional_hash == CONSTITUTIONAL_HASH

    def test_custom_config(self):
        """Test custom configuration."""
        config = WrapperConfig(
            validate_inputs=False,
            block_on_output_violation=True,
            max_retries=5,
        )
        assert config.validate_inputs is False
        assert config.block_on_output_violation is True
        assert config.max_retries == 5


class TestExecutionResult:
    """Tests for ExecutionResult."""

    def test_success_result(self):
        """Test successful execution result."""
        result = ExecutionResult(
            success=True,
            output="Test output",
        )
        assert result.success is True
        assert result.output == "Test output"
        assert result.error is None
        assert result.constitutional_hash == CONSTITUTIONAL_HASH

    def test_error_result(self):
        """Test error execution result."""
        result = ExecutionResult(
            success=False,
            error="Something went wrong",
        )
        assert result.success is False
        assert result.output is None
        assert result.error == "Something went wrong"

    def test_result_with_checks(self):
        """Test result with guardrail checks."""
        input_check = GuardrailResult(
            action=GuardrailAction.ALLOW,
            allowed=True,
        )
        output_check = GuardrailResult(
            action=GuardrailAction.ALLOW,
            allowed=True,
        )
        result = ExecutionResult(
            success=True,
            output="Output",
            input_check=input_check,
            output_check=output_check,
            execution_time_ms=50.5,
        )
        assert result.input_check is not None
        assert result.output_check is not None
        assert result.execution_time_ms == 50.5


class TestConstitutionalAgentWrapper:
    """Tests for ConstitutionalAgentWrapper."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent."""
        agent = MagicMock()
        agent.invoke = AsyncMock(return_value="Agent response")
        return agent

    @pytest.fixture
    def wrapper(self, mock_agent):
        """Create wrapper with mock agent."""
        return ConstitutionalAgentWrapper(agent=mock_agent)

    def test_wrapper_initialization(self, wrapper, mock_agent):
        """Test wrapper initialization."""
        assert wrapper.agent is mock_agent
        assert wrapper.guardrails is not None

    def test_access_wrapped_agent(self, wrapper, mock_agent):
        """Test accessing the wrapped agent."""
        assert wrapper.agent is mock_agent

    def test_access_guardrails(self, wrapper):
        """Test accessing guardrails."""
        assert isinstance(wrapper.guardrails, ConstitutionalGuardrails)

    @pytest.mark.asyncio
    async def test_run_clean_input(self, wrapper):
        """Test running with clean input."""
        result = await wrapper.run("Hello, how are you?")
        assert result.success is True
        assert result.output == "Agent response"
        assert result.input_check is not None
        assert result.input_check.allowed is True

    @pytest.mark.asyncio
    async def test_run_blocked_input(self, mock_agent):
        """Test running with blocked input."""
        config = WrapperConfig(block_on_input_violation=True)
        wrapper = ConstitutionalAgentWrapper(agent=mock_agent, config=config)

        result = await wrapper.run("My SSN is 123-45-6789")
        assert result.success is False
        assert "blocked by constitutional guardrails" in result.error
        assert result.input_check.allowed is False

    @pytest.mark.asyncio
    async def test_run_with_context(self, wrapper):
        """Test running with context."""
        result = await wrapper.run(
            "Process this",
            context={"user_id": "123", "session": "abc"},
        )
        assert result.success is True

    @pytest.mark.asyncio
    async def test_run_dict_input(self, wrapper):
        """Test running with dictionary input."""
        result = await wrapper.run({"query": "test query"})
        assert result.success is True

    @pytest.mark.asyncio
    async def test_execution_history(self, wrapper):
        """Test execution history is recorded."""
        await wrapper.run("Test input 1")
        await wrapper.run("Test input 2")

        history = wrapper.get_execution_history()
        assert len(history) == 2
        assert all(h["constitutional_hash"] == CONSTITUTIONAL_HASH for h in history)

    @pytest.mark.asyncio
    async def test_get_metrics(self, wrapper):
        """Test getting metrics."""
        await wrapper.run("Test 1")
        await wrapper.run("Test 2")

        metrics = await wrapper.get_metrics()
        assert metrics["total_executions"] == 2
        assert "success_rate" in metrics
        assert "average_execution_time_ms" in metrics
        assert metrics["constitutional_hash"] == CONSTITUTIONAL_HASH

    @pytest.mark.asyncio
    async def test_get_metrics_empty(self, wrapper):
        """Test getting metrics with no executions."""
        metrics = await wrapper.get_metrics()
        assert metrics["total_executions"] == 0
        assert metrics["success_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_validation_disabled(self, mock_agent):
        """Test with validation disabled."""
        config = WrapperConfig(
            validate_inputs=False,
            validate_outputs=False,
        )
        wrapper = ConstitutionalAgentWrapper(agent=mock_agent, config=config)

        result = await wrapper.run("SSN: 123-45-6789")
        assert result.success is True
        assert result.input_check is None
        assert result.output_check is None

    @pytest.mark.asyncio
    async def test_agent_execution_error(self, mock_agent):
        """Test handling agent execution error."""
        mock_agent.invoke = AsyncMock(side_effect=Exception("Agent error"))
        wrapper = ConstitutionalAgentWrapper(agent=mock_agent)

        result = await wrapper.run("Test input")
        assert result.success is False
        assert "Agent error" in result.error


class TestAgentExecutionMethods:
    """Tests for different agent execution methods."""

    @pytest.mark.asyncio
    async def test_invoke_method(self):
        """Test agent with invoke method."""
        agent = MagicMock()
        agent.invoke = MagicMock(return_value="invoke result")
        wrapper = ConstitutionalAgentWrapper(agent=agent)

        result = await wrapper.run("test")
        assert result.output == "invoke result"

    @pytest.mark.asyncio
    async def test_ainvoke_method(self):
        """Test agent with ainvoke method."""
        agent = MagicMock(spec=["ainvoke"])
        agent.ainvoke = AsyncMock(return_value="ainvoke result")
        wrapper = ConstitutionalAgentWrapper(agent=agent)

        result = await wrapper.run("test")
        assert result.output == "ainvoke result"

    @pytest.mark.asyncio
    async def test_query_method(self):
        """Test agent with query method."""
        agent = MagicMock(spec=["query"])
        agent.query = MagicMock(return_value="query result")
        wrapper = ConstitutionalAgentWrapper(agent=agent)

        result = await wrapper.run("test")
        assert result.output == "query result"

    @pytest.mark.asyncio
    async def test_run_method(self):
        """Test agent with run method."""
        agent = MagicMock(spec=["run"])
        agent.run = MagicMock(return_value="run result")
        wrapper = ConstitutionalAgentWrapper(agent=agent)

        result = await wrapper.run("test")
        assert result.output == "run result"

    @pytest.mark.asyncio
    async def test_callable_agent(self):
        """Test callable agent."""
        # Create a callable that doesn't have invoke/run methods
        def simple_agent(x):
            return "callable result"

        wrapper = ConstitutionalAgentWrapper(agent=simple_agent)

        result = await wrapper.run("test")
        assert result.output == "callable result"


class TestWrapperFunctions:
    """Tests for wrapper convenience functions."""

    def test_wrap_langchain_agent(self):
        """Test wrap_langchain_agent function."""
        mock_agent = MagicMock()
        wrapped = wrap_langchain_agent(mock_agent)
        assert isinstance(wrapped, ConstitutionalAgentWrapper)
        assert wrapped.agent is mock_agent

    def test_wrap_langchain_agent_with_config(self):
        """Test wrap_langchain_agent with config."""
        mock_agent = MagicMock()
        config = WrapperConfig(validate_inputs=False)
        wrapped = wrap_langchain_agent(mock_agent, config=config)
        assert wrapped._config.validate_inputs is False

    def test_wrap_llamaindex_agent(self):
        """Test wrap_llamaindex_agent function."""
        mock_agent = MagicMock()
        wrapped = wrap_llamaindex_agent(mock_agent)
        assert isinstance(wrapped, ConstitutionalAgentWrapper)

    def test_wrap_crewai_agent(self):
        """Test wrap_crewai_agent function."""
        mock_crew = MagicMock()
        wrapped = wrap_crewai_agent(mock_crew)
        assert isinstance(wrapped, ConstitutionalAgentWrapper)


class TestConstitutionalGuardrailDecorator:
    """Tests for constitutional_guardrail decorator."""

    @pytest.mark.asyncio
    async def test_decorator_allows_clean_function(self):
        """Test decorator allows clean function execution."""
        @constitutional_guardrail()
        async def my_function(query: str) -> str:
            return f"Processed: {query}"

        result = await my_function("Hello world")
        assert result == "Processed: Hello world"

    @pytest.mark.asyncio
    async def test_decorator_blocks_violation(self):
        """Test decorator blocks on input violation."""
        @constitutional_guardrail()
        async def my_function(query: str) -> str:
            return f"Processed: {query}"

        with pytest.raises(ValueError, match="Input blocked"):
            await my_function("SSN: 123-45-6789")

    @pytest.mark.asyncio
    async def test_decorator_with_custom_guardrails(self):
        """Test decorator with custom guardrails."""
        config = GuardrailConfig(privacy_protection=False)
        guardrails = ConstitutionalGuardrails(config=config)

        @constitutional_guardrail(guardrails=guardrails)
        async def my_function(query: str) -> str:
            return f"Processed: {query}"

        # Should not block since privacy protection is disabled
        result = await my_function("Email: test@example.com")
        assert "Processed" in result

    @pytest.mark.asyncio
    async def test_decorator_input_validation_disabled(self):
        """Test decorator with input validation disabled."""
        @constitutional_guardrail(validate_input=False)
        async def my_function(query: str) -> str:
            return f"Processed: {query}"

        result = await my_function("SSN: 123-45-6789")
        assert "Processed" in result


class TestNeMoAgentIntegration:
    """Tests for NeMoAgentIntegration."""

    @pytest.fixture
    def integration(self):
        """Create integration instance."""
        return NeMoAgentIntegration()

    def test_create_input_hook(self, integration):
        """Test creating input hook."""
        hook = integration.create_input_hook()
        assert callable(hook)

    def test_create_output_hook(self, integration):
        """Test creating output hook."""
        hook = integration.create_output_hook()
        assert callable(hook)

    def test_get_profiler_callback(self, integration):
        """Test getting profiler callback."""
        callback = integration.get_profiler_callback()
        assert callable(callback)

        # Test callback adds constitutional hash
        event = {"type": "test"}
        callback(event)
        assert event["constitutional_hash"] == CONSTITUTIONAL_HASH


class TestConstitutionalHashEnforcement:
    """Tests for constitutional hash enforcement."""

    def test_module_hash(self):
        """Test module-level constitutional hash."""
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"

    def test_config_default_hash(self):
        """Test config default hash."""
        config = WrapperConfig()
        assert config.constitutional_hash == "cdd01ef066bc6cf2"

    def test_result_default_hash(self):
        """Test result default hash."""
        result = ExecutionResult(success=True, output="test")
        assert result.constitutional_hash == "cdd01ef066bc6cf2"

    @pytest.mark.asyncio
    async def test_metrics_include_hash(self):
        """Test metrics include constitutional hash."""
        agent = MagicMock()
        agent.invoke = MagicMock(return_value="test")
        wrapper = ConstitutionalAgentWrapper(agent=agent)

        await wrapper.run("test")
        metrics = await wrapper.get_metrics()
        assert metrics["constitutional_hash"] == "cdd01ef066bc6cf2"
