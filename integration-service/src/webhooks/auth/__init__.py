"""
Webhook Authentication Framework for ACGS-2 Integration Service.

Provides authentication handlers, models, and utilities for verifying incoming
webhook requests and preparing outgoing webhook authentication. Supports multiple
authentication methods including API keys, HMAC signatures, and OAuth 2.0 bearer
tokens.
"""

from .api_key import ApiKeyAuthHandler
from .base import WebhookAuthHandler, WebhookAuthRegistry
from .exceptions import (
    InvalidApiKeyError,
    InvalidBearerTokenError,
    InvalidSignatureError,
    MissingAuthHeaderError,
    SignatureTimestampError,
    TokenExpiredError,
    WebhookAuthError,
)
from .factory import (
    create_api_key_handler,
    create_default_registry,
    create_hmac_handler,
    create_oauth_handler,
)
from .hmac import HmacAuthHandler
from .models import AuthResult, OAuthToken
from .oauth import OAuthBearerAuthHandler

__all__ = [
    # Base Classes
    "WebhookAuthHandler",
    "WebhookAuthRegistry",
    # Exceptions
    "WebhookAuthError",
    "InvalidSignatureError",
    "InvalidApiKeyError",
    "InvalidBearerTokenError",
    "TokenExpiredError",
    "SignatureTimestampError",
    "MissingAuthHeaderError",
    # Models
    "AuthResult",
    "OAuthToken",
    # Handlers
    "ApiKeyAuthHandler",
    "HmacAuthHandler",
    "OAuthBearerAuthHandler",
    # Factory Functions
    "create_api_key_handler",
    "create_hmac_handler",
    "create_oauth_handler",
    "create_default_registry",
]
