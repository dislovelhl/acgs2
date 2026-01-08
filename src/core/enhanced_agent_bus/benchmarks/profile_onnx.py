#!/usr/bin/env python3
"""
ACGS-2 ONNX Inference Profiler
Constitutional Hash: profile_baseline_v1

Profiles baseline ONNX inference to identify performance bottlenecks causing:
- 25.24ms P99 latency (target: <5ms)
- 798.6% CPU usage

Usage:
    python src/core/enhanced_agent_bus/benchmarks/profile_onnx.py

Output:
    Profile report with memory/CPU metrics identifying:
    1. Memory allocation hotspots
    2. CPU-bound operations
    3. Tokenization overhead vs inference overhead
    4. Batch size impact on throughput
"""

import cProfile
import io
import logging
import pstats
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add parent directories to path for imports
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Availability flags (following tensorrt_optimizer.py pattern)
ONNX_AVAILABLE = False
TRANSFORMERS_AVAILABLE = False
MEMORY_PROFILER_AVAILABLE = False
TRACEMALLOC_AVAILABLE = False

try:
    import onnxruntime as ort

    ONNX_AVAILABLE = True
except ImportError:
    logger.warning("onnxruntime not available - ONNX profiling will be limited")

try:
    from transformers import AutoTokenizer

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    logger.warning("transformers not available - tokenization profiling will be limited")

try:
    from memory_profiler import memory_usage

    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    logger.warning("memory_profiler not available - memory profiling will use tracemalloc")

try:
    import tracemalloc

    TRACEMALLOC_AVAILABLE = True
except ImportError:
    logger.warning("tracemalloc not available - memory profiling disabled")


@dataclass
class ProfilingMetrics:
    """Container for profiling metrics."""

    operation: str
    latency_ms: List[float] = field(default_factory=list)
    memory_mb: List[float] = field(default_factory=list)
    cpu_time_ms: float = 0.0
    call_count: int = 0

    @property
    def latency_p50(self) -> float:
        if not self.latency_ms:
            return 0.0
        return statistics.median(self.latency_ms)

    @property
    def latency_p95(self) -> float:
        if not self.latency_ms:
            return 0.0
        return np.percentile(self.latency_ms, 95)

    @property
    def latency_p99(self) -> float:
        if not self.latency_ms:
            return 0.0
        return np.percentile(self.latency_ms, 99)

    @property
    def latency_mean(self) -> float:
        if not self.latency_ms:
            return 0.0
        return statistics.mean(self.latency_ms)

    @property
    def memory_peak_mb(self) -> float:
        if not self.memory_mb:
            return 0.0
        return max(self.memory_mb)

    @property
    def memory_mean_mb(self) -> float:
        if not self.memory_mb:
            return 0.0
        return statistics.mean(self.memory_mb)


