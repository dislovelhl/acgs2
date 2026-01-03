"""
Linear Integration Module

Provides GraphQL client and integration components for Linear.app
"""

from .client import LinearClient
from .state import (
    LinearStateConnectionError,
    LinearStateError,
    LinearStateLockError,
    LinearStateManager,
    get_state_manager,
    reset_state_manager,
)
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
    # State Management
    "LinearStateManager",
    "LinearStateError",
    "LinearStateConnectionError",
    "LinearStateLockError",
    "get_state_manager",
    "reset_state_manager",
    # Webhook Auth
    "LinearWebhookAuthError",
    "get_linear_webhook_handler",
    "is_linear_webhook_configured",
    "verify_linear_signature_sync",
    "verify_linear_webhook_signature",
    "verify_linear_webhook_signature_strict",
]
