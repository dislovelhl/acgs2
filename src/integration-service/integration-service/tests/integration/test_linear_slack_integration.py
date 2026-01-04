"""
Integration Tests for Linear → Slack Notification Flow

Tests cover the complete notification flow from Linear webhook to Slack:
- Linear webhook → Slack notification for issue creation
- Linear webhook → Slack notification for status changes
- Linear webhook → Slack notification for comments
- Deduplication logic prevents duplicate notifications
- Error handling (Slack not configured, auth failures, rate limits)
- Block Kit message formatting verification

These are integration tests with mocked external APIs (Linear webhooks, Slack API).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

from src.integrations.linear.deduplication import LinearDeduplicationManager
from src.integrations.linear.models import IssueEvent, LinearWebhookPayload
from src.integrations.linear.slack_notifier import (
    SlackAuthenticationError,
    SlackChannelNotFoundError,
    SlackNotConfiguredError,
    SlackNotifier,
    SlackRateLimitError,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_slack_config():
    """Create mock Slack configuration."""
    config = MagicMock()
    config.slack_bot_token = SecretStr("xoxb-test-token-12345")
    config.slack_signing_secret = SecretStr("test-signing-secret")
    config.slack_default_channel = "C123456"
    config.slack_timeout_seconds = 30.0
    config.is_configured = True
    return config


@pytest.fixture
def unconfigured_slack_config():
    """Create unconfigured Slack configuration."""
    config = MagicMock()
    config.slack_bot_token = None
    config.slack_signing_secret = None
    config.slack_default_channel = None
    config.slack_timeout_seconds = 30.0
    config.is_configured = False
    return config


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client for state tracking."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.setex = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.exists = AsyncMock(return_value=0)
    redis.lpush = AsyncMock(return_value=1)
    redis.lrange = AsyncMock(return_value=[])
    redis.expire = AsyncMock(return_value=True)
    redis.ping = AsyncMock(return_value=True)
    redis.close = AsyncMock()
    return redis


@pytest.fixture
async def mock_dedup_manager(mock_redis_client):
    """Create mock deduplication manager."""
    manager = MagicMock(spec=LinearDeduplicationManager)
    manager._redis = mock_redis_client
    manager._initialized = True

    manager.connect = AsyncMock()
    manager.close = AsyncMock()
    manager.is_duplicate = AsyncMock(return_value=False)
    manager.mark_processed = AsyncMock()
    manager.should_process_event = AsyncMock(return_value=True)
    manager.record_sync = AsyncMock()

    return manager


@pytest.fixture
def mock_slack_client():
    """Create mock Slack AsyncWebClient."""
    client = MagicMock()
    client.chat_postMessage = AsyncMock(
        return_value={"ok": True, "ts": "1234567890.123456"}
    )
    return client


@pytest.fixture
def sample_linear_issue():
    """Create sample Linear issue data."""
    return {
        "id": "linear-issue-123",
        "identifier": "ENG-123",
        "title": "Test Linear Issue",
        "description": "This is a test issue from Linear",
        "priority": 2,
        "url": "https://linear.app/test/issue/ENG-123",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "updatedAt": "2024-01-02T00:00:00.000Z",
        "state": {
            "id": "state-123",
            "name": "In Progress",
            "type": "started",
        },
        "assignee": {
            "id": "user-123",
            "name": "Test User",
            "email": "test@example.com",
        },
        "team": {
            "id": "team-123",
            "name": "Engineering",
            "key": "ENG",
        },
        "labels": {
            "nodes": [
                {"id": "label-1", "name": "bug"},
                {"id": "label-2", "name": "priority-high"},
            ]
        },
    }


@pytest.fixture
def sample_issue_created_webhook(sample_linear_issue):
    """Create sample Linear webhook payload for issue creation."""
    return {
        "action": "create",
        "type": "Issue",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "organizationId": "org-123",
        "webhookId": "webhook-456",
        "url": "https://linear.app/test/issue/ENG-123",
        "data": sample_linear_issue,
    }


@pytest.fixture
def sample_status_change_webhook(sample_linear_issue):
    """Create sample Linear webhook payload for status change."""
    return {
        "action": "update",
        "type": "Issue",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "organizationId": "org-123",
        "webhookId": "webhook-789",
        "url": "https://linear.app/test/issue/ENG-123",
        "data": sample_linear_issue,
        "updatedFrom": {
            "state": {
                "id": "state-old-123",
                "name": "Todo",
                "type": "unstarted",
            }
        },
    }


@pytest.fixture
def sample_comment_webhook():
    """Create sample Linear webhook payload for comment."""
    return {
        "action": "create",
        "type": "Comment",
        "createdAt": "2024-01-01T00:00:00.000Z",
        "organizationId": "org-123",
        "webhookId": "webhook-comment-123",
        "url": "https://linear.app/test/issue/ENG-123#comment-456",
        "data": {
            "id": "comment-456",
            "body": "This is a test comment on the issue",
            "createdAt": "2024-01-01T00:00:00.000Z",
            "updatedAt": "2024-01-01T00:00:00.000Z",
            "user": {
                "id": "user-789",
                "name": "Comment Author",
                "email": "author@example.com",
            },
            "issue": {
                "id": "linear-issue-123",
                "identifier": "ENG-123",
                "title": "Test Linear Issue",
            },
        },
    }


@pytest.fixture
async def slack_notifier(mock_slack_config, mock_dedup_manager):
    """Create SlackNotifier instance for testing."""
    return SlackNotifier(config=mock_slack_config, dedup_manager=mock_dedup_manager)


# ============================================================================
# Integration Tests: Linear Webhook → Slack Notification Flow
# ============================================================================


@pytest.mark.asyncio
async def test_linear_issue_created_triggers_slack_notification(
    slack_notifier, mock_slack_client, sample_issue_created_webhook
):
    """Test that Linear issue creation webhook triggers Slack notification."""
    # Setup
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            issue_data = sample_issue_created_webhook["data"]

            # Send issue created notification
            await slack_notifier.post_issue_created(
                issue_id=issue_data["id"],
                title=issue_data["title"],
                description=issue_data.get("description", ""),
                assignee=issue_data.get("assignee", {}).get("name"),
                status=issue_data["state"]["name"],
                priority=issue_data.get("priority"),
                url=issue_data["url"],
            )

            # Verify Slack notification was sent
            mock_slack_client.chat_postMessage.assert_called_once()
            call_args = mock_slack_client.chat_postMessage.call_args

            # Verify channel
            assert call_args.kwargs["channel"] == "C123456"

            # Verify blocks are present (Block Kit formatting)
            assert "blocks" in call_args.kwargs
            blocks = call_args.kwargs["blocks"]
            assert len(blocks) > 0

            # Verify fallback text is present
            assert "text" in call_args.kwargs


@pytest.mark.asyncio
async def test_linear_status_change_triggers_slack_notification(
    slack_notifier, mock_slack_client, sample_status_change_webhook
):
    """Test that Linear status change webhook triggers Slack notification."""
    # Setup
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            issue_data = sample_status_change_webhook["data"]
            old_status = sample_status_change_webhook["updatedFrom"]["state"]["name"]
            new_status = issue_data["state"]["name"]

            # Send status changed notification
            await slack_notifier.post_status_changed(
                issue_id=issue_data["id"],
                title=issue_data["title"],
                old_status=old_status,
                new_status=new_status,
                url=issue_data["url"],
            )

            # Verify Slack notification was sent
            mock_slack_client.chat_postMessage.assert_called_once()
            call_args = mock_slack_client.chat_postMessage.call_args

            # Verify channel
            assert call_args.kwargs["channel"] == "C123456"

            # Verify blocks contain status information
            assert "blocks" in call_args.kwargs
            blocks = call_args.kwargs["blocks"]
            assert len(blocks) > 0


@pytest.mark.asyncio
async def test_linear_comment_added_triggers_slack_notification(
    slack_notifier, mock_slack_client, sample_comment_webhook
):
    """Test that Linear comment creation webhook triggers Slack notification."""
    # Setup
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            comment_data = sample_comment_webhook["data"]

            # Send comment added notification
            await slack_notifier.post_comment_added(
                issue_id=comment_data["issue"]["id"],
                issue_title=comment_data["issue"]["title"],
                comment_body=comment_data["body"],
                comment_author=comment_data["user"]["name"],
                url=sample_comment_webhook["url"],
            )

            # Verify Slack notification was sent
            mock_slack_client.chat_postMessage.assert_called_once()
            call_args = mock_slack_client.chat_postMessage.call_args

            # Verify channel
            assert call_args.kwargs["channel"] == "C123456"

            # Verify blocks contain comment information
            assert "blocks" in call_args.kwargs


@pytest.mark.asyncio
async def test_slack_notification_with_custom_channel(
    slack_notifier, mock_slack_client, sample_linear_issue
):
    """Test Slack notification with custom channel specified."""
    # Setup
    custom_channel = "C789012"

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            # Send notification to custom channel
            await slack_notifier.post_issue_created(
                issue_id=sample_linear_issue["id"],
                title=sample_linear_issue["title"],
                description=sample_linear_issue["description"],
                assignee=sample_linear_issue["assignee"]["name"],
                status=sample_linear_issue["state"]["name"],
                url=sample_linear_issue["url"],
                channel=custom_channel,
            )

            # Verify notification was sent to custom channel
            call_args = mock_slack_client.chat_postMessage.call_args
            assert call_args.kwargs["channel"] == custom_channel


@pytest.mark.asyncio
async def test_deduplication_prevents_duplicate_notifications(
    mock_slack_config, mock_dedup_manager, mock_slack_client, sample_linear_issue
):
    """Test that deduplication prevents duplicate Slack notifications."""
    # Setup dedup manager to indicate duplicate event
    mock_dedup_manager.is_duplicate = AsyncMock(return_value=True)

    notifier = SlackNotifier(config=mock_slack_config, dedup_manager=mock_dedup_manager)

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with notifier:
            # Try to send notification for duplicate event
            await notifier.post_issue_created(
                issue_id=sample_linear_issue["id"],
                title=sample_linear_issue["title"],
                description=sample_linear_issue["description"],
                assignee=sample_linear_issue["assignee"]["name"],
                status=sample_linear_issue["state"]["name"],
                url=sample_linear_issue["url"],
            )

            # Verify notification was NOT sent (due to deduplication)
            mock_slack_client.chat_postMessage.assert_not_called()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_slack_not_configured_graceful_degradation(
    unconfigured_slack_config, mock_dedup_manager, sample_linear_issue
):
    """Test graceful degradation when Slack is not configured."""
    notifier = SlackNotifier(
        config=unconfigured_slack_config, dedup_manager=mock_dedup_manager
    )

    # Should raise SlackNotConfiguredError when trying to send
    with pytest.raises(SlackNotConfiguredError):
        async with notifier:
            await notifier.post_issue_created(
                issue_id=sample_linear_issue["id"],
                title=sample_linear_issue["title"],
                description=sample_linear_issue["description"],
                assignee=sample_linear_issue["assignee"]["name"],
                status=sample_linear_issue["state"]["name"],
                url=sample_linear_issue["url"],
            )


@pytest.mark.asyncio
async def test_slack_authentication_error_handling(
    slack_notifier, mock_slack_client, sample_linear_issue
):
    """Test handling of Slack authentication errors."""
    # Setup mock to raise authentication error
    from slack_sdk.errors import SlackApiError

    mock_slack_client.chat_postMessage = AsyncMock(
        side_effect=SlackApiError(
            message="Invalid auth token",
            response={"ok": False, "error": "invalid_auth"},
        )
    )

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            # Should raise SlackAuthenticationError
            with pytest.raises(SlackAuthenticationError):
                await slack_notifier.post_issue_created(
                    issue_id=sample_linear_issue["id"],
                    title=sample_linear_issue["title"],
                    description=sample_linear_issue["description"],
                    assignee=sample_linear_issue["assignee"]["name"],
                    status=sample_linear_issue["state"]["name"],
                    url=sample_linear_issue["url"],
                )


@pytest.mark.asyncio
async def test_slack_rate_limit_error_handling(
    slack_notifier, mock_slack_client, sample_linear_issue
):
    """Test handling of Slack rate limit errors."""
    # Setup mock to raise rate limit error
    from slack_sdk.errors import SlackApiError

    mock_slack_client.chat_postMessage = AsyncMock(
        side_effect=SlackApiError(
            message="Rate limited",
            response={"ok": False, "error": "rate_limited"},
        )
    )

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            # Should raise SlackRateLimitError
            with pytest.raises(SlackRateLimitError):
                await slack_notifier.post_issue_created(
                    issue_id=sample_linear_issue["id"],
                    title=sample_linear_issue["title"],
                    description=sample_linear_issue["description"],
                    assignee=sample_linear_issue["assignee"]["name"],
                    status=sample_linear_issue["state"]["name"],
                    url=sample_linear_issue["url"],
                )


@pytest.mark.asyncio
async def test_slack_channel_not_found_error_handling(
    slack_notifier, mock_slack_client, sample_linear_issue
):
    """Test handling of Slack channel not found errors."""
    # Setup mock to raise channel not found error
    from slack_sdk.errors import SlackApiError

    mock_slack_client.chat_postMessage = AsyncMock(
        side_effect=SlackApiError(
            message="Channel not found",
            response={"ok": False, "error": "channel_not_found"},
        )
    )

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            # Should raise SlackChannelNotFoundError
            with pytest.raises(SlackChannelNotFoundError):
                await slack_notifier.post_issue_created(
                    issue_id=sample_linear_issue["id"],
                    title=sample_linear_issue["title"],
                    description=sample_linear_issue["description"],
                    assignee=sample_linear_issue["assignee"]["name"],
                    status=sample_linear_issue["state"]["name"],
                    url=sample_linear_issue["url"],
                )


# ============================================================================
# End-to-End Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_complete_linear_webhook_to_slack_flow(
    slack_notifier, mock_slack_client, sample_issue_created_webhook
):
    """Test complete flow: Linear webhook → parse → Slack notification."""
    # Setup
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            # Parse webhook payload
            payload = LinearWebhookPayload(**sample_issue_created_webhook)
            assert payload.action == "create"
            assert payload.type == "Issue"

            # Extract issue event
            issue_event = IssueEvent.from_webhook_payload(payload)
            assert issue_event.issue_id == sample_issue_created_webhook["data"]["id"]

            # Send Slack notification
            await slack_notifier.post_issue_created(
                issue_id=issue_event.issue_id,
                title=issue_event.title,
                description=issue_event.description or "",
                assignee=issue_event.assignee,
                status=issue_event.status,
                priority=issue_event.priority,
                url=issue_event.url,
            )

            # Verify complete flow
            mock_slack_client.chat_postMessage.assert_called_once()
            call_args = mock_slack_client.chat_postMessage.call_args

            # Verify message structure
            assert "channel" in call_args.kwargs
            assert "blocks" in call_args.kwargs
            assert "text" in call_args.kwargs


@pytest.mark.asyncio
async def test_multiple_notifications_respect_rate_limiting(
    slack_notifier, mock_slack_client, sample_linear_issue
):
    """Test that multiple Slack notifications respect rate limiting."""
    # Setup
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            # Send multiple notifications rapidly
            start_time = asyncio.get_event_loop().time()

            for i in range(3):
                await slack_notifier.post_issue_created(
                    issue_id=f"issue-{i}",
                    title=f"Test Issue {i}",
                    description="Test description",
                    assignee="Test User",
                    status="In Progress",
                    url=f"https://linear.app/test/issue/{i}",
                )

            end_time = asyncio.get_event_loop().time()
            elapsed_time = end_time - start_time

            # Verify rate limiting (should take at least 2 seconds for 3 messages)
            # 1 second between each message = 2 seconds total delay
            assert elapsed_time >= 2.0

            # Verify all messages were sent
            assert mock_slack_client.chat_postMessage.call_count == 3


@pytest.mark.asyncio
async def test_slack_notification_block_kit_formatting(
    slack_notifier, mock_slack_client, sample_linear_issue
):
    """Test that Slack notifications use proper Block Kit formatting."""
    # Setup
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            # Send notification
            await slack_notifier.post_issue_created(
                issue_id=sample_linear_issue["id"],
                title=sample_linear_issue["title"],
                description=sample_linear_issue["description"],
                assignee=sample_linear_issue["assignee"]["name"],
                status=sample_linear_issue["state"]["name"],
                priority=sample_linear_issue["priority"],
                url=sample_linear_issue["url"],
            )

            # Verify Block Kit structure
            call_args = mock_slack_client.chat_postMessage.call_args
            blocks = call_args.kwargs["blocks"]

            # Verify blocks structure
            assert isinstance(blocks, list)
            assert len(blocks) > 0

            # Verify blocks contain required types (header, section, actions)
            block_types = [block["type"] for block in blocks]
            assert "header" in block_types or "section" in block_types

            # Verify action button is present (link to Linear)
            action_blocks = [block for block in blocks if block.get("type") == "actions"]
            if action_blocks:
                assert len(action_blocks[0].get("elements", [])) > 0


@pytest.mark.asyncio
async def test_status_change_notification_includes_old_and_new_status(
    slack_notifier, mock_slack_client, sample_status_change_webhook
):
    """Test that status change notifications include both old and new status."""
    # Setup
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier:
            issue_data = sample_status_change_webhook["data"]
            old_status = sample_status_change_webhook["updatedFrom"]["state"]["name"]
            new_status = issue_data["state"]["name"]

            # Send status change notification
            await slack_notifier.post_status_changed(
                issue_id=issue_data["id"],
                title=issue_data["title"],
                old_status=old_status,
                new_status=new_status,
                url=issue_data["url"],
            )

            # Verify notification contains both statuses
            call_args = mock_slack_client.chat_postMessage.call_args
            text = call_args.kwargs["text"]

            # Fallback text should contain both statuses
            assert old_status in text or "Todo" in text
            assert new_status in text or "In Progress" in text
