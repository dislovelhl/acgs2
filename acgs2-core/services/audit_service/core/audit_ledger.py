"""
ACGS-2 Audit Ledger with Multi-Backend Blockchain Anchoring
Constitutional Hash: cdd01ef066bc6cf2

Enhanced with:
- Multi-backend blockchain anchoring (Local, Ethereum L2, Arweave, Hyperledger)
- Circuit breaker integration for fault tolerance
- Fire-and-forget async pattern for minimal latency impact
- Configurable anchoring strategies
"""

import asyncio
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .merkle_tree.merkle_tree import MerkleTree

# Blockchain anchoring - prefer unified manager, fallback to local
try:
    from .blockchain_anchor_manager import (
        AnchorBackend,
        AnchorManagerConfig,
        AnchorResult,
        BlockchainAnchorManager,
        get_anchor_manager,
    )

    ANCHOR_MANAGER_AVAILABLE = True
except ImportError:
    ANCHOR_MANAGER_AVAILABLE = False

# Fallback to local anchor if manager unavailable
try:
    from .anchor import LocalFileSystemAnchor
except ImportError:
    LocalFileSystemAnchor = None

try:
    import redis
    from shared.config import settings

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    settings = None

logger = logging.getLogger(__name__)

from shared.constants import CONSTITUTIONAL_HASH

# Import ValidationResult from the canonical source (enhanced_agent_bus)
try:
    from enhanced_agent_bus.validators import ValidationResult
except ImportError:

    @dataclass
    class ValidationResult:
        """Fallback ValidationResult for standalone usage."""

        is_valid: bool = True
        errors: List[str] = field(default_factory=list)
        warnings: List[str] = field(default_factory=list)
        metadata: Dict[str, Any] = field(default_factory=dict)
        constitutional_hash: str = CONSTITUTIONAL_HASH

        def to_dict(self) -> Dict[str, Any]:
            return {
                "is_valid": self.is_valid,
                "errors": self.errors,
                "warnings": self.warnings,
                "metadata": self.metadata,
                "constitutional_hash": self.constitutional_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }


