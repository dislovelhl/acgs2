#!/usr/bin/env python3
"""
ACGS-2 Comprehensive Performance Profiler
Constitutional Hash: cdd01ef066bc6cf2

Provides detailed performance profiling and baseline metrics for ACGS-2 system:
- P99/P95/P50 latency measurements
- Throughput (RPS) analysis
- Memory usage profiling
- CPU utilization tracking
- Cache hit rate analysis
- Bottleneck identification
"""

import asyncio
import gc
import logging
import os
import sys
import time
import tracemalloc
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None

# Import ACGS-2 components
try:
    from src.core.enhanced_agent_bus import (
        CONSTITUTIONAL_HASH,
        AgentMessage,
        EnhancedAgentBus,
        MessagePriority,
        MessageProcessor,
        MessageType,
    )

    AGENT_BUS_AVAILABLE = True
except ImportError:
    AGENT_BUS_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    # Latency metrics (milliseconds)
    latencies: List[float] = field(default_factory=list)
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    mean_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0

    # Throughput metrics
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    duration_seconds: float = 0.0
    throughput_rps: float = 0.0

    # Resource metrics
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_peak_mb: float = 0.0

    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0

    # Component-specific metrics
    component_timings: Dict[str, List[float]] = field(default_factory=dict)

    # Constitutional compliance
    constitutional_hash: str = CONSTITUTIONAL_HASH
    compliance_rate: float = 100.0


@dataclass
class BottleneckAnalysis:
    """Container for bottleneck analysis results."""

    component: str
    mean_latency_ms: float
    p99_latency_ms: float
    percentage_of_total: float
    severity: str  # 'critical', 'high', 'medium', 'low'


