"""
ACGS-2 Agent Wrapper for NeMo-Agent-Toolkit
Constitutional Hash: cdd01ef066bc6cf2

Provides wrapper classes that add constitutional guardrails to
popular AI agent frameworks: LangChain, LlamaIndex, CrewAI, etc.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

from nemo_agent_toolkit.constitutional_guardrails import (
    ConstitutionalGuardrails,
    GuardrailConfig,
    GuardrailResult,
    GuardrailAction,
)

if TYPE_CHECKING:
    pass

CONSTITUTIONAL_HASH: str = "cdd01ef066bc6cf2"

logger = logging.getLogger(__name__)

T = TypeVar("T")
AgentT = TypeVar("AgentT")


@dataclass
class WrapperConfig:
    """Configuration for agent wrapper."""

    validate_inputs: bool = True
    validate_outputs: bool = True
    audit_enabled: bool = True
    block_on_input_violation: bool = True
    block_on_output_violation: bool = False
    redact_output_pii: bool = True
    max_retries: int = 3
    timeout_seconds: float = 30.0
    constitutional_hash: str = CONSTITUTIONAL_HASH


@dataclass
class ExecutionResult(Generic[T]):
    """Result of a wrapped agent execution."""

    success: bool
    output: T | None = None
    error: str | None = None
    input_check: GuardrailResult | None = None
    output_check: GuardrailResult | None = None
    execution_time_ms: float = 0.0
    constitutional_hash: str = CONSTITUTIONAL_HASH
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class ConstitutionalAgentWrapper(Generic[AgentT]):
    """
    Generic wrapper that adds constitutional guardrails to any agent.

    This wrapper intercepts input and output, validates against
    constitutional principles, and provides audit logging.
    """

    def __init__(
        self,
        agent: AgentT,
        guardrails: ConstitutionalGuardrails | None = None,
        config: WrapperConfig | None = None,
        acgs2_client: Any | None = None,
    ) -> None:
        """
        Initialize the wrapper.

        Args:
            agent: The agent to wrap
            guardrails: Constitutional guardrails instance
            config: Wrapper configuration
            acgs2_client: ACGS-2 SDK client for backend operations
        """
        self._agent = agent
        self._config = config or WrapperConfig()
        self._guardrails = guardrails or ConstitutionalGuardrails(
            config=GuardrailConfig(
                block_on_violation=self._config.block_on_input_violation,
            ),
            acgs2_client=acgs2_client,
        )
        self._client = acgs2_client
        self._execution_history: list[dict[str, Any]] = []

    @property
    def agent(self) -> AgentT:
        """Get the wrapped agent."""
        return self._agent

    @property
    def guardrails(self) -> ConstitutionalGuardrails:
        """Get the guardrails instance."""
        return self._guardrails

    async def run(
        self,
        input_data: str | dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult[Any]:
        """
        Run the agent with constitutional guardrails.

        Args:
            input_data: Input for the agent
            context: Optional context for validation

        Returns:
            ExecutionResult with output and validation results
        """
        start_time = datetime.now(UTC)

        # Convert input to string for validation
        input_str = (
            input_data if isinstance(input_data, str)
            else str(input_data)
        )

        # Validate input
        input_check = None
        if self._config.validate_inputs:
            input_check = await self._guardrails.check_input(input_str, context)
            if not input_check.allowed and self._config.block_on_input_violation:
                return ExecutionResult(
                    success=False,
                    error=f"Input blocked by constitutional guardrails: {input_check.reasoning}",
                    input_check=input_check,
                    execution_time_ms=self._calculate_elapsed(start_time),
                )

        # Execute agent
        try:
            output = await self._execute_agent(input_data)
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                input_check=input_check,
                execution_time_ms=self._calculate_elapsed(start_time),
            )

        # Convert output to string for validation
        output_str = str(output) if output is not None else ""

        # Validate output
        output_check = None
        if self._config.validate_outputs:
            output_check = await self._guardrails.check_output(output_str, context)

            if output_check.action == GuardrailAction.MODIFY and output_check.modified_content:
                # Use modified (redacted) output
                output = output_check.modified_content

            if not output_check.allowed and self._config.block_on_output_violation:
                return ExecutionResult(
                    success=False,
                    error=f"Output blocked by constitutional guardrails: {output_check.reasoning}",
                    input_check=input_check,
                    output_check=output_check,
                    execution_time_ms=self._calculate_elapsed(start_time),
                )

        # Record execution
        execution_time = self._calculate_elapsed(start_time)
        self._record_execution(input_str, output_str, input_check, output_check, execution_time)

        return ExecutionResult(
            success=True,
            output=output,
            input_check=input_check,
            output_check=output_check,
            execution_time_ms=execution_time,
        )

    async def _execute_agent(self, input_data: str | dict[str, Any]) -> Any:
        """Execute the wrapped agent."""
        # Try common agent interfaces
        agent = self._agent

        # LangChain-style invoke
        if hasattr(agent, "invoke"):
            result = agent.invoke(input_data)
            if asyncio.iscoroutine(result):
                result = await result
            return result

        # LangChain-style ainvoke
        if hasattr(agent, "ainvoke"):
            return await agent.ainvoke(input_data)

        # LlamaIndex-style query
        if hasattr(agent, "query"):
            result = agent.query(input_data)
            if asyncio.iscoroutine(result):
                result = await result
            return result

        # LlamaIndex-style aquery
        if hasattr(agent, "aquery"):
            return await agent.aquery(input_data)

        # CrewAI-style kickoff
        if hasattr(agent, "kickoff"):
            result = agent.kickoff(inputs=input_data if isinstance(input_data, dict) else {"input": input_data})
            if asyncio.iscoroutine(result):
                result = await result
            return result

        # Generic run method
        if hasattr(agent, "run"):
            result = agent.run(input_data)
            if asyncio.iscoroutine(result):
                result = await result
            return result

        # Callable
        if callable(agent):
            result = agent(input_data)
            if asyncio.iscoroutine(result):
                result = await result
            return result

        raise TypeError(f"Unknown agent type: {type(agent)}. Cannot determine execution method.")

    def _calculate_elapsed(self, start_time: datetime) -> float:
        """Calculate elapsed time in milliseconds."""
        elapsed = datetime.now(UTC) - start_time
        return elapsed.total_seconds() * 1000

    def _record_execution(
        self,
        input_str: str,
        output_str: str,
        input_check: GuardrailResult | None,
        output_check: GuardrailResult | None,
        execution_time: float,
    ) -> None:
        """Record execution for audit."""
        if not self._config.audit_enabled:
            return

        import hashlib
        record = {
            "input_hash": hashlib.sha256(input_str.encode()).hexdigest()[:16],
            "output_hash": hashlib.sha256(output_str.encode()).hexdigest()[:16],
            "input_allowed": input_check.allowed if input_check else True,
            "output_allowed": output_check.allowed if output_check else True,
            "input_violations": len(input_check.violations) if input_check else 0,
            "output_violations": len(output_check.violations) if output_check else 0,
            "execution_time_ms": execution_time,
            "timestamp": datetime.now(UTC).isoformat(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }
        self._execution_history.append(record)

    def get_execution_history(self) -> list[dict[str, Any]]:
        """Get execution history."""
        return self._execution_history.copy()

    async def get_metrics(self) -> dict[str, Any]:
        """Get wrapper metrics."""
        total = len(self._execution_history)
        if total == 0:
            return {
                "total_executions": 0,
                "success_rate": 1.0,
                "average_execution_time_ms": 0.0,
                "constitutional_hash": CONSTITUTIONAL_HASH,
            }

        successful = sum(
            1 for e in self._execution_history
            if e.get("input_allowed", True) and e.get("output_allowed", True)
        )
        total_time = sum(e.get("execution_time_ms", 0) for e in self._execution_history)

        return {
            "total_executions": total,
            "successful_executions": successful,
            "success_rate": successful / total,
            "average_execution_time_ms": total_time / total,
            "input_violation_count": sum(e.get("input_violations", 0) for e in self._execution_history),
            "output_violation_count": sum(e.get("output_violations", 0) for e in self._execution_history),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }


def wrap_langchain_agent(
    agent: Any,
    config: WrapperConfig | None = None,
    acgs2_client: Any | None = None,
) -> ConstitutionalAgentWrapper[Any]:
    """
    Wrap a LangChain agent with constitutional guardrails.

    Args:
        agent: LangChain agent (chain, agent executor, etc.)
        config: Wrapper configuration
        acgs2_client: ACGS-2 SDK client

    Returns:
        ConstitutionalAgentWrapper wrapping the agent

    Example:
        ```python
        from langchain.agents import create_openai_agent
        from integrations.nemo_agent_toolkit import wrap_langchain_agent

        agent = create_openai_agent(llm, tools, prompt)
        wrapped = wrap_langchain_agent(agent)
        result = await wrapped.run("What is the weather?")
        ```
    """
    return ConstitutionalAgentWrapper(
        agent=agent,
        config=config,
        acgs2_client=acgs2_client,
    )


def wrap_llamaindex_agent(
    agent: Any,
    config: WrapperConfig | None = None,
    acgs2_client: Any | None = None,
) -> ConstitutionalAgentWrapper[Any]:
    """
    Wrap a LlamaIndex agent with constitutional guardrails.

    Args:
        agent: LlamaIndex agent or query engine
        config: Wrapper configuration
        acgs2_client: ACGS-2 SDK client

    Returns:
        ConstitutionalAgentWrapper wrapping the agent

    Example:
        ```python
        from llama_index.core.agent import ReActAgent
        from integrations.nemo_agent_toolkit import wrap_llamaindex_agent

        agent = ReActAgent.from_tools(tools, llm=llm)
        wrapped = wrap_llamaindex_agent(agent)
        result = await wrapped.run("Analyze this document")
        ```
    """
    return ConstitutionalAgentWrapper(
        agent=agent,
        config=config,
        acgs2_client=acgs2_client,
    )


def wrap_crewai_agent(
    crew: Any,
    config: WrapperConfig | None = None,
    acgs2_client: Any | None = None,
) -> ConstitutionalAgentWrapper[Any]:
    """
    Wrap a CrewAI crew with constitutional guardrails.

    Args:
        crew: CrewAI Crew instance
        config: Wrapper configuration
        acgs2_client: ACGS-2 SDK client

    Returns:
        ConstitutionalAgentWrapper wrapping the crew

    Example:
        ```python
        from crewai import Crew, Agent, Task
        from integrations.nemo_agent_toolkit import wrap_crewai_agent

        crew = Crew(agents=[agent], tasks=[task])
        wrapped = wrap_crewai_agent(crew)
        result = await wrapped.run({"topic": "AI Safety"})
        ```
    """
    return ConstitutionalAgentWrapper(
        agent=crew,
        config=config,
        acgs2_client=acgs2_client,
    )


def constitutional_guardrail(
    guardrails: ConstitutionalGuardrails | None = None,
    validate_input: bool = True,
    validate_output: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add constitutional guardrails to any async function.

    Args:
        guardrails: Constitutional guardrails instance
        validate_input: Whether to validate input
        validate_output: Whether to validate output

    Returns:
        Decorator function

    Example:
        ```python
        @constitutional_guardrail()
        async def process_request(query: str) -> str:
            # Process the query
            return response
        ```
    """
    _guardrails = guardrails or ConstitutionalGuardrails()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            # Validate input
            if validate_input and args:
                input_str = str(args[0])
                result = await _guardrails.check_input(input_str)
                if not result.allowed:
                    raise ValueError(f"Input blocked: {result.reasoning}")

            # Execute function
            output = func(*args, **kwargs)
            if asyncio.iscoroutine(output):
                output = await output

            # Validate output
            if validate_output and output is not None:
                output_str = str(output)
                result = await _guardrails.check_output(output_str)
                if result.action == GuardrailAction.MODIFY and result.modified_content:
                    return result.modified_content  # type: ignore
                if not result.allowed:
                    raise ValueError(f"Output blocked: {result.reasoning}")

            return output

        return wrapper  # type: ignore

    return decorator


