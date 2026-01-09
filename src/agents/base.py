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
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from src.agents.skills import SkillManager

# Core AI Infrastructure Imports
try:
    from src.core.services.core.constitutional_retrieval_system.document_processor import (
        DocumentProcessor,
    )
    from src.core.services.core.constitutional_retrieval_system.llm_reasoner import LLMReasoner
    from src.core.services.core.constitutional_retrieval_system.retrieval_engine import (
        RetrievalEngine,
    )
    from src.core.services.core.constitutional_retrieval_system.vector_database import (
        create_vector_db_manager,
    )

    CORE_AI_AVAILABLE = True
except ImportError:
    LLMReasoner = None
    RetrievalEngine = None
    DocumentProcessor = None
    create_vector_db_manager = None
    CORE_AI_AVAILABLE = False

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

    # Skills
    skills: List[str] = field(default_factory=list)


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

        # AI Infrastructure
        self._ai_initialized: bool = False
        self.llm_reasoner: Optional[LLMReasoner] = None
        self.retrieval_engine: Optional[RetrievalEngine] = None

        # Skill Management
        self.skill_manager = SkillManager()
        self._skill_system_prompt: Optional[str] = None

        logger.info(f"Agent {name} initialized.")

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

    def get_effective_system_prompt(self) -> str:
        """Return system prompt augmented with skill instructions."""
        base_prompt = self.system_prompt
        if self.config.skills:
            return self.skill_manager.augment_prompt(base_prompt, self.config.skills)
        return base_prompt

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
        options: Dict[str, Any] = {
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

    async def _init_ai_infrastructure(self):
        """Initialize real AI components for production execution."""
        if self._ai_initialized:
            return

        if not CORE_AI_AVAILABLE:
            logger.warning("Core AI components not available. Falling back to simulation.")
            return

        try:
            # Initialize Vector DB
            vector_db = create_vector_db_manager(db_type="qdrant")
            await vector_db.connect()

            # Initialize Processors and Engines
            doc_processor = DocumentProcessor()
            self.retrieval_engine = RetrievalEngine(vector_db, doc_processor)
            self.llm_reasoner = LLMReasoner(
                retrieval_engine=self.retrieval_engine,
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                model_name=os.getenv("ACGS2_AGENT_MODEL", "gpt-4"),
            )
            self._ai_initialized = True
            logger.info(f"Agent {self.name} initialized with real AI infrastructure.")
        except Exception as e:
            logger.error(f"Failed to initialize AI infrastructure for {self.name}: {e}")
            self._ai_initialized = False

    async def run(self, prompt: str) -> AgentResult:
        """
        Execute the agent loop.

        In production, this retrieves context and calls the LLM Reasoner.
        """
        await self._init_ai_infrastructure()

        self.status = AgentStatus.RUNNING
        self._messages.append({"role": "user", "content": prompt})

        try:
            # Execute pre-execution hooks
            await self._execute_hooks("PreExecution", {"prompt": prompt})

            if self._ai_initialized:
                agent_result = await self._run_production_loop(prompt)
            else:
                agent_result = await self._run_simulation_fallback(prompt)

            # Execute post-execution hooks
            await self._execute_hooks(
                "PostExecution",
                {
                    "prompt": prompt,
                    "result": agent_result.to_dict(),
                },
            )

            self.status = AgentStatus.COMPLETED
            return agent_result

        except Exception as e:
            self.status = AgentStatus.FAILED
            logger.exception(f"Agent {self.name} failed during execution")
            return AgentResult(
                agent_name=self.name,
                status=AgentStatus.FAILED,
                errors=[str(e)],
            )

    async def _run_production_loop(self, prompt: str) -> AgentResult:
        """Execute the real retrieval-reasoning loop."""
        # 1. Retrieve relevant constitutional context
        if self.retrieval_engine is None:
            raise RuntimeError("Retrieval engine not initialized")

        context_docs = await self.retrieval_engine.retrieve_similar_documents(prompt, limit=5)

        # 2. Reason with context
        if self.llm_reasoner is None:
            raise RuntimeError("LLM Reasoner not initialized")

        response = await self.llm_reasoner.reason_with_context(
            query=prompt, context_documents=context_docs
        )

        result_text = response.get("reasoning", str(response))

        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=result_text,
            session_id=self._session_id,
            messages=self._messages + [{"role": "assistant", "content": result_text}],
            metrics={
                **response.get("metrics", {}),
                "context_docs_count": len(context_docs),
            },
        )

    async def _run_simulation_fallback(self, prompt: str) -> AgentResult:
        """Execute simulation fallback logic."""
        await asyncio.sleep(0.1)
        return AgentResult(
            agent_name=self.name,
            status=AgentStatus.COMPLETED,
            result=f"[SIMULATED] Processed: {prompt[:100]}...",
            session_id=self._session_id,
            messages=self._messages,
            metrics={"simulated": True},
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
