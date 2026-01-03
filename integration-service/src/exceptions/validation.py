"""
Validation exception classes for the integration-service.

Provides exceptions for validation errors including:
- Configuration validation failures
- Data validation errors
- Schema validation errors
- Field-level validation failures
"""

from typing import Any, Dict, Optional

from .base import BaseIntegrationServiceError


class ValidationError(BaseIntegrationServiceError):
    """
    Base exception for validation-related errors.

    All validation exceptions inherit from this class to enable
    catch-all validation error handling.

    Attributes:
        message: Human-readable error description
        error_code: Machine-readable error identifier
        status_code: HTTP status code (defaults to 400 Bad Request)
        details: Additional context about the validation failure

    Example:
        >>> error = ValidationError(
        ...     message="Validation failed",
        ...     error_code="VALIDATION_ERROR",
        ...     details={"field": "email", "reason": "invalid format"}
        ... )
        >>> error.status_code
        400
    """

    def __init__(
        self,
        message: str,
        error_code: str = "VALIDATION_ERROR",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize validation error.

        Args:
            message: Human-readable error description
            error_code: Machine-readable error identifier (default: "VALIDATION_ERROR")
            status_code: HTTP status code (default: 400)
            details: Additional context about the error (default: {})
        """
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class ConfigValidationError(ValidationError):
    """
    Raised when configuration validation fails.

    This error indicates that an integration or system configuration
    is invalid, missing required fields, or contains incompatible values.
    Optionally tracks the specific field that failed validation.

    Attributes:
        field: Optional name of the specific field that failed validation

    Example:
        >>> raise ConfigValidationError(
        ...     message="Invalid Splunk configuration",
        ...     field="hec_token",
        ...     details={"reason": "token must be at least 32 characters"}
        ... )
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize config validation error.

        Args:
            message: Human-readable error description
            field: Optional name of the specific field that failed validation
            details: Additional context (automatically includes field if provided)
        """
        # Store field as instance attribute for easy access
        self.field = field

        # Merge field into details if provided
        merged_details = details or {}
        if field is not None:
            merged_details["field"] = field

        super().__init__(
            message=message,
            error_code="CONFIG_VALIDATION_ERROR",
            status_code=400,
            details=merged_details,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary representation.

        Extends the base to_dict() to include the field attribute
        for backward compatibility with existing ConfigValidationError usage.

        Returns:
            Dictionary containing error information with keys:
            - error: Exception class name
            - message: Human-readable error message
            - error_code: Machine-readable error code
            - status_code: HTTP status code
            - field: Field name if set (for backward compatibility)
            - details: Additional error context
        """
        result = super().to_dict()
        # Add field to top-level for backward compatibility
        result["field"] = self.field
        return result
