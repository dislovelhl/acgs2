"""
ACGS-2 Enhanced Agent Bus - Exceptions
Constitutional Hash: cdd01ef066bc6cf2

Custom exception types for better error handling, debugging, and monitoring.
Provides specific exception classes for different error categories.
"""

from typing import Any, Dict, List, Optional


CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


class AgentBusError(Exception):
    """
    Base exception for all Enhanced Agent Bus errors.

    All custom exceptions in the agent bus inherit from this class,
    allowing for catch-all error handling when needed.
    """

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        constitutional_hash: str = CONSTITUTIONAL_HASH,
    ):
        self.message = message
        self.details = details or {}
        self.constitutional_hash = constitutional_hash
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
            "constitutional_hash": self.constitutional_hash,
        }


# =============================================================================
# Constitutional Validation Errors
# =============================================================================

class ConstitutionalError(AgentBusError):
    """Base exception for constitutional compliance failures."""
    pass


class ConstitutionalHashMismatchError(ConstitutionalError):
    """Raised when constitutional hash validation fails."""

    def __init__(
        self,
        expected_hash: str,
        actual_hash: str,
        context: Optional[str] = None,
    ):
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        message = f"Constitutional hash mismatch: expected '{expected_hash}', got '{actual_hash}'"
        if context:
            message += f" (context: {context})"
        super().__init__(
            message=message,
            details={
                "expected_hash": expected_hash,
                "actual_hash": actual_hash,
                "context": context,
            },
        )


class ConstitutionalValidationError(ConstitutionalError):
    """Raised when constitutional validation fails for any reason."""

    def __init__(
        self,
        validation_errors: List[str],
        agent_id: Optional[str] = None,
        action_type: Optional[str] = None,
    ):
        self.validation_errors = validation_errors
        self.agent_id = agent_id
        self.action_type = action_type
        message = f"Constitutional validation failed: {'; '.join(validation_errors)}"
        super().__init__(
            message=message,
            details={
                "validation_errors": validation_errors,
                "agent_id": agent_id,
                "action_type": action_type,
            },
        )


# =============================================================================
# Message Processing Errors
# =============================================================================

class MessageError(AgentBusError):
    """Base exception for message-related errors."""
    pass


class MessageValidationError(MessageError):
    """Raised when message validation fails."""

    def __init__(
        self,
        message_id: str,
        errors: List[str],
        warnings: Optional[List[str]] = None,
    ):
        self.message_id = message_id
        self.errors = errors
        self.warnings = warnings or []
        error_text = f"Message validation failed for '{message_id}': {'; '.join(errors)}"
        super().__init__(
            message=error_text,
            details={
                "message_id": message_id,
                "errors": errors,
                "warnings": self.warnings,
            },
        )


class MessageDeliveryError(MessageError):
    """Raised when message delivery fails."""

    def __init__(
        self,
        message_id: str,
        target_agent: str,
        reason: str,
    ):
        self.message_id = message_id
        self.target_agent = target_agent
        self.reason = reason
        super().__init__(
            message=f"Failed to deliver message '{message_id}' to agent '{target_agent}': {reason}",
            details={
                "message_id": message_id,
                "target_agent": target_agent,
                "reason": reason,
            },
        )


class MessageTimeoutError(MessageError):
    """Raised when message processing times out."""

    def __init__(
        self,
        message_id: str,
        timeout_ms: int,
        operation: Optional[str] = None,
    ):
        self.message_id = message_id
        self.timeout_ms = timeout_ms
        self.operation = operation
        message = f"Message '{message_id}' timed out after {timeout_ms}ms"
        if operation:
            message += f" during {operation}"
        super().__init__(
            message=message,
            details={
                "message_id": message_id,
                "timeout_ms": timeout_ms,
                "operation": operation,
            },
        )


class MessageRoutingError(MessageError):
    """Raised when message routing fails."""

    def __init__(
        self,
        message_id: str,
        source_agent: str,
        target_agent: str,
        reason: str,
    ):
        self.message_id = message_id
        self.source_agent = source_agent
        self.target_agent = target_agent
        self.reason = reason
        super().__init__(
            message=f"Failed to route message '{message_id}' from '{source_agent}' to '{target_agent}': {reason}",
            details={
                "message_id": message_id,
                "source_agent": source_agent,
                "target_agent": target_agent,
                "reason": reason,
            },
        )


