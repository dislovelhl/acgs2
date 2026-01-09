"""
ACGS-2 Unified Blockchain Anchor Manager
Constitutional Hash: cdd01ef066bc6cf2

Provides a unified interface for multi-backend blockchain anchoring with:
- Circuit breaker integration for fault tolerance
- Multi-backend failover (Ethereum L2, Arweave, Local)
- Async batching for efficient submission
- Health monitoring and status reporting
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

try:
    from src.core.shared.constants import CONSTITUTIONAL_HASH
except ImportError:
    CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"

try:
    from src.core.shared.circuit_breaker import (
        CircuitBreakerConfig,
        get_circuit_breaker,
    )

    CIRCUIT_BREAKER_AVAILABLE = True
except ImportError:
    CIRCUIT_BREAKER_AVAILABLE = False

logger = logging.getLogger(__name__)


class AnchorBackend(Enum):
    """Supported blockchain anchor backends."""

    LOCAL = "local"
    ETHEREUM_L2 = "ethereum_l2"
    ARWEAVE = "arweave"
    HYPERLEDGER = "hyperledger"
    SOLANA = "solana"


class AnchorStatus(Enum):
    """Status of anchor operation."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"


@dataclass
class AnchorResult:
    """Result of a blockchain anchoring operation."""

    backend: AnchorBackend
    status: AnchorStatus
    batch_id: Optional[str] = None
    transaction_id: Optional[str] = None
    block_info: Optional[Dict[str, Any]] = None
    timestamp: float = field(default_factory=time.time)
    start_time: Optional[float] = None  # Latency tracking
    error: Optional[str] = None
    constitutional_hash: str = CONSTITUTIONAL_HASH

    def to_dict(self) -> Dict[str, Any]:
        return {
            "backend": self.backend.value,
            "status": self.status.value,
            "batch_id": self.batch_id,
            "transaction_id": self.transaction_id,
            "block_info": self.block_info,
            "timestamp": self.timestamp,
            "latency": (self.timestamp - self.start_time) if self.start_time else 0,
            "error": self.error,
            "constitutional_hash": self.constitutional_hash,
        }


@dataclass
class AnchorManagerConfig:
    """Configuration for BlockchainAnchorManager."""

    # Enabled backends (in priority order)
    enabled_backends: List[AnchorBackend] = field(default_factory=lambda: [AnchorBackend.LOCAL])

    # Failover settings
    enable_failover: bool = True
    max_failover_attempts: int = 2

    # Batching settings
    batch_submission_delay_s: float = 1.0
    max_batch_size: int = 100

    # Circuit breaker settings (per backend)
    circuit_breaker_fail_max: int = 3
    circuit_breaker_reset_timeout: int = 30

    # Retry settings
    retry_delay_s: float = 0.5
    max_retries: int = 3

    # Async queue settings
    queue_size: int = 1000
    worker_count: int = 2

    # Global mode
    live: bool = True

    # Network-specific settings
    ethereum_network: str = "optimism"
    arweave_host: str = "arweave.net"


@dataclass
class PendingAnchor:
    """Pending anchor request in the queue."""

    root_hash: str
    batch_id: str
    metadata: Dict[str, Any]
    timestamp: float
    callbacks: List[Callable[[AnchorResult], None]] = field(default_factory=list)


