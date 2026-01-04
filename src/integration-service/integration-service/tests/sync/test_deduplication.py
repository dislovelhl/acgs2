"""
Tests for Linear Deduplication Logic.

Tests cover:
- LinearDeduplicationManager initialization and configuration
- Event ID tracking to prevent duplicate processing
- Source tracking to prevent infinite sync loops
- Sync chain tracking and loop detection
- TTL-based automatic cleanup
- should_process_event comprehensive checks
- Async context manager support
- Error handling and edge cases
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.linear.deduplication import (
    DEFAULT_EVENT_TTL,
    DEFAULT_SYNC_CHAIN_TTL,
    MAX_SYNC_CHAIN_LENGTH,
    SYNC_SOURCE_GITHUB,
    SYNC_SOURCE_GITLAB,
    SYNC_SOURCE_LINEAR,
    SYNC_SOURCE_MANUAL,
    SYNC_SOURCE_SLACK,
    VALID_SYNC_SOURCES,
    DeduplicationError,
    LinearDeduplicationManager,
    get_dedup_manager,
    reset_dedup_manager,
)

if TYPE_CHECKING:
    pass


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_state_manager():
    """Create a mock Linear state manager."""
    manager = MagicMock()
    manager.connect = AsyncMock()
    manager.close = AsyncMock()
    manager.is_duplicate_event = AsyncMock(return_value=False)
    manager.mark_event_processed = AsyncMock()
    manager.record_sync = AsyncMock()
    manager.get_sync_state = AsyncMock(return_value=None)
    manager.clear_sync_state = AsyncMock(return_value=True)
    # Mock Redis client for sync chain operations
    manager._redis_client = MagicMock()
    manager._redis_client.rpush = AsyncMock()
    manager._redis_client.expire = AsyncMock()
    manager._redis_client.ltrim = AsyncMock()
    manager._redis_client.lrange = AsyncMock(return_value=[])
    manager._redis_client.delete = AsyncMock(return_value=1)
    return manager


@pytest.fixture
def dedup_manager(mock_state_manager):
    """Create a deduplication manager for testing."""
    return LinearDeduplicationManager(
        state_manager=mock_state_manager,
        event_ttl=DEFAULT_EVENT_TTL,
        sync_chain_ttl=DEFAULT_SYNC_CHAIN_TTL,
        max_chain_length=MAX_SYNC_CHAIN_LENGTH,
    )


@pytest.fixture
async def connected_dedup_manager(dedup_manager: LinearDeduplicationManager):
    """Create a connected deduplication manager for testing."""
    await dedup_manager.connect()
    yield dedup_manager
    await dedup_manager.close()


@pytest.fixture
def sample_webhook_payload():
    """Create a sample Linear webhook payload."""
    payload = MagicMock()
    payload.type = "Issue"
    payload.action = "create"
    payload.data = MagicMock()
    payload.data.id = "issue-123"
    payload.createdAt = datetime.now(timezone.utc)
    payload.organizationId = "org-456"
    return payload


# ============================================================================
# Initialization Tests
# ============================================================================


def test_dedup_manager_initialization():
    """Test deduplication manager initializes with default values."""
    manager = LinearDeduplicationManager()

    assert manager._event_ttl == DEFAULT_EVENT_TTL
    assert manager._sync_chain_ttl == DEFAULT_SYNC_CHAIN_TTL
    assert manager._max_chain_length == MAX_SYNC_CHAIN_LENGTH
    assert not manager._connected
    assert manager._owns_state_manager is True


def test_dedup_manager_initialization_with_custom_values():
    """Test deduplication manager initialization with custom values."""
    custom_ttl = 7200
    custom_chain_ttl = 600
    custom_max_length = 10

    manager = LinearDeduplicationManager(
        event_ttl=custom_ttl,
        sync_chain_ttl=custom_chain_ttl,
        max_chain_length=custom_max_length,
    )

    assert manager._event_ttl == custom_ttl
    assert manager._sync_chain_ttl == custom_chain_ttl
    assert manager._max_chain_length == custom_max_length


def test_dedup_manager_initialization_with_state_manager(mock_state_manager):
    """Test deduplication manager initialization with provided state manager."""
    manager = LinearDeduplicationManager(state_manager=mock_state_manager)

    assert manager._state_manager == mock_state_manager
    assert manager._owns_state_manager is False


# ============================================================================
# Connection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_connect_success(dedup_manager: LinearDeduplicationManager):
    """Test successful connection to Redis."""
    await dedup_manager.connect()

    assert dedup_manager._connected is True
    dedup_manager._state_manager.connect.assert_called_once()


@pytest.mark.asyncio
async def test_connect_already_connected(dedup_manager: LinearDeduplicationManager):
    """Test connecting when already connected does nothing."""
    await dedup_manager.connect()
    await dedup_manager.connect()

    # Should only call state manager connect once
    assert dedup_manager._state_manager.connect.call_count == 1


@pytest.mark.asyncio
async def test_connect_failure(dedup_manager: LinearDeduplicationManager):
    """Test connection failure raises DeduplicationError."""
    dedup_manager._state_manager.connect.side_effect = Exception("Connection failed")

    with pytest.raises(DeduplicationError, match="Connection failed"):
        await dedup_manager.connect()

    assert dedup_manager._connected is False


@pytest.mark.asyncio
async def test_close(connected_dedup_manager: LinearDeduplicationManager):
    """Test closing connection."""
    await connected_dedup_manager.close()

    assert connected_dedup_manager._connected is False


@pytest.mark.asyncio
async def test_close_with_owned_state_manager(mock_state_manager):
    """Test closing calls state manager close when owned."""
    manager = LinearDeduplicationManager()
    manager._state_manager = mock_state_manager
    manager._owns_state_manager = True
    await manager.connect()

    await manager.close()

    mock_state_manager.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_without_owned_state_manager(mock_state_manager):
    """Test closing does not call state manager close when not owned."""
    manager = LinearDeduplicationManager(state_manager=mock_state_manager)
    await manager.connect()

    await manager.close()

    # Should not close state manager when not owned
    mock_state_manager.close.assert_not_called()


# ============================================================================
# Context Manager Tests
# ============================================================================


@pytest.mark.asyncio
async def test_context_manager(dedup_manager: LinearDeduplicationManager):
    """Test async context manager support."""
    async with dedup_manager as manager:
        assert manager._connected is True
        assert manager == dedup_manager

    assert dedup_manager._connected is False


# ============================================================================
# Event ID Generation Tests
# ============================================================================


def test_generate_event_id_from_webhook(
    dedup_manager: LinearDeduplicationManager, sample_webhook_payload
):
    """Test event ID generation from webhook payload."""
    event_id = dedup_manager._generate_event_id(webhook_payload=sample_webhook_payload)

    assert isinstance(event_id, str)
    assert len(event_id) == 32  # SHA256 hash truncated to 32 chars

    # Should be deterministic
    event_id2 = dedup_manager._generate_event_id(webhook_payload=sample_webhook_payload)
    assert event_id == event_id2


def test_generate_event_id_from_kwargs(dedup_manager: LinearDeduplicationManager):
    """Test event ID generation from kwargs."""
    event_id = dedup_manager._generate_event_id(
        issue_id="issue-123",
        action="create",
        source="linear",
    )

    assert isinstance(event_id, str)
    assert len(event_id) == 32

    # Should be deterministic
    event_id2 = dedup_manager._generate_event_id(
        issue_id="issue-123",
        action="create",
        source="linear",
    )
    assert event_id == event_id2


def test_generate_event_id_different_inputs(dedup_manager: LinearDeduplicationManager):
    """Test different inputs generate different event IDs."""
    event_id1 = dedup_manager._generate_event_id(issue_id="issue-1")
    event_id2 = dedup_manager._generate_event_id(issue_id="issue-2")

    assert event_id1 != event_id2


# ============================================================================
# Duplicate Detection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_is_duplicate_not_duplicate(connected_dedup_manager: LinearDeduplicationManager):
    """Test is_duplicate returns False for new event."""
    connected_dedup_manager._state_manager.is_duplicate_event.return_value = False

    is_dup = await connected_dedup_manager.is_duplicate("event-123")

    assert is_dup is False
    connected_dedup_manager._state_manager.is_duplicate_event.assert_called_once_with("event-123")


@pytest.mark.asyncio
async def test_is_duplicate_is_duplicate(connected_dedup_manager: LinearDeduplicationManager):
    """Test is_duplicate returns True for duplicate event."""
    connected_dedup_manager._state_manager.is_duplicate_event.return_value = True

    is_dup = await connected_dedup_manager.is_duplicate("event-123")

    assert is_dup is True


@pytest.mark.asyncio
async def test_is_duplicate_auto_connect(dedup_manager: LinearDeduplicationManager):
    """Test is_duplicate auto-connects if not connected."""
    dedup_manager._state_manager.is_duplicate_event.return_value = False

    await dedup_manager.is_duplicate("event-123")

    assert dedup_manager._connected is True


@pytest.mark.asyncio
async def test_is_duplicate_check_only(connected_dedup_manager: LinearDeduplicationManager):
    """Test is_duplicate with check_only flag."""
    connected_dedup_manager._state_manager.is_duplicate_event.return_value = True

    is_dup = await connected_dedup_manager.is_duplicate("event-123", check_only=True)

    assert is_dup is True


@pytest.mark.asyncio
async def test_is_duplicate_error_handling(connected_dedup_manager: LinearDeduplicationManager):
    """Test is_duplicate fails open on error (returns False to avoid losing events)."""
    connected_dedup_manager._state_manager.is_duplicate_event.side_effect = Exception("Redis error")

    is_dup = await connected_dedup_manager.is_duplicate("event-123")

    # Should fail open - assume not duplicate to avoid losing events
    assert is_dup is False


# ============================================================================
# Mark Processed Tests
# ============================================================================


@pytest.mark.asyncio
async def test_mark_processed_success(connected_dedup_manager: LinearDeduplicationManager):
    """Test successfully marking event as processed."""
    await connected_dedup_manager.mark_processed(
        event_id="event-123",
        source=SYNC_SOURCE_LINEAR,
        event_type="webhook",
        metadata={"title": "Test"},
    )

    connected_dedup_manager._state_manager.mark_event_processed.assert_called_once()
    call_args = connected_dedup_manager._state_manager.mark_event_processed.call_args

    assert call_args.kwargs["event_id"] == "event-123"
    assert call_args.kwargs["event_type"] == "webhook"
    assert call_args.kwargs["metadata"]["source"] == SYNC_SOURCE_LINEAR
    assert call_args.kwargs["metadata"]["title"] == "Test"
    assert "marked_at" in call_args.kwargs["metadata"]


@pytest.mark.asyncio
async def test_mark_processed_invalid_source(connected_dedup_manager: LinearDeduplicationManager):
    """Test marking event with invalid source raises ValueError."""
    with pytest.raises(ValueError, match="Invalid sync source"):
        await connected_dedup_manager.mark_processed(
            event_id="event-123",
            source="invalid-source",
        )


@pytest.mark.asyncio
async def test_mark_processed_all_valid_sources(
    connected_dedup_manager: LinearDeduplicationManager,
):
    """Test marking events with all valid sources."""
    for source in VALID_SYNC_SOURCES:
        await connected_dedup_manager.mark_processed(
            event_id=f"event-{source}",
            source=source,
        )

        # Verify state manager was called
        connected_dedup_manager._state_manager.mark_event_processed.assert_called()


@pytest.mark.asyncio
async def test_mark_processed_auto_connect(dedup_manager: LinearDeduplicationManager):
    """Test mark_processed auto-connects if not connected."""
    await dedup_manager.mark_processed(
        event_id="event-123",
        source=SYNC_SOURCE_LINEAR,
    )

    assert dedup_manager._connected is True


@pytest.mark.asyncio
async def test_mark_processed_failure(connected_dedup_manager: LinearDeduplicationManager):
    """Test mark_processed raises DeduplicationError on failure."""
    connected_dedup_manager._state_manager.mark_event_processed.side_effect = Exception(
        "Redis error"
    )

    with pytest.raises(DeduplicationError, match="Failed to mark event processed"):
        await connected_dedup_manager.mark_processed(
            event_id="event-123",
            source=SYNC_SOURCE_LINEAR,
        )


# ============================================================================
# Record Sync Tests
# ============================================================================


@pytest.mark.asyncio
async def test_record_sync_success(connected_dedup_manager: LinearDeduplicationManager):
    """Test successfully recording a sync operation."""
    await connected_dedup_manager.record_sync(
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
        metadata={"title": "Test"},
    )

    # Verify state manager record_sync was called
    connected_dedup_manager._state_manager.record_sync.assert_called_once()
    call_args = connected_dedup_manager._state_manager.record_sync.call_args

    assert call_args.kwargs["issue_id"] == "issue-123"
    assert call_args.kwargs["sync_source"] == SYNC_SOURCE_LINEAR
    assert call_args.kwargs["metadata"]["from_source"] == SYNC_SOURCE_LINEAR
    assert call_args.kwargs["metadata"]["to_source"] == SYNC_SOURCE_GITHUB

    # Verify sync chain was updated
    redis = connected_dedup_manager._state_manager._redis_client
    redis.rpush.assert_called_once()
    redis.expire.assert_called_once()
    redis.ltrim.assert_called_once()


@pytest.mark.asyncio
async def test_record_sync_invalid_source(connected_dedup_manager: LinearDeduplicationManager):
    """Test recording sync with invalid source raises ValueError."""
    with pytest.raises(ValueError, match="Invalid sync sources"):
        await connected_dedup_manager.record_sync(
            issue_id="issue-123",
            from_source="invalid",
            to_source=SYNC_SOURCE_GITHUB,
        )


@pytest.mark.asyncio
async def test_record_sync_failure(connected_dedup_manager: LinearDeduplicationManager):
    """Test record_sync raises DeduplicationError on failure."""
    connected_dedup_manager._state_manager.record_sync.side_effect = Exception("Redis error")

    with pytest.raises(DeduplicationError, match="Failed to record sync"):
        await connected_dedup_manager.record_sync(
            issue_id="issue-123",
            from_source=SYNC_SOURCE_LINEAR,
            to_source=SYNC_SOURCE_GITHUB,
        )


# ============================================================================
# Sync Chain Tests
# ============================================================================


@pytest.mark.asyncio
async def test_add_to_sync_chain(connected_dedup_manager: LinearDeduplicationManager):
    """Test adding entry to sync chain."""
    await connected_dedup_manager._add_to_sync_chain(
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    redis = connected_dedup_manager._state_manager._redis_client

    # Verify Redis operations
    redis.rpush.assert_called_once()
    call_args = redis.rpush.call_args
    assert call_args[0][0] == "linear:sync_chain:issue-123"
    assert SYNC_SOURCE_LINEAR in call_args[0][1]
    assert SYNC_SOURCE_GITHUB in call_args[0][1]

    redis.expire.assert_called_once_with(
        "linear:sync_chain:issue-123",
        DEFAULT_SYNC_CHAIN_TTL,
    )

    redis.ltrim.assert_called_once()


@pytest.mark.asyncio
async def test_get_sync_chain_empty(connected_dedup_manager: LinearDeduplicationManager):
    """Test getting empty sync chain."""
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = []

    chain = await connected_dedup_manager._get_sync_chain("issue-123")

    assert chain == []


@pytest.mark.asyncio
async def test_get_sync_chain_with_entries(connected_dedup_manager: LinearDeduplicationManager):
    """Test getting sync chain with entries."""
    expected_chain = [
        f"{SYNC_SOURCE_LINEAR}->{SYNC_SOURCE_GITHUB}:2024-01-01T00:00:00Z",
        f"{SYNC_SOURCE_GITHUB}->{SYNC_SOURCE_LINEAR}:2024-01-01T00:01:00Z",
    ]
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = expected_chain

    chain = await connected_dedup_manager._get_sync_chain("issue-123")

    assert chain == expected_chain


@pytest.mark.asyncio
async def test_get_sync_chain_error(connected_dedup_manager: LinearDeduplicationManager):
    """Test getting sync chain handles errors gracefully."""
    connected_dedup_manager._state_manager._redis_client.lrange.side_effect = Exception(
        "Redis error"
    )

    chain = await connected_dedup_manager._get_sync_chain("issue-123")

    # Should return empty list on error
    assert chain == []


# ============================================================================
# Loop Detection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_would_create_loop_no_chain(connected_dedup_manager: LinearDeduplicationManager):
    """Test loop detection with no existing chain."""
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = []

    would_loop = await connected_dedup_manager.would_create_loop(
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    assert would_loop is False


@pytest.mark.asyncio
async def test_would_create_loop_exact_match(connected_dedup_manager: LinearDeduplicationManager):
    """Test loop detection with exact sync match."""
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = [
        f"{SYNC_SOURCE_LINEAR}->{SYNC_SOURCE_GITHUB}:2024-01-01T00:00:00Z",
    ]

    would_loop = await connected_dedup_manager.would_create_loop(
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    assert would_loop is True


@pytest.mark.asyncio
async def test_would_create_loop_bounce_pattern(
    connected_dedup_manager: LinearDeduplicationManager,
):
    """Test loop detection with bounce pattern (A->B->A)."""
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = [
        f"{SYNC_SOURCE_LINEAR}->{SYNC_SOURCE_GITHUB}:2024-01-01T00:00:00Z",
        f"{SYNC_SOURCE_GITHUB}->{SYNC_SOURCE_LINEAR}:2024-01-01T00:01:00Z",
    ]

    # Trying to sync Linear->GitHub again would create a bounce loop
    would_loop = await connected_dedup_manager.would_create_loop(
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    assert would_loop is True


@pytest.mark.asyncio
async def test_would_create_loop_max_chain_length(
    connected_dedup_manager: LinearDeduplicationManager,
):
    """Test loop detection when chain exceeds max length."""
    # Create a chain that exceeds max length
    chain = [
        f"{SYNC_SOURCE_LINEAR}->{SYNC_SOURCE_GITHUB}:{i}:00:00Z"
        for i in range(MAX_SYNC_CHAIN_LENGTH)
    ]
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = chain

    would_loop = await connected_dedup_manager.would_create_loop(
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    assert would_loop is True


@pytest.mark.asyncio
async def test_would_create_loop_different_sync(
    connected_dedup_manager: LinearDeduplicationManager,
):
    """Test loop detection allows different sync patterns."""
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = [
        f"{SYNC_SOURCE_LINEAR}->{SYNC_SOURCE_GITHUB}:2024-01-01T00:00:00Z",
    ]

    # Different sync should not create loop
    would_loop = await connected_dedup_manager.would_create_loop(
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITLAB,
    )

    assert would_loop is False


@pytest.mark.asyncio
async def test_would_create_loop_error_handling(
    connected_dedup_manager: LinearDeduplicationManager,
):
    """Test loop detection fails safe on error (returns False)."""
    connected_dedup_manager._state_manager._redis_client.lrange.side_effect = Exception(
        "Redis error"
    )

    would_loop = await connected_dedup_manager.would_create_loop(
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    # Should fail safe - assume no loop to allow sync
    assert would_loop is False


# ============================================================================
# Comprehensive Event Processing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_should_process_event_success(connected_dedup_manager: LinearDeduplicationManager):
    """Test should_process_event returns True for valid event."""
    connected_dedup_manager._state_manager.is_duplicate_event.return_value = False
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = []

    should_process = await connected_dedup_manager.should_process_event(
        event_id="event-123",
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    assert should_process is True


@pytest.mark.asyncio
async def test_should_process_event_duplicate(connected_dedup_manager: LinearDeduplicationManager):
    """Test should_process_event returns False for duplicate event."""
    connected_dedup_manager._state_manager.is_duplicate_event.return_value = True

    should_process = await connected_dedup_manager.should_process_event(
        event_id="event-123",
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    assert should_process is False


@pytest.mark.asyncio
async def test_should_process_event_would_create_loop(
    connected_dedup_manager: LinearDeduplicationManager,
):
    """Test should_process_event returns False when would create loop."""
    connected_dedup_manager._state_manager.is_duplicate_event.return_value = False
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = [
        f"{SYNC_SOURCE_LINEAR}->{SYNC_SOURCE_GITHUB}:2024-01-01T00:00:00Z",
    ]

    should_process = await connected_dedup_manager.should_process_event(
        event_id="event-123",
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    assert should_process is False


@pytest.mark.asyncio
async def test_should_process_event_auto_connect(dedup_manager: LinearDeduplicationManager):
    """Test should_process_event auto-connects if not connected."""
    dedup_manager._state_manager.is_duplicate_event.return_value = False
    dedup_manager._state_manager._redis_client.lrange.return_value = []

    await dedup_manager.should_process_event(
        event_id="event-123",
        issue_id="issue-123",
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    assert dedup_manager._connected is True


# ============================================================================
# Event Sources Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_event_sources_empty(connected_dedup_manager: LinearDeduplicationManager):
    """Test getting event sources with no data."""
    connected_dedup_manager._state_manager.get_sync_state.return_value = None
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = []

    sources = await connected_dedup_manager.get_event_sources("issue-123")

    assert sources == []


@pytest.mark.asyncio
async def test_get_event_sources_with_sync_state(
    connected_dedup_manager: LinearDeduplicationManager,
):
    """Test getting event sources with sync state."""
    connected_dedup_manager._state_manager.get_sync_state.return_value = {
        "sync_source": SYNC_SOURCE_LINEAR,
        "last_synced_at": "2024-01-01T00:00:00Z",
        "metadata": {"title": "Test"},
    }
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = []

    sources = await connected_dedup_manager.get_event_sources("issue-123")

    assert len(sources) == 1
    assert sources[0]["type"] == "sync_state"
    assert sources[0]["source"] == SYNC_SOURCE_LINEAR


@pytest.mark.asyncio
async def test_get_event_sources_with_chain(connected_dedup_manager: LinearDeduplicationManager):
    """Test getting event sources with sync chain."""
    connected_dedup_manager._state_manager.get_sync_state.return_value = None
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = [
        f"{SYNC_SOURCE_LINEAR}->{SYNC_SOURCE_GITHUB}:2024-01-01T00:00:00Z",
        f"{SYNC_SOURCE_GITHUB}->{SYNC_SOURCE_LINEAR}:2024-01-01T00:01:00Z",
    ]

    sources = await connected_dedup_manager.get_event_sources("issue-123")

    assert len(sources) == 2
    assert sources[0]["type"] == "sync_chain"
    assert sources[0]["from_source"] == SYNC_SOURCE_LINEAR
    assert sources[0]["to_source"] == SYNC_SOURCE_GITHUB


@pytest.mark.asyncio
async def test_get_event_sources_limit(connected_dedup_manager: LinearDeduplicationManager):
    """Test getting event sources respects limit."""
    connected_dedup_manager._state_manager.get_sync_state.return_value = None
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = [
        f"{SYNC_SOURCE_LINEAR}->{SYNC_SOURCE_GITHUB}:{i}:00:00Z" for i in range(20)
    ]

    sources = await connected_dedup_manager.get_event_sources("issue-123", limit=5)

    assert len(sources) <= 5


@pytest.mark.asyncio
async def test_get_event_sources_error(connected_dedup_manager: LinearDeduplicationManager):
    """Test getting event sources handles errors gracefully."""
    connected_dedup_manager._state_manager.get_sync_state.side_effect = Exception("Redis error")

    sources = await connected_dedup_manager.get_event_sources("issue-123")

    assert sources == []


# ============================================================================
# Clear History Tests
# ============================================================================


@pytest.mark.asyncio
async def test_clear_issue_history_success(connected_dedup_manager: LinearDeduplicationManager):
    """Test successfully clearing issue history."""
    connected_dedup_manager._state_manager.clear_sync_state.return_value = True
    connected_dedup_manager._state_manager._redis_client.delete.return_value = 1

    cleared = await connected_dedup_manager.clear_issue_history("issue-123")

    assert cleared is True
    connected_dedup_manager._state_manager.clear_sync_state.assert_called_once_with("issue-123")
    connected_dedup_manager._state_manager._redis_client.delete.assert_called_once_with(
        "linear:sync_chain:issue-123"
    )


@pytest.mark.asyncio
async def test_clear_issue_history_partial(connected_dedup_manager: LinearDeduplicationManager):
    """Test clearing history when only chain exists."""
    connected_dedup_manager._state_manager.clear_sync_state.return_value = False
    connected_dedup_manager._state_manager._redis_client.delete.return_value = 1

    cleared = await connected_dedup_manager.clear_issue_history("issue-123")

    assert cleared is True


@pytest.mark.asyncio
async def test_clear_issue_history_failure(connected_dedup_manager: LinearDeduplicationManager):
    """Test clearing history raises DeduplicationError on failure."""
    connected_dedup_manager._state_manager.clear_sync_state.side_effect = Exception("Redis error")

    with pytest.raises(DeduplicationError, match="Failed to clear history"):
        await connected_dedup_manager.clear_issue_history("issue-123")


# ============================================================================
# Singleton Tests
# ============================================================================


def test_get_dedup_manager_singleton():
    """Test get_dedup_manager returns singleton instance."""
    # Reset first
    reset_dedup_manager()

    manager1 = get_dedup_manager()
    manager2 = get_dedup_manager()

    assert manager1 is manager2


def test_reset_dedup_manager():
    """Test reset_dedup_manager clears singleton."""
    manager1 = get_dedup_manager()
    reset_dedup_manager()
    manager2 = get_dedup_manager()

    assert manager1 is not manager2


# ============================================================================
# Constants Tests
# ============================================================================


def test_valid_sync_sources():
    """Test all expected sync sources are defined."""
    expected_sources = {
        SYNC_SOURCE_LINEAR,
        SYNC_SOURCE_GITHUB,
        SYNC_SOURCE_GITLAB,
        SYNC_SOURCE_SLACK,
        SYNC_SOURCE_MANUAL,
    }

    assert VALID_SYNC_SOURCES == expected_sources


def test_default_values():
    """Test default TTL and chain length values."""
    assert DEFAULT_EVENT_TTL == 86400 * 3  # 3 days
    assert DEFAULT_SYNC_CHAIN_TTL == 300  # 5 minutes
    assert MAX_SYNC_CHAIN_LENGTH == 5


# ============================================================================
# Integration Tests (Combined Operations)
# ============================================================================


@pytest.mark.asyncio
async def test_full_deduplication_flow(connected_dedup_manager: LinearDeduplicationManager):
    """Test complete deduplication flow: check, mark, record."""
    event_id = "event-123"
    issue_id = "issue-123"

    # Configure mocks for new event
    connected_dedup_manager._state_manager.is_duplicate_event.return_value = False
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = []

    # 1. Check if should process (should be True for new event)
    should_process = await connected_dedup_manager.should_process_event(
        event_id=event_id,
        issue_id=issue_id,
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )
    assert should_process is True

    # 2. Mark event as processed
    await connected_dedup_manager.mark_processed(
        event_id=event_id,
        source=SYNC_SOURCE_LINEAR,
        event_type="webhook",
    )

    # 3. Record the sync
    await connected_dedup_manager.record_sync(
        issue_id=issue_id,
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    # Verify all operations were called
    connected_dedup_manager._state_manager.is_duplicate_event.assert_called()
    connected_dedup_manager._state_manager.mark_event_processed.assert_called()
    connected_dedup_manager._state_manager.record_sync.assert_called()


@pytest.mark.asyncio
async def test_loop_prevention_flow(connected_dedup_manager: LinearDeduplicationManager):
    """Test loop prevention across multiple sync operations."""
    issue_id = "issue-123"

    # Simulate a sync chain: Linear -> GitHub
    await connected_dedup_manager.record_sync(
        issue_id=issue_id,
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    # Mock the chain to have the first sync
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = [
        f"{SYNC_SOURCE_LINEAR}->{SYNC_SOURCE_GITHUB}:2024-01-01T00:00:00Z",
    ]

    # Trying to sync Linear -> GitHub again should create loop
    would_loop = await connected_dedup_manager.would_create_loop(
        issue_id=issue_id,
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    assert would_loop is True


@pytest.mark.asyncio
async def test_multi_source_sync_flow(connected_dedup_manager: LinearDeduplicationManager):
    """Test syncing across multiple sources (Linear -> GitHub -> GitLab)."""
    issue_id = "issue-123"

    # Linear -> GitHub
    await connected_dedup_manager.record_sync(
        issue_id=issue_id,
        from_source=SYNC_SOURCE_LINEAR,
        to_source=SYNC_SOURCE_GITHUB,
    )

    # GitHub -> GitLab (should be allowed)
    connected_dedup_manager._state_manager._redis_client.lrange.return_value = [
        f"{SYNC_SOURCE_LINEAR}->{SYNC_SOURCE_GITHUB}:2024-01-01T00:00:00Z",
    ]

    would_loop = await connected_dedup_manager.would_create_loop(
        issue_id=issue_id,
        from_source=SYNC_SOURCE_GITHUB,
        to_source=SYNC_SOURCE_GITLAB,
    )

    assert would_loop is False
