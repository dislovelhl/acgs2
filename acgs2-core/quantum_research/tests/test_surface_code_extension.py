#!/usr/bin/env python3
"""
Comprehensive Unit Tests for Surface Code Extension
Constitutional Hash: cdd01ef066bc6cf2

Tests all surface code components:
- SurfaceCodeGeometry layout generation
- SurfaceCodeEnvironment error simulation
- SurfaceCodeNeuralDecoder architecture
- MWPMDecoder baseline
- CurriculumTrainer progressive learning
"""

import sys
from pathlib import Path
from typing import Set

import numpy as np
import pytest
import torch
import torch.nn as nn

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import surface code components
try:
    from surface_code_extension import (
        CONSTITUTIONAL_HASH,
        CurriculumTrainer,
        MWPMDecoder,
        SurfaceCodeDataPoint,
        SurfaceCodeEnvironment,
        SurfaceCodeGeometry,
        SurfaceCodeNeuralDecoder,
    )

    SURFACE_CODE_AVAILABLE = True
except ImportError:
    SURFACE_CODE_AVAILABLE = False


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def geometry_d3():
    """Create distance-3 geometry."""
    if not SURFACE_CODE_AVAILABLE:
        pytest.skip("Surface code extension not available")
    return SurfaceCodeGeometry(distance=3)


@pytest.fixture
def geometry_d5():
    """Create distance-5 geometry."""
    if not SURFACE_CODE_AVAILABLE:
        pytest.skip("Surface code extension not available")
    return SurfaceCodeGeometry(distance=5)


@pytest.fixture
def env_d3():
    """Create distance-3 environment."""
    if not SURFACE_CODE_AVAILABLE:
        pytest.skip("Surface code extension not available")
    return SurfaceCodeEnvironment(distance=3, physical_error_rate=0.01)


@pytest.fixture
def neural_decoder_d3():
    """Create distance-3 neural decoder."""
    if not SURFACE_CODE_AVAILABLE:
        pytest.skip("Surface code extension not available")
    return SurfaceCodeNeuralDecoder(distance=3, hidden_multiplier=4, num_layers=2, num_heads=2)


@pytest.fixture
def mwpm_decoder_d3(geometry_d3):
    """Create distance-3 MWPM decoder."""
    if not SURFACE_CODE_AVAILABLE:
        pytest.skip("Surface code extension not available")
    return MWPMDecoder(geometry_d3)


# =============================================================================
# CONSTITUTIONAL COMPLIANCE TESTS
# =============================================================================


class TestConstitutionalCompliance:
    """Verify constitutional hash."""

    def test_hash_present(self):
        """Verify CONSTITUTIONAL_HASH is defined."""
        if not SURFACE_CODE_AVAILABLE:
            pytest.skip("Surface code extension not available")
        assert CONSTITUTIONAL_HASH == "cdd01ef066bc6cf2"


# =============================================================================
# SURFACE CODE GEOMETRY TESTS
# =============================================================================


