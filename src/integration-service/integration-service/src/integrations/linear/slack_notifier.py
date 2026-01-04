"""
Slack Notification Service for Linear Integration

Provides async Slack notifications for Linear issue updates using slack-sdk.
Sends rich formatted messages to Slack channels when Linear issues are created,
updated, or have their status changed.

Features:
- Async/await support for FastAPI integration
- Slack Block Kit for rich message formatting
- Rate limiting (1 message per second per Slack guidelines)
- Graceful degradation when Slack is not configured
- Comprehensive error handling and logging
- Deduplication to prevent duplicate notifications

Architecture:
- Uses slack-sdk WebClient for Slack API access
- Integrates with SlackConfig for configuration
- Redis-backed deduplication via LinearDeduplicationManager
- Singleton pattern for instance management
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ...config import SlackConfig, get_slack_config
from .deduplication import SYNC_SOURCE_SLACK, LinearDeduplicationManager, get_dedup_manager

logger = logging.getLogger(__name__)

# Rate limiting: Slack recommends max 1 message per second
SLACK_RATE_LIMIT_SECONDS = 1.0


class SlackNotifierError(Exception):
    """Base exception for Slack notifier errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SlackAuthenticationError(SlackNotifierError):
    """Raised when Slack authentication fails."""
    pass


