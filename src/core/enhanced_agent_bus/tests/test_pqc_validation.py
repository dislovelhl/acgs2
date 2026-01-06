"""
Test PQC Validation Integration
================================

Tests for Post-Quantum Cryptographic validation in the Enhanced Agent Bus.

Constitutional Hash: cdd01ef066bc6cf2

Coverage:
- PQCValidationStrategy functionality
- CompositeValidationStrategy PQC integration
- AgentMessage PQC fields
- Performance benchmarks
- Hybrid mode fallback behavior
"""

import asyncio
import base64
import hashlib
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure proper module path resolution for isolated testing
_current_dir = os.path.dirname(os.path.abspath(__file__))
_parent_dir = os.path.dirname(_current_dir)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

try:
    from ..models import CONSTITUTIONAL_HASH, AgentMessage, MessageStatus, MessageType, Priority
    from ..validation_strategies import (
        CompositeValidationStrategy,
        PQCValidationStrategy,
        StaticHashValidationStrategy,
    )
except ImportError:
    from models import CONSTITUTIONAL_HASH, AgentMessage, MessageStatus, MessageType, Priority
    from validation_strategies import (
        CompositeValidationStrategy,
        PQCValidationStrategy,
        StaticHashValidationStrategy,
    )


@pytest.fixture
def sample_agent_message():
    """Create a sample AgentMessage for testing."""
    return AgentMessage(
        content={"action": "test_action", "data": "test_data"},
        from_agent="test_agent",
        to_agent="target_agent",
        message_type=MessageType.COMMAND,
        priority=Priority.HIGH,
    )


@pytest.fixture
def pqc_validator():
    """Create a PQCValidationStrategy instance."""
    return PQCValidationStrategy(hybrid_mode=True)


@pytest.fixture
def mock_constitutional_validator():
    """Create a mock ConstitutionalHashValidator."""
    mock_validator = AsyncMock()
    mock_validator.verify_governance_decision.return_value = True
    return mock_validator


class TestPQCValidationStrategy:
    """Tests for PQCValidationStrategy."""

    @pytest.mark.asyncio
    async def test_pqc_validation_without_signature_uses_fallback(
        self, pqc_validator, sample_agent_message
    ):
        """Test that PQC validation falls back to static hash when no signature present."""
        # Message without PQC signature
        is_valid, error = await pqc_validator.validate(sample_agent_message)

        assert is_valid is True
        assert error is None

    @pytest.mark.asyncio
    async def test_pqc_validation_without_signature_strict_mode(self):
        """Test that PQC validation rejects messages without signature in strict mode."""
        validator = PQCValidationStrategy(hybrid_mode=False)
        message = AgentMessage(content={"test": "data"})

        is_valid, error = await validator.validate(message)

        assert is_valid is False
        assert "PQC signature required" in error

    @pytest.mark.asyncio
    async def test_pqc_validation_with_invalid_signature(self, pqc_validator, sample_agent_message):
        """Test PQC validation with invalid signature."""
        # Add invalid PQC signature
        sample_agent_message.pqc_signature = "invalid_base64"
        sample_agent_message.pqc_public_key = "invalid_key"

        is_valid, error = await pqc_validator.validate(sample_agent_message)

        assert is_valid is False
        assert "PQC validation error" in error

    @pytest.mark.asyncio
    async def test_pqc_validation_unavailable_fallback(self, sample_agent_message):
        """Test PQC validation when validator is not available."""
        with patch(
            "quantum_research.post_quantum_crypto.ConstitutionalHashValidator",
            side_effect=ImportError,
        ):
            validator = PQCValidationStrategy()

            is_valid, error = await validator.validate(sample_agent_message)

            assert is_valid is False
            assert "PQC validator not available" in error


class TestCompositeValidationStrategyPQC:
    """Tests for CompositeValidationStrategy with PQC integration."""

    @pytest.mark.asyncio
    async def test_composite_auto_enables_pqc(self):
        """Test that CompositeValidationStrategy auto-enables PQC."""
        composite = CompositeValidationStrategy(enable_pqc=True)

        # Check that PQC strategy was added
        pqc_strategies = [s for s in composite._strategies if isinstance(s, PQCValidationStrategy)]
        assert len(pqc_strategies) == 1

    @pytest.mark.asyncio
    async def test_composite_pqc_disabled(self):
        """Test CompositeValidationStrategy with PQC disabled."""
        composite = CompositeValidationStrategy(enable_pqc=False)

        # Check that no PQC strategy was added
        pqc_strategies = [s for s in composite._strategies if isinstance(s, PQCValidationStrategy)]
        assert len(pqc_strategies) == 0

    @pytest.mark.asyncio
    async def test_composite_pqc_prioritization(self, sample_agent_message):
        """Test that PQC validation is prioritized when signature present."""
        composite = CompositeValidationStrategy(enable_pqc=True)

        # Add PQC signature to message
        sample_agent_message.pqc_signature = "test_signature"
        sample_agent_message.pqc_public_key = "test_key"

        # Mock the PQC validator to fail
        for strategy in composite._strategies:
            if isinstance(strategy, PQCValidationStrategy):
                with patch.object(strategy, "validate", return_value=(False, "PQC failed")):
                    is_valid, error = await composite.validate(sample_agent_message)
                    assert is_valid is False
                    assert "PQC:" in error

    @pytest.mark.asyncio
    async def test_composite_fallback_behavior(self, sample_agent_message):
        """Test composite validation fallback behavior."""
        # Create composite with static hash and PQC
        static_strategy = StaticHashValidationStrategy(strict=True)
        composite = CompositeValidationStrategy(strategies=[static_strategy], enable_pqc=True)

        # Valid message (should pass)
        is_valid, error = await composite.validate(sample_agent_message)
        assert is_valid is True
        assert error is None

        # Invalid constitutional hash (should fail)
        sample_agent_message.constitutional_hash = "invalid_hash"
        is_valid, error = await composite.validate(sample_agent_message)
        assert is_valid is False
        assert "StaticHashValidationStrategy:" in error