class NeMoAgentIntegration:
    """
    Direct integration with NeMo-Agent-Toolkit.

    Provides hooks for NeMo's agent optimization pipeline
    with constitutional compliance.
    """

    def __init__(
        self,
        guardrails: ConstitutionalGuardrails | None = None,
        acgs2_client: Any | None = None,
    ) -> None:
        """
        Initialize NeMo integration.

        Args:
            guardrails: Constitutional guardrails instance
            acgs2_client: ACGS-2 SDK client
        """
        self._guardrails = guardrails or ConstitutionalGuardrails(
            acgs2_client=acgs2_client
        )
        self._client = acgs2_client

    def create_input_hook(self) -> Callable[[str], str]:
        """
        Create an input hook for NeMo's agent pipeline.

        Returns:
            Hook function for input processing
        """
        async def hook(input_text: str) -> str:
            result = await self._guardrails.check_input(input_text)
            if not result.allowed:
                raise ValueError(f"Constitutional violation: {result.reasoning}")
            return input_text

        return lambda x: asyncio.get_event_loop().run_until_complete(hook(x))

    def create_output_hook(self) -> Callable[[str], str]:
        """
        Create an output hook for NeMo's agent pipeline.

        Returns:
            Hook function for output processing
        """
        async def hook(output_text: str) -> str:
            result = await self._guardrails.check_output(output_text)
            if result.modified_content:
                return result.modified_content
            if not result.allowed:
                raise ValueError(f"Constitutional violation: {result.reasoning}")
            return output_text

        return lambda x: asyncio.get_event_loop().run_until_complete(hook(x))

    def get_profiler_callback(self) -> Callable[[dict[str, Any]], None]:
        """
        Get a callback for NeMo's profiler integration.

        Returns:
            Callback function for profiler events
        """
        def callback(event: dict[str, Any]) -> None:
            logger.info(f"NeMo profiler event: {event}")
            # Add constitutional hash to events
            event["constitutional_hash"] = CONSTITUTIONAL_HASH

        return callback
