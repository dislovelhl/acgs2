"""
PagerDuty Enums for Integration.
Constitutional Hash: cdd01ef066bc6cf2
"""

from enum import Enum


class PagerDutyAuthType(str, Enum):
    """Authentication methods supported by PagerDuty."""

    EVENTS_V2 = "events_v2"  # Integration key only
    REST_API = "rest_api"  # API token only
    BOTH = "both"  # Both methods (full lifecycle)
