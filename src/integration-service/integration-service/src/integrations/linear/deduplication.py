"""
Deduplication Logic for Linear Sync Operations

Prevents duplicate event processing and infinite sync loops between
Linear, GitHub, GitLab, and Slack integrations using Redis-backed
event tracking and source attribution.

Features:
- Event ID tracking to prevent duplicate processing
- Source tracking to prevent infinite sync loops
- Correlation ID support for cross-service event tracking
- TTL-based automatic cleanup
- Comprehensive logging for debugging

Architecture:
- Events are tracked with unique IDs (from webhook or generated)
- Each sync operation records its source (linear, github, gitlab, slack)
- Before processing, check if event was already seen
- Track sync chains to detect and break infinite loops
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .models import LinearWebhookPayload
from .state import LinearStateManager, get_state_manager

logger = logging.getLogger(__name__)

# Constants for deduplication
DEFAULT_EVENT_TTL = 86400 * 3  # 3 days
DEFAULT_SYNC_CHAIN_TTL = 300  # 5 minutes (to detect rapid loops)
MAX_SYNC_CHAIN_LENGTH = 5  # Max number of syncs in chain before loop detected

# Sync sources
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


class DeduplicationError(Exception):
    """Base exception for deduplication errors."""

    pass


class DuplicateEventError(DeduplicationError):
    """Raised when a duplicate event is detected."""

    pass


class SyncLoopDetectedError(DeduplicationError):
    """Raised when an infinite sync loop is detected."""

    pass


class LinearDeduplicationManager:
    """
    Manages deduplication for Linear sync operations.

    Prevents duplicate event processing and detects infinite sync loops
    using Redis-backed state tracking.

    Usage:
        dedup_mgr = LinearDeduplicationManager()
        await dedup_mgr.connect()

        # Check if event is duplicate
        if await dedup_mgr.is_duplicate(event_id):
            logger.info("Duplicate event, skipping")
            return

        # Mark event as processed
        await dedup_mgr.mark_processed(event_id, "linear", metadata)

        # Check for sync loops
        if await dedup_mgr.would_create_loop(issue_id, "github", "linear"):
            logger.warning("Sync loop detected, breaking")
            return

        await dedup_mgr.close()
    """

    def __init__(
        self,
        state_manager: Optional[LinearStateManager] = None,
        event_ttl: int = DEFAULT_EVENT_TTL,
        sync_chain_ttl: int = DEFAULT_SYNC_CHAIN_TTL,
        max_chain_length: int = MAX_SYNC_CHAIN_LENGTH,
    ):
        """
        Initialize deduplication manager.

        Args:
            state_manager: Optional pre-configured state manager
            event_ttl: TTL for event tracking in seconds
            sync_chain_ttl: TTL for sync chain tracking in seconds
            max_chain_length: Maximum sync chain length before loop detection
        """
        self._state_manager = state_manager or get_state_manager()
        self._owns_state_manager = state_manager is None
        self._event_ttl = event_ttl
        self._sync_chain_ttl = sync_chain_ttl
        self._max_chain_length = max_chain_length
        self._connected = False

    async def connect(self) -> None:
        """
        Establish connection to Redis.

        Raises:
            DeduplicationError: If connection fails
        """
        if self._connected:
            return

        try:
            await self._state_manager.connect()
            self._connected = True
            logger.info("Linear deduplication manager connected")
        except Exception as e:
            logger.error(f"Failed to connect deduplication manager: {e}")
            raise DeduplicationError(f"Connection failed: {e}") from e

    async def close(self) -> None:
        """Close connection to Redis if owned by this manager."""
        if self._owns_state_manager:
            await self._state_manager.close()
        self._connected = False
        logger.info("Linear deduplication manager disconnected")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def _generate_event_id(
        self,
        webhook_payload: Optional[LinearWebhookPayload] = None,
        **kwargs,
    ) -> str:
        """
        Generate a deterministic event ID.

        If webhook_payload is provided, generates ID from webhook data.
        Otherwise, generates from provided kwargs.

        Args:
            webhook_payload: Optional webhook payload
            **kwargs: Additional data for ID generation

        Returns:
            str: Event ID
        """
        if webhook_payload:
            # Use webhook data for ID generation
            data = {
                "type": webhook_payload.type,
                "action": webhook_payload.action,
                "entity_id": webhook_payload.data.id,
                "created_at": webhook_payload.createdAt.isoformat(),
                "org_id": webhook_payload.organizationId,
            }
        else:
            data = kwargs

        # Create deterministic hash from data
        data_str = str(sorted(data.items()))
        hash_obj = hashlib.sha256(data_str.encode())
        return hash_obj.hexdigest()[:32]

    async def is_duplicate(
        self,
        event_id: str,
        check_only: bool = False,
    ) -> bool:
        """
        Check if an event has already been processed.

        Args:
            event_id: Event identifier to check
            check_only: If True, only check without logging (for internal use)

        Returns:
            bool: True if event is a duplicate, False otherwise

        Raises:
            DeduplicationError: If check fails
        """
        if not self._connected:
            await self.connect()

        try:
            is_dup = await self._state_manager.is_duplicate_event(event_id)

            if is_dup and not check_only:
                logger.info(f"Duplicate event detected: {event_id}")

            return is_dup

        except Exception as e:
            logger.error(f"Failed to check duplicate event {event_id}: {e}")
            # Fail open - assume not duplicate to avoid losing events
            return False

    async def mark_processed(
        self,
        event_id: str,
        source: str,
        event_type: str = "webhook",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Mark an event as processed.

        Args:
            event_id: Event identifier
            source: Source of the event (linear, github, gitlab, slack)
            event_type: Type of event (webhook, sync, manual)
            metadata: Optional event metadata

        Raises:
            DeduplicationError: If marking fails
            ValueError: If source is invalid
        """
        if source not in VALID_SYNC_SOURCES:
            raise ValueError(
                f"Invalid sync source: {source}. Must be one of: {', '.join(VALID_SYNC_SOURCES)}"
            )

        if not self._connected:
            await self.connect()

        try:
            # Enrich metadata with source tracking
            enriched_metadata = metadata or {}
            enriched_metadata.update(
                {
                    "source": source,
                    "marked_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            await self._state_manager.mark_event_processed(
                event_id=event_id,
                event_type=event_type,
                metadata=enriched_metadata,
            )

        except Exception as e:
            logger.error(f"Failed to mark event {event_id} as processed: {e}")
            raise DeduplicationError(f"Failed to mark event processed: {e}") from e

    async def record_sync(
        self,
        issue_id: str,
        from_source: str,
        to_source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a sync operation between sources.

        This tracks the sync chain to detect loops.

        Args:
            issue_id: Issue identifier
            from_source: Source initiating the sync
            to_source: Target of the sync
            metadata: Optional sync metadata

        Raises:
            DeduplicationError: If recording fails
            ValueError: If sources are invalid
        """
        if from_source not in VALID_SYNC_SOURCES or to_source not in VALID_SYNC_SOURCES:
            raise ValueError(
                f"Invalid sync sources: {from_source} -> {to_source}. "
                f"Must be from: {', '.join(VALID_SYNC_SOURCES)}"
            )

        if not self._connected:
            await self.connect()

        try:
            # Create sync metadata
            sync_metadata = metadata or {}
            sync_metadata.update(
                {
                    "from_source": from_source,
                    "to_source": to_source,
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                }
            )

            # Record sync in state manager
            await self._state_manager.record_sync(
                issue_id=issue_id,
                sync_source=from_source,
                metadata=sync_metadata,
            )

            # Also record in sync chain for loop detection
            await self._add_to_sync_chain(issue_id, from_source, to_source)

        except Exception as e:
            logger.error(f"Failed to record sync for {issue_id}: {e}")
            raise DeduplicationError(f"Failed to record sync: {e}") from e

    async def _add_to_sync_chain(
        self,
        issue_id: str,
        from_source: str,
        to_source: str,
    ) -> None:
        """
        Add a sync operation to the chain tracking.

        Uses Redis to track recent sync operations to detect loops.

        Args:
            issue_id: Issue identifier
            from_source: Source initiating the sync
            to_source: Target of the sync
        """
        if not self._connected:
            await self.connect()

        # Get the Redis client directly from state manager
        redis = self._state_manager._redis_client

        chain_key = f"linear:sync_chain:{issue_id}"
        sync_entry = f"{from_source}->{to_source}:{datetime.now(timezone.utc).isoformat()}"

        # Add to list and set TTL
        await redis.rpush(chain_key, sync_entry)
        await redis.expire(chain_key, self._sync_chain_ttl)

        # Trim to max length to prevent unbounded growth
        await redis.ltrim(chain_key, -self._max_chain_length * 2, -1)

    async def _get_sync_chain(self, issue_id: str) -> List[str]:
        """
        Get the sync chain for an issue.

        Args:
            issue_id: Issue identifier

        Returns:
            List of sync entries in chain
        """
        if not self._connected:
            await self.connect()

        redis = self._state_manager._redis_client
        chain_key = f"linear:sync_chain:{issue_id}"

        try:
            chain = await redis.lrange(chain_key, 0, -1)
            return chain or []
        except Exception as e:
            logger.error(f"Failed to get sync chain for {issue_id}: {e}")
            return []

    async def would_create_loop(
        self,
        issue_id: str,
        from_source: str,
        to_source: str,
    ) -> bool:
        """
        Check if a sync operation would create an infinite loop.

        Detects loops by analyzing the recent sync chain.

        Args:
            issue_id: Issue identifier
            from_source: Source initiating the sync
            to_source: Target of the sync

        Returns:
            bool: True if loop would be created, False otherwise
        """
        if not self._connected:
            await self.connect()

        try:
            # Get recent sync chain
            chain = await self._get_sync_chain(issue_id)

            if not chain:
                return False

            # Parse sync chain entries
            sync_pairs = []
            for entry in chain:
                # Entry format: "source1->source2:timestamp"
                if "->" in entry:
                    sync_part = entry.split(":")[0]  # Remove timestamp
                    sync_pairs.append(sync_part)

            # Check if this sync would create a loop
            new_sync = f"{from_source}->{to_source}"

            # Simple loop detection: check if we've seen this exact sync recently
            if new_sync in sync_pairs:
                logger.warning(f"Loop detected for {issue_id}: {new_sync} already in chain")
                return True

            # Advanced loop detection: check if we're bouncing back and forth
            # between the same sources (A->B->A->B pattern)
            if len(sync_pairs) >= 2:
                reverse_sync = f"{to_source}->{from_source}"
                recent_syncs = sync_pairs[-2:]
                if reverse_sync in recent_syncs:
                    logger.warning(
                        f"Bounce loop detected for {issue_id}: {from_source} <-> {to_source}"
                    )
                    return True

            # Check chain length
            if len(sync_pairs) >= self._max_chain_length:
                logger.warning(
                    f"Sync chain too long for {issue_id}: "
                    f"{len(sync_pairs)} >= {self._max_chain_length}"
                )
                return True

            return False

        except Exception as e:
            logger.error(f"Failed to check sync loop for {issue_id}: {e}")
            # Fail safe - assume no loop to allow sync
            return False

    async def get_event_sources(
        self,
        issue_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get recent event sources for an issue.

        Useful for debugging and understanding sync flow.

        Args:
            issue_id: Issue identifier
            limit: Maximum number of sources to return

        Returns:
            List of event source metadata
        """
        if not self._connected:
            await self.connect()

        try:
            # Get sync state
            sync_state = await self._state_manager.get_sync_state(issue_id)

            # Get sync chain
            chain = await self._get_sync_chain(issue_id)

            sources = []

            # Add sync state
            if sync_state:
                sources.append(
                    {
                        "type": "sync_state",
                        "source": sync_state.get("sync_source"),
                        "timestamp": sync_state.get("last_synced_at"),
                        "metadata": sync_state.get("metadata", {}),
                    }
                )

            # Add chain entries
            for entry in chain[-limit:]:
                if "->" in entry:
                    parts = entry.split(":")
                    sync_part = parts[0]
                    timestamp = parts[1] if len(parts) > 1 else None

                    from_src, to_src = sync_part.split("->")
                    sources.append(
                        {
                            "type": "sync_chain",
                            "from_source": from_src,
                            "to_source": to_src,
                            "timestamp": timestamp,
                        }
                    )

            return sources[-limit:]

        except Exception as e:
            logger.error(f"Failed to get event sources for {issue_id}: {e}")
            return []

    async def clear_issue_history(self, issue_id: str) -> bool:
        """
        Clear deduplication history for an issue.

        Useful for testing or manual intervention.

        Args:
            issue_id: Issue identifier

        Returns:
            bool: True if cleared, False otherwise

        Raises:
            DeduplicationError: If clearing fails
        """
        if not self._connected:
            await self.connect()

        try:
            # Clear sync state
            state_cleared = await self._state_manager.clear_sync_state(issue_id)

            # Clear sync chain
            redis = self._state_manager._redis_client
            chain_key = f"linear:sync_chain:{issue_id}"
            chain_cleared = await redis.delete(chain_key)

            logger.info(
                f"Cleared history for {issue_id}: state={state_cleared}, chain={chain_cleared}"
            )

            return state_cleared or bool(chain_cleared)

        except Exception as e:
            logger.error(f"Failed to clear history for {issue_id}: {e}")
            raise DeduplicationError(f"Failed to clear history: {e}") from e

    async def should_process_event(
        self,
        event_id: str,
        issue_id: str,
        from_source: str,
        to_source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Comprehensive check if an event should be processed.

        Combines duplicate checking and loop detection.

        Args:
            event_id: Event identifier
            issue_id: Issue identifier
            from_source: Source of the event
            to_source: Target of the sync
            metadata: Optional event metadata

        Returns:
            bool: True if event should be processed, False otherwise
        """
        if not self._connected:
            await self.connect()

        # Check for duplicate
        if await self.is_duplicate(event_id):
            logger.info(f"Skipping duplicate event {event_id} for {issue_id}")
            return False

        # Check for sync loop
        if await self.would_create_loop(issue_id, from_source, to_source):
            logger.warning(
                f"Skipping event {event_id} for {issue_id} - would create loop: "
                f"{from_source} -> {to_source}"
            )
            return False

        # Event should be processed

        return True


# Singleton instance for easy access
_dedup_manager: Optional[LinearDeduplicationManager] = None


def get_dedup_manager() -> LinearDeduplicationManager:
    """
    Get or create the global Linear deduplication manager singleton.

    Returns:
        LinearDeduplicationManager instance

    Note:
        You must call await dedup_manager.connect() before using
    """
    global _dedup_manager
    if _dedup_manager is None:
        _dedup_manager = LinearDeduplicationManager()
    return _dedup_manager


def reset_dedup_manager() -> None:
    """
    Reset the global deduplication manager singleton.

    Useful for testing. Closes existing connection if open.
    """
    global _dedup_manager
    _dedup_manager = None
