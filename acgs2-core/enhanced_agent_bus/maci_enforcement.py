"""
ACGS-2 MACI Role Separation Enforcement
Constitutional Hash: cdd01ef066bc6cf2

Implements the MACI (Model-based AI Constitutional Intelligence) framework
for preventing Gödel bypass attacks through strict role separation:
- Executive: Proposes decisions and actions
- Legislative: Extracts and synthesizes rules
- Judicial: Validates outputs from other roles

No agent can validate its own output (self-validation prevention).
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

from .exceptions import (
    MACICrossRoleValidationError,
    MACIRoleNotAssignedError,
    MACIRoleViolationError,
    MACISelfValidationError,
)
from .models import AgentMessage

logger = logging.getLogger(__name__)


class MACIRole(Enum):
    """MACI Framework roles implementing separation of powers."""

    EXECUTIVE = "executive"  # Proposes decisions
    LEGISLATIVE = "legislative"  # Extracts/synthesizes rules
    JUDICIAL = "judicial"  # Validates decisions


class MACIAction(Enum):
    """Actions that can be performed by MACI agents."""

    PROPOSE = "propose"  # Create a decision/proposal
    VALIDATE = "validate"  # Validate another agent's output
    EXTRACT_RULES = "extract_rules"  # Extract rules from content
    SYNTHESIZE = "synthesize"  # Synthesize policies
    AUDIT = "audit"  # Audit trail operations
    QUERY = "query"  # Read-only query (allowed for all)


# Role-to-action mapping: which roles can perform which actions
ROLE_PERMISSIONS: Dict[MACIRole, Set[MACIAction]] = {
    MACIRole.EXECUTIVE: {
        MACIAction.PROPOSE,
        MACIAction.SYNTHESIZE,
        MACIAction.QUERY,
    },
    MACIRole.LEGISLATIVE: {
        MACIAction.EXTRACT_RULES,
        MACIAction.SYNTHESIZE,
        MACIAction.QUERY,
    },
    MACIRole.JUDICIAL: {
        MACIAction.VALIDATE,
        MACIAction.AUDIT,
        MACIAction.QUERY,
    },
}

# Cross-role validation constraints: which roles can validate which
# Judicial can validate Executive and Legislative, but not other Judicial
VALIDATION_CONSTRAINTS: Dict[MACIRole, Set[MACIRole]] = {
    MACIRole.JUDICIAL: {MACIRole.EXECUTIVE, MACIRole.LEGISLATIVE},
}


@dataclass
class MACIAgentRecord:
    """Record of an agent's MACI role and outputs."""

    agent_id: str
    role: MACIRole
    outputs: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def add_output(self, output_id: str) -> None:
        """Record an output produced by this agent."""
        self.outputs.append(output_id)

    def owns_output(self, output_id: str) -> bool:
        """Check if this agent produced the given output."""
        return output_id in self.outputs

    def can_perform(self, action: MACIAction) -> bool:
        """Check if this agent's role allows the given action."""
        return action in ROLE_PERMISSIONS.get(self.role, set())

    def can_validate_role(self, target_role: MACIRole) -> bool:
        """Check if this agent can validate outputs from the target role."""
        if self.role != MACIRole.JUDICIAL:
            return False
        allowed = VALIDATION_CONSTRAINTS.get(self.role, set())
        return target_role in allowed


@dataclass
class MACIValidationContext:
    """Context for MACI validation operations."""

    source_agent_id: str
    action: MACIAction
    target_output_id: Optional[str] = None
    target_agent_id: Optional[str] = None
    message_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    constitutional_hash: str = CONSTITUTIONAL_HASH


@dataclass
class MACIValidationResult:
    """Result of MACI role validation."""

    is_valid: bool
    context: MACIValidationContext
    error_message: Optional[str] = None
    violation_type: Optional[str] = None
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "error_message": self.error_message,
            "violation_type": self.violation_type,
            "source_agent_id": self.context.source_agent_id,
            "action": self.context.action.value,
            "target_output_id": self.context.target_output_id,
            "target_agent_id": self.context.target_agent_id,
            "constitutional_hash": self.constitutional_hash,
        }


