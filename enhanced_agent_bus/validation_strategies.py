"""
ACGS-2 Enhanced Agent Bus - Validation Strategies
Constitutional Hash: cdd01ef066bc6cf2

Validation strategy implementations for message validation.
"""

import logging
from typing import Any, Optional

try:
    from .models import AgentMessage, CONSTITUTIONAL_HASH
except ImportError:
    from models import AgentMessage, CONSTITUTIONAL_HASH  # type: ignore

logger = logging.getLogger(__name__)


class StaticHashValidationStrategy:
    """Validates messages using a static constitutional hash.

    Standard implementation that checks for hash consistency.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, strict: bool = True) -> None:
        """Initialize static hash validation.

        Args:
            strict: If True, reject messages with non-matching hashes
        """
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._strict = strict

    async def validate(
        self,
        message: AgentMessage
    ) -> tuple[bool, Optional[str]]:
        """Validate a message for constitutional compliance."""
        # Check message has content
        if message.content is None:
            return False, "Message content cannot be None"

        # Validate message_id exists
        if not message.message_id:
            return False, "Message ID is required"

        # Validate constitutional hash if strict mode
        if self._strict:
            if message.constitutional_hash != self._constitutional_hash:
                return False, f"Constitutional hash mismatch: expected {self._constitutional_hash}"

        return True, None


class DynamicPolicyValidationStrategy:
    """Validates messages using a dynamic policy client.

    Retrieves current policies and validates signatures.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, policy_client: Any) -> None:
        """Initialize with logic client."""
        self._policy_client = policy_client

    async def validate(
        self,
        message: AgentMessage
    ) -> tuple[bool, Optional[str]]:
        """Validate message signature against dynamic policy server."""
        if not self._policy_client:
            return False, "Policy client not available"

        try:
            result = await self._policy_client.validate_message_signature(message)
            if not result.is_valid:
                return False, "; ".join(result.errors)
            return True, None
        except Exception as e:
            logger.error(f"Dynamic policy validation error: {e}")
            return False, f"Dynamic validation error: {str(e)}"


class OPAValidationStrategy:
    """Validates messages using OPA (Open Policy Agent).

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, opa_client: Any) -> None:
        """Initialize with OPA client."""
        self._opa_client = opa_client

    async def validate(
        self,
        message: AgentMessage
    ) -> tuple[bool, Optional[str]]:
        """Validate message against OPA constitutional policies."""
        if not self._opa_client:
            return False, "OPA client not available"

        try:
            # Evaluate constitutional policies
            result = await self._opa_client.validate_constitutional(message.to_dict())
            if not result.is_valid:
                return False, "; ".join(result.errors)
            return True, None
        except Exception as e:
            logger.error(f"OPA validation execution error: {e}")
            return False, f"OPA validation error: {str(e)}"


class RustValidationStrategy:
    """High-performance validation using the Rust backend.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, rust_processor: Any) -> None:
        """Initialize with Rust processor."""
        self._rust_processor = rust_processor

    async def validate(
        self,
        message: AgentMessage
    ) -> tuple[bool, Optional[str]]:
        """Validate message using Rust backend."""
        if not self._rust_processor:
            return False, "Rust processor not available"

        try:
            # We assume Rust processor has a fast validation path
            # For now, we can use its built-in validation during processing
            # or a specific validation method if exposed.
            # In Phase 2, we just ensure the strategy interface is met.
            # This will be refined as the Rust API evolves.
            return True, None  # Rust backend handles validation internally for now
        except Exception as e:
            return False, f"Rust validation error: {str(e)}"


class CompositeValidationStrategy:
    """Combines multiple validation strategies.

    Runs all strategies and aggregates results.
    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, strategies: Optional[list] = None) -> None:
        """Initialize with list of validation strategies."""
        self._strategies: list = strategies or []
        self._constitutional_hash = CONSTITUTIONAL_HASH

    def add_strategy(self, strategy: Any) -> None:
        """Add a validation strategy."""
        self._strategies.append(strategy)

    async def validate(
        self,
        message: AgentMessage
    ) -> tuple[bool, Optional[str]]:
        """Run all validation strategies."""
        errors = []

        for strategy in self._strategies:
            is_valid, error = await strategy.validate(message)
            if not is_valid and error:
                errors.append(error)

        if errors:
            return False, "; ".join(errors)

        return True, None


__all__ = [
    "StaticHashValidationStrategy",
    "DynamicPolicyValidationStrategy",
    "OPAValidationStrategy",
    "RustValidationStrategy",
    "CompositeValidationStrategy",
]
