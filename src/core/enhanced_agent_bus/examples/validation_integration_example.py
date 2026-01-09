"""
ACGS-2 Enhanced Agent Bus - Validation Integration Example
Constitutional Hash: cdd01ef066bc6cf2

Demonstrates integrated validation system combining standard and governance validators.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..models import CONSTITUTIONAL_HASH, AgentMessage, MessageType, Priority, ValidationStatus

# Dangerous pattern detection for security validation
DANGEROUS_PATTERNS = [
    r"<script",  # Script tag opening
    r"</script>",  # Script tag closing
    r"javascript:",  # JavaScript protocol
    r"on\w+\s*=",  # Event handlers
    r"eval\s*\(",  # Eval function
    r"document\.cookie",  # Cookie access
    r"<iframe",  # IFrame tag
]


@dataclass
class ValidationResult:
    """Result of a validation operation."""

    validator_name: str
    status: ValidationStatus = ValidationStatus.VALID
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    constitutional_hash: str = CONSTITUTIONAL_HASH
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def is_valid(self) -> bool:
        """Check if validation passed."""
        return self.status == ValidationStatus.VALID

    @classmethod
    def success(cls, validator_name: str, message: str = "Validation passed") -> "ValidationResult":
        """Create a successful validation result."""
        return cls(
            validator_name=validator_name,
            status=ValidationStatus.VALID,
            message=message,
        )

    @classmethod
    def failure(
        cls, validator_name: str, errors: List[str], message: str = "Validation failed"
    ) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(
            validator_name=validator_name,
            status=ValidationStatus.INVALID,
            errors=errors,
            message=message,
        )

    @classmethod
    def warning(
        cls,
        validator_name: str,
        warnings: List[str],
        message: str = "Validation passed with warnings",
    ) -> "ValidationResult":
        """Create a validation result with warnings."""
        return cls(
            validator_name=validator_name,
            status=ValidationStatus.VALID,
            warnings=warnings,
            message=message,
        )


class BaseValidator:
    """Base validator interface."""

    def __init__(self, fail_fast: bool = False):
        self.fail_fast = fail_fast
        self.constitutional_hash = CONSTITUTIONAL_HASH

    def validate(self, message: AgentMessage) -> ValidationResult:
        """Validate a message."""
        raise NotImplementedError


class StructureValidator(BaseValidator):
    """Validates message structure and required fields."""

    def validate(self, message: AgentMessage) -> ValidationResult:
        errors = []

        # Check required fields
        if message.payload is None:
            errors.append("Required field is None: payload")
        if message.routing is None:
            errors.append("Message requires routing configuration")
        if message.sender_id is None or message.sender_id == "":
            errors.append("Required field is empty: sender_id")

        if errors:
            return ValidationResult.failure(
                "StructureValidator", errors, "Structure validation failed"
            )
        return ValidationResult.success("StructureValidator", "Structure validation passed")


class SecurityValidator(BaseValidator):
    """Validates message security and dangerous patterns."""

    def _check_dangerous_patterns(self, value: Any) -> List[str]:
        """Recursively check value for dangerous patterns."""
        errors = []
        if isinstance(value, str):
            for pattern in DANGEROUS_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE | re.DOTALL):
                    errors.append("Dangerous pattern detected in payload")
                    if self.fail_fast:
                        return errors
        elif isinstance(value, dict):
            for v in value.values():
                errors.extend(self._check_dangerous_patterns(v))
                if self.fail_fast and errors:
                    return errors
        elif isinstance(value, list):
            for item in value:
                errors.extend(self._check_dangerous_patterns(item))
                if self.fail_fast and errors:
                    return errors
        return errors

    def validate(self, message: AgentMessage) -> ValidationResult:
        errors = []

        # Check payload for dangerous patterns
        if hasattr(message, "payload") and message.payload:
            errors.extend(self._check_dangerous_patterns(message.payload))
            if self.fail_fast and errors:
                return ValidationResult.failure(
                    "SecurityValidator", errors, "Security validation failed"
                )

        if errors:
            return ValidationResult.failure(
                "SecurityValidator", errors, "Security validation failed"
            )
        return ValidationResult.success("SecurityValidator", "Security validation passed")


class ConstitutionalHashValidator(BaseValidator):
    """Validates constitutional hash compliance."""

    def validate(self, message: AgentMessage) -> ValidationResult:
        if message.constitutional_hash != CONSTITUTIONAL_HASH:
            return ValidationResult.failure(
                "ConstitutionalHashValidator",
                [
                    f"Constitutional hash mismatch: expected {CONSTITUTIONAL_HASH}, got {message.constitutional_hash}"
                ],
                "Constitutional hash validation failed",
            )
        return ValidationResult.success("ConstitutionalHashValidator", "Constitutional hash valid")


class RoutingValidator(BaseValidator):
    """Validates message routing configuration."""

    def validate(self, message: AgentMessage) -> ValidationResult:
        if message.routing is None:
            return ValidationResult.failure(
                "RoutingValidator",
                ["Message requires routing configuration"],
                "Routing validation failed",
            )
        return ValidationResult.success("RoutingValidator", "Routing validation passed")


class PriorityValidator(BaseValidator):
    """Validates message priority with optional justification requirement."""

    def __init__(self, require_justification_for_high: bool = True, fail_fast: bool = False):
        super().__init__(fail_fast)
        self.require_justification_for_high = require_justification_for_high

    def validate(self, message: AgentMessage) -> ValidationResult:
        warnings = []

        if self.require_justification_for_high:
            if message.priority in [Priority.HIGH, Priority.CRITICAL]:
                headers = getattr(message, "headers", {}) or {}
                if "priority_justification" not in headers:
                    warnings.append("High priority message without justification")

        if warnings:
            return ValidationResult.warning(
                "PriorityValidator", warnings, "Priority validation passed with warnings"
            )
        return ValidationResult.success("PriorityValidator", "Priority validation passed")


class CompositeValidator(BaseValidator):
    """Combines multiple validators."""

    def __init__(self, validators: List[BaseValidator], fail_fast: bool = False):
        super().__init__(fail_fast)
        self.validators = validators

    def validate(self, message: AgentMessage) -> ValidationResult:
        all_errors = []
        all_warnings = []
        validator_name = "CompositeValidator"

        for validator in self.validators:
            result = validator.validate(message)
            validator_name = result.validator_name  # Use last validator's name
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

            if self.fail_fast and not result.is_valid():
                return ValidationResult.failure(
                    validator_name, all_errors, "Validation failed (fail-fast)"
                )

        if all_errors:
            return ValidationResult.failure(validator_name, all_errors, "Validation failed")

        if all_warnings:
            return ValidationResult.warning(
                validator_name, all_warnings, "Validation passed with warnings"
            )

        return ValidationResult.success(validator_name, "All validations passed")


class StandardValidator(CompositeValidator):
    """Standard validation chain for regular messages."""

    def __init__(self, fail_fast: bool = False):
        # Order: ConstitutionalHash -> Security -> Structure -> Routing
        # Security runs early to detect dangerous content before other validation
        validators = [
            ConstitutionalHashValidator(fail_fast),
            SecurityValidator(fail_fast),
            StructureValidator(fail_fast),
            RoutingValidator(fail_fast),
        ]
        super().__init__(validators, fail_fast)


class GovernanceValidator(CompositeValidator):
    """Validation chain for governance messages with stricter requirements."""

    def __init__(self, fail_fast: bool = False):
        validators = [
            ConstitutionalHashValidator(fail_fast),
            StructureValidator(fail_fast),
            SecurityValidator(fail_fast),
            RoutingValidator(fail_fast),
            PriorityValidator(require_justification_for_high=True, fail_fast=fail_fast),
        ]
        super().__init__(validators, fail_fast)


@dataclass
class ValidationHistoryEntry:
    """Entry in validation history."""

    message_id: str
    validator_name: str
    status: ValidationStatus
    timestamp: datetime
    constitutional_hash: str = CONSTITUTIONAL_HASH


class IntegratedValidationSystem:
    """
    Integrated validation system combining standard and governance validators.

    Provides:
    - Automatic validator selection based on message type
    - Validation history tracking
    - System status reporting
    - Constitutional compliance enforcement
    """

    def __init__(self, enable_governance: bool = True, fail_fast: bool = False):
        self.constitutional_hash = CONSTITUTIONAL_HASH
        self.fail_fast = fail_fast
        self.standard_validator = StandardValidator(fail_fast)
        self.governance_validator = GovernanceValidator(fail_fast) if enable_governance else None
        self.validation_history: List[ValidationHistoryEntry] = []
        self._history_limit = 100

    def validate_message(self, message: AgentMessage) -> ValidationResult:
        """
        Validate a message using the appropriate validator.

        Args:
            message: The message to validate

        Returns:
            ValidationResult indicating success or failure
        """
        # First check system integrity (constitutional hash)
        if message.constitutional_hash != self.constitutional_hash:
            result = ValidationResult.failure(
                "SystemIntegrity",
                [
                    f"Message constitutional hash {message.constitutional_hash} does not match system hash {self.constitutional_hash}"
                ],
                "System integrity check failed",
            )
            self._record_validation(message, result)
            return result

        # Select validator based on message type
        if message.message_type in [
            MessageType.GOVERNANCE_REQUEST,
            MessageType.GOVERNANCE_RESPONSE,
        ]:
            if self.governance_validator:
                result = self.governance_validator.validate(message)
                # Update validator name to indicate governance
                result.validator_name = f"Governance{result.validator_name}"
            else:
                result = self.standard_validator.validate(message)
        else:
            result = self.standard_validator.validate(message)

        self._record_validation(message, result)
        return result

    def _record_validation(self, message: AgentMessage, result: ValidationResult):
        """Record validation in history."""
        entry = ValidationHistoryEntry(
            message_id=message.message_id,
            validator_name=result.validator_name,
            status=result.status,
            timestamp=datetime.now(timezone.utc),
        )
        self.validation_history.append(entry)

        # Trim history if exceeds limit
        if len(self.validation_history) > self._history_limit:
            self.validation_history = self.validation_history[-self._history_limit :]

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        total = len(self.validation_history)
        passed = sum(1 for h in self.validation_history if h.status == ValidationStatus.VALID)
        failed = total - passed

        return {
            "constitutional_hash": self.constitutional_hash,
            "validators": {
                "standard": "enabled",
                "governance": "enabled" if self.governance_validator else "disabled",
            },
            "stats": {
                "total_validations": total,
                "passed": passed,
                "failed": failed,
                "success_rate": (passed / total * 100) if total > 0 else 0.0,
            },
            "fail_fast": self.fail_fast,
        }


def create_standard_validator(fail_fast: bool = False) -> StandardValidator:
    """Factory function to create standard validator."""
    return StandardValidator(fail_fast)


def create_governance_validator(fail_fast: bool = False) -> GovernanceValidator:
    """Factory function to create governance validator."""
    return GovernanceValidator(fail_fast)


__all__ = [
    "CONSTITUTIONAL_HASH",
    "ValidationResult",
    "BaseValidator",
    "StructureValidator",
    "SecurityValidator",
    "ConstitutionalHashValidator",
    "RoutingValidator",
    "PriorityValidator",
    "CompositeValidator",
    "StandardValidator",
    "GovernanceValidator",
    "IntegratedValidationSystem",
    "ValidationHistoryEntry",
    "create_standard_validator",
    "create_governance_validator",
]