class MACIRoleRegistry:
    """
    Registry for MACI agent roles.

    Tracks which agents have which roles and their produced outputs.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self) -> None:
        self._agents: Dict[str, MACIAgentRecord] = {}
        self._output_to_agent: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        self.constitutional_hash = CONSTITUTIONAL_HASH

    async def register_agent(
        self,
        agent_id: str,
        role: MACIRole,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MACIAgentRecord:
        """
        Register an agent with a MACI role.

        Args:
            agent_id: Unique agent identifier
            role: MACI role (executive/legislative/judicial)
            metadata: Optional agent metadata

        Returns:
            MACIAgentRecord for the registered agent
        """
        async with self._lock:
            record = MACIAgentRecord(
                agent_id=agent_id,
                role=role,
                metadata=metadata or {},
            )
            self._agents[agent_id] = record
            logger.info(
                f"MACI: Registered agent '{agent_id}' with role '{role.value}' "
                f"[hash: {self.constitutional_hash}]"
            )
            return record

    async def unregister_agent(self, agent_id: str) -> Optional[MACIAgentRecord]:
        """Unregister an agent and clean up its output mappings."""
        async with self._lock:
            record = self._agents.pop(agent_id, None)
            if record:
                # Clean up output mappings
                for output_id in record.outputs:
                    self._output_to_agent.pop(output_id, None)
                logger.info(f"MACI: Unregistered agent '{agent_id}'")
            return record

    async def get_agent(self, agent_id: str) -> Optional[MACIAgentRecord]:
        """Get the MACI record for an agent."""
        async with self._lock:
            return self._agents.get(agent_id)

    async def get_agent_role(self, agent_id: str) -> Optional[MACIRole]:
        """Get the role of an agent."""
        record = await self.get_agent(agent_id)
        return record.role if record else None

    async def record_output(self, agent_id: str, output_id: str) -> None:
        """Record that an agent produced an output."""
        async with self._lock:
            record = self._agents.get(agent_id)
            if record:
                record.add_output(output_id)
                self._output_to_agent[output_id] = agent_id
                logger.debug(
                    f"MACI: Agent '{agent_id}' produced output '{output_id}'"
                )

    async def get_output_producer(self, output_id: str) -> Optional[str]:
        """Get the agent that produced a given output."""
        async with self._lock:
            return self._output_to_agent.get(output_id)

    async def get_output_producer_record(
        self, output_id: str
    ) -> Optional[MACIAgentRecord]:
        """Get the full record of the agent that produced an output."""
        agent_id = await self.get_output_producer(output_id)
        if agent_id:
            return await self.get_agent(agent_id)
        return None

    async def get_agents_by_role(self, role: MACIRole) -> List[MACIAgentRecord]:
        """Get all agents with a specific role."""
        async with self._lock:
            return [r for r in self._agents.values() if r.role == role]

    async def is_self_output(self, agent_id: str, output_id: str) -> bool:
        """Check if an agent is the producer of an output."""
        record = await self.get_agent(agent_id)
        if record:
            return record.owns_output(output_id)
        return False

    def get_all_agents(self) -> Dict[str, MACIAgentRecord]:
        """Get all registered agents (sync for inspection)."""
        return self._agents.copy()


class MACIEnforcer:
    """
    MACI role separation enforcer.

    Validates that agents only perform actions allowed by their role,
    prevents self-validation (Gödel bypass), and enforces cross-role
    validation constraints.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(
        self,
        registry: Optional[MACIRoleRegistry] = None,
        strict_mode: bool = True,
    ) -> None:
        """
        Initialize MACI enforcer.

        Args:
            registry: MACI role registry (created if not provided)
            strict_mode: If True, unregistered agents are rejected
        """
        self._registry = registry or MACIRoleRegistry()
        self._strict_mode = strict_mode
        self._validation_log: List[MACIValidationResult] = []
        self.constitutional_hash = CONSTITUTIONAL_HASH

    @property
    def registry(self) -> MACIRoleRegistry:
        """Get the MACI role registry."""
        return self._registry

    async def validate_action(
        self,
        agent_id: str,
        action: MACIAction,
        target_output_id: Optional[str] = None,
        target_agent_id: Optional[str] = None,
        message_id: Optional[str] = None,
    ) -> MACIValidationResult:
        """
        Validate that an agent can perform an action.

        Args:
            agent_id: Agent attempting the action
            action: Action being attempted
            target_output_id: For validation actions, the output being validated
            target_agent_id: For validation actions, the target agent
            message_id: Optional message ID for context

        Returns:
            MACIValidationResult with validation outcome

        Raises:
            MACIRoleNotAssignedError: If agent has no role (strict mode)
            MACIRoleViolationError: If action violates role permissions
            MACISelfValidationError: If self-validation attempted
            MACICrossRoleValidationError: If cross-role validation violated
        """
        context = MACIValidationContext(
            source_agent_id=agent_id,
            action=action,
            target_output_id=target_output_id,
            target_agent_id=target_agent_id,
            message_id=message_id,
        )

        # Get agent record
        record = await self._registry.get_agent(agent_id)

        # Check if agent is registered
        if record is None:
            if self._strict_mode:
                result = MACIValidationResult(
                    is_valid=False,
                    context=context,
                    error_message=f"Agent '{agent_id}' has no MACI role",
                    violation_type="no_role",
                )
                self._validation_log.append(result)
                raise MACIRoleNotAssignedError(agent_id, action.value)
            else:
                # Non-strict mode: allow unregistered agents
                return MACIValidationResult(
                    is_valid=True,
                    context=context,
                )

        # Check role permits the action
        if not record.can_perform(action):
            allowed_roles = [
                role.value
                for role, actions in ROLE_PERMISSIONS.items()
                if action in actions
            ]
            result = MACIValidationResult(
                is_valid=False,
                context=context,
                error_message=f"Role '{record.role.value}' cannot perform '{action.value}'",
                violation_type="role_violation",
            )
            self._validation_log.append(result)
            raise MACIRoleViolationError(
                agent_id=agent_id,
                role=record.role.value,
                action=action.value,
                allowed_roles=allowed_roles,
            )

        # For validation actions, check self-validation and cross-role constraints
        if action == MACIAction.VALIDATE:
            await self._check_validation_constraints(
                record, context, target_output_id, target_agent_id
            )

        # All checks passed
        result = MACIValidationResult(
            is_valid=True,
            context=context,
        )
        self._validation_log.append(result)
        return result

    async def _check_validation_constraints(
        self,
        validator_record: MACIAgentRecord,
        context: MACIValidationContext,
        target_output_id: Optional[str],
        target_agent_id: Optional[str],
    ) -> None:
        """Check self-validation and cross-role validation constraints."""
        # Check self-validation (Gödel bypass prevention)
        if target_output_id:
            if validator_record.owns_output(target_output_id):
                result = MACIValidationResult(
                    is_valid=False,
                    context=context,
                    error_message="Self-validation attempted (Gödel bypass)",
                    violation_type="self_validation",
                )
                self._validation_log.append(result)
                raise MACISelfValidationError(
                    agent_id=validator_record.agent_id,
                    action="validate",
                    output_id=target_output_id,
                )

            # Also check via registry
            producer_id = await self._registry.get_output_producer(target_output_id)
            if producer_id == validator_record.agent_id:
                result = MACIValidationResult(
                    is_valid=False,
                    context=context,
                    error_message="Self-validation attempted (Gödel bypass)",
                    violation_type="self_validation",
                )
                self._validation_log.append(result)
                raise MACISelfValidationError(
                    agent_id=validator_record.agent_id,
                    action="validate",
                    output_id=target_output_id,
                )

        # Check cross-role validation constraints
        if target_agent_id:
            target_record = await self._registry.get_agent(target_agent_id)
            if target_record is None:
                # Fail-closed: reject validation if target agent not registered
                if self._registry._agents:  # Registry has agents but target not found
                    result = MACIValidationResult(
                        is_valid=False,
                        context=context,
                        error_message=f"Target agent '{target_agent_id}' not registered",
                        violation_type="target_not_found",
                    )
                    self._validation_log.append(result)
                    raise MACIRoleNotAssignedError(target_agent_id, "validate_target")
            else:
                if not validator_record.can_validate_role(target_record.role):
                    result = MACIValidationResult(
                        is_valid=False,
                        context=context,
                        error_message=f"Cannot validate {target_record.role.value} outputs",
                        violation_type="cross_role_violation",
                    )
                    self._validation_log.append(result)
                    raise MACICrossRoleValidationError(
                        validator_agent=validator_record.agent_id,
                        validator_role=validator_record.role.value,
                        target_agent=target_agent_id,
                        target_role=target_record.role.value,
                        reason="Judicial agents cannot validate other judicial outputs",
                    )

        # Check via output producer if target_agent_id not provided
        if target_output_id and not target_agent_id:
            producer_record = await self._registry.get_output_producer_record(
                target_output_id
            )
            if producer_record:
                if not validator_record.can_validate_role(producer_record.role):
                    result = MACIValidationResult(
                        is_valid=False,
                        context=context,
                        error_message=f"Cannot validate {producer_record.role.value} outputs",
                        violation_type="cross_role_violation",
                    )
                    self._validation_log.append(result)
                    raise MACICrossRoleValidationError(
                        validator_agent=validator_record.agent_id,
                        validator_role=validator_record.role.value,
                        target_agent=producer_record.agent_id,
                        target_role=producer_record.role.value,
                        reason="Judicial agents cannot validate other judicial outputs",
                    )

    def get_validation_log(self) -> List[MACIValidationResult]:
        """Get the validation log."""
        return self._validation_log.copy()

    def clear_validation_log(self) -> None:
        """Clear the validation log."""
        self._validation_log.clear()