class PerformanceProfiler:
    """Comprehensive performance profiler for ACGS-2."""

    def __init__(self, iterations: int = 1000, warmup_iterations: int = 100):
        """Initialize profiler.

        Args:
            iterations: Number of measurement iterations
            warmup_iterations: Number of warmup iterations before measurement
        """
        self.iterations = iterations
        self.warmup_iterations = warmup_iterations
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None

    def calculate_percentiles(self, values: List[float]) -> Tuple[float, float, float]:
        """Calculate P50, P95, P99 percentiles."""
        if not values:
            return 0.0, 0.0, 0.0

        sorted_values = sorted(values)
        n = len(sorted_values)

        p50_idx = int(n * 0.50)
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)

        return (
            sorted_values[p50_idx],
            sorted_values[p95_idx],
            sorted_values[p99_idx],
        )

    def get_system_metrics(self) -> Dict[str, float]:
        """Get current system resource metrics."""
        if not PSUTIL_AVAILABLE or not self.process:
            return {
                "cpu_percent": 0.0,
                "memory_mb": 0.0,
                "memory_percent": 0.0,
            }

        return {
            "cpu_percent": self.process.cpu_percent(interval=0.1),
            "memory_mb": self.process.memory_info().rss / (1024 * 1024),
            "memory_percent": self.process.memory_percent(),
        }

    async def profile_message_processing(self) -> PerformanceMetrics:
        """Profile Enhanced Agent Bus message processing."""
        logger.info(f"[{CONSTITUTIONAL_HASH}] Profiling message processing...")

        if not AGENT_BUS_AVAILABLE:
            logger.error("Enhanced Agent Bus not available")
            return PerformanceMetrics()

        metrics = PerformanceMetrics()

        # Start memory tracking
        tracemalloc.start()
        initial_memory = tracemalloc.get_traced_memory()[0] / (1024 * 1024)

        # Initialize components
        bus = EnhancedAgentBus()
        await bus.start()

        # Warmup phase
        logger.info(f"Warmup phase: {self.warmup_iterations} iterations")
        for i in range(self.warmup_iterations):
            message = AgentMessage(
                from_agent=f"agent_{i}",
                to_agent="target_agent",
                message_type=MessageType.QUERY,
                content={"query": f"test_query_{i}"},
                priority=MessagePriority.NORMAL,
                constitutional_hash=CONSTITUTIONAL_HASH,
            )
            try:
                await bus.send_message(message)
            except Exception as e:
                logger.debug(f"Warmup iteration {i} error: {e}")

        # Measurement phase
        logger.info(f"Measurement phase: {self.iterations} iterations")
        start_time = time.perf_counter()
        start_cpu_time = time.process_time()

        for i in range(self.iterations):
            message = AgentMessage(
                from_agent=f"agent_{i}",
                to_agent="target_agent",
                message_type=MessageType.QUERY,
                content={"query": f"test_query_{i}"},
                priority=MessagePriority.NORMAL,
                constitutional_hash=CONSTITUTIONAL_HASH,
            )

            iteration_start = time.perf_counter()

            try:
                await bus.send_message(message)
                iteration_end = time.perf_counter()

                latency_ms = (iteration_end - iteration_start) * 1000
                metrics.latencies.append(latency_ms)
                metrics.successful_operations += 1

            except Exception as e:
                iteration_end = time.perf_counter()
                logger.debug(f"Iteration {i} failed: {e}")
                metrics.failed_operations += 1

        end_time = time.perf_counter()
        end_cpu_time = time.process_time()

        # Calculate metrics
        metrics.duration_seconds = end_time - start_time
        metrics.total_operations = self.iterations
        metrics.throughput_rps = metrics.successful_operations / metrics.duration_seconds

        if metrics.latencies:
            metrics.p50_latency_ms, metrics.p95_latency_ms, metrics.p99_latency_ms = (
                self.calculate_percentiles(metrics.latencies)
            )
            metrics.mean_latency_ms = sum(metrics.latencies) / len(metrics.latencies)
            metrics.min_latency_ms = min(metrics.latencies)
            metrics.max_latency_ms = max(metrics.latencies)

        # Resource metrics
        metrics.cpu_percent = (end_cpu_time - start_cpu_time) / metrics.duration_seconds * 100
        current_memory, peak_memory = tracemalloc.get_traced_memory()
        metrics.memory_mb = (current_memory / (1024 * 1024)) - initial_memory
        metrics.memory_peak_mb = (peak_memory / (1024 * 1024)) - initial_memory

        # Get processor metrics if available
        if hasattr(bus, "processor") and hasattr(bus.processor, "get_metrics"):
            processor_metrics = bus.processor.get_metrics()
            metrics.cache_hits = processor_metrics.get("cache_hits", 0)
            metrics.cache_misses = processor_metrics.get("cache_misses", 0)
            if metrics.cache_hits + metrics.cache_misses > 0:
                metrics.cache_hit_rate = metrics.cache_hits / (
                    metrics.cache_hits + metrics.cache_misses
                )

        # Stop bus and cleanup
        await bus.stop()
        tracemalloc.stop()
        gc.collect()

        return metrics

    async def profile_message_processor(self) -> PerformanceMetrics:
        """Profile MessageProcessor independently."""
        logger.info(f"[{CONSTITUTIONAL_HASH}] Profiling message processor...")

        if not AGENT_BUS_AVAILABLE:
            logger.error("MessageProcessor not available")
            return PerformanceMetrics()

        metrics = PerformanceMetrics()
        processor = MessageProcessor()

        # Warmup
        for i in range(self.warmup_iterations):
            message = AgentMessage(
                from_agent=f"agent_{i}",
                to_agent="target",
                message_type=MessageType.QUERY,
                content={"test": "data"},
                constitutional_hash=CONSTITUTIONAL_HASH,
            )
            try:
                await processor.process(message)
            except Exception:
                pass

        # Measurement
        start_time = time.perf_counter()

        for i in range(self.iterations):
            message = AgentMessage(
                from_agent=f"agent_{i}",
                to_agent="target",
                message_type=MessageType.QUERY,
                content={"test": "data"},
                constitutional_hash=CONSTITUTIONAL_HASH,
            )

            iteration_start = time.perf_counter()

            try:
                result = await processor.process(message)
                iteration_end = time.perf_counter()

                latency_ms = (iteration_end - iteration_start) * 1000
                metrics.latencies.append(latency_ms)

                if result.is_valid:
                    metrics.successful_operations += 1
                else:
                    metrics.failed_operations += 1

            except Exception:
                iteration_end = time.perf_counter()
                metrics.failed_operations += 1

        end_time = time.perf_counter()

        # Calculate metrics
        metrics.duration_seconds = end_time - start_time
        metrics.total_operations = self.iterations
        metrics.throughput_rps = metrics.successful_operations / metrics.duration_seconds

        if metrics.latencies:
            metrics.p50_latency_ms, metrics.p95_latency_ms, metrics.p99_latency_ms = (
                self.calculate_percentiles(metrics.latencies)
            )
            metrics.mean_latency_ms = sum(metrics.latencies) / len(metrics.latencies)
            metrics.min_latency_ms = min(metrics.latencies)
            metrics.max_latency_ms = max(metrics.latencies)

        # Get processor-specific metrics
        proc_metrics = processor.get_metrics()
        logger.info(f"Processor metrics: {proc_metrics}")

        return metrics

    def identify_bottlenecks(
        self, component_metrics: Dict[str, PerformanceMetrics]
    ) -> List[BottleneckAnalysis]:
        """Identify performance bottlenecks from component metrics."""
        bottlenecks = []

        # Calculate total latency
        total_p99 = sum(m.p99_latency_ms for m in component_metrics.values())

        for component, metrics in component_metrics.items():
            if total_p99 > 0:
                percentage = (metrics.p99_latency_ms / total_p99) * 100
            else:
                percentage = 0.0

            # Determine severity
            if metrics.p99_latency_ms > 2.0:  # >2ms is critical
                severity = "critical"
            elif metrics.p99_latency_ms > 1.0:  # >1ms is high
                severity = "high"
            elif metrics.p99_latency_ms > 0.5:  # >0.5ms is medium
                severity = "medium"
            else:
                severity = "low"

            bottlenecks.append(
                BottleneckAnalysis(
                    component=component,
                    mean_latency_ms=metrics.mean_latency_ms,
                    p99_latency_ms=metrics.p99_latency_ms,
                    percentage_of_total=percentage,
                    severity=severity,
                )
            )

        # Sort by P99 latency descending
        bottlenecks.sort(key=lambda x: x.p99_latency_ms, reverse=True)

        return bottlenecks

    def print_metrics(self, name: str, metrics: PerformanceMetrics) -> None:
        """Print formatted metrics."""
        logging.info(f"\n{'=' * 80}")
        logging.info(f" {name}")
        logging.info(f"{'=' * 80}")
        logging.info(f"Constitutional Hash: {metrics.constitutional_hash}")
        logging.info("\nLatency Metrics:")
        logging.info(f"  P50: {metrics.p50_latency_ms:.3f}ms")
        logging.info(f"  P95: {metrics.p95_latency_ms:.3f}ms")
        logging.info(f"  P99: {metrics.p99_latency_ms:.3f}ms")
        logging.info(f"  Mean: {metrics.mean_latency_ms:.3f}ms")
        logging.info(f"  Min: {metrics.min_latency_ms:.3f}ms")
        logging.info(f"  Max: {metrics.max_latency_ms:.3f}ms")

        logging.info("\nThroughput Metrics:")
        logging.info(f"  Total Operations: {metrics.total_operations}")
        logging.info(f"  Successful: {metrics.successful_operations}")
        logging.error(f"  Failed: {metrics.failed_operations}")
        logging.info(f"  Duration: {metrics.duration_seconds:.2f}s")
        logging.info(f"  Throughput: {metrics.throughput_rps:.1f} RPS")

        logging.info("\nResource Metrics:")
        logging.info(f"  CPU: {metrics.cpu_percent:.1f}%")
        logging.info(f"  Memory: {metrics.memory_mb:.1f} MB")
        logging.info(f"  Memory Peak: {metrics.memory_peak_mb:.1f} MB")

        if metrics.cache_hits + metrics.cache_misses > 0:
            logging.info("\nCache Metrics:")
            logging.info(f"  Hits: {metrics.cache_hits}")
            logging.info(f"  Misses: {metrics.cache_misses}")
            logging.info(f"  Hit Rate: {metrics.cache_hit_rate:.1%}")

    def print_bottlenecks(self, bottlenecks: List[BottleneckAnalysis]) -> None:
        """Print bottleneck analysis."""
        logging.info(f"\n{'=' * 80}")
        logging.info(" Bottleneck Analysis")
        logging.info(f"{'=' * 80}")

        if not bottlenecks:
            logging.info("No bottlenecks identified.")
            return

        logging.info(f"\n{'Component':<30} {'P99 Latency':<15} {'% of Total':<12} {'Severity':<10}")
        logging.info("-" * 80)

        for bottleneck in bottlenecks:
            logging.info(
                f"{bottleneck.component:<30} "
                f"{bottleneck.p99_latency_ms:>8.3f}ms    "
                f"{bottleneck.percentage_of_total:>7.1f}%     "
                f"{bottleneck.severity.upper()}"
            )

    def print_recommendations(
        self, metrics: PerformanceMetrics, bottlenecks: List[BottleneckAnalysis]
    ) -> None:
        """Print optimization recommendations."""
        logging.info(f"\n{'=' * 80}")
        logging.info(" Optimization Recommendations")
        logging.info(f"{'=' * 80}\n")

        recommendations = []

        # Check against targets
        if metrics.p99_latency_ms > 5.0:
            recommendations.append(
                f"🔴 CRITICAL: P99 latency {metrics.p99_latency_ms:.3f}ms exceeds 5ms target by "
                f"{((metrics.p99_latency_ms / 5.0) - 1) * 100:.1f}%"
            )
        elif metrics.p99_latency_ms > 1.0:
            recommendations.append(
                f"🟡 WARNING: P99 latency {metrics.p99_latency_ms:.3f}ms above optimal (<1ms)"
            )
        else:
            recommendations.append(
                f"🟢 EXCELLENT: P99 latency {metrics.p99_latency_ms:.3f}ms meets targets"
            )

        if metrics.throughput_rps < 100:
            recommendations.append(
                f"🔴 CRITICAL: Throughput {metrics.throughput_rps:.1f} RPS below 100 RPS minimum"
            )
        elif metrics.throughput_rps < 1000:
            recommendations.append(
                f"🟡 WARNING: Throughput {metrics.throughput_rps:.1f} RPS has room for improvement"
            )
        else:
            recommendations.append(
                f"🟢 EXCELLENT: Throughput {metrics.throughput_rps:.1f} RPS exceeds targets"
            )

        if metrics.cache_hit_rate > 0:
            if metrics.cache_hit_rate < 0.85:
                recommendations.append(
                    f"🔴 CRITICAL: Cache hit rate {metrics.cache_hit_rate:.1%} below 85% target"
                )
            elif metrics.cache_hit_rate < 0.95:
                recommendations.append(
                    f"🟡 WARNING: Cache hit rate {metrics.cache_hit_rate:.1%} could be improved"
                )
            else:
                recommendations.append(
                    f"🟢 EXCELLENT: Cache hit rate {metrics.cache_hit_rate:.1%} meets targets"
                )

        # Component-specific recommendations
        for bottleneck in bottlenecks[:3]:  # Top 3 bottlenecks
            if bottleneck.severity == "critical":
                recommendations.append(
                    f"🔴 Optimize {bottleneck.component}: {bottleneck.p99_latency_ms:.3f}ms P99 "
                    f"({bottleneck.percentage_of_total:.1f}% of total)"
                )

        for rec in recommendations:
            logging.info(f"  {rec}")


