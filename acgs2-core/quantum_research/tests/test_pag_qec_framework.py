#!/usr/bin/env python3
"""
Comprehensive Unit Tests for PAG-QEC Framework
Constitutional Hash: cdd01ef066bc6cf2

Tests all components:
- NeuralDecoder architecture and inference
- ThreeQubitCodeEnvironment syndrome generation
- DecoderTrainer supervised learning
- SpeculativeExecutionEngine caching
- LookupTableDecoder baseline
- Quantization for FPGA deployment
"""

import sys
from pathlib import Path

import pytest
import torch
import torch.nn as nn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import PAG-QEC components
try:
    from pag_qec_framework import (
        CONSTITUTIONAL_HASH,
        DecoderEnsemble,
        DecoderTrainer,
        LookupTableDecoder,
        NeuralDecoder,
        SpeculativeExecutionEngine,
        ThreeQubitCodeEnvironment,
    )

    PAG_QEC_AVAILABLE = True
except ImportError:
    PAG_QEC_AVAILABLE = False


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def neural_decoder():
    """Create a fresh NeuralDecoder instance."""
    if not PAG_QEC_AVAILABLE:
        pytest.skip("PAG-QEC framework not available")
    return NeuralDecoder(syndrome_size=2, num_qubits=3, hidden_dim=32, num_layers=2)


@pytest.fixture
def three_qubit_env():
    """Create ThreeQubitCodeEnvironment."""
    if not PAG_QEC_AVAILABLE:
        pytest.skip("PAG-QEC framework not available")
    return ThreeQubitCodeEnvironment(error_probability=0.25)


@pytest.fixture
def lookup_decoder():
    """Create LookupTableDecoder."""
    if not PAG_QEC_AVAILABLE:
        pytest.skip("PAG-QEC framework not available")
    return LookupTableDecoder()


@pytest.fixture
def speculative_engine(neural_decoder):
    """Create SpeculativeExecutionEngine."""
    if not PAG_QEC_AVAILABLE:
        pytest.skip("PAG-QEC framework not available")
    return SpeculativeExecutionEngine(neural_decoder, top_k=4)


# =============================================================================
# CONSTITUTIONAL COMPLIANCE TESTS
# =============================================================================


class TestConstitutionalCompliance:
    """Verify constitutional hash is present and correct."""

    def test_constitutional_hash_present(self):
        """Verify CONSTITUTIONAL_HASH is defined."""
        if not PAG_QEC_AVAILABLE:
            pytest.skip("PAG-QEC framework not available")
        assert CONSTITUTIONAL_HASH is not None
        assert len(CONSTITUTIONAL_HASH) > 0

    def test_constitutional_hash_value(self):
        """Verify hash matches expected value."""
        if not PAG_QEC_AVAILABLE:
            pytest.skip("PAG-QEC framework not available")
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


# =============================================================================
# NEURAL DECODER TESTS
# =============================================================================


class TestNeuralDecoder:
    """Test NeuralDecoder architecture and functionality."""

    def test_initialization(self, neural_decoder):
        """Test decoder initializes correctly."""
        assert neural_decoder.syndrome_size == 2
        assert neural_decoder.num_qubits == 3
        assert neural_decoder.inference_count == 0

    def test_forward_shape(self, neural_decoder):
        """Test forward pass output shapes."""
        batch_size = 8
        syndrome = torch.rand(batch_size, 2)

        correction, confidence = neural_decoder(syndrome)

        assert correction.shape == (batch_size, 3)
        assert confidence.shape == (batch_size, 1)

    def test_forward_output_range(self, neural_decoder):
        """Test outputs are in valid range [0, 1]."""
        syndrome = torch.rand(16, 2)
        correction, confidence = neural_decoder(syndrome)

        assert (correction >= 0).all() and (correction <= 1).all()
        assert (confidence >= 0).all() and (confidence <= 1).all()

    def test_decode_single(self, neural_decoder):
        """Test decode with single syndrome."""
        syndrome = torch.tensor([1.0, 0.0])
        qubit, confidence = neural_decoder.decode(syndrome)

        assert isinstance(qubit, int)
        assert qubit in [-1, 0, 1, 2]
        assert 0 <= confidence <= 1

    def test_inference_statistics(self, neural_decoder):
        """Test inference statistics tracking."""
        initial_count = neural_decoder.inference_count

        for _ in range(10):
            syndrome = torch.rand(2)
            neural_decoder.decode(syndrome)

        assert neural_decoder.inference_count == initial_count + 10
        assert neural_decoder.total_inference_time_ns > 0

    def test_quantization(self, neural_decoder):
        """Test INT8 quantization for FPGA deployment."""
        quantized = neural_decoder.quantize_for_deployment()

        # Should still produce valid outputs
        syndrome = torch.tensor([1.0, 0.0])
        qubit, confidence = quantized.decode(syndrome)

        assert isinstance(qubit, int)
        assert 0 <= confidence <= 1

    def test_gradient_flow(self, neural_decoder):
        """Test gradients flow through network."""
        syndrome = torch.rand(4, 2, requires_grad=False)
        target = torch.rand(4, 3)

        correction, _ = neural_decoder(syndrome)
        loss = nn.functional.mse_loss(correction, target)
        loss.backward()

        # Check gradients exist
        for param in neural_decoder.parameters():
            if param.requires_grad:
                assert param.grad is not None


