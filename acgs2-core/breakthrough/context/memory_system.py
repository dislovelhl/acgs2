"""
Constitutional Memory System
============================

Constitutional Hash: cdd01ef066bc6cf2

Implements persistent memory for governance decisions enabling
multi-day autonomous agent sessions with:
- Episodic memory (past decisions as precedents)
- Semantic memory (constitutional principles)
- Working memory (current context)

References:
- Memory in the Age of AI Agents (arXiv:2512.13564)
- MongoDB LangGraph Store patterns
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .. import CONSTITUTIONAL_HASH

logger = logging.getLogger(__name__)


class MemoryType(Enum):
    """Types of memory in the system."""
    EPISODIC = "episodic"  # Past decisions/events
    SEMANTIC = "semantic"  # Principles/knowledge
    WORKING = "working"    # Current context


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: Any
    memory_type: MemoryType
    timestamp: datetime
    importance: float
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type.value,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance,
            "metadata": self.metadata,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class Precedent:
    """A governance precedent from episodic memory."""
    case_id: str
    description: str
    decision: str
    outcome: str
    timestamp: datetime
    relevance_score: float
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "description": self.description,
            "decision": self.decision,
            "outcome": self.outcome,
            "timestamp": self.timestamp.isoformat(),
            "relevance_score": self.relevance_score,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class GovernanceCase:
    """A current governance case to evaluate."""
    case_id: str
    description: str
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    embedding: Optional[List[float]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "description": self.description,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class GovernanceDecision:
    """A governance decision to be stored."""
    decision_id: str
    case: GovernanceCase
    decision: str
    rationale: str
    confidence: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    precedents_used: List[str] = field(default_factory=list)
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "case": self.case.to_dict(),
            "decision": self.decision,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "precedents_used": self.precedents_used,
            "constitutional_hash": self.constitutional_hash,
        }


class EpisodicMemory:
    """
    Episodic Memory for past governance decisions.

    Stores decisions as precedents that can be retrieved
    for similar future cases using semantic search.
    """

    def __init__(self, max_entries: int = 10000):
        self.max_entries = max_entries
        self._entries: Dict[str, MemoryEntry] = {}
        self._embeddings_index: Dict[str, List[float]] = {}

        logger.info(f"Initialized EpisodicMemory with max_entries={max_entries}")

    async def store(self, decision: GovernanceDecision) -> str:
        """Store a governance decision as episodic memory."""
        entry_id = decision.decision_id

        # Create embedding from decision content
        embedding = await self._create_embedding(decision)

        entry = MemoryEntry(
            id=entry_id,
            content=decision.to_dict(),
            memory_type=MemoryType.EPISODIC,
            timestamp=decision.timestamp,
            importance=decision.confidence,
            embedding=embedding,
            metadata={
                "case_id": decision.case.case_id,
                "decision_type": "governance",
            }
        )

        # Evict if at capacity
        if len(self._entries) >= self.max_entries:
            await self._evict_least_important()

        self._entries[entry_id] = entry
        if embedding:
            self._embeddings_index[entry_id] = embedding

        logger.debug(f"Stored episodic memory: {entry_id}")
        return entry_id

    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_criteria: Optional[Dict[str, Any]] = None
    ) -> List[MemoryEntry]:
        """
        Search episodic memory by similarity.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            filter_criteria: Optional filters (e.g., constitutional_hash)

        Returns:
            List of matching memory entries
        """
        if not self._embeddings_index:
            return []

        # Compute similarities
        similarities = []
        for entry_id, embedding in self._embeddings_index.items():
            sim = self._cosine_similarity(query_embedding, embedding)
            entry = self._entries[entry_id]

            # Apply filters
            if filter_criteria:
                if not self._matches_filter(entry, filter_criteria):
                    continue

            similarities.append((entry_id, sim))

        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)

        # Return top-k entries
        results = []
        for entry_id, sim in similarities[:top_k]:
            entry = self._entries[entry_id]
            entry.metadata["similarity_score"] = sim
            results.append(entry)

        return results

    async def _create_embedding(self, decision: GovernanceDecision) -> List[float]:
        """Create embedding from decision content."""
        # In production, this would use a proper embedding model
        # For now, create a simple hash-based pseudo-embedding
        content = json.dumps(decision.to_dict(), sort_keys=True)
        hash_bytes = hashlib.sha256(content.encode()).digest()
        # Convert to float vector
        return [b / 255.0 for b in hash_bytes[:128]]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def _matches_filter(
        self,
        entry: MemoryEntry,
        filter_criteria: Dict[str, Any]
    ) -> bool:
        """Check if entry matches filter criteria."""
        for key, value in filter_criteria.items():
            if key == "constitutional_hash":
                if entry.constitutional_hash != value:
                    return False
            elif key in entry.metadata:
                if entry.metadata[key] != value:
                    return False
        return True

    async def _evict_least_important(self) -> None:
        """Evict least important entry to make room."""
        if not self._entries:
            return

        # Find entry with lowest importance
        min_entry_id = min(
            self._entries.keys(),
            key=lambda k: self._entries[k].importance
        )

        del self._entries[min_entry_id]
        if min_entry_id in self._embeddings_index:
            del self._embeddings_index[min_entry_id]

        logger.debug(f"Evicted episodic memory: {min_entry_id}")


class SemanticMemory:
    """
    Semantic Memory for constitutional principles and knowledge.

    Stores long-term factual knowledge that doesn't change
    with individual decisions.
    """

    def __init__(self):
        self._principles: Dict[str, MemoryEntry] = {}
        self._knowledge: Dict[str, MemoryEntry] = {}

        logger.info("Initialized SemanticMemory")

    async def store_principle(
        self,
        principle_id: str,
        content: str,
        importance: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a constitutional principle."""
        entry = MemoryEntry(
            id=principle_id,
            content=content,
            memory_type=MemoryType.SEMANTIC,
            timestamp=datetime.utcnow(),
            importance=importance,
            metadata=metadata or {}
        )

        self._principles[principle_id] = entry
        logger.debug(f"Stored principle: {principle_id}")
        return principle_id

    async def get_principle(self, principle_id: str) -> Optional[MemoryEntry]:
        """Retrieve a constitutional principle."""
        return self._principles.get(principle_id)

    async def get_all_principles(self) -> List[MemoryEntry]:
        """Get all constitutional principles."""
        return list(self._principles.values())

    async def store_knowledge(
        self,
        knowledge_id: str,
        content: Any,
        category: str,
        importance: float = 0.5
    ) -> str:
        """Store general knowledge."""
        entry = MemoryEntry(
            id=knowledge_id,
            content=content,
            memory_type=MemoryType.SEMANTIC,
            timestamp=datetime.utcnow(),
            importance=importance,
            metadata={"category": category}
        )

        self._knowledge[knowledge_id] = entry
        return knowledge_id

    async def search_knowledge(
        self,
        query: str,
        category: Optional[str] = None
    ) -> List[MemoryEntry]:
        """Search knowledge base."""
        results = []
        for entry in self._knowledge.values():
            if category and entry.metadata.get("category") != category:
                continue
            # Simple text matching (would use semantic search in production)
            if query.lower() in str(entry.content).lower():
                results.append(entry)
        return results