async def main():
    """Main profiling execution."""
    logging.info(f"\n{'=' * 80}")
    logging.info(" ACGS-2 Comprehensive Performance Profiler")
    logging.info(f" Constitutional Hash: {CONSTITUTIONAL_HASH}")
    logging.info(f"{'=' * 80}\n")

    profiler = PerformanceProfiler(iterations=1000, warmup_iterations=100)

    # Profile components
    component_metrics = {}

    logging.info("Running performance profiling...")
    logging.info(f"Iterations: {profiler.iterations} (after {profiler.warmup_iterations} warmup)")

    # Profile message processor
    processor_metrics = await profiler.profile_message_processor()
    component_metrics["MessageProcessor"] = processor_metrics
    profiler.print_metrics("MessageProcessor Performance", processor_metrics)

    # Profile full bus
    bus_metrics = await profiler.profile_message_processing()
    component_metrics["EnhancedAgentBus"] = bus_metrics
    profiler.print_metrics("Enhanced Agent Bus Performance", bus_metrics)

    # Identify bottlenecks
    bottlenecks = profiler.identify_bottlenecks(component_metrics)
    profiler.print_bottlenecks(bottlenecks)

    # Print recommendations
    profiler.print_recommendations(bus_metrics, bottlenecks)

    # Summary
    logging.info(f"\n{'=' * 80}")
    logging.info(" Performance Summary")
    logging.info(f"{'=' * 80}\n")
    logging.info(f"  Overall P99 Latency: {bus_metrics.p99_latency_ms:.3f}ms (target: <5ms)")
    logging.info(f"  Overall Throughput: {bus_metrics.throughput_rps:.1f} RPS (target: >100 RPS)")
    logging.info(f"  Cache Hit Rate: {bus_metrics.cache_hit_rate:.1%} (target: >85%)")
    logging.info(f"  Constitutional Compliance: {bus_metrics.compliance_rate:.1%}")
    logging.info(f"\n{'=' * 80}\n")


if __name__ == "__main__":
    asyncio.run(main())
