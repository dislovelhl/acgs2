"""
Linear Integration Module

Provides GraphQL client and integration components for Linear.app
"""

from .client import LinearClient
from .webhook_auth import (
    LinearWebhookAuthError,
    get_linear_webhook_handler,
    is_linear_webhook_configured,
    verify_linear_signature_sync,
    verify_linear_webhook_signature,
    verify_linear_webhook_signature_strict,
)

__all__ = [
    "LinearClient",
    "LinearWebhookAuthError",
    "get_linear_webhook_handler",
    "is_linear_webhook_configured",
    "verify_linear_signature_sync",
    "verify_linear_webhook_signature",
    "verify_linear_webhook_signature_strict",
]
