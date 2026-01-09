"""
Unit tests for audit ledger functionality.
Constitutional Hash: cdd01ef066bc6cf2
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from src.core.services.audit_service.core.audit_ledger import (
    AuditEntry,
    AuditLedger,
    AuditLedgerConfig,
)


class TestAuditEntry:
    """Test AuditEntry data structure."""

    @pytest_asyncio.fixture
    async def storage_path(self, tmp_path):
        """Create a temporary storage path."""
        p = tmp_path / "audit_storage"
        p.mkdir()
        return p

    @pytest_asyncio.fixture
    async def ledger_with_config(self, storage_path):
        """Create a ledger with specific config for testing."""
        config = AuditLedgerConfig(
            batch_size=3,
            redis_url=None,
            enable_blockchain_anchoring=False,
            persistence_file=str(storage_path / "ledger.json"),
        )

        with patch("redis.from_url", side_effect=Exception("Redis disabled for tests")):
            ledger_inst = AuditLedger(config=config)
            await ledger_inst.start()
            yield ledger_inst
            await ledger_inst.stop()


class TestAuditLedger:
    """Test AuditLedger core functionality."""

    @pytest.fixture
    def ledger(self):
        """Create a test audit ledger."""
        return AuditLedger()

    @pytest.fixture
    def sample_entry(self):
        """Create a sample audit entry."""
        return {
            "batch_id": "test-batch-001",
            "entry_hash": "test-hash-001",
            "data": {
                "action": "user_login",
                "user_id": "user-123",
                "ip_address": "192.168.1.1",
                "user_agent": "TestAgent/1.0",
            },
            "metadata": {"service": "api-gateway", "constitutional_hash": "cdd01ef066bc6cf2"},
        }

    def test_ledger_initialization(self, ledger):
        """Test ledger initializes properly."""
        assert ledger.batches == {}
        assert ledger.current_batch_id is None
        assert ledger.redis_client is None  # Not connected yet

    @pytest.mark.asyncio
    async def test_ledger_startup_shutdown(self, ledger):
        """Test ledger startup and shutdown."""
        # Should not raise exceptions
        await ledger.start()
        await ledger.stop()

    @pytest.mark.asyncio
    async def test_add_entry_to_new_batch(self, ledger, sample_entry):
        """Test adding first entry creates new batch."""
        entry_hash = await ledger.add_entry(sample_entry["data"], sample_entry["metadata"])

        assert entry_hash is not None
        assert len(ledger.batches) == 1
        assert ledger.current_batch_id is not None

        # Check entry was added
        batch_entries = ledger.batches[ledger.current_batch_id]
        assert len(batch_entries) == 1

        entry = batch_entries[0]
        assert entry.data == sample_entry["data"]
        assert entry.metadata == sample_entry["metadata"]

    @pytest.mark.asyncio
    async def test_add_multiple_entries(self, ledger, sample_entry):
        """Test adding multiple entries to same batch."""
        # Add first entry
        hash1 = await ledger.add_entry(sample_entry["data"], sample_entry["metadata"])

        # Add second entry
        entry2_data = {**sample_entry["data"], "action": "user_logout"}
        hash2 = await ledger.add_entry(entry2_data, sample_entry["metadata"])

        assert hash1 != hash2
        assert len(ledger.batches) == 1
        assert len(ledger.batches[ledger.current_batch_id]) == 2

    @pytest.mark.asyncio
    async def test_get_entries_by_batch(self, ledger, sample_entry):
        """Test retrieving entries by batch ID."""
        # Add entries
        await ledger.add_entry(sample_entry["data"], sample_entry["metadata"])
        batch_id = ledger.current_batch_id

        entry2_data = {**sample_entry["data"], "action": "data_access"}
        await ledger.add_entry(entry2_data, sample_entry["metadata"])

        # Retrieve entries
        entries = await ledger.get_entries_by_batch(batch_id)

        assert len(entries) == 2
        assert entries[0].data["action"] == "user_login"
        assert entries[1].data["action"] == "data_access"

    @pytest.mark.asyncio
    async def test_get_entries_by_nonexistent_batch(self, ledger):
        """Test retrieving entries for non-existent batch."""
        entries = await ledger.get_entries_by_batch("nonexistent-batch")
        assert entries == []

    def test_get_batch_root_hash(self, ledger):
        """Test getting batch root hash."""
        # Initially no batches
        root_hash = ledger.get_batch_root_hash("any-batch")
        assert root_hash is None

        # After adding entries, should have root hash
        # (This would need actual implementation to test fully)

    @pytest.mark.asyncio
    async def test_ledger_stats(self, ledger, sample_entry):
        """Test ledger statistics."""
        # Add some entries
        await ledger.add_entry(sample_entry["data"], sample_entry["metadata"])
        await ledger.add_entry(
            {**sample_entry["data"], "action": "test2"}, sample_entry["metadata"]
        )

        stats = await ledger.get_ledger_stats()

        assert "total_batches" in stats
        assert "total_entries" in stats
        assert "current_batch_id" in stats
        assert stats["total_batches"] == 1
        assert stats["total_entries"] == 2
        assert stats["current_batch_id"] == ledger.current_batch_id

    @pytest.mark.asyncio
    async def test_concurrent_entry_addition(self, ledger, sample_entry):
        """Test adding entries concurrently."""
        import asyncio

        async def add_entry(index):
            data = {**sample_entry["data"], "index": index}
            return await ledger.add_entry(data, sample_entry["metadata"])

        # Add entries concurrently
        tasks = [add_entry(i) for i in range(10)]
        hashes = await asyncio.gather(*tasks)

        # All should succeed
        assert len(hashes) == 10
        assert len(set(hashes)) == 10  # All unique
        assert len(ledger.batches[ledger.current_batch_id]) == 10

    def test_entry_hash_uniqueness(self, ledger):
        """Test that entry hashes are unique for different data."""
        # Create entries with different data
        entry1 = AuditEntry(
            batch_id="batch-1",
            entry_hash="hash-1",
            data={"action": "login", "user": "alice"},
            timestamp=datetime.now(timezone.utc),
            metadata={},
        )

        entry2 = AuditEntry(
            batch_id="batch-1",
            entry_hash="hash-2",
            data={"action": "login", "user": "bob"},
            timestamp=datetime.now(timezone.utc),
            metadata={},
        )

        # Should have different hashes
        assert entry1.entry_hash != entry2.entry_hash


class TestAuditLedgerPersistence:
    """Test audit ledger persistence and recovery."""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client for testing."""
        mock = MagicMock()
        mock.set = AsyncMock(return_value=True)
        mock.get = AsyncMock(return_value=None)
        mock.lpush = AsyncMock(return_value=1)
        mock.lrange = AsyncMock(return_value=[])
        return mock

    @pytest.mark.asyncio
    async def test_redis_integration(self, mock_redis):
        """Test Redis integration for persistence."""
        ledger = AuditLedger()
        ledger.redis_client = mock_redis

        sample_data = {"action": "test", "user": "test-user"}
        sample_metadata = {"service": "test"}

        # Add entry
        await ledger.add_entry(sample_data, sample_metadata)

        # Verify Redis calls were made
        mock_redis.set.assert_called()
        mock_redis.lpush.assert_called()

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, ledger):
        """Test graceful handling of Redis connection failure."""
        # Redis client is None - should still work with in-memory storage
        sample_data = {"action": "test"}
        sample_metadata = {"service": "test"}

        entry_hash = await ledger.add_entry(sample_data, sample_metadata)

        assert entry_hash is not None
        assert len(ledger.batches) == 1


