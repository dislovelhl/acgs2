"""
Field validation logic for ticket mapping in ACGS-2 Integration Service.

This module provides the FieldValidator class which validates field values
against validation rules. Supports multiple validation types including required,
length constraints, regex patterns, allowed values, and numeric ranges.
"""

import re
from typing import Any, List, Optional

from .enums import FieldValidationType
from .models import FieldValidationRule


class FieldValidator:
    """Validates field values against rules."""

    @staticmethod
    def validate(
        value: Any,
        rules: List[FieldValidationRule],
        field_name: str,
    ) -> List[str]:
        """
        Validate a value against a list of rules.

        Args:
            value: The value to validate
            rules: List of validation rules
            field_name: Name of the field (for error messages)

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        for rule in rules:
            error = FieldValidator._validate_rule(value, rule, field_name)
            if error:
                errors.append(error)

        return errors

    @staticmethod
    def _validate_rule(
        value: Any,
        rule: FieldValidationRule,
        field_name: str,
    ) -> Optional[str]:
        """Validate a single rule."""
        if rule.validation_type == FieldValidationType.REQUIRED:
            if value is None or (isinstance(value, str) and not value.strip()):
                return rule.error_message or f"Field '{field_name}' is required"

        elif rule.validation_type == FieldValidationType.MAX_LENGTH:
            if value is not None and isinstance(value, str):
                max_len = int(rule.value)
                if len(value) > max_len:
                    return (
                        rule.error_message
                        or f"Field '{field_name}' exceeds maximum length of {max_len}"
                    )

        elif rule.validation_type == FieldValidationType.MIN_LENGTH:
            if value is not None and isinstance(value, str):
                min_len = int(rule.value)
                if len(value) < min_len:
                    return (
                        rule.error_message
                        or f"Field '{field_name}' is shorter than minimum length of {min_len}"
                    )

        elif rule.validation_type == FieldValidationType.REGEX:
            if value is not None and isinstance(value, str):
                pattern = str(rule.value)
                if not re.match(pattern, value):
                    return (
                        rule.error_message
                        or f"Field '{field_name}' does not match required pattern"
                    )

        elif rule.validation_type == FieldValidationType.ALLOWED_VALUES:
            if value is not None and rule.value is not None:
                allowed = rule.value if isinstance(rule.value, list) else [rule.value]
                if value not in allowed:
                    allowed_str = ", ".join(str(v) for v in allowed)
                    return (
                        rule.error_message or f"Field '{field_name}' must be one of: {allowed_str}"
                    )

        elif rule.validation_type == FieldValidationType.NUMERIC_RANGE:
            if value is not None:
                try:
                    num_value = float(value)
                    if isinstance(rule.value, dict):
                        min_val = rule.value.get("min")
                        max_val = rule.value.get("max")
                        if min_val is not None and num_value < min_val:
                            return (
                                rule.error_message or f"Field '{field_name}' must be >= {min_val}"
                            )
                        if max_val is not None and num_value > max_val:
                            return (
                                rule.error_message or f"Field '{field_name}' must be <= {max_val}"
                            )
                except (ValueError, TypeError):
                    return rule.error_message or f"Field '{field_name}' must be a valid number"

        return None


__all__ = [
    "FieldValidator",
]
