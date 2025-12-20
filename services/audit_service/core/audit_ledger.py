import asyncio
import hashlib
import json
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from .merkle_tree.merkle_tree import MerkleTree

try:
    from shared.config import settings
    import redis
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
                "timestamp": datetime.now(timezone.utc).isoformat()
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
            "merkle_proof": self.merkle_proof
        }


class AuditLedger:
    """Asynchronous immutable audit ledger for recording validation results.

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, batch_size: int = 100, redis_url: Optional[str] = None):
        self.entries: List[AuditEntry] = []
        self.current_batch: List[ValidationResult] = []
        self.batch_size = batch_size
        self.merkle_tree: Optional[MerkleTree] = None
        self.batch_counter = 0
        
        # Persistence (Redis first, then File fallback)
        self.redis_client = None
        self.persistence_file = "audit_ledger_storage.json"
        
        if HAS_REDIS:
            url = redis_url or (settings.redis.url if settings else "redis://localhost:6379")
            try:
                self.redis_client = redis.from_url(url)
                logger.info(f"AuditLedger connected to Redis at {url}")
            except Exception as e:
                logger.warning(f"Fallback to local file persistence: Redis connection failed: {e}")
        else:
            logger.info("Using local file persistence (Redis not available)")

        # Async components
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._running = False

    async def start(self):
        """Start the background processing worker."""
        if not self._running:
            # Try to restore state from Redis
            await self._load_from_storage()
            
            self._running = True
            self._worker_task = asyncio.create_task(self._processing_worker())
            logger.info("AsyncAuditLedger worker started")

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
        logger.info("AsyncAuditLedger worker stopped")

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
                    entry = AuditEntry(
                        validation_result=vr,
                        hash=entry_hash,
                        timestamp=ts
                    )
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
            'is_valid': validation_result.is_valid,
            'errors': validation_result.errors,
            'warnings': validation_result.warnings,
            'metadata': validation_result.metadata,
            'constitutional_hash': validation_result.constitutional_hash
        }
        data = json.dumps(hash_data, sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()

    async def _commit_batch(self) -> str:
        if not self.current_batch:
            return ""

        batch_id = f"batch_{self.batch_counter}_{int(time.time())}"
        self.batch_counter += 1

        batch_data = []
        for vr in self.current_batch:
            hash_data = {
                'is_valid': vr.is_valid,
                'errors': vr.errors,
                'warnings': vr.warnings,
                'metadata': vr.metadata,
                'constitutional_hash': vr.constitutional_hash
            }
            batch_data.append(json.dumps(hash_data, sort_keys=True).encode())
        
        self.merkle_tree = MerkleTree(batch_data)
        root_hash = self.merkle_tree.get_root_hash()

        # Update entries with proofs
        batch_count = len(self.current_batch)
        for i, entry in enumerate(self.entries[-batch_count:]):
            entry.batch_id = batch_id
            if self.merkle_tree:
                entry.merkle_proof = self.merkle_tree.get_proof(i)

        self.current_batch = []
        logger.info(f"Committed batch {batch_id} with root {root_hash}")
        
        # Persist to Redis
        await self._save_to_storage(batch_id, root_hash, batch_data)
        
        return batch_id

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
            storage_data = {
                "batch_counter": self.batch_counter,
                "batches": {}
            }
            # Load existing
            try:
                with open(self.persistence_file, 'r') as f:
                    storage_data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            
            storage_data["batch_counter"] = self.batch_counter
            storage_data["batches"][batch_id] = {
                "root": root_hash,
                "entries": entries_data
            }
            
            with open(self.persistence_file, 'w') as f:
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
            with open(self.persistence_file, 'r') as f:
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
            vr_dict = e_dict['validation_result']
            vr = ValidationResult(
                is_valid=vr_dict['is_valid'],
                errors=vr_dict['errors'],
                warnings=vr_dict['warnings'],
                metadata=vr_dict['metadata'],
                constitutional_hash=vr_dict['constitutional_hash']
            )
            
            entry = AuditEntry(
                validation_result=vr,
                hash=e_dict['hash'],
                timestamp=e_dict['timestamp'],
                batch_id=e_dict['batch_id'],
                merkle_proof=e_dict['merkle_proof']
            )
            self.entries.append(entry)

    def get_batch_root_hash(self, batch_id: str) -> Optional[str]:
        if self.merkle_tree:
            return self.merkle_tree.get_root_hash()
        return None

    async def verify_entry(self, entry_hash: str, merkle_proof: List[Tuple[str, bool]],
                          root_hash: str) -> bool:
        entry = None
        async with self._lock:
            for e in self.entries:
                if e.hash == entry_hash:
                    entry = e
                    break

        if not entry:
            return False

        hash_data = {
            'is_valid': entry.validation_result.is_valid,
            'errors': entry.validation_result.errors,
            'warnings': entry.validation_result.warnings,
            'metadata': entry.validation_result.metadata,
            'constitutional_hash': entry.validation_result.constitutional_hash
        }
        entry_data = json.dumps(hash_data, sort_keys=True).encode()
        return self.merkle_tree.verify_proof(entry_data, merkle_proof, root_hash) \
               if self.merkle_tree else False

    async def get_entries_by_batch(self, batch_id: str) -> List[AuditEntry]:
        async with self._lock:
            return [entry for entry in self.entries if entry.batch_id == batch_id]

    async def get_ledger_stats(self) -> Dict[str, Any]:
        async with self._lock:
            return {
                "total_entries": len(self.entries),
                "current_batch_size": len(self.current_batch),
                "batch_size_limit": self.batch_size,
                "batches_committed": self.batch_counter,
                "current_root_hash": self.merkle_tree.get_root_hash() if self.merkle_tree else None,
                "queue_size": self._queue.qsize()
            }

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
            "entries_hashes": [entry.hash for entry in entries]
        }