class WorkingMemory:
    """
    Working Memory for current context.

    Short-term memory that holds active context during
    governance processing. Uses TTL for automatic cleanup.
    """

    def __init__(self, default_ttl_seconds: int = 3600):
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        self._entries: Dict[str, Tuple[MemoryEntry, datetime]] = {}  # entry, expiry

        logger.info(f"Initialized WorkingMemory with TTL={default_ttl_seconds}s")

    async def store(
        self,
        key: str,
        content: Any,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """Store content in working memory with TTL."""
        ttl = timedelta(seconds=ttl_seconds) if ttl_seconds else self.default_ttl
        expiry = datetime.utcnow() + ttl

        entry = MemoryEntry(
            id=key,
            content=content,
            memory_type=MemoryType.WORKING,
            timestamp=datetime.utcnow(),
            importance=0.5,
        )

        self._entries[key] = (entry, expiry)
        return key

    async def get(self, key: str) -> Optional[Any]:
        """Get content from working memory."""
        await self._cleanup_expired()

        if key not in self._entries:
            return None

        entry, expiry = self._entries[key]
        if datetime.utcnow() > expiry:
            del self._entries[key]
            return None

        return entry.content

    async def delete(self, key: str) -> bool:
        """Delete entry from working memory."""
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    async def clear(self) -> None:
        """Clear all working memory."""
        self._entries.clear()

    async def _cleanup_expired(self) -> None:
        """Remove expired entries."""
        now = datetime.utcnow()
        expired = [
            key for key, (_, expiry) in self._entries.items()
            if now > expiry
        ]
        for key in expired:
            del self._entries[key]


class ConstitutionalMemorySystem:
    """
    Unified Constitutional Memory System.

    Integrates episodic, semantic, and working memory to enable
    multi-day autonomous governance with precedent retrieval.
    """

    def __init__(
        self,
        episodic_max_entries: int = 10000,
        working_ttl_seconds: int = 3600
    ):
        """
        Initialize the Constitutional Memory System.

        Args:
            episodic_max_entries: Max precedents to store
            working_ttl_seconds: Working memory TTL
        """
        self.episodic = EpisodicMemory(max_entries=episodic_max_entries)
        self.semantic = SemanticMemory()
        self.working = WorkingMemory(default_ttl_seconds=working_ttl_seconds)

        self._audit_log: List[Dict[str, Any]] = []
        self._stats = {
            "precedents_retrieved": 0,
            "decisions_stored": 0,
            "cache_hits": 0,
        }

        logger.info("Initialized ConstitutionalMemorySystem")

    async def recall_relevant_precedents(
        self,
        current_case: GovernanceCase,
        top_k: int = 10
    ) -> List[Precedent]:
        """
        Retrieve relevant past governance decisions.

        Args:
            current_case: The current case to find precedents for
            top_k: Number of precedents to retrieve

        Returns:
            List of relevant precedents
        """
        # Create embedding from current case
        if current_case.embedding:
            query_embedding = current_case.embedding
        else:
            query_embedding = await self._create_case_embedding(current_case)

        # Search episodic memory
        similar_entries = await self.episodic.search(
            query_embedding=query_embedding,
            top_k=top_k,
            filter_criteria={"constitutional_hash": CONSTITUTIONAL_HASH}
        )

        # Convert to precedents
        precedents = []
        for entry in similar_entries:
            content = entry.content
            precedent = Precedent(
                case_id=content.get("case", {}).get("case_id", entry.id),
                description=content.get("case", {}).get("description", ""),
                decision=content.get("decision", ""),
                outcome=content.get("rationale", ""),
                timestamp=entry.timestamp,
                relevance_score=entry.metadata.get("similarity_score", 0.0),
            )
            precedents.append(precedent)

        # Rank by relevance and recency
        precedents = self._rank_precedents(precedents, current_case)

        self._stats["precedents_retrieved"] += len(precedents)
        return precedents

    async def commit_decision(self, decision: GovernanceDecision) -> str:
        """
        Store a governance decision for future reference.

        Args:
            decision: The decision to store

        Returns:
            The decision ID
        """
        # Store in episodic memory
        entry_id = await self.episodic.store(decision)

        # Record in audit log
        await self._record_audit(decision)

        self._stats["decisions_stored"] += 1
        logger.info(f"Committed decision: {decision.decision_id}")

        return entry_id

    async def get_constitutional_principles(self) -> List[MemoryEntry]:
        """Get all stored constitutional principles."""
        return await self.semantic.get_all_principles()

    async def store_context(
        self,
        key: str,
        content: Any,
        ttl_seconds: Optional[int] = None
    ) -> str:
        """Store context in working memory."""
        return await self.working.store(key, content, ttl_seconds)

    async def get_context(self, key: str) -> Optional[Any]:
        """Retrieve context from working memory."""
        return await self.working.get(key)

    def _rank_precedents(
        self,
        precedents: List[Precedent],
        current_case: GovernanceCase
    ) -> List[Precedent]:
        """
        Rank precedents by relevance and recency.

        Combined scoring: 0.7 * relevance + 0.3 * recency
        """
        now = datetime.utcnow()
        max_age_days = 365  # 1 year

        for precedent in precedents:
            # Recency score (1.0 for today, 0.0 for 1 year ago)
            age = (now - precedent.timestamp).days
            recency_score = max(0.0, 1.0 - (age / max_age_days))

            # Combined score
            combined_score = 0.7 * precedent.relevance_score + 0.3 * recency_score
            precedent.relevance_score = combined_score

        # Sort by combined score
        precedents.sort(key=lambda p: p.relevance_score, reverse=True)
        return precedents

    async def _create_case_embedding(
        self,
        case: GovernanceCase
    ) -> List[float]:
        """Create embedding from governance case."""
        content = json.dumps(case.to_dict(), sort_keys=True)
        hash_bytes = hashlib.sha256(content.encode()).digest()
        return [b / 255.0 for b in hash_bytes[:128]]

    async def _record_audit(self, decision: GovernanceDecision) -> None:
        """Record decision in audit log."""
        self._audit_log.append({
            "timestamp": datetime.utcnow().isoformat(),
            "decision_id": decision.decision_id,
            "case_id": decision.case.case_id,
            "constitutional_hash": decision.constitutional_hash,
        })

    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics."""
        return {
            **self._stats,
            "episodic_entries": len(self.episodic._entries),
            "semantic_principles": len(self.semantic._principles),
            "working_entries": len(self.working._entries),
            "audit_log_size": len(self._audit_log),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }
