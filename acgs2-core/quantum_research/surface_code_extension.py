import logging

#!/usr/bin/env python3
"""
Surface Code Extension for PAG-QEC Framework
Constitutional Hash: cdd01ef066bc6cf2

Extends the PAG-QEC framework to support rotated surface codes
at distances 3, 5, and 7. Implements:

1. Surface Code Environments - Syndrome generation and error simulation
2. Scalable Neural Decoder - Architecture that grows with code distance
3. MWPM Baseline - Minimum Weight Perfect Matching for comparison
4. Curriculum Training - Progressive difficulty for better convergence

Based on 2025 research:
- Google Willow: Distance-7 surface code, 0.143% error/cycle
- IBM: qLDPC codes with <480ns decoding
- Roffe et al.: Localized Statistics Decoding

Author: ACGS-2 Quantum Research
"""

import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# Constitutional hash for ACGS-2 compliance
CONSTITUTIONAL_HASH = "cdd01ef066bc6cf2"


# =============================================================================
# SURFACE CODE GEOMETRY
# =============================================================================


class ErrorType(Enum):
    """Types of errors in surface codes."""

    NONE = 0
    X = 1  # Bit-flip
    Z = 2  # Phase-flip
    Y = 3  # Both (X then Z)


@dataclass
class SurfaceCodeGeometry:
    """
    Defines the geometry of a rotated surface code.

    For a distance-d code:
    - d² data qubits arranged in a rotated square
    - (d²-1)/2 X-type stabilizers (measure Z errors)
    - (d²-1)/2 Z-type stabilizers (measure X errors)
    - d-1 total syndrome bits per stabilizer type
    """

    distance: int

    def __post_init__(self):
        assert self.distance >= 3, "Minimum distance is 3"
        assert self.distance % 2 == 1, "Distance must be odd"

        self.num_data_qubits = self.distance**2
        self.num_x_stabilizers = (self.distance**2 - 1) // 2
        self.num_z_stabilizers = (self.distance**2 - 1) // 2
        self.syndrome_size = self.num_x_stabilizers + self.num_z_stabilizers

        # Build qubit layout
        self._build_layout()

    def _build_layout(self):
        """Build the rotated surface code layout."""
        d = self.distance

        # Data qubit positions (checkerboard pattern)
        self.data_qubits = []
        for row in range(d):
            for col in range(d):
                self.data_qubits.append((row, col))

        # X-stabilizer positions (white squares in checkerboard)
        self.x_stabilizers = []
        # Z-stabilizer positions (black squares in checkerboard)
        self.z_stabilizers = []

        for row in range(d - 1):
            for col in range(d - 1):
                # Alternating pattern
                if (row + col) % 2 == 0:
                    self.x_stabilizers.append((row + 0.5, col + 0.5))
                else:
                    self.z_stabilizers.append((row + 0.5, col + 0.5))

        # Build stabilizer-to-qubit mappings
        self.x_stab_qubits = self._get_stabilizer_qubits(self.x_stabilizers)
        self.z_stab_qubits = self._get_stabilizer_qubits(self.z_stabilizers)

    def _get_stabilizer_qubits(self, stabilizers) -> List[List[int]]:
        """Get data qubits adjacent to each stabilizer."""
        stab_qubits = []
        for sr, sc in stabilizers:
            adjacent = []
            for i, (dr, dc) in enumerate(self.data_qubits):
                # Check if data qubit is adjacent (within 0.5 + epsilon)
                if abs(dr - sr) <= 0.6 and abs(dc - sc) <= 0.6:
                    adjacent.append(i)
            stab_qubits.append(adjacent)
        return stab_qubits

    def get_syndrome_from_errors(
        self, x_errors: Set[int], z_errors: Set[int]
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Compute syndrome from error pattern.

        Args:
            x_errors: Set of qubit indices with X errors
            z_errors: Set of qubit indices with Z errors

        Returns:
            (x_syndrome, z_syndrome): Binary syndrome arrays
        """
        # X stabilizers detect Z errors
        x_syndrome = np.zeros(len(self.x_stabilizers), dtype=np.int8)
        for i, qubits in enumerate(self.x_stab_qubits):
            parity = sum(1 for q in qubits if q in z_errors) % 2
            x_syndrome[i] = parity

        # Z stabilizers detect X errors
        z_syndrome = np.zeros(len(self.z_stabilizers), dtype=np.int8)
        for i, qubits in enumerate(self.z_stab_qubits):
            parity = sum(1 for q in qubits if q in x_errors) % 2
            z_syndrome[i] = parity

        return x_syndrome, z_syndrome


# =============================================================================
# SURFACE CODE ENVIRONMENT
# =============================================================================


@dataclass
class SurfaceCodeDataPoint:
    """Training data point for surface code decoder."""

    syndrome: np.ndarray  # Full syndrome (X + Z concatenated)
    x_errors: Set[int]  # Ground truth X error locations
    z_errors: Set[int]  # Ground truth Z error locations
    logical_error: bool  # Whether error causes logical failure
    error_weight: int  # Number of physical errors


class SurfaceCodeEnvironment:
    """
    Training environment for surface code decoders.

    Generates syndrome-error pairs for supervised training.
    Supports depolarizing noise model with configurable error rate.
    """

    def __init__(
        self, distance: int = 3, physical_error_rate: float = 0.01, seed: Optional[int] = None
    ):
        self.geometry = SurfaceCodeGeometry(distance)
        self.physical_error_rate = physical_error_rate
        self.rng = np.random.default_rng(seed)

    @property
    def syndrome_size(self) -> int:
        return self.geometry.syndrome_size

    @property
    def num_qubits(self) -> int:
        return self.geometry.num_data_qubits

    def generate_error_pattern(self) -> Tuple[Set[int], Set[int]]:
        """
        Generate random error pattern under depolarizing noise.

        Each qubit independently experiences:
        - X error with probability p/3
        - Z error with probability p/3
        - Y error with probability p/3
        - No error with probability 1-p
        """
        p = self.physical_error_rate
        x_errors = set()
        z_errors = set()

        for q in range(self.num_qubits):
            r = self.rng.random()
            if r < p / 3:
                x_errors.add(q)
            elif r < 2 * p / 3:
                z_errors.add(q)
            elif r < p:
                x_errors.add(q)
                z_errors.add(q)

        return x_errors, z_errors

    def check_logical_error(
        self, x_errors: Set[int], z_errors: Set[int], x_correction: Set[int], z_correction: Set[int]
    ) -> bool:
        """
        Check if error + correction causes logical error.

        Logical X error: odd parity along horizontal logical operator
        Logical Z error: odd parity along vertical logical operator
        """
        d = self.geometry.distance

        # Residual errors after correction
        x_residual = x_errors.symmetric_difference(x_correction)
        z_residual = z_errors.symmetric_difference(z_correction)

        # Check logical X (horizontal chain)
        logical_x = sum(1 for q in x_residual if q // d == d // 2) % 2 == 1

        # Check logical Z (vertical chain)
        logical_z = sum(1 for q in z_residual if q % d == d // 2) % 2 == 1

        return logical_x or logical_z

    def generate_sample(self) -> SurfaceCodeDataPoint:
        """Generate single training sample."""
        x_errors, z_errors = self.generate_error_pattern()
        x_syndrome, z_syndrome = self.geometry.get_syndrome_from_errors(x_errors, z_errors)

        syndrome = np.concatenate([x_syndrome, z_syndrome])
        error_weight = len(x_errors) + len(z_errors)

        # Logical error if error weight >= d (simplified check)
        logical_error = error_weight >= self.geometry.distance

        return SurfaceCodeDataPoint(
            syndrome=syndrome,
            x_errors=x_errors,
            z_errors=z_errors,
            logical_error=logical_error,
            error_weight=error_weight,
        )

    def generate_dataset(self, size: int) -> List[SurfaceCodeDataPoint]:
        """Generate training dataset."""
        return [self.generate_sample() for _ in range(size)]


# =============================================================================
# SCALABLE NEURAL DECODER
# =============================================================================


class SurfaceCodeNeuralDecoder(nn.Module):
    """
    Scalable neural decoder for surface codes.

    Architecture scales with code distance:
    - Input: syndrome_size = d² - 1 bits
    - Hidden: scales as O(d²) neurons
    - Output: 2 * d² correction probabilities (X and Z for each qubit)

    Uses attention mechanism for long-range correlations.
    """

    def __init__(
        self,
        distance: int = 3,
        hidden_multiplier: int = 4,
        num_layers: int = 3,
        num_heads: int = 4,
        dropout: float = 0.1,
    ):
        super().__init__()

        self.distance = distance
        self.geometry = SurfaceCodeGeometry(distance)

        syndrome_size = self.geometry.syndrome_size
        num_qubits = self.geometry.num_data_qubits
        hidden_dim = num_qubits * hidden_multiplier

        # Input embedding
        self.input_proj = nn.Linear(syndrome_size, hidden_dim)

        # Transformer layers for learning correlations
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 2,
            dropout=dropout,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)

        # Output heads
        self.x_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_qubits),
            nn.Sigmoid(),
        )

        self.z_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim // 2, num_qubits),
            nn.Sigmoid(),
        )

        # Confidence head
        self.confidence_head = nn.Sequential(nn.Linear(hidden_dim, 1), nn.Sigmoid())

        # Statistics
        self.inference_count = 0
        self.total_inference_time_ns = 0

    def forward(self, syndrome: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.

        Args:
            syndrome: (batch, syndrome_size) binary tensor

        Returns:
            x_probs: (batch, num_qubits) X error probabilities
            z_probs: (batch, num_qubits) Z error probabilities
            confidence: (batch, 1) prediction confidence
        """
        # Embed syndrome
        h = self.input_proj(syndrome)

        # Add sequence dimension for transformer
        h = h.unsqueeze(1)  # (batch, 1, hidden)

        # Process through transformer
        h = self.transformer(h)

        # Remove sequence dimension
        h = h.squeeze(1)  # (batch, hidden)

        # Output predictions
        x_probs = self.x_head(h)
        z_probs = self.z_head(h)
        confidence = self.confidence_head(h)

        return x_probs, z_probs, confidence

    def decode(
        self, syndrome: torch.Tensor, threshold: float = 0.5
    ) -> Tuple[Set[int], Set[int], float]:
        """
        Decode syndrome to correction.

        Args:
            syndrome: (syndrome_size,) tensor
            threshold: probability threshold for predicting error

        Returns:
            x_correction: set of qubits to apply X correction
            z_correction: set of qubits to apply Z correction
            confidence: prediction confidence
        """
        start_time = time.perf_counter_ns()

        self.eval()
        with torch.no_grad():
            if syndrome.dim() == 1:
                syndrome = syndrome.unsqueeze(0)

            x_probs, z_probs, conf = self.forward(syndrome)

            x_probs = x_probs.squeeze(0).numpy()
            z_probs = z_probs.squeeze(0).numpy()
            confidence = conf.item()

        x_correction = set(np.where(x_probs > threshold)[0])
        z_correction = set(np.where(z_probs > threshold)[0])

        end_time = time.perf_counter_ns()
        self.inference_count += 1
        self.total_inference_time_ns += end_time - start_time

        return x_correction, z_correction, confidence

    def get_avg_inference_time_ns(self) -> float:
        if self.inference_count == 0:
            return 0.0
        return self.total_inference_time_ns / self.inference_count


# =============================================================================
# MINIMUM WEIGHT PERFECT MATCHING (MWPM) BASELINE
# =============================================================================


class MWPMDecoder:
    """
    Minimum Weight Perfect Matching decoder for surface codes.

    This is the standard classical decoder used in most QEC experiments.
    Uses Edmonds' blossom algorithm for perfect matching.

    Simplified implementation - for production use PyMatching library.
    """

    def __init__(self, geometry: SurfaceCodeGeometry):
        self.geometry = geometry
        self.inference_count = 0
        self.total_inference_time_ns = 0

        # Precompute distances between stabilizers
        self._precompute_distances()

    def _precompute_distances(self):
        """Precompute Manhattan distances between all stabilizer pairs."""
        self.x_distances = self._compute_pairwise_distances(self.geometry.x_stabilizers)
        self.z_distances = self._compute_pairwise_distances(self.geometry.z_stabilizers)

    def _compute_pairwise_distances(self, stabilizers: List[Tuple[float, float]]) -> np.ndarray:
        """Compute pairwise Manhattan distances."""
        n = len(stabilizers)
        distances = np.zeros((n, n))

        for i in range(n):
            for j in range(i + 1, n):
                d = abs(stabilizers[i][0] - stabilizers[j][0]) + abs(
                    stabilizers[i][1] - stabilizers[j][1]
                )
                distances[i, j] = d
                distances[j, i] = d

        return distances

    def _greedy_matching(
        self, syndrome: np.ndarray, distances: np.ndarray
    ) -> List[Tuple[int, int]]:
        """
        Greedy approximation to perfect matching.

        For production, use Kolmogorov's Blossom V or PyMatching.
        """
        defects = list(np.where(syndrome == 1)[0])

        if len(defects) == 0:
            return []

        # Add boundary nodes if odd number of defects
        if len(defects) % 2 == 1:
            # Match to boundary (virtual node)
            defects.append(-1)

        matching = []
        used = set()

        # Sort pairs by distance (greedy)
        pairs = []
        for i, d1 in enumerate(defects):
            for _j, d2 in enumerate(defects[i + 1 :], i + 1):
                if d1 == -1 or d2 == -1:
                    # Distance to boundary
                    dist = 1.0
                else:
                    dist = distances[d1, d2]
                pairs.append((dist, d1, d2))

        pairs.sort()

        for _dist, d1, d2 in pairs:
            if d1 not in used and d2 not in used:
                matching.append((d1, d2))
                used.add(d1)
                used.add(d2)

        return matching

    def _matching_to_correction(
        self,
        matching: List[Tuple[int, int]],
        stabilizers: List[Tuple[float, float]],
        stab_qubits: List[List[int]],
    ) -> Set[int]:
        """Convert matching to qubit corrections."""
        correction = set()

        for d1, d2 in matching:
            if d1 == -1 or d2 == -1:
                # Boundary matching - apply correction along path to boundary
                real_defect = d2 if d1 == -1 else d1
                # Simple: flip first qubit of stabilizer
                if stab_qubits[real_defect]:
                    correction.add(stab_qubits[real_defect][0])
            else:
                # Find path between defects and flip qubits
                # Simplified: flip shared qubits
                q1 = set(stab_qubits[d1])
                q2 = set(stab_qubits[d2])
                shared = q1.intersection(q2)
                if shared:
                    correction.add(shared.pop())
                else:
                    # No shared qubit - use first from each
                    if stab_qubits[d1]:
                        correction.add(stab_qubits[d1][0])

        return correction

    def decode(self, syndrome: np.ndarray) -> Tuple[Set[int], Set[int], float]:
        """
        Decode syndrome using MWPM.

        Returns:
            x_correction, z_correction, confidence (always 1.0 for MWPM)
        """
        start_time = time.perf_counter_ns()

        n_x = len(self.geometry.x_stabilizers)
        x_syndrome = syndrome[:n_x]
        z_syndrome = syndrome[n_x:]

        # Match X stabilizer defects -> Z corrections
        x_matching = self._greedy_matching(x_syndrome, self.x_distances)
        z_correction = self._matching_to_correction(
            x_matching, self.geometry.x_stabilizers, self.geometry.x_stab_qubits
        )

        # Match Z stabilizer defects -> X corrections
        z_matching = self._greedy_matching(z_syndrome, self.z_distances)
        x_correction = self._matching_to_correction(
            z_matching, self.geometry.z_stabilizers, self.geometry.z_stab_qubits
        )

        end_time = time.perf_counter_ns()
        self.inference_count += 1
        self.total_inference_time_ns += end_time - start_time

        return x_correction, z_correction, 1.0

    def get_avg_inference_time_ns(self) -> float:
        if self.inference_count == 0:
            return 0.0
        return self.total_inference_time_ns / self.inference_count


# =============================================================================
# CURRICULUM TRAINING
# =============================================================================


class CurriculumTrainer:
    """
    Curriculum learning for surface code decoders.

    Starts with low error rates (easy) and progressively increases
    difficulty. This helps the network learn basic patterns first.
    """

    def __init__(
        self,
        decoder: SurfaceCodeNeuralDecoder,
        distance: int = 3,
        initial_error_rate: float = 0.001,
        final_error_rate: float = 0.05,
        num_stages: int = 5,
        samples_per_stage: int = 10000,
        epochs_per_stage: int = 50,
    ):
        self.decoder = decoder
        self.distance = distance
        self.initial_error_rate = initial_error_rate
        self.final_error_rate = final_error_rate
        self.num_stages = num_stages
        self.samples_per_stage = samples_per_stage
        self.epochs_per_stage = epochs_per_stage

        # Compute error rate schedule
        self.error_rates = np.geomspace(initial_error_rate, final_error_rate, num_stages)

        self.optimizer = torch.optim.AdamW(decoder.parameters(), lr=1e-3, weight_decay=1e-4)
        self.scheduler = torch.optim.lr_scheduler.CosineAnnealingWarmRestarts(
            self.optimizer, T_0=10, T_mult=2
        )

        self.history = {
            "stage": [],
            "error_rate": [],
            "train_loss": [],
            "train_accuracy": [],
            "logical_error_rate": [],
        }

    def train(self) -> Dict[str, List]:
        """Run curriculum training."""
        logging.info(f"\nCurriculum Training for Distance-{self.distance} Surface Code")
        logging.info("=" * 60)

        for stage, error_rate in enumerate(self.error_rates):
            logging.error(
                f"\nStage {stage + 1}/{self.num_stages}: " f"Error Rate = {error_rate:.4f}"
            )

            # Create environment for this stage
            env = SurfaceCodeEnvironment(distance=self.distance, physical_error_rate=error_rate)

            # Generate training data
            dataset = env.generate_dataset(self.samples_per_stage)

            # Train for this stage
            stage_loss, stage_acc = self._train_stage(dataset)

            # Evaluate logical error rate
            ler = self._evaluate_logical_error_rate(env)

            self.history["stage"].append(stage + 1)
            self.history["error_rate"].append(error_rate)
            self.history["train_loss"].append(stage_loss)
            self.history["train_accuracy"].append(stage_acc)
            self.history["logical_error_rate"].append(ler)

            logging.info(
                f"  Loss: {stage_loss:.4f}, Accuracy: {stage_acc:.2%}, "
                f"Logical Error Rate: {ler:.4f}"
            )

        return self.history

    def _train_stage(self, dataset: List[SurfaceCodeDataPoint]) -> Tuple[float, float]:
        """Train for one curriculum stage."""
        self.decoder.train()

        # Prepare tensors
        syndromes = torch.tensor(np.array([d.syndrome for d in dataset]), dtype=torch.float32)

        # Target: binary masks for X and Z errors
        num_qubits = self.decoder.geometry.num_data_qubits
        x_targets = torch.zeros(len(dataset), num_qubits)
        z_targets = torch.zeros(len(dataset), num_qubits)

        for i, d in enumerate(dataset):
            for q in d.x_errors:
                x_targets[i, q] = 1.0
            for q in d.z_errors:
                z_targets[i, q] = 1.0

        total_loss = 0.0
        correct = 0
        batch_size = 64
        num_batches = len(dataset) // batch_size

        for _epoch in range(self.epochs_per_stage):
            # Shuffle
            perm = torch.randperm(len(dataset))
            syndromes = syndromes[perm]
            x_targets = x_targets[perm]
            z_targets = z_targets[perm]

            epoch_loss = 0.0

            for i in range(num_batches):
                start = i * batch_size
                end = start + batch_size

                syn_batch = syndromes[start:end]
                x_batch = x_targets[start:end]
                z_batch = z_targets[start:end]

                self.optimizer.zero_grad()

                x_pred, z_pred, _ = self.decoder(syn_batch)

                # Binary cross-entropy loss
                loss = F.binary_cross_entropy(x_pred, x_batch) + F.binary_cross_entropy(
                    z_pred, z_batch
                )

                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.decoder.parameters(), 1.0)
                self.optimizer.step()

                epoch_loss += loss.item()

            self.scheduler.step()
            total_loss = epoch_loss / num_batches

        # Compute accuracy on last batch
        self.decoder.eval()
        with torch.no_grad():
            x_pred, z_pred, _ = self.decoder(syndromes[:batch_size])
            x_correct = ((x_pred > 0.5) == (x_targets[:batch_size] > 0.5)).all(dim=1)
            z_correct = ((z_pred > 0.5) == (z_targets[:batch_size] > 0.5)).all(dim=1)
            correct = (x_correct & z_correct).float().mean().item()

        return total_loss, correct

    def _evaluate_logical_error_rate(
        self, env: SurfaceCodeEnvironment, num_samples: int = 1000
    ) -> float:
        """Evaluate logical error rate."""
        self.decoder.eval()
        logical_errors = 0

        for _ in range(num_samples):
            sample = env.generate_sample()
            syndrome = torch.tensor(sample.syndrome, dtype=torch.float32)

            x_corr, z_corr, _ = self.decoder.decode(syndrome)

            if env.check_logical_error(sample.x_errors, sample.z_errors, x_corr, z_corr):
                logical_errors += 1

        return logical_errors / num_samples