class ONNXProfiler:
    """
    Profiles ONNX Runtime inference to identify bottlenecks.

    Profiling Pipeline:
    1. Tokenization profiling (transformers overhead)
    2. ONNX session creation profiling
    3. Inference profiling (per-operation breakdown)
    4. Memory allocation tracking
    5. Batch size scaling analysis

    Expected Output:
    - Root cause identification (tokenization vs inference vs memory)
    - Optimization recommendations
    """

    MODEL_NAME = "distilbert-base-uncased"
    MAX_SEQ_LENGTH = 128
    DEFAULT_MODEL_DIR = Path(__file__).parent.parent / "deliberation_layer" / "optimized_models"

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        max_seq_length: int = MAX_SEQ_LENGTH,
        model_dir: Optional[Path] = None,
    ):
        """
        Initialize ONNX profiler.

        Args:
            model_name: HuggingFace model name for tokenizer
            max_seq_length: Maximum sequence length for inference
            model_dir: Directory containing ONNX model files
        """
        self.model_name = model_name
        self.max_seq_length = max_seq_length
        self.model_dir = model_dir or self.DEFAULT_MODEL_DIR

        # Lazy-loaded components
        self._tokenizer = None
        self._onnx_session = None

        # Profiling results
        self.metrics: Dict[str, ProfilingMetrics] = {}

        # Sample test data
        self.sample_texts = [
            "Critical security breach detected in blockchain consensus layer",
            "Standard health check request",
            "Unauthorized financial transfer attempt blocked",
            "Performance metrics indicate potential anomaly",
            "User requested password reset",
            "System configuration change detected in production environment",
            "Routine database backup completed successfully",
            "New API endpoint deployment initiated",
            "Network traffic spike observed on main gateway",
            "Authentication failure for admin account after 5 attempts",
        ]

    def _get_onnx_path(self) -> Path:
        """Get path to ONNX model file."""
        model_id = self.model_name.replace("/", "_").replace("-", "_")
        return self.model_dir / f"{model_id}.onnx"

    def _load_tokenizer(self):
        """Load HuggingFace tokenizer with timing."""
        if self._tokenizer is None:
            if not TRANSFORMERS_AVAILABLE:
                logger.warning("Transformers not available - using mock tokenizer")
                return None

            start = time.perf_counter()
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(f"Tokenizer loaded in {elapsed_ms:.2f}ms")

        return self._tokenizer

    def _load_onnx_session(self) -> Optional[ort.InferenceSession]:
        """Load ONNX Runtime session with timing."""
        if self._onnx_session is None:
            if not ONNX_AVAILABLE:
                logger.warning("ONNX Runtime not available")
                return None

            onnx_path = self._get_onnx_path()
            if not onnx_path.exists():
                logger.warning(f"ONNX model not found at: {onnx_path}")
                logger.info("Run export_onnx() from tensorrt_optimizer.py first")
                return None

            # Configure ONNX Runtime with CPU provider
            providers = ["CPUExecutionProvider"]
            if "CUDAExecutionProvider" in ort.get_available_providers():
                providers.insert(0, "CUDAExecutionProvider")
                logger.info("CUDA provider available")

            start = time.perf_counter()
            self._onnx_session = ort.InferenceSession(
                str(onnx_path),
                providers=providers,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(f"ONNX session loaded in {elapsed_ms:.2f}ms")

        return self._onnx_session

    def _tokenize(self, texts: List[str]) -> Dict[str, np.ndarray]:
        """Tokenize texts with timing."""
        tokenizer = self._load_tokenizer()
        if tokenizer is None:
            # Mock tokenization for testing without transformers
            batch_size = len(texts)
            return {
                "input_ids": np.ones((batch_size, self.max_seq_length), dtype=np.int64),
                "attention_mask": np.ones((batch_size, self.max_seq_length), dtype=np.int64),
            }

        inputs = tokenizer(
            texts,
            padding="max_length",
            truncation=True,
            max_length=self.max_seq_length,
            return_tensors="np",
        )
        return {k: v for k, v in inputs.items()}

    def _infer_onnx(self, inputs: Dict[str, np.ndarray]) -> np.ndarray:
        """Run ONNX inference."""
        session = self._load_onnx_session()
        if session is None:
            # Mock output for testing without ONNX
            batch_size = inputs["input_ids"].shape[0]
            return np.zeros((batch_size, 768), dtype=np.float32)

        input_feed = {
            "input_ids": inputs["input_ids"],
            "attention_mask": inputs["attention_mask"],
        }

        outputs = session.run(None, input_feed)

        # Mean pooling (following tensorrt_optimizer.py pattern)
        last_hidden_state = outputs[0]
        attention_mask = inputs["attention_mask"]

        input_mask_expanded = np.broadcast_to(
            attention_mask[:, :, np.newaxis], last_hidden_state.shape
        ).astype(np.float32)

        sum_embeddings = np.sum(last_hidden_state * input_mask_expanded, axis=1)
        sum_mask = np.clip(input_mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)

        return sum_embeddings / sum_mask

    def profile_tokenization(self, num_iterations: int = 100) -> ProfilingMetrics:
        """
        Profile tokenization overhead.

        Args:
            num_iterations: Number of iterations for timing

        Returns:
            ProfilingMetrics for tokenization
        """
        logger.info(f"Profiling tokenization ({num_iterations} iterations)...")

        metrics = ProfilingMetrics(operation="tokenization")

        # Warm up tokenizer
        self._load_tokenizer()

        for i in range(num_iterations):
            text = self.sample_texts[i % len(self.sample_texts)]

            start = time.perf_counter()
            self._tokenize([text])
            elapsed_ms = (time.perf_counter() - start) * 1000

            metrics.latency_ms.append(elapsed_ms)
            metrics.call_count += 1

        self.metrics["tokenization"] = metrics
        logger.info(
            f"Tokenization: P50={metrics.latency_p50:.2f}ms, P99={metrics.latency_p99:.2f}ms"
        )

        return metrics

    def profile_inference(self, num_iterations: int = 100) -> ProfilingMetrics:
        """
        Profile ONNX inference.

        Args:
            num_iterations: Number of iterations for timing

        Returns:
            ProfilingMetrics for inference
        """
        logger.info(f"Profiling ONNX inference ({num_iterations} iterations)...")

        metrics = ProfilingMetrics(operation="onnx_inference")

        # Warm up session
        self._load_onnx_session()

        # Pre-tokenize to isolate inference time
        pre_tokenized = [self._tokenize([text]) for text in self.sample_texts]

        for i in range(num_iterations):
            inputs = pre_tokenized[i % len(pre_tokenized)]

            start = time.perf_counter()
            self._infer_onnx(inputs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            metrics.latency_ms.append(elapsed_ms)
            metrics.call_count += 1

        self.metrics["onnx_inference"] = metrics
        logger.info(
            f"ONNX Inference: P50={metrics.latency_p50:.2f}ms, P99={metrics.latency_p99:.2f}ms"
        )

        return metrics

    def profile_end_to_end(self, num_iterations: int = 100) -> ProfilingMetrics:
        """
        Profile end-to-end inference (tokenization + inference).

        Args:
            num_iterations: Number of iterations for timing

        Returns:
            ProfilingMetrics for end-to-end
        """
        logger.info(f"Profiling end-to-end inference ({num_iterations} iterations)...")

        metrics = ProfilingMetrics(operation="end_to_end")

        # Warm up
        self._load_tokenizer()
        self._load_onnx_session()

        for i in range(num_iterations):
            text = self.sample_texts[i % len(self.sample_texts)]

            start = time.perf_counter()
            inputs = self._tokenize([text])
            self._infer_onnx(inputs)
            elapsed_ms = (time.perf_counter() - start) * 1000

            metrics.latency_ms.append(elapsed_ms)
            metrics.call_count += 1

        self.metrics["end_to_end"] = metrics
        logger.info(f"End-to-End: P50={metrics.latency_p50:.2f}ms, P99={metrics.latency_p99:.2f}ms")

        return metrics

    def profile_batch_scaling(self, batch_sizes: List[int] = None) -> Dict[int, ProfilingMetrics]:
        """
        Profile batch size impact on throughput.

        Args:
            batch_sizes: List of batch sizes to test

        Returns:
            Dict mapping batch_size to ProfilingMetrics
        """
        if batch_sizes is None:
            batch_sizes = [1, 2, 4, 8, 16, 32]

        logger.info(f"Profiling batch scaling: {batch_sizes}...")

        results = {}

        for batch_size in batch_sizes:
            metrics = ProfilingMetrics(operation=f"batch_{batch_size}")

            # Create batched input
            texts = self.sample_texts[:batch_size]
            if len(texts) < batch_size:
                texts = texts * (batch_size // len(texts) + 1)
                texts = texts[:batch_size]

            # Pre-tokenize
            inputs = self._tokenize(texts)

            # Warm up
            self._infer_onnx(inputs)

            # Profile
            num_iterations = 50
            for _ in range(num_iterations):
                start = time.perf_counter()
                self._infer_onnx(inputs)
                elapsed_ms = (time.perf_counter() - start) * 1000

                metrics.latency_ms.append(elapsed_ms)
                metrics.call_count += 1

            results[batch_size] = metrics
            throughput = (
                (batch_size * 1000) / metrics.latency_mean if metrics.latency_mean > 0 else 0
            )
            logger.info(
                f"Batch {batch_size}: P50={metrics.latency_p50:.2f}ms, "
                f"throughput={throughput:.1f} req/sec"
            )

        self.metrics["batch_scaling"] = results
        return results

    def profile_memory(self) -> Dict[str, float]:
        """
        Profile memory usage during inference.

        Returns:
            Dict with memory metrics
        """
        logger.info("Profiling memory usage...")

        memory_results = {}

        if TRACEMALLOC_AVAILABLE:
            import tracemalloc

            # Profile session creation
            tracemalloc.start()
            self._onnx_session = None  # Reset
            self._load_onnx_session()
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            memory_results["session_creation_mb"] = peak / (1024 * 1024)
            logger.info(f"Session creation peak memory: {peak / (1024 * 1024):.2f} MB")

            # Profile inference
            inputs = self._tokenize(["Test input for memory profiling"])

            tracemalloc.start()
            for _ in range(10):
                self._infer_onnx(inputs)
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            memory_results["inference_peak_mb"] = peak / (1024 * 1024)
            logger.info(f"Inference peak memory: {peak / (1024 * 1024):.2f} MB")

        if MEMORY_PROFILER_AVAILABLE:
            # More accurate memory profiling with memory_profiler
            def run_inference():
                inputs = self._tokenize(["Test input"])
                for _ in range(10):
                    self._infer_onnx(inputs)

            mem_usage = memory_usage(run_inference, interval=0.1, max_iterations=1)
            memory_results["memory_profiler_peak_mb"] = max(mem_usage)
            memory_results["memory_profiler_mean_mb"] = statistics.mean(mem_usage)
            logger.info(f"memory_profiler peak: {max(mem_usage):.2f} MB")

        self.metrics["memory"] = memory_results
        return memory_results

    def profile_cpu_cprofile(self) -> str:
        """
        Profile CPU usage with cProfile.

        Returns:
            Formatted cProfile statistics string
        """
        logger.info("Profiling CPU with cProfile...")

        profiler = cProfile.Profile()

        # Profile end-to-end workflow
        profiler.enable()

        for i in range(50):
            text = self.sample_texts[i % len(self.sample_texts)]
            inputs = self._tokenize([text])
            self._infer_onnx(inputs)

        profiler.disable()

        # Format results
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats("cumulative")
        stats.print_stats(30)  # Top 30 functions

        cpu_profile = stream.getvalue()
        self.metrics["cpu_profile"] = cpu_profile

        return cpu_profile

    def generate_report(self) -> str:
        """
        Generate comprehensive profiling report.

        Returns:
            Formatted report string
        """
        report_lines = [
            "=" * 70,
            "ACGS-2 ONNX INFERENCE PROFILING REPORT",
            "=" * 70,
            "",
            f"Model: {self.model_name}",
            f"Max Sequence Length: {self.max_seq_length}",
            f"ONNX Path: {self._get_onnx_path()}",
            "",
            "-" * 70,
            "AVAILABILITY STATUS",
            "-" * 70,
            f"ONNX Runtime: {'Available' if ONNX_AVAILABLE else 'NOT AVAILABLE'}",
            f"Transformers: {'Available' if TRANSFORMERS_AVAILABLE else 'NOT AVAILABLE'}",
            f"memory_profiler: {'Available' if MEMORY_PROFILER_AVAILABLE else 'NOT AVAILABLE'}",
            f"tracemalloc: {'Available' if TRACEMALLOC_AVAILABLE else 'NOT AVAILABLE'}",
            "",
        ]

        # Latency metrics
        if "tokenization" in self.metrics:
            m = self.metrics["tokenization"]
            report_lines.extend(
                [
                    "-" * 70,
                    "TOKENIZATION LATENCY",
                    "-" * 70,
                    f"P50: {m.latency_p50:.2f} ms",
                    f"P95: {m.latency_p95:.2f} ms",
                    f"P99: {m.latency_p99:.2f} ms",
                    f"Mean: {m.latency_mean:.2f} ms",
                    f"Samples: {m.call_count}",
                    "",
                ]
            )

        if "onnx_inference" in self.metrics:
            m = self.metrics["onnx_inference"]
            report_lines.extend(
                [
                    "-" * 70,
                    "ONNX INFERENCE LATENCY",
                    "-" * 70,
                    f"P50: {m.latency_p50:.2f} ms",
                    f"P95: {m.latency_p95:.2f} ms",
                    f"P99: {m.latency_p99:.2f} ms",
                    f"Mean: {m.latency_mean:.2f} ms",
                    f"Samples: {m.call_count}",
                    "",
                ]
            )

        if "end_to_end" in self.metrics:
            m = self.metrics["end_to_end"]
            report_lines.extend(
                [
                    "-" * 70,
                    "END-TO-END LATENCY (Tokenization + Inference)",
                    "-" * 70,
                    f"P50: {m.latency_p50:.2f} ms",
                    f"P95: {m.latency_p95:.2f} ms",
                    f"P99: {m.latency_p99:.2f} ms  {'[BASELINE: 25.24ms]' if m.latency_p99 > 0 else ''}",
                    f"Mean: {m.latency_mean:.2f} ms",
                    f"Samples: {m.call_count}",
                    "",
                ]
            )

        # Batch scaling
        if "batch_scaling" in self.metrics:
            batch_results = self.metrics["batch_scaling"]
            report_lines.extend(
                [
                    "-" * 70,
                    "BATCH SIZE SCALING",
                    "-" * 70,
                    f"{'Batch':<8} {'P50 (ms)':<12} {'P99 (ms)':<12} {'Throughput (req/s)':<20}",
                    "-" * 52,
                ]
            )
            for batch_size, m in batch_results.items():
                throughput = (batch_size * 1000) / m.latency_mean if m.latency_mean > 0 else 0
                report_lines.append(
                    f"{batch_size:<8} {m.latency_p50:<12.2f} {m.latency_p99:<12.2f} {throughput:<20.1f}"
                )
            report_lines.append("")

        # Memory metrics
        if "memory" in self.metrics:
            mem = self.metrics["memory"]
            report_lines.extend(
                [
                    "-" * 70,
                    "MEMORY USAGE",
                    "-" * 70,
                ]
            )
            for key, value in mem.items():
                report_lines.append(f"{key}: {value:.2f} MB")
            report_lines.append("")

        # Analysis and recommendations
        report_lines.extend(
            [
                "-" * 70,
                "BOTTLENECK ANALYSIS",
                "-" * 70,
            ]
        )

        # Analyze bottlenecks
        if "tokenization" in self.metrics and "onnx_inference" in self.metrics:
            tok_latency = self.metrics["tokenization"].latency_mean
            inf_latency = self.metrics["onnx_inference"].latency_mean
            total = tok_latency + inf_latency

            if total > 0:
                tok_pct = (tok_latency / total) * 100
                inf_pct = (inf_latency / total) * 100

                report_lines.extend(
                    [
                        f"Tokenization overhead: {tok_pct:.1f}%",
                        f"Inference overhead: {inf_pct:.1f}%",
                        "",
                    ]
                )

                if tok_pct > 50:
                    report_lines.append(">>> BOTTLENECK: Tokenization is the primary bottleneck")
                    report_lines.append(
                        "    Recommendation: Cache tokenizer, use batch tokenization"
                    )
                else:
                    report_lines.append(">>> BOTTLENECK: ONNX inference is the primary bottleneck")
                    report_lines.append("    Recommendation: Use TensorRT, optimize batch size")
        else:
            report_lines.append("Insufficient data for bottleneck analysis - run full profiling")

        report_lines.extend(
            [
                "",
                "-" * 70,
                "OPTIMIZATION RECOMMENDATIONS",
                "-" * 70,
                "1. Enable tokenizer caching (avoid repeated initialization)",
                "2. Use batch inference for high-throughput scenarios",
                "3. Consider TensorRT conversion for GPU acceleration",
                "4. Implement lazy loading for ONNX session",
                "5. Pre-warmup inference to avoid cold-start latency",
                "",
                "=" * 70,
                "END OF REPORT",
                "=" * 70,
            ]
        )

        # CPU profile (truncated)
        if "cpu_profile" in self.metrics:
            report_lines.extend(
                [
                    "",
                    "-" * 70,
                    "CPU PROFILE (Top 30 Functions)",
                    "-" * 70,
                    self.metrics["cpu_profile"][:5000],  # Truncate for readability
                ]
            )

        return "\n".join(report_lines)

    def run_full_profile(self) -> str:
        """
        Run complete profiling suite and generate report.

        Returns:
            Formatted profiling report
        """
        logger.info("Starting full ONNX profiling suite...")

        # Run all profiles
        self.profile_tokenization()
        self.profile_inference()
        self.profile_end_to_end()
        self.profile_batch_scaling()
        self.profile_memory()
        self.profile_cpu_cprofile()

        # Generate report
        report = self.generate_report()

        return report


def main():
    """Main entry point for ONNX profiling."""
    logger.info("ACGS-2 ONNX Inference Profiler")
    logger.info("=" * 50)

    # Create profiler
    profiler = ONNXProfiler()

    # Run profiling
    report = profiler.run_full_profile()

    # Output report

    # Save report to file
    output_dir = SCRIPT_DIR
    report_path = output_dir / "profile_report.txt"

    with open(report_path, "w") as f:
        f.write(report)

    logger.info(f"Profile report saved to: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
