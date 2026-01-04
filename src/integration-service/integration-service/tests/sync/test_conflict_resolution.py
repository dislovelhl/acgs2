"""
Tests for Linear Conflict Resolution Logic.

Tests cover:
- ConflictResolutionManager initialization and configuration
- Timestamp parsing from various formats
- Timestamp comparison with tolerance
- Last-write-wins conflict resolution
- Source priority resolution for simultaneous updates
- should_apply_update comprehensive checks
- record_update for tracking applied updates
- Conflict history tracking and retrieval
- Async context manager support
- Error handling and edge cases
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.integrations.linear.conflict_resolution import (
    DEFAULT_CONFLICT_TTL,
    SYNC_SOURCE_GITHUB,
    SYNC_SOURCE_GITLAB,
    SYNC_SOURCE_LINEAR,
    SYNC_SOURCE_MANUAL,
    SYNC_SOURCE_SLACK,
    TIMESTAMP_TOLERANCE_SECONDS,
    VALID_SYNC_SOURCES,
    ConflictResolutionError,
    ConflictResolutionManager,
    ConflictTimestampError,
    get_conflict_manager,
    reset_conflict_manager,
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
    manager.get_sync_state = AsyncMock(return_value=None)
    manager.record_sync = AsyncMock()
    # Mock Redis client for conflict tracking
    manager._redis_client = MagicMock()
    manager._redis_client.rpush = AsyncMock()
    manager._redis_client.expire = AsyncMock()
    manager._redis_client.ltrim = AsyncMock()
    manager._redis_client.lrange = AsyncMock(return_value=[])
    manager._redis_client.delete = AsyncMock(return_value=1)
    return manager


@pytest.fixture
def conflict_manager(mock_state_manager):
    """Create a conflict resolution manager for testing."""
    return ConflictResolutionManager(
        state_manager=mock_state_manager,
        conflict_ttl=DEFAULT_CONFLICT_TTL,
        timestamp_tolerance=TIMESTAMP_TOLERANCE_SECONDS,
    )


@pytest.fixture
async def connected_conflict_manager(conflict_manager: ConflictResolutionManager):
    """Create a connected conflict resolution manager for testing."""
    await conflict_manager.connect()
    yield conflict_manager
    await conflict_manager.close()


@pytest.fixture
def sample_update():
    """Create a sample update for testing."""
    return {
        "source": SYNC_SOURCE_LINEAR,
        "updated_at": datetime.now(timezone.utc),
        "title": "Test Issue",
        "description": "Test description",
    }


# ============================================================================
# Initialization Tests
# ============================================================================


def test_conflict_manager_initialization():
    """Test conflict manager initializes with default values."""
    manager = ConflictResolutionManager()

    assert manager._conflict_ttl == DEFAULT_CONFLICT_TTL
    assert manager._timestamp_tolerance == TIMESTAMP_TOLERANCE_SECONDS
    assert not manager._connected
    assert manager._owns_state_manager is True


def test_conflict_manager_initialization_with_custom_values():
    """Test conflict manager initialization with custom values."""
    custom_ttl = 7200
    custom_tolerance = 5

    manager = ConflictResolutionManager(
        conflict_ttl=custom_ttl,
        timestamp_tolerance=custom_tolerance,
    )

    assert manager._conflict_ttl == custom_ttl
    assert manager._timestamp_tolerance == custom_tolerance


def test_conflict_manager_initialization_with_state_manager(mock_state_manager):
    """Test conflict manager initialization with provided state manager."""
    manager = ConflictResolutionManager(state_manager=mock_state_manager)

    assert manager._state_manager == mock_state_manager
    assert manager._owns_state_manager is False


# ============================================================================
# Connection Tests
# ============================================================================


@pytest.mark.asyncio
async def test_connect_success(conflict_manager: ConflictResolutionManager):
    """Test successful connection to Redis."""
    await conflict_manager.connect()

    assert conflict_manager._connected is True
    conflict_manager._state_manager.connect.assert_called_once()


@pytest.mark.asyncio
async def test_connect_already_connected(conflict_manager: ConflictResolutionManager):
    """Test connecting when already connected does nothing."""
    await conflict_manager.connect()
    await conflict_manager.connect()

    # Should only call state manager connect once
    assert conflict_manager._state_manager.connect.call_count == 1


@pytest.mark.asyncio
async def test_connect_failure(conflict_manager: ConflictResolutionManager):
    """Test connection failure raises ConflictResolutionError."""
    conflict_manager._state_manager.connect.side_effect = Exception("Connection failed")

    with pytest.raises(ConflictResolutionError, match="Connection failed"):
        await conflict_manager.connect()

    assert conflict_manager._connected is False


@pytest.mark.asyncio
async def test_close(connected_conflict_manager: ConflictResolutionManager):
    """Test closing connection."""
    await connected_conflict_manager.close()

    assert connected_conflict_manager._connected is False


@pytest.mark.asyncio
async def test_close_with_owned_state_manager(mock_state_manager):
    """Test closing calls state manager close when owned."""
    manager = ConflictResolutionManager()
    manager._state_manager = mock_state_manager
    manager._owns_state_manager = True
    await manager.connect()

    await manager.close()

    mock_state_manager.close.assert_called_once()


@pytest.mark.asyncio
async def test_close_without_owned_state_manager(mock_state_manager):
    """Test closing does not call state manager close when not owned."""
    manager = ConflictResolutionManager(state_manager=mock_state_manager)
    await manager.connect()

    await manager.close()

    # Should not close state manager when not owned
    mock_state_manager.close.assert_not_called()


# ============================================================================
# Context Manager Tests
# ============================================================================


@pytest.mark.asyncio
async def test_context_manager(conflict_manager: ConflictResolutionManager):
    """Test async context manager support."""
    async with conflict_manager as manager:
        assert manager._connected is True
        assert manager == conflict_manager

    assert conflict_manager._connected is False


# ============================================================================
# Timestamp Parsing Tests
# ============================================================================


def test_parse_timestamp_from_datetime_with_tz(conflict_manager: ConflictResolutionManager):
    """Test parsing timestamp from datetime with timezone."""
    dt = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    parsed = conflict_manager._parse_timestamp(dt)

    assert parsed == dt
    assert parsed.tzinfo is not None


def test_parse_timestamp_from_datetime_without_tz(conflict_manager: ConflictResolutionManager):
    """Test parsing timestamp from datetime without timezone."""
    dt = datetime(2024, 1, 1, 10, 0, 0)  # Naive datetime
    parsed = conflict_manager._parse_timestamp(dt)

    assert parsed.tzinfo is not None
    assert parsed == dt.replace(tzinfo=timezone.utc)


def test_parse_timestamp_from_iso_string(conflict_manager: ConflictResolutionManager):
    """Test parsing timestamp from ISO string."""
    iso_str = "2024-01-01T10:00:00Z"
    parsed = conflict_manager._parse_timestamp(iso_str)

    assert isinstance(parsed, datetime)
    assert parsed.year == 2024
    assert parsed.month == 1
    assert parsed.day == 1
    assert parsed.hour == 10


def test_parse_timestamp_from_iso_string_with_offset(conflict_manager: ConflictResolutionManager):
    """Test parsing timestamp from ISO string with offset."""
    iso_str = "2024-01-01T10:00:00+00:00"
    parsed = conflict_manager._parse_timestamp(iso_str)

    assert isinstance(parsed, datetime)
    assert parsed.tzinfo is not None


def test_parse_timestamp_invalid_format(conflict_manager: ConflictResolutionManager):
    """Test parsing invalid timestamp raises ConflictTimestampError."""
    with pytest.raises(ConflictTimestampError, match="Failed to parse timestamp"):
        conflict_manager._parse_timestamp("invalid-timestamp")


def test_parse_timestamp_invalid_type(conflict_manager: ConflictResolutionManager):
    """Test parsing invalid timestamp type raises ConflictTimestampError."""
    with pytest.raises(ConflictTimestampError, match="Unsupported timestamp type"):
        conflict_manager._parse_timestamp(12345)


# ============================================================================
# Timestamp Comparison Tests
# ============================================================================


def test_compare_timestamps_a_newer(conflict_manager: ConflictResolutionManager):
    """Test comparing timestamps when A is newer."""
    timestamp_a = datetime(2024, 1, 1, 10, 0, 5, tzinfo=timezone.utc)
    timestamp_b = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    result = conflict_manager._compare_timestamps(timestamp_a, timestamp_b)

    assert result == 1


def test_compare_timestamps_b_newer(conflict_manager: ConflictResolutionManager):
    """Test comparing timestamps when B is newer."""
    timestamp_a = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    timestamp_b = datetime(2024, 1, 1, 10, 0, 5, tzinfo=timezone.utc)

    result = conflict_manager._compare_timestamps(timestamp_a, timestamp_b)

    assert result == -1


def test_compare_timestamps_simultaneous_within_tolerance(
    conflict_manager: ConflictResolutionManager,
):
    """Test comparing timestamps within tolerance (simultaneous)."""
    timestamp_a = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    timestamp_b = datetime(2024, 1, 1, 10, 0, 0, 500000, tzinfo=timezone.utc)  # 0.5 seconds later

    result = conflict_manager._compare_timestamps(timestamp_a, timestamp_b)

    # Within 1 second tolerance - should be considered simultaneous
    assert result == 0


def test_compare_timestamps_exactly_equal(conflict_manager: ConflictResolutionManager):
    """Test comparing identical timestamps."""
    timestamp = datetime(2024, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    result = conflict_manager._compare_timestamps(timestamp, timestamp)

    assert result == 0


# ============================================================================
# Source Priority Tests
# ============================================================================


def test_resolve_by_source_priority_manual_wins(conflict_manager: ConflictResolutionManager):
    """Test source priority resolution - manual beats all."""
    update_manual = {"source": SYNC_SOURCE_MANUAL, "updated_at": "2024-01-01T10:00:00Z"}
    update_linear = {"source": SYNC_SOURCE_LINEAR, "updated_at": "2024-01-01T10:00:00Z"}

    winner = conflict_manager._resolve_by_source_priority(update_manual, update_linear)

    assert winner["source"] == SYNC_SOURCE_MANUAL


def test_resolve_by_source_priority_linear_beats_github(
    conflict_manager: ConflictResolutionManager,
):
    """Test source priority resolution - linear beats github."""
    update_linear = {"source": SYNC_SOURCE_LINEAR, "updated_at": "2024-01-01T10:00:00Z"}
    update_github = {"source": SYNC_SOURCE_GITHUB, "updated_at": "2024-01-01T10:00:00Z"}

    winner = conflict_manager._resolve_by_source_priority(update_linear, update_github)

    assert winner["source"] == SYNC_SOURCE_LINEAR


def test_resolve_by_source_priority_github_beats_gitlab(
    conflict_manager: ConflictResolutionManager,
):
    """Test source priority resolution - github beats gitlab."""
    update_github = {"source": SYNC_SOURCE_GITHUB, "updated_at": "2024-01-01T10:00:00Z"}
    update_gitlab = {"source": SYNC_SOURCE_GITLAB, "updated_at": "2024-01-01T10:00:00Z"}

    winner = conflict_manager._resolve_by_source_priority(update_github, update_gitlab)

    assert winner["source"] == SYNC_SOURCE_GITHUB


def test_resolve_by_source_priority_gitlab_beats_slack(conflict_manager: ConflictResolutionManager):
    """Test source priority resolution - gitlab beats slack."""
    update_gitlab = {"source": SYNC_SOURCE_GITLAB, "updated_at": "2024-01-01T10:00:00Z"}
    update_slack = {"source": SYNC_SOURCE_SLACK, "updated_at": "2024-01-01T10:00:00Z"}

    winner = conflict_manager._resolve_by_source_priority(update_gitlab, update_slack)

    assert winner["source"] == SYNC_SOURCE_GITLAB


def test_resolve_by_source_priority_unknown_source_loses(
    conflict_manager: ConflictResolutionManager,
):
    """Test source priority resolution - unknown source has lowest priority."""
    update_unknown = {"source": "unknown", "updated_at": "2024-01-01T10:00:00Z"}
    update_slack = {"source": SYNC_SOURCE_SLACK, "updated_at": "2024-01-01T10:00:00Z"}

    winner = conflict_manager._resolve_by_source_priority(update_unknown, update_slack)

    assert winner["source"] == SYNC_SOURCE_SLACK


# ============================================================================
# Conflict Resolution Tests
# ============================================================================


@pytest.mark.asyncio
async def test_resolve_conflict_timestamp_a_wins(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test conflict resolution when update A has newer timestamp."""
    update_a = {
        "source": SYNC_SOURCE_GITHUB,
        "updated_at": "2024-01-01T10:00:05Z",
        "title": "Updated title A",
    }
    update_b = {
        "source": SYNC_SOURCE_LINEAR,
        "updated_at": "2024-01-01T10:00:00Z",
        "title": "Updated title B",
    }

    winner = await connected_conflict_manager.resolve_conflict("issue-123", update_a, update_b)

    assert winner == update_a
    assert winner["source"] == SYNC_SOURCE_GITHUB