class MACIValidationStrategy:
    """
    Validation strategy implementing MACI role separation.

    Can be composed with other validation strategies in the agent bus.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(
        self,
        enforcer: Optional[MACIEnforcer] = None,
        strict_mode: bool = True,
    ) -> None:
        """
        Initialize MACI validation strategy.

        Args:
            enforcer: MACI enforcer (created if not provided)
            strict_mode: If True, messages without MACI context fail validation
        """
        self._enforcer = enforcer or MACIEnforcer(strict_mode=strict_mode)
        self._strict_mode = strict_mode
        self.constitutional_hash = CONSTITUTIONAL_HASH

    @property
    def enforcer(self) -> MACIEnforcer:
        """Get the MACI enforcer."""
        return self._enforcer

    @property
    def registry(self) -> MACIRoleRegistry:
        """Get the MACI role registry."""
        return self._enforcer.registry

    async def validate(
        self,
        message: AgentMessage,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate a message for MACI compliance.

        Checks that the sender has appropriate MACI role permissions
        for the message type/action.

        Args:
            message: The message to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Determine action from message type
        action = self._message_type_to_action(message)

        if action is None:
            # Unknown message type - pass through in non-strict mode
            if self._strict_mode:
                return False, f"Unknown message type for MACI validation: {message.message_type}"
            return True, None

        # Determine target output/agent from message content
        target_output_id = message.content.get("target_output_id") if isinstance(message.content, dict) else None
        target_agent_id = message.to_agent

        try:
            await self._enforcer.validate_action(
                agent_id=message.from_agent,
                action=action,
                target_output_id=target_output_id,
                target_agent_id=target_agent_id,
                message_id=message.message_id,
            )
            return True, None
        except (
            MACIRoleNotAssignedError,
            MACIRoleViolationError,
            MACISelfValidationError,
            MACICrossRoleValidationError,
        ) as e:
            logger.warning(
                f"MACI validation failed: {e} "
                f"[hash: {self.constitutional_hash}]"
            )
            return False, str(e)

    def _message_type_to_action(self, message: AgentMessage) -> Optional[MACIAction]:
        """Map message type to MACI action."""
        from .models import MessageType

        # Map existing MessageType enum values to MACI actions
        mapping = {
            MessageType.GOVERNANCE_REQUEST: MACIAction.PROPOSE,
            MessageType.GOVERNANCE_RESPONSE: MACIAction.PROPOSE,
            MessageType.CONSTITUTIONAL_VALIDATION: MACIAction.VALIDATE,
            MessageType.TASK_REQUEST: MACIAction.SYNTHESIZE,
            MessageType.TASK_RESPONSE: MACIAction.SYNTHESIZE,
            MessageType.QUERY: MACIAction.QUERY,
            MessageType.RESPONSE: MACIAction.QUERY,
            MessageType.COMMAND: MACIAction.PROPOSE,
            MessageType.EVENT: MACIAction.QUERY,
            MessageType.NOTIFICATION: MACIAction.QUERY,
            MessageType.HEARTBEAT: MACIAction.QUERY,
        }

        return mapping.get(message.message_type)


def create_maci_enforcement_middleware(
    enforcer: Optional[MACIEnforcer] = None,
) -> Callable:
    """
    Create middleware for MACI enforcement in the message processor.

    Usage:
        middleware = create_maci_enforcement_middleware()
        processor.add_middleware(middleware)
    """
    _enforcer = enforcer or MACIEnforcer()

    async def maci_middleware(
        message: AgentMessage,
        next_handler: Callable,
    ) -> Any:
        """MACI enforcement middleware."""
        strategy = MACIValidationStrategy(enforcer=_enforcer)
        is_valid, error = await strategy.validate(message)

        if not is_valid:
            logger.error(
                f"MACI validation blocked message: {error} "
                f"[message_id: {message.message_id}]"
            )
            raise MACIRoleViolationError(
                agent_id=message.from_agent,
                role="unknown",
                action=str(message.message_type),
            )

        return await next_handler(message)

    return maci_middleware


# =============================================================================
# Configuration-Based Role Management
# Constitutional Hash: cdd01ef066bc6cf2
# =============================================================================


@dataclass
class MACIAgentRoleConfig:
    """
    Configuration for a single agent's MACI role assignment.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    agent_id: str
    role: MACIRole
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize role if provided as string."""
        if isinstance(self.role, str):
            try:
                self.role = MACIRole(self.role.lower())
            except ValueError:
                # Try by name
                self.role = MACIRole[self.role.upper()]


@dataclass
class MACIConfig:
    """
    Full MACI configuration including role assignments.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    strict_mode: bool = True
    agents: List[MACIAgentRoleConfig] = field(default_factory=list)
    default_role: Optional[MACIRole] = None
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def get_role_for_agent(self, agent_id: str) -> Optional[MACIRole]:
        """Get the configured role for an agent ID."""
        for agent_config in self.agents:
            if agent_config.agent_id == agent_id:
                return agent_config.role
        return self.default_role

    def get_agent_config(self, agent_id: str) -> Optional[MACIAgentRoleConfig]:
        """Get the full configuration for an agent."""
        for agent_config in self.agents:
            if agent_config.agent_id == agent_id:
                return agent_config
        return None


