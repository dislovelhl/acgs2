"""
Tests for Slack notification service for Linear integration.

Tests cover:
- SlackNotifier initialization and configuration
- Message sending with retry logic
- Issue created, status changed, and comment added notifications
- Error handling (auth failures, rate limits, channel not found, not configured)
- Deduplication to prevent duplicate notifications
- Rate limiting (1 message per second)
- Block Kit message formatting
- Async context manager support
- Singleton pattern
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import SecretStr

# Import the Slack notifier and related classes
from src.integrations.linear.slack_notifier import (
    SLACK_RATE_LIMIT_SECONDS,
    SlackAuthenticationError,
    SlackChannelNotFoundError,
    SlackNotConfiguredError,
    SlackNotifier,
    SlackNotifierError,
    SlackRateLimitError,
    get_slack_notifier,
    reset_slack_notifier,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_slack_config():
    """Create mock Slack configuration for testing."""
    config = MagicMock()
    config.slack_bot_token = SecretStr("xoxb-test-token-12345")
    config.slack_signing_secret = SecretStr("test-signing-secret")
    config.slack_default_channel = "C123456"
    config.slack_timeout_seconds = 30.0
    config.is_configured = True
    return config


@pytest.fixture
def unconfigured_slack_config():
    """Create unconfigured Slack config (missing credentials)."""
    config = MagicMock()
    config.slack_bot_token = None
    config.slack_signing_secret = None
    config.slack_default_channel = None
    config.slack_timeout_seconds = 30.0
    config.is_configured = False
    return config


@pytest.fixture
def mock_dedup_manager():
    """Create mock deduplication manager."""
    dedup = MagicMock()
    dedup.is_duplicate = AsyncMock(return_value=False)
    dedup.mark_processed = AsyncMock()
    return dedup


@pytest.fixture
def slack_notifier(mock_slack_config, mock_dedup_manager):
    """Create SlackNotifier instance for testing."""
    return SlackNotifier(config=mock_slack_config, dedup_manager=mock_dedup_manager)


@pytest.fixture
def unconfigured_slack_notifier(unconfigured_slack_config, mock_dedup_manager):
    """Create unconfigured SlackNotifier instance."""
    return SlackNotifier(
        config=unconfigured_slack_config, dedup_manager=mock_dedup_manager
    )


@pytest.fixture
def mock_slack_client():
    """Create mock Slack AsyncWebClient."""
    client = MagicMock()
    client.chat_postMessage = AsyncMock(
        return_value={"ok": True, "ts": "1234567890.123456"}
    )
    return client


@pytest.fixture
def mock_slack_api_error():
    """Create mock SlackApiError class."""
    # Create a mock SlackApiError
    from slack_sdk.errors import SlackApiError

    return SlackApiError


# ============================================================================
# Initialization Tests
# ============================================================================


def test_slack_notifier_initialization(mock_slack_config, mock_dedup_manager):
    """Test SlackNotifier initialization with valid config."""
    notifier = SlackNotifier(config=mock_slack_config, dedup_manager=mock_dedup_manager)

    assert notifier._config == mock_slack_config
    assert notifier._dedup_manager == mock_dedup_manager
    assert notifier._client is None
    assert notifier._last_send_time == 0.0


def test_slack_notifier_initialization_unconfigured(
    unconfigured_slack_config, mock_dedup_manager
):
    """Test SlackNotifier initialization with unconfigured Slack."""
    notifier = SlackNotifier(
        config=unconfigured_slack_config, dedup_manager=mock_dedup_manager
    )

    assert notifier._config == unconfigured_slack_config
    assert not notifier._config.is_configured


def test_slack_notifier_default_initialization():
    """Test SlackNotifier uses get_slack_config and get_dedup_manager by default."""
    with patch("src.integrations.linear.slack_notifier.get_slack_config") as mock_config:
        with patch(
            "src.integrations.linear.slack_notifier.get_dedup_manager"
        ) as mock_dedup:
            mock_config.return_value = MagicMock(is_configured=True)
            mock_dedup.return_value = MagicMock()

            notifier = SlackNotifier()

            mock_config.assert_called_once()
            mock_dedup.assert_called_once()
            assert notifier._config is not None
            assert notifier._dedup_manager is not None


# ============================================================================
# Async Context Manager Tests
# ============================================================================


@pytest.mark.asyncio
async def test_slack_notifier_context_manager(slack_notifier, mock_slack_client):
    """Test SlackNotifier async context manager."""
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        async with slack_notifier as notifier:
            assert notifier._client is not None

        # After exiting, client should be cleaned up
        assert slack_notifier._client is None


@pytest.mark.asyncio
async def test_slack_notifier_ensure_client(slack_notifier, mock_slack_client):
    """Test _ensure_client initializes Slack client correctly."""
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        client = await slack_notifier._ensure_client()

        assert client is not None
        assert slack_notifier._client is mock_slack_client


@pytest.mark.asyncio
async def test_slack_notifier_ensure_client_not_configured(unconfigured_slack_notifier):
    """Test _ensure_client raises error when Slack not configured."""
    with pytest.raises(SlackNotConfiguredError) as exc_info:
        await unconfigured_slack_notifier._ensure_client()

    assert "not configured" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_slack_notifier_close(slack_notifier, mock_slack_client):
    """Test close() method cleans up client."""
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        await slack_notifier._ensure_client()
        assert slack_notifier._client is not None

        await slack_notifier.close()
        assert slack_notifier._client is None


# ============================================================================
# Rate Limiting Tests
# ============================================================================


@pytest.mark.asyncio
async def test_rate_limiting_enforced(slack_notifier):
    """Test rate limiting enforces 1 message per second."""
    # Set last send time to current time
    slack_notifier._last_send_time = asyncio.get_event_loop().time()

    # Measure time taken to apply rate limit
    start_time = asyncio.get_event_loop().time()
    await slack_notifier._apply_rate_limit()
    elapsed_time = asyncio.get_event_loop().time() - start_time

    # Should have waited approximately 1 second
    assert elapsed_time >= SLACK_RATE_LIMIT_SECONDS * 0.9


@pytest.mark.asyncio
async def test_rate_limiting_no_delay_when_sufficient_time_passed(slack_notifier):
    """Test rate limiting doesn't delay when sufficient time has passed."""
    # Set last send time to 2 seconds ago
    slack_notifier._last_send_time = asyncio.get_event_loop().time() - 2.0

    # Measure time taken to apply rate limit
    start_time = asyncio.get_event_loop().time()
    await slack_notifier._apply_rate_limit()
    elapsed_time = asyncio.get_event_loop().time() - start_time

    # Should not wait (or wait very little)
    assert elapsed_time < 0.1


