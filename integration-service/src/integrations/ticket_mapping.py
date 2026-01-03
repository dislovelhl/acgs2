"""
Ticket Field Mapping Configuration and Validation

Provides a comprehensive framework for mapping governance events to ticketing
system fields (Jira, ServiceNow). Supports template-based field values,
severity/priority mapping, custom field transformations, and validation.

Features:
- Template-based field value generation using event data
- Severity to priority/impact/urgency mapping
- Custom field transformations
- Field validation for ticketing system requirements
- Reusable mapping configurations for Jira and ServiceNow
"""

import logging
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..types import ConfigDict as ConfigDictType
from ..types import JSONDict, JSONValue
from .base import EventSeverity, IntegrationEvent

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================


class TicketingProvider(str, Enum):
    """Supported ticketing providers."""

    JIRA = "jira"
    SERVICENOW = "servicenow"


class FieldMappingType(str, Enum):
    """Types of field mapping."""

    STATIC = "static"  # Fixed value
    TEMPLATE = "template"  # Template with placeholders
    EVENT_FIELD = "event_field"  # Direct mapping from event field
    TRANSFORM = "transform"  # Transform using a function
    CONDITIONAL = "conditional"  # Conditional based on event data


class FieldValidationType(str, Enum):
    """Types of field validation."""

    REQUIRED = "required"
    MAX_LENGTH = "max_length"
    MIN_LENGTH = "min_length"
    REGEX = "regex"
    ALLOWED_VALUES = "allowed_values"
    NUMERIC_RANGE = "numeric_range"
    DATE_FORMAT = "date_format"


class JiraPriority(str, Enum):
    """Standard Jira priority levels."""

    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"


class ServiceNowImpactUrgency(str, Enum):
    """ServiceNow impact/urgency values."""

    HIGH = "1"
    MEDIUM = "2"
    LOW = "3"


# ============================================================================
# Default Mappings
# ============================================================================


# Severity to Jira Priority mapping
DEFAULT_JIRA_PRIORITY_MAP: Dict[EventSeverity, JiraPriority] = {
    EventSeverity.CRITICAL: JiraPriority.HIGHEST,
    EventSeverity.HIGH: JiraPriority.HIGH,
    EventSeverity.MEDIUM: JiraPriority.MEDIUM,
    EventSeverity.LOW: JiraPriority.LOW,
    EventSeverity.INFO: JiraPriority.LOWEST,
}

# Severity to ServiceNow Impact mapping
DEFAULT_SERVICENOW_IMPACT_MAP: Dict[EventSeverity, ServiceNowImpactUrgency] = {
    EventSeverity.CRITICAL: ServiceNowImpactUrgency.HIGH,
    EventSeverity.HIGH: ServiceNowImpactUrgency.HIGH,
    EventSeverity.MEDIUM: ServiceNowImpactUrgency.MEDIUM,
    EventSeverity.LOW: ServiceNowImpactUrgency.LOW,
    EventSeverity.INFO: ServiceNowImpactUrgency.LOW,
}

# Severity to ServiceNow Urgency mapping
DEFAULT_SERVICENOW_URGENCY_MAP: Dict[EventSeverity, ServiceNowImpactUrgency] = {
    EventSeverity.CRITICAL: ServiceNowImpactUrgency.HIGH,
    EventSeverity.HIGH: ServiceNowImpactUrgency.MEDIUM,
    EventSeverity.MEDIUM: ServiceNowImpactUrgency.MEDIUM,
    EventSeverity.LOW: ServiceNowImpactUrgency.LOW,
    EventSeverity.INFO: ServiceNowImpactUrgency.LOW,
}


# ============================================================================
# Pydantic Models
# ============================================================================