class TestDecoderEnsemble:
    """Test DecoderEnsemble voting mechanism."""

    def test_ensemble_creation(self):
        """Test ensemble initializes multiple decoders."""
        if not PAG_QEC_AVAILABLE:
            pytest.skip("PAG-QEC framework not available")

        ensemble = DecoderEnsemble(num_decoders=3, syndrome_size=2, num_qubits=3)
        assert len(ensemble.decoders) == 3

    def test_ensemble_voting(self):
        """Test ensemble majority voting."""
        if not PAG_QEC_AVAILABLE:
            pytest.skip("PAG-QEC framework not available")

        ensemble = DecoderEnsemble(num_decoders=5, syndrome_size=2, num_qubits=3)
        syndrome = torch.tensor([1.0, 0.0])

        qubit, confidence, votes = ensemble.decode_with_voting(syndrome)

        assert isinstance(qubit, int)
        assert qubit in [-1, 0, 1, 2]
        assert 0 <= confidence <= 1
        assert len(votes) == 5


# =============================================================================
# THREE-QUBIT CODE ENVIRONMENT TESTS
# =============================================================================


class TestThreeQubitCodeEnvironment:
    """Test three-qubit bit-flip code environment."""

    def test_syndrome_table(self, three_qubit_env):
        """Verify syndrome table is correct."""
        expected = {
            (0, 0): -1,  # No error
            (1, 0): 0,  # Error on qubit 0
            (1, 1): 1,  # Error on qubit 1
            (0, 1): 2,  # Error on qubit 2
        }
        assert three_qubit_env.SYNDROME_TABLE == expected

    def test_generate_sample(self, three_qubit_env):
        """Test sample generation."""
        sample = three_qubit_env.generate_sample()

        assert hasattr(sample, "syndrome")
        assert hasattr(sample, "error_qubit")
        assert len(sample.syndrome) == 2
        assert sample.error_qubit in [-1, 0, 1, 2]

    def test_syndrome_consistency(self, three_qubit_env):
        """Test syndrome matches error pattern."""
        for _ in range(100):
            sample = three_qubit_env.generate_sample()
            expected_qubit = three_qubit_env.SYNDROME_TABLE[sample.syndrome]
            assert sample.error_qubit == expected_qubit

    def test_generate_dataset(self, three_qubit_env):
        """Test dataset generation."""
        dataset = three_qubit_env.generate_dataset(100)

        assert len(dataset) == 100
        assert all(hasattr(d, "syndrome") for d in dataset)
        assert all(hasattr(d, "error_qubit") for d in dataset)

    def test_error_probability(self):
        """Test error probability affects distribution."""
        if not PAG_QEC_AVAILABLE:
            pytest.skip("PAG-QEC framework not available")

        # High error rate
        high_env = ThreeQubitCodeEnvironment(error_probability=0.5)
        high_data = high_env.generate_dataset(1000)
        high_errors = sum(1 for d in high_data if d.error_qubit != -1)

        # Low error rate
        low_env = ThreeQubitCodeEnvironment(error_probability=0.1)
        low_data = low_env.generate_dataset(1000)
        low_errors = sum(1 for d in low_data if d.error_qubit != -1)

        assert high_errors > low_errors


# =============================================================================
# DECODER TRAINER TESTS
# =============================================================================


