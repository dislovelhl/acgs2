"""
ACGS-2 Enhanced Agent Bus - Validation Strategies
Constitutional Hash: cdd01ef066bc6cf2

Validation strategy implementations for message validation.
"""

import base64
import hashlib
import logging
from typing import Any, Optional

try:
    from .imports import OPA_CLIENT_AVAILABLE, get_opa_client
    from .models import AgentMessage
except (ImportError, ValueError):
    from models import AgentMessage  # type: ignore

try:
    from .models import CONSTITUTIONAL_HASH, AgentMessage
except ImportError:
    from models import CONSTITUTIONAL_HASH, AgentMessage  # type: ignore

# PQC imports (lazy loaded for optional dependency)
try:
    from quantum_research.post_quantum_crypto import (
        ConstitutionalHashValidator,
        PQCAlgorithm,
        PQCSignature,
    )

    PQC_AVAILABLE = True
except ImportError:
    PQC_AVAILABLE = False
    PQCAlgorithm = None  # type: ignore
    PQCSignature = None  # type: ignore
    ConstitutionalHashValidator = None  # type: ignore

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

    async def validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]:
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

    async def validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]:
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

    async def validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]:
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

    SECURITY: This strategy implements fail-closed behavior by default.
    Validation only returns True when the Rust backend explicitly confirms
    the message is valid. Any error or unavailability results in rejection.
    """

    def __init__(self, rust_processor: Any, fail_closed: bool = True) -> None:
        """Initialize with Rust processor.

        Args:
            rust_processor: The Rust processor instance for validation
            fail_closed: If True, reject on any validation uncertainty (default: True)
        """
        self._rust_processor = rust_processor
        self._fail_closed = fail_closed
        self._constitutional_hash = CONSTITUTIONAL_HASH

    async def validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]:
        """Validate message using Rust backend.

        SECURITY: Implements fail-closed validation. Only returns True when
        the Rust backend explicitly confirms validation success.
        """
        if not self._rust_processor:
            return False, "Rust processor not available"

        try:
            # Attempt to use Rust processor's validation method
            # Check for validate_message method (preferred)
            if hasattr(self._rust_processor, "validate_message"):
                result = await self._rust_processor.validate_message(message.to_dict())
                if isinstance(result, bool):
                    if result:
                        return True, None
                    return False, "Rust validation rejected message"
                elif isinstance(result, dict):
                    is_valid = result.get("is_valid", False)
                    if is_valid:
                        return True, None
                    error = result.get("error", "Rust validation failed")
                    return False, error

            # Check for synchronous validate method
            if hasattr(self._rust_processor, "validate"):
                result = self._rust_processor.validate(message.to_dict())
                if isinstance(result, bool):
                    if result:
                        return True, None
                    return False, "Rust validation rejected message"
                elif isinstance(result, dict):
                    is_valid = result.get("is_valid", False)
                    if is_valid:
                        return True, None
                    error = result.get("error", "Rust validation failed")
                    return False, error

            # Check for constitutional_validate method
            if hasattr(self._rust_processor, "constitutional_validate"):
                result = self._rust_processor.constitutional_validate(
                    message.constitutional_hash, self._constitutional_hash
                )
                if result:
                    return True, None
                return False, "Constitutional hash validation failed in Rust backend"

            # SECURITY: No validation method available - fail closed
            logger.warning(
                "RustValidationStrategy: No validation method found on Rust processor. "
                "Failing closed for security."
            )
            return False, "Rust processor has no validation method - fail closed"

        except Exception as e:
            logger.error(f"Rust validation execution error: {e}")
            # SECURITY: Always fail closed on exceptions
            return False, f"Rust validation error: {str(e)}"


class PQCValidationStrategy:
    """
    Post-Quantum Cryptographic Validation Strategy.

    Validates messages using NIST-approved post-quantum algorithms
    (CRYSTALS-Kyber and CRYSTALS-Dilithium) for quantum-resistant
    constitutional hash validation.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, validator: Any = None, hybrid_mode: bool = True) -> None:
        """
        Initialize PQC validation strategy.

        Args:
            validator: ConstitutionalHashValidator instance
            hybrid_mode: Allow fallback to static hash if PQC fails
        """
        self._hybrid_mode = hybrid_mode
        self._constitutional_hash = CONSTITUTIONAL_HASH

        # Initialize PQC validator
        if validator is not None:
            self._validator = validator
        else:
            # Lazy import to avoid circular dependencies
            try:
                from quantum_research.post_quantum_crypto import (
                    ConstitutionalHashValidator,
                    PQCAlgorithm,
                    PQCSignature,
                )

                self._validator = ConstitutionalHashValidator()
                self._PQCSignature = PQCSignature
                self._PQCAlgorithm = PQCAlgorithm
            except ImportError:
                logger.warning("Post-quantum crypto not available, PQC validation disabled")
                self._validator = None
                self._PQCSignature = None
                self._PQCAlgorithm = None

    async def validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]:
        """
        Validate message using post-quantum cryptography.

        Algorithm:
        1. Check if message has PQC signature
        2. If PQC signature present, validate it
        3. If no PQC signature and hybrid mode enabled, fall back to static hash
        4. If no PQC signature and hybrid mode disabled, reject

        Returns:
            Tuple of (is_valid, error_message)
        """
        # If PQC validator is not available, fall back to static hash in hybrid mode
        if not self._validator:
            if self._hybrid_mode:
                # Fall back to static hash validation when PQC is unavailable
                if message.constitutional_hash != self._constitutional_hash:
                    return (
                        False,
                        f"Constitutional hash mismatch: expected {self._constitutional_hash}",
                    )
                return True, None
            return False, "PQC validator not available"

        # Check if message has PQC signature
        if not message.pqc_signature:
            if self._hybrid_mode:
                # Fall back to static hash validation
                if message.constitutional_hash != self._constitutional_hash:
                    return (
                        False,
                        f"Constitutional hash mismatch: expected {self._constitutional_hash}",
                    )
                return True, None
            else:
                return False, "PQC signature required but not provided"

        # Validate PQC signature
        try:
            # Convert base64 signature and public key back to bytes for validation
            import base64

            signature_bytes = base64.b64decode(message.pqc_signature)

            # Create decision dict for validation
            decision = {
                "message_id": message.message_id,
                "content": message.content,
                "from_agent": message.from_agent,
                "tenant_id": message.tenant_id,
                "timestamp": message.created_at.isoformat(),
                "constitutional_hash": message.constitutional_hash,
            }

            # Parse public key (expecting base64 encoded bytes)
            if not message.pqc_public_key:
                return False, "PQC public key is required for signature verification"

            try:
                public_key_bytes = base64.b64decode(message.pqc_public_key)
            except Exception as e:
                # Try hex decoding as fallback
                try:
                    public_key_bytes = bytes.fromhex(message.pqc_public_key)
                except Exception:
                    return False, f"Invalid PQC public key format: {str(e)}"

            # Create PQCSignature object for validation
            if self._PQCSignature is None or self._PQCAlgorithm is None:
                return False, "PQC classes not available"

            signature_obj = self._PQCSignature(
                algorithm=self._PQCAlgorithm.DILITHIUM_3,
                signature=signature_bytes,
                message_hash=hashlib.sha3_256(str(decision).encode()).digest(),
                signer_key_id=f"pqc-{message.message_id[:16]}",
            )

            # Validate the signature
            is_valid = self._validator.verify_governance_decision(
                decision=decision, signature=signature_obj, public_key=public_key_bytes
            )

            if is_valid:
                return True, None
            else:
                return False, "PQC signature verification failed"

        except Exception as e:
            logger.error(f"PQC validation error: {e}")
            if self._hybrid_mode:
                # Fall back to static hash in case of PQC errors
                if message.constitutional_hash == self._constitutional_hash:
                    return True, None
            return False, f"PQC validation error: {str(e)}"