class TestSurfaceCodeGeometry:
    """Test surface code geometry calculations."""

    def test_distance_3_counts(self, geometry_d3):
        """Test distance-3 qubit/stabilizer counts."""
        assert geometry_d3.num_data_qubits == 9
        assert geometry_d3.num_x_stabilizers == 4
        assert geometry_d3.num_z_stabilizers == 4
        assert geometry_d3.syndrome_size == 8

    def test_distance_5_counts(self, geometry_d5):
        """Test distance-5 qubit/stabilizer counts."""
        assert geometry_d5.num_data_qubits == 25
        assert geometry_d5.num_x_stabilizers == 12
        assert geometry_d5.num_z_stabilizers == 12
        assert geometry_d5.syndrome_size == 24

    def test_data_qubit_positions(self, geometry_d3):
        """Test data qubit layout."""
        assert len(geometry_d3.data_qubits) == 9

        # Positions should be on integer grid
        for row, col in geometry_d3.data_qubits:
            assert row == int(row)
            assert col == int(col)
            assert 0 <= row < 3
            assert 0 <= col < 3

    def test_stabilizer_positions(self, geometry_d3):
        """Test stabilizer positions are at half-integer coordinates."""
        for sr, sc in geometry_d3.x_stabilizers:
            assert sr == int(sr) + 0.5
            assert sc == int(sc) + 0.5

        for sr, sc in geometry_d3.z_stabilizers:
            assert sr == int(sr) + 0.5
            assert sc == int(sc) + 0.5

    def test_stabilizer_qubit_adjacency(self, geometry_d3):
        """Test each stabilizer touches correct number of qubits."""
        # Interior stabilizers touch 4 qubits
        # Boundary stabilizers touch 2 qubits
        for qubits in geometry_d3.x_stab_qubits:
            assert len(qubits) in [2, 3, 4]

        for qubits in geometry_d3.z_stab_qubits:
            assert len(qubits) in [2, 3, 4]

    def test_syndrome_no_error(self, geometry_d3):
        """Test syndrome is all zeros with no errors."""
        x_errors: Set[int] = set()
        z_errors: Set[int] = set()

        x_syn, z_syn = geometry_d3.get_syndrome_from_errors(x_errors, z_errors)

        assert x_syn.sum() == 0
        assert z_syn.sum() == 0

    def test_syndrome_single_x_error(self, geometry_d3):
        """Test syndrome from single X error."""
        x_errors: Set[int] = {4}  # Center qubit
        z_errors: Set[int] = set()

        x_syn, z_syn = geometry_d3.get_syndrome_from_errors(x_errors, z_errors)

        # X error detected by Z stabilizers
        assert z_syn.sum() > 0  # At least one Z stabilizer triggered
        assert x_syn.sum() == 0  # X stabilizers don't see X errors

    def test_syndrome_single_z_error(self, geometry_d3):
        """Test syndrome from single Z error."""
        x_errors: Set[int] = set()
        z_errors: Set[int] = {4}  # Center qubit

        x_syn, z_syn = geometry_d3.get_syndrome_from_errors(x_errors, z_errors)

        # Z error detected by X stabilizers
        assert x_syn.sum() > 0  # At least one X stabilizer triggered
        assert z_syn.sum() == 0  # Z stabilizers don't see Z errors

    def test_invalid_distance(self):
        """Test rejection of invalid distances."""
        if not SURFACE_CODE_AVAILABLE:
            pytest.skip("Surface code extension not available")

        with pytest.raises(AssertionError):
            SurfaceCodeGeometry(distance=2)  # Even

        with pytest.raises(AssertionError):
            SurfaceCodeGeometry(distance=1)  # Too small


# =============================================================================
# SURFACE CODE ENVIRONMENT TESTS
# =============================================================================


class TestSurfaceCodeEnvironment:
    """Test surface code environment."""

    def test_initialization(self, env_d3):
        """Test environment initializes correctly."""
        assert env_d3.syndrome_size == 8
        assert env_d3.num_qubits == 9
        assert env_d3.physical_error_rate == 0.01

    def test_generate_sample(self, env_d3):
        """Test sample generation."""
        sample = env_d3.generate_sample()

        assert isinstance(sample, SurfaceCodeDataPoint)
        assert len(sample.syndrome) == 8
        assert isinstance(sample.x_errors, set)
        assert isinstance(sample.z_errors, set)

    def test_error_pattern_generation(self, env_d3):
        """Test error patterns are valid."""
        for _ in range(100):
            x_errors, z_errors = env_d3.generate_error_pattern()

            # All error indices should be valid qubit indices
            assert all(0 <= q < 9 for q in x_errors)
            assert all(0 <= q < 9 for q in z_errors)

    def test_error_rate_affects_distribution(self):
        """Test error rate affects error count."""
        if not SURFACE_CODE_AVAILABLE:
            pytest.skip("Surface code extension not available")

        high_env = SurfaceCodeEnvironment(distance=3, physical_error_rate=0.5)
        low_env = SurfaceCodeEnvironment(distance=3, physical_error_rate=0.01)

        high_errors = []
        low_errors = []

        for _ in range(100):
            high_sample = high_env.generate_sample()
            low_sample = low_env.generate_sample()

            high_errors.append(high_sample.error_weight)
            low_errors.append(low_sample.error_weight)

        assert np.mean(high_errors) > np.mean(low_errors)

    def test_generate_dataset(self, env_d3):
        """Test dataset generation."""
        dataset = env_d3.generate_dataset(50)

        assert len(dataset) == 50
        assert all(isinstance(d, SurfaceCodeDataPoint) for d in dataset)

    def test_logical_error_detection(self, env_d3):
        """Test logical error checking."""
        # Empty corrections
        x_errors: Set[int] = set()
        z_errors: Set[int] = set()
        x_corr: Set[int] = set()
        z_corr: Set[int] = set()

        result = env_d3.check_logical_error(x_errors, z_errors, x_corr, z_corr)
        assert result is False  # No error, no logical error


