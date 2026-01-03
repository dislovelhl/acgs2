"""
HITL Approvals Notification Providers

This module provides notification integrations for Slack, Microsoft Teams,
and PagerDuty to deliver approval workflow notifications.
"""

from app.notifications.base import (
    NotificationProvider,
    NotificationResult,
    NotificationStatus,
)
from app.notifications.retry import (
    FailedNotification,
    FailedNotificationStore,
    RetryableNotificationSender,
    RetryConfig,
    calculate_backoff_delay,
    get_failed_notification_store,
    retry_with_backoff,
    with_retry,
)

__all__ = [
    # Base classes
    "NotificationProvider",
    "NotificationResult",
    "NotificationStatus",
    # Retry functionality
    "RetryConfig",
    "FailedNotification",
    "FailedNotificationStore",
    "RetryableNotificationSender",
    "retry_with_backoff",
    "with_retry",
    "calculate_backoff_delay",
    "get_failed_notification_store",
]
