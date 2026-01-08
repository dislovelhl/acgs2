"""Constitutional Hash: cdd01ef066bc6cf2
PagerDuty Payload Builder.
Handles construction of payloads for PagerDuty Events and REST APIs.
"""

from typing import Any, Dict, List, Optional
from ..base import EventSeverity, IntegrationEvent
from ..pagerduty_models import (
    DEFAULT_SEVERITY_MAP,
    PagerDutyCredentials,
)

class PagerDutyPayloadBuilder:
    """Helper class to build PagerDuty payloads."""

    def __init__(self, credentials: PagerDutyCredentials):
        self.credentials = credentials

    def build_incident_payload(self, event: IntegrationEvent) -> Dict[str, Any]:
        """Build the PagerDuty incident creation payload from an event."""
        # Generate dedup_key from event_id
        dedup_key = f"{self.credentials.dedup_key_prefix}-{event.event_id}"

        # Build summary from template
        summary = self.credentials.summary_template.format(
            title=event.title,
            event_type=event.event_type,
            severity=event.severity.value,
        )
        # PagerDuty summary max length is 1024 characters
        if len(summary) > 1024:
            summary = summary[:1021] + "..."

        # Get PagerDuty severity for the event
        pd_severity = self.get_severity_for_event(event.severity)

        # Build custom details
        custom_details = {}

        # Add event details if configured
        if self.credentials.include_event_details:
            custom_details.update(
                {
                    "event_id": event.event_id,
                    "event_type": event.event_type,
                    "acgs2_severity": event.severity.value,
                    "timestamp": event.timestamp.isoformat(),
                }
            )

            if event.policy_id:
                custom_details["policy_id"] = event.policy_id
            if event.resource_id:
                custom_details["resource_id"] = event.resource_id
            if event.resource_type:
                custom_details["resource_type"] = event.resource_type
            if event.action:
                custom_details["action"] = event.action
            if event.outcome:
                custom_details["outcome"] = event.outcome
            if event.user_id:
                custom_details["user_id"] = event.user_id
            if event.tenant_id:
                custom_details["tenant_id"] = event.tenant_id
            if event.correlation_id:
                custom_details["correlation_id"] = event.correlation_id
            if event.tags:
                custom_details["tags"] = event.tags
            if event.details:
                custom_details["event_details"] = event.details

        # Add configured custom details
        custom_details.update(self.credentials.custom_details)

        # Build the payload
        payload: Dict[str, Any] = {
            "summary": summary,
            "source": self.credentials.default_source,
            "severity": pd_severity,
        }

        # Add optional fields
        if event.timestamp:
            payload["timestamp"] = event.timestamp.isoformat()

        if self.credentials.default_component:
            payload["component"] = self.credentials.default_component

        if self.credentials.default_group:
            payload["group"] = self.credentials.default_group

        if self.credentials.default_class:
            payload["class"] = self.credentials.default_class

        # Add custom details
        if custom_details:
            payload["custom_details"] = custom_details

        # Build the full event payload
        event_payload = {
            "routing_key": self.credentials.integration_key.get_secret_value() if self.credentials.integration_key else "",
            "event_action": "trigger",
            "dedup_key": dedup_key,
            "payload": payload,
        }

        return event_payload

    def get_severity_for_event(self, severity: EventSeverity) -> str:
        """Get PagerDuty severity for a given event severity level."""
        # Check custom mapping first
        custom_severity = self.credentials.severity_mapping.get(severity.value)
        if custom_severity:
            return custom_severity

        # Use default mapping
        return DEFAULT_SEVERITY_MAP.get(severity, "info")

    def get_urgency_for_severity(self, severity: EventSeverity) -> str:
        """Get PagerDuty urgency for a given event severity level."""
        # Check custom mapping first
        custom_urgency = self.credentials.urgency_mapping.get(severity.value)
        if custom_urgency:
            return custom_urgency

        # Use default mapping
        from ..pagerduty_models import DEFAULT_URGENCY_MAP
        return DEFAULT_URGENCY_MAP.get(severity, "low")

    def build_resolve_payload(self, dedup_key: str) -> Dict[str, Any]:
        """Build the payload for resolving an incident."""
        return {
            "routing_key": self.credentials.integration_key.get_secret_value() if self.credentials.integration_key else "",
            "event_action": "resolve",
            "dedup_key": dedup_key,
        }

    def build_update_payload(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        escalation_policy_id: Optional[str] = None,
        assigned_to_user_ids: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Build the payload for updating an incident."""
        update_payload: Dict[str, Any] = {}

        if status:
            update_payload["status"] = status

        if priority:
            update_payload["priority"] = {"id": priority, "type": "priority_reference"}

        if escalation_policy_id:
            update_payload["escalation_policy"] = {
                "id": escalation_policy_id,
                "type": "escalation_policy_reference",
            }

        if assigned_to_user_ids:
            update_payload["assignments"] = [
                {"assignee": {"id": user_id, "type": "user_reference"}}
                for user_id in assigned_to_user_ids
            ]

        # Add any additional fields
        update_payload.update(kwargs)
        return {"incident": update_payload}

    def build_note_payload(self, note: str) -> Dict[str, Any]:
        """Build the payload for adding a note to an incident."""
        return {
            "note": {
                "content": note,
            }
        }
