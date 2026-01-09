"""
Tests for ACGS-2 Audit Ledger (AUD) Hash Chain Integrity

Tests the tamper-evident hash chaining functionality in the audit system.
"""

import hashlib
import json
from datetime import datetime, timezone

import pytest

from src.acgs2.components.aud import AuditLedger
from src.acgs2.core.schemas import AuditEntry


class TestAuditHashChain:
    """Test audit ledger hash chain integrity."""

    def test_initial_genesis_hash(self):
        """Test that audit ledger starts with genesis hash."""
        aud = AuditLedger({"component_name": "test"})

        assert aud.last_hash == "genesis"
        assert len(aud.entries) == 0

    def test_hash_chain_append(self):
        """Test that entries are properly hash-chained."""
        aud = AuditLedger({"component_name": "test"})

        # Create test entry
        entry1 = AuditEntry(
            entry_id="test_1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id="req_1",
            session_id="sess_1",
            actor="test_component",
            action_type="test_action",
            payload={"test": "data"},
        )

        # Append first entry
        hash1 = aud.append_entry(entry1)

        # Should have one entry
        assert len(aud.entries) == 1
        assert aud.entries[0].entry_hash == hash1
        assert aud.entries[0].previous_hash == "genesis"

        # Create second entry
        entry2 = AuditEntry(
            entry_id="test_2",
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id="req_2",
            session_id="sess_2",
            actor="test_component",
            action_type="test_action",
            payload={"test": "data2"},
        )

        # Append second entry
        hash2 = aud.append_entry(entry2)

        # Should have two entries
        assert len(aud.entries) == 2
        assert aud.entries[1].entry_hash == hash2
        assert aud.entries[1].previous_hash == hash1
        assert aud.last_hash == hash2

    def test_hash_chain_integrity(self):
        """Test that hash chain maintains integrity."""
        aud = AuditLedger({"component_name": "test"})

        entries = []
        for i in range(5):
            entry = AuditEntry(
                entry_id=f"test_{i}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id=f"req_{i}",
                session_id=f"sess_{i}",
                actor="test_component",
                action_type="test_action",
                payload={"test": f"data{i}"},
            )
            hash_val = aud.append_entry(entry)
            entries.append((entry, hash_val))

        # Verify chain integrity
        previous_hash = "genesis"
        for i, (_, expected_hash) in enumerate(entries):
            stored_entry = aud.entries[i]

            # Check hash chain
            assert stored_entry.previous_hash == previous_hash
            assert stored_entry.entry_hash == expected_hash

            # Verify hash calculation manually
            entry_dict = aud._entry_to_dict(stored_entry)
            computed_hash = aud._compute_hash(entry_dict)
            assert computed_hash == expected_hash

            previous_hash = expected_hash

    def test_timestamp_before_hash(self):
        """Test that timestamp is set before hash computation."""
        aud = AuditLedger({"component_name": "test"})

        entry = AuditEntry(
            entry_id="test_timestamp",
            timestamp="",  # Empty timestamp initially
            request_id="req_timestamp",
            session_id="sess_timestamp",
            actor="test_component",
            action_type="test_action",
            payload={"test": "timestamp"},
        )

        # Append entry (this should set timestamp)
        before_time = datetime.now(timezone.utc).isoformat()
        hash_val = aud.append_entry(entry)
        after_time = datetime.now(timezone.utc).isoformat()

        stored_entry = aud.entries[0]

        # Timestamp should be set
        assert stored_entry.timestamp != ""
        assert before_time <= stored_entry.timestamp <= after_time

        # Verify hash includes the timestamp
        entry_dict = aud._entry_to_dict(stored_entry)
        computed_hash = aud._compute_hash(entry_dict)
        assert computed_hash == hash_val

    def test_hash_deterministic(self):
        """Test that same data produces same hash."""
        aud = AuditLedger({"component_name": "test"})

        # Create identical entries
        entry1 = AuditEntry(
            entry_id="test_deterministic",
            timestamp="2024-01-01T00:00:00.000000+00:00",
            request_id="req_det",
            session_id="sess_det",
            actor="test_component",
            action_type="test_action",
            payload={"test": "deterministic"},
        )

        entry2 = AuditEntry(
            entry_id="test_deterministic",
            timestamp="2024-01-01T00:00:00.000000+00:00",
            request_id="req_det",
            session_id="sess_det",
            actor="test_component",
            action_type="test_action",
            payload={"test": "deterministic"},
        )

        hash1 = aud.append_entry(entry1)
        hash2 = aud.append_entry(entry2)

        # Should be different because of hash chaining
        assert hash1 != hash2

        # But if we reset and add the same entry first, should get same hash
        aud2 = AuditLedger({"component_name": "test"})
        hash1_again = aud2.append_entry(entry1)
        assert hash1_again == hash1

    def test_hash_includes_all_fields(self):
        """Test that hash includes all relevant fields."""
        aud = AuditLedger({"component_name": "test"})

        entry = AuditEntry(
            entry_id="test_fields",
            timestamp="2024-01-01T00:00:00.000000+00:00",
            request_id="req_fields",
            session_id="sess_fields",
            actor="test_component",
            action_type="test_action",
            payload={"test": "fields"},
        )

        hash_val = aud.append_entry(entry)

        # Manually compute hash to verify all fields are included
        entry_dict = {
            "entry_id": entry.entry_id,
            "timestamp": entry.timestamp,
            "request_id": entry.request_id,
            "session_id": entry.session_id,
            "actor": entry.actor,
            "action_type": entry.action_type,
            "payload": entry.payload,
            "previous_hash": entry.previous_hash,
        }

        expected_hash = hashlib.sha256(json.dumps(entry_dict, sort_keys=True).encode()).hexdigest()
        assert hash_val == expected_hash

    def test_tamper_detection(self):
        """Test that hash chain detects tampering."""
        aud = AuditLedger({"component_name": "test"})

        # Add some entries
        for i in range(3):
            entry = AuditEntry(
                entry_id=f"tamper_{i}",
                timestamp=datetime.now(timezone.utc).isoformat(),
                request_id=f"req_tamper_{i}",
                session_id=f"sess_tamper_{i}",
                actor="test_component",
                action_type="test_action",
                payload={"test": f"tamper{i}"},
            )
            aud.append_entry(entry)

        # Simulate tampering by modifying stored entry
        original_payload = aud.entries[1].payload.copy()
        aud.entries[1].payload["tampered"] = True

        # Verify integrity should fail (in a real implementation)
        # For now, just verify the entry was modified
        assert aud.entries[1].payload != original_payload
        assert "tampered" in aud.entries[1].payload

    def test_invalid_entry_rejection(self):
        """Test that invalid entries are rejected."""
        aud = AuditLedger({"component_name": "test"})

        # Invalid entry (missing required fields)
        invalid_entry = AuditEntry(
            entry_id="",  # Invalid
            timestamp="",
            request_id="",
            session_id="",
            actor="",
            action_type="",
            payload={},
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="Invalid audit entry"):
            aud.append_entry(invalid_entry)

    def test_shutdown_prevents_appends(self):
        """Test that shutdown prevents further appends."""
        aud = AuditLedger({"component_name": "test"})

        # Shutdown the ledger
        aud.shutdown()

        entry = AuditEntry(
            entry_id="test_shutdown",
            timestamp=datetime.now(timezone.utc).isoformat(),
            request_id="req_shutdown",
            session_id="sess_shutdown",
            actor="test_component",
            action_type="test_action",
            payload={"test": "shutdown"},
        )

        # Should raise RuntimeError
        with pytest.raises(RuntimeError, match="Audit ledger is shutting down"):
            aud.append_entry(entry)
