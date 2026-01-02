"""
Abstract Notification Provider Base Class

Defines the interface for notification providers (Slack, Teams, PagerDuty)
with common functionality for delivery confirmation, retry logic, and health checks.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from app.models import NotificationPayload

logger = logging.getLogger(__name__)


class NotificationStatus(str, Enum):
    """Status of a notification delivery attempt."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    INVALID_CONFIG = "invalid_config"


@dataclass
class NotificationResult:
    """Result of a notification delivery attempt."""

    status: NotificationStatus
    provider: str
    message_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    retry_after: Optional[int] = None  # Seconds to wait before retry
    raw_response: Optional[Dict[str, Any]] = None

    @property
    def is_success(self) -> bool:
        """Check if the notification was successfully delivered."""
        return self.status in (NotificationStatus.SENT, NotificationStatus.DELIVERED)

    @property
    def should_retry(self) -> bool:
        """Check if the notification should be retried."""
        return self.status in (NotificationStatus.FAILED, NotificationStatus.RATE_LIMITED)


class NotificationProvider(ABC):
    """
    Abstract base class for notification providers.

    All notification providers (Slack, Teams, PagerDuty) must implement this interface
    to ensure consistent behavior across the HITL approvals service.

    Implementations must:
    - Provide async send_notification method
    - Implement health check for webhook validation
    - Handle rate limiting appropriately
    - Sanitize sensitive data from logs
    """

    def __init__(self, name: str):
        """
        Initialize the notification provider.

        Args:
            name: Human-readable name of the provider (e.g., "Slack", "Teams")
        """
        self._name = name
        self._enabled = False
        self._last_health_check: Optional[datetime] = None
        self._health_status: bool = False

    @property
    def name(self) -> str:
        """Get the provider name."""
        return self._name

    @property
    def is_enabled(self) -> bool:
        """Check if the provider is enabled and configured."""
        return self._enabled

    @property
    def is_healthy(self) -> bool:
        """Check if the provider passed the last health check."""
        return self._health_status

    @abstractmethod
    async def send_notification(self, payload: NotificationPayload) -> NotificationResult:
        """
        Send a notification through this provider.

        Args:
            payload: The notification payload containing message details

        Returns:
            NotificationResult with delivery status and any error details

        Implementations should:
        - Handle rate limiting and return appropriate status
        - Validate payload before sending
        - Log attempts with sanitized URLs (no secrets)
        - Capture delivery confirmation from provider
        """
        pass

    @abstractmethod
    async def validate_config(self) -> bool:
        """
        Validate the provider configuration (webhook URL, API keys, etc.).

        Returns:
            True if configuration is valid and provider can send notifications

        This method should:
        - Check that required credentials are present
        - Validate URL formats
        - NOT make network calls (use health_check for that)
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Perform a health check to verify provider connectivity.

        Returns:
            True if the provider is reachable and functional

        This method should:
        - Make a lightweight call to verify connectivity
        - Update internal health status
        - Log failures with sanitized details
        """
        pass

    @abstractmethod
    def format_message(self, payload: NotificationPayload) -> Dict[str, Any]:
        """
        Format the notification payload for this provider's API.

        Args:
            payload: The notification payload to format

        Returns:
            Provider-specific message format (Slack blocks, Teams cards, etc.)
        """
        pass

    async def initialize(self) -> bool:
        """
        Initialize the provider, validating configuration and connectivity.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Validate configuration first
            if not await self.validate_config():
                logger.warning(f"{self._name} provider: Invalid configuration")
                self._enabled = False
                return False

            # Perform health check
            self._health_status = await self.health_check()
            self._last_health_check = datetime.utcnow()

            if self._health_status:
                self._enabled = True
                logger.info(f"{self._name} provider: Initialized successfully")
            else:
                self._enabled = False
                logger.warning(f"{self._name} provider: Health check failed")

            return self._health_status

        except Exception as e:
            logger.error(f"{self._name} provider: Initialization failed - {e}")
            self._enabled = False
            self._health_status = False
            return False

    def sanitize_url(self, url: str) -> str:
        """
        Sanitize a webhook URL for logging by masking sensitive parts.

        Args:
            url: The URL to sanitize

        Returns:
            Sanitized URL safe for logging
        """
        if not url:
            return "<not configured>"

        # Keep only the domain part visible for debugging
        if "hooks.slack.com" in url:
            return "https://hooks.slack.com/services/***"
        elif "outlook.office.com" in url:
            return "https://outlook.office.com/webhook/***"
        elif "events.pagerduty.com" in url:
            return "https://events.pagerduty.com/***"
        else:
            # Generic masking for unknown webhook URLs
            parts = url.split("/")
            if len(parts) > 3:
                return f"{parts[0]}//{parts[2]}/***"
            return "<webhook URL>"

    def __repr__(self) -> str:
        """String representation of the provider."""
        status = "enabled" if self._enabled else "disabled"
        health = "healthy" if self._health_status else "unhealthy"
        return f"<{self.__class__.__name__}(name={self._name}, {status}, {health})>"