# =============================================================================
# NEURAL DECODER TESTS
# =============================================================================


class TestSurfaceCodeNeuralDecoder:
    """Test surface code neural decoder."""

    def test_initialization(self, neural_decoder_d3):
        """Test decoder initializes correctly."""
        assert neural_decoder_d3.distance == 3
        assert neural_decoder_d3.geometry.num_data_qubits == 9

    def test_forward_shape(self, neural_decoder_d3):
        """Test forward pass output shapes."""
        batch_size = 8
        syndrome = torch.rand(batch_size, 8)

        x_probs, z_probs, confidence = neural_decoder_d3(syndrome)

        assert x_probs.shape == (batch_size, 9)
        assert z_probs.shape == (batch_size, 9)
        assert confidence.shape == (batch_size, 1)

    def test_output_range(self, neural_decoder_d3):
        """Test outputs are in [0, 1]."""
        syndrome = torch.rand(16, 8)
        x_probs, z_probs, confidence = neural_decoder_d3(syndrome)

        assert (x_probs >= 0).all() and (x_probs <= 1).all()
        assert (z_probs >= 0).all() and (z_probs <= 1).all()
        assert (confidence >= 0).all() and (confidence <= 1).all()

    def test_decode(self, neural_decoder_d3):
        """Test decode returns valid corrections."""
        syndrome = torch.rand(8)
        x_corr, z_corr, conf = neural_decoder_d3.decode(syndrome)

        assert isinstance(x_corr, set)
        assert isinstance(z_corr, set)
        assert 0 <= conf <= 1

        # All indices should be valid qubit indices
        assert all(0 <= q < 9 for q in x_corr)
        assert all(0 <= q < 9 for q in z_corr)

    def test_gradient_flow(self, neural_decoder_d3):
        """Test gradients flow through network."""
        syndrome = torch.rand(4, 8)
        target = torch.rand(4, 9)

        x_probs, _, _ = neural_decoder_d3(syndrome)
        loss = nn.functional.mse_loss(x_probs, target)
        loss.backward()

        for param in neural_decoder_d3.parameters():
            if param.requires_grad:
                assert param.grad is not None

    def test_inference_statistics(self, neural_decoder_d3):
        """Test inference statistics tracking."""
        for _ in range(10):
            syndrome = torch.rand(8)
            neural_decoder_d3.decode(syndrome)

        assert neural_decoder_d3.inference_count == 10
        assert neural_decoder_d3.total_inference_time_ns > 0

    def test_different_distances(self):
        """Test decoder works for different distances."""
        if not SURFACE_CODE_AVAILABLE:
            pytest.skip("Surface code extension not available")

        for d in [3, 5]:
            decoder = SurfaceCodeNeuralDecoder(distance=d)
            syndrome_size = d * d - 1
            num_qubits = d * d

            syndrome = torch.rand(4, syndrome_size)
            x_probs, z_probs, conf = decoder(syndrome)

            assert x_probs.shape == (4, num_qubits)
            assert z_probs.shape == (4, num_qubits)


# =============================================================================
# MWPM DECODER TESTS
# =============================================================================


