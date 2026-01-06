"""
Conflict Resolution for Linear Sync Operations

Implements last-write-wins conflict resolution strategy using timestamp
tracking in Redis to handle simultaneous updates from multiple sources
(Linear, GitHub, GitLab, Slack).

Features:
- Last-write-wins strategy based on update timestamps
- Conflict tracking and logging for auditing
- Support for multiple sync sources
- Redis-backed state persistence
- Comprehensive metadata tracking

Architecture:
- Each update includes a timestamp (from API or generated)
- Before syncing, compare timestamps to determine winner
- Track conflicts in Redis for debugging and auditing
- Record resolution decisions for transparency
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .state import LinearStateManager, get_state_manager

logger = logging.getLogger(__name__)

# Constants for conflict resolution
DEFAULT_CONFLICT_TTL = 86400 * 30  # 30 days for conflict history
TIMESTAMP_TOLERANCE_SECONDS = 1  # Consider updates within 1s as simultaneous

# Sync sources (must match deduplication.py)
SYNC_SOURCE_LINEAR = "linear"
SYNC_SOURCE_GITHUB = "github"
SYNC_SOURCE_GITLAB = "gitlab"
SYNC_SOURCE_SLACK = "slack"
SYNC_SOURCE_MANUAL = "manual"

VALID_SYNC_SOURCES = {
    SYNC_SOURCE_LINEAR,
    SYNC_SOURCE_GITHUB,
    SYNC_SOURCE_GITLAB,
    SYNC_SOURCE_SLACK,
    SYNC_SOURCE_MANUAL,
}


class ConflictResolutionError(Exception):
    """Base exception for conflict resolution errors."""

    pass


class ConflictTimestampError(ConflictResolutionError):
    """Raised when timestamp comparison fails."""

    pass


class ConflictResolutionManager:
    """
    Manages conflict resolution for Linear sync operations.

    Implements last-write-wins strategy to handle simultaneous updates
    from multiple sources using timestamp comparison.

    Usage:
        conflict_mgr = ConflictResolutionManager()
        await conflict_mgr.connect()

        # Resolve conflict between two updates
        winner = await conflict_mgr.resolve_conflict(
            issue_id="issue-123",
            update_a={"source": "linear", "updated_at": "2024-01-01T10:00:00Z", ...},
            update_b={"source": "github", "updated_at": "2024-01-01T10:00:05Z", ...},
        )

        # Check if update should be applied
        should_apply = await conflict_mgr.should_apply_update(
            issue_id="issue-123",
            source="github",
            updated_at="2024-01-01T10:00:00Z",
        )

        await conflict_mgr.close()
    """

    def __init__(
        self,
        state_manager: Optional[LinearStateManager] = None,
        conflict_ttl: int = DEFAULT_CONFLICT_TTL,
        timestamp_tolerance: int = TIMESTAMP_TOLERANCE_SECONDS,
    ):
        """
        Initialize conflict resolution manager.

        Args:
            state_manager: Optional pre-configured state manager
            conflict_ttl: TTL for conflict records in seconds
            timestamp_tolerance: Tolerance for timestamp comparison in seconds
        """
        self._state_manager = state_manager or get_state_manager()
        self._owns_state_manager = state_manager is None
        self._conflict_ttl = conflict_ttl
        self._timestamp_tolerance = timestamp_tolerance
        self._connected = False

    async def connect(self) -> None:
        """
        Establish connection to Redis.

        Raises:
            ConflictResolutionError: If connection fails
        """
        if self._connected:
            return

        try:
            await self._state_manager.connect()
            self._connected = True
            logger.info("Conflict resolution manager connected")
        except Exception as e:
            logger.error(f"Failed to connect conflict resolution manager: {e}")
            raise ConflictResolutionError(f"Connection failed: {e}") from e

    async def close(self) -> None:
        """Close connection to Redis if owned by this manager."""
        if self._owns_state_manager:
            await self._state_manager.close()
        self._connected = False
        logger.info("Conflict resolution manager disconnected")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _get_conflict_key(self, issue_id: str) -> str:
        """
        Get Redis key for conflict tracking.

        Args:
            issue_id: Issue identifier

        Returns:
            Redis key string
        """
        return f"linear:conflict:{issue_id}"

    def _parse_timestamp(self, timestamp: Any) -> datetime:
        """
        Parse timestamp from various formats.

        Args:
            timestamp: Timestamp as string, datetime, or ISO format

        Returns:
            datetime object in UTC

        Raises:
            ConflictTimestampError: If timestamp parsing fails
        """
        try:
            if isinstance(timestamp, datetime):
                # Ensure UTC timezone
                if timestamp.tzinfo is None:
                    return timestamp.replace(tzinfo=timezone.utc)
                return timestamp.astimezone(timezone.utc)

            if isinstance(timestamp, str):
                # Try parsing ISO format
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)

            raise ValueError(f"Unsupported timestamp type: {type(timestamp)}")

        except (ValueError, AttributeError) as e:
            raise ConflictTimestampError(f"Failed to parse timestamp '{timestamp}': {e}") from e

    def _compare_timestamps(
        self,
        timestamp_a: datetime,
        timestamp_b: datetime,
    ) -> int:
        """
        Compare two timestamps considering tolerance.

        Args:
            timestamp_a: First timestamp
            timestamp_b: Second timestamp

        Returns:
            1 if A is newer, -1 if B is newer, 0 if simultaneous
        """
        diff = (timestamp_a - timestamp_b).total_seconds()

        if abs(diff) <= self._timestamp_tolerance:
            # Timestamps are within tolerance - consider simultaneous
            return 0

        return 1 if diff > 0 else -1

    async def resolve_conflict(
        self,
        issue_id: str,
        update_a: Dict[str, Any],
        update_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Resolve conflict between two updates using last-write-wins.

        Args:
            issue_id: Issue identifier
            update_a: First update with 'source', 'updated_at', and data
            update_b: Second update with 'source', 'updated_at', and data

        Returns:
            Dict: The winning update (most recent)

        Raises:
            ConflictResolutionError: If resolution fails
            ValueError: If update data is invalid
        """
        if not self._connected:
            await self.connect()

        try:
            # Validate input
            if "source" not in update_a or "updated_at" not in update_a:
                raise ValueError("update_a missing required fields: source, updated_at")
            if "source" not in update_b or "updated_at" not in update_b:
                raise ValueError("update_b missing required fields: source, updated_at")

            # Parse timestamps
            timestamp_a = self._parse_timestamp(update_a["updated_at"])
            timestamp_b = self._parse_timestamp(update_b["updated_at"])

            # Compare timestamps
            comparison = self._compare_timestamps(timestamp_a, timestamp_b)

            if comparison == 0:
                # Simultaneous updates - use source priority
                winner = self._resolve_by_source_priority(update_a, update_b)
                logger.info(
                    f"Conflict for {issue_id}: Simultaneous updates, using source priority. "
                    f"Winner: {winner['source']}"
                )
            elif comparison > 0:
                winner = update_a
                logger.info(
                    f"Conflict for {issue_id}: {update_a['source']} wins "
                    f"({timestamp_a} > {timestamp_b})"
                )
            else:
                winner = update_b
                logger.info(
                    f"Conflict for {issue_id}: {update_b['source']} wins "
                    f"({timestamp_b} > {timestamp_a})"
                )

            # Record conflict for auditing
            await self._record_conflict(
                issue_id=issue_id,
                update_a=update_a,
                update_b=update_b,
                winner=winner,
                comparison=comparison,
            )

            return winner

        except ConflictTimestampError:
            raise
        except Exception as e:
            logger.error(f"Failed to resolve conflict for {issue_id}: {e}")
            raise ConflictResolutionError(f"Conflict resolution failed: {e}") from e

    def _resolve_by_source_priority(
        self,
        update_a: Dict[str, Any],
        update_b: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Resolve simultaneous updates by source priority.

        Priority order (highest to lowest):
        1. manual (explicit user action)
        2. linear (source of truth)
        3. github (development platform)
        4. gitlab (development platform)
        5. slack (notification only)

        Args:
            update_a: First update
            update_b: Second update

        Returns:
            Dict: The update from higher priority source
        """
        priority_order = [
            SYNC_SOURCE_MANUAL,
            SYNC_SOURCE_LINEAR,
            SYNC_SOURCE_GITHUB,
            SYNC_SOURCE_GITLAB,
            SYNC_SOURCE_SLACK,
        ]

        source_a = update_a["source"]
        source_b = update_b["source"]

        try:
            priority_a = priority_order.index(source_a)
        except ValueError:
            priority_a = 999  # Unknown source, lowest priority

        try:
            priority_b = priority_order.index(source_b)
        except ValueError:
            priority_b = 999

        if priority_a <= priority_b:
            return update_a
        else:
            return update_b

    async def _record_conflict(
        self,
        issue_id: str,
        update_a: Dict[str, Any],
        update_b: Dict[str, Any],
        winner: Dict[str, Any],
        comparison: int,
    ) -> None:
        """
        Record conflict details in Redis for auditing.

        Args:
            issue_id: Issue identifier
            update_a: First update
            update_b: Second update
            winner: Winning update
            comparison: Timestamp comparison result
        """
        if not self._connected:
            await self.connect()

        try:
            redis = self._state_manager._redis_client
            conflict_key = self._get_conflict_key(issue_id)

            conflict_data = {
                "issue_id": issue_id,
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "update_a": {
                    "source": update_a["source"],
                    "updated_at": str(update_a["updated_at"]),
                },
                "update_b": {
                    "source": update_b["source"],
                    "updated_at": str(update_b["updated_at"]),
                },
                "winner": {
                    "source": winner["source"],
                    "updated_at": str(winner["updated_at"]),
                },
                "resolution_method": "timestamp" if comparison != 0 else "source_priority",
                "timestamp_diff_seconds": abs(
                    (
                        self._parse_timestamp(update_a["updated_at"])
                        - self._parse_timestamp(update_b["updated_at"])
                    ).total_seconds()
                ),
            }

            # Add to conflict list (Redis list for history)
            import json

            await redis.rpush(conflict_key, json.dumps(conflict_data))
            await redis.expire(conflict_key, self._conflict_ttl)

            # Keep only recent conflicts (last 100)
            await redis.ltrim(conflict_key, -100, -1)

        except Exception as e:
            logger.error(f"Failed to record conflict for {issue_id}: {e}")
            # Don't raise - conflict recording is non-critical

    async def should_apply_update(
        self,
        issue_id: str,
        source: str,
        updated_at: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Determine if an update should be applied based on last-write-wins.

        Compares the update timestamp with the last known sync state.

        Args:
            issue_id: Issue identifier
            source: Source of the update
            updated_at: Update timestamp
            metadata: Optional update metadata

        Returns:
            bool: True if update should be applied, False otherwise

        Raises:
            ConflictResolutionError: If check fails
        """
        if not self._connected:
            await self.connect()

        try:
            # Validate source
            if source not in VALID_SYNC_SOURCES:
                raise ValueError(
                    f"Invalid source: {source}. Must be one of: {', '.join(VALID_SYNC_SOURCES)}"
                )

            # Get current sync state
            sync_state = await self._state_manager.get_sync_state(issue_id)

            # If no previous state, apply the update
            if sync_state is None:
                return True

            # Parse timestamps
            update_timestamp = self._parse_timestamp(updated_at)
            last_sync_timestamp = self._parse_timestamp(sync_state["last_synced_at"])

            # Compare timestamps
            comparison = self._compare_timestamps(update_timestamp, last_sync_timestamp)

            if comparison > 0:
                # Update is newer - apply it
                logger.debug(
                    f"Update from {source} is newer for {issue_id} "
                    f"({update_timestamp} > {last_sync_timestamp})"
                )
                return True
            elif comparison < 0:
                # Update is older - skip it
                logger.info(
                    f"Update from {source} is older for {issue_id} "
                    f"({update_timestamp} < {last_sync_timestamp}), skipping"
                )
                return False
            else:
                # Timestamps are simultaneous - check source priority
                current_source = sync_state.get("sync_source", "")
                update_a = {"source": current_source, "updated_at": last_sync_timestamp}
                update_b = {"source": source, "updated_at": update_timestamp}

                winner = self._resolve_by_source_priority(update_a, update_b)
                should_apply = winner["source"] == source

                logger.debug(
                    f"Simultaneous update for {issue_id}: "
                    f"{'applying' if should_apply else 'skipping'} {source}"
                )

                return should_apply

        except ConflictTimestampError:
            raise
        except Exception as e:
            logger.error(f"Failed to check if update should apply for {issue_id}: {e}")
            raise ConflictResolutionError(f"Update check failed: {e}") from e

    async def record_update(
        self,
        issue_id: str,
        source: str,
        updated_at: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record an update after applying it.

        Updates the sync state with the new timestamp and source.

        Args:
            issue_id: Issue identifier
            source: Source of the update
            updated_at: Update timestamp
            metadata: Optional update metadata

        Raises:
            ConflictResolutionError: If recording fails
        """
        if not self._connected:
            await self.connect()

        try:
            # Validate source
            if source not in VALID_SYNC_SOURCES:
                raise ValueError(
                    f"Invalid source: {source}. Must be one of: {', '.join(VALID_SYNC_SOURCES)}"
                )

            # Parse timestamp
            update_timestamp = self._parse_timestamp(updated_at)

            # Create metadata
            update_metadata = metadata or {}
            update_metadata.update(
                {
                    "updated_at": update_timestamp.isoformat(),
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            # Record in state manager
            await self._state_manager.record_sync(
                issue_id=issue_id,
                sync_source=source,
                metadata=update_metadata,
            )

        except Exception as e:
            logger.error(f"Failed to record update for {issue_id}: {e}")
            raise ConflictResolutionError(f"Failed to record update: {e}") from e

    async def get_conflict_history(
        self,
        issue_id: str,
        limit: int = 10,
    ) -> list[Dict[str, Any]]:
        """
        Get conflict resolution history for an issue.

        Args:
            issue_id: Issue identifier
            limit: Maximum number of conflicts to return

        Returns:
            List of conflict records (most recent first)

        Raises:
            ConflictResolutionError: If retrieval fails
        """
        if not self._connected:
            await self.connect()

        try:
            redis = self._state_manager._redis_client
            conflict_key = self._get_conflict_key(issue_id)

            # Get recent conflicts from Redis list
            conflict_data = await redis.lrange(conflict_key, -limit, -1)

            # Parse JSON records
            import json

            conflicts = []
            for data in reversed(conflict_data):  # Most recent first
                try:
                    conflicts.append(json.loads(data))
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse conflict data: {e}")
                    continue

            return conflicts

        except Exception as e:
            logger.error(f"Failed to get conflict history for {issue_id}: {e}")
            raise ConflictResolutionError(f"Failed to get conflict history: {e}") from e

    async def clear_conflict_history(self, issue_id: str) -> bool:
        """
        Clear conflict history for an issue.

        Useful for testing or manual intervention.

        Args:
            issue_id: Issue identifier

        Returns:
            bool: True if cleared, False otherwise

        Raises:
            ConflictResolutionError: If clearing fails
        """
        if not self._connected:
            await self.connect()

        try:
            redis = self._state_manager._redis_client
            conflict_key = self._get_conflict_key(issue_id)

            deleted = await redis.delete(conflict_key)

            if deleted:
                logger.info(f"Cleared conflict history for {issue_id}")

            return bool(deleted)

        except Exception as e:
            logger.error(f"Failed to clear conflict history for {issue_id}: {e}")
            raise ConflictResolutionError(f"Failed to clear conflict history: {e}") from e


# Singleton instance for easy access
_conflict_manager: Optional[ConflictResolutionManager] = None


def get_conflict_manager() -> ConflictResolutionManager:
    """
    Get or create the global conflict resolution manager singleton.

    Returns:
        ConflictResolutionManager instance

    Note:
        You must call await conflict_manager.connect() before using
    """
    global _conflict_manager
    if _conflict_manager is None:
        _conflict_manager = ConflictResolutionManager()
    return _conflict_manager


def reset_conflict_manager() -> None:
    """
    Reset the global conflict resolution manager singleton.

    Useful for testing. Closes existing connection if open.
    """
    global _conflict_manager
    _conflict_manager = None
