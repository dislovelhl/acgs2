"""
ACGS-2 Enhanced Agent Bus - Validators
Constitutional Hash: cdd01ef066bc6cf2

Validation utilities for message and agent compliance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Import centralized constitutional hash from shared module
try:
    from shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    # Fallback for standalone usage
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@dataclass
class ValidationResult:
    """Result of a validation operation.

    Attributes:
        is_valid (bool): Whether the validation passed. Defaults to True.
        errors (List[str]): A list of error messages if validation failed.
        warnings (List[str]): A list of warning messages.
        metadata (Dict[str, Any]): Additional metadata associated with the validation.
        constitutional_hash (str): The constitutional hash `cdd01ef066bc6cf2`.
    """
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    decision: str = "ALLOW"
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def add_error(self, error: str) -> None:
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the result."""
        self.warnings.append(warning)

    def merge(self, other: "ValidationResult") -> None:
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False

    def to_dict(self) -> Dict[str, Any]:
        """Converts the validation result to a dictionary for serialization.

        Returns:
            Dict[str, Any]: A dictionary representation of the validation result.
        """
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "metadata": self.metadata,
            "decision": self.decision,
            "constitutional_hash": self.constitutional_hash,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


def validate_constitutional_hash(hash_value: str) -> ValidationResult:
    """Validate a constitutional hash."""
    result = ValidationResult()
    if hash_value != CONSTITUTIONAL_HASH:
        result.add_error(f"Invalid constitutional hash: {hash_value}")
    return result


def validate_message_content(content: Dict[str, Any]) -> ValidationResult:
    """Validate message content."""
    result = ValidationResult()

    if not isinstance(content, dict):
        result.add_error("Content must be a dictionary")
        return result

    # Check for required fields if specified
    if "action" in content and not content["action"]:
        result.add_warning("Empty action field")

    return result


__all__ = [
    "CONSTITUTIONAL_HASH",
    "ValidationResult",
    "validate_constitutional_hash",
    "validate_message_content",
]
