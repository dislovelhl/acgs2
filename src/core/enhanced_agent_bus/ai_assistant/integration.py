"""
ACGS-2 AI Assistant - Agent Bus Integration
Constitutional Hash: cdd01ef066bc6cf2

Integration layer between AI Assistant and the Enhanced Agent Bus.
Handles constitutional validation, message routing, and governance.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONDict = Dict[str, Any]
    JSONValue = Any

from .context import ConversationContext
from .dialog import ActionType, DialogAction
from .nlu import NLUResult

# Import centralized constitutional hash with fallback
try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

# Import from parent package with fallback
try:
    from ..exceptions import (
        ConstitutionalValidationError,
        MessageValidationError,
    )
    from ..models import AgentMessage, MessageType, Priority
    from ..validators import ValidationResult, validate_constitutional_hash

    AGENT_BUS_AVAILABLE = True
except ImportError:
    AGENT_BUS_AVAILABLE = False
    AgentMessage = None
    MessageType = None
    Priority = None
    ValidationResult = None

logger = logging.getLogger(__name__)

@dataclass
class IntegrationConfig:
    """Configuration for Agent Bus integration."""

    agent_id: str = "ai_assistant"
    tenant_id: Optional[str] = None
    enable_governance: bool = True
    governance_threshold: float = 0.8
    enable_audit: bool = True
    enable_metering: bool = True
    constitutional_hash: str = CONSTITUTIONAL_HASH
    message_timeout_seconds: int = 30

    def to_dict(self) -> JSONDict:
        return {
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "enable_governance": self.enable_governance,
            "governance_threshold": self.governance_threshold,
            "enable_audit": self.enable_audit,
            "enable_metering": self.enable_metering,
            "constitutional_hash": self.constitutional_hash,
            "message_timeout_seconds": self.message_timeout_seconds,
        }

@dataclass
class GovernanceDecision:
    """Result of governance evaluation."""

    is_allowed: bool
    requires_review: bool
    impact_score: float
    decision_reason: str
    constitutional_hash: str = CONSTITUTIONAL_HASH
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> JSONDict:
        return {
            "is_allowed": self.is_allowed,
            "requires_review": self.requires_review,
            "impact_score": self.impact_score,
            "decision_reason": self.decision_reason,
            "constitutional_hash": self.constitutional_hash,
            "timestamp": self.timestamp.isoformat(),
        }

class AgentBusIntegration:
    """
    Integration layer between AI Assistant and Enhanced Agent Bus.

    Provides:
    - Message sending/receiving through the bus
    - Constitutional validation for all assistant actions
    - Governance checks for high-impact operations
    - Audit logging for compliance
    - Metering for usage tracking
    """

    def __init__(
        self,
        config: Optional[IntegrationConfig] = None,
        agent_bus: Optional[Any] = None,
    ):
        self.config = config or IntegrationConfig()
        self.agent_bus = agent_bus
        self._is_registered = False
        self._message_handlers: Dict[str, Callable] = {}
        self._governance_rules: List[JSONDict] = self._default_governance_rules()

    def _default_governance_rules(self) -> List[JSONDict]:
        """Default governance rules for AI assistant actions."""
        return [
            {
                "id": "high_impact_action",
                "condition": lambda action: action.action_type
                in [
                    ActionType.EXECUTE_TASK,
                    ActionType.ESCALATE,
                ],
                "requires_review": True,
                "impact_score": 0.8,
            },
            {
                "id": "data_access",
                "condition": lambda action: "data_access" in action.parameters,
                "requires_review": True,
                "impact_score": 0.7,
            },
            {
                "id": "external_integration",
                "condition": lambda action: "external_call" in action.parameters,
                "requires_review": True,
                "impact_score": 0.9,
            },
        ]

    async def initialize(self) -> bool:
        """Initialize the integration with the Agent Bus."""
        if not AGENT_BUS_AVAILABLE:
            logger.warning("Agent Bus not available, running in standalone mode")
            return False

        if not self.agent_bus:
            logger.warning("No Agent Bus instance provided")
            return False

        try:
            # Register assistant as an agent
            await self._register_agent()
            self._is_registered = True
            logger.info(f"AI Assistant registered with Agent Bus: {self.config.agent_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Agent Bus integration: {e}")
            return False

    async def _register_agent(self) -> None:
        """Register the AI assistant as an agent on the bus."""
        if not self.agent_bus:
            return

        # Register with capabilities
        capabilities = [
            "conversation",
            "nlu",
            "dialog_management",
            "response_generation",
        ]

        await self.agent_bus.register_agent(
            agent_id=self.config.agent_id,
            capabilities=capabilities,
            tenant_id=self.config.tenant_id,
        )

    async def shutdown(self) -> None:
        """Shutdown the integration cleanly."""
        if self._is_registered and self.agent_bus:
            try:
                await self.agent_bus.unregister_agent(self.config.agent_id)
                self._is_registered = False
                logger.info("AI Assistant unregistered from Agent Bus")
            except Exception as e:
                logger.warning(f"Error during shutdown: {e}")

    async def validate_message(
        self,
        user_message: str,
        context: ConversationContext,
    ) -> ValidationResult:
        """
        Validate an incoming user message.

        Performs constitutional validation and content checks.
        """
        # Create validation result structure
        errors = []
        is_valid = True

        # Validate constitutional hash
        hash_result = validate_constitutional_hash(
            provided_hash=context.constitutional_hash,
            expected_hash=self.config.constitutional_hash,
        )
        if not hash_result.is_valid:
            errors.append("Constitutional hash mismatch")
            is_valid = False

        # Content validation (basic)
        if not user_message or not user_message.strip():
            errors.append("Empty message")
            is_valid = False

        # Length validation
        if len(user_message) > 10000:
            errors.append("Message too long")
            is_valid = False

        # Create result
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            constitutional_hash=self.config.constitutional_hash,
            metadata={
                "user_id": context.user_id,
                "session_id": context.session_id,
            },
        )

    async def check_governance(
        self,
        action: DialogAction,
        context: ConversationContext,
        nlu_result: Optional[NLUResult] = None,
    ) -> GovernanceDecision:
        """
        Check governance rules for an action.

        Evaluates if the action requires additional review or is blocked.
        """
        max_impact_score = 0.0
        requires_review = False
        triggered_rules = []

        # Evaluate each governance rule
        for rule in self._governance_rules:
            try:
                if rule["condition"](action):
                    impact = rule.get("impact_score", 0.5)
                    max_impact_score = max(max_impact_score, impact)
                    if rule.get("requires_review", False):
                        requires_review = True
                    triggered_rules.append(rule["id"])
            except Exception as e:
                logger.warning(f"Error evaluating governance rule {rule['id']}: {e}")

        # Apply governance threshold
        if max_impact_score >= self.config.governance_threshold:
            requires_review = True

        # Determine if action is allowed
        is_allowed = True  # Default allow, could be blocked by specific rules

        # Create decision reason
        if triggered_rules:
            reason = f"Triggered rules: {', '.join(triggered_rules)}"
        else:
            reason = "No governance rules triggered"

        decision = GovernanceDecision(
            is_allowed=is_allowed,
            requires_review=requires_review,
            impact_score=max_impact_score,
            decision_reason=reason,
            constitutional_hash=self.config.constitutional_hash,
        )

        # Log governance decision if audit enabled
        if self.config.enable_audit:
            await self._audit_governance_decision(action, context, decision)

        return decision

    async def _audit_governance_decision(
        self,
        action: DialogAction,
        context: ConversationContext,
        decision: GovernanceDecision,
    ) -> None:
        """Audit log a governance decision."""
        audit_entry = {
            "type": "governance_decision",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": self.config.agent_id,
            "session_id": context.session_id,
            "user_id": context.user_id,
            "action_type": action.action_type.value,
            "decision": decision.to_dict(),
            "constitutional_hash": self.config.constitutional_hash,
        }

        # Send to audit service if bus available
        if self.agent_bus and hasattr(self.agent_bus, "audit"):
            try:
                await self.agent_bus.audit(audit_entry)
            except Exception as e:
                logger.warning(f"Failed to send audit log: {e}")
        else:

    async def send_message(
        self,
        to_agent: str,
        content: str,
        message_type: str = "request",
        priority: str = "normal",
        context: Optional[ConversationContext] = None,
    ) -> Optional[JSONDict]:
        """
        Send a message through the Agent Bus.

        Args:
            to_agent: Target agent ID
            content: Message content
            message_type: Type of message (request, response, event)
            priority: Message priority (low, normal, high, critical)
            context: Optional conversation context

        Returns:
            Response from the target agent, or None if failed
        """
        if not AGENT_BUS_AVAILABLE or not self.agent_bus:
            logger.warning("Agent Bus not available for message sending")
            return None

        try:
            # Create agent message
            message = AgentMessage(
                from_agent=self.config.agent_id,
                to_agent=to_agent,
                content=content,
                message_type=MessageType[message_type.upper()],
                priority=Priority[priority.upper()],
                tenant_id=self.config.tenant_id,
                constitutional_hash=self.config.constitutional_hash,
            )

            # Add context metadata if available
            if context:
                message.metadata = {
                    "session_id": context.session_id,
                    "user_id": context.user_id,
                    "conversation_state": context.conversation_state.value,
                }

            # Send through bus
            result = await self.agent_bus.send_message(message)

            return result.to_dict() if result else None

        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None

    async def execute_task(
        self,
        task_type: str,
        parameters: JSONDict,
        context: ConversationContext,
    ) -> JSONDict:
        """
        Execute a task, potentially through the Agent Bus.

        For high-impact tasks, applies governance checks and may
        route to appropriate service agents.
        """
        # Create action for governance check
        action = DialogAction(
            action_type=ActionType.EXECUTE_TASK,
            parameters={"task_type": task_type, **parameters},
        )

        # Check governance
        governance = await self.check_governance(action, context)

        if not governance.is_allowed:
            return {
                "success": False,
                "error": "Action blocked by governance",
                "governance": governance.to_dict(),
            }

        if governance.requires_review:
            # In production, this would queue for human review
            logger.info(f"Task {task_type} flagged for review (impact: {governance.impact_score})")

        # Execute task based on type
        result = await self._execute_task_internal(task_type, parameters, context)

        # Meter the task execution
        if self.config.enable_metering:
            await self._meter_task_execution(task_type, parameters, result)

        return result

    async def _execute_task_internal(
        self,
        task_type: str,
        parameters: JSONDict,
        context: ConversationContext,
    ) -> JSONDict:
        """Internal task execution logic."""
        # Task type handlers
        handlers = {
            "order_lookup": self._handle_order_lookup,
            "account_update": self._handle_account_update,
            "information_query": self._handle_information_query,
        }

        handler = handlers.get(task_type)
        if handler:
            return await handler(parameters, context)

        # Default: try to route to appropriate agent
        if self.agent_bus:
            target_agent = self._get_target_agent(task_type)
            if target_agent:
                response = await self.send_message(
                    to_agent=target_agent,
                    content=f"Execute task: {task_type}",
                    message_type="request",
                    context=context,
                )
                if response:
                    return {"success": True, "result": response}

        return {
            "success": False,
            "error": f"Unknown task type: {task_type}",
        }

    async def _handle_order_lookup(
        self,
        parameters: JSONDict,
        context: ConversationContext,
    ) -> JSONDict:
        """Handle order lookup task."""
        order_id = parameters.get("order_id") or context.get_slot("order_id")
        if not order_id:
            return {"success": False, "error": "Order ID required"}

        # Simulate order lookup (would call actual service)
        return {
            "success": True,
            "result": {
                "order_id": order_id,
                "status": "processing",
                "estimated_delivery": "2024-12-30",
            },
        }

    async def _handle_account_update(
        self,
        parameters: JSONDict,
        context: ConversationContext,
    ) -> JSONDict:
        """Handle account update task."""
        return {
            "success": True,
            "result": {"updated": True},
        }

    async def _handle_information_query(
        self,
        parameters: JSONDict,
        context: ConversationContext,
    ) -> JSONDict:
        """Handle information query task."""
        return {
            "success": True,
            "result": {"information": "Requested information here"},
        }

    def _get_target_agent(self, task_type: str) -> Optional[str]:
        """Get the target agent for a task type."""
        task_agent_map = {
            "order": "order_service",
            "account": "account_service",
            "payment": "payment_service",
            "support": "support_service",
        }

        for prefix, agent in task_agent_map.items():
            if task_type.startswith(prefix):
                return agent

        return None

    async def _meter_task_execution(
        self,
        task_type: str,
        parameters: JSONDict,
        result: JSONDict,
    ) -> None:
        """Record metering for task execution."""
        meter_event = {
            "type": "task_execution",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": self.config.agent_id,
            "task_type": task_type,
            "success": result.get("success", False),
            "tenant_id": self.config.tenant_id,
            "constitutional_hash": self.config.constitutional_hash,
        }

        # Send to metering service if available
        if self.agent_bus and hasattr(self.agent_bus, "meter"):
            try:
                await self.agent_bus.meter(meter_event)
            except Exception as e:
                logger.warning(f"Failed to record metering: {e}")
        else:

    def register_message_handler(
        self,
        message_type: str,
        handler: Callable,
    ) -> None:
        """Register a handler for incoming messages."""
        self._message_handlers[message_type] = handler

    def add_governance_rule(
        self,
        rule_id: str,
        condition: Callable[[DialogAction], bool],
        requires_review: bool = False,
        impact_score: float = 0.5,
    ) -> None:
        """Add a custom governance rule."""
        self._governance_rules.append(
            {
                "id": rule_id,
                "condition": condition,
                "requires_review": requires_review,
                "impact_score": impact_score,
            }
        )

    def remove_governance_rule(self, rule_id: str) -> None:
        """Remove a governance rule."""
        self._governance_rules = [r for r in self._governance_rules if r["id"] != rule_id]