# ============================================================================
# Message Sending Tests
# ============================================================================


@pytest.mark.asyncio
async def test_send_message_success(slack_notifier, mock_slack_client):
    """Test _send_message sends message successfully."""
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        blocks = [{"type": "section", "text": {"type": "plain_text", "text": "Test"}}]
        text = "Test message"

        response = await slack_notifier._send_message(
            channel="C123456", blocks=blocks, text=text
        )

        assert response["ok"] is True
        mock_slack_client.chat_postMessage.assert_called_once_with(
            channel="C123456", blocks=blocks, text=text
        )


@pytest.mark.asyncio
async def test_send_message_authentication_error(slack_notifier, mock_slack_client):
    """Test _send_message raises SlackAuthenticationError on auth failure."""
    from slack_sdk.errors import SlackApiError

    # Mock authentication error
    error_response = {"ok": False, "error": "invalid_auth"}
    error = SlackApiError("Authentication failed", error_response)
    mock_slack_client.chat_postMessage = AsyncMock(side_effect=error)

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        blocks = [{"type": "section", "text": {"type": "plain_text", "text": "Test"}}]

        with pytest.raises(SlackAuthenticationError) as exc_info:
            await slack_notifier._send_message(
                channel="C123456", blocks=blocks, text="Test"
            )

        assert "authentication failed" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_send_message_rate_limit_error(slack_notifier, mock_slack_client):
    """Test _send_message raises SlackRateLimitError when rate limited."""
    from slack_sdk.errors import SlackApiError

    # Mock rate limit error
    error_response = {
        "ok": False,
        "error": "rate_limited",
        "headers": {"Retry-After": "60"},
    }
    error = SlackApiError("Rate limited", error_response)
    error.response.headers = {"Retry-After": "60"}
    mock_slack_client.chat_postMessage = AsyncMock(side_effect=error)

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        blocks = [{"type": "section", "text": {"type": "plain_text", "text": "Test"}}]

        with pytest.raises(SlackRateLimitError) as exc_info:
            await slack_notifier._send_message(
                channel="C123456", blocks=blocks, text="Test"
            )

        assert exc_info.value.retry_after == 60


