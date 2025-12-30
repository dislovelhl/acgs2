import asyncio
import os

import pytest
from services.audit_service.core.audit_ledger import AuditLedger, ValidationResult


@pytest.mark.asyncio
async def test_audit_ledger_persistence():
    """Test that AuditLedger persists to and recovers from Redis/File."""
    persistence_file = "audit_ledger_storage.json"
    if os.path.exists(persistence_file):
        os.remove(persistence_file)

    # 1. Initialize ledger and add entries
    ledger1 = AuditLedger(batch_size=2)
    # Ensure it uses a fresh file if it falls back
    ledger1.persistence_file = persistence_file
    await ledger1.start()

    vr1 = ValidationResult(is_valid=True, metadata={"msg": "first"})
    vr2 = ValidationResult(is_valid=True, metadata={"msg": "second"})

    entry_hash1 = await ledger1.add_validation_result(vr1)
    entry_hash2 = await ledger1.add_validation_result(vr2)

    # Wait for background processing (queue empty + lock released)
    for _ in range(20):
        if ledger1._queue.empty() and len(ledger1.entries) >= 2:
            break
        await asyncio.sleep(0.1)

    # Check if batch was committed
    stats1 = await ledger1.get_ledger_stats()
    assert stats1["batches_committed"] >= 1
    assert stats1["total_entries"] == 2

    # Get proof for verification later
    entry1 = ledger1.entries[0]
    batch_id = entry1.batch_id
    root_hash = ledger1.get_batch_root_hash(batch_id)
    proof = entry1.merkle_proof

    # 2. Shutdown first ledger instance
    await ledger1.stop()

    # Verify file exists if no Redis
    if not ledger1.redis_client:
        assert os.path.exists(persistence_file)

    # 3. Initialize second ledger instance (simulated restart)
    ledger2 = AuditLedger(batch_size=2)
    ledger2.persistence_file = persistence_file
    await ledger2.start()

    # 4. Verify recovery
    stats2 = await ledger2.get_ledger_stats()
    assert stats2["total_entries"] == 2
    assert stats2["batches_committed"] == stats1["batches_committed"]

    # Check if entries match
    recovered_entry1 = ledger2.entries[0]
    assert recovered_entry1.hash == entry_hash1
    assert recovered_entry1.batch_id == batch_id

    # Verify Merkle linkage on recovered data
    # Note: verify_entry requires the root_hash
    is_valid = await ledger2.verify_entry(entry_hash1, proof, root_hash)
    assert is_valid is True

    await ledger2.stop()

    if os.path.exists(persistence_file):
        os.remove(persistence_file)


if __name__ == "__main__":
    asyncio.run(test_audit_ledger_persistence())
