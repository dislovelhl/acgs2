"""
Factory functions for webhook authentication handlers.

This module provides convenient factory functions for creating pre-configured
authentication handlers and registries. These functions simplify the creation
of authentication handlers with common configurations.
"""

from typing import Dict, List, Optional

from pydantic import SecretStr

from .api_key import ApiKeyAuthHandler
from .base import WebhookAuthRegistry
from .hmac import HmacAuthHandler
from .oauth import OAuthBearerAuthHandler


def create_api_key_handler(
    valid_keys: Optional[Dict[str, str]] = None,
    header_name: str = "X-API-Key",
    api_key: Optional[SecretStr] = None,
) -> ApiKeyAuthHandler:
    """
    Create an API key authentication handler.

    Args:
        valid_keys: Dict mapping API key values to principals
        header_name: Header name for API key
        api_key: API key for outgoing requests

    Returns:
        Configured ApiKeyAuthHandler
    """
    return ApiKeyAuthHandler(
        valid_keys=valid_keys,
        header_name=header_name,
        api_key=api_key,
    )


def create_hmac_handler(
    secret: SecretStr,
    signature_header: str = "X-Webhook-Signature",
    timestamp_header: str = "X-Webhook-Timestamp",
    algorithm: str = "sha256",
    timestamp_tolerance_seconds: int = 300,
) -> HmacAuthHandler:
    """
    Create an HMAC signature authentication handler.

    Args:
        secret: HMAC secret key
        signature_header: Header name for signature
        timestamp_header: Header name for timestamp
        algorithm: Hash algorithm (sha256 or sha512)
        timestamp_tolerance_seconds: Maximum request age

    Returns:
        Configured HmacAuthHandler
    """
    return HmacAuthHandler(
        secret=secret,
        signature_header=signature_header,
        timestamp_header=timestamp_header,
        algorithm=algorithm,
        timestamp_tolerance_seconds=timestamp_tolerance_seconds,
    )


def create_oauth_handler(
    token_info_url: Optional[str] = None,
    required_scopes: Optional[List[str]] = None,
    access_token: Optional[SecretStr] = None,
    refresh_token: Optional[SecretStr] = None,
    client_id: Optional[str] = None,
    client_secret: Optional[SecretStr] = None,
    token_url: Optional[str] = None,
) -> OAuthBearerAuthHandler:
    """
    Create an OAuth bearer token authentication handler.

    Args:
        token_info_url: URL to validate tokens
        required_scopes: Required scopes for authorization
        access_token: Access token for outgoing requests
        refresh_token: Refresh token for refresh flow
        client_id: OAuth client ID
        client_secret: OAuth client secret
        token_url: Token endpoint URL

    Returns:
        Configured OAuthBearerAuthHandler
    """
    return OAuthBearerAuthHandler(
        token_info_url=token_info_url,
        required_scopes=required_scopes,
        access_token=access_token,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_url=token_url,
    )


def create_default_registry() -> WebhookAuthRegistry:
    """
    Create a registry with default handlers.

    Returns:
        WebhookAuthRegistry with common handlers registered
    """
    registry = WebhookAuthRegistry()
    # Note: Handlers need to be configured with secrets before use
    # This just provides the registry structure
    return registry


__all__ = [
    "create_api_key_handler",
    "create_hmac_handler",
    "create_oauth_handler",
    "create_default_registry",
]
