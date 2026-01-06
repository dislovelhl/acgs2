"""
Distributed Memory System (DMS) Implementation

The DMS implements dual-layer retention with short-term working memory
(active context windows) and long-term semantic archival (vector-based RAG)
for extended recall.

Key features:
- Session-based short-term memory
- Vector-based long-term fact storage
- Provenance tracking for all writes
- Privacy controls and retention policies
- Swarm blackboard pattern for agent coordination
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.core.shared.security import redact_pii

from ..core.interfaces import (
    AuditLedgerInterface,
    DistributedMemorySystemInterface,
    ObservabilitySystemInterface,
)
from ..core.schemas import (
    AuditEntry,
    ContextBundle,
    CoreEnvelope,
    MemoryRecord,
    RecordType,
    TelemetryEvent,
)

logger = logging.getLogger(__name__)


class DistributedMemorySystem(DistributedMemorySystemInterface):
    """Distributed Memory System - Dual-layer memory with provenance tracking."""

    def __init__(
        self,
        config: Dict[str, Any],
        obs: ObservabilitySystemInterface = None,
        aud: AuditLedgerInterface = None,
    ):
        self.config = config
        self.obs = obs
        self.aud = aud
        self._running = True

        # Short-term memory (session-based)
        self.session_history: Dict[str, List[str]] = {}
        self.session_metadata: Dict[str, Dict[str, Any]] = {}

        # Long-term memory (facts and RAG)
        self.facts_store: List[Dict[str, Any]] = []
        self.vector_index: Dict[str, List[float]] = {}  # Simple placeholder for vectors

        # RAG content (can be swapped for real vector DB)
        self.rag_content: str = "Default knowledge base content. Replace with actual RAG system."

        # Persistence
        self.storage_path = config.get("storage_path", "/tmp/acgs2_dms")
        os.makedirs(self.storage_path, exist_ok=True)

        logger.info(f"DMS initialized with storage at {self.storage_path}")

    @property
    def component_name(self) -> str:
        return "DMS"

    async def health_check(self) -> Dict[str, Any]:
        """Health check for DMS."""
        return {
            "component": self.component_name,
            "status": "healthy" if self._running else "unhealthy",
            "active_sessions": len(self.session_history),
            "facts_stored": len(self.facts_store),
            "storage_path": self.storage_path,
        }

    async def shutdown(self) -> None:
        """Graceful shutdown with persistence."""
        logger.info("DMS shutting down")
        await self._persist_state()
        self._running = False

    async def retrieve(self, session_id: str, query: Optional[str] = None) -> ContextBundle:
        """Retrieve context bundle for session with optional RAG."""
        if not self._running:
            return ContextBundle(
                session_history=[],
                rag_content="",
                facts=[],
            )

        # Get session history
        session_history = self.session_history.get(session_id, [])

        # Get relevant facts (simple keyword matching for now)
        relevant_facts = []
        if query:
            relevant_facts = await self.search_facts(query, limit=5)

        # Get RAG content (could be enhanced with real vector similarity)
        rag_content = self.rag_content

        return ContextBundle(
            session_history=session_history,
            rag_content=rag_content,
            facts=relevant_facts,
        )

    async def write(self, record: MemoryRecord, envelope) -> Dict[str, Any]:
        """Write memory record with provenance tracking."""
        if not self._running:
            return {"status": "error", "message": "DMS not running"}

        # Ensure provenance is complete
        if "request_id" not in record.provenance:
            record.provenance["request_id"] = envelope.request_id
        if "actor" not in record.provenance:
            record.provenance["actor"] = envelope.actor
        if "timestamp" not in record.provenance:
            record.provenance["timestamp"] = envelope.timestamp

        # Apply privacy controls
        record = await self._apply_privacy_controls(record)

        # Store based on record type
        if record.record_type == RecordType.SUMMARY:
            await self._store_session_summary(record, envelope.session_id)
        elif record.record_type == RecordType.FACT:
            await self._store_fact(record)
        elif record.record_type == RecordType.PREFERENCE:
            await self._store_preference(record, envelope.session_id)
        elif record.record_type == RecordType.TASK_ARTIFACT:
            await self._store_task_artifact(record, envelope.session_id)

        # Apply retention policy
        await self._apply_retention_policy(record)

        # Emit telemetry and audit for successful memory write
        await self._emit_memory_events(record, envelope)

        return {
            "status": "success",
            "record_id": f"{record.record_type.value}_{envelope.request_id}",
            "provenance": record.provenance,
        }

    async def search_facts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search long-term facts using simple keyword matching."""
        query_lower = query.lower()
        matches = []

        for fact in self.facts_store:
            content = fact.get("content", "").lower()
            if any(word in content for word in query_lower.split()):
                matches.append(fact)
                if len(matches) >= limit:
                    break

        return matches

    async def get_session_history(self, session_id: str) -> List[str]:
        """Get conversation history for session."""
        return self.session_history.get(session_id, [])

    async def clear_session(self, session_id: str) -> bool:
        """Clear session data for privacy."""
        if session_id in self.session_history:
            del self.session_history[session_id]
        if session_id in self.session_metadata:
            del self.session_metadata[session_id]

        logger.info(f"Cleared session data for {session_id}")
        return True

    async def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session."""
        history = self.session_history.get(session_id, [])
        metadata = self.session_metadata.get(session_id, {})

        return {
            "session_id": session_id,
            "turn_count": len(history),
            "created_at": metadata.get("created_at"),
            "last_activity": metadata.get("last_activity"),
        }

    async def list_active_sessions(self) -> List[str]:
        """List sessions with recent activity."""
        active_sessions = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)  # Last hour

        for session_id, metadata in self.session_metadata.items():
            last_activity = metadata.get("last_activity")
            if last_activity:
                last_activity_dt = datetime.fromisoformat(last_activity)
                if last_activity_dt > cutoff:
                    active_sessions.append(session_id)

        return active_sessions

    async def _store_session_summary(self, record: MemoryRecord, session_id: str) -> None:
        """Store session conversation summary."""
        if session_id not in self.session_history:
            self.session_history[session_id] = []
            self.session_metadata[session_id] = {
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

        self.session_history[session_id].append(record.content)
        self.session_metadata[session_id]["last_activity"] = record.provenance["timestamp"]

        # Limit session history length
        max_history = self.config.get("max_session_history", 50)
        if len(self.session_history[session_id]) > max_history:
            self.session_history[session_id] = self.session_history[session_id][-max_history:]

    async def _store_fact(self, record: MemoryRecord) -> None:
        """Store long-term fact."""
        fact_entry = {
            "id": f"fact_{len(self.facts_store)}",
            "content": record.content,
            "provenance": record.provenance,
            "retention": record.retention,
            "stored_at": datetime.now(timezone.utc).isoformat(),
        }

        self.facts_store.append(fact_entry)

        # Simple vector placeholder (would be real embeddings in production)
        self.vector_index[fact_entry["id"]] = [0.1, 0.2, 0.3]  # Placeholder vector

    async def _store_preference(self, record: MemoryRecord, session_id: str) -> None:
        """Store user preference."""
        if session_id not in self.session_metadata:
            self.session_metadata[session_id] = {}

        # Store preference in session metadata
        pref_key = record.content.split(":")[0] if ":" in record.content else "general"
        self.session_metadata[session_id][f"pref_{pref_key}"] = {
            "value": record.content,
            "provenance": record.provenance,
        }

    async def _store_task_artifact(self, record: MemoryRecord, session_id: str) -> None:
        """Store task execution artifact."""
        # Task artifacts are stored as special session entries
        artifact_entry = f"[TASK] {record.content}"

        if session_id not in self.session_history:
            self.session_history[session_id] = []

        self.session_history[session_id].append(artifact_entry)

    async def _apply_privacy_controls(self, record: MemoryRecord) -> MemoryRecord:
        """Apply privacy controls to record before storage."""
        content = record.content

        # Simple PII detection (would be more sophisticated in production)
        pii_patterns = [
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",  # Credit card
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        ]

        for pattern in pii_patterns:
            content = re.sub(pattern, "[REDACTED]", content)

        # Mark as containing PII if redaction occurred
        if content != record.content:
            record.retention["pii"] = True

        record.content = content
        return record

    async def _apply_retention_policy(self, record: MemoryRecord) -> None:
        """Apply retention policy based on record type and content."""
        retention = record.retention

        # Default retention based on record type
        type_defaults = {
            RecordType.SUMMARY: {"ttl_days": 30, "pii": False},
            RecordType.FACT: {"ttl_days": 365, "pii": False},
            RecordType.PREFERENCE: {"ttl_days": 90, "pii": False},
            RecordType.TASK_ARTIFACT: {"ttl_days": 7, "pii": False},
        }

        defaults = type_defaults.get(record.record_type, {"ttl_days": 30, "pii": False})

        # Apply defaults if not specified
        for key, default_value in defaults.items():
            if key not in retention:
                retention[key] = default_value

    async def _persist_state(self) -> None:
        """Persist current state to disk."""
        try:
            state = {
                "session_history": self.session_history,
                "session_metadata": self.session_metadata,
                "facts_store": self.facts_store,
                "rag_content": self.rag_content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            state_file = os.path.join(self.storage_path, "dms_state.json")
            with open(state_file, "w") as f:
                json.dump(state, f, indent=2, default=str)

            logger.info(f"Persisted DMS state to {state_file}")

        except Exception as e:
            logger.error(f"Failed to persist DMS state: {e}")

    async def _load_state(self) -> None:
        """Load persisted state from disk."""
        try:
            state_file = os.path.join(self.storage_path, "dms_state.json")
            if os.path.exists(state_file):
                with open(state_file, "r") as f:
                    state = json.load(f)

                self.session_history = state.get("session_history", {})
                self.session_metadata = state.get("session_metadata", {})
                self.facts_store = state.get("facts_store", [])
                self.rag_content = state.get("rag_content", "")

                logger.info(f"Loaded DMS state from {state_file}")

        except Exception as e:
            logger.error(f"Failed to load DMS state: {e}")

    async def set_rag_content(self, content: str) -> None:
        """Set RAG content (admin operation)."""
        self.rag_content = content
        logger.info("RAG content updated")

    async def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        return {
            "sessions": len(self.session_history),
            "facts": len(self.facts_store),
            "total_conversation_turns": sum(
                len(history) for history in self.session_history.values()
            ),
            "pii_records": sum(
                1 for fact in self.facts_store if fact.get("retention", {}).get("pii", False)
            ),
        }

    async def _emit_memory_events(self, record: MemoryRecord, envelope: CoreEnvelope) -> None:
        """Emit telemetry and audit events for memory writes."""
        if not self.obs or not self.aud:
            return

        timestamp = datetime.now(timezone.utc).isoformat()

        # Emit telemetry
        telemetry_event = TelemetryEvent(
            timestamp=timestamp,
            request_id=envelope.request_id,
            component=self.component_name,
            event_type="memory_write",
            metadata={
                "record_type": record.record_type.value,
                "content_length": len(record.content),
                "has_provenance": bool(record.provenance),
                "retention_ttl_days": record.retention.get("ttl_days"),
                "pii_flagged": record.retention.get("pii", False),
            },
        )
        await self.obs.emit_event(telemetry_event)

        # Emit audit entry (with PII redaction)
        raw_payload = {
            "record_type": record.record_type.value,
            "content_length": len(record.content),
            "source": record.provenance.get("source"),
            "retention_ttl_days": record.retention.get("ttl_days"),
            "pii_flagged": record.retention.get("pii", False),
            "confidence": record.provenance.get("confidence"),
        }
        audit_entry = AuditEntry(
            entry_id=f"{envelope.request_id}_memory_{record.record_type.value}",
            timestamp=timestamp,
            request_id=envelope.request_id,
            session_id=envelope.session_id,
            actor=self.component_name,
            action_type="memory_write",
            payload=redact_pii(raw_payload),
        )
        await self.aud.append_entry(audit_entry)

    async def write_checkpoint(
        self, plan_id: str, step_idx: int, data: Dict[str, Any], envelope: CoreEnvelope
    ) -> str:
        """
        Write orchestration checkpoint for resumable multi-step tasks.
        """
        checkpoint_id = f"{plan_id}_step_{step_idx}"

        checkpoint_record = MemoryRecord(
            record_type=RecordType.TASK_ARTIFACT,
            content=json.dumps(
                {
                    "plan_id": plan_id,
                    "step_idx": step_idx,
                    "data": data,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "request_id": envelope.request_id,
                    "session_id": envelope.session_id,
                }
            ),
            provenance={
                "source": "orchestration_checkpoint",
                "request_id": envelope.request_id,
                "plan_id": plan_id,
                "step_idx": step_idx,
            },
            retention={"ttl_days": 7, "pii": False},  # Keep checkpoints for task resumption
        )

        result = await self.write(checkpoint_record, envelope)
        return checkpoint_id

    async def read_checkpoint(self, plan_id: str, step_idx: int) -> Optional[Dict[str, Any]]:
        """
        Read orchestration checkpoint for task resumption.
        """
        # This is a simplified implementation - in practice would need indexing
        # For now, return None (checkpoints not persisted across restarts)
        return None
