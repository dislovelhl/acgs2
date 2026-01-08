"""
Base Agent Infrastructure for ACGS-2 Claude Agent SDK Integration.

Provides shared functionality for all governance agents including:
- Session management
- Hook registration
- Error handling
- Logging integration
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentConfig:
    """Configuration for governance agents."""

    # Core settings
    allowed_tools: List[str] = field(default_factory=lambda: ["Read", "Glob", "Grep"])
    permission_mode: str = "default"  # "default", "acceptEdits", "bypassPermissions"
    working_directory: str = "."

    # Session settings
    resume_session: Optional[str] = None
    max_iterations: int = 50

    # MCP servers
    mcp_servers: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Hooks
    hooks: Dict[str, List[Any]] = field(default_factory=dict)

    # Subagents
    agents: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Governance-specific
    constitutional_hash: Optional[str] = None
    dfc_threshold: float = 0.70


@dataclass
class AgentResult:
    """Result from agent execution."""

    agent_name: str
    status: AgentStatus
    result: Optional[str] = None
    session_id: Optional[str] = None
    messages: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "status": self.status.value,
            "result": self.result,
            "session_id": self.session_id,
            "message_count": len(self.messages),
            "errors": self.errors,
            "metrics": self.metrics,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseGovernanceAgent(ABC):
    """
    Base class for all ACGS-2 governance agents.

    Provides common functionality for Claude Agent SDK integration.
    """

    def __init__(self, name: str, config: Optional[AgentConfig] = None):
        """
        Initialize the agent.

        Args:
            name: Agent identifier
            config: Agent configuration
        """
        self.name = name
        self.config = config or AgentConfig()
        self.status = AgentStatus.IDLE
        self._session_id: Optional[str] = None
        self._messages: List[Dict[str, Any]] = []
        self._hooks: Dict[str, List[Callable]] = {}

        logger.info(f"Initialized agent: {name}")

    @property
    @abstractmethod
    def description(self) -> str:
        """Return agent description."""
        pass

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return agent system prompt."""
        pass

    @abstractmethod
    async def run(self, prompt: str) -> AgentResult:
        """
        Execute the agent with given prompt.

        Args:
            prompt: User prompt for the agent

        Returns:
            AgentResult with execution details
        """
        pass

    def register_hook(self, hook_type: str, callback: Callable) -> None:
        """
        Register a hook callback.

        Args:
            hook_type: Type of hook (PreToolUse, PostToolUse, Stop, etc.)
            callback: Async callback function
        """
        if hook_type not in self._hooks:
            self._hooks[hook_type] = []
        self._hooks[hook_type].append(callback)
        logger.debug(f"Registered {hook_type} hook for {self.name}")

    async def _execute_hooks(self, hook_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute all hooks of a given type."""
        result = {}
        for callback in self._hooks.get(hook_type, []):
            try:
                hook_result = await callback(data)
                if hook_result:
                    result.update(hook_result)
            except Exception as e:
                logger.error(f"Hook {hook_type} failed: {e}")
        return result

    def _build_query_options(self) -> Dict[str, Any]:
        """Build options dict for claude_agent_sdk.query()."""
        options = {
            "allowedTools": self.config.allowed_tools,
            "permissionMode": self.config.permission_mode,
        }

        if self.config.resume_session:
            options["resume"] = self.config.resume_session

        if self.config.mcp_servers:
            options["mcpServers"] = self.config.mcp_servers

        if self.config.agents:
            options["agents"] = self.config.agents

        if self.config.hooks:
            options["hooks"] = self.config.hooks

        return options

    async def _simulate_execution(self, prompt: str) -> AgentResult:
        """
        Simulate agent execution for testing.

        In production, this would call claude_agent_sdk.query().
        """
        self.status = AgentStatus.RUNNING

        try:
            # Simulate processing
            await asyncio.sleep(0.1)

            self.status = AgentStatus.COMPLETED
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                result=f"[SIMULATED] Processed: {prompt[:100]}...",
                session_id=self._session_id,
                messages=self._messages,
                metrics={"simulated": True},
            )
        except Exception as e:
            self.status = AgentStatus.FAILED
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                errors=[str(e)],
            )


def create_audit_hook(log_file: str = "./agent_audit.log") -> Callable:
    """
    Create an audit hook that logs all tool usage.

    Args:
        log_file: Path to audit log file

    Returns:
        Async hook callback function
    """

    async def audit_hook(input_data: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = input_data.get("tool_name", "unknown")
        timestamp = datetime.now(timezone.utc).isoformat()

        with open(log_file, "a") as f:
            f.write(f"{timestamp}: {tool_name} - {input_data}\n")

        return {}

    return audit_hook


def create_governance_scope_hook(allowed_paths: List[str]) -> Callable:
    """
    Create a hook that restricts file access to governance-related paths.

    Args:
        allowed_paths: List of allowed path prefixes

    Returns:
        Async hook callback function
    """

    async def scope_hook(input_data: Dict[str, Any]) -> Dict[str, Any]:
        file_path = input_data.get("tool_input", {}).get("file_path", "")

        if not any(file_path.startswith(p) for p in allowed_paths):
            return {"decision": "block", "reason": "Path outside governance scope"}

        return {}

    return scope_hook