class MACIConfigLoader:
    """
    Loads MACI configuration from various sources.

    Supports:
    - YAML files
    - JSON files
    - Python dictionaries
    - Environment variables

    Constitutional Hash: cdd01ef066bc6cf2
    """

    ENV_PREFIX = "MACI_AGENT_"

    def __init__(self):
        self.constitutional_hash = CONSTITUTIONAL_HASH

    def load_from_dict(self, config_dict: Dict[str, Any]) -> MACIConfig:
        """
        Load configuration from a dictionary.

        Args:
            config_dict: Dictionary with MACI configuration

        Returns:
            MACIConfig instance
        """
        strict_mode = config_dict.get("strict_mode", True)
        default_role_str = config_dict.get("default_role")
        default_role = None

        if default_role_str:
            try:
                default_role = MACIRole(default_role_str.lower())
            except ValueError:
                default_role = MACIRole[default_role_str.upper()]

        agents = []
        for agent_dict in config_dict.get("agents", []):
            agent_id = agent_dict.get("agent_id") or agent_dict.get("id")
            role_str = agent_dict.get("role")

            if not agent_id or not role_str:
                continue

            try:
                role = MACIRole(role_str.lower())
            except ValueError:
                role = MACIRole[role_str.upper()]

            agents.append(MACIAgentRoleConfig(
                agent_id=agent_id,
                role=role,
                capabilities=agent_dict.get("capabilities", []),
                metadata=agent_dict.get("metadata", {}),
            ))

        return MACIConfig(
            strict_mode=strict_mode,
            agents=agents,
            default_role=default_role,
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

    def load_from_yaml(self, yaml_path: str) -> MACIConfig:
        """
        Load configuration from a YAML file.

        Args:
            yaml_path: Path to YAML file

        Returns:
            MACIConfig instance
        """
        try:
            import yaml
        except ImportError:
            raise ImportError("PyYAML is required for YAML config loading. Install with: pip install pyyaml")

        with open(yaml_path, 'r') as f:
            config_dict = yaml.safe_load(f)

        return self.load_from_dict(config_dict)

    def load_from_json(self, json_path: str) -> MACIConfig:
        """
        Load configuration from a JSON file.

        Args:
            json_path: Path to JSON file

        Returns:
            MACIConfig instance
        """
        import json

        with open(json_path, 'r') as f:
            config_dict = json.load(f)

        return self.load_from_dict(config_dict)

    def load_from_env(self) -> MACIConfig:
        """
        Load configuration from environment variables.

        Environment variable format:
        - MACI_STRICT_MODE=true|false
        - MACI_DEFAULT_ROLE=executive|legislative|judicial
        - MACI_AGENT_<agent_id>=<role>
        - MACI_AGENT_<agent_id>_CAPABILITIES=cap1,cap2,cap3

        Returns:
            MACIConfig instance
        """
        import os

        strict_mode = os.environ.get("MACI_STRICT_MODE", "true").lower() == "true"
        default_role_str = os.environ.get("MACI_DEFAULT_ROLE")
        default_role = None

        if default_role_str:
            try:
                default_role = MACIRole(default_role_str.lower())
            except ValueError:
                default_role = None

        agents = []
        agent_ids = set()

        # Collect all agent IDs from environment variables
        for key in os.environ:
            if key.startswith(self.ENV_PREFIX) and not key.endswith("_CAPABILITIES"):
                agent_id = key[len(self.ENV_PREFIX):].lower()
                agent_ids.add(agent_id)

        for agent_id in agent_ids:
            role_str = os.environ.get(f"{self.ENV_PREFIX}{agent_id.upper()}")
            if not role_str:
                continue

            try:
                role = MACIRole(role_str.lower())
            except ValueError:
                continue

            capabilities_str = os.environ.get(f"{self.ENV_PREFIX}{agent_id.upper()}_CAPABILITIES", "")
            capabilities = [c.strip() for c in capabilities_str.split(",") if c.strip()]

            agents.append(MACIAgentRoleConfig(
                agent_id=agent_id,
                role=role,
                capabilities=capabilities,
            ))

        return MACIConfig(
            strict_mode=strict_mode,
            agents=agents,
            default_role=default_role,
            constitutional_hash=CONSTITUTIONAL_HASH,
        )

    def load(self, source: Optional[str] = None) -> MACIConfig:
        """
        Load configuration from auto-detected source.

        Args:
            source: Optional path to config file (YAML or JSON).
                   If None, loads from environment variables.

        Returns:
            MACIConfig instance
        """
        if source is None:
            return self.load_from_env()

        source_lower = source.lower()
        if source_lower.endswith(".yaml") or source_lower.endswith(".yml"):
            return self.load_from_yaml(source)
        elif source_lower.endswith(".json"):
            return self.load_from_json(source)
        else:
            # Try JSON first, then YAML
            try:
                return self.load_from_json(source)
            except Exception:
                return self.load_from_yaml(source)


async def apply_maci_config(
    registry: MACIRoleRegistry,
    config: MACIConfig,
) -> int:
    """
    Apply a MACI configuration to a registry.

    Args:
        registry: MACIRoleRegistry to populate
        config: MACIConfig with agent role assignments

    Returns:
        Number of agents registered
    """
    count = 0
    for agent_config in config.agents:
        await registry.register_agent(
            agent_id=agent_config.agent_id,
            role=agent_config.role,
            metadata={
                "capabilities": agent_config.capabilities,
                **agent_config.metadata,
            },
        )
        count += 1
        logger.info(
            f"Configured MACI role from config: {agent_config.agent_id} -> {agent_config.role.value}"
        )

    return count


__all__ = [
    # Enums
    "MACIRole",
    "MACIAction",
    # Data classes
    "MACIAgentRecord",
    "MACIValidationContext",
    "MACIValidationResult",
    # Configuration classes
    "MACIAgentRoleConfig",
    "MACIConfig",
    "MACIConfigLoader",
    # Core classes
    "MACIRoleRegistry",
    "MACIEnforcer",
    "MACIValidationStrategy",
    # Factory functions
    "create_maci_enforcement_middleware",
    "apply_maci_config",
    # Constants
    "ROLE_PERMISSIONS",
    "VALIDATION_CONSTRAINTS",
    "CONSTITUTIONAL_HASH",
]
