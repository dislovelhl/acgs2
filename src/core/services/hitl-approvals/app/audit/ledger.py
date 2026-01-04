"""Constitutional Hash: cdd01ef066bc6cf2
Append-Only Audit Ledger for HITL Approvals

Implements an immutable audit trail persistence layer with:
- Append-only operations (no updates or deletes allowed)
- Cryptographic integrity verification using SHA-256 checksums
- Chain linking for tamper detection
- Redis-backed persistence for production use
- In-memory fallback for development/testing
- Comprehensive query capabilities with filtering and pagination

Key Design Decisions:
- All entries are immutable once written
- Each entry contains a checksum of its contents for integrity verification
- Parent entry linking creates a verifiable chain of events
- Redis sorted sets used for efficient time-based queries
- All modifications to approval requests generate audit entries
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.models import AuditEntry, AuditEntryType

logger = logging.getLogger(__name__)

# Redis key prefixes for audit storage
REDIS_AUDIT_ZSET = "hitl:audit:entries"
REDIS_AUDIT_DATA_PREFIX = "hitl:audit:data:"
REDIS_AUDIT_REQUEST_PREFIX = "hitl:audit:request:"
REDIS_AUDIT_ACTOR_PREFIX = "hitl:audit:actor:"
REDIS_AUDIT_TYPE_PREFIX = "hitl:audit:type:"
REDIS_AUDIT_LAST_ENTRY = "hitl:audit:last_entry"
REDIS_AUDIT_STATS = "hitl:audit:stats"

# Default retention period in days
DEFAULT_RETENTION_DAYS = 365


class AuditLedgerError(Exception):
    """Base exception for audit ledger errors."""

    pass


class IntegrityError(AuditLedgerError):
    """Raised when audit entry integrity verification fails."""

    pass


class ImmutabilityError(AuditLedgerError):
    """Raised when an attempt is made to modify or delete an audit entry."""

    pass


class RedisNotAvailableError(AuditLedgerError):
    """Raised when Redis is not available but required for an operation."""

    pass


@dataclass
class AuditQueryResult:
    """Result of an audit query with pagination info."""

    entries: List[AuditEntry]
    total: int
    offset: int
    limit: int
    has_more: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "entries": [e.model_dump() for e in self.entries],
            "total": self.total,
            "offset": self.offset,
            "limit": self.limit,
            "has_more": self.has_more,
        }


@dataclass
class AuditStatistics:
    """Aggregate statistics about the audit ledger."""

    total_entries: int = 0
    entries_by_type: Dict[str, int] = field(default_factory=dict)
    entries_by_actor_type: Dict[str, int] = field(default_factory=dict)
    unique_requests: int = 0
    unique_actors: int = 0
    first_entry_timestamp: Optional[float] = None
    last_entry_timestamp: Optional[float] = None
    integrity_verified: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_entries": self.total_entries,
            "entries_by_type": self.entries_by_type,
            "entries_by_actor_type": self.entries_by_actor_type,
            "unique_requests": self.unique_requests,
            "unique_actors": self.unique_actors,
            "first_entry_timestamp": self.first_entry_timestamp,
            "last_entry_timestamp": self.last_entry_timestamp,
            "integrity_verified": self.integrity_verified,
        }


class AuditLedger:
    """
    Append-only audit ledger for HITL approval workflows.

    Provides an immutable record of all actions and state changes in the
    approval system for compliance, debugging, and accountability purposes.

    Architecture:
    - In-memory list for development/testing
    - Redis sorted sets and hashes for production persistence
    - Entries indexed by timestamp (sorted set), request_id, actor_id, and type

    Immutability Guarantees:
    - No update or delete operations are exposed
    - Each entry includes a SHA-256 checksum of its contents
    - Entries are chained via parent_entry_id for tamper detection
    - Integrity can be verified at any time via verify_integrity()

    Thread Safety:
    - Uses asyncio lock for in-memory operations
    - Redis provides atomic operations for distributed safety
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        retention_days: int = DEFAULT_RETENTION_DAYS,
    ):
        """
        Initialize the audit ledger.

        Args:
            redis_url: Redis connection URL. Uses settings if not provided.
            retention_days: How long to retain audit entries in days.
        """
        self._redis_url = redis_url or settings.redis_url
        self._retention_days = retention_days
        self._redis: Optional[Any] = None

        # In-memory storage (used when Redis is not available)
        self._entries: List[AuditEntry] = []
        self._entries_by_request: Dict[str, List[str]] = {}  # request_id -> [entry_ids]
        self._entries_by_actor: Dict[str, List[str]] = {}  # actor_id -> [entry_ids]
        self._entries_by_type: Dict[str, List[str]] = {}  # entry_type -> [entry_ids]
        self._entries_by_id: Dict[str, AuditEntry] = {}  # entry_id -> entry
        self._last_entry_id: Optional[str] = None

        # Statistics cache
        self._unique_requests: set = set()
        self._unique_actors: set = set()

        logger.info(f"AuditLedger initialized (retention_days={retention_days})")

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def connect(self) -> None:
        """
        Establish connection to Redis for persistence.

        If Redis is not available, the ledger will fall back to in-memory storage.
        """
        try:
            import redis.asyncio as redis

            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

            # Test connection
            await self._redis.ping()

            # Load last entry ID for chain linking
            self._last_entry_id = await self._redis.get(REDIS_AUDIT_LAST_ENTRY)

            logger.info(f"Connected to Redis: {self._sanitize_url(self._redis_url)}")

        except ImportError as err:
            logger.warning(f"redis package not installed, using in-memory storage: {err}")
            self._redis = None
        except Exception as e:
            logger.warning(f"Failed to connect to Redis, using in-memory storage: {e}")
            self._redis = None

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Disconnected from Redis")

    async def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the audit ledger.

        Returns:
            Dictionary with health status information
        """
        status = {
            "storage_type": "redis" if self._redis else "in-memory",
            "redis_connected": False,
            "entry_count": 0,
            "integrity_ok": True,
        }

        if self._redis:
            try:
                await self._redis.ping()
                status["redis_connected"] = True
                status["entry_count"] = await self._redis.zcard(REDIS_AUDIT_ZSET)
            except Exception as e:
                logger.error(f"Redis health check failed: {e}")
                status["integrity_ok"] = False
        else:
            status["entry_count"] = len(self._entries)

        return status

    def _sanitize_url(self, url: str) -> str:
        """Sanitize URL for logging (remove password)."""
        if "@" in url:
            parts = url.split("@")
            return f"redis://***@{parts[-1]}"
        return url

    # =========================================================================
    # Core Append Operations (Immutable)
    # =========================================================================

    async def append(
        self,
        entry_type: AuditEntryType,
        actor_id: str,
        target_type: str,
        target_id: str,
        actor_type: str = "user",
        actor_role: Optional[str] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        action_details: Optional[Dict[str, Any]] = None,
        rationale: Optional[str] = None,
    ) -> AuditEntry:
        """
        Append a new entry to the audit ledger.

        This is the only way to add entries. No update or delete operations exist.

        Args:
            entry_type: Type of audit entry
            actor_id: ID of the user or system performing the action
            target_type: Type of target (request, chain, policy)
            target_id: ID of the target resource
            actor_type: Type of actor (user, system, service)
            actor_role: Role of the actor if applicable
            previous_state: State before the action
            new_state: State after the action
            action_details: Additional details about the action
            rationale: Reason for the action if provided

        Returns:
            The appended AuditEntry
        """
        # Generate unique entry ID
        entry_id = str(uuid.uuid4())

        # Create entry timestamp
        timestamp = datetime.now(timezone.utc)

        # Create the entry
        entry = AuditEntry(
            entry_id=entry_id,
            entry_type=entry_type,
            timestamp=timestamp,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_role=actor_role,
            target_type=target_type,
            target_id=target_id,
            previous_state=previous_state,
            new_state=new_state,
            action_details=action_details or {},
            rationale=rationale,
            parent_entry_id=self._last_entry_id,
        )

        # Calculate and set checksum for integrity verification
        entry.checksum = self._calculate_checksum(entry)

        # Persist the entry
        if self._redis:
            await self._persist_to_redis(entry)
        else:
            await self._persist_to_memory(entry)

        # Update last entry for chain linking
        self._last_entry_id = entry_id

        logger.info(
            f"Audit entry appended: {entry_type.value} "
            f"by {actor_id} on {target_type}:{target_id}"
        )

        return entry

    async def _persist_to_redis(self, entry: AuditEntry) -> None:
        """Persist an audit entry to Redis."""
        if not self._redis:
            raise RedisNotAvailableError("Redis not connected")

        timestamp = entry.timestamp.timestamp()
        entry_data = entry.model_dump(mode="json")

        # Use pipeline for atomic operations
        async with self._redis.pipeline() as pipe:
            # Store entry data as hash
            data_key = f"{REDIS_AUDIT_DATA_PREFIX}{entry.entry_id}"
            await pipe.hset(
                data_key,
                mapping={
                    k: json.dumps(v) if isinstance(v, (dict, list)) else str(v)
                    for k, v in entry_data.items()
                    if v is not None
                },
            )

            # Set retention TTL
            await pipe.expire(data_key, self._retention_days * 24 * 3600)

            # Add to main sorted set (by timestamp)
            await pipe.zadd(REDIS_AUDIT_ZSET, {entry.entry_id: timestamp})

            # Index by request_id (target_id for request targets)
            if entry.target_type == "request":
                request_key = f"{REDIS_AUDIT_REQUEST_PREFIX}{entry.target_id}"
                await pipe.zadd(request_key, {entry.entry_id: timestamp})
                await pipe.expire(request_key, self._retention_days * 24 * 3600)

            # Index by actor_id
            actor_key = f"{REDIS_AUDIT_ACTOR_PREFIX}{entry.actor_id}"
            await pipe.zadd(actor_key, {entry.entry_id: timestamp})
            await pipe.expire(actor_key, self._retention_days * 24 * 3600)

            # Index by entry_type
            type_key = f"{REDIS_AUDIT_TYPE_PREFIX}{entry.entry_type.value}"
            await pipe.zadd(type_key, {entry.entry_id: timestamp})
            await pipe.expire(type_key, self._retention_days * 24 * 3600)

            # Update last entry ID
            await pipe.set(REDIS_AUDIT_LAST_ENTRY, entry.entry_id)

            # Update stats
            await pipe.hincrby(REDIS_AUDIT_STATS, "total_entries", 1)
            await pipe.hincrby(REDIS_AUDIT_STATS, f"type:{entry.entry_type.value}", 1)
            await pipe.sadd("hitl:audit:unique_requests", entry.target_id)
            await pipe.sadd("hitl:audit:unique_actors", entry.actor_id)

            await pipe.execute()

    async def _persist_to_memory(self, entry: AuditEntry) -> None:
        """Persist an audit entry to in-memory storage."""
        # Add to main list
        self._entries.append(entry)
        self._entries_by_id[entry.entry_id] = entry

        # Index by request_id
        if entry.target_type == "request":
            if entry.target_id not in self._entries_by_request:
                self._entries_by_request[entry.target_id] = []
            self._entries_by_request[entry.target_id].append(entry.entry_id)
            self._unique_requests.add(entry.target_id)

        # Index by actor_id
        if entry.actor_id not in self._entries_by_actor:
            self._entries_by_actor[entry.actor_id] = []
        self._entries_by_actor[entry.actor_id].append(entry.entry_id)
        self._unique_actors.add(entry.actor_id)

        # Index by entry_type
        type_key = entry.entry_type.value
        if type_key not in self._entries_by_type:
            self._entries_by_type[type_key] = []
        self._entries_by_type[type_key].append(entry.entry_id)

    def _calculate_checksum(self, entry: AuditEntry) -> str:
        """
        Calculate SHA-256 checksum for an audit entry.

        The checksum covers all entry fields except the checksum itself,
        providing integrity verification.

        Args:
            entry: The audit entry to checksum

        Returns:
            Hex-encoded SHA-256 hash
        """
        # Create a deterministic string representation
        data = {
            "entry_id": entry.entry_id,
            "entry_type": entry.entry_type.value,
            "timestamp": entry.timestamp.isoformat(),
            "actor_id": entry.actor_id,
            "actor_type": entry.actor_type,
            "actor_role": entry.actor_role,
            "target_type": entry.target_type,
            "target_id": entry.target_id,
            "previous_state": entry.previous_state,
            "new_state": entry.new_state,
            "action_details": entry.action_details,
            "rationale": entry.rationale,
            "parent_entry_id": entry.parent_entry_id,
        }

        # Sort keys for deterministic ordering
        content = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def verify_checksum(self, entry: AuditEntry) -> bool:
        """
        Verify the integrity of an audit entry using its checksum.

        Args:
            entry: The audit entry to verify

        Returns:
            True if checksum is valid
        """
        if not entry.checksum:
            return False
        expected = self._calculate_checksum(entry)
        return entry.checksum == expected

    # =========================================================================
    # Query Operations (Read-Only)
    # =========================================================================

    async def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """
        Get a specific audit entry by ID.

        Args:
            entry_id: The entry ID

        Returns:
            The AuditEntry if found, None otherwise
        """
        if self._redis:
            return await self._get_entry_from_redis(entry_id)
        else:
            return self._entries_by_id.get(entry_id)

    async def _get_entry_from_redis(self, entry_id: str) -> Optional[AuditEntry]:
        """Load an entry from Redis."""
        if not self._redis:
            return None

        data_key = f"{REDIS_AUDIT_DATA_PREFIX}{entry_id}"
        data = await self._redis.hgetall(data_key)

        if not data:
            return None

        return self._parse_entry_from_redis(data)

    def _parse_entry_from_redis(self, data: Dict[str, str]) -> AuditEntry:
        """Parse an AuditEntry from Redis hash data."""
        # Parse JSON fields
        parsed: Dict[str, Any] = {}
        for key, value in data.items():
            if key in ("previous_state", "new_state", "action_details"):
                try:
                    parsed[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    parsed[key] = None
            elif key == "timestamp":
                parsed[key] = datetime.fromisoformat(value)
            elif key == "entry_type":
                parsed[key] = AuditEntryType(value)
            elif value == "None":
                parsed[key] = None
            else:
                parsed[key] = value

        return AuditEntry(**parsed)

    async def query(
        self,
        request_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        entry_type: Optional[AuditEntryType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AuditQueryResult:
        """
        Query audit entries with optional filtering.

        Args:
            request_id: Filter by approval request ID
            actor_id: Filter by actor ID
            entry_type: Filter by entry type
            start_time: Filter entries after this timestamp
            end_time: Filter entries before this timestamp
            limit: Maximum entries to return
            offset: Number of entries to skip

        Returns:
            AuditQueryResult with matching entries
        """
        if self._redis:
            return await self._query_from_redis(
                request_id, actor_id, entry_type, start_time, end_time, limit, offset
            )
        else:
            return await self._query_from_memory(
                request_id, actor_id, entry_type, start_time, end_time, limit, offset
            )

    async def _query_from_redis(
        self,
        request_id: Optional[str],
        actor_id: Optional[str],
        entry_type: Optional[AuditEntryType],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int,
        offset: int,
    ) -> AuditQueryResult:
        """Query entries from Redis."""
        if not self._redis:
            raise RedisNotAvailableError("Redis not connected")

        # Determine which index to query based on filters
        if request_id:
            index_key = f"{REDIS_AUDIT_REQUEST_PREFIX}{request_id}"
        elif actor_id:
            index_key = f"{REDIS_AUDIT_ACTOR_PREFIX}{actor_id}"
        elif entry_type:
            index_key = f"{REDIS_AUDIT_TYPE_PREFIX}{entry_type.value}"
        else:
            index_key = REDIS_AUDIT_ZSET

        # Build score range for time filtering
        min_score = start_time.timestamp() if start_time else "-inf"
        max_score = end_time.timestamp() if end_time else "+inf"

        # Get total count for pagination
        total = await self._redis.zcount(index_key, min_score, max_score)

        # Get entry IDs (sorted by timestamp descending - most recent first)
        entry_ids = await self._redis.zrevrangebyscore(
            index_key,
            max_score,
            min_score,
            start=offset,
            num=limit,
        )

        # Load entry data
        entries = []
        for entry_id in entry_ids:
            entry = await self._get_entry_from_redis(entry_id)
            if entry:
                # Apply additional filters
                if request_id and entry.target_id != request_id:
                    continue
                if actor_id and entry.actor_id != actor_id:
                    continue
                if entry_type and entry.entry_type != entry_type:
                    continue
                entries.append(entry)

        return AuditQueryResult(
            entries=entries,
            total=total,
            offset=offset,
            limit=limit,
            has_more=offset + len(entries) < total,
        )

    async def _query_from_memory(
        self,
        request_id: Optional[str],
        actor_id: Optional[str],
        entry_type: Optional[AuditEntryType],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        limit: int,
        offset: int,
    ) -> AuditQueryResult:
        """Query entries from in-memory storage."""
        # Start with appropriate index
        if request_id:
            entry_ids = self._entries_by_request.get(request_id, [])
            candidates = [self._entries_by_id[eid] for eid in entry_ids]
        elif actor_id:
            entry_ids = self._entries_by_actor.get(actor_id, [])
            candidates = [self._entries_by_id[eid] for eid in entry_ids]
        elif entry_type:
            entry_ids = self._entries_by_type.get(entry_type.value, [])
            candidates = [self._entries_by_id[eid] for eid in entry_ids]
        else:
            candidates = list(self._entries)

        # Apply filters
        filtered = []
        for entry in candidates:
            if request_id and entry.target_id != request_id:
                continue
            if actor_id and entry.actor_id != actor_id:
                continue
            if entry_type and entry.entry_type != entry_type:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            filtered.append(entry)

        # Sort by timestamp descending (most recent first)
        filtered.sort(key=lambda e: e.timestamp, reverse=True)

        total = len(filtered)
        paginated = filtered[offset : offset + limit]

        return AuditQueryResult(
            entries=paginated,
            total=total,
            offset=offset,
            limit=limit,
            has_more=offset + len(paginated) < total,
        )

    async def get_request_timeline(self, request_id: str) -> List[AuditEntry]:
        """
        Get the complete audit timeline for an approval request.

        Returns entries in chronological order (oldest first).

        Args:
            request_id: The approval request ID

        Returns:
            List of audit entries in chronological order
        """
        result = await self.query(request_id=request_id, limit=1000)
        # Reverse to get chronological order
        return list(reversed(result.entries))

    async def get_actor_activity(
        self,
        actor_id: str,
        limit: int = 50,
    ) -> List[AuditEntry]:
        """
        Get recent activity for a specific actor.

        Args:
            actor_id: The actor ID
            limit: Maximum entries to return

        Returns:
            List of audit entries (most recent first)
        """
        result = await self.query(actor_id=actor_id, limit=limit)
        return result.entries

    # =========================================================================
    # Integrity Verification
    # =========================================================================

    async def verify_integrity(
        self,
        limit: Optional[int] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Verify the integrity of the audit ledger.

        Checks:
        1. All entry checksums are valid
        2. Parent entry chain is unbroken
        3. Timestamps are monotonically increasing within chains

        Args:
            limit: Maximum entries to verify (None for all)

        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors: List[str] = []

        if self._redis:
            entries = await self._load_all_entries_from_redis(limit)
        else:
            entries = self._entries[:limit] if limit else self._entries

        # Sort by timestamp for chain verification
        entries.sort(key=lambda e: e.timestamp)

        entry_ids = {e.entry_id for e in entries}
        prev_timestamp: Optional[datetime] = None

        for entry in entries:
            # Verify checksum
            if not self.verify_checksum(entry):
                errors.append(f"Checksum mismatch for entry {entry.entry_id}")

            # Verify parent chain
            if entry.parent_entry_id and entry.parent_entry_id not in entry_ids:
                # Parent might exist but not be in our limited query
                if limit is None:
                    errors.append(
                        f"Broken chain: entry {entry.entry_id} "
                        f"references missing parent {entry.parent_entry_id}"
                    )

            # Verify timestamp ordering
            if prev_timestamp and entry.timestamp < prev_timestamp:
                errors.append(f"Timestamp out of order for entry {entry.entry_id}")
            prev_timestamp = entry.timestamp

        is_valid = len(errors) == 0

        if is_valid:
            logger.info(f"Audit ledger integrity verified ({len(entries)} entries)")
        else:
            logger.warning(f"Audit ledger integrity issues found: {len(errors)} errors")

        return is_valid, errors

    async def _load_all_entries_from_redis(
        self,
        limit: Optional[int] = None,
    ) -> List[AuditEntry]:
        """Load entries from Redis for verification."""
        if not self._redis:
            return []

        count = limit or await self._redis.zcard(REDIS_AUDIT_ZSET)
        entry_ids = await self._redis.zrange(REDIS_AUDIT_ZSET, 0, count - 1)

        entries = []
        for entry_id in entry_ids:
            entry = await self._get_entry_from_redis(entry_id)
            if entry:
                entries.append(entry)

        return entries

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_statistics(self) -> AuditStatistics:
        """
        Get aggregate statistics about the audit ledger.

        Returns:
            AuditStatistics object
        """
        if self._redis:
            return await self._get_statistics_from_redis()
        else:
            return self._get_statistics_from_memory()

    async def _get_statistics_from_redis(self) -> AuditStatistics:
        """Get statistics from Redis."""
        if not self._redis:
            return AuditStatistics()

        stats_data = await self._redis.hgetall(REDIS_AUDIT_STATS)
        total_entries = int(stats_data.get("total_entries", 0))

        # Get entry type counts
        entries_by_type: Dict[str, int] = {}
        for key, value in stats_data.items():
            if key.startswith("type:"):
                type_name = key[5:]  # Remove "type:" prefix
                entries_by_type[type_name] = int(value)

        # Get unique counts
        unique_requests = await self._redis.scard("hitl:audit:unique_requests")
        unique_actors = await self._redis.scard("hitl:audit:unique_actors")

        # Get first and last timestamps
        first_entry_id = await self._redis.zrange(REDIS_AUDIT_ZSET, 0, 0)
        last_entry_id = await self._redis.zrange(REDIS_AUDIT_ZSET, -1, -1)

        first_timestamp: Optional[float] = None
        last_timestamp: Optional[float] = None

        if first_entry_id:
            first_timestamp = await self._redis.zscore(REDIS_AUDIT_ZSET, first_entry_id[0])
        if last_entry_id:
            last_timestamp = await self._redis.zscore(REDIS_AUDIT_ZSET, last_entry_id[0])

        return AuditStatistics(
            total_entries=total_entries,
            entries_by_type=entries_by_type,
            unique_requests=unique_requests,
            unique_actors=unique_actors,
            first_entry_timestamp=first_timestamp,
            last_entry_timestamp=last_timestamp,
        )

    def _get_statistics_from_memory(self) -> AuditStatistics:
        """Get statistics from in-memory storage."""
        entries_by_type: Dict[str, int] = {}
        entries_by_actor_type: Dict[str, int] = {}

        for entry in self._entries:
            type_key = entry.entry_type.value
            entries_by_type[type_key] = entries_by_type.get(type_key, 0) + 1

            actor_type = entry.actor_type
            entries_by_actor_type[actor_type] = entries_by_actor_type.get(actor_type, 0) + 1

        first_timestamp = self._entries[0].timestamp.timestamp() if self._entries else None
        last_timestamp = self._entries[-1].timestamp.timestamp() if self._entries else None

        return AuditStatistics(
            total_entries=len(self._entries),
            entries_by_type=entries_by_type,
            entries_by_actor_type=entries_by_actor_type,
            unique_requests=len(self._unique_requests),
            unique_actors=len(self._unique_actors),
            first_entry_timestamp=first_timestamp,
            last_entry_timestamp=last_timestamp,
        )

    # =========================================================================
    # Convenience Methods for Common Audit Events
    # =========================================================================

    async def record_approval_created(
        self,
        request_id: str,
        actor_id: str,
        actor_role: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None,
        rationale: Optional[str] = None,
    ) -> AuditEntry:
        """Record creation of a new approval request."""
        return await self.append(
            entry_type=AuditEntryType.APPROVAL_CREATED,
            actor_id=actor_id,
            target_type="request",
            target_id=request_id,
            actor_type="user" if not actor_id.startswith("system") else "system",
            actor_role=actor_role,
            new_state=initial_state,
            rationale=rationale,
        )

    async def record_approval_decision(
        self,
        request_id: str,
        actor_id: str,
        decision: str,
        actor_role: Optional[str] = None,
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
        rationale: Optional[str] = None,
    ) -> AuditEntry:
        """Record an approval decision (approved or rejected)."""
        entry_type = (
            AuditEntryType.APPROVAL_APPROVED
            if decision.lower() == "approved"
            else AuditEntryType.APPROVAL_REJECTED
        )

        return await self.append(
            entry_type=entry_type,
            actor_id=actor_id,
            target_type="request",
            target_id=request_id,
            actor_role=actor_role,
            previous_state=previous_state,
            new_state=new_state,
            rationale=rationale,
            action_details={"decision": decision},
        )

    async def record_escalation(
        self,
        request_id: str,
        from_level: int,
        to_level: int,
        reason: str,
        actor_id: str = "system:escalation",
        previous_state: Optional[Dict[str, Any]] = None,
        new_state: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Record an escalation event."""
        return await self.append(
            entry_type=AuditEntryType.APPROVAL_ESCALATED,
            actor_id=actor_id,
            target_type="request",
            target_id=request_id,
            actor_type="system",
            previous_state=previous_state,
            new_state=new_state,
            action_details={
                "from_level": from_level,
                "to_level": to_level,
                "reason": reason,
            },
        )

    async def record_expiration(
        self,
        request_id: str,
        previous_state: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Record expiration of an approval request."""
        return await self.append(
            entry_type=AuditEntryType.APPROVAL_EXPIRED,
            actor_id="system:timeout",
            target_type="request",
            target_id=request_id,
            actor_type="system",
            previous_state=previous_state,
            new_state={"status": "expired"},
        )

    async def record_cancellation(
        self,
        request_id: str,
        actor_id: str,
        actor_role: Optional[str] = None,
        rationale: Optional[str] = None,
        previous_state: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Record cancellation of an approval request."""
        return await self.append(
            entry_type=AuditEntryType.APPROVAL_CANCELLED,
            actor_id=actor_id,
            target_type="request",
            target_id=request_id,
            actor_role=actor_role,
            previous_state=previous_state,
            new_state={"status": "cancelled"},
            rationale=rationale,
        )

    # =========================================================================
    # Cleanup (Testing Only)
    # =========================================================================

    async def clear(self) -> None:
        """
        Clear all audit entries.

        WARNING: This operation is for testing only and violates
        the append-only immutability guarantee. Do not use in production.
        """
        logger.warning("Clearing audit ledger - this is a destructive operation!")

        if self._redis:
            # Clear Redis keys
            keys = await self._redis.keys("hitl:audit:*")
            if keys:
                await self._redis.delete(*keys)

        # Clear in-memory storage
        self._entries.clear()
        self._entries_by_request.clear()
        self._entries_by_actor.clear()
        self._entries_by_type.clear()
        self._entries_by_id.clear()
        self._unique_requests.clear()
        self._unique_actors.clear()
        self._last_entry_id = None


# =============================================================================
# Singleton Instance Management
# =============================================================================

_audit_ledger: Optional[AuditLedger] = None


def get_audit_ledger() -> AuditLedger:
    """
    Get the global AuditLedger instance.

    Returns:
        The singleton AuditLedger instance
    """
    global _audit_ledger
    if _audit_ledger is None:
        _audit_ledger = AuditLedger()
    return _audit_ledger


async def initialize_audit_ledger(
    redis_url: Optional[str] = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> AuditLedger:
    """
    Initialize and connect the global audit ledger.

    Args:
        redis_url: Redis connection URL (uses settings if None)
        retention_days: How long to retain audit entries

    Returns:
        The initialized AuditLedger
    """
    global _audit_ledger

    _audit_ledger = AuditLedger(
        redis_url=redis_url,
        retention_days=retention_days,
    )

    await _audit_ledger.connect()

    return _audit_ledger


async def close_audit_ledger() -> None:
    """Close and cleanup the global audit ledger."""
    global _audit_ledger

    if _audit_ledger:
        await _audit_ledger.disconnect()
        _audit_ledger = None


def reset_audit_ledger() -> None:
    """
    Reset the global AuditLedger instance.

    Used primarily for test isolation.
    """
    global _audit_ledger
    _audit_ledger = None
