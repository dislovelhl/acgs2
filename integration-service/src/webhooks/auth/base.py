"""
Webhook authentication base classes for ACGS-2 Integration Service.

This module defines the abstract base class for webhook authentication handlers
and the registry for managing multiple authentication handlers. The handler
interface supports both incoming webhook verification and outgoing webhook
authentication.
"""

import abc
import logging
from typing import Dict, Optional

from ..models import WebhookAuthType
from .models import AuthResult

logger = logging.getLogger(__name__)


class WebhookAuthHandler(abc.ABC):
    """
    Abstract base class for webhook authentication handlers.

    Handlers can be used to:
    - Verify incoming webhook requests (requests received by our service)
    - Prepare authentication for outgoing webhook requests (requests we send)
    """

    @property
    @abc.abstractmethod
    def auth_type(self) -> WebhookAuthType:
        """Get the authentication type this handler supports."""
        pass

    @abc.abstractmethod
    async def verify_request(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> AuthResult:
        """
        Verify an incoming webhook request.

        Args:
            headers: Request headers (case-insensitive lookup)
            body: Raw request body bytes
            method: HTTP method
            url: Request URL (optional)

        Returns:
            AuthResult indicating if the request is authenticated
        """
        pass

    @abc.abstractmethod
    async def prepare_headers(
        self,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Prepare authentication headers for an outgoing request.

        Args:
            headers: Existing headers to augment
            body: Request body bytes
            method: HTTP method
            url: Request URL (optional)

        Returns:
            Headers dict with authentication headers added
        """
        pass


class WebhookAuthRegistry:
    """
    Registry for webhook authentication handlers.

    Provides a centralized way to manage and lookup authentication handlers
    by type for both incoming and outgoing webhook authentication.
    """

    def __init__(self):
        """Initialize the registry."""
        self._handlers: Dict[WebhookAuthType, WebhookAuthHandler] = {}

    def register(self, handler: WebhookAuthHandler) -> None:
        """Register an authentication handler."""
        self._handlers[handler.auth_type] = handler
        logger.debug(f"Registered auth handler for {handler.auth_type.value}")

    def unregister(self, auth_type: WebhookAuthType) -> Optional[WebhookAuthHandler]:
        """Unregister and return an authentication handler."""
        return self._handlers.pop(auth_type, None)

    def get(self, auth_type: WebhookAuthType) -> Optional[WebhookAuthHandler]:
        """Get an authentication handler by type."""
        return self._handlers.get(auth_type)

    def get_all(self) -> Dict[WebhookAuthType, WebhookAuthHandler]:
        """Get all registered handlers."""
        return dict(self._handlers)

    async def verify_request(
        self,
        auth_type: WebhookAuthType,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> AuthResult:
        """
        Verify a request using the appropriate handler.

        Args:
            auth_type: Type of authentication to use
            headers: Request headers
            body: Request body bytes
            method: HTTP method
            url: Request URL

        Returns:
            AuthResult from the handler
        """
        if auth_type == WebhookAuthType.NONE:
            return AuthResult.success(auth_type=auth_type)

        handler = self._handlers.get(auth_type)
        if handler is None:
            return AuthResult.failure(
                auth_type=auth_type,
                error_code="NO_HANDLER",
                error_message=f"No handler registered for {auth_type.value}",
            )

        return await handler.verify_request(headers, body, method, url)

    async def prepare_headers(
        self,
        auth_type: WebhookAuthType,
        headers: Dict[str, str],
        body: bytes,
        method: str = "POST",
        url: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Prepare authentication headers using the appropriate handler.

        Args:
            auth_type: Type of authentication to use
            headers: Existing headers
            body: Request body bytes
            method: HTTP method
            url: Request URL

        Returns:
            Headers dict with authentication added
        """
        if auth_type == WebhookAuthType.NONE:
            return dict(headers)

        handler = self._handlers.get(auth_type)
        if handler is None:
            logger.warning(f"No handler for {auth_type.value}, returning headers unchanged")
            return dict(headers)

        return await handler.prepare_headers(headers, body, method, url)


__all__ = [
    "WebhookAuthHandler",
    "WebhookAuthRegistry",
]