@pytest.mark.asyncio
async def test_resolve_conflict_timestamp_b_wins(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test conflict resolution when update B has newer timestamp."""
    update_a = {
        "source": SYNC_SOURCE_GITHUB,
        "updated_at": "2024-01-01T10:00:00Z",
        "title": "Updated title A",
    }
    update_b = {
        "source": SYNC_SOURCE_LINEAR,
        "updated_at": "2024-01-01T10:00:05Z",
        "title": "Updated title B",
    }

    winner = await connected_conflict_manager.resolve_conflict("issue-123", update_a, update_b)

    assert winner == update_b
    assert winner["source"] == SYNC_SOURCE_LINEAR


@pytest.mark.asyncio
async def test_resolve_conflict_simultaneous_uses_source_priority(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test conflict resolution for simultaneous updates uses source priority."""
    update_a = {
        "source": SYNC_SOURCE_GITHUB,
        "updated_at": "2024-01-01T10:00:00Z",
        "title": "Updated title A",
    }
    update_b = {
        "source": SYNC_SOURCE_LINEAR,
        "updated_at": "2024-01-01T10:00:00Z",
        "title": "Updated title B",
    }

    winner = await connected_conflict_manager.resolve_conflict("issue-123", update_a, update_b)

    # Linear has higher priority than GitHub
    assert winner == update_b
    assert winner["source"] == SYNC_SOURCE_LINEAR


@pytest.mark.asyncio
async def test_resolve_conflict_records_conflict(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test conflict resolution records conflict in Redis."""
    update_a = {
        "source": SYNC_SOURCE_GITHUB,
        "updated_at": "2024-01-01T10:00:05Z",
        "title": "Updated title A",
    }
    update_b = {
        "source": SYNC_SOURCE_LINEAR,
        "updated_at": "2024-01-01T10:00:00Z",
        "title": "Updated title B",
    }

    await connected_conflict_manager.resolve_conflict("issue-123", update_a, update_b)

    # Verify conflict was recorded
    redis_client = connected_conflict_manager._state_manager._redis_client
    redis_client.rpush.assert_called_once()
    redis_client.expire.assert_called_once()
    redis_client.ltrim.assert_called_once()


@pytest.mark.asyncio
async def test_resolve_conflict_missing_source(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test conflict resolution with missing source raises ValueError."""
    update_a = {
        "updated_at": "2024-01-01T10:00:00Z",
        "title": "Updated title A",
    }
    update_b = {
        "source": SYNC_SOURCE_LINEAR,
        "updated_at": "2024-01-01T10:00:05Z",
        "title": "Updated title B",
    }

    with pytest.raises(ValueError, match="missing required fields"):
        await connected_conflict_manager.resolve_conflict("issue-123", update_a, update_b)


@pytest.mark.asyncio
async def test_resolve_conflict_missing_updated_at(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test conflict resolution with missing updated_at raises ValueError."""
    update_a = {
        "source": SYNC_SOURCE_GITHUB,
        "title": "Updated title A",
    }
    update_b = {
        "source": SYNC_SOURCE_LINEAR,
        "updated_at": "2024-01-01T10:00:05Z",
        "title": "Updated title B",
    }

    with pytest.raises(ValueError, match="missing required fields"):
        await connected_conflict_manager.resolve_conflict("issue-123", update_a, update_b)


@pytest.mark.asyncio
async def test_resolve_conflict_auto_connect(conflict_manager: ConflictResolutionManager):
    """Test conflict resolution auto-connects if not connected."""
    update_a = {
        "source": SYNC_SOURCE_GITHUB,
        "updated_at": "2024-01-01T10:00:05Z",
        "title": "Updated title A",
    }
    update_b = {
        "source": SYNC_SOURCE_LINEAR,
        "updated_at": "2024-01-01T10:00:00Z",
        "title": "Updated title B",
    }

    assert not conflict_manager._connected

    await conflict_manager.resolve_conflict("issue-123", update_a, update_b)

    assert conflict_manager._connected


# ============================================================================
# should_apply_update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_should_apply_update_no_previous_state(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test should_apply_update returns True when no previous state exists."""
    # Mock state manager to return None (no previous state)
    connected_conflict_manager._state_manager.get_sync_state.return_value = None

    result = await connected_conflict_manager.should_apply_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_GITHUB,
        updated_at="2024-01-01T10:00:00Z",
    )

    assert result is True


@pytest.mark.asyncio
async def test_should_apply_update_newer_timestamp(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test should_apply_update returns True for newer timestamp."""
    # Mock state manager to return older state
    connected_conflict_manager._state_manager.get_sync_state.return_value = {
        "last_synced_at": "2024-01-01T09:00:00Z",
        "sync_source": SYNC_SOURCE_LINEAR,
    }

    result = await connected_conflict_manager.should_apply_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_GITHUB,
        updated_at="2024-01-01T10:00:00Z",
    )

    assert result is True


@pytest.mark.asyncio
async def test_should_apply_update_older_timestamp(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test should_apply_update returns False for older timestamp."""
    # Mock state manager to return newer state
    connected_conflict_manager._state_manager.get_sync_state.return_value = {
        "last_synced_at": "2024-01-01T11:00:00Z",
        "sync_source": SYNC_SOURCE_LINEAR,
    }

    result = await connected_conflict_manager.should_apply_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_GITHUB,
        updated_at="2024-01-01T10:00:00Z",
    )

    assert result is False


@pytest.mark.asyncio
async def test_should_apply_update_simultaneous_higher_priority(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test should_apply_update returns True for simultaneous update with higher priority."""
    # Mock state manager to return simultaneous state with lower priority source
    connected_conflict_manager._state_manager.get_sync_state.return_value = {
        "last_synced_at": "2024-01-01T10:00:00Z",
        "sync_source": SYNC_SOURCE_GITHUB,
    }

    result = await connected_conflict_manager.should_apply_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_LINEAR,  # Linear has higher priority than GitHub
        updated_at="2024-01-01T10:00:00Z",
    )

    assert result is True


@pytest.mark.asyncio
async def test_should_apply_update_simultaneous_lower_priority(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test should_apply_update returns False for simultaneous update with lower priority."""
    # Mock state manager to return simultaneous state with higher priority source
    connected_conflict_manager._state_manager.get_sync_state.return_value = {
        "last_synced_at": "2024-01-01T10:00:00Z",
        "sync_source": SYNC_SOURCE_LINEAR,
    }

    result = await connected_conflict_manager.should_apply_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_GITHUB,  # GitHub has lower priority than Linear
        updated_at="2024-01-01T10:00:00Z",
    )

    assert result is False


@pytest.mark.asyncio
async def test_should_apply_update_invalid_source(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test should_apply_update raises ValueError for invalid source."""
    with pytest.raises(ValueError, match="Invalid source"):
        await connected_conflict_manager.should_apply_update(
            issue_id="issue-123",
            source="invalid-source",
            updated_at="2024-01-01T10:00:00Z",
        )


@pytest.mark.asyncio
async def test_should_apply_update_auto_connect(conflict_manager: ConflictResolutionManager):
    """Test should_apply_update auto-connects if not connected."""
    conflict_manager._state_manager.get_sync_state.return_value = None

    assert not conflict_manager._connected

    await conflict_manager.should_apply_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_GITHUB,
        updated_at="2024-01-01T10:00:00Z",
    )

    assert conflict_manager._connected


# ============================================================================
# record_update Tests
# ============================================================================


@pytest.mark.asyncio
async def test_record_update_success(connected_conflict_manager: ConflictResolutionManager):
    """Test recording update successfully."""
    await connected_conflict_manager.record_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_GITHUB,
        updated_at="2024-01-01T10:00:00Z",
    )

    # Verify state manager record_sync was called
    connected_conflict_manager._state_manager.record_sync.assert_called_once()
    call_args = connected_conflict_manager._state_manager.record_sync.call_args

    assert call_args[1]["issue_id"] == "issue-123"
    assert call_args[1]["sync_source"] == SYNC_SOURCE_GITHUB
    assert "metadata" in call_args[1]


@pytest.mark.asyncio
async def test_record_update_with_metadata(connected_conflict_manager: ConflictResolutionManager):
    """Test recording update with custom metadata."""
    metadata = {"title": "Test Issue", "description": "Test description"}

    await connected_conflict_manager.record_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_GITHUB,
        updated_at="2024-01-01T10:00:00Z",
        metadata=metadata,
    )

    # Verify metadata was included
    call_args = connected_conflict_manager._state_manager.record_sync.call_args
    saved_metadata = call_args[1]["metadata"]

    assert saved_metadata["title"] == "Test Issue"
    assert saved_metadata["description"] == "Test description"
    assert "updated_at" in saved_metadata
    assert "recorded_at" in saved_metadata


@pytest.mark.asyncio
async def test_record_update_invalid_source(connected_conflict_manager: ConflictResolutionManager):
    """Test recording update with invalid source raises ValueError."""
    with pytest.raises(ValueError, match="Invalid source"):
        await connected_conflict_manager.record_update(
            issue_id="issue-123",
            source="invalid-source",
            updated_at="2024-01-01T10:00:00Z",
        )


@pytest.mark.asyncio
async def test_record_update_auto_connect(conflict_manager: ConflictResolutionManager):
    """Test record_update auto-connects if not connected."""
    assert not conflict_manager._connected

    await conflict_manager.record_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_GITHUB,
        updated_at="2024-01-01T10:00:00Z",
    )

    assert conflict_manager._connected


# ============================================================================
# Conflict History Tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_conflict_history_empty(connected_conflict_manager: ConflictResolutionManager):
    """Test getting conflict history when no conflicts exist."""
    connected_conflict_manager._state_manager._redis_client.lrange.return_value = []

    history = await connected_conflict_manager.get_conflict_history("issue-123")

    assert history == []


@pytest.mark.asyncio
async def test_get_conflict_history_with_conflicts(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test getting conflict history with existing conflicts."""
    conflict_data = [
        json.dumps(
            {
                "issue_id": "issue-123",
                "detected_at": "2024-01-01T10:00:00Z",
                "update_a": {"source": "github", "updated_at": "2024-01-01T09:00:00Z"},
                "update_b": {"source": "linear", "updated_at": "2024-01-01T10:00:00Z"},
                "winner": {"source": "linear", "updated_at": "2024-01-01T10:00:00Z"},
                "resolution_method": "timestamp",
                "timestamp_diff_seconds": 3600,
            }
        ),
    ]
    connected_conflict_manager._state_manager._redis_client.lrange.return_value = conflict_data

    history = await connected_conflict_manager.get_conflict_history("issue-123")

    assert len(history) == 1
    assert history[0]["issue_id"] == "issue-123"
    assert history[0]["winner"]["source"] == "linear"
    assert history[0]["resolution_method"] == "timestamp"


@pytest.mark.asyncio
async def test_get_conflict_history_with_limit(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test getting conflict history respects limit parameter."""
    await connected_conflict_manager.get_conflict_history("issue-123", limit=5)

    # Verify Redis lrange called with correct limit
    redis_client = connected_conflict_manager._state_manager._redis_client
    redis_client.lrange.assert_called_once()
    call_args = redis_client.lrange.call_args[0]
    assert call_args[1] == -5  # Negative limit for recent entries


@pytest.mark.asyncio
async def test_get_conflict_history_auto_connect(conflict_manager: ConflictResolutionManager):
    """Test get_conflict_history auto-connects if not connected."""
    conflict_manager._state_manager._redis_client.lrange.return_value = []

    assert not conflict_manager._connected

    await conflict_manager.get_conflict_history("issue-123")

    assert conflict_manager._connected


@pytest.mark.asyncio
async def test_clear_conflict_history_success(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test clearing conflict history successfully."""
    connected_conflict_manager._state_manager._redis_client.delete.return_value = 1

    result = await connected_conflict_manager.clear_conflict_history("issue-123")

    assert result is True
    connected_conflict_manager._state_manager._redis_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_clear_conflict_history_no_history(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test clearing conflict history when no history exists."""
    connected_conflict_manager._state_manager._redis_client.delete.return_value = 0

    result = await connected_conflict_manager.clear_conflict_history("issue-123")

    assert result is False


@pytest.mark.asyncio
async def test_clear_conflict_history_auto_connect(conflict_manager: ConflictResolutionManager):
    """Test clear_conflict_history auto-connects if not connected."""
    conflict_manager._state_manager._redis_client.delete.return_value = 1

    assert not conflict_manager._connected

    await conflict_manager.clear_conflict_history("issue-123")

    assert conflict_manager._connected


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


def test_get_conflict_manager_singleton():
    """Test get_conflict_manager returns singleton instance."""
    reset_conflict_manager()

    manager1 = get_conflict_manager()
    manager2 = get_conflict_manager()

    assert manager1 is manager2


def test_reset_conflict_manager():
    """Test reset_conflict_manager clears singleton."""
    manager1 = get_conflict_manager()
    reset_conflict_manager()
    manager2 = get_conflict_manager()

    assert manager1 is not manager2


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.asyncio
async def test_resolve_conflict_state_manager_error(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test resolve_conflict handles state manager errors gracefully."""
    # Make Redis operations fail, but conflict resolution should still work
    connected_conflict_manager._state_manager._redis_client.rpush.side_effect = Exception(
        "Redis error"
    )

    update_a = {
        "source": SYNC_SOURCE_GITHUB,
        "updated_at": "2024-01-01T10:00:05Z",
        "title": "Updated title A",
    }
    update_b = {
        "source": SYNC_SOURCE_LINEAR,
        "updated_at": "2024-01-01T10:00:00Z",
        "title": "Updated title B",
    }

    # Should not raise - conflict recording is non-critical
    winner = await connected_conflict_manager.resolve_conflict("issue-123", update_a, update_b)

    assert winner == update_a


@pytest.mark.asyncio
async def test_should_apply_update_state_manager_error(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test should_apply_update raises error when state manager fails."""
    connected_conflict_manager._state_manager.get_sync_state.side_effect = Exception("Redis error")

    with pytest.raises(ConflictResolutionError, match="Update check failed"):
        await connected_conflict_manager.should_apply_update(
            issue_id="issue-123",
            source=SYNC_SOURCE_GITHUB,
            updated_at="2024-01-01T10:00:00Z",
        )


@pytest.mark.asyncio
async def test_record_update_state_manager_error(
    connected_conflict_manager: ConflictResolutionManager,
):
    """Test record_update raises error when state manager fails."""
    connected_conflict_manager._state_manager.record_sync.side_effect = Exception("Redis error")

    with pytest.raises(ConflictResolutionError, match="Failed to record update"):
        await connected_conflict_manager.record_update(
            issue_id="issue-123",
            source=SYNC_SOURCE_GITHUB,
            updated_at="2024-01-01T10:00:00Z",
        )


@pytest.mark.asyncio
async def test_get_conflict_history_error(connected_conflict_manager: ConflictResolutionManager):
    """Test get_conflict_history raises error when Redis fails."""
    connected_conflict_manager._state_manager._redis_client.lrange.side_effect = Exception(
        "Redis error"
    )

    with pytest.raises(ConflictResolutionError, match="Failed to get conflict history"):
        await connected_conflict_manager.get_conflict_history("issue-123")


@pytest.mark.asyncio
async def test_clear_conflict_history_error(connected_conflict_manager: ConflictResolutionManager):
    """Test clear_conflict_history raises error when Redis fails."""
    connected_conflict_manager._state_manager._redis_client.delete.side_effect = Exception(
        "Redis error"
    )

    with pytest.raises(ConflictResolutionError, match="Failed to clear conflict history"):
        await connected_conflict_manager.clear_conflict_history("issue-123")


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.asyncio
async def test_full_conflict_resolution_flow(connected_conflict_manager: ConflictResolutionManager):
    """Test complete conflict resolution flow."""
    # Setup: No previous state
    connected_conflict_manager._state_manager.get_sync_state.return_value = None

    # 1. Check if update should be applied (no previous state)
    should_apply = await connected_conflict_manager.should_apply_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_GITHUB,
        updated_at="2024-01-01T10:00:00Z",
    )
    assert should_apply is True

    # 2. Record the update
    await connected_conflict_manager.record_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_GITHUB,
        updated_at="2024-01-01T10:00:00Z",
    )

    # 3. Simulate concurrent update from Linear
    connected_conflict_manager._state_manager.get_sync_state.return_value = {
        "last_synced_at": "2024-01-01T10:00:00Z",
        "sync_source": SYNC_SOURCE_GITHUB,
    }

    # 4. Check if newer update should be applied
    should_apply = await connected_conflict_manager.should_apply_update(
        issue_id="issue-123",
        source=SYNC_SOURCE_LINEAR,
        updated_at="2024-01-01T10:00:05Z",
    )
    assert should_apply is True  # Newer timestamp

    # 5. Verify state manager was called correctly
    assert connected_conflict_manager._state_manager.get_sync_state.called
    assert connected_conflict_manager._state_manager.record_sync.called


@pytest.mark.asyncio
async def test_constants_validation():
    """Test that constants are properly defined."""
    assert DEFAULT_CONFLICT_TTL == 86400 * 30  # 30 days
    assert TIMESTAMP_TOLERANCE_SECONDS == 1  # 1 second

    # Verify sync sources match deduplication.py
    assert SYNC_SOURCE_LINEAR == "linear"
    assert SYNC_SOURCE_GITHUB == "github"
    assert SYNC_SOURCE_GITLAB == "gitlab"
    assert SYNC_SOURCE_SLACK == "slack"
    assert SYNC_SOURCE_MANUAL == "manual"

    # Verify valid sources set
    assert len(VALID_SYNC_SOURCES) == 5
    assert SYNC_SOURCE_LINEAR in VALID_SYNC_SOURCES
    assert SYNC_SOURCE_GITHUB in VALID_SYNC_SOURCES
    assert SYNC_SOURCE_GITLAB in VALID_SYNC_SOURCES
    assert SYNC_SOURCE_SLACK in VALID_SYNC_SOURCES
    assert SYNC_SOURCE_MANUAL in VALID_SYNC_SOURCES
