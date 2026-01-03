"""
Ticket mapping Pydantic models for ACGS-2 Integration Service.

This module defines the data models used for ticket field mapping configuration,
validation rules, severity mappings, and mapping results. These models provide
type safety and validation for the ticket mapping framework.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..base import EventSeverity
from .enums import FieldMappingType, FieldValidationType, TicketingProvider


class FieldValidationRule(BaseModel):
    """Validation rule for a ticket field."""

    validation_type: FieldValidationType = Field(..., description="Type of validation to perform")
    value: Optional[Any] = Field(
        None, description="Value for the validation (e.g., max length, regex pattern)"
    )
    error_message: Optional[str] = Field(
        None, description="Custom error message for validation failure"
    )

    model_config = ConfigDict(frozen=True)


class FieldMapping(BaseModel):
    """Configuration for mapping a single field."""

    target_field: str = Field(..., description="Name of the target field in the ticketing system")
    mapping_type: FieldMappingType = Field(
        default=FieldMappingType.STATIC,
        description="How the field value should be determined",
    )

    # Value configuration based on mapping type
    static_value: Optional[Any] = Field(None, description="Static value to use (for STATIC type)")
    template: Optional[str] = Field(
        None,
        description="Template string with {placeholders} (for TEMPLATE type)",
    )
    source_field: Optional[str] = Field(
        None, description="Event field to map from (for EVENT_FIELD type)"
    )
    transform_name: Optional[str] = Field(
        None, description="Name of the transform function (for TRANSFORM type)"
    )
    transform_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the transform function",
    )

    # Conditional mapping
    conditions: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Conditions for CONDITIONAL mapping [{field, operator, value, result}]",
    )
    default_value: Optional[Any] = Field(None, description="Default value if no condition matches")

    # Validation
    validation_rules: List[FieldValidationRule] = Field(
        default_factory=list, description="Validation rules for this field"
    )
    required: bool = Field(default=False, description="Whether this field is required")

    # Metadata
    description: Optional[str] = Field(None, description="Description of this field mapping")
    provider_specific: Dict[str, Any] = Field(
        default_factory=dict,
        description="Provider-specific configuration",
    )

    model_config = ConfigDict(validate_assignment=True)

    @model_validator(mode="after")
    def validate_mapping_config(self) -> "FieldMapping":
        """Validate that appropriate values are provided for the mapping type."""
        if self.mapping_type == FieldMappingType.STATIC:
            if self.static_value is None:
                raise ValueError("static_value is required for STATIC mapping type")
        elif self.mapping_type == FieldMappingType.TEMPLATE:
            if not self.template:
                raise ValueError("template is required for TEMPLATE mapping type")
        elif self.mapping_type == FieldMappingType.EVENT_FIELD:
            if not self.source_field:
                raise ValueError("source_field is required for EVENT_FIELD mapping type")
        elif self.mapping_type == FieldMappingType.TRANSFORM:
            if not self.transform_name:
                raise ValueError("transform_name is required for TRANSFORM mapping type")
        elif self.mapping_type == FieldMappingType.CONDITIONAL:
            if not self.conditions:
                raise ValueError("conditions are required for CONDITIONAL mapping type")
        return self


class SeverityMapping(BaseModel):
    """Mapping configuration for severity to priority/impact/urgency."""

    critical: str = Field(..., description="Value for CRITICAL severity")
    high: str = Field(..., description="Value for HIGH severity")
    medium: str = Field(..., description="Value for MEDIUM severity")
    low: str = Field(..., description="Value for LOW severity")
    info: str = Field(..., description="Value for INFO severity")

    model_config = ConfigDict(frozen=True)

    def get_value(self, severity: EventSeverity) -> str:
        """Get the mapped value for a severity level."""
        mapping = {
            EventSeverity.CRITICAL: self.critical,
            EventSeverity.HIGH: self.high,
            EventSeverity.MEDIUM: self.medium,
            EventSeverity.LOW: self.low,
            EventSeverity.INFO: self.info,
        }
        return mapping.get(severity, self.medium)


class TicketMappingConfig(BaseModel):
    """Complete ticket field mapping configuration."""

    id: str = Field(
        default="",
        description="Unique identifier for this mapping configuration",
    )
    name: str = Field(..., description="Name of this mapping configuration")
    provider: TicketingProvider = Field(
        ..., description="Ticketing provider this configuration is for"
    )
    description: Optional[str] = Field(
        None, description="Description of this mapping configuration"
    )

    # Field mappings
    field_mappings: List[FieldMapping] = Field(
        default_factory=list,
        description="List of field mappings to apply",
    )

    # Priority/Impact/Urgency mappings
    severity_mapping: Optional[SeverityMapping] = Field(
        None, description="Custom severity to priority/impact mapping"
    )

    # Template settings
    summary_template: str = Field(
        default="[ACGS-2] {title}",
        description="Template for ticket summary/short description",
    )
    description_template: Optional[str] = Field(
        None, description="Template for ticket description (if not using default)"
    )

    # Provider-specific settings
    jira_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Jira-specific settings (e.g., project_key, issue_type)",
    )
    servicenow_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="ServiceNow-specific settings (e.g., category, subcategory)",
    )

    # Metadata
    enabled: bool = Field(default=True, description="Whether this mapping is enabled")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp",
    )

    model_config = ConfigDict(validate_assignment=True)

    def get_field_mapping(self, target_field: str) -> Optional[FieldMapping]:
        """Get the mapping for a specific target field."""
        for mapping in self.field_mappings:
            if mapping.target_field == target_field:
                return mapping
        return None


class FieldMappingResult(BaseModel):
    """Result of applying a field mapping."""

    field_name: str = Field(..., description="Name of the mapped field")
    value: Any = Field(..., description="Computed value for the field")
    success: bool = Field(default=True, description="Whether mapping succeeded")
    error_message: Optional[str] = Field(None, description="Error message if mapping failed")
    validation_errors: List[str] = Field(
        default_factory=list, description="List of validation errors"
    )

    model_config = ConfigDict(validate_assignment=True)


class TicketMappingResult(BaseModel):
    """Result of applying all field mappings for a ticket."""

    success: bool = Field(default=True, description="Whether all required mappings succeeded")
    fields: Dict[str, Any] = Field(default_factory=dict, description="Mapped field values")
    field_results: List[FieldMappingResult] = Field(
        default_factory=list, description="Individual field mapping results"
    )
    validation_errors: List[str] = Field(
        default_factory=list, description="Overall validation errors"
    )
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")

    model_config = ConfigDict(validate_assignment=True)


__all__ = [
    "FieldValidationRule",
    "FieldMapping",
    "SeverityMapping",
    "TicketMappingConfig",
    "FieldMappingResult",
    "TicketMappingResult",
]
