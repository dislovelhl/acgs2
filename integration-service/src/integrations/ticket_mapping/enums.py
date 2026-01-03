"""
Ticket mapping enums and default mappings for ACGS-2 Integration Service.

This module defines enumerations for ticketing providers, field mapping types,
validation types, and priority/impact/urgency levels. It also provides default
mappings from event severity to Jira priorities and ServiceNow impact/urgency values.
"""

from enum import Enum
from typing import Dict

from ..base import EventSeverity


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


__all__ = [
    "TicketingProvider",
    "FieldMappingType",
    "FieldValidationType",
    "JiraPriority",
    "ServiceNowImpactUrgency",
    "DEFAULT_JIRA_PRIORITY_MAP",
    "DEFAULT_SERVICENOW_IMPACT_MAP",
    "DEFAULT_SERVICENOW_URGENCY_MAP",
]