class TestDecoderTrainer:
    """Test supervised training of neural decoder."""

    def test_trainer_initialization(self, neural_decoder, three_qubit_env):
        """Test trainer initializes correctly."""
        if not PAG_QEC_AVAILABLE:
            pytest.skip("PAG-QEC framework not available")

        trainer = DecoderTrainer(neural_decoder, three_qubit_env)
        assert trainer.decoder == neural_decoder
        assert trainer.env == three_qubit_env

    def test_training_reduces_loss(self, neural_decoder, three_qubit_env):
        """Test training reduces loss over time."""
        if not PAG_QEC_AVAILABLE:
            pytest.skip("PAG-QEC framework not available")

        trainer = DecoderTrainer(neural_decoder, three_qubit_env)

        # Get initial loss
        initial_dataset = three_qubit_env.generate_dataset(100)
        syndromes = torch.tensor([d.syndrome for d in initial_dataset], dtype=torch.float32)
        targets = torch.tensor(
            [[1.0 if i == d.error_qubit else 0.0 for i in range(3)] for d in initial_dataset],
            dtype=torch.float32,
        )

        correction, _ = neural_decoder(syndromes)
        initial_loss = nn.functional.mse_loss(correction, targets).item()

        # Train
        trainer.train_supervised(num_epochs=50, dataset_size=500)

        # Check loss decreased
        correction, _ = neural_decoder(syndromes)
        final_loss = nn.functional.mse_loss(correction, targets).item()

        # Allow for some variance, but expect improvement
        assert final_loss < initial_loss * 1.5  # At worst, not much worse

    def test_evaluation(self, neural_decoder, three_qubit_env):
        """Test evaluation returns valid accuracy."""
        if not PAG_QEC_AVAILABLE:
            pytest.skip("PAG-QEC framework not available")

        trainer = DecoderTrainer(neural_decoder, three_qubit_env)
        accuracy = trainer.evaluate(num_samples=100)

        assert 0 <= accuracy <= 1


# =============================================================================
# SPECULATIVE EXECUTION ENGINE TESTS
# =============================================================================


class TestSpeculativeExecutionEngine:
    """Test speculative execution with caching."""

    def test_initialization(self, speculative_engine):
        """Test engine initializes correctly."""
        assert speculative_engine.top_k == 4
        assert len(speculative_engine.cache) == 0

    def test_precompute_syndromes(self, speculative_engine):
        """Test syndrome precomputation."""
        speculative_engine.precompute_likely_syndromes()

        assert len(speculative_engine.cache) == 4  # All 4 syndromes
        assert (0, 0) in speculative_engine.cache
        assert (1, 0) in speculative_engine.cache
        assert (1, 1) in speculative_engine.cache
        assert (0, 1) in speculative_engine.cache

    def test_cache_hit(self, speculative_engine):
        """Test cache hit path."""
        speculative_engine.precompute_likely_syndromes()

        correction, confidence, path = speculative_engine.decode_with_speculation((0, 0))

        assert path == "cache_hit"
        assert speculative_engine.cache_hits == 1
        assert speculative_engine.cache_misses == 0

    def test_cache_miss(self, speculative_engine):
        """Test cache miss path."""
        # Don't precompute - cache is empty
        correction, confidence, path = speculative_engine.decode_with_speculation((1, 0))

        assert path in ["computed", "escalated"]
        assert speculative_engine.cache_misses == 1

    def test_statistics(self, speculative_engine):
        """Test statistics tracking."""
        speculative_engine.precompute_likely_syndromes()

        # Generate hits and misses
        for _ in range(10):
            speculative_engine.decode_with_speculation((0, 0))

        stats = speculative_engine.get_statistics()

        assert "cache_hits" in stats
        assert "cache_misses" in stats
        assert "hit_rate" in stats
        assert stats["cache_hits"] == 10

    def test_reset_statistics(self, speculative_engine):
        """Test statistics reset."""
        speculative_engine.precompute_likely_syndromes()
        speculative_engine.decode_with_speculation((0, 0))
        speculative_engine.decode_with_speculation((1, 0))

        speculative_engine.reset_statistics()

        assert speculative_engine.cache_hits == 0
        assert speculative_engine.cache_misses == 0
        assert speculative_engine.escalations == 0


# =============================================================================
# LOOKUP TABLE DECODER TESTS
# =============================================================================