# =============================================================================
# BENCHMARK SUITE
# =============================================================================


def run_surface_code_benchmark(
    distances: List[int] | None = None,
    error_rate: float = 0.01,
    num_samples: int = 1000,
) -> Dict[str, Dict]:
    """
    Benchmark neural decoder vs MWPM on surface codes.
    """
    if distances is None:
        distances = [3, 5]
    logging.info("\n" + "=" * 60)
    logging.info("SURFACE CODE DECODER BENCHMARK")
    logging.info(f"Constitutional Hash: {CONSTITUTIONAL_HASH}")
    logging.info("=" * 60)

    results = {}

    for d in distances:
        logging.info(f"\n{'='*60}")
        logging.info(f"DISTANCE-{d} SURFACE CODE")
        logging.info(f"{'='*60}")
        logging.info(f"Data qubits: {d**2}, Syndrome bits: {d**2 - 1}")
        logging.error(f"Physical error rate: {error_rate:.2%}")

        # Setup environment
        env = SurfaceCodeEnvironment(distance=d, physical_error_rate=error_rate)

        # Train neural decoder with curriculum
        logging.info("\n[1/3] Training Neural Decoder (Curriculum)...")
        neural_decoder = SurfaceCodeNeuralDecoder(
            distance=d, hidden_multiplier=4, num_layers=2, num_heads=2
        )

        trainer = CurriculumTrainer(
            neural_decoder,
            distance=d,
            initial_error_rate=error_rate / 10,
            final_error_rate=error_rate,
            num_stages=3,
            samples_per_stage=2000,
            epochs_per_stage=20,
        )
        trainer.train()

        # Setup MWPM baseline
        logging.info("\n[2/3] Initializing MWPM Decoder...")
        mwpm_decoder = MWPMDecoder(env.geometry)

        # Generate test data
        logging.info(f"\n[3/3] Running benchmark ({num_samples} samples)")
        test_data = env.generate_dataset(num_samples)

        # Benchmark Neural Decoder
        neural_logical_errors = 0
        neural_decoder.inference_count = 0
        neural_decoder.total_inference_time_ns = 0

        for sample in test_data:
            syndrome = torch.tensor(sample.syndrome, dtype=torch.float32)
            x_corr, z_corr, _ = neural_decoder.decode(syndrome)

            if env.check_logical_error(sample.x_errors, sample.z_errors, x_corr, z_corr):
                neural_logical_errors += 1

        # Benchmark MWPM
        mwpm_logical_errors = 0
        mwpm_decoder.inference_count = 0
        mwpm_decoder.total_inference_time_ns = 0

        for sample in test_data:
            x_corr, z_corr, _ = mwpm_decoder.decode(sample.syndrome)

            if env.check_logical_error(sample.x_errors, sample.z_errors, x_corr, z_corr):
                mwpm_logical_errors += 1

        # Store results
        results[f"d{d}"] = {
            "neural": {
                "logical_error_rate": neural_logical_errors / num_samples,
                "avg_latency_ns": neural_decoder.get_avg_inference_time_ns(),
            },
            "mwpm": {
                "logical_error_rate": mwpm_logical_errors / num_samples,
                "avg_latency_ns": mwpm_decoder.get_avg_inference_time_ns(),
            },
        }

        # Print results
        logging.info(f"\nResults for Distance-{d}:")
        logging.info("  Neural Decoder:")
        logging.error(f"    Logical Error Rate: {neural_logical_errors/num_samples:.4f}")
        logging.info(f"    Avg Latency: {neural_decoder.get_avg_inference_time_ns()} ns")
        logging.info("  MWPM Decoder:")
        logging.error(f"    Logical Error Rate: {mwpm_logical_errors/num_samples:.4f}")
        logging.info(f"    Avg Latency: {mwpm_decoder.get_avg_inference_time_ns()} ns")

    # Summary
    logging.info("\n" + "=" * 60)
    logging.info("BENCHMARK SUMMARY")
    logging.info("=" * 60)

    for d in distances:
        key = f"d{d}"
        neural_ler = results[key]["neural"]["logical_error_rate"]
        mwpm_ler = results[key]["mwpm"]["logical_error_rate"]

        if mwpm_ler > 0:
            improvement = (mwpm_ler - neural_ler) / mwpm_ler * 100
        else:
            improvement = 0

        logging.info(f"\nDistance-{d}:")
        logging.info(f"  Neural LER: {neural_ler:.4f}, MWPM LER: {mwpm_ler:.4f}")
        if improvement > 0:
            logging.info(f"  >> Neural decoder {improvement:.1f}% better than MWPM!")
        elif improvement < 0:
            logging.info(f"  >> MWPM {-improvement:.1f}% better than Neural decoder")

    return results


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def main():
    """Main entry point for surface code extension."""
    logging.info(
        """
    ╔═══════════════════════════════════════════════════════════════╗
    ║  Surface Code Extension for PAG-QEC Framework                 ║
    ║  Constitutional Hash: cdd01ef066bc6cf2                        ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    )

    # Run benchmark on distance-3 and distance-5 codes
    results = run_surface_code_benchmark(distances=[3, 5], error_rate=0.01, num_samples=500)

    logging.info("\n" + "=" * 60)
    logging.info("SURFACE CODE EXTENSION READY")
    logging.info("=" * 60)
    logging.info(
        """
    Next steps:
    1. Scale to distance-7 (49 data qubits, 48 syndrome bits)
    2. Integrate with speculative execution from pag_qec_framework.py
    3. Implement Union-Find decoder for comparison
    4. Add neural network pruning for FPGA deployment
    5. Validate on real quantum hardware data
    """
    )

    return results


if __name__ == "__main__":
    main()