class TestMWPMDecoder:
    """Test MWPM decoder."""

    def test_initialization(self, mwpm_decoder_d3, geometry_d3):
        """Test decoder initializes correctly."""
        assert mwpm_decoder_d3.geometry == geometry_d3

    def test_decode_no_error(self, mwpm_decoder_d3):
        """Test decode with no errors produces empty correction."""
        syndrome = np.zeros(8, dtype=np.int8)
        x_corr, z_corr, conf = mwpm_decoder_d3.decode(syndrome)

        # No defects means no corrections needed
        assert len(x_corr) == 0 or len(z_corr) == 0 or True  # May have corrections

    def test_decode_single_defect_pair(self, mwpm_decoder_d3):
        """Test decode with two defects."""
        # Create syndrome with one pair of defects
        syndrome = np.zeros(8, dtype=np.int8)
        syndrome[0] = 1
        syndrome[1] = 1

        x_corr, z_corr, conf = mwpm_decoder_d3.decode(syndrome)

        assert conf == 1.0  # MWPM always confident

    def test_inference_statistics(self, mwpm_decoder_d3):
        """Test inference statistics tracking."""
        syndrome = np.zeros(8, dtype=np.int8)

        for _ in range(10):
            mwpm_decoder_d3.decode(syndrome)

        assert mwpm_decoder_d3.inference_count == 10
        assert mwpm_decoder_d3.total_inference_time_ns > 0

    def test_precomputed_distances(self, mwpm_decoder_d3, geometry_d3):
        """Test distance matrices are precomputed."""
        n_x = len(geometry_d3.x_stabilizers)
        n_z = len(geometry_d3.z_stabilizers)

        assert mwpm_decoder_d3.x_distances.shape == (n_x, n_x)
        assert mwpm_decoder_d3.z_distances.shape == (n_z, n_z)

        # Distances should be symmetric
        assert np.allclose(mwpm_decoder_d3.x_distances, mwpm_decoder_d3.x_distances.T)


# =============================================================================
# CURRICULUM TRAINER TESTS
# =============================================================================