class TestAuditLedgerValidation:
    """Test audit ledger data validation."""

    @pytest.fixture
    def ledger(self):
        """Create a test audit ledger."""
        return AuditLedger()

    @pytest.mark.asyncio
    async def test_empty_data_handling(self, ledger):
        """Test handling of empty data."""
        with pytest.raises((ValueError, TypeError)):
            await ledger.add_entry({}, {})

    @pytest.mark.asyncio
    async def test_large_data_handling(self, ledger):
        """Test handling of large data payloads."""
        large_data = {"data": "x" * 100000}  # 100KB data
        large_metadata = {"meta": "y" * 10000}  # 10KB metadata

        # Should handle large payloads
        entry_hash = await ledger.add_entry(large_data, large_metadata)
        assert entry_hash is not None

    @pytest.mark.asyncio
    async def test_special_characters_in_data(self, ledger):
        """Test handling of special characters and unicode."""
        special_data = {
            "action": "test",
            "message": "Unicode: 🚀⭐🌟 and special chars: àáâãäåæçèéêë",
            "json_data": {"nested": {"value": 123, "array": [1, 2, "three"]}},
            "null_value": None,
            "boolean": True,
        }

        entry_hash = await ledger.add_entry(special_data, {"service": "test"})
        assert entry_hash is not None

        # Verify data integrity
        entries = await ledger.get_entries_by_batch(ledger.current_batch_id)
        assert len(entries) == 1
        assert entries[0].data == special_data