@pytest.mark.asyncio
async def test_send_message_channel_not_found_error(slack_notifier, mock_slack_client):
    """Test _send_message raises SlackChannelNotFoundError when channel not found."""
    from slack_sdk.errors import SlackApiError

    # Mock channel not found error
    error_response = {"ok": False, "error": "channel_not_found"}
    error = SlackApiError("Channel not found", error_response)
    mock_slack_client.chat_postMessage = AsyncMock(side_effect=error)

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        blocks = [{"type": "section", "text": {"type": "plain_text", "text": "Test"}}]

        with pytest.raises(SlackChannelNotFoundError) as exc_info:
            await slack_notifier._send_message(
                channel="C123456", blocks=blocks, text="Test"
            )

        assert "channel not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_send_message_generic_slack_error(slack_notifier, mock_slack_client):
    """Test _send_message raises SlackNotifierError for generic errors."""
    from slack_sdk.errors import SlackApiError

    # Mock generic error
    error_response = {"ok": False, "error": "some_other_error"}
    error = SlackApiError("Generic error", error_response)
    mock_slack_client.chat_postMessage = AsyncMock(side_effect=error)

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        blocks = [{"type": "section", "text": {"type": "plain_text", "text": "Test"}}]

        with pytest.raises(SlackNotifierError) as exc_info:
            await slack_notifier._send_message(
                channel="C123456", blocks=blocks, text="Test"
            )

        assert "slack api error" in str(exc_info.value).lower()


# ============================================================================
# Block Building Tests
# ============================================================================


def test_build_issue_created_blocks(slack_notifier):
    """Test _build_issue_created_blocks creates correct Block Kit structure."""
    blocks = slack_notifier._build_issue_created_blocks(
        issue_id="LIN-123",
        title="Fix authentication bug",
        description="Users unable to log in with SSO",
        assignee="Alice",
        status="In Progress",
        priority="high",
        url="https://linear.app/issue/123",
    )

    # Verify block structure
    assert len(blocks) >= 3
    assert blocks[0]["type"] == "header"
    assert "New Linear Issue Created" in blocks[0]["text"]["text"]
    assert ":large_orange_circle:" in blocks[0]["text"]["text"]  # high priority emoji

    # Find section with title
    title_block = next(b for b in blocks if b["type"] == "section" and "Fix" in str(b))
    assert "Fix authentication bug" in title_block["text"]["text"]

    # Find action button if URL provided
    action_blocks = [b for b in blocks if b["type"] == "actions"]
    assert len(action_blocks) == 1
    assert action_blocks[0]["elements"][0]["url"] == "https://linear.app/issue/123"


def test_build_issue_created_blocks_truncates_long_description(slack_notifier):
    """Test _build_issue_created_blocks truncates long descriptions."""
    long_description = "x" * 600  # Longer than 500 char limit

    blocks = slack_notifier._build_issue_created_blocks(
        issue_id="LIN-123",
        title="Test",
        description=long_description,
        assignee=None,
        status=None,
        priority=None,
        url=None,
    )

    # Find description block
    desc_blocks = [
        b
        for b in blocks
        if b["type"] == "section" and "xxx..." in b["text"]["text"]
    ]
    assert len(desc_blocks) == 1
    assert len(desc_blocks[0]["text"]["text"]) < len(long_description)
    assert desc_blocks[0]["text"]["text"].endswith("...")