# =============================================================================
# Agent Registration Errors
# =============================================================================

class AgentError(AgentBusError):
    """Base exception for agent-related errors."""
    pass


class AgentNotRegisteredError(AgentError):
    """Raised when an operation requires a registered agent that doesn't exist."""

    def __init__(self, agent_id: str, operation: Optional[str] = None):
        self.agent_id = agent_id
        self.operation = operation
        message = f"Agent '{agent_id}' is not registered"
        if operation:
            message += f" (required for {operation})"
        super().__init__(
            message=message,
            details={
                "agent_id": agent_id,
                "operation": operation,
            },
        )


class AgentAlreadyRegisteredError(AgentError):
    """Raised when attempting to register an agent that already exists."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        super().__init__(
            message=f"Agent '{agent_id}' is already registered",
            details={"agent_id": agent_id},
        )


class AgentCapabilityError(AgentError):
    """Raised when an agent lacks required capabilities."""

    def __init__(
        self,
        agent_id: str,
        required_capabilities: List[str],
        available_capabilities: List[str],
    ):
        self.agent_id = agent_id
        self.required_capabilities = required_capabilities
        self.available_capabilities = available_capabilities
        missing = set(required_capabilities) - set(available_capabilities)
        super().__init__(
            message=f"Agent '{agent_id}' missing capabilities: {', '.join(missing)}",
            details={
                "agent_id": agent_id,
                "required_capabilities": required_capabilities,
                "available_capabilities": available_capabilities,
                "missing_capabilities": list(missing),
            },
        )


# =============================================================================
# Policy and OPA Errors
# =============================================================================

class PolicyError(AgentBusError):
    """Base exception for policy-related errors."""
    pass


class PolicyEvaluationError(PolicyError):
    """Raised when policy evaluation fails."""

    def __init__(
        self,
        policy_path: str,
        reason: str,
        input_data: Optional[Dict[str, Any]] = None,
    ):
        self.policy_path = policy_path
        self.reason = reason
        self.input_data = input_data
        super().__init__(
            message=f"Policy evaluation failed for '{policy_path}': {reason}",
            details={
                "policy_path": policy_path,
                "reason": reason,
                "input_data": input_data,
            },
        )


class PolicyNotFoundError(PolicyError):
    """Raised when a required policy is not found."""

    def __init__(self, policy_path: str):
        self.policy_path = policy_path
        super().__init__(
            message=f"Policy not found: '{policy_path}'",
            details={"policy_path": policy_path},
        )


class OPAConnectionError(PolicyError):
    """Raised when connection to OPA server fails."""

    def __init__(self, opa_url: str, reason: str):
        self.opa_url = opa_url
        self.reason = reason
        super().__init__(
            message=f"Failed to connect to OPA at '{opa_url}': {reason}",
            details={
                "opa_url": opa_url,
                "reason": reason,
            },
        )


class OPANotInitializedError(PolicyError):
    """Raised when OPA client is not properly initialized."""

    def __init__(self, operation: str):
        self.operation = operation
        super().__init__(
            message=f"OPA client not initialized for operation: {operation}",
            details={"operation": operation},
        )


# =============================================================================
# Deliberation Layer Errors
# =============================================================================

class DeliberationError(AgentBusError):
    """Base exception for deliberation layer errors."""
    pass


class DeliberationTimeoutError(DeliberationError):
    """Raised when deliberation process times out."""

    def __init__(
        self,
        decision_id: str,
        timeout_seconds: int,
        pending_reviews: int = 0,
        pending_signatures: int = 0,
    ):
        self.decision_id = decision_id
        self.timeout_seconds = timeout_seconds
        self.pending_reviews = pending_reviews
        self.pending_signatures = pending_signatures
        super().__init__(
            message=f"Deliberation '{decision_id}' timed out after {timeout_seconds}s",
            details={
                "decision_id": decision_id,
                "timeout_seconds": timeout_seconds,
                "pending_reviews": pending_reviews,
                "pending_signatures": pending_signatures,
            },
        )


class SignatureCollectionError(DeliberationError):
    """Raised when signature collection fails."""

    def __init__(
        self,
        decision_id: str,
        required_signers: List[str],
        collected_signers: List[str],
        reason: str,
    ):
        self.decision_id = decision_id
        self.required_signers = required_signers
        self.collected_signers = collected_signers
        self.reason = reason
        missing = set(required_signers) - set(collected_signers)
        super().__init__(
            message=f"Signature collection failed for '{decision_id}': {reason}",
            details={
                "decision_id": decision_id,
                "required_signers": required_signers,
                "collected_signers": collected_signers,
                "missing_signers": list(missing),
                "reason": reason,
            },
        )


class ReviewConsensusError(DeliberationError):
    """Raised when critic review consensus cannot be reached."""

    def __init__(
        self,
        decision_id: str,
        approval_count: int,
        rejection_count: int,
        escalation_count: int,
    ):
        self.decision_id = decision_id
        self.approval_count = approval_count
        self.rejection_count = rejection_count
        self.escalation_count = escalation_count
        super().__init__(
            message=f"Review consensus not reached for '{decision_id}': "
                    f"{approval_count} approvals, {rejection_count} rejections, "
                    f"{escalation_count} escalations",
            details={
                "decision_id": decision_id,
                "approval_count": approval_count,
                "rejection_count": rejection_count,
                "escalation_count": escalation_count,
            },
        )


# =============================================================================
# Bus Operation Errors
# =============================================================================

class BusOperationError(AgentBusError):
    """Base exception for bus operation errors."""
    pass


class BusNotStartedError(BusOperationError):
    """Raised when operation requires a started bus."""

    def __init__(self, operation: str):
        self.operation = operation
        super().__init__(
            message=f"Agent bus not started for operation: {operation}",
            details={"operation": operation},
        )


class BusAlreadyStartedError(BusOperationError):
    """Raised when attempting to start an already running bus."""

    def __init__(self):
        super().__init__(
            message="Agent bus is already running",
            details={},
        )


class HandlerExecutionError(BusOperationError):
    """Raised when a message handler fails during execution."""

    def __init__(
        self,
        handler_name: str,
        message_id: str,
        original_error: Exception,
    ):
        self.handler_name = handler_name
        self.message_id = message_id
        self.original_error = original_error
        super().__init__(
            message=f"Handler '{handler_name}' failed for message '{message_id}': {original_error}",
            details={
                "handler_name": handler_name,
                "message_id": message_id,
                "original_error": str(original_error),
                "original_error_type": type(original_error).__name__,
            },
        )


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(AgentBusError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, config_key: str, reason: str):
        self.config_key = config_key
        self.reason = reason
        super().__init__(
            message=f"Configuration error for '{config_key}': {reason}",
            details={
                "config_key": config_key,
                "reason": reason,
            },
        )


# =============================================================================
# Export all exceptions
# =============================================================================

__all__ = [
    # Base
    "AgentBusError",
    # Constitutional
    "ConstitutionalError",
    "ConstitutionalHashMismatchError",
    "ConstitutionalValidationError",
    # Message
    "MessageError",
    "MessageValidationError",
    "MessageDeliveryError",
    "MessageTimeoutError",
    "MessageRoutingError",
    # Agent
    "AgentError",
    "AgentNotRegisteredError",
    "AgentAlreadyRegisteredError",
    "AgentCapabilityError",
    # Policy/OPA
    "PolicyError",
    "PolicyEvaluationError",
    "PolicyNotFoundError",
    "OPAConnectionError",
    "OPANotInitializedError",
    # Deliberation
    "DeliberationError",
    "DeliberationTimeoutError",
    "SignatureCollectionError",
    "ReviewConsensusError",
    # Bus Operations
    "BusOperationError",
    "BusNotStartedError",
    "BusAlreadyStartedError",
    "HandlerExecutionError",
    # Configuration
    "ConfigurationError",
    # Constants
    "CONSTITUTIONAL_HASH",
]
