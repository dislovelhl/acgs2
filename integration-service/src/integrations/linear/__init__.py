"""
Linear Integration Module

Provides GraphQL client and integration components for Linear.app
"""

from .client import LinearClient
from .conflict_resolution import (
    ConflictResolutionError,
    ConflictResolutionManager,
    ConflictTimestampError,
    get_conflict_manager,
    reset_conflict_manager,
)
from .deduplication import (
    DeduplicationError,
    DuplicateEventError,
    LinearDeduplicationManager,
    SyncLoopDetectedError,
    get_dedup_manager,
    reset_dedup_manager,
)
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
    # Deduplication
    "LinearDeduplicationManager",
    "DeduplicationError",
    "DuplicateEventError",
    "SyncLoopDetectedError",
    "get_dedup_manager",
    "reset_dedup_manager",
    # Conflict Resolution
    "ConflictResolutionManager",
    "ConflictResolutionError",
    "ConflictTimestampError",
    "get_conflict_manager",
    "reset_conflict_manager",
    # Webhook Auth
    "LinearWebhookAuthError",
    "get_linear_webhook_handler",
    "is_linear_webhook_configured",
    "verify_linear_signature_sync",
    "verify_linear_webhook_signature",
    "verify_linear_webhook_signature_strict",
]
