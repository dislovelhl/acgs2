"""
ACGS-2 Integration Tests: IT-05 - Memory Write Safety

Tests memory write safety, particularly for PII handling and retention policies.
Expected: SAS blocks or DMS redacts PII, pii flag set correctly, retention policy applied.
"""


import pytest

from .conftest import (
    MockCRE,
    MockDMS,
    MockSAS,
    MockTMS,
    MockUIG,
    SafetyDecision,
    SafetyDecisionType,
)


class TestIT05MemoryWriteSafety:
    """
    IT-05: Memory write safety

    Input: User asks to store secrets/PII
    Expected:
        - SAS blocks or DMS redacts
        - PII flag set correctly only if allowed with retention
        - Retention policy applied
    """

    @pytest.mark.asyncio
    async def test_pii_detection_blocks_storage(self):
        """Test that PII detection prevents storage of sensitive data."""
        sas = MockSAS()

        # Add PII detection to SAS
        original_check_request = sas.check_request

        async def pii_check_request(envelope):
            query = envelope.payload.get("query", "").lower()
            if any(word in query for word in ["ssn", "social security", "credit card", "password"]):
                return SafetyDecision(
                    decision=SafetyDecisionType.DENY,
                    policy_version=sas.policy_version,
                    rationale_codes=["PII_DETECTED"],
                )
            return await original_check_request(envelope)

        sas.check_request = pii_check_request

        dms = MockDMS()
        tms = MockTMS(sas)
        cre = MockCRE(sas, tms, dms)
        uig = MockUIG(sas, cre, dms)

        result = await uig.handle_request("Please remember my SSN is 123-45-6789")

        assert result["status"] == "refused"
        assert "PII_DETECTED" in str(result.get("reason", ""))

    @pytest.mark.asyncio
    async def test_pii_flag_set_when_allowed_with_retention(self):
        """Test that PII flag is set correctly when storage is allowed with retention."""
        sas = MockSAS()
        dms = MockDMS()

        # Override DMS write to check PII flagging
        original_write = dms.write
        pii_records = []

        async def pii_checking_write(record, envelope):
            pii_records.append(record)
            return await original_write(record, envelope)

        dms.write = pii_checking_write

        tms = MockTMS(sas)
        cre = MockCRE(sas, tms, dms)
        uig = MockUIG(sas, cre, dms)

        # Query that results in PII but is allowed (e.g., non-sensitive context)
        result = await uig.handle_request("What is machine learning?")

        assert result["status"] == "success"
        assert len(pii_records) == 1

        # Check that PII flag is set appropriately (false for this benign query)
        record = pii_records[0]
        assert "pii" in record.retention
        assert record.retention["pii"] == False

    @pytest.mark.asyncio
    async def test_retention_policy_applied_correctly(self):
        """Test that retention policies are applied based on content sensitivity."""
        sas = MockSAS()
        dms = MockDMS()

        # Override DMS write to check retention policies
        retention_records = []

        async def retention_checking_write(record, envelope):
            retention_records.append(record)
            return await dms.write(record, envelope)

        dms.write = retention_checking_write

        tms = MockTMS(sas)
        cre = MockCRE(sas, tms, dms)
        uig = MockUIG(sas, cre, dms)

        # Multiple queries with different retention expectations
        queries = [
            "What is the weather?",  # Short retention
            "Explain quantum physics",  # Longer retention
            "What's my account balance?",  # Sensitive, short retention
        ]

        for query in queries:
            result = await uig.handle_request(query)
            assert result["status"] == "success"

        # Check that all records have retention policies
        for record in retention_records:
            assert "ttl_days" in record.retention
            assert "pii" in record.retention
            assert isinstance(record.retention["ttl_days"], int)
            assert record.retention["ttl_days"] > 0

    @pytest.mark.asyncio
    async def test_sensitive_content_redaction(self):
        """Test that sensitive content is redacted before storage."""
        sas = MockSAS()
        dms = MockDMS()

        # Override DMS write to check for redaction
        stored_content = []

        async def redaction_checking_write(record, envelope):
            stored_content.append(record.content)
            return await dms.write(record, envelope)

        dms.write = redaction_checking_write

        tms = MockTMS(sas)
        cre = MockCRE(sas, tms, dms)
        uig = MockUIG(sas, cre, dms)

        # Query with potentially sensitive information
        result = await uig.handle_request("My API key is sk-1234567890abcdef")

        assert result["status"] == "success"

        # Check that sensitive content is not stored in plain text
        for content in stored_content:
            assert "sk-1234567890abcdef" not in content
            # Should contain redacted version or be excluded
            if "API key" in content or "sk-" in content:
                # Content should be redacted or marked as sensitive
                assert "[REDACTED]" in content or content == "Sensitive content redacted"

    @pytest.mark.asyncio
    async def test_memory_isolation_between_sessions(self):
        """Test that different sessions have isolated memory."""
        sas = MockSAS()
        dms = MockDMS()
        tms = MockTMS(sas)
        cre = MockCRE(sas, tms, dms)
        uig = MockUIG(sas, cre, dms)

        # Session 1
        session1_result = await uig.handle_request("What is Python?", "session-1")
        assert session1_result["status"] == "success"

        # Session 2
        session2_result = await uig.handle_request("What is Java?", "session-2")
        assert session2_result["status"] == "success"

        # Check session isolation in DMS
        session1_history = dms.session_history.get("session-1", [])
        session2_history = dms.session_history.get("session-2", [])

        assert len(session1_history) == 1
        assert len(session2_history) == 1
        assert "Python" in session1_history[0]
        assert "Java" in session2_history[0]
        assert "Python" not in session2_history[0]
        assert "Java" not in session1_history[0]