class FieldValidationRule(BaseModel):
    """Validation rule for a ticket field."""

    validation_type: FieldValidationType = Field(..., description="Type of validation to perform")
    value: Optional[JSONValue] = Field(
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
    static_value: Optional[JSONValue] = Field(
        None, description="Static value to use (for STATIC type)"
    )
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
    transform_params: Dict[str, JSONValue] = Field(
        default_factory=dict,
        description="Parameters for the transform function",
    )

    # Conditional mapping
    conditions: List[JSONDict] = Field(
        default_factory=list,
        description="Conditions for CONDITIONAL mapping [{field, operator, value, result}]",
    )
    default_value: Optional[JSONValue] = Field(
        None, description="Default value if no condition matches"
    )

    # Validation
    validation_rules: List[FieldValidationRule] = Field(
        default_factory=list, description="Validation rules for this field"
    )
    required: bool = Field(default=False, description="Whether this field is required")

    # Metadata
    description: Optional[str] = Field(None, description="Description of this field mapping")
    provider_specific: JSONDict = Field(
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
    jira_settings: ConfigDictType = Field(
        default_factory=dict,
        description="Jira-specific settings (e.g., project_key, issue_type)",
    )
    servicenow_settings: ConfigDictType = Field(
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
    value: Optional[JSONValue] = Field(None, description="Computed value for the field")
    success: bool = Field(default=True, description="Whether mapping succeeded")
    error_message: Optional[str] = Field(None, description="Error message if mapping failed")
    validation_errors: List[str] = Field(
        default_factory=list, description="List of validation errors"
    )

    model_config = ConfigDict(validate_assignment=True)


class TicketMappingResult(BaseModel):
    """Result of applying all field mappings for a ticket."""

    success: bool = Field(default=True, description="Whether all required mappings succeeded")
    fields: Dict[str, JSONValue] = Field(default_factory=dict, description="Mapped field values")
    field_results: List[FieldMappingResult] = Field(
        default_factory=list, description="Individual field mapping results"
    )
    validation_errors: List[str] = Field(
        default_factory=list, description="Overall validation errors"
    )
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")

    model_config = ConfigDict(validate_assignment=True)


# ============================================================================
# Field Validators
# ============================================================================


class FieldValidator:
    """Validates field values against rules."""

    @staticmethod
    def validate(
        value: JSONValue,
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
        value: JSONValue,
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


# ============================================================================
# Field Transformers
# ============================================================================


# Type for transform functions
TransformFunc = Callable[[IntegrationEvent, Dict[str, JSONValue]], JSONValue]


class FieldTransformers:
    """Collection of built-in field transformer functions."""

    _registry: Dict[str, TransformFunc] = {}

    @classmethod
    def register(cls, name: str) -> Callable[[TransformFunc], TransformFunc]:
        """Decorator to register a transform function."""

        def decorator(func: TransformFunc) -> TransformFunc:
            cls._registry[name] = func
            return func

        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[TransformFunc]:
        """Get a registered transform function by name."""
        return cls._registry.get(name)

    @classmethod
    def list_transforms(cls) -> List[str]:
        """List all registered transform names."""
        return list(cls._registry.keys())


# Built-in transforms
@FieldTransformers.register("severity_to_jira_priority")
def severity_to_jira_priority(event: IntegrationEvent, params: Dict[str, JSONValue]) -> str:
    """Convert event severity to Jira priority name."""
    custom_map = params.get("mapping", {})
    if custom_map and event.severity.value in custom_map:
        return str(custom_map[event.severity.value])
    return DEFAULT_JIRA_PRIORITY_MAP.get(event.severity, JiraPriority.MEDIUM).value


@FieldTransformers.register("severity_to_servicenow_impact")
def severity_to_servicenow_impact(event: IntegrationEvent, params: Dict[str, JSONValue]) -> str:
    """Convert event severity to ServiceNow impact value."""
    custom_map = params.get("mapping", {})
    if custom_map and event.severity.value in custom_map:
        return str(custom_map[event.severity.value])
    return DEFAULT_SERVICENOW_IMPACT_MAP.get(event.severity, ServiceNowImpactUrgency.MEDIUM).value


@FieldTransformers.register("severity_to_servicenow_urgency")
def severity_to_servicenow_urgency(event: IntegrationEvent, params: Dict[str, JSONValue]) -> str:
    """Convert event severity to ServiceNow urgency value."""
    custom_map = params.get("mapping", {})
    if custom_map and event.severity.value in custom_map:
        return str(custom_map[event.severity.value])
    return DEFAULT_SERVICENOW_URGENCY_MAP.get(event.severity, ServiceNowImpactUrgency.MEDIUM).value


@FieldTransformers.register("format_timestamp")
def format_timestamp(event: IntegrationEvent, params: Dict[str, JSONValue]) -> str:
    """Format event timestamp to a specific format."""
    fmt = params.get("format", "%Y-%m-%d %H:%M:%S")
    return event.timestamp.strftime(str(fmt))


@FieldTransformers.register("format_tags")
def format_tags(event: IntegrationEvent, params: Dict[str, JSONValue]) -> str:
    """Format event tags as a string."""
    separator = params.get("separator", ", ")
    return str(separator).join(event.tags)


@FieldTransformers.register("build_labels")
def build_labels(event: IntegrationEvent, params: Dict[str, JSONValue]) -> List[str]:
    """Build a list of labels from event data."""
    base_labels_param = params.get("base_labels", ["governance", "acgs2"])
    # Ensure base_labels is a list
    if isinstance(base_labels_param, list):
        base_labels = [str(label) for label in base_labels_param]
    else:
        base_labels = ["governance", "acgs2"]

    labels = list(base_labels)

    if params.get("include_severity", True):
        labels.append(f"severity-{event.severity.value}")

    if params.get("include_event_type", True) and event.event_type:
        labels.append(event.event_type.replace("_", "-").replace(" ", "-").lower())

    if params.get("include_tags", False):
        labels.extend(event.tags)

    return labels


@FieldTransformers.register("truncate")
def truncate(event: IntegrationEvent, params: Dict[str, JSONValue]) -> str:
    """Truncate a field value to max length."""
    source_field = params.get("source_field", "title")
    max_length_param = params.get("max_length", 255)
    max_length = int(max_length_param) if isinstance(max_length_param, (int, float, str)) else 255
    suffix = params.get("suffix", "...")

    value = getattr(event, str(source_field), "") or ""
    if len(value) > max_length:
        return value[: max_length - len(str(suffix))] + str(suffix)
    return value


@FieldTransformers.register("json_details")
def json_details(event: IntegrationEvent, params: Dict[str, JSONValue]) -> str:
    """Format event details as JSON string."""
    import json

    indent_param = params.get("indent", 2)
    indent = int(indent_param) if isinstance(indent_param, (int, float, str)) else 2
    include_fields = params.get("include_fields", None)

    if include_fields and isinstance(include_fields, list):
        details = {k: v for k, v in event.details.items() if k in include_fields}
    else:
        details = event.details

    return json.dumps(details, indent=indent, default=str)


@FieldTransformers.register("concatenate")
def concatenate(event: IntegrationEvent, params: Dict[str, JSONValue]) -> str:
    """Concatenate multiple event fields."""
    fields_param = params.get("fields", [])
    fields = fields_param if isinstance(fields_param, list) else []
    separator = params.get("separator", " ")

    values = []
    for field in fields:
        value = getattr(event, str(field), None)
        if value is not None:
            values.append(str(value))

    return str(separator).join(values)


@FieldTransformers.register("map_value")
def map_value(event: IntegrationEvent, params: Dict[str, JSONValue]) -> JSONValue:
    """Map a field value using a lookup table."""
    source_field = params.get("source_field", "")
    mapping_param = params.get("mapping", {})
    mapping = mapping_param if isinstance(mapping_param, dict) else {}
    default = params.get("default", None)

    value = getattr(event, str(source_field), None)
    if value is not None and isinstance(mapping, dict):
        return mapping.get(str(value), default)
    return default


# ============================================================================
# Ticket Field Mapper
# ============================================================================


class TicketFieldMapper:
    """
    Maps governance events to ticket fields using configurable mappings.

    Supports template-based field generation, severity mapping, custom
    transformations, and field validation.

    Usage:
        mapper = TicketFieldMapper(config)
        result = mapper.map_event(event)
        if result.success:
            fields = result.fields
    """

    # Template placeholder pattern
    TEMPLATE_PATTERN = re.compile(r"\{(\w+(?:\.\w+)*)\}")

    def __init__(self, config: TicketMappingConfig):
        """
        Initialize the mapper with a configuration.

        Args:
            config: Ticket mapping configuration
        """
        self.config = config
        self._custom_transforms: Dict[str, TransformFunc] = {}

    @property
    def provider(self) -> TicketingProvider:
        """Get the ticketing provider for this mapper."""
        return self.config.provider

    def register_transform(self, name: str, func: TransformFunc) -> None:
        """
        Register a custom transform function.

        Args:
            name: Name of the transform
            func: Transform function (event, params) -> value
        """
        self._custom_transforms[name] = func

    def map_event(self, event: IntegrationEvent) -> TicketMappingResult:
        """
        Map an event to ticket fields using the configured mappings.

        Args:
            event: The governance event to map

        Returns:
            TicketMappingResult with mapped fields and any errors
        """
        result = TicketMappingResult()
        all_errors = []

        # Process each field mapping
        for mapping in self.config.field_mappings:
            field_result = self._map_field(event, mapping)
            result.field_results.append(field_result)

            if field_result.success:
                result.fields[field_result.field_name] = field_result.value
            else:
                if mapping.required:
                    all_errors.append(
                        f"Required field '{mapping.target_field}' mapping failed: "
                        f"{field_result.error_message}"
                    )
                else:
                    result.warnings.append(
                        f"Optional field '{mapping.target_field}' mapping failed: "
                        f"{field_result.error_message}"
                    )

            # Add validation errors
            if field_result.validation_errors:
                if mapping.required:
                    all_errors.extend(field_result.validation_errors)
                else:
                    result.warnings.extend(field_result.validation_errors)

        result.validation_errors = all_errors
        result.success = len(all_errors) == 0

        return result

    def _map_field(self, event: IntegrationEvent, mapping: FieldMapping) -> FieldMappingResult:
        """Map a single field."""
        try:
            value = self._compute_value(event, mapping)

            # Validate the computed value
            validation_errors = FieldValidator.validate(
                value, mapping.validation_rules, mapping.target_field
            )

            # Check required
            if mapping.required and (value is None or value == ""):
                validation_errors.append(
                    f"Field '{mapping.target_field}' is required but has no value"
                )

            return FieldMappingResult(
                field_name=mapping.target_field,
                value=value,
                success=len(validation_errors) == 0,
                validation_errors=validation_errors,
            )

        except Exception as e:
            logger.warning(f"Error mapping field '{mapping.target_field}': {str(e)}")
            return FieldMappingResult(
                field_name=mapping.target_field,
                value=None,
                success=False,
                error_message=str(e),
            )

    def _compute_value(self, event: IntegrationEvent, mapping: FieldMapping) -> JSONValue:
        """Compute the field value based on mapping type."""
        if mapping.mapping_type == FieldMappingType.STATIC:
            return mapping.static_value

        elif mapping.mapping_type == FieldMappingType.TEMPLATE:
            return self._apply_template(event, mapping.template or "")

        elif mapping.mapping_type == FieldMappingType.EVENT_FIELD:
            return self._get_event_field(event, mapping.source_field or "")

        elif mapping.mapping_type == FieldMappingType.TRANSFORM:
            return self._apply_transform(
                event, mapping.transform_name or "", mapping.transform_params
            )

        elif mapping.mapping_type == FieldMappingType.CONDITIONAL:
            return self._apply_conditional(event, mapping.conditions, mapping.default_value)

        return None

    def _apply_template(self, event: IntegrationEvent, template: str) -> str:
        """
        Apply a template with event field placeholders.

        Supports placeholders like {title}, {severity}, {details.key}, etc.

        Args:
            event: The event to get values from
            template: Template string with {placeholders}

        Returns:
            Rendered template string
        """

        def replace_placeholder(match: re.Match) -> str:
            path = match.group(1)
            value = self._get_event_field(event, path)
            return str(value) if value is not None else ""

        return self.TEMPLATE_PATTERN.sub(replace_placeholder, template)

    def _get_event_field(self, event: IntegrationEvent, field_path: str) -> JSONValue:
        """
        Get a field value from an event, supporting nested paths.

        Args:
            event: The event to get value from
            field_path: Field path (e.g., "title", "details.key")

        Returns:
            Field value or None if not found
        """
        parts = field_path.split(".")
        value: Union[IntegrationEvent, JSONValue] = event

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None

        # Ensure we return a JSONValue type
        if isinstance(value, (str, int, float, bool, dict, list, type(None))):
            return value  # type: ignore[return-value]
        return str(value)

    def _apply_transform(
        self,
        event: IntegrationEvent,
        transform_name: str,
        params: Dict[str, JSONValue],
    ) -> JSONValue:
        """
        Apply a transform function to compute a field value.

        Args:
            event: The event to transform
            transform_name: Name of the transform function
            params: Parameters for the transform

        Returns:
            Transformed value
        """
        # Check custom transforms first
        if transform_name in self._custom_transforms:
            return self._custom_transforms[transform_name](event, params)

        # Check built-in transforms
        transform_func = FieldTransformers.get(transform_name)
        if transform_func:
            return transform_func(event, params)

        raise ValueError(f"Unknown transform: {transform_name}")

    def _apply_conditional(
        self,
        event: IntegrationEvent,
        conditions: List[JSONDict],
        default: JSONValue,
    ) -> JSONValue:
        """
        Apply conditional logic to determine field value.

        Each condition has: {field, operator, value, result}

        Supported operators:
        - eq: equals
        - ne: not equals
        - gt, gte, lt, lte: comparison
        - in: value in list
        - contains: string contains
        - regex: regex match

        Args:
            event: The event to evaluate
            conditions: List of condition dictionaries
            default: Default value if no condition matches

        Returns:
            Result from matching condition or default
        """
        for condition in conditions:
            field = str(condition.get("field", ""))
            operator = str(condition.get("operator", "eq"))
            expected = condition.get("value")
            result = condition.get("result")

            actual = self._get_event_field(event, field)

            if self._evaluate_condition(actual, operator, expected):
                return result

        return default

    def _evaluate_condition(self, actual: JSONValue, operator: str, expected: JSONValue) -> bool:
        """Evaluate a single condition."""
        if actual is None:
            return operator == "eq" and expected is None

        if operator == "eq":
            return actual == expected
        elif operator == "ne":
            return actual != expected
        elif operator == "gt":
            return actual > expected  # type: ignore[operator]
        elif operator == "gte":
            return actual >= expected  # type: ignore[operator]
        elif operator == "lt":
            return actual < expected  # type: ignore[operator]
        elif operator == "lte":
            return actual <= expected  # type: ignore[operator]
        elif operator == "in":
            expected_list = expected if isinstance(expected, list) else []
            return actual in expected_list
        elif operator == "contains":
            return str(expected) in str(actual)
        elif operator == "regex":
            return bool(re.match(str(expected), str(actual)))

        return False

    def get_summary(self, event: IntegrationEvent) -> str:
        """
        Get the ticket summary using the configured template.

        Args:
            event: The governance event

        Returns:
            Formatted summary string
        """
        return self._apply_template(event, self.config.summary_template)

    def get_priority(self, severity: EventSeverity) -> str:
        """
        Get the priority value for a severity level.

        Uses custom mapping if configured, otherwise uses defaults.

        Args:
            severity: Event severity level

        Returns:
            Priority/impact value as string
        """
        if self.config.severity_mapping:
            return self.config.severity_mapping.get_value(severity)

        if self.config.provider == TicketingProvider.JIRA:
            return DEFAULT_JIRA_PRIORITY_MAP.get(severity, JiraPriority.MEDIUM).value
        else:
            return DEFAULT_SERVICENOW_IMPACT_MAP.get(severity, ServiceNowImpactUrgency.MEDIUM).value

    def validate_config(self) -> List[str]:
        """
        Validate the mapping configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check field mappings
        for i, mapping in enumerate(self.config.field_mappings):
            prefix = f"field_mappings[{i}] ({mapping.target_field})"

            # Validate transform exists
            if mapping.mapping_type == FieldMappingType.TRANSFORM:
                transform_name = mapping.transform_name or ""
                if (
                    transform_name not in self._custom_transforms
                    and FieldTransformers.get(transform_name) is None
                ):
                    errors.append(f"{prefix}: Unknown transform '{transform_name}'")

            # Validate template placeholders
            if mapping.mapping_type == FieldMappingType.TEMPLATE:
                template = mapping.template or ""
                placeholders = self.TEMPLATE_PATTERN.findall(template)
                for placeholder in placeholders:
                    root_field = placeholder.split(".")[0]
                    if not hasattr(IntegrationEvent, root_field) and root_field != "details":
                        errors.append(f"{prefix}: Unknown event field '{placeholder}' in template")

            # Validate conditional operators
            if mapping.mapping_type == FieldMappingType.CONDITIONAL:
                valid_operators = {"eq", "ne", "gt", "gte", "lt", "lte", "in", "contains", "regex"}
                for j, cond in enumerate(mapping.conditions):
                    op = cond.get("operator", "eq")
                    if op not in valid_operators:
                        errors.append(f"{prefix}: conditions[{j}] has invalid operator '{op}'")

        return errors


# ============================================================================
# Factory Functions
# ============================================================================


def create_jira_mapping_config(
    name: str = "Default Jira Mapping",
    project_key: str = "GOV",
    issue_type: str = "Bug",
    labels: Optional[List[str]] = None,
    summary_template: str = "[ACGS-2] {title}",
    severity_mapping: Optional[Dict[str, str]] = None,
    custom_fields: Optional[Dict[str, JSONValue]] = None,
) -> TicketMappingConfig:
    """
    Create a default Jira ticket mapping configuration.

    Args:
        name: Configuration name
        project_key: Jira project key
        issue_type: Jira issue type
        labels: Labels to add to tickets
        summary_template: Template for ticket summary
        severity_mapping: Custom severity to priority mapping
        custom_fields: Additional custom field mappings

    Returns:
        TicketMappingConfig for Jira
    """
    if labels is None:
        labels = ["governance", "acgs2"]

    field_mappings = [
        FieldMapping(
            target_field="project",
            mapping_type=FieldMappingType.STATIC,
            static_value={"key": project_key},
            required=True,
        ),
        FieldMapping(
            target_field="issuetype",
            mapping_type=FieldMappingType.STATIC,
            static_value={"name": issue_type},
            required=True,
        ),
        FieldMapping(
            target_field="summary",
            mapping_type=FieldMappingType.TEMPLATE,
            template=summary_template,
            required=True,
            validation_rules=[
                FieldValidationRule(
                    validation_type=FieldValidationType.MAX_LENGTH,
                    value=255,
                    error_message="Jira summary must be 255 characters or less",
                ),
            ],
        ),
        FieldMapping(
            target_field="priority",
            mapping_type=FieldMappingType.TRANSFORM,
            transform_name="severity_to_jira_priority",
            transform_params={"mapping": severity_mapping or {}},
        ),
        FieldMapping(
            target_field="labels",
            mapping_type=FieldMappingType.TRANSFORM,
            transform_name="build_labels",
            transform_params={
                "base_labels": labels,
                "include_severity": True,
                "include_event_type": True,
            },
        ),
    ]

    # Add custom field mappings
    if custom_fields:
        for field_id, value in custom_fields.items():
            field_mappings.append(
                FieldMapping(
                    target_field=field_id,
                    mapping_type=FieldMappingType.STATIC,
                    static_value=value,
                )
            )

    return TicketMappingConfig(
        name=name,
        provider=TicketingProvider.JIRA,
        summary_template=summary_template,
        field_mappings=field_mappings,
        jira_settings={
            "project_key": project_key,
            "issue_type": issue_type,
        },
    )


def create_servicenow_mapping_config(
    name: str = "Default ServiceNow Mapping",
    category: str = "Governance",
    subcategory: Optional[str] = None,
    assignment_group: Optional[str] = None,
    summary_template: str = "[ACGS-2] {title}",
    severity_mapping: Optional[Dict[str, str]] = None,
    additional_fields: Optional[Dict[str, JSONValue]] = None,
) -> TicketMappingConfig:
    """
    Create a default ServiceNow incident mapping configuration.

    Args:
        name: Configuration name
        category: Incident category
        subcategory: Incident subcategory
        assignment_group: Assignment group for incidents
        summary_template: Template for short description
        severity_mapping: Custom severity to impact/urgency mapping
        additional_fields: Additional field mappings

    Returns:
        TicketMappingConfig for ServiceNow
    """
    field_mappings = [
        FieldMapping(
            target_field="short_description",
            mapping_type=FieldMappingType.TEMPLATE,
            template=summary_template,
            required=True,
            validation_rules=[
                FieldValidationRule(
                    validation_type=FieldValidationType.MAX_LENGTH,
                    value=160,
                    error_message="ServiceNow short_description must be 160 characters or less",
                ),
            ],
        ),
        FieldMapping(
            target_field="category",
            mapping_type=FieldMappingType.STATIC,
            static_value=category,
        ),
        FieldMapping(
            target_field="impact",
            mapping_type=FieldMappingType.TRANSFORM,
            transform_name="severity_to_servicenow_impact",
            transform_params={"mapping": severity_mapping or {}},
        ),
        FieldMapping(
            target_field="urgency",
            mapping_type=FieldMappingType.TRANSFORM,
            transform_name="severity_to_servicenow_urgency",
            transform_params={"mapping": severity_mapping or {}},
        ),
    ]

    if subcategory:
        field_mappings.append(
            FieldMapping(
                target_field="subcategory",
                mapping_type=FieldMappingType.STATIC,
                static_value=subcategory,
            )
        )

    if assignment_group:
        field_mappings.append(
            FieldMapping(
                target_field="assignment_group",
                mapping_type=FieldMappingType.STATIC,
                static_value=assignment_group,
            )
        )

    # Add additional field mappings
    if additional_fields:
        for field_name, value in additional_fields.items():
            field_mappings.append(
                FieldMapping(
                    target_field=field_name,
                    mapping_type=FieldMappingType.STATIC,
                    static_value=value,
                )
            )

    return TicketMappingConfig(
        name=name,
        provider=TicketingProvider.SERVICENOW,
        summary_template=summary_template,
        field_mappings=field_mappings,
        servicenow_settings={
            "category": category,
            "subcategory": subcategory,
            "assignment_group": assignment_group,
        },
    )
