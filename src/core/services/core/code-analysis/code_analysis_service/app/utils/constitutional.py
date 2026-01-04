"""
ACGS Code Analysis Engine - Constitutional Compliance Utilities
Utilities for constitutional validation and compliance checking.

Constitutional Hash: cdd01ef066bc6cf2
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# Constitutional hash constant - must match across all ACGS-2 services
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


def validate_constitutional_hash(hash_value: str) -> bool:
    """Validate that a hash matches the constitutional hash.

    Args:
        hash_value: Hash value to validate

    Returns:
        bool: True if hash matches constitutional hash
    """
    return hash_value == CONSTITUTIONAL_HASH


def ensure_constitutional_compliance(data: dict[str, Any]) -> dict[str, Any]:
    """Ensure constitutional compliance by adding hash to data.

    Args:
        data: Dictionary to add constitutional hash to

    Returns:
        dict: Data with constitutional_hash field added
    """
    data["constitutional_hash"] = CONSTITUTIONAL_HASH
    return data


def create_constitutional_metadata() -> dict[str, Any]:
    """Create metadata with constitutional compliance information.

    Returns:
        dict: Constitutional metadata including hash and timestamp
    """
    return {
        "constitutional_hash": CONSTITUTIONAL_HASH,
        "compliance_validated_at": datetime.now(timezone.utc).isoformat(),
        "service": "acgs-code-analysis-engine",
    }


def verify_constitutional_compliance(data: dict[str, Any]) -> tuple[bool, str]:
    """Verify that data is constitutionally compliant.

    Args:
        data: Data dictionary to verify

    Returns:
        tuple: (is_compliant, message)
    """
    if "constitutional_hash" not in data:
        return False, "Missing constitutional_hash field"

    if data["constitutional_hash"] != CONSTITUTIONAL_HASH:
        return False, f"Invalid constitutional hash: {data['constitutional_hash']}"

    return True, "Constitutional compliance verified"


def generate_content_hash(content: str) -> str:
    """Generate a hash for content verification.

    Args:
        content: Content to hash

    Returns:
        str: SHA-256 hash of content with constitutional prefix
    """
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"{CONSTITUTIONAL_HASH}:{content_hash}"


def log_constitutional_operation(
    operation: str,
    success: bool,
    details: dict[str, Any] | None = None,
) -> None:
    """Log a constitutional operation with compliance context.

    Args:
        operation: Name of the operation
        success: Whether operation succeeded
        details: Additional details to log
    """
    log_data = {
        "operation": operation,
        "success": success,
        "constitutional_hash": CONSTITUTIONAL_HASH,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if details:
        log_data.update(details)

    if success:
        logger.info(f"Constitutional operation: {operation}", extra=log_data)
    else:
        logger.warning(f"Constitutional operation failed: {operation}", extra=log_data)


class ConstitutionalValidator:
    """Validator for constitutional compliance checks."""

    def __init__(self):
        """Initialize constitutional validator."""
        self.hash = CONSTITUTIONAL_HASH
        self.validations_performed = 0
        self.validations_passed = 0
        self.validations_failed = 0

    def validate(self, data: dict[str, Any]) -> bool:
        """Validate data for constitutional compliance.

        Args:
            data: Data to validate

        Returns:
            bool: True if compliant
        """
        self.validations_performed += 1

        is_compliant, message = verify_constitutional_compliance(data)

        if is_compliant:
            self.validations_passed += 1
        else:
            self.validations_failed += 1
            logger.warning(f"Constitutional validation failed: {message}")

        return is_compliant

    def get_stats(self) -> dict[str, Any]:
        """Get validation statistics.

        Returns:
            dict: Validation statistics
        """
        return {
            "constitutional_hash": self.hash,
            "validations_performed": self.validations_performed,
            "validations_passed": self.validations_passed,
            "validations_failed": self.validations_failed,
            "compliance_rate": (
                self.validations_passed / self.validations_performed
                if self.validations_performed > 0
                else 1.0
            ),
        }