def test_build_status_changed_blocks(slack_notifier):
    """Test _build_status_changed_blocks creates correct Block Kit structure."""
    blocks = slack_notifier._build_status_changed_blocks(
        issue_id="LIN-123",
        title="Fix authentication bug",
        old_status="In Progress",
        new_status="Done",
        assignee="Alice",
        url="https://linear.app/issue/123",
    )

    # Verify block structure
    assert len(blocks) >= 3
    assert blocks[0]["type"] == "header"
    assert "Issue Status Changed" in blocks[0]["text"]["text"]

    # Find section with status transition
    status_block = next(
        b for b in blocks if b["type"] == "section" and "→" in b["text"]["text"]
    )
    assert "In Progress" in status_block["text"]["text"]
    assert "Done" in status_block["text"]["text"]


def test_build_comment_added_blocks(slack_notifier):
    """Test _build_comment_added_blocks creates correct Block Kit structure."""
    blocks = slack_notifier._build_comment_added_blocks(
        issue_id="LIN-123",
        title="Fix authentication bug",
        comment_author="Bob",
        comment_body="I've identified the root cause of this issue.",
        url="https://linear.app/issue/123",
    )

    # Verify block structure
    assert len(blocks) >= 3
    assert blocks[0]["type"] == "header"
    assert "New Comment Added" in blocks[0]["text"]["text"]

    # Find section with comment
    comment_blocks = [
        b for b in blocks if b["type"] == "section" and "Bob" in str(b)
    ]
    assert len(comment_blocks) > 0
    assert "Bob commented" in comment_blocks[0]["text"]["text"]


def test_build_comment_added_blocks_truncates_long_comment(slack_notifier):
    """Test _build_comment_added_blocks truncates long comments."""
    long_comment = "y" * 400  # Longer than 300 char limit

    blocks = slack_notifier._build_comment_added_blocks(
        issue_id="LIN-123",
        title="Test",
        comment_author="Bob",
        comment_body=long_comment,
        url=None,
    )

    # Find comment block
    comment_blocks = [
        b for b in blocks if b["type"] == "section" and "yyy..." in str(b)
    ]
    assert len(comment_blocks) == 1
    assert "..." in comment_blocks[0]["text"]["text"]


# ============================================================================
# Notification Method Tests
# ============================================================================


@pytest.mark.asyncio
async def test_post_issue_created_success(
    slack_notifier, mock_slack_client, mock_dedup_manager
):
    """Test post_issue_created sends notification successfully."""
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        result = await slack_notifier.post_issue_created(
            issue_id="LIN-123",
            title="Fix authentication bug",
            description="Users unable to log in",
            assignee="Alice",
            status="In Progress",
            priority="high",
            url="https://linear.app/issue/123",
            channel="C123456",
        )

        assert result is True
        mock_slack_client.chat_postMessage.assert_called_once()
        mock_dedup_manager.mark_processed.assert_called_once()


@pytest.mark.asyncio
async def test_post_issue_created_not_configured(
    unconfigured_slack_notifier, mock_dedup_manager
):
    """Test post_issue_created returns False when Slack not configured."""
    result = await unconfigured_slack_notifier.post_issue_created(
        issue_id="LIN-123",
        title="Test issue",
    )

    assert result is False
    mock_dedup_manager.mark_processed.assert_not_called()


@pytest.mark.asyncio
async def test_post_issue_created_duplicate_detected(
    slack_notifier, mock_slack_client, mock_dedup_manager
):
    """Test post_issue_created skips duplicate notifications."""
    # Configure dedup manager to return duplicate
    mock_dedup_manager.is_duplicate = AsyncMock(return_value=True)

    result = await slack_notifier.post_issue_created(
        issue_id="LIN-123",
        title="Test issue",
    )

    assert result is False
    mock_slack_client.chat_postMessage.assert_not_called()
    mock_dedup_manager.mark_processed.assert_not_called()


@pytest.mark.asyncio
async def test_post_issue_created_no_channel(
    slack_notifier, mock_slack_client, mock_dedup_manager
):
    """Test post_issue_created returns False when no channel specified."""
    # Remove default channel
    slack_notifier._config.slack_default_channel = None

    result = await slack_notifier.post_issue_created(
        issue_id="LIN-123",
        title="Test issue",
    )

    assert result is False
    mock_slack_client.chat_postMessage.assert_not_called()


