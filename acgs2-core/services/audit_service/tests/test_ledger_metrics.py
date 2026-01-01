import asyncio
import time
from services.audit_service.core.audit_ledger import AuditLedger, AuditLedgerConfig
from services.audit_service.core.blockchain_anchor_manager import (
import logging
    AnchorBackend,
    AnchorResult,
    AnchorStatus,
)
from shared.constants import CONSTITUTIONAL_HASH


async def test_ledger_metrics():
    logging.info("\n--- Testing AuditLedger Metrics ---")
    config = AuditLedgerConfig(
        enable_blockchain_anchoring=True, blockchain_backends=["local"], batch_size=2
    )
    ledger = AuditLedger(config=config)
    await ledger.start()

    # Simulate an anchor completion
    result = AnchorResult(
        backend=AnchorBackend.LOCAL,
        status=AnchorStatus.CONFIRMED,
        batch_id="batch_1",
        transaction_id="tx_123",
        start_time=time.time() - 0.5,  # 500ms latency
        timestamp=time.time(),
    )

    # Inject result via callback
    ledger._on_anchor_complete(result)

    stats = ledger.get_anchor_stats()
    logging.info(f"Stats: {stats}")

    if stats["successful"] == 1 and stats["avg_latency_sec"] > 0.4:
        logging.info("PASS: Ledger metrics correctly updated and reported latency")
    else:
        logging.info("FAIL: Ledger metrics NOT correctly updated")

    await ledger.stop()


if __name__ == "__main__":
    asyncio.run(test_ledger_metrics())
