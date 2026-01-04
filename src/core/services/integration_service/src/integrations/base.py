"""Constitutional Hash: cdd01ef066bc6cf2
Base integration adapter class
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class IntegrationAdapter(ABC):
    """
    Base class for all third-party integrations.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client = httpx.AsyncClient(timeout=30.0)

    @abstractmethod
    async def authenticate(self) -> bool:
        """Validate credentials and authenticate with the provider."""
        pass

    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate integration configuration."""
        pass

    @abstractmethod
    async def send_event(self, event_data: Dict[str, Any]) -> bool:
        """Send a governance event to the third-party system."""
        pass

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _post_with_retry(self, url: str, **kwargs) -> httpx.Response:
        """Internal helper for HTTP POST with retry logic."""
        response = await self.client.post(url, **kwargs)
        response.raise_for_status()
        return response

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