@pytest.mark.asyncio
async def test_post_issue_created_uses_default_channel(
    slack_notifier, mock_slack_client, mock_dedup_manager
):
    """Test post_issue_created uses default channel when none specified."""
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        result = await slack_notifier.post_issue_created(
            issue_id="LIN-123",
            title="Test issue",
        )

        assert result is True
        # Verify default channel was used
        call_args = mock_slack_client.chat_postMessage.call_args
        assert call_args.kwargs["channel"] == "C123456"


@pytest.mark.asyncio
async def test_post_status_changed_success(
    slack_notifier, mock_slack_client, mock_dedup_manager
):
    """Test post_status_changed sends notification successfully."""
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        result = await slack_notifier.post_status_changed(
            issue_id="LIN-123",
            title="Fix authentication bug",
            old_status="In Progress",
            new_status="Done",
            assignee="Alice",
            url="https://linear.app/issue/123",
            channel="C123456",
        )

        assert result is True
        mock_slack_client.chat_postMessage.assert_called_once()
        mock_dedup_manager.mark_processed.assert_called_once()


@pytest.mark.asyncio
async def test_post_status_changed_not_configured(
    unconfigured_slack_notifier, mock_dedup_manager
):
    """Test post_status_changed returns False when Slack not configured."""
    result = await unconfigured_slack_notifier.post_status_changed(
        issue_id="LIN-123",
        title="Test issue",
        old_status="Todo",
        new_status="Done",
    )

    assert result is False
    mock_dedup_manager.mark_processed.assert_not_called()


@pytest.mark.asyncio
async def test_post_comment_added_success(
    slack_notifier, mock_slack_client, mock_dedup_manager
):
    """Test post_comment_added sends notification successfully."""
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        result = await slack_notifier.post_comment_added(
            issue_id="LIN-123",
            title="Fix authentication bug",
            comment_author="Bob",
            comment_body="I've identified the root cause.",
            url="https://linear.app/issue/123",
            channel="C123456",
        )

        assert result is True
        mock_slack_client.chat_postMessage.assert_called_once()
        mock_dedup_manager.mark_processed.assert_called_once()


@pytest.mark.asyncio
async def test_post_comment_added_deduplication_uses_hash(
    slack_notifier, mock_slack_client, mock_dedup_manager
):
    """Test post_comment_added uses comment hash for deduplication."""
    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        await slack_notifier.post_comment_added(
            issue_id="LIN-123",
            title="Test issue",
            comment_author="Bob",
            comment_body="This is a comment",
            channel="C123456",
        )

        # Verify deduplication was checked with event ID containing hash
        check_call = mock_dedup_manager.is_duplicate.call_args
        event_id = check_call[0][0]
        assert event_id.startswith("slack_comment_added_LIN-123_")
        assert len(event_id.split("_")[-1]) == 8  # MD5 hash prefix


@pytest.mark.asyncio
async def test_post_comment_added_not_configured(
    unconfigured_slack_notifier, mock_dedup_manager
):
    """Test post_comment_added returns False when Slack not configured."""
    result = await unconfigured_slack_notifier.post_comment_added(
        issue_id="LIN-123",
        title="Test issue",
        comment_author="Bob",
        comment_body="Comment",
    )

    assert result is False
    mock_dedup_manager.mark_processed.assert_not_called()


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_post_issue_created_handles_slack_error(
    slack_notifier, mock_slack_client, mock_dedup_manager
):
    """Test post_issue_created handles Slack API errors gracefully."""
    from slack_sdk.errors import SlackApiError

    error_response = {"ok": False, "error": "some_error"}
    error = SlackApiError("API error", error_response)
    mock_slack_client.chat_postMessage = AsyncMock(side_effect=error)

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        with pytest.raises(SlackNotifierError):
            await slack_notifier.post_issue_created(
                issue_id="LIN-123",
                title="Test issue",
                channel="C123456",
            )