class CompositeValidationStrategy:
    """
    Combines multiple validation strategies with intelligent orchestration.

    Features:
    - Runs all strategies and aggregates results
    - Prioritizes PQC validation when available
    - Falls back gracefully on validation failures
    - Supports hybrid classical/PQC modes

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, strategies: Optional[list] = None, enable_pqc: bool = True) -> None:
        """
        Initialize with list of validation strategies.

        Args:
            strategies: List of validation strategies to use
            enable_pqc: Whether to automatically include PQC validation
        """
        self._strategies: list = strategies or []
        self._constitutional_hash = CONSTITUTIONAL_HASH
        self._enable_pqc = enable_pqc

        # Auto-include PQC validation if enabled and not already present
        if enable_pqc and not any(isinstance(s, PQCValidationStrategy) for s in self._strategies):
            try:
                pqc_strategy = PQCValidationStrategy(hybrid_mode=True)
                self._strategies.append(pqc_strategy)
                logger.info("PQC validation strategy auto-enabled in composite validation")
            except Exception as e:
                logger.warning(f"Failed to initialize PQC validation strategy: {e}")

    def add_strategy(self, strategy: Any) -> None:
        """Add a validation strategy."""
        self._strategies.append(strategy)

    async def validate(self, message: AgentMessage) -> tuple[bool, Optional[str]]:
        """
        Run all validation strategies with intelligent orchestration.

        Algorithm:
        1. If PQC signature present, prioritize PQC validation
        2. Run all strategies and collect results
        3. Require ALL strategies to pass (fail-closed security)
        4. Aggregate error messages for debugging

        Returns:
            Tuple of (is_valid, error_message)
        """
        errors = []
        pqc_validated = False

        # Prioritize PQC validation if signature is present
        for strategy in self._strategies:
            if isinstance(strategy, PQCValidationStrategy) and message.pqc_signature:
                is_valid, error = await strategy.validate(message)
                if not is_valid:
                    errors.append(f"PQC: {error}")
                else:
                    pqc_validated = True
                continue

        # Run remaining strategies
        for strategy in self._strategies:
            if isinstance(strategy, PQCValidationStrategy) and message.pqc_signature:
                continue  # Already handled above

            is_valid, error = await strategy.validate(message)
            if not is_valid and error:
                strategy_name = strategy.__class__.__name__.replace("ValidationStrategy", "")
                errors.append(f"{strategy_name}: {error}")

        if errors:
            return False, "; ".join(errors)

        return True, None


__all__ = [
    "StaticHashValidationStrategy",
    "DynamicPolicyValidationStrategy",
    "OPAValidationStrategy",
    "RustValidationStrategy",
    "PQCValidationStrategy",
    "CompositeValidationStrategy",
]