@dataclass
class AuditEntry:
    """Represents a single entry in the audit ledger."""

    validation_result: ValidationResult
    hash: str
    timestamp: float
    batch_id: Optional[str] = None
    merkle_proof: Optional[List[Tuple[str, bool]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_result": self.validation_result.to_dict(),
            "hash": self.hash,
            "timestamp": self.timestamp,
            "batch_id": self.batch_id,
            "merkle_proof": self.merkle_proof,
        }


@dataclass
class AuditLedgerConfig:
    """Configuration for AuditLedger."""

    batch_size: int = 100
    redis_url: Optional[str] = None
    persistence_file: str = "audit_ledger_storage.json"

    # Blockchain anchoring configuration
    enable_blockchain_anchoring: bool = True
    blockchain_backends: List[str] = field(
        default_factory=lambda: ["local"]
    )  # Options: local, ethereum_l2, arweave, hyperledger
    enable_failover: bool = True
    anchor_fire_and_forget: bool = True  # Use async fire-and-forget pattern

    # Ethereum L2 settings (if enabled)
    ethereum_network: str = "optimism"  # optimism, arbitrum, polygon, base

    # Circuit breaker settings for blockchain
    circuit_breaker_fail_max: int = 3
    circuit_breaker_reset_timeout: int = 30

    constitutional_hash: str = CONSTITUTIONAL_HASH


class AuditLedger:
    """
    Asynchronous immutable audit ledger for recording validation results.

    Constitutional Hash: cdd01ef066bc6cf2

    Enhanced features:
    - Multi-backend blockchain anchoring (Local, Ethereum L2, Arweave, Hyperledger)
    - Circuit breaker integration for fault tolerance
    - Fire-and-forget async pattern for minimal latency impact
    - Configurable anchoring strategies and failover
    """

    def __init__(
        self,
        batch_size: int = 100,
        redis_url: Optional[str] = None,
        config: Optional[AuditLedgerConfig] = None,
    ):
        # Support both old API and new config-based API
        if config:
            self.config = config
        else:
            self.config = AuditLedgerConfig(batch_size=batch_size, redis_url=redis_url)

        self.entries: List[AuditEntry] = []
        self.current_batch: List[ValidationResult] = []
        self.batch_size = self.config.batch_size
        self.merkle_tree: Optional[MerkleTree] = None
        self.batch_counter = 0

        # Initialize blockchain anchoring
        self._anchor_manager: Optional[BlockchainAnchorManager] = None
        self._legacy_anchor = None
        self._init_blockchain_anchoring()

        # Persistence (Redis first, then File fallback)
        self.redis_client = None
        self.persistence_file = self.config.persistence_file

        if HAS_REDIS:
            url = self.config.redis_url or (
                settings.redis.url if settings else "redis://localhost:6379"
            )
            try:
                self.redis_client = redis.from_url(url)
                logger.info(f"[{CONSTITUTIONAL_HASH}] AuditLedger connected to Redis at {url}")
            except Exception as e:
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] Fallback to local file persistence: "
                    f"Redis connection failed: {e}"
                )
        else:
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] Using local file persistence (Redis not available)"
            )

        # Async components
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._running = False

        # Anchoring statistics
        self._anchor_stats = {
            "total_anchored": 0,
            "successful": 0,
            "failed": 0,
            "pending": 0,
        }

    def _init_blockchain_anchoring(self):
        """Initialize blockchain anchoring backend."""
        if not self.config.enable_blockchain_anchoring:
            logger.info(f"[{CONSTITUTIONAL_HASH}] Blockchain anchoring disabled")
            return

        # Try to use unified BlockchainAnchorManager
        if ANCHOR_MANAGER_AVAILABLE:
            try:
                # Convert string backend names to AnchorBackend enum
                backends = []
                for backend_name in self.config.blockchain_backends:
                    try:
                        backend = AnchorBackend(backend_name.lower())
                        backends.append(backend)
                    except ValueError:
                        logger.warning(
                            f"[{CONSTITUTIONAL_HASH}] Unknown blockchain backend: {backend_name}"
                        )

                if not backends:
                    backends = [AnchorBackend.LOCAL]

                anchor_config = AnchorManagerConfig(
                    enabled_backends=backends,
                    enable_failover=self.config.enable_failover,
                    ethereum_network=self.config.ethereum_network,
                    circuit_breaker_fail_max=self.config.circuit_breaker_fail_max,
                    circuit_breaker_reset_timeout=self.config.circuit_breaker_reset_timeout,
                )
                self._anchor_manager = BlockchainAnchorManager(anchor_config)
                logger.info(
                    f"[{CONSTITUTIONAL_HASH}] Initialized BlockchainAnchorManager "
                    f"with backends: {[b.value for b in backends]}"
                )
                return
            except Exception as e:
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] Failed to initialize BlockchainAnchorManager: {e}"
                )

        # Fallback to legacy LocalFileSystemAnchor
        if LocalFileSystemAnchor:
            self._legacy_anchor = LocalFileSystemAnchor()
            logger.info(f"[{CONSTITUTIONAL_HASH}] Using legacy LocalFileSystemAnchor")
        else:
            logger.warning(f"[{CONSTITUTIONAL_HASH}] No blockchain anchoring available")

    async def start(self):
        """Start the background processing worker and blockchain anchor manager."""
        if not self._running:
            # Try to restore state from Redis
            await self._load_from_storage()

            # Start blockchain anchor manager
            if self._anchor_manager:
                try:
                    await self._anchor_manager.start()
                    logger.info(f"[{CONSTITUTIONAL_HASH}] BlockchainAnchorManager started")
                except Exception as e:
                    logger.warning(
                        f"[{CONSTITUTIONAL_HASH}] Failed to start BlockchainAnchorManager: {e}"
                    )

            self._running = True
            self._worker_task = asyncio.create_task(self._processing_worker())
            logger.info(f"[{CONSTITUTIONAL_HASH}] AuditLedger worker started")

    async def stop(self):
        """Stop the background processing worker and flush queue."""
        self._running = False
        if self._queue.empty():
            if self._worker_task:
                self._worker_task.cancel()
        else:
            # Wait for queue to be empty
            await self._queue.join()
            if self._worker_task:
                self._worker_task.cancel()

        # Stop blockchain anchor manager
        if self._anchor_manager:
            try:
                await self._anchor_manager.stop()
                logger.info(f"[{CONSTITUTIONAL_HASH}] BlockchainAnchorManager stopped")
            except Exception as e:
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] Error stopping BlockchainAnchorManager: {e}"
                )

        logger.info(f"[{CONSTITUTIONAL_HASH}] AuditLedger worker stopped")

    async def add_validation_result(self, validation_result: ValidationResult) -> str:
        """Add a validation result to the ledger (non-blocking)."""
        entry_hash = self._hash_validation_result(validation_result)

        # We put it in the queue for the background worker to handle
        # This decouples the caller from Merkle Tree construction/Blockchain lag
        await self._queue.put((entry_hash, validation_result, time.time()))
        return entry_hash

    async def _processing_worker(self):
        """Background worker that builds batches and commits them."""
        while self._running:
            try:
                # Get item from queue
                entry_hash, vr, ts = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                async with self._lock:
                    entry = AuditEntry(validation_result=vr, hash=entry_hash, timestamp=ts)
                    self.entries.append(entry)
                    self.current_batch.append(vr)

                    if len(self.current_batch) >= self.batch_size:
                        await self._commit_batch()

                self._queue.task_done()
            except asyncio.TimeoutError:
                # If we've been idle and have a partial batch, commit it?
                # For now, only commit if queue is empty or batch full
                if self.current_batch and self._queue.empty():
                    async with self._lock:
                        await self._commit_batch()
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in AuditLedger worker: {e}")

    def _hash_validation_result(self, validation_result: ValidationResult) -> str:
        hash_data = {
            "is_valid": validation_result.is_valid,
            "errors": validation_result.errors,
            "warnings": validation_result.warnings,
            "metadata": validation_result.metadata,
            "constitutional_hash": validation_result.constitutional_hash,
        }
        data = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    async def _commit_batch(self) -> str:
        if not self.current_batch:
            return ""

        batch_id = f"batch_{self.batch_counter}_{int(time.time())}"
        self.batch_counter += 1

        batch_data = []
        entries_hashes = []
        for vr in self.current_batch:
            hash_data = {
                "is_valid": vr.is_valid,
                "errors": vr.errors,
                "warnings": vr.warnings,
                "metadata": vr.metadata,
                "constitutional_hash": vr.constitutional_hash,
            }
            batch_data.append(json.dumps(hash_data, sort_keys=True).encode())
            entries_hashes.append(self._hash_validation_result(vr))

        self.merkle_tree = MerkleTree(batch_data)
        root_hash = self.merkle_tree.get_root_hash()

        # Update entries with proofs
        batch_count = len(self.current_batch)
        for i, entry in enumerate(self.entries[-batch_count:]):
            entry.batch_id = batch_id
            if self.merkle_tree:
                entry.merkle_proof = self.merkle_tree.get_proof(i)

        self.current_batch = []
        logger.info(f"[{CONSTITUTIONAL_HASH}] Committed batch {batch_id} with root {root_hash}")

        # Persist to Redis
        await self._save_to_storage(batch_id, root_hash, batch_data)

        # Anchor to Blockchain
        await self._anchor_batch(
            root_hash=root_hash,
            batch_id=batch_id,
            entry_count=batch_count,
            entries_hashes=entries_hashes,
        )

        return batch_id

    async def _anchor_batch(
        self,
        root_hash: str,
        batch_id: str,
        entry_count: int,
        entries_hashes: List[str],
    ):
        """Anchor batch to blockchain using configured backend."""
        self._anchor_stats["total_anchored"] += 1
        self._anchor_stats["pending"] += 1

        metadata = {
            "entry_count": entry_count,
            "entries_hashes": entries_hashes,
            "timestamp": time.time(),
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

        # Use BlockchainAnchorManager if available
        if self._anchor_manager:
            if self.config.anchor_fire_and_forget:
                # Fire-and-forget pattern for minimal latency impact
                success = await self._anchor_manager.anchor_root(
                    root_hash=root_hash,
                    batch_id=batch_id,
                    metadata=metadata,
                    callback=self._on_anchor_complete,
                )
                if not success:
                    self._anchor_stats["pending"] -= 1
                    self._anchor_stats["failed"] += 1
                    logger.warning(
                        f"[{CONSTITUTIONAL_HASH}] Failed to queue anchor for batch {batch_id}"
                    )
            else:
                # Synchronous anchoring (wait for result)
                try:
                    result = await self._anchor_manager.anchor_root_sync(
                        root_hash=root_hash,
                        batch_id=batch_id,
                        metadata=metadata,
                    )
                    self._on_anchor_complete(result)
                except Exception as e:
                    self._anchor_stats["pending"] -= 1
                    self._anchor_stats["failed"] += 1
                    logger.error(
                        f"[{CONSTITUTIONAL_HASH}] Anchor sync failed for batch {batch_id}: {e}"
                    )

        # Fallback to legacy LocalFileSystemAnchor
        elif self._legacy_anchor:
            try:
                self._legacy_anchor.anchor_root(root_hash)
                self._anchor_stats["pending"] -= 1
                self._anchor_stats["successful"] += 1
                logger.info(f"[{CONSTITUTIONAL_HASH}] Batch {batch_id} anchored via legacy anchor")
            except Exception as e:
                self._anchor_stats["pending"] -= 1
                self._anchor_stats["failed"] += 1
                logger.error(
                    f"[{CONSTITUTIONAL_HASH}] Legacy anchor failed for batch {batch_id}: {e}"
                )
        else:
            self._anchor_stats["pending"] -= 1
            logger.warning(
                f"[{CONSTITUTIONAL_HASH}] No anchor backend available for batch {batch_id}"
            )

    def _on_anchor_complete(self, result: AnchorResult):
        """Callback for async anchor completion."""
        self._anchor_stats["pending"] -= 1

        if result.status.value in ("confirmed", "submitted"):
            self._anchor_stats["successful"] += 1
            logger.info(
                f"[{CONSTITUTIONAL_HASH}] Anchor completed: "
                f"{result.backend.value} -> {result.status.value} "
                f"(tx: {result.transaction_id})"
            )
        else:
            self._anchor_stats["failed"] += 1
            logger.warning(
                f"[{CONSTITUTIONAL_HASH}] Anchor failed: "
                f"{result.backend.value} -> {result.status.value} "
                f"(error: {result.error})"
            )

    async def _save_to_storage(self, batch_id: str, root_hash: str, batch_data: List[bytes]):
        """Persist batch information to storage."""
        batch_count = len(batch_data)
        entries_data = [entry.to_dict() for entry in self.entries[-batch_count:]]

        # 1. Try Redis
        if self.redis_client:
            try:
                self.redis_client.set(f"audit:batch:{batch_id}:root", root_hash)
                self.redis_client.set(f"audit:batch:{batch_id}:entries", json.dumps(entries_data))
                self.redis_client.set("audit:batch_counter", self.batch_counter)
                self.redis_client.rpush("audit:batches", batch_id)
                logger.debug(f"Persisted batch {batch_id} to Redis")
                return
            except Exception as e:
                logger.error(f"Error saving to Redis: {e}")

        # 2. Local File Fallback
        try:
            storage_data = {"batch_counter": self.batch_counter, "batches": {}}
            # Load existing
            try:
                with open(self.persistence_file, "r") as f:
                    storage_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

            storage_data["batch_counter"] = self.batch_counter
            storage_data["batches"][batch_id] = {"root": root_hash, "entries": entries_data}

            with open(self.persistence_file, "w") as f:
                json.dump(storage_data, f)
            logger.debug(f"Persisted batch {batch_id} to local file")
        except Exception as e:
            logger.error(f"Error saving to local file: {e}")

    async def _load_from_storage(self):
        """Restore ledger state from storage."""
        # 1. Try Redis
        if self.redis_client:
            try:
                counter = self.redis_client.get("audit:batch_counter")
                if counter:
                    self.batch_counter = int(counter)

                batch_ids = self.redis_client.lrange("audit:batches", 0, -1)
                for b_id_bytes in batch_ids:
                    b_id = b_id_bytes.decode()
                    entries_json = self.redis_client.get(f"audit:batch:{b_id}:entries")
                    if entries_json:
                        self._reconstruct_entries(json.loads(entries_json))

                if batch_ids:
                    logger.info(f"Loaded {len(self.entries)} entries from Redis")
                    return
            except Exception as e:
                logger.error(f"Error loading from Redis: {e}")

        # 2. Local File Fallback
        try:
            with open(self.persistence_file, "r") as f:
                storage_data = json.load(f)
                self.batch_counter = storage_data.get("batch_counter", 0)
                # Sort batches to maintain order if possible, though dict is insertion ordered in modern python
                for b_id, b_data in storage_data.get("batches", {}).items():
                    self._reconstruct_entries(b_data["entries"])
            # Rebuild the latest Merkle Tree if we have batches
            if self.entries:
                self.merkle_tree = MerkleTree([e.hash.encode() for e in self.entries])
                logger.info(f"Rebuilt Merkle Tree with {len(self.entries)} entries")
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.error(f"Error loading from local file: {e}")

    def _reconstruct_entries(self, entries_list: List[Dict[str, Any]]):
        """Helper to reconstruct AuditEntry objects from dicts."""
        for e_dict in entries_list:
            vr_dict = e_dict["validation_result"]
            vr = ValidationResult(
                is_valid=vr_dict["is_valid"],
                errors=vr_dict["errors"],
                warnings=vr_dict["warnings"],
                metadata=vr_dict["metadata"],
                constitutional_hash=vr_dict["constitutional_hash"],
            )

            entry = AuditEntry(
                validation_result=vr,
                hash=e_dict["hash"],
                timestamp=e_dict["timestamp"],
                batch_id=e_dict["batch_id"],
                merkle_proof=e_dict["merkle_proof"],
            )
            self.entries.append(entry)

    def get_batch_root_hash(self, batch_id: str) -> Optional[str]:
        if self.merkle_tree:
            return self.merkle_tree.get_root_hash()
        return None

    async def verify_entry(
        self, entry_hash: str, merkle_proof: List[Tuple[str, bool]], root_hash: str
    ) -> bool:
        entry = None
        async with self._lock:
            for e in self.entries:
                if e.hash == entry_hash:
                    entry = e
                    break

        if not entry:
            return False

        hash_data = {
            "is_valid": entry.validation_result.is_valid,
            "errors": entry.validation_result.errors,
            "warnings": entry.validation_result.warnings,
            "metadata": entry.validation_result.metadata,
            "constitutional_hash": entry.validation_result.constitutional_hash,
        }
        entry_data = json.dumps(hash_data, sort_keys=True).encode()
        return (
            self.merkle_tree.verify_proof(entry_data, merkle_proof, root_hash)
            if self.merkle_tree
            else False
        )

    async def get_entries_by_batch(self, batch_id: str) -> List[AuditEntry]:
        async with self._lock:
            return [entry for entry in self.entries if entry.batch_id == batch_id]

    async def get_ledger_stats(self) -> Dict[str, Any]:
        async with self._lock:
            stats = {
                "total_entries": len(self.entries),
                "current_batch_size": len(self.current_batch),
                "batch_size_limit": self.batch_size,
                "batches_committed": self.batch_counter,
                "current_root_hash": self.merkle_tree.get_root_hash() if self.merkle_tree else None,
                "queue_size": self._queue.qsize(),
                "constitutional_hash": CONSTITUTIONAL_HASH,
                "anchoring": {
                    **self._anchor_stats,
                    "manager_type": (
                        "BlockchainAnchorManager"
                        if self._anchor_manager
                        else ("LocalFileSystemAnchor" if self._legacy_anchor else "none")
                    ),
                    "enabled_backends": self.config.blockchain_backends,
                    "fire_and_forget": self.config.anchor_fire_and_forget,
                },
            }

            # Add anchor manager stats if available
            if self._anchor_manager:
                stats["anchoring"]["manager_stats"] = self._anchor_manager.get_stats()

            return stats

    async def get_anchor_health(self) -> Dict[str, Any]:
        """Get health status of blockchain anchoring backends."""
        if self._anchor_manager:
            return await self._anchor_manager.health_check()

        return {
            "overall": "healthy" if self._legacy_anchor else "unavailable",
            "backends": {"local": {"status": "healthy" if self._legacy_anchor else "unavailable"}},
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    def get_recent_anchor_results(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get recent anchor results for monitoring."""
        if self._anchor_manager:
            return self._anchor_manager.get_recent_results(n)
        return []

    async def force_commit_batch(self) -> str:
        async with self._lock:
            return await self._commit_batch()

    async def prepare_blockchain_transaction(self, batch_id: str) -> Dict[str, Any]:
        """
        准备区块链交易数据
        返回包含根哈希和批次信息的交易数据
        """
        root_hash = self.get_batch_root_hash(batch_id)
        entries = await self.get_entries_by_batch(batch_id)

        return {
            "batch_id": batch_id,
            "root_hash": root_hash,
            "entry_count": len(entries),
            "timestamp": int(time.time()),
            "entries_hashes": [entry.hash for entry in entries],
        }