@pytest.mark.asyncio
async def test_post_status_changed_handles_slack_error(
    slack_notifier, mock_slack_client, mock_dedup_manager
):
    """Test post_status_changed handles Slack API errors gracefully."""
    from slack_sdk.errors import SlackApiError

    error_response = {"ok": False, "error": "some_error"}
    error = SlackApiError("API error", error_response)
    mock_slack_client.chat_postMessage = AsyncMock(side_effect=error)

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        with pytest.raises(SlackNotifierError):
            await slack_notifier.post_status_changed(
                issue_id="LIN-123",
                title="Test issue",
                old_status="Todo",
                new_status="Done",
                channel="C123456",
            )


@pytest.mark.asyncio
async def test_post_comment_added_handles_slack_error(
    slack_notifier, mock_slack_client, mock_dedup_manager
):
    """Test post_comment_added handles Slack API errors gracefully."""
    from slack_sdk.errors import SlackApiError

    error_response = {"ok": False, "error": "some_error"}
    error = SlackApiError("API error", error_response)
    mock_slack_client.chat_postMessage = AsyncMock(side_effect=error)

    with patch(
        "src.integrations.linear.slack_notifier.AsyncWebClient",
        return_value=mock_slack_client,
    ):
        with pytest.raises(SlackNotifierError):
            await slack_notifier.post_comment_added(
                issue_id="LIN-123",
                title="Test issue",
                comment_author="Bob",
                comment_body="Comment",
                channel="C123456",
            )


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


def test_get_slack_notifier_singleton():
    """Test get_slack_notifier returns singleton instance."""
    # Reset singleton first
    reset_slack_notifier()

    notifier1 = get_slack_notifier()
    notifier2 = get_slack_notifier()

    assert notifier1 is notifier2


def test_reset_slack_notifier():
    """Test reset_slack_notifier clears singleton instance."""
    notifier1 = get_slack_notifier()
    reset_slack_notifier()
    notifier2 = get_slack_notifier()

    assert notifier1 is not notifier2


# ============================================================================
# Priority Emoji Tests
# ============================================================================


def test_priority_emoji_urgent(slack_notifier):
    """Test urgent priority uses red circle emoji."""
    blocks = slack_notifier._build_issue_created_blocks(
        issue_id="LIN-123",
        title="Test",
        description=None,
        assignee=None,
        status=None,
        priority="urgent",
        url=None,
    )

    assert ":red_circle:" in blocks[0]["text"]["text"]


def test_priority_emoji_high(slack_notifier):
    """Test high priority uses orange circle emoji."""
    blocks = slack_notifier._build_issue_created_blocks(
        issue_id="LIN-123",
        title="Test",
        description=None,
        assignee=None,
        status=None,
        priority="high",
        url=None,
    )

    assert ":large_orange_circle:" in blocks[0]["text"]["text"]


def test_priority_emoji_medium(slack_notifier):
    """Test medium priority uses blue circle emoji."""
    blocks = slack_notifier._build_issue_created_blocks(
        issue_id="LIN-123",
        title="Test",
        description=None,
        assignee=None,
        status=None,
        priority="medium",
        url=None,
    )

    assert ":large_blue_circle:" in blocks[0]["text"]["text"]


def test_priority_emoji_low(slack_notifier):
    """Test low priority uses white circle emoji."""
    blocks = slack_notifier._build_issue_created_blocks(
        issue_id="LIN-123",
        title="Test",
        description=None,
        assignee=None,
        status=None,
        priority="low",
        url=None,
    )

    assert ":white_circle:" in blocks[0]["text"]["text"]


def test_priority_emoji_case_insensitive(slack_notifier):
    """Test priority emoji mapping is case-insensitive."""
    blocks = slack_notifier._build_issue_created_blocks(
        issue_id="LIN-123",
        title="Test",
        description=None,
        assignee=None,
        status=None,
        priority="HIGH",  # Uppercase
        url=None,
    )

    assert ":large_orange_circle:" in blocks[0]["text"]["text"]


def test_priority_emoji_default_for_unknown(slack_notifier):
    """Test unknown priority uses default white circle emoji."""
    blocks = slack_notifier._build_issue_created_blocks(
        issue_id="LIN-123",
        title="Test",
        description=None,
        assignee=None,
        status=None,
        priority="unknown_priority",
        url=None,
    )

    assert ":white_circle:" in blocks[0]["text"]["text"]
