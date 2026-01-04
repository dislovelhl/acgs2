"""
SIEM Event Formatter

Provides standardized JSON payload formatting for SIEM integrations.
Supports formatting governance events for Splunk HEC and Microsoft Sentinel
with consistent field mapping and severity translation.

Features:
- Standardized event payload structure
- SIEM-specific formatting (Splunk, Sentinel)
- Configurable field mappings
- CEF (Common Event Format) output option
- Severity normalization across platforms
- JSON serialization utilities
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ..types import EventData, JSONDict, ModelContext
from .base import EventSeverity, IntegrationEvent

logger = logging.getLogger(__name__)


class SIEMFormat(str, Enum):
    """Supported SIEM output formats"""

    SPLUNK = "splunk"
    SENTINEL = "sentinel"
    CEF = "cef"  # Common Event Format
    JSON = "json"  # Generic standardized JSON


class SeverityLevel(int, Enum):
    """Numeric severity levels (1=Critical to 5=Info)"""

    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5


# Severity mappings
SEVERITY_TO_LEVEL: Dict[EventSeverity, int] = {
    EventSeverity.CRITICAL: SeverityLevel.CRITICAL,
    EventSeverity.HIGH: SeverityLevel.HIGH,
    EventSeverity.MEDIUM: SeverityLevel.MEDIUM,
    EventSeverity.LOW: SeverityLevel.LOW,
    EventSeverity.INFO: SeverityLevel.INFO,
}

SEVERITY_TO_NAME: Dict[EventSeverity, str] = {
    EventSeverity.CRITICAL: "Critical",
    EventSeverity.HIGH: "High",
    EventSeverity.MEDIUM: "Medium",
    EventSeverity.LOW: "Low",
    EventSeverity.INFO: "Informational",
}

# CEF severity mapping (0-10 scale)
SEVERITY_TO_CEF: Dict[EventSeverity, int] = {
    EventSeverity.CRITICAL: 10,
    EventSeverity.HIGH: 8,
    EventSeverity.MEDIUM: 5,
    EventSeverity.LOW: 3,
    EventSeverity.INFO: 1,
}


class StandardizedSIEMEvent(BaseModel):
    """
    Standardized SIEM event payload structure.

    This model provides a consistent event format that can be transformed
    into SIEM-specific formats (Splunk, Sentinel, CEF).
    """

    # Timing
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp in UTC",
    )
    time_epoch: Optional[float] = Field(
        None,
        description="Unix epoch timestamp (auto-calculated from timestamp)",
    )

    # Event identification
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Type of governance event")
    event_category: str = Field(
        default="governance",
        description="Event category for SIEM classification",
    )

    # Severity
    severity: str = Field(..., description="Severity level name (Critical, High, etc.)")
    severity_level: int = Field(
        ...,
        ge=1,
        le=5,
        description="Numeric severity (1=Critical to 5=Info)",
    )

    # Source information
    source: str = Field(default="acgs2", description="Source system identifier")
    source_type: str = Field(
        default="governance:event",
        description="Source type for event classification",
    )
    host: str = Field(
        default="acgs2-integration-service",
        description="Originating host",
    )

    # Event content
    title: str = Field(..., description="Event title/summary")
    description: Optional[str] = Field(None, description="Detailed description")
    message: str = Field(..., description="Human-readable event message")

    # Governance context
    policy_id: Optional[str] = Field(None, description="Related policy ID")
    policy_name: Optional[str] = Field(None, description="Related policy name")
    resource_id: Optional[str] = Field(None, description="Affected resource ID")
    resource_type: Optional[str] = Field(None, description="Type of affected resource")
    resource_name: Optional[str] = Field(None, description="Name of affected resource")
    action: Optional[str] = Field(None, description="Action that triggered the event")
    outcome: Optional[str] = Field(None, description="Outcome of the action (success/failure)")

    # Actor information
    user_id: Optional[str] = Field(None, description="User who triggered the event")
    user_name: Optional[str] = Field(None, description="Username of actor")
    user_email: Optional[str] = Field(None, description="Email of actor")

    # Multi-tenancy and correlation
    tenant_id: Optional[str] = Field(None, description="Tenant ID for multi-tenant deployments")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for tracing")
    session_id: Optional[str] = Field(None, description="Session ID if applicable")

    # Classification
    tags: List[str] = Field(default_factory=list, description="Event tags")
    labels: Dict[str, str] = Field(default_factory=dict, description="Key-value labels")

    # Extended details
    details: EventData = Field(
        default_factory=dict,
        description="Additional event details",
    )
    raw_event: Optional[JSONDict] = Field(
        None,
        description="Original raw event data",
    )

    def model_post_init(self, __context: ModelContext) -> None:
        """Calculate derived fields after initialization"""
        if self.time_epoch is None:
            self.time_epoch = self.timestamp.timestamp()


class SplunkEventConfig(BaseModel):
    """Configuration for Splunk event formatting"""

    index: str = Field(default="main", description="Target Splunk index")
    source: str = Field(default="acgs2", description="Source identifier")
    sourcetype: str = Field(
        default="acgs2:governance",
        description="Sourcetype for events",
    )
    host: str = Field(
        default="acgs2-integration-service",
        description="Originating host",
    )
    include_raw_event: bool = Field(
        default=False,
        description="Whether to include raw event data",
    )


class SentinelEventConfig(BaseModel):
    """Configuration for Sentinel event formatting"""

    stream_name: str = Field(
        default="Custom-GovernanceEvents_CL",
        description="Target Log Analytics stream",
    )
    include_raw_event: bool = Field(
        default=False,
        description="Whether to include raw event data",
    )


class CEFEventConfig(BaseModel):
    """Configuration for CEF event formatting"""

    vendor: str = Field(default="ACGS2", description="Vendor name")
    product: str = Field(
        default="Governance Platform",
        description="Product name",
    )
    version: str = Field(default="1.0", description="Product version")
    device_event_class_id: str = Field(
        default="governance",
        description="Device event class ID",
    )


def format_siem_event(
    event: Union[IntegrationEvent, JSONDict],
    format_type: SIEMFormat = SIEMFormat.JSON,
    config: Optional[Union[SplunkEventConfig, SentinelEventConfig, CEFEventConfig]] = None,
) -> JSONDict:
    """
    Format a governance event for SIEM ingestion.

    This is the main entry point for formatting events for various SIEM platforms.
    It converts an IntegrationEvent or dict into a standardized format suitable
    for the target SIEM system.

    Args:
        event: The governance event to format (IntegrationEvent or dict)
        format_type: Target SIEM format (splunk, sentinel, cef, json)
        config: Optional SIEM-specific configuration

    Returns:
        Formatted event dictionary ready for SIEM submission

    Examples:
        >>> event = IntegrationEvent(
        ...     event_type="policy_violation",
        ...     title="Policy Violation Detected",
        ...     severity=EventSeverity.HIGH,
        ... )
        >>> formatted = format_siem_event(event, SIEMFormat.SPLUNK)
        >>> formatted = format_siem_event(event, SIEMFormat.SENTINEL)
    """
    # Convert dict to IntegrationEvent if needed
    if isinstance(event, dict):
        event = _dict_to_integration_event(event)

    # Create standardized event
    standardized = _to_standardized_event(event)

    # Format for target SIEM
    if format_type == SIEMFormat.SPLUNK:
        splunk_config = config if isinstance(config, SplunkEventConfig) else SplunkEventConfig()
        return format_splunk_event(standardized, splunk_config)
    elif format_type == SIEMFormat.SENTINEL:
        sentinel_config = (
            config if isinstance(config, SentinelEventConfig) else SentinelEventConfig()
        )
        return format_sentinel_event(standardized, sentinel_config)
    elif format_type == SIEMFormat.CEF:
        cef_config = config if isinstance(config, CEFEventConfig) else CEFEventConfig()
        return format_cef_event(standardized, cef_config)
    else:
        return format_json_event(standardized)


def format_splunk_event(
    event: StandardizedSIEMEvent,
    config: Optional[SplunkEventConfig] = None,
) -> JSONDict:
    """
    Format an event for Splunk HEC submission.

    Creates a Splunk HEC-compatible JSON payload with proper field mapping
    and metadata for the event.

    Args:
        event: Standardized SIEM event
        config: Splunk-specific configuration

    Returns:
        Dictionary formatted for Splunk HEC endpoint
    """
    if config is None:
        config = SplunkEventConfig()

    # Build the event payload
    event_data = {
        # Core event fields
        "event_id": event.event_id,
        "event_type": event.event_type,
        "event_category": event.event_category,
        "severity": event.severity,
        "severity_level": event.severity_level,
        "source_system": event.source,
        # Content
        "title": event.title,
        "description": event.description,
        "message": event.message,
        # Governance context
        "policy_id": event.policy_id,
        "policy_name": event.policy_name,
        "resource_id": event.resource_id,
        "resource_type": event.resource_type,
        "resource_name": event.resource_name,
        "action": event.action,
        "outcome": event.outcome,
        # Actor
        "user_id": event.user_id,
        "user_name": event.user_name,
        "user_email": event.user_email,
        # Correlation
        "tenant_id": event.tenant_id,
        "correlation_id": event.correlation_id,
        "session_id": event.session_id,
        # Classification
        "tags": event.tags,
        "labels": event.labels,
    }

    # Add extended details
    if event.details:
        event_data.update(event.details)

    # Optionally include raw event
    if config.include_raw_event and event.raw_event:
        event_data["raw_event"] = event.raw_event

    # Remove None values for cleaner Splunk indexing
    event_data = {k: v for k, v in event_data.items() if v is not None}

    # Build HEC payload
    splunk_payload = {
        "event": event_data,
        "time": event.time_epoch,
        "source": config.source,
        "sourcetype": config.sourcetype,
        "index": config.index,
        "host": config.host,
    }

    return splunk_payload


def format_sentinel_event(
    event: StandardizedSIEMEvent,
    config: Optional[SentinelEventConfig] = None,
) -> JSONDict:
    """
    Format an event for Azure Monitor Logs Ingestion API.

    Creates an Azure Monitor-compatible JSON payload with proper field mapping
    for Log Analytics custom tables.

    Args:
        event: Standardized SIEM event
        config: Sentinel-specific configuration

    Returns:
        Dictionary formatted for Azure Monitor Logs Ingestion
    """
    if config is None:
        config = SentinelEventConfig()

    # TimeGenerated is required by Azure Monitor and must be ISO 8601 format
    sentinel_event = {
        # Required field - must be ISO 8601 format
        "TimeGenerated": event.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Core event fields
        "EventId": event.event_id,
        "EventType": event.event_type,
        "EventCategory": event.event_category,
        "Severity": event.severity,
        "SeverityLevel": event.severity_level,
        "Source": event.source,
        # Content
        "Title": event.title,
        "Description": event.description or "",
        "Message": event.message,
        # Governance context
        "PolicyId": event.policy_id or "",
        "PolicyName": event.policy_name or "",
        "ResourceId": event.resource_id or "",
        "ResourceType": event.resource_type or "",
        "ResourceName": event.resource_name or "",
        "Action": event.action or "",
        "Outcome": event.outcome or "",
        # Actor
        "UserId": event.user_id or "",
        "UserName": event.user_name or "",
        "UserEmail": event.user_email or "",
        # Correlation
        "TenantId": event.tenant_id or "",
        "CorrelationId": event.correlation_id or "",
        "SessionId": event.session_id or "",
        # Classification - serialize lists/dicts as JSON strings for Log Analytics
        "Tags": json.dumps(event.tags) if event.tags else "[]",
        "Labels": json.dumps(event.labels) if event.labels else "{}",
        # Extended details as JSON string
        "Details": json.dumps(event.details) if event.details else "{}",
    }

    # Optionally include raw event
    if config.include_raw_event and event.raw_event:
        sentinel_event["RawEvent"] = json.dumps(event.raw_event)

    return sentinel_event


def format_cef_event(
    event: StandardizedSIEMEvent,
    config: Optional[CEFEventConfig] = None,
) -> JSONDict:
    """
    Format an event in Common Event Format (CEF).

    Creates a CEF-compatible payload for SIEM systems that support CEF.
    Returns both the CEF string and a structured dict representation.

    Args:
        event: Standardized SIEM event
        config: CEF-specific configuration

    Returns:
        Dictionary with 'cef_string' and 'structured' keys
    """
    if config is None:
        config = CEFEventConfig()

    # Map severity to CEF severity (0-10)
    severity_level = event.severity_level
    cef_severity = 10 - (severity_level - 1) * 2  # Maps 1->10, 2->8, 3->6, 4->4, 5->2

    # Build CEF extension fields
    extensions = {
        "eventId": event.event_id,
        "msg": event.message,
        "cat": event.event_category,
        "src": event.source,
        "suser": event.user_id or "",
        "suid": event.user_id or "",
        "cs1": event.policy_id or "",
        "cs1Label": "PolicyId",
        "cs2": event.resource_id or "",
        "cs2Label": "ResourceId",
        "cs3": event.tenant_id or "",
        "cs3Label": "TenantId",
        "cs4": event.correlation_id or "",
        "cs4Label": "CorrelationId",
        "outcome": event.outcome or "",
        "act": event.action or "",
        "rt": int(event.time_epoch * 1000) if event.time_epoch else 0,  # CEF uses milliseconds
    }

    # Build extension string (key=value pairs)
    ext_parts = []
    for key, value in extensions.items():
        if value:  # Only include non-empty values
            # Escape special characters in values
            escaped_value = _escape_cef_value(str(value))
            ext_parts.append(f"{key}={escaped_value}")
    extension_str = " ".join(ext_parts)

    # Build CEF header
    # Format: CEF:Version|Vendor|Product|Version|EventClassID|Name|Severity|Extension
    cef_header = (
        f"CEF:0|{_escape_cef_header(config.vendor)}|"
        f"{_escape_cef_header(config.product)}|"
        f"{_escape_cef_header(config.version)}|"
        f"{_escape_cef_header(config.device_event_class_id)}|"
        f"{_escape_cef_header(event.title)}|"
        f"{cef_severity}|"
    )

    cef_string = cef_header + extension_str

    return {
        "cef_string": cef_string,
        "structured": {
            "cef_version": 0,
            "vendor": config.vendor,
            "product": config.product,
            "version": config.version,
            "device_event_class_id": config.device_event_class_id,
            "name": event.title,
            "severity": cef_severity,
            "extensions": extensions,
        },
    }


def format_json_event(
    event: StandardizedSIEMEvent,
) -> JSONDict:
    """
    Format an event as a generic standardized JSON payload.

    Creates a JSON payload that can be used with any SIEM that accepts
    JSON-formatted events.

    Args:
        event: Standardized SIEM event

    Returns:
        Dictionary with standardized JSON structure
    """
    return {
        "version": "1.0",
        "schema": "acgs2-governance-event",
        "timestamp": event.timestamp.isoformat(),
        "timestamp_epoch": event.time_epoch,
        "event": {
            "id": event.event_id,
            "type": event.event_type,
            "category": event.event_category,
            "severity": {
                "name": event.severity,
                "level": event.severity_level,
            },
            "title": event.title,
            "description": event.description,
            "message": event.message,
        },
        "source": {
            "name": event.source,
            "type": event.source_type,
            "host": event.host,
        },
        "governance": {
            "policy": {
                "id": event.policy_id,
                "name": event.policy_name,
            },
            "resource": {
                "id": event.resource_id,
                "type": event.resource_type,
                "name": event.resource_name,
            },
            "action": event.action,
            "outcome": event.outcome,
        },
        "actor": {
            "user_id": event.user_id,
            "user_name": event.user_name,
            "user_email": event.user_email,
        },
        "context": {
            "tenant_id": event.tenant_id,
            "correlation_id": event.correlation_id,
            "session_id": event.session_id,
        },
        "classification": {
            "tags": event.tags,
            "labels": event.labels,
        },
        "details": event.details,
        "raw_event": event.raw_event,
    }


def format_events_batch(
    events: List[Union[IntegrationEvent, JSONDict]],
    format_type: SIEMFormat = SIEMFormat.JSON,
    config: Optional[Union[SplunkEventConfig, SentinelEventConfig, CEFEventConfig]] = None,
) -> List[JSONDict]:
    """
    Format multiple events for SIEM ingestion.

    Args:
        events: List of governance events to format
        format_type: Target SIEM format
        config: Optional SIEM-specific configuration

    Returns:
        List of formatted event dictionaries
    """
    return [format_siem_event(event, format_type, config) for event in events]


def _dict_to_integration_event(data: JSONDict) -> IntegrationEvent:
    """
    Convert a dictionary to an IntegrationEvent.

    Args:
        data: Event data dictionary

    Returns:
        IntegrationEvent instance
    """
    # Map common field name variations
    field_mappings = {
        "id": "event_id",
        "type": "event_type",
        "time": "timestamp",
        "datetime": "timestamp",
    }

    normalized = {}
    for key, value in data.items():
        mapped_key = field_mappings.get(key, key)
        normalized[mapped_key] = value

    # Handle severity conversion
    if "severity" in normalized and isinstance(normalized["severity"], str):
        severity_str = normalized["severity"].lower()
        severity_map = {
            "critical": EventSeverity.CRITICAL,
            "high": EventSeverity.HIGH,
            "medium": EventSeverity.MEDIUM,
            "low": EventSeverity.LOW,
            "info": EventSeverity.INFO,
            "informational": EventSeverity.INFO,
        }
        normalized["severity"] = severity_map.get(severity_str, EventSeverity.INFO)

    # Ensure required fields have defaults
    if "event_type" not in normalized:
        normalized["event_type"] = "unknown"
    if "title" not in normalized:
        normalized["title"] = normalized.get("message", "Governance Event")

    return IntegrationEvent(**normalized)


def _to_standardized_event(event: IntegrationEvent) -> StandardizedSIEMEvent:
    """
    Convert an IntegrationEvent to a StandardizedSIEMEvent.

    Args:
        event: Integration event to convert

    Returns:
        StandardizedSIEMEvent instance
    """
    # Build message from event content
    message = event.description or event.title
    if event.policy_id:
        message = f"[Policy: {event.policy_id}] {message}"

    return StandardizedSIEMEvent(
        timestamp=event.timestamp,
        event_id=event.event_id,
        event_type=event.event_type,
        event_category="governance",
        severity=SEVERITY_TO_NAME.get(event.severity, "Informational"),
        severity_level=SEVERITY_TO_LEVEL.get(event.severity, SeverityLevel.INFO),
        source=event.source,
        source_type=f"governance:{event.event_type}",
        title=event.title,
        description=event.description,
        message=message,
        policy_id=event.policy_id,
        resource_id=event.resource_id,
        resource_type=event.resource_type,
        action=event.action,
        outcome=event.outcome,
        user_id=event.user_id,
        tenant_id=event.tenant_id,
        correlation_id=event.correlation_id,
        tags=event.tags,
        details=event.details,
    )


def _escape_cef_header(value: str) -> str:
    """
    Escape special characters in CEF header fields.

    CEF header fields need to escape: backslash and pipe characters.

    Args:
        value: Header field value

    Returns:
        Escaped value
    """
    if not value:
        return ""
    return value.replace("\\", "\\\\").replace("|", "\\|")


def _escape_cef_value(value: str) -> str:
    """
    Escape special characters in CEF extension values.

    CEF extension values need to escape: backslash, equals, and newlines.

    Args:
        value: Extension field value

    Returns:
        Escaped value
    """
    if not value:
        return ""
    return value.replace("\\", "\\\\").replace("=", "\\=").replace("\n", "\\n").replace("\r", "")


def normalize_severity(
    severity: Union[str, int, EventSeverity],
) -> tuple[str, int]:
    """
    Normalize severity to standard name and level.

    Accepts various severity formats and returns a tuple of (name, level).

    Args:
        severity: Severity as string, int, or EventSeverity enum

    Returns:
        Tuple of (severity_name, severity_level)

    Examples:
        >>> normalize_severity("high")
        ('High', 2)
        >>> normalize_severity(1)
        ('Critical', 1)
        >>> normalize_severity(EventSeverity.MEDIUM)
        ('Medium', 3)
    """
    if isinstance(severity, EventSeverity):
        return (
            SEVERITY_TO_NAME.get(severity, "Informational"),
            SEVERITY_TO_LEVEL.get(severity, SeverityLevel.INFO),
        )

    if isinstance(severity, int):
        level = max(1, min(5, severity))  # Clamp to 1-5
        level_to_name = {v: k for k, v in SEVERITY_TO_LEVEL.items()}
        event_severity = level_to_name.get(level, EventSeverity.INFO)
        return (
            SEVERITY_TO_NAME.get(event_severity, "Informational"),
            level,
        )

    if isinstance(severity, str):
        severity_lower = severity.lower().strip()
        str_to_enum = {
            "critical": EventSeverity.CRITICAL,
            "crit": EventSeverity.CRITICAL,
            "high": EventSeverity.HIGH,
            "medium": EventSeverity.MEDIUM,
            "med": EventSeverity.MEDIUM,
            "low": EventSeverity.LOW,
            "info": EventSeverity.INFO,
            "informational": EventSeverity.INFO,
            "information": EventSeverity.INFO,
        }
        event_severity = str_to_enum.get(severity_lower, EventSeverity.INFO)
        return (
            SEVERITY_TO_NAME.get(event_severity, "Informational"),
            SEVERITY_TO_LEVEL.get(event_severity, SeverityLevel.INFO),
        )

    # Default fallback
    return ("Informational", SeverityLevel.INFO)


def get_event_signature(event: IntegrationEvent) -> str:
    """
    Generate a unique signature for an event for deduplication.

    Creates a hash-like signature based on key event fields that can be
    used for event deduplication in SIEM systems.

    Args:
        event: Integration event

    Returns:
        Event signature string
    """
    components = [
        event.event_type,
        event.policy_id or "",
        event.resource_id or "",
        event.action or "",
        event.user_id or "",
        event.tenant_id or "",
    ]
    return ":".join(c for c in components if c)
