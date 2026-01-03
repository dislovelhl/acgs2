"""
Base notification interfaces and utilities
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class NotificationMessage:
    """Base notification message structure"""

    title: str
    message: str
    priority: str
    request_id: str
    approval_url: str
    tenant_id: str
    metadata: Dict[str, Any]


class NotificationProvider(ABC):
    """Base class for notification providers"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.retry_attempts = config.get("retry_attempts", 3)
        self.retry_delay = config.get("retry_delay", 1.0)

    @abstractmethod
    async def send_notification(self, message: NotificationMessage) -> bool:
        """Send a notification. Returns True if successful."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the provider is properly configured."""
        pass

    async def _retry_with_backoff(self, operation, *args, **kwargs) -> bool:
        """Retry an operation with exponential backoff."""
        for attempt in range(self.retry_attempts):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                if attempt == self.retry_attempts - 1:
                    logger.error(f"Operation failed after {self.retry_attempts} attempts: {e}")
                    return False

                delay = self.retry_delay * (2**attempt)
                logger.warning(
                    f"Operation failed (attempt {attempt + 1}/{self.retry_attempts}), retrying in {delay}s: {e}"
                )
                await asyncio.sleep(delay)

        return False


class NotificationManager:
    """Manages multiple notification providers"""

    def __init__(self):
        self.providers: Dict[str, NotificationProvider] = {}

    def register_provider(self, name: str, provider: NotificationProvider):
        """Register a notification provider"""
        self.providers[name] = provider
        logger.info(f"Registered notification provider: {name}")

    async def send_notifications(
        self, message: NotificationMessage, providers: Optional[list] = None
    ) -> Dict[str, bool]:
        """
        Send notifications via specified providers or all configured providers.
        Returns dict of provider_name -> success status.
        """
        if providers is None:
            providers = list(self.providers.keys())

        results = {}
        for provider_name in providers:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                if provider.is_configured():
                    success = await provider.send_notification(message)
                    results[provider_name] = success
                    status = "succeeded" if success else "failed"
                    logger.info(
                        f"Notification via {provider_name} {status} for request {message.request_id}"
                    )
                else:
                    logger.warning(f"Provider {provider_name} not configured, skipping")
                    results[provider_name] = False
            else:
                logger.warning(f"Unknown provider: {provider_name}")
                results[provider_name] = False

        return results

    def get_configured_providers(self) -> list:
        """Get list of properly configured providers"""
        return [name for name, provider in self.providers.items() if provider.is_configured()]


# Global notification manager instance
notification_manager = NotificationManager()