class BlockchainAnchorManager:
    """
    Unified manager for multi-backend blockchain anchoring.

    Features:
    - Multi-backend support with automatic failover
    - Circuit breaker integration for fault tolerance
    - Async batching for efficient submission
    - Health monitoring and status reporting
    - Fire-and-forget pattern for minimal latency impact

    Constitutional Hash: cdd01ef066bc6cf2
    """

    def __init__(self, config: Optional[AnchorManagerConfig] = None):
        self.config = config or AnchorManagerConfig()
        self._backends: Dict[AnchorBackend, Any] = {}
        self._circuit_breakers: Dict[AnchorBackend, Any] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=self.config.queue_size)
        self._workers: List[asyncio.Task] = []
        self._running = False
        self._stats: Dict[str, Any] = {
            "total_anchored": 0,
            "successful": 0,
            "failed": 0,
            "failovers": 0,
            "by_backend": {b.value: 0 for b in AnchorBackend},
        }
        self._recent_results: List[AnchorResult] = []
        self._max_recent_results = 100

        self._initialize_backends()

    def _initialize_backends(self):
        """Initialize enabled blockchain backends."""
        for backend in self.config.enabled_backends:
            try:
                if backend == AnchorBackend.LOCAL:
                    from .anchor import LocalFileSystemAnchor

                    self._backends[backend] = LocalFileSystemAnchor()
                    logger.info(f"[{CONSTITUTIONAL_HASH}] Initialized LOCAL anchor backend")

                elif backend == AnchorBackend.ETHEREUM_L2:
                    from ..blockchain.ethereum_l2.ethereum_client import (
                        EthereumL2Client,
                    )

                    self._backends[backend] = EthereumL2Client(
                        network=self.config.ethereum_network,
                        config={"contract_address": "0x..."},  # Configure appropriately
                    )
                    logger.info(
                        f"[{CONSTITUTIONAL_HASH}] Initialized ETHEREUM_L2 anchor backend "
                        f"({self.config.ethereum_network})"
                    )

                elif backend == AnchorBackend.ARWEAVE:
                    from ..blockchain.arweave.arweave_client import ArweaveClient

                    self._backends[backend] = ArweaveClient(
                        config={"host": self.config.arweave_host}
                    )
                    logger.info(f"[{CONSTITUTIONAL_HASH}] Initialized ARWEAVE anchor backend")

                elif backend == AnchorBackend.HYPERLEDGER:
                    from ..blockchain.hyperledger_fabric.fabric_client import (
                        FabricClient,
                    )

                    self._backends[backend] = FabricClient(config={})
                    logger.info(f"[{CONSTITUTIONAL_HASH}] Initialized HYPERLEDGER anchor backend")

                elif backend == AnchorBackend.SOLANA:
                    from ..blockchain.solana.solana_client import SolanaClient

                    self._backends[backend] = SolanaClient(
                        config={
                            "rpc_url": "https://api.devnet.solana.com",
                            "commitment": "confirmed",
                            "live": self.config.live,
                        }
                    )
                    logger.info(f"[{CONSTITUTIONAL_HASH}] Initialized SOLANA anchor backend")

                # Initialize circuit breaker for this backend
                if CIRCUIT_BREAKER_AVAILABLE:
                    cb_config = CircuitBreakerConfig(
                        fail_max=self.config.circuit_breaker_fail_max,
                        reset_timeout=self.config.circuit_breaker_reset_timeout,
                    )
                    self._circuit_breakers[backend] = get_circuit_breaker(
                        f"blockchain_{backend.value}", cb_config
                    )

            except ImportError as e:
                logger.warning(
                    f"[{CONSTITUTIONAL_HASH}] Failed to initialize {backend.value} backend: {e}"
                )
            except Exception as e:
                logger.error(
                    f"[{CONSTITUTIONAL_HASH}] Error initializing {backend.value} backend: {e}"
                )

    def get_backend(self, backend: AnchorBackend) -> Optional[Any]:
        """
        Get a specific blockchain backend client.

        Args:
            backend: The backend to retrieve

        Returns:
            The backend client or None if not found/enabled
        """
        return self._backends.get(backend)

    async def start(self):
        """Start the anchor manager and background workers."""
        if self._running:
            return

        self._running = True

        # Connect async backends
        for backend, client in self._backends.items():
            if hasattr(client, "connect") and asyncio.iscoroutinefunction(client.connect):
                try:
                    await client.connect()
                except Exception as e:
                    logger.warning(
                        f"[{CONSTITUTIONAL_HASH}] Failed to connect {backend.value}: {e}"
                    )

        # Start worker tasks
        for i in range(self.config.worker_count):
            worker = asyncio.create_task(self._worker_loop(worker_id=i))
            self._workers.append(worker)

        logger.info(
            f"[{CONSTITUTIONAL_HASH}] BlockchainAnchorManager started with "
            f"{len(self._backends)} backends and {self.config.worker_count} workers"
        )

    async def stop(self):
        """Stop the anchor manager and cleanup."""
        self._running = False

        # Wait for queue to drain
        if not self._queue.empty():
            try:
                await asyncio.wait_for(self._queue.join(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning(f"[{CONSTITUTIONAL_HASH}] Queue drain timeout, forcing stop")

        # Cancel workers
        for worker in self._workers:
            worker.cancel()
            try:
                await worker
            except asyncio.CancelledError:
                pass

        self._workers.clear()

        # Disconnect async backends
        for backend, client in self._backends.items():
            if hasattr(client, "disconnect"):
                try:
                    if asyncio.iscoroutinefunction(client.disconnect):
                        await client.disconnect()
                    else:
                        client.disconnect()
                except Exception as e:
                    logger.warning(
                        f"[{CONSTITUTIONAL_HASH}] Error disconnecting {backend.value}: {e}"
                    )

        logger.info(f"[{CONSTITUTIONAL_HASH}] BlockchainAnchorManager stopped")

    async def anchor_root(
        self,
        root_hash: str,
        batch_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        callback: Optional[Callable[[AnchorResult], None]] = None,
    ) -> bool:
        """
        Submit a Merkle root for blockchain anchoring (fire-and-forget).

        Args:
            root_hash: The Merkle root hash to anchor
            batch_id: Batch identifier
            metadata: Optional metadata to include
            callback: Optional callback when anchoring completes

        Returns:
            bool: True if queued successfully, False if queue is full
        """
        if not self._running:
            logger.warning(f"[{CONSTITUTIONAL_HASH}] Anchor manager not running")
            return False

        pending = PendingAnchor(
            root_hash=root_hash,
            batch_id=batch_id,
            metadata=metadata or {},
            timestamp=time.time(),
            callbacks=[callback] if callback else [],
        )

        try:
            self._queue.put_nowait(pending)
            return True
        except asyncio.QueueFull:
            logger.warning(
                f"[{CONSTITUTIONAL_HASH}] Anchor queue full, dropping request for {batch_id}"
            )
            return False

    async def anchor_root_sync(
        self,
        root_hash: str,
        batch_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AnchorResult:
        """
        Submit a Merkle root and wait for result (synchronous).

        Args:
            root_hash: The Merkle root hash to anchor
            batch_id: Batch identifier
            metadata: Optional metadata to include

        Returns:
            AnchorResult: Result of anchoring operation
        """
        return await self._execute_anchor(
            root_hash=root_hash,
            batch_id=batch_id,
            metadata=metadata or {},
        )

    async def _worker_loop(self, worker_id: int):
        """Background worker for processing anchor requests."""

        while self._running:
            try:
                pending = await asyncio.wait_for(self._queue.get(), timeout=1.0)

                result = await self._execute_anchor(
                    root_hash=pending.root_hash,
                    batch_id=pending.batch_id,
                    metadata=pending.metadata,
                )

                # Execute callbacks
                for callback in pending.callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(result)
                        else:
                            callback(result)
                    except Exception as e:
                        logger.warning(f"[{CONSTITUTIONAL_HASH}] Callback error: {e}")

                self._queue.task_done()

            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[{CONSTITUTIONAL_HASH}] Worker {worker_id} error: {e}")

    async def _execute_anchor(
        self,
        root_hash: str,
        batch_id: str,
        metadata: Dict[str, Any],
    ) -> AnchorResult:
        """Execute anchoring with failover support."""
        start_time = time.time()
        self._stats["total_anchored"] += 1
        backends_to_try = list(self.config.enabled_backends)
        failover_count = 0

        for backend in backends_to_try:
            if backend not in self._backends:
                continue

            # Check circuit breaker
            if CIRCUIT_BREAKER_AVAILABLE and backend in self._circuit_breakers:
                cb = self._circuit_breakers[backend]
                # pybreaker uses state property
                if hasattr(cb, "current_state") and cb.current_state == "open":
                    logger.debug(
                        f"[{CONSTITUTIONAL_HASH}] Circuit open for {backend.value}, skipping"
                    )
                    continue

            try:
                result = await self._anchor_to_backend(
                    backend=backend,
                    root_hash=root_hash,
                    batch_id=batch_id,
                    metadata=metadata,
                )
                result.start_time = start_time

                if (
                    result.status == AnchorStatus.CONFIRMED
                    or result.status == AnchorStatus.SUBMITTED
                ):
                    self._stats["successful"] += 1
                    self._stats["by_backend"][backend.value] += 1
                    if failover_count > 0:
                        self._stats["failovers"] += 1
                    self._store_result(result)
                    return result

            except Exception as e:
                logger.warning(f"[{CONSTITUTIONAL_HASH}] Anchor to {backend.value} failed: {e}")
                failover_count += 1

                if not self.config.enable_failover:
                    break

                if failover_count >= self.config.max_failover_attempts:
                    break

        # All backends failed
        self._stats["failed"] += 1
        failed_result = AnchorResult(
            backend=backends_to_try[0] if backends_to_try else AnchorBackend.LOCAL,
            status=AnchorStatus.FAILED,
            batch_id=batch_id,
            start_time=start_time,
            error="All backends failed",
        )
        self._store_result(failed_result)
        return failed_result

    async def _anchor_to_backend(
        self,
        backend: AnchorBackend,
        root_hash: str,
        batch_id: str,
        metadata: Dict[str, Any],
    ) -> AnchorResult:
        """Anchor to a specific backend."""
        client = self._backends[backend]

        if backend == AnchorBackend.LOCAL:
            # LocalFileSystemAnchor is synchronous
            block = client.anchor_root(root_hash)
            return AnchorResult(
                backend=backend,
                status=AnchorStatus.CONFIRMED,
                batch_id=batch_id,
                transaction_id=block.get("hash"),
                block_info=block,
            )

        elif backend == AnchorBackend.ETHEREUM_L2:
            batch_data = {
                "batch_id": batch_id,
                "root_hash": root_hash,
                "entry_count": metadata.get("entry_count", 0),
                "timestamp": int(time.time()),
                "entries_hashes": metadata.get("entries_hashes", []),
            }
            tx_hash = await client.submit_audit_batch(batch_data)
            if tx_hash:
                return AnchorResult(
                    backend=backend,
                    status=AnchorStatus.SUBMITTED,
                    batch_id=batch_id,
                    transaction_id=tx_hash,
                    block_info={"network": self.config.ethereum_network},
                )
            raise Exception("Transaction submission failed")

        elif backend == AnchorBackend.ARWEAVE:
            tx_id = client.store_batch_hash(batch_id, root_hash, metadata)
            if tx_id:
                return AnchorResult(
                    backend=backend,
                    status=AnchorStatus.SUBMITTED,
                    batch_id=batch_id,
                    transaction_id=tx_id,
                )
            raise Exception("Arweave storage failed")

        elif backend == AnchorBackend.HYPERLEDGER:
            # Implement Hyperledger anchoring
            raise NotImplementedError("Hyperledger anchoring not implemented")

        elif backend == AnchorBackend.SOLANA:
            tx_hash = await client.submit_audit_batch(
                {
                    "batch_id": batch_id,
                    "root_hash": root_hash,
                    "entry_count": metadata.get("entry_count", 0),
                    "timestamp": int(time.time()),
                    "entries_hashes": metadata.get("entries_hashes", []),
                }
            )
            if tx_hash:
                return AnchorResult(
                    backend=backend,
                    status=AnchorStatus.SUBMITTED,
                    batch_id=batch_id,
                    transaction_id=tx_hash,
                )
            raise Exception("Solana transaction submission failed")

        raise ValueError(f"Unknown backend: {backend}")

    def _store_result(self, result: AnchorResult):
        """Store recent result for status reporting."""
        self._recent_results.append(result)
        if len(self._recent_results) > self._max_recent_results:
            self._recent_results = self._recent_results[-self._max_recent_results :]

    def get_stats(self) -> Dict[str, Any]:
        """Get anchor manager statistics."""
        return {
            **self._stats,
            "queue_size": self._queue.qsize(),
            "running": self._running,
            "enabled_backends": [b.value for b in self.config.enabled_backends],
            "initialized_backends": [b.value for b in self._backends.keys()],
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

    def get_recent_results(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get recent anchor results."""
        return [r.to_dict() for r in self._recent_results[-n:]]

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all backends."""
        health = {
            "overall": "healthy",
            "backends": {},
            "constitutional_hash": CONSTITUTIONAL_HASH,
        }

        unhealthy_count = 0
        for backend, client in self._backends.items():
            backend_health = {"status": "unknown", "connected": False}

            try:
                if hasattr(client, "is_connected"):
                    backend_health["connected"] = client.is_connected()
                elif hasattr(client, "connected"):
                    backend_health["connected"] = client.connected

                if hasattr(client, "get_network_stats"):
                    if asyncio.iscoroutinefunction(client.get_network_stats):
                        stats = await client.get_network_stats()
                    else:
                        stats = client.get_network_stats()
                    backend_health["stats"] = stats

                # Check circuit breaker status
                if CIRCUIT_BREAKER_AVAILABLE and backend in self._circuit_breakers:
                    cb = self._circuit_breakers[backend]
                    if hasattr(cb, "current_state"):
                        backend_health["circuit_state"] = cb.current_state

                backend_health["status"] = "healthy" if backend_health["connected"] else "degraded"

            except Exception as e:
                backend_health["status"] = "unhealthy"
                backend_health["error"] = str(e)
                unhealthy_count += 1

            health["backends"][backend.value] = backend_health

        if unhealthy_count == len(self._backends):
            health["overall"] = "unhealthy"
        elif unhealthy_count > 0:
            health["overall"] = "degraded"

        return health


# Module-level convenience functions
_anchor_manager: Optional[BlockchainAnchorManager] = None


def get_anchor_manager(
    config: Optional[AnchorManagerConfig] = None,
) -> BlockchainAnchorManager:
    """Get or create the global anchor manager."""
    global _anchor_manager
    if _anchor_manager is None:
        _anchor_manager = BlockchainAnchorManager(config)
    return _anchor_manager


async def initialize_anchor_manager(
    config: Optional[AnchorManagerConfig] = None,
) -> BlockchainAnchorManager:
    """Initialize and start the global anchor manager."""
    manager = get_anchor_manager(config)
    await manager.start()
    return manager


async def close_anchor_manager():
    """Stop and cleanup the global anchor manager."""
    global _anchor_manager
    if _anchor_manager:
        await _anchor_manager.stop()
        _anchor_manager = None


def reset_anchor_manager() -> None:
    """Reset the global anchor manager instance without async cleanup.

    Used primarily for test isolation to prevent state leakage between tests.
    For graceful shutdown, use close_anchor_manager() instead.
    Constitutional Hash: cdd01ef066bc6cf2
    """
    global _anchor_manager
    if _anchor_manager is not None:
        # Set running to False to prevent worker loops from continuing
        _anchor_manager._running = False
        # Cancel all worker tasks
        for worker in _anchor_manager._workers:
            if not worker.done():
                worker.cancel()
        _anchor_manager._workers.clear()
        # Clear the queue
        while not _anchor_manager._queue.empty():
            try:
                _anchor_manager._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    _anchor_manager = None


__all__ = [
    "AnchorBackend",
    "AnchorStatus",
    "AnchorResult",
    "AnchorManagerConfig",
    "PendingAnchor",
    "BlockchainAnchorManager",
    "get_anchor_manager",
    "initialize_anchor_manager",
    "close_anchor_manager",
    "reset_anchor_manager",
    "CIRCUIT_BREAKER_AVAILABLE",
]