class SlackRateLimitError(SlackNotifierError):
    """Raised when Slack rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, details)
        self.retry_after = retry_after


class SlackChannelNotFoundError(SlackNotifierError):
    """Raised when specified Slack channel is not found."""
    pass


class SlackNotConfiguredError(SlackNotifierError):
    """Raised when Slack integration is not configured."""
    pass


class SlackNotifier:
    """
    Manages Slack notifications for Linear issue updates.

    Sends formatted messages to Slack channels using Block Kit when Linear
    issues are created, updated, or have their status changed.

    Usage:
        notifier = SlackNotifier()
        async with notifier:
            await notifier.post_issue_created(
                issue_id="issue-123",
                title="Bug in authentication",
                description="Users unable to log in",
                assignee="Alice",
                status="In Progress",
                url="https://linear.app/issue/123"
            )
    """

    def __init__(
        self,
        config: Optional[SlackConfig] = None,
        dedup_manager: Optional[LinearDeduplicationManager] = None,
    ):
        """
        Initialize the Slack notifier.

        Args:
            config: Slack configuration. If not provided, uses get_slack_config()
            dedup_manager: Deduplication manager. If not provided, uses get_dedup_manager()
        """
        self._config = config or get_slack_config()
        self._dedup_manager = dedup_manager or get_dedup_manager()
        self._client: Optional[AsyncWebClient] = None
        self._last_send_time: float = 0.0
        self._rate_limit_lock = asyncio.Lock()

        # Check if Slack is configured
        if not self._config.is_configured:
            logger.warning(
                "Slack integration not configured. "
                "Notifications will be skipped. "
                "Set SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET to enable."
            )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> AsyncWebClient:
        """
        Ensure Slack client is initialized.

        Returns:
            Initialized AsyncWebClient

        Raises:
            SlackNotConfiguredError: If Slack is not configured
        """
        if not self._config.is_configured:
            raise SlackNotConfiguredError(
                "Slack integration not configured. "
                "Please set SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET."
            )

        if self._client is None:
            if not self._config.slack_bot_token:
                raise SlackNotConfiguredError("SLACK_BOT_TOKEN is required")

            token = self._config.slack_bot_token.get_secret_value()

            self._client = AsyncWebClient(
                token=token,
                timeout=self._config.slack_timeout_seconds,
            )
            logger.info("Slack WebClient initialized")

        return self._client

    async def close(self):
        """Close the Slack client and cleanup resources."""
        if self._client:
            # AsyncWebClient doesn't require explicit cleanup
            self._client = None
            logger.info("Slack WebClient closed")

    async def _apply_rate_limit(self):
        """
        Apply rate limiting to respect Slack's 1 message per second guideline.

        Uses an async lock to ensure thread-safe rate limiting.
        """
        async with self._rate_limit_lock:
            current_time = asyncio.get_event_loop().time()
            time_since_last_send = current_time - self._last_send_time

            if time_since_last_send < SLACK_RATE_LIMIT_SECONDS:
                sleep_time = SLACK_RATE_LIMIT_SECONDS - time_since_last_send
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)

            self._last_send_time = asyncio.get_event_loop().time()

    @retry(
        retry=retry_if_exception_type(SlackApiError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _send_message(
        self,
        channel: str,
        blocks: List[Dict[str, Any]],
        text: str,
    ) -> Dict[str, Any]:
        """
        Send a message to Slack with retry logic.

        Args:
            channel: Slack channel ID or name
            blocks: Slack Block Kit blocks
            text: Fallback text for notifications

        Returns:
            Slack API response

        Raises:
            SlackAuthenticationError: If authentication fails
            SlackRateLimitError: If rate limit is exceeded
            SlackChannelNotFoundError: If channel is not found
            SlackNotifierError: For other API errors
        """
        client = await self._ensure_client()

        # Apply rate limiting
        await self._apply_rate_limit()

        try:
            response = await client.chat_postMessage(
                channel=channel,
                blocks=blocks,
                text=text,
            )

            logger.info(
                "Slack message sent successfully",
                extra={
                    "channel": channel,
                    "timestamp": response.get("ts"),
                },
            )

            return response

        except SlackApiError as e:
            error_code = e.response.get("error", "unknown")

            # Handle specific error types
            if error_code in ("invalid_auth", "token_revoked", "not_authed"):
                raise SlackAuthenticationError(
                    f"Slack authentication failed: {error_code}",
                    details={"error": error_code, "response": e.response},
                ) from e
            elif error_code == "rate_limited":
                retry_after = int(e.response.headers.get("Retry-After", 60))
                raise SlackRateLimitError(
                    "Slack rate limit exceeded",
                    retry_after=retry_after,
                    details={"retry_after": retry_after, "response": e.response},
                ) from e
            elif error_code in ("channel_not_found", "is_archived"):
                raise SlackChannelNotFoundError(
                    f"Slack channel not found or archived: {channel}",
                    details={
                        "channel": channel,
                        "error": error_code,
                        "response": e.response,
                    },
                ) from e
            else:
                raise SlackNotifierError(
                    f"Slack API error: {error_code}",
                    details={"error": error_code, "response": e.response},
                ) from e

    def _build_issue_created_blocks(
        self,
        issue_id: str,
        title: str,
        description: Optional[str],
        assignee: Optional[str],
        status: Optional[str],
        priority: Optional[str],
        url: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Build Slack Block Kit blocks for issue created notification.

        Args:
            issue_id: Linear issue ID
            title: Issue title
            description: Issue description
            assignee: Assignee name
            status: Issue status
            priority: Issue priority
            url: Linear issue URL

        Returns:
            List of Slack Block Kit blocks
        """
        # Priority to emoji mapping
        priority_emoji = {
            "urgent": ":red_circle:",
            "high": ":large_orange_circle:",
            "medium": ":large_blue_circle:",
            "low": ":white_circle:",
        }

        priority_key = priority.lower() if priority else ""
        emoji = priority_emoji.get(priority_key, ":white_circle:")

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} New Linear Issue Created",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*",
                },
            },
        ]

        # Add description if provided
        if description:
            # Truncate long descriptions
            max_len = 500
            truncated_desc = (
                description[:max_len] + "..."
                if len(description) > max_len
                else description
            )
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": truncated_desc,
                },
            })

        # Add metadata
        metadata_parts = [f"*Issue ID:* `{issue_id}`"]
        if status:
            metadata_parts.append(f"*Status:* {status}")
        if priority:
            metadata_parts.append(f"*Priority:* {priority}")
        if assignee:
            metadata_parts.append(f"*Assignee:* {assignee}")

        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": " | ".join(metadata_parts),
                }
            ],
        })

        # Add link to issue
        if url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Linear",
                            "emoji": True,
                        },
                        "url": url,
                        "style": "primary",
                    }
                ],
            })

        return blocks

    def _build_status_changed_blocks(
        self,
        issue_id: str,
        title: str,
        old_status: str,
        new_status: str,
        assignee: Optional[str],
        url: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Build Slack Block Kit blocks for status changed notification.

        Args:
            issue_id: Linear issue ID
            title: Issue title
            old_status: Previous status
            new_status: New status
            assignee: Assignee name
            url: Linear issue URL

        Returns:
            List of Slack Block Kit blocks
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":arrows_counterclockwise: Issue Status Changed",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*\n\n`{old_status}` → `{new_status}`",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*Issue ID:* `{issue_id}`"
                            + (f" | *Assignee:* {assignee}" if assignee else "")
                        ),
                    }
                ],
            },
        ]

        # Add link to issue
        if url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Linear",
                            "emoji": True,
                        },
                        "url": url,
                    }
                ],
            })

        return blocks

    def _build_comment_added_blocks(
        self,
        issue_id: str,
        title: str,
        comment_author: str,
        comment_body: str,
        url: Optional[str],
    ) -> List[Dict[str, Any]]:
        """
        Build Slack Block Kit blocks for comment added notification.

        Args:
            issue_id: Linear issue ID
            title: Issue title
            comment_author: Comment author name
            comment_body: Comment text
            url: Linear issue URL

        Returns:
            List of Slack Block Kit blocks
        """
        # Truncate long comments
        max_comment_len = 300
        truncated_comment = (
            comment_body[:max_comment_len] + "..."
            if len(comment_body) > max_comment_len
            else comment_body
        )

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":speech_balloon: New Comment Added",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{title}*",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"_{comment_author} commented:_\n\n{truncated_comment}",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Issue ID:* `{issue_id}`",
                    }
                ],
            },
        ]

        # Add link to issue
        if url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View in Linear",
                            "emoji": True,
                        },
                        "url": url,
                    }
                ],
            })

        return blocks

    async def post_issue_created(
        self,
        issue_id: str,
        title: str,
        description: Optional[str] = None,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        url: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> bool:
        """
        Post a notification when a Linear issue is created.

        Args:
            issue_id: Linear issue ID
            title: Issue title
            description: Issue description
            assignee: Assignee name
            status: Issue status
            priority: Issue priority (urgent, high, medium, low)
            url: Linear issue URL
            channel: Slack channel ID or name (uses default if not provided)

        Returns:
            True if notification was sent successfully, False if Slack not configured

        Raises:
            SlackNotifierError: If notification fails
        """
        # Skip if Slack not configured
        if not self._config.is_configured:
            logger.info(
                f"Slack not configured, skipping issue created notification "
                f"for {issue_id}"
            )
            return False

        # Check for duplicate notification
        event_id = f"slack_issue_created_{issue_id}"
        if await self._dedup_manager.is_duplicate(event_id):
            logger.info(
                f"Duplicate Slack notification detected for issue created: "
                f"{issue_id}"
            )
            return False

        # Use default channel if not specified
        target_channel = channel or self._config.slack_default_channel
        if not target_channel:
            logger.warning("No Slack channel specified and no default channel configured")
            return False

        try:
            blocks = self._build_issue_created_blocks(
                issue_id=issue_id,
                title=title,
                description=description,
                assignee=assignee,
                status=status,
                priority=priority,
                url=url,
            )

            fallback_text = f"New Linear issue created: {title}"

            await self._send_message(
                channel=target_channel,
                blocks=blocks,
                text=fallback_text,
            )

            # Mark as processed to prevent duplicates
            await self._dedup_manager.mark_processed(event_id, SYNC_SOURCE_SLACK)

            logger.info(
                "Issue created notification sent to Slack",
                extra={
                    "issue_id": issue_id,
                    "channel": target_channel,
                },
            )

            return True

        except SlackNotConfiguredError:
            logger.warning(f"Slack not configured, skipping notification for {issue_id}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to send issue created notification to Slack: {e}",
                exc_info=True,
                extra={
                    "issue_id": issue_id,
                    "error": str(e),
                },
            )
            raise

    async def post_status_changed(
        self,
        issue_id: str,
        title: str,
        old_status: str,
        new_status: str,
        assignee: Optional[str] = None,
        url: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> bool:
        """
        Post a notification when a Linear issue status changes.

        Args:
            issue_id: Linear issue ID
            title: Issue title
            old_status: Previous status
            new_status: New status
            assignee: Assignee name
            url: Linear issue URL
            channel: Slack channel ID or name (uses default if not provided)

        Returns:
            True if notification was sent successfully, False if Slack not configured

        Raises:
            SlackNotifierError: If notification fails
        """
        # Skip if Slack not configured
        if not self._config.is_configured:
            logger.info(
                f"Slack not configured, skipping status changed notification "
                f"for {issue_id}"
            )
            return False

        # Check for duplicate notification
        timestamp = datetime.now(timezone.utc).timestamp()
        event_id = f"slack_status_changed_{issue_id}_{new_status}_{timestamp}"
        if await self._dedup_manager.is_duplicate(event_id):
            logger.info(
                f"Duplicate Slack notification detected for status change: "
                f"{issue_id}"
            )
            return False

        # Use default channel if not specified
        target_channel = channel or self._config.slack_default_channel
        if not target_channel:
            logger.warning("No Slack channel specified and no default channel configured")
            return False

        try:
            blocks = self._build_status_changed_blocks(
                issue_id=issue_id,
                title=title,
                old_status=old_status,
                new_status=new_status,
                assignee=assignee,
                url=url,
            )

            fallback_text = f"Linear issue status changed: {title} ({old_status} → {new_status})"

            await self._send_message(
                channel=target_channel,
                blocks=blocks,
                text=fallback_text,
            )

            # Mark as processed to prevent duplicates
            await self._dedup_manager.mark_processed(event_id, SYNC_SOURCE_SLACK)

            logger.info(
                "Status changed notification sent to Slack",
                extra={
                    "issue_id": issue_id,
                    "old_status": old_status,
                    "new_status": new_status,
                    "channel": target_channel,
                },
            )

            return True

        except SlackNotConfiguredError:
            logger.warning(f"Slack not configured, skipping notification for {issue_id}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to send status changed notification to Slack: {e}",
                exc_info=True,
                extra={
                    "issue_id": issue_id,
                    "error": str(e),
                },
            )
            raise

    async def post_comment_added(
        self,
        issue_id: str,
        title: str,
        comment_author: str,
        comment_body: str,
        url: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> bool:
        """
        Post a notification when a comment is added to a Linear issue.

        Args:
            issue_id: Linear issue ID
            title: Issue title
            comment_author: Comment author name
            comment_body: Comment text
            url: Linear issue URL
            channel: Slack channel ID or name (uses default if not provided)

        Returns:
            True if notification was sent successfully, False if Slack not configured

        Raises:
            SlackNotifierError: If notification fails
        """
        # Skip if Slack not configured
        if not self._config.is_configured:
            logger.info(
                f"Slack not configured, skipping comment added notification "
                f"for {issue_id}"
            )
            return False

        # Check for duplicate notification (using comment body hash)
        import hashlib

        comment_hash = hashlib.md5(
            comment_body.encode(), usedforsecurity=False
        ).hexdigest()[:8]
        event_id = f"slack_comment_added_{issue_id}_{comment_hash}"

        if await self._dedup_manager.is_duplicate(event_id):
            logger.info(
                f"Duplicate Slack notification detected for comment: {issue_id}"
            )
            return False

        # Use default channel if not specified
        target_channel = channel or self._config.slack_default_channel
        if not target_channel:
            logger.warning("No Slack channel specified and no default channel configured")
            return False

        try:
            blocks = self._build_comment_added_blocks(
                issue_id=issue_id,
                title=title,
                comment_author=comment_author,
                comment_body=comment_body,
                url=url,
            )

            fallback_text = f"New comment on Linear issue: {title}"

            await self._send_message(
                channel=target_channel,
                blocks=blocks,
                text=fallback_text,
            )

            # Mark as processed to prevent duplicates
            await self._dedup_manager.mark_processed(event_id, SYNC_SOURCE_SLACK)

            logger.info(
                "Comment added notification sent to Slack",
                extra={
                    "issue_id": issue_id,
                    "author": comment_author,
                    "channel": target_channel,
                },
            )

            return True

        except SlackNotConfiguredError:
            logger.warning(f"Slack not configured, skipping notification for {issue_id}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to send comment added notification to Slack: {e}",
                exc_info=True,
                extra={
                    "issue_id": issue_id,
                    "error": str(e),
                },
            )
            raise


# Singleton instance management
_slack_notifier_instance: Optional[SlackNotifier] = None


def get_slack_notifier() -> SlackNotifier:
    """
    Get the singleton SlackNotifier instance.

    Returns:
        Singleton SlackNotifier instance
    """
    global _slack_notifier_instance
    if _slack_notifier_instance is None:
        _slack_notifier_instance = SlackNotifier()
        logger.debug("SlackNotifier singleton instance created")
    return _slack_notifier_instance


def reset_slack_notifier():
    """
    Reset the singleton SlackNotifier instance.

    Useful for testing to ensure a clean state.
    """
    global _slack_notifier_instance
    _slack_notifier_instance = None
    logger.debug("SlackNotifier singleton instance reset")
