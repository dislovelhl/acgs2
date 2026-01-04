"""
Redis State Tracking for Linear Sync Operations

Provides Redis-backed state management for Linear bidirectional sync to:
- Track last sync timestamps for deduplication
- Store sync source information to prevent infinite loops
- Manage event IDs for duplicate event filtering
- Support conflict resolution with last-write-wins

Features:
- Async Redis operations for FastAPI compatibility
- Automatic TTL for state cleanup
- Namespace isolation for Linear-specific keys
- JSON serialization for complex state data
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

from ...config import get_service_config

logger = logging.getLogger(__name__)

# Redis key prefixes for Linear state tracking
LINEAR_STATE_PREFIX = "linear:sync"
LINEAR_EVENT_PREFIX = "linear:event"
LINEAR_LOCK_PREFIX = "linear:lock"

# Default TTL values (in seconds)
DEFAULT_STATE_TTL = 86400 * 7  # 7 days
DEFAULT_EVENT_TTL = 86400 * 3  # 3 days
DEFAULT_LOCK_TTL = 300  # 5 minutes


class LinearStateError(Exception):
    """Base exception for Linear state tracking errors."""

    pass


class LinearStateConnectionError(LinearStateError):
    """Raised when Redis connection fails."""

    pass


class LinearStateLockError(LinearStateError):
    """Raised when unable to acquire a lock."""

    pass


class LinearStateManager:
    """
    Redis-backed state manager for Linear sync operations.

    Tracks sync state across Linear, GitHub, GitLab, and Slack integrations
    to prevent duplicate syncs, infinite loops, and resolve conflicts.

    Usage:
        state_mgr = LinearStateManager()
        await state_mgr.connect()

        # Track a sync
        await state_mgr.record_sync("issue-123", "linear", {"title": "..."})

        # Check if event was already processed
        if await state_mgr.is_duplicate_event("evt-456"):
            return  # Skip duplicate

        # Acquire lock for concurrent sync protection
        async with state_mgr.lock("issue-123"):
            # Perform sync operations
            pass

        await state_mgr.close()
    """

    def __init__(
        self,
        redis_client: Optional[Redis] = None,
        redis_url: Optional[str] = None,
        state_ttl: int = DEFAULT_STATE_TTL,
        event_ttl: int = DEFAULT_EVENT_TTL,
        lock_ttl: int = DEFAULT_LOCK_TTL,
    ):
        """
        Initialize Linear state manager.

        Args:
            redis_client: Optional pre-configured Redis client
            redis_url: Optional Redis connection URL (uses config if not provided)
            state_ttl: TTL for sync state entries in seconds
            event_ttl: TTL for event deduplication entries in seconds
            lock_ttl: TTL for distributed locks in seconds
        """
        self._redis_client = redis_client
        self._redis_url = redis_url
        self._owns_client = redis_client is None
        self._state_ttl = state_ttl
        self._event_ttl = event_ttl
        self._lock_ttl = lock_ttl
        self._connected = False

    async def connect(self) -> None:
        """
        Establish Redis connection.

        Raises:
            LinearStateConnectionError: If connection fails
        """
        if self._connected:
            return

        try:
            if self._redis_client is None:
                # Get Redis URL from config if not provided
                if self._redis_url is None:
                    config = get_service_config()
                    self._redis_url = config.redis_url

                # Create async Redis client
                self._redis_client = await aioredis.from_url(
                    self._redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_timeout=5.0,
                    socket_connect_timeout=5.0,
                )

            # Test connection
            await self._redis_client.ping()
            self._connected = True
            logger.info("Linear state manager connected to Redis")

        except (RedisConnectionError, RedisTimeoutError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise LinearStateConnectionError(f"Redis connection failed: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error connecting to Redis: {e}")
            raise LinearStateConnectionError(f"Unexpected connection error: {e}") from e

    async def close(self) -> None:
        """Close Redis connection if owned by this manager."""
        if self._owns_client and self._redis_client is not None:
            await self._redis_client.aclose()
            self._redis_client = None
            self._connected = False
            logger.info("Linear state manager disconnected from Redis")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _get_state_key(self, issue_id: str) -> str:
        """
        Get Redis key for issue sync state.

        Args:
            issue_id: Linear issue ID

        Returns:
            Redis key string
        """
        return f"{LINEAR_STATE_PREFIX}:issue:{issue_id}"

    def _get_event_key(self, event_id: str) -> str:
        """
        Get Redis key for event deduplication.

        Args:
            event_id: Event ID

        Returns:
            Redis key string
        """
        return f"{LINEAR_EVENT_PREFIX}:{event_id}"

    def _get_lock_key(self, resource_id: str) -> str:
        """
        Get Redis key for distributed lock.

        Args:
            resource_id: Resource to lock (e.g., issue ID)

        Returns:
            Redis key string
        """
        return f"{LINEAR_LOCK_PREFIX}:{resource_id}"

    async def record_sync(
        self,
        issue_id: str,
        sync_source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a sync operation for an issue.

        Stores sync timestamp, source, and optional metadata for
        deduplication and conflict resolution.

        Args:
            issue_id: Linear issue ID (or GitHub/GitLab issue ID)
            sync_source: Source of the sync (linear, github, gitlab, slack)
            metadata: Optional metadata to store with the sync state

        Raises:
            LinearStateError: If recording fails
        """
        if not self._connected:
            await self.connect()

        try:
            key = self._get_state_key(issue_id)
            state_data = {
                "issue_id": issue_id,
                "sync_source": sync_source,
                "last_synced_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }

            # Store as JSON with TTL
            await self._redis_client.setex(
                key,
                self._state_ttl,
                json.dumps(state_data),
            )

            logger.debug(
                f"Recorded sync for issue {issue_id} from {sync_source} "
                f"at {state_data['last_synced_at']}"
            )

        except RedisError as e:
            logger.error(f"Failed to record sync state for {issue_id}: {e}")
            raise LinearStateError(f"Failed to record sync: {e}") from e

    async def get_sync_state(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """
        Get sync state for an issue.

        Args:
            issue_id: Linear issue ID

        Returns:
            Dict with sync state or None if not found

        Raises:
            LinearStateError: If retrieval fails
        """
        if not self._connected:
            await self.connect()

        try:
            key = self._get_state_key(issue_id)
            data = await self._redis_client.get(key)

            if data is None:
                return None

            return json.loads(data)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse sync state for {issue_id}: {e}")
            return None
        except RedisError as e:
            logger.error(f"Failed to get sync state for {issue_id}: {e}")
            raise LinearStateError(f"Failed to get sync state: {e}") from e

    async def mark_event_processed(
        self,
        event_id: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mark an event as processed for deduplication.

        Args:
            event_id: Unique event identifier
            event_type: Type of event (issue.create, issue.update, etc.)
            metadata: Optional event metadata

        Raises:
            LinearStateError: If marking fails
        """
        if not self._connected:
            await self.connect()

        try:
            key = self._get_event_key(event_id)
            event_data = {
                "event_id": event_id,
                "event_type": event_type,
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata or {},
            }

            await self._redis_client.setex(
                key,
                self._event_ttl,
                json.dumps(event_data),
            )

            logger.debug(f"Marked event {event_id} ({event_type}) as processed")

        except RedisError as e:
            logger.error(f"Failed to mark event {event_id} as processed: {e}")
            raise LinearStateError(f"Failed to mark event processed: {e}") from e

    async def is_duplicate_event(self, event_id: str) -> bool:
        """
        Check if an event has already been processed.

        Args:
            event_id: Event identifier to check

        Returns:
            True if event was already processed, False otherwise

        Raises:
            LinearStateError: If check fails
        """
        if not self._connected:
            await self.connect()

        try:
            key = self._get_event_key(event_id)
            exists = await self._redis_client.exists(key)
            return bool(exists)

        except RedisError as e:
            logger.error(f"Failed to check duplicate event {event_id}: {e}")
            # Fail open - assume not duplicate to avoid losing events
            return False

    async def acquire_lock(
        self,
        resource_id: str,
        timeout_seconds: Optional[int] = None,
    ) -> bool:
        """
        Acquire a distributed lock for a resource.

        Uses Redis SET NX (set if not exists) for atomic lock acquisition.

        Args:
            resource_id: Resource to lock (e.g., issue ID)
            timeout_seconds: Lock timeout (uses default if not provided)

        Returns:
            True if lock acquired, False otherwise

        Raises:
            LinearStateError: If lock operation fails
        """
        if not self._connected:
            await self.connect()

        try:
            key = self._get_lock_key(resource_id)
            ttl = timeout_seconds or self._lock_ttl

            # SET key value NX EX ttl (atomic set-if-not-exists with expiry)
            lock_acquired = await self._redis_client.set(
                key,
                datetime.now(timezone.utc).isoformat(),
                nx=True,  # Only set if key doesn't exist
                ex=ttl,  # Expire after ttl seconds
            )

            if lock_acquired:
                logger.debug(f"Acquired lock for {resource_id} (TTL: {ttl}s)")
            else:
                logger.debug(f"Failed to acquire lock for {resource_id} (already locked)")

            return bool(lock_acquired)

        except RedisError as e:
            logger.error(f"Failed to acquire lock for {resource_id}: {e}")
            raise LinearStateError(f"Failed to acquire lock: {e}") from e

    async def release_lock(self, resource_id: str) -> bool:
        """
        Release a distributed lock.

        Args:
            resource_id: Resource to unlock

        Returns:
            True if lock was released, False if it didn't exist

        Raises:
            LinearStateError: If unlock operation fails
        """
        if not self._connected:
            await self.connect()

        try:
            key = self._get_lock_key(resource_id)
            deleted = await self._redis_client.delete(key)

            if deleted:
                logger.debug(f"Released lock for {resource_id}")

            return bool(deleted)

        except RedisError as e:
            logger.error(f"Failed to release lock for {resource_id}: {e}")
            raise LinearStateError(f"Failed to release lock: {e}") from e

    async def lock(self, resource_id: str, timeout_seconds: Optional[int] = None):
        """
        Async context manager for distributed locks.

        Usage:
            async with state_mgr.lock("issue-123"):
                # Perform synchronized operations
                pass

        Args:
            resource_id: Resource to lock
            timeout_seconds: Lock timeout

        Raises:
            LinearStateLockError: If unable to acquire lock
        """
        return _LockContext(self, resource_id, timeout_seconds)

    async def get_all_sync_states(self, pattern: str = "*") -> List[Dict[str, Any]]:
        """
        Get all sync states matching a pattern.

        Args:
            pattern: Redis key pattern (default: all issues)

        Returns:
            List of sync state dictionaries

        Raises:
            LinearStateError: If retrieval fails
        """
        if not self._connected:
            await self.connect()

        try:
            key_pattern = f"{LINEAR_STATE_PREFIX}:issue:{pattern}"
            keys = []

            # Use SCAN for safe iteration over keys
            async for key in self._redis_client.scan_iter(match=key_pattern, count=100):
                keys.append(key)

            # Fetch all states
            states = []
            if keys:
                values = await self._redis_client.mget(keys)
                for value in values:
                    if value:
                        try:
                            states.append(json.loads(value))
                        except json.JSONDecodeError:
                            continue

            return states

        except RedisError as e:
            logger.error(f"Failed to get sync states: {e}")
            raise LinearStateError(f"Failed to get sync states: {e}") from e

    async def clear_sync_state(self, issue_id: str) -> bool:
        """
        Clear sync state for an issue.

        Args:
            issue_id: Linear issue ID

        Returns:
            True if state was cleared, False if it didn't exist

        Raises:
            LinearStateError: If clear operation fails
        """
        if not self._connected:
            await self.connect()

        try:
            key = self._get_state_key(issue_id)
            deleted = await self._redis_client.delete(key)
            return bool(deleted)

        except RedisError as e:
            logger.error(f"Failed to clear sync state for {issue_id}: {e}")
            raise LinearStateError(f"Failed to clear sync state: {e}") from e


class _LockContext:
    """Async context manager for distributed locks."""

    def __init__(
        self,
        state_manager: LinearStateManager,
        resource_id: str,
        timeout_seconds: Optional[int],
    ):
        self.state_manager = state_manager
        self.resource_id = resource_id
        self.timeout_seconds = timeout_seconds
        self._acquired = False

    async def __aenter__(self):
        """Acquire lock on entry."""
        self._acquired = await self.state_manager.acquire_lock(
            self.resource_id,
            self.timeout_seconds,
        )

        if not self._acquired:
            raise LinearStateLockError(
                f"Failed to acquire lock for {self.resource_id}. "
                f"Resource may be locked by another process."
            )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Release lock on exit."""
        if self._acquired:
            await self.state_manager.release_lock(self.resource_id)


# Singleton instance for easy access
_state_manager: Optional[LinearStateManager] = None


def get_state_manager() -> LinearStateManager:
    """
    Get or create the global Linear state manager singleton.

    Returns:
        LinearStateManager instance

    Note:
        You must call await state_manager.connect() before using
    """
    global _state_manager
    if _state_manager is None:
        _state_manager = LinearStateManager()
    return _state_manager


def reset_state_manager() -> None:
    """
    Reset the global state manager singleton.

    Useful for testing. Closes existing connection if open.
    """
    global _state_manager
    _state_manager = None