class TestAgentMessagePQCExtensions:
    """Tests for AgentMessage PQC field extensions."""

    def test_agent_message_pqc_fields_initialization(self):
        """Test that AgentMessage initializes PQC fields correctly."""
        message = AgentMessage()

        assert message.pqc_signature is None
        assert message.pqc_public_key is None
        assert message.pqc_algorithm is None

    def test_agent_message_to_dict_includes_pqc_fields(self):
        """Test that to_dict includes PQC fields."""
        message = AgentMessage()
        message.pqc_signature = "test_sig"
        message.pqc_public_key = "test_key"
        message.pqc_algorithm = "dilithium-3"

        data = message.to_dict()

        assert data["pqc_signature"] == "test_sig"
        assert data["pqc_public_key"] == "test_key"
        assert data["pqc_algorithm"] == "dilithium-3"

    def test_agent_message_from_dict_pqc_fields(self):
        """Test that from_dict handles PQC fields."""
        data = {
            "message_id": "test-123",
            "conversation_id": "conv-123",
            "content": {"test": "data"},
            "from_agent": "agent1",
            "to_agent": "agent2",
            "message_type": "command",
            "priority": 1,
            "status": "pending",
            "constitutional_hash": CONSTITUTIONAL_HASH,
            "pqc_signature": "test_sig",
            "pqc_public_key": "test_key",
            "pqc_algorithm": "dilithium-3",
        }

        message = AgentMessage.from_dict(data)

        assert message.pqc_signature == "test_sig"
        assert message.pqc_public_key == "test_key"
        assert message.pqc_algorithm == "dilithium-3"


class TestPQCHybridModeIntegration:
    """Tests for PQC hybrid mode integration."""

    @pytest.mark.asyncio
    async def test_hybrid_mode_static_hash_fallback(self, sample_agent_message):
        """Test hybrid mode falls back to static hash validation."""
        validator = PQCValidationStrategy(hybrid_mode=True)

        # Valid constitutional hash
        sample_agent_message.constitutional_hash = CONSTITUTIONAL_HASH
        is_valid, error = await validator.validate(sample_agent_message)

        assert is_valid is True
        assert error is None

        # Invalid constitutional hash
        sample_agent_message.constitutional_hash = "invalid_hash"
        is_valid, error = await validator.validate(sample_agent_message)

        assert is_valid is False
        assert "Constitutional hash mismatch" in error


class TestPQCPerformanceBenchmarks:
    """Performance benchmarks for PQC validation."""

    @pytest.mark.asyncio
    async def test_pqc_validation_performance_baseline(self, benchmark):
        """Benchmark PQC validation performance."""
        validator = PQCValidationStrategy(hybrid_mode=True)
        message = AgentMessage(content={"test": "benchmark"})

        # Benchmark the validation
        async def validate_message():
            return await validator.validate(message)

        result = await benchmark(validate_message)
        assert result[0] is True  # Should pass (hybrid mode fallback)

    @pytest.mark.asyncio
    async def test_composite_validation_performance(self, benchmark):
        """Benchmark composite validation with PQC."""
        composite = CompositeValidationStrategy(enable_pqc=True)
        message = AgentMessage(content={"test": "benchmark"})

        async def validate_message():
            return await composite.validate(message)

        result = await benchmark(validate_message)
        assert result[0] is True  # Should pass


class TestPQCSecurityProperties:
    """Tests for PQC security properties."""

    @pytest.mark.asyncio
    async def test_pqc_signature_verification_logic(self):
        """Test the PQC signature verification logic."""
        validator = PQCValidationStrategy(hybrid_mode=True)

        # Create a message with PQC signature
        message = AgentMessage(content={"test": "data"})
        message.pqc_signature = base64.b64encode(b"test_signature").decode()
        message.pqc_public_key = "test_public_key"

        # Mock the underlying validator
        with patch(
            "quantum_research.post_quantum_crypto.ConstitutionalHashValidator"
        ) as mock_class:
            mock_validator = AsyncMock()
            mock_validator.verify_governance_decision.return_value = True
            mock_class.return_value = mock_validator

            # Create new validator to pick up mock
            validator = PQCValidationStrategy(hybrid_mode=True)

            is_valid, error = await validator.validate(message)

            # Verify the mock was called correctly
            assert mock_validator.verify_governance_decision.called
            call_args = mock_validator.verify_governance_decision.call_args
            assert len(call_args[0]) == 3  # decision, signature, public_key


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