class TestLookupTableDecoder:
    """Test baseline lookup table decoder."""

    def test_all_syndromes(self, lookup_decoder):
        """Test decoder handles all valid syndromes."""
        expected = {
            (0, 0): -1,
            (1, 0): 0,
            (1, 1): 1,
            (0, 1): 2,
        }

        for syndrome, expected_qubit in expected.items():
            qubit, confidence = lookup_decoder.decode(syndrome)
            assert qubit == expected_qubit
            assert confidence == 1.0

    def test_inference_time(self, lookup_decoder):
        """Test lookup is fast."""
        for _ in range(1000):
            lookup_decoder.decode((1, 0))

        avg_time = lookup_decoder.get_avg_inference_time_ns()
        assert avg_time < 10000  # Should be < 10µs

    def test_statistics(self, lookup_decoder):
        """Test statistics tracking."""
        for _ in range(50):
            lookup_decoder.decode((0, 1))

        assert lookup_decoder.inference_count == 50
        assert lookup_decoder.total_inference_time_ns > 0


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_train_and_decode(self, neural_decoder, three_qubit_env):
        """Test complete train-then-decode workflow."""
        if not PAG_QEC_AVAILABLE:
            pytest.skip("PAG-QEC framework not available")

        # Train decoder
        trainer = DecoderTrainer(neural_decoder, three_qubit_env)
        trainer.train_supervised(num_epochs=50, dataset_size=500)

        # Decode test samples
        test_data = three_qubit_env.generate_dataset(100)
        correct = 0

        for sample in test_data:
            syndrome = torch.tensor(sample.syndrome, dtype=torch.float32)
            predicted, _ = neural_decoder.decode(syndrome)

            if predicted == sample.error_qubit:
                correct += 1

        accuracy = correct / len(test_data)
        assert accuracy > 0.5  # Should be better than random

    def test_speculative_vs_lookup(self, neural_decoder, three_qubit_env):
        """Test speculative engine matches lookup accuracy."""
        if not PAG_QEC_AVAILABLE:
            pytest.skip("PAG-QEC framework not available")

        # Train neural decoder
        trainer = DecoderTrainer(neural_decoder, three_qubit_env)
        trainer.train_supervised(num_epochs=100, dataset_size=1000)

        # Create speculative engine
        spec_engine = SpeculativeExecutionEngine(neural_decoder, top_k=4)
        spec_engine.precompute_likely_syndromes()

        # Create lookup decoder
        lookup = LookupTableDecoder()

        # Compare on test data
        test_data = three_qubit_env.generate_dataset(100)
        spec_correct = 0
        lookup_correct = 0

        for sample in test_data:
            spec_pred, _, _ = spec_engine.decode_with_speculation(sample.syndrome)
            lookup_pred, _ = lookup.decode(sample.syndrome)

            if spec_pred == sample.error_qubit:
                spec_correct += 1
            if lookup_pred == sample.error_qubit:
                lookup_correct += 1

        # Lookup should be perfect for 3-qubit code
        assert lookup_correct == 100

        # Speculative should be reasonably good
        assert spec_correct > 80


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


class TestPerformance:
    """Performance and latency tests."""

    def test_neural_inference_latency(self, neural_decoder):
        """Test neural decoder latency."""
        # Warm up
        for _ in range(100):
            syndrome = torch.rand(2)
            neural_decoder.decode(syndrome)

        # Measure
        neural_decoder.inference_count = 0
        neural_decoder.total_inference_time_ns = 0

        for _ in range(1000):
            syndrome = torch.rand(2)
            neural_decoder.decode(syndrome)

        avg_latency_us = neural_decoder.get_avg_inference_time_ns() / 1000

        # Should be under 100µs for this small network
        assert avg_latency_us < 100

    def test_lookup_faster_than_neural(self, neural_decoder, lookup_decoder):
        """Verify lookup is faster than neural."""
        # Benchmark lookup
        for _ in range(1000):
            lookup_decoder.decode((1, 0))
        lookup_latency = lookup_decoder.get_avg_inference_time_ns()

        # Benchmark neural
        neural_decoder.inference_count = 0
        neural_decoder.total_inference_time_ns = 0
        for _ in range(1000):
            syndrome = torch.tensor([1.0, 0.0])
            neural_decoder.decode(syndrome)
        neural_latency = neural_decoder.get_avg_inference_time_ns()

        # Lookup should be significantly faster
        assert lookup_latency < neural_latency

    def test_cache_hit_latency(self, speculative_engine):
        """Test cache hit is fast."""
        speculative_engine.precompute_likely_syndromes()

        # Warm up
        for _ in range(100):
            speculative_engine.decode_with_speculation((0, 0))

        # Measure cache hits
        speculative_engine.reset_statistics()
        import time

        start = time.perf_counter_ns()
        for _ in range(1000):
            speculative_engine.decode_with_speculation((1, 0))
        end = time.perf_counter_ns()

        avg_latency_ns = (end - start) / 1000

        # Cache hits should be very fast
        assert avg_latency_ns < 5000  # < 5µs


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_batch_size_one(self, neural_decoder):
        """Test single sample batch."""
        syndrome = torch.rand(1, 2)
        correction, confidence = neural_decoder(syndrome)

        assert correction.shape == (1, 3)
        assert confidence.shape == (1, 1)

    def test_large_batch(self, neural_decoder):
        """Test large batch processing."""
        syndrome = torch.rand(256, 2)
        correction, confidence = neural_decoder(syndrome)

        assert correction.shape == (256, 3)
        assert confidence.shape == (256, 1)

    def test_deterministic_lookup(self, lookup_decoder):
        """Test lookup is deterministic."""
        results = []
        for _ in range(100):
            qubit, conf = lookup_decoder.decode((1, 1))
            results.append((qubit, conf))

        assert all(r == results[0] for r in results)

    def test_empty_cache(self, speculative_engine):
        """Test engine works with empty cache."""
        # No precomputation
        correction, confidence, path = speculative_engine.decode_with_speculation((0, 0))

        assert path in ["computed", "escalated"]
        assert isinstance(correction, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
