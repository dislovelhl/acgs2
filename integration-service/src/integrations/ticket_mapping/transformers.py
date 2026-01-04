"""
Field transformation functions for ticket mapping in ACGS-2 Integration Service.

This module provides the FieldTransformers registry class and a collection of
built-in transformer functions for common field transformations. Transformers
convert event data into ticketing system field values (e.g., severity to priority,
timestamp formatting, label generation).
"""

import json
from typing import Any, Callable, Dict, List, Optional

from ..base import IntegrationEvent
from .enums import (
    DEFAULT_JIRA_PRIORITY_MAP,
    DEFAULT_SERVICENOW_IMPACT_MAP,
    DEFAULT_SERVICENOW_URGENCY_MAP,
    JiraPriority,
    ServiceNowImpactUrgency,
)

# Type for transform functions
TransformFunc = Callable[[IntegrationEvent, Dict[str, Any]], Any]


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
def severity_to_jira_priority(event: IntegrationEvent, params: Dict[str, Any]) -> str:
    """Convert event severity to Jira priority name."""
    custom_map = params.get("mapping", {})
    if custom_map and event.severity.value in custom_map:
        return custom_map[event.severity.value]
    return DEFAULT_JIRA_PRIORITY_MAP.get(event.severity, JiraPriority.MEDIUM).value


@FieldTransformers.register("severity_to_servicenow_impact")
def severity_to_servicenow_impact(event: IntegrationEvent, params: Dict[str, Any]) -> str:
    """Convert event severity to ServiceNow impact value."""
    custom_map = params.get("mapping", {})
    if custom_map and event.severity.value in custom_map:
        return custom_map[event.severity.value]
    return DEFAULT_SERVICENOW_IMPACT_MAP.get(event.severity, ServiceNowImpactUrgency.MEDIUM).value


@FieldTransformers.register("severity_to_servicenow_urgency")
def severity_to_servicenow_urgency(event: IntegrationEvent, params: Dict[str, Any]) -> str:
    """Convert event severity to ServiceNow urgency value."""
    custom_map = params.get("mapping", {})
    if custom_map and event.severity.value in custom_map:
        return custom_map[event.severity.value]
    return DEFAULT_SERVICENOW_URGENCY_MAP.get(event.severity, ServiceNowImpactUrgency.MEDIUM).value


@FieldTransformers.register("format_timestamp")
def format_timestamp(event: IntegrationEvent, params: Dict[str, Any]) -> str:
    """Format event timestamp to a specific format."""
    fmt = params.get("format", "%Y-%m-%d %H:%M:%S")
    return event.timestamp.strftime(fmt)


@FieldTransformers.register("format_tags")
def format_tags(event: IntegrationEvent, params: Dict[str, Any]) -> str:
    """Format event tags as a string."""
    separator = params.get("separator", ", ")
    return separator.join(event.tags)


@FieldTransformers.register("build_labels")
def build_labels(event: IntegrationEvent, params: Dict[str, Any]) -> List[str]:
    """Build a list of labels from event data."""
    base_labels = params.get("base_labels", ["governance", "acgs2"])
    labels = list(base_labels)

    if params.get("include_severity", True):
        labels.append(f"severity-{event.severity.value}")

    if params.get("include_event_type", True) and event.event_type:
        labels.append(event.event_type.replace("_", "-").replace(" ", "-").lower())

    if params.get("include_tags", False):
        labels.extend(event.tags)

    return labels


@FieldTransformers.register("truncate")
def truncate(event: IntegrationEvent, params: Dict[str, Any]) -> str:
    """Truncate a field value to max length."""
    source_field = params.get("source_field", "title")
    max_length = params.get("max_length", 255)
    suffix = params.get("suffix", "...")

    value = getattr(event, source_field, "") or ""
    if len(value) > max_length:
        return value[: max_length - len(suffix)] + suffix
    return value


@FieldTransformers.register("json_details")
def json_details(event: IntegrationEvent, params: Dict[str, Any]) -> str:
    """Format event details as JSON string."""
    indent = params.get("indent", 2)
    include_fields = params.get("include_fields", None)

    if include_fields:
        details = {k: v for k, v in event.details.items() if k in include_fields}
    else:
        details = event.details

    return json.dumps(details, indent=indent, default=str)


@FieldTransformers.register("concatenate")
def concatenate(event: IntegrationEvent, params: Dict[str, Any]) -> str:
    """Concatenate multiple event fields."""
    fields = params.get("fields", [])
    separator = params.get("separator", " ")

    values = []
    for field in fields:
        value = getattr(event, field, None)
        if value is not None:
            values.append(str(value))

    return separator.join(values)


@FieldTransformers.register("map_value")
def map_value(event: IntegrationEvent, params: Dict[str, Any]) -> Any:
    """Map a field value using a lookup table."""
    source_field = params.get("source_field", "")
    mapping = params.get("mapping", {})
    default = params.get("default", None)

    value = getattr(event, source_field, None)
    if value is not None:
        return mapping.get(str(value), default)
    return default


__all__ = [
    "TransformFunc",
    "FieldTransformers",
    "severity_to_jira_priority",
    "severity_to_servicenow_impact",
    "severity_to_servicenow_urgency",
    "format_timestamp",
    "format_tags",
    "build_labels",
    "truncate",
    "json_details",
    "concatenate",
    "map_value",
]