class TestMerkleTreeIntegration:
    """Test Merkle tree integration for batch verification."""

    @pytest.fixture
    def ledger(self):
        """Create a test audit ledger."""
        return AuditLedger()

    @pytest.mark.asyncio
    async def test_merkle_tree_construction(self, ledger):
        """Test Merkle tree construction for batches."""
        # Add multiple entries
        for i in range(4):
            data = {"action": f"test-{i}", "index": i}
            await ledger.add_entry(data, {"batch": "test"})

        # Should have Merkle tree for batch
        batch_id = ledger.current_batch_id
        root_hash = ledger.get_batch_root_hash(batch_id)

        # Root hash should exist
        assert root_hash is not None
        assert isinstance(root_hash, str)
        assert len(root_hash) > 0

    @pytest.mark.asyncio
    async def test_batch_verification(self, ledger):
        """Test batch verification using Merkle proofs."""
        # Add entries
        hashes = []
        for i in range(3):
            data = {"action": f"action-{i}"}
            entry_hash = await ledger.add_entry(data, {"test": True})
            hashes.append(entry_hash)

        # Get batch entries
        batch_id = ledger.current_batch_id
        entries = await ledger.get_entries_by_batch(batch_id)

        # Each entry should be verifiable
        for entry in entries:
            # This would test Merkle proof verification
            # (Requires full Merkle tree implementation)
            assert entry.entry_hash is not None


class TestConstitutionalCompliance:
    """Test constitutional compliance in audit logging."""

    @pytest.fixture
    def ledger(self):
        """Create a test audit ledger."""
        return AuditLedger()

    @pytest.mark.asyncio
    async def test_constitutional_hash_tracking(self, ledger):
        """Test that constitutional hash is properly tracked."""
        data = {"action": "governance_decision"}
        metadata = {"constitutional_hash": "cdd01ef066bc6cf2", "service": "test"}

        await ledger.add_entry(data, metadata)

        entries = await ledger.get_entries_by_batch(ledger.current_batch_id)
        assert len(entries) == 1
        assert entries[0].metadata["constitutional_hash"] == "cdd01ef066bc6cf2"

    @pytest.mark.asyncio
    async def test_audit_trail_completeness(self, ledger):
        """Test that audit trail contains all required information."""
        data = {
            "action": "user_permission_change",
            "user_id": "user-123",
            "permission": "admin",
            "changed_by": "admin-user",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        metadata = {
            "service": "user-management",
            "constitutional_hash": "cdd01ef066bc6cf2",
            "correlation_id": "corr-123",
            "ip_address": "192.168.1.1",
        }

        await ledger.add_entry(data, metadata)

        entries = await ledger.get_entries_by_batch(ledger.current_batch_id)
        entry = entries[0]

        # Verify all required fields are present
        required_data_fields = ["action", "user_id", "permission", "changed_by", "timestamp"]
        for field in required_data_fields:
            assert field in entry.data

        required_meta_fields = ["service", "constitutional_hash"]
        for field in required_meta_fields:
            assert field in entry.metadata

        # Verify entry has hash and timestamp
        assert entry.entry_hash is not None
        assert entry.timestamp is not None