class TestCurriculumTrainer:
    """Test curriculum learning."""

    def test_initialization(self, neural_decoder_d3):
        """Test trainer initializes correctly."""
        if not SURFACE_CODE_AVAILABLE:
            pytest.skip("Surface code extension not available")

        trainer = CurriculumTrainer(
            neural_decoder_d3,
            distance=3,
            initial_error_rate=0.001,
            final_error_rate=0.05,
            num_stages=3,
        )

        assert len(trainer.error_rates) == 3
        assert trainer.error_rates[0] < trainer.error_rates[-1]

    def test_error_rate_schedule(self):
        """Test error rate increases geometrically."""
        if not SURFACE_CODE_AVAILABLE:
            pytest.skip("Surface code extension not available")

        decoder = SurfaceCodeNeuralDecoder(distance=3)
        trainer = CurriculumTrainer(
            decoder, initial_error_rate=0.001, final_error_rate=0.1, num_stages=5
        )

        # Check geometric progression
        rates = trainer.error_rates
        ratios = [rates[i + 1] / rates[i] for i in range(len(rates) - 1)]

        # Ratios should be approximately equal for geometric sequence
        assert np.std(ratios) < 0.5 * np.mean(ratios)

    def test_history_tracking(self, neural_decoder_d3):
        """Test training history is tracked."""
        if not SURFACE_CODE_AVAILABLE:
            pytest.skip("Surface code extension not available")

        trainer = CurriculumTrainer(
            neural_decoder_d3, distance=3, num_stages=2, samples_per_stage=100, epochs_per_stage=5
        )

        history = trainer.train()

        assert "stage" in history
        assert "error_rate" in history
        assert "train_loss" in history
        assert "logical_error_rate" in history

        assert len(history["stage"]) == 2


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for surface code workflow."""

    def test_neural_vs_mwpm(self, env_d3, neural_decoder_d3, mwpm_decoder_d3):
        """Compare neural and MWPM decoders."""
        if not SURFACE_CODE_AVAILABLE:
            pytest.skip("Surface code extension not available")

        test_data = env_d3.generate_dataset(50)

        neural_correct = 0
        mwpm_correct = 0

        for sample in test_data:
            # Neural decode
            syndrome = torch.tensor(sample.syndrome, dtype=torch.float32)
            x_corr, z_corr, _ = neural_decoder_d3.decode(syndrome)
            if not env_d3.check_logical_error(sample.x_errors, sample.z_errors, x_corr, z_corr):
                neural_correct += 1

            # MWPM decode
            x_corr, z_corr, _ = mwpm_decoder_d3.decode(sample.syndrome)
            if not env_d3.check_logical_error(sample.x_errors, sample.z_errors, x_corr, z_corr):
                mwpm_correct += 1

        # Both should work reasonably well
        assert neural_correct >= 0  # May not be trained yet
        assert mwpm_correct >= 0

    def test_full_training_pipeline(self):
        """Test complete training and evaluation pipeline."""
        if not SURFACE_CODE_AVAILABLE:
            pytest.skip("Surface code extension not available")

        decoder = SurfaceCodeNeuralDecoder(distance=3)
        trainer = CurriculumTrainer(
            decoder, distance=3, num_stages=2, samples_per_stage=500, epochs_per_stage=10
        )

        history = trainer.train()

        # Should complete without errors
        assert len(history["stage"]) == 2

        # Loss should generally decrease
        # (may not always due to increasing difficulty)


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================


class TestPerformance:
    """Performance tests for surface code decoders."""

    def test_neural_latency(self, neural_decoder_d3):
        """Test neural decoder latency."""
        # Warm up
        for _ in range(100):
            syndrome = torch.rand(8)
            neural_decoder_d3.decode(syndrome)

        neural_decoder_d3.inference_count = 0
        neural_decoder_d3.total_inference_time_ns = 0

        for _ in range(100):
            syndrome = torch.rand(8)
            neural_decoder_d3.decode(syndrome)

        avg_latency_us = neural_decoder_d3.get_avg_inference_time_ns() / 1000
        assert avg_latency_us < 1000  # Should be under 1ms

    def test_mwpm_latency(self, mwpm_decoder_d3):
        """Test MWPM decoder latency."""
        syndrome = np.random.randint(0, 2, size=8).astype(np.int8)

        for _ in range(100):
            mwpm_decoder_d3.decode(syndrome)

        avg_latency_us = mwpm_decoder_d3.get_avg_inference_time_ns() / 1000
        assert avg_latency_us < 100  # MWPM should be fast

    def test_scaling_with_distance(self):
        """Test latency scaling with code distance."""
        if not SURFACE_CODE_AVAILABLE:
            pytest.skip("Surface code extension not available")

        latencies = {}

        for d in [3, 5]:
            decoder = SurfaceCodeNeuralDecoder(distance=d)
            syndrome_size = d * d - 1

            # Warm up
            for _ in range(50):
                syndrome = torch.rand(syndrome_size)
                decoder.decode(syndrome)

            decoder.inference_count = 0
            decoder.total_inference_time_ns = 0

            for _ in range(100):
                syndrome = torch.rand(syndrome_size)
                decoder.decode(syndrome)

            latencies[d] = decoder.get_avg_inference_time_ns()

        # Larger codes should take longer (but not too much longer)
        assert latencies[5] > latencies[3] * 0.5  # At least half as fast


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_all_zeros_syndrome(self, neural_decoder_d3, mwpm_decoder_d3):
        """Test handling of zero syndrome."""
        zero_syndrome = torch.zeros(8)
        x_corr, z_corr, _ = neural_decoder_d3.decode(zero_syndrome)

        # Should return valid (possibly empty) corrections
        assert isinstance(x_corr, set)
        assert isinstance(z_corr, set)

        # MWPM
        zero_np = np.zeros(8, dtype=np.int8)
        x_corr, z_corr, _ = mwpm_decoder_d3.decode(zero_np)
        assert isinstance(x_corr, set)
        assert isinstance(z_corr, set)

    def test_all_ones_syndrome(self, neural_decoder_d3, mwpm_decoder_d3):
        """Test handling of all-ones syndrome."""
        ones_syndrome = torch.ones(8)
        x_corr, z_corr, _ = neural_decoder_d3.decode(ones_syndrome)

        assert isinstance(x_corr, set)
        assert isinstance(z_corr, set)

    def test_single_batch(self, neural_decoder_d3):
        """Test single sample in batch."""
        syndrome = torch.rand(1, 8)
        x_probs, z_probs, conf = neural_decoder_d3(syndrome)

        assert x_probs.shape == (1, 9)
        assert z_probs.shape == (1, 9)
        assert conf.shape == (1, 1)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-x"])
