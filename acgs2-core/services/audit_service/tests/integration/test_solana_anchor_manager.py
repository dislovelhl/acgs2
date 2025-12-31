import asyncio
import logging
from services.audit_service.core.blockchain_anchor_manager import (
    BlockchainAnchorManager,
    AnchorManagerConfig,
    AnchorBackend,
    AnchorStatus
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_solana_integration():
    # 1. Configure manager with Solana enabled
    config = AnchorManagerConfig(
        enabled_backends=[AnchorBackend.SOLANA],
        queue_size=10,
        worker_count=1,
        live=False
    )

    manager = BlockchainAnchorManager(config)

    # 2. Start the manager
    logger.info("Starting BlockchainAnchorManager...")
    await manager.start()

    # 3. Verify backend initialization
    stats = manager.get_stats()
    logger.info(f"Stats: {stats}")
    assert "solana" in stats["initialized_backends"]

    # 4. Perform a synchronous anchor operation
    logger.info("Anchoring root hash to Solana...")
    try:
        result = await asyncio.wait_for(
            manager.anchor_root_sync(
                root_hash="integration_test_root_solana",
                batch_id="batch_sol_001",
                metadata={"entry_count": 10}
            ),
            timeout=30.0  # 30 second timeout for devnet
        )
    except asyncio.TimeoutError:
        logger.error("Timed out waiting for Solana anchor in integration test")
        await manager.stop()
        raise

    logger.info(f"Anchor Result: {result.to_dict()}")
    assert result.status == AnchorStatus.SUBMITTED
    assert result.backend == AnchorBackend.SOLANA
    # Real signature is a base58 string, no longer "sol_sig_"
    assert len(result.transaction_id) >= 32

    # 5. Stop the manager
    logger.info("Stopping manager...")
    await manager.stop()
    logger.info("Integration test PASSED")

if __name__ == "__main__":
    asyncio.run(test_solana_integration())
