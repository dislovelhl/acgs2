"""
ACGS-2 Enhanced Agent Bus - Validators
Constitutional Hash: cdd01ef066bc6cf2

Validation utilities for message and agent compliance.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


@dataclass
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def add_error(self, error: str):
        """Add an error to the result."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """Add a warning to the result."""
        self.warnings.append(warning)

    def merge(self, other: "ValidationResult"):
        """Merge another validation result into this one."""
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
        if not other.is_valid:
            self.is_valid = False


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
