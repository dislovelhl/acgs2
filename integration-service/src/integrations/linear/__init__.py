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
from .github_sync import (
    GitHubAuthenticationError,
    GitHubNotFoundError,
    GitHubRateLimitError,
    GitHubSyncError,
    GitHubSyncManager,
    get_github_sync_manager,
    reset_github_sync_manager,
)
from .gitlab_sync import (
    GitLabAuthenticationError,
    GitLabNotFoundError,
    GitLabRateLimitError,
    GitLabSyncError,
    GitLabSyncManager,
    get_gitlab_sync_manager,
    reset_gitlab_sync_manager,
)
from .slack_notifier import (
    SlackAuthenticationError,
    SlackChannelNotFoundError,
    SlackNotConfiguredError,
    SlackNotifier,
    SlackNotifierError,
    SlackRateLimitError,
    get_slack_notifier,
    reset_slack_notifier,
)
from .slack_templates import (
    build_comment_added_template,
    build_issue_assigned_template,
    build_issue_created_template,
    build_priority_changed_template,
    build_status_changed_template,
    get_comment_added_fallback,
    get_issue_assigned_fallback,
    get_issue_created_fallback,
    get_priority_changed_fallback,
    get_status_changed_fallback,
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
    # GitHub Sync
    "GitHubSyncManager",
    "GitHubSyncError",
    "GitHubAuthenticationError",
    "GitHubRateLimitError",
    "GitHubNotFoundError",
    "get_github_sync_manager",
    "reset_github_sync_manager",
    # GitLab Sync
    "GitLabSyncManager",
    "GitLabSyncError",
    "GitLabAuthenticationError",
    "GitLabRateLimitError",
    "GitLabNotFoundError",
    "get_gitlab_sync_manager",
    "reset_gitlab_sync_manager",
    # Slack Notifier
    "SlackNotifier",
    "SlackNotifierError",
    "SlackAuthenticationError",
    "SlackRateLimitError",
    "SlackChannelNotFoundError",
    "SlackNotConfiguredError",
    "get_slack_notifier",
    "reset_slack_notifier",
    # Slack Templates
    "build_issue_created_template",
    "build_status_changed_template",
    "build_comment_added_template",
    "build_issue_assigned_template",
    "build_priority_changed_template",
    "get_issue_created_fallback",
    "get_status_changed_fallback",
    "get_comment_added_fallback",
    "get_issue_assigned_fallback",
    "get_priority_changed_fallback",
    # Webhook Auth
    "LinearWebhookAuthError",
    "get_linear_webhook_handler",
    "is_linear_webhook_configured",
    "verify_linear_signature_sync",
    "verify_linear_webhook_signature",
    "verify_linear_webhook_signature_strict",
]
