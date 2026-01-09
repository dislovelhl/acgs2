"""
Ticket field mapper for ACGS-2 Integration Service.

This module provides the TicketFieldMapper class which orchestrates the mapping
of governance events to ticketing system fields. It supports template-based field
generation, severity mapping, custom transformations, and field validation.
"""

import logging
import re
from typing import Any, Dict, List

from ..base import EventSeverity, IntegrationEvent
from .enums import (
    DEFAULT_JIRA_PRIORITY_MAP,
    DEFAULT_SERVICENOW_IMPACT_MAP,
    FieldMappingType,
    JiraPriority,
    ServiceNowImpactUrgency,
    TicketingProvider,
)
from .models import FieldMapping, FieldMappingResult, TicketMappingConfig, TicketMappingResult
from .transformers import FieldTransformers, TransformFunc
from .validators import FieldValidator

logger = logging.getLogger(__name__)


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

    def _compute_value(self, event: IntegrationEvent, mapping: FieldMapping) -> Any:
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

    def _get_event_field(self, event: IntegrationEvent, field_path: str) -> Any:
        """
        Get a field value from an event, supporting nested paths.

        Args:
            event: The event to get value from
            field_path: Field path (e.g., "title", "details.key")

        Returns:
            Field value or None if not found
        """
        parts = field_path.split(".")
        value: Any = event

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None

        # Ensure we return a simple type
        if isinstance(value, (str, int, float, bool, dict, list, type(None))):
            return value  # type: ignore[return-value]
        return str(value)

    def _apply_transform(
        self,
        event: IntegrationEvent,
        transform_name: str,
        params: Dict[str, Any],
    ) -> Any:
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
        conditions: List[Dict[str, Any]],
        default: Any,
    ) -> Any:
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

    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
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


__all__ = [
    "TicketFieldMapper",
]
