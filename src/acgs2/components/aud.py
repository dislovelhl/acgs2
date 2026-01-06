"""
Audit Ledger (AUD) Implementation

The AUD maintains an immutable audit trail of all system activities with:
- Hash-chained entries for tamper evidence
- Four entry types: decisions (SAS), actions (TMS), writes (DMS), sessions (UIG)
- Forensic query support by request_id, session_id, time range
- Compliance reporting and integrity verification
"""

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..core.interfaces import AuditLedgerInterface
from ..core.schemas import AuditEntry

logger = logging.getLogger(__name__)


class AuditLedger(AuditLedgerInterface):
    """Audit Ledger - Immutable audit trail with hash chaining for tamper evidence.

    Enhanced with:
    - Fire-and-forget async pattern for minimal latency impact
    - Background processing worker
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._running = False

        # Core audit chain
        self.entries: List[AuditEntry] = []
        self.last_hash: str = "genesis"  # Genesis block hash

        # Indices for efficient querying
        self.index_by_request: Dict[str, List[int]] = defaultdict(
            list
        )  # request_id -> entry indices
        self.index_by_session: Dict[str, List[int]] = defaultdict(
            list
        )  # session_id -> entry indices
        self.index_by_actor: Dict[str, List[int]] = defaultdict(list)  # actor -> entry indices
        self.index_by_type: Dict[str, List[int]] = defaultdict(list)  # action_type -> entry indices

        # Statistics
        self.stats = {
            "total_entries": 0,
            "entries_by_type": defaultdict(int),
            "entries_by_actor": defaultdict(int),
            "last_integrity_check": None,
        }

        # Async components
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

        logger.info("AUD initialized with hash-chained audit ledger")

    async def start(self) -> None:
        """Start the background processing worker."""
        if not self._running:
            self._running = True
            self._worker_task = asyncio.create_task(self._processing_worker())
            logger.info("AUD worker started")

    @property
    def component_name(self) -> str:
        return "AUD"

    async def health_check(self) -> Dict[str, Any]:
        """Health check for AUD."""
        async with self._lock:
            total_entries = len(self.entries)
            last_hash = self.last_hash

        # Check integrity on health check (but not too frequently)
        integrity_ok = await self.verify_integrity()

        return {
            "component": self.component_name,
            "status": "healthy" if self._running and integrity_ok else "unhealthy",
            "total_entries": total_entries,
            "last_hash": last_hash[:16] + "...",  # Truncate for display
            "integrity_verified": integrity_ok,
            "entries_by_type": dict(self.stats["entries_by_type"]),
            "last_integrity_check": self.stats["last_integrity_check"],
            "queue_size": self._queue.qsize(),
        }

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        logger.info("AUD shutting down")
        self._running = False

        if not self._queue.empty():
            logger.info(f"Draining {self._queue.qsize()} entries before shutdown")
            # Wait for queue to be empty
            await self._queue.join()

        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def append_entry(self, entry: AuditEntry) -> str:
        """
        Append audit entry to the immutable ledger (non-blocking).

        Uses hash chaining for tamper evidence: each entry includes hash of previous entry.
        """
        # Add timestamp if not set (must be before hash computation for consistency)
        if not entry.timestamp:
            entry.timestamp = datetime.now(timezone.utc).isoformat()

        # Compute entry hash (pre-compute to return to caller)
        # Note: In a fully non-blocking way, we might not know the hash yet
        # if it depends on the previous entry's hash.
        # But for audit, we can return a correlation ID or pre-calculated hash if we chain them.

        # We put it in the queue for the background worker to handle
        # This decouples the caller from hash computation and index updates
        await self._queue.put(entry)

        # We return a placeholder or the entry_id for now as the actual hash
        # will be computed in the background worker to maintain chain integrity
        return entry.entry_id

    async def _processing_worker(self):
        """Background worker that handles audit entry chaining and persistence."""
        while self._running or not self._queue.empty():
            try:
                # Get entry from queue with timeout to allow checking self._running
                try:
                    entry = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                async with self._lock:
                    # Set previous hash from the current last_hash
                    entry.previous_hash = self.last_hash

                    # Compute entry hash
                    entry_data = self._entry_to_dict(entry)
                    entry_hash = self._compute_hash(entry_data)
                    entry.entry_hash = entry_hash

                    # Append to chain
                    entry_index = len(self.entries)
                    self.entries.append(entry)

                    # Update indices
                    self.index_by_request[entry.request_id].append(entry_index)
                    self.index_by_session[entry.session_id].append(entry_index)
                    self.index_by_actor[entry.actor].append(entry_index)
                    self.index_by_type[entry.action_type].append(entry_index)

                    # Update stats
                    self.stats["total_entries"] += 1
                    self.stats["entries_by_type"][entry.action_type] += 1
                    self.stats["entries_by_actor"][entry.actor] += 1

                    # Update last hash for next entry
                    self.last_hash = entry_hash

                self._queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in AuditLedger processing worker: {e}")

    async def query_by_request(self, request_id: str) -> List[AuditEntry]:
        """
        Query audit entries by request ID.

        Returns all entries related to a specific request in chronological order.
        """
        async with self._lock:
            indices = self.index_by_request.get(request_id, [])
            entries = [self.entries[i] for i in indices]
        return sorted(entries, key=lambda e: e.timestamp)

    async def query_by_session(self, session_id: str) -> List[AuditEntry]:
        """
        Query audit entries by session ID.

        Returns all entries related to a session in chronological order.
        """
        async with self._lock:
            indices = self.index_by_session.get(session_id, [])
            entries = [self.entries[i] for i in indices]
        return sorted(entries, key=lambda e: e.timestamp)

    async def query_entries(
        self,
        actor: Optional[str] = None,
        action_type: Optional[str] = None,
        time_range: Optional[Dict[str, str]] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """
        Query audit entries with flexible filtering.

        Args:
            actor: Filter by actor (component)
            action_type: Filter by action type
            time_range: Dict with "start" and "end" ISO timestamps
            limit: Maximum entries to return

        Returns:
            List of matching entries in chronological order
        """
        async with self._lock:
            candidates = set()

            # Start with broadest set based on filters
            if actor:
                candidates.update(self.index_by_actor.get(actor, []))
            if action_type:
                if candidates:
                    candidates.intersection_update(self.index_by_type.get(action_type, []))
                else:
                    candidates.update(self.index_by_type.get(action_type, []))

            # If no filters, get all indices
            if not candidates:
                candidates = set(range(len(self.entries)))

            # Get entries
            matching_entries = [self.entries[i] for i in candidates]

        # Apply time range filter outside of lock
        if time_range:
            start_time = time_range.get("start")
            end_time = time_range.get("end")

            filtered = []
            for entry in matching_entries:
                entry_time = entry.timestamp

                if start_time and entry_time < start_time:
                    continue
                if end_time and entry_time > end_time:
                    continue

                filtered.append(entry)
            matching_entries = filtered

        # Sort by timestamp
        matching_entries.sort(key=lambda e: e.timestamp)

        # Apply limit
        return matching_entries[-limit:] if limit > 0 else matching_entries

    async def verify_integrity(self) -> bool:
        """
        Verify the integrity of the entire audit chain.

        Walks through all entries and verifies hash chaining.
        """
        async with self._lock:
            if not self.entries:
                self.stats["last_integrity_check"] = datetime.now(timezone.utc).isoformat()
                return True

            entries_copy = list(self.entries)

        expected_hash = "genesis"

        for entry in entries_copy:
            # Check previous hash matches expected
            if entry.previous_hash != expected_hash:
                logger.error(f"Audit chain integrity violation at entry {entry.entry_id}")
                self.stats["last_integrity_check"] = datetime.now(timezone.utc).isoformat()
                return False

            # Recompute hash and verify
            entry_data = self._entry_to_dict(entry)
            computed_hash = self._compute_hash(entry_data)

            if computed_hash != entry.entry_hash:
                logger.error(f"Audit entry hash mismatch at entry {entry.entry_id}")
                self.stats["last_integrity_check"] = datetime.now(timezone.utc).isoformat()
                return False

            expected_hash = computed_hash

        self.stats["last_integrity_check"] = datetime.now(timezone.utc).isoformat()
        return True

    async def get_compliance_report(self, time_range: Dict[str, str]) -> Dict[str, Any]:
        """
        Generate compliance report for the specified time range.

        Includes statistics on safety decisions, tool executions, and policy adherence.
        """
        start_time = time_range.get("start")
        end_time = time_range.get("end")

        # Get entries in time range
        entries = await self.query_entries(time_range=time_range, limit=0)

        # Analyze compliance metrics
        report = {
            "time_range": time_range,
            "total_entries": len(entries),
            "compliance_metrics": {},
        }

        # Count by action type
        action_counts = defaultdict(int)
        for entry in entries:
            action_counts[entry.action_type] += 1

        report["compliance_metrics"] = {
            "safety_decisions": action_counts.get("safety_decision", 0),
            "tool_executions": action_counts.get("tool_execution", 0),
            "memory_writes": action_counts.get("memory_write", 0),
            "session_events": action_counts.get("session_event", 0),
        }

        # Calculate denial rates, etc.
        safety_decisions = await self.query_entries(
            action_type="safety_decision", time_range=time_range, limit=0
        )

        denials = sum(1 for e in safety_decisions if e.payload.get("decision") == "DENY")

        total_decisions = len(safety_decisions)
        denial_rate = denials / total_decisions if total_decisions > 0 else 0

        report["compliance_metrics"]["safety_denial_rate"] = denial_rate

        return report

    async def get_chain_summary(self) -> Dict[str, Any]:
        """
        Get summary of the audit chain.

        Returns basic statistics and integrity status.
        """
        integrity_ok = await self.verify_integrity()

        async with self._lock:
            total_entries = len(self.entries)
            last_hash = self.last_hash
            entries_by_type = dict(self.stats["entries_by_type"])
            entries_by_actor = dict(self.stats["entries_by_actor"])
            last_integrity_check = self.stats["last_integrity_check"]

        return {
            "total_entries": total_entries,
            "chain_length": total_entries,
            "last_hash": last_hash,
            "genesis_hash": "genesis",
            "integrity_verified": integrity_ok,
            "last_integrity_check": last_integrity_check,
            "entries_by_type": entries_by_type,
            "entries_by_actor": entries_by_actor,
        }

    def _validate_entry(self, entry: AuditEntry) -> bool:
        """Validate audit entry before appending."""
        required_fields = ["request_id", "session_id", "actor", "action_type", "payload"]

        for field in required_fields:
            if not getattr(entry, field, None):
                logger.error(f"Audit entry missing required field: {field}")
                return False

        # Validate action_type
        valid_types = [
            "safety_decision",
            "tool_execution",
            "memory_write",
            "session_event",
            "system_event",
        ]

        if entry.action_type not in valid_types:
            logger.error(f"Invalid action_type: {entry.action_type}")
            return False

        return True

    def _entry_to_dict(self, entry: AuditEntry) -> Dict[str, Any]:
        """Convert entry to dict for hashing (excluding computed fields)."""
        return {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp,
            "request_id": entry.request_id,
            "session_id": entry.session_id,
            "actor": entry.actor,
            "action_type": entry.action_type,
            "payload": entry.payload,
            "previous_hash": entry.previous_hash,
        }

    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute SHA256 hash of entry data."""
        # Canonicalize JSON for consistent hashing
        json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(json_str.encode("utf-8")).hexdigest()

    async def export_chain(self, format: str = "json") -> str:
        """
        Export the audit chain for backup or analysis.

        Args:
            format: Export format ("json" or "csv")

        Returns:
            Exported data as string
        """
        async with self._lock:
            entries_copy = list(self.entries)
            summary = await self.get_chain_summary()

        if format == "json":
            entries_dict = [self._entry_to_dict(entry) for entry in entries_copy]
            return json.dumps({"chain_summary": summary, "entries": entries_dict}, indent=2)

        elif format == "csv":
            lines = [
                "entry_id,timestamp,request_id,session_id,actor,action_type,payload_hash,previous_hash,entry_hash"
            ]

            for entry in entries_copy:
                payload_hash = self._compute_hash(entry.payload)
                lines.append(
                    ",".join(
                        [
                            str(entry.entry_id),
                            str(entry.timestamp),
                            str(entry.request_id),
                            str(entry.session_id),
                            str(entry.actor),
                            str(entry.action_type),
                            str(payload_hash),
                            str(entry.previous_hash),
                            str(entry.entry_hash),
                        ]
                    )
                )

            return "\n".join(lines)

        else:
            raise ValueError(f"Unsupported export format: {format}")
