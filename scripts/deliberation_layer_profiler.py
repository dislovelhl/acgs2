#!/usr/bin/env python3
"""
ACGS-2 Deliberation Layer Throughput Profiler
Identifies bottlenecks in the deliberation layer to close the 41% throughput gap.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Dict, List

import numpy as np


@dataclass
class ProfilingResult:
    """Results from profiling run."""

    total_requests: int
    total_time: float
    requests_per_second: float
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    bottlenecks: List[str]
    recommendations: List[str]


class DeliberationLayerProfiler:
    """Profiles the deliberation layer for throughput optimization."""

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def profile_deliberation_queue(self, num_requests: int = 1000) -> ProfilingResult:
        """Profile the deliberation queue throughput."""
        print(f"🔍 Profiling Deliberation Queue with {num_requests} requests...")

        # Import deliberation components
        from acgs2_core.enhanced_agent_bus.deliberation_layer.deliberation_queue import (
            DeliberationQueue,
        )
        from acgs2_core.enhanced_agent_bus.models import AgentMessage, MessageType, Priority

        queue = DeliberationQueue()
        latencies = []

        start_time = time.time()

        # Create test messages
        messages = []
        for i in range(num_requests):
            msg = AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                sender_id=f"agent_{i}",
                content={"action": f"test_action_{i}", "data": "x" * 100},
                priority=Priority.NORMAL if i % 10 != 0 else Priority.HIGH,
                message_id=f"msg_{i}",
            )
            messages.append(msg)

        # Profile enqueue operations
        enqueue_start = time.time()
        task_ids = []
        for msg in messages:
            task_id = await queue.enqueue_for_deliberation(msg)
            task_ids.append(task_id)

        enqueue_time = time.time() - enqueue_start
        total_time = time.time() - start_time

        # Calculate metrics
        rps = num_requests / total_time
        avg_latency = (enqueue_time / num_requests) * 1000

        # Simulate some processing to measure full pipeline
        await asyncio.sleep(0.1)  # Brief processing simulation

        bottlenecks = []
        recommendations = []

        # Analyze bottlenecks
        if rps < 100:  # Less than 100 RPS is concerning
            bottlenecks.append("Low enqueue throughput (<100 RPS)")
            recommendations.append("Consider async batching for enqueue operations")

        if avg_latency > 10:  # >10ms average latency
            bottlenecks.append("High average latency (>10ms)")
            recommendations.append("Profile JSON serialization/deserialization overhead")

        # Check for lock contention
        if hasattr(queue, "_lock"):
            bottlenecks.append("Potential lock contention in enqueue operations")
            recommendations.append("Consider lock-free data structures or sharding")

        result = ProfilingResult(
            total_requests=num_requests,
            total_time=total_time,
            requests_per_second=rps,
            avg_latency_ms=avg_latency,
            p50_latency_ms=np.percentile(latencies, 50) if latencies else 0,
            p95_latency_ms=np.percentile(latencies, 95) if latencies else 0,
            p99_latency_ms=np.percentile(latencies, 99) if latencies else 0,
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )

        await queue.cleanup()
        return result

    async def profile_impact_scorer(self, num_requests: int = 1000) -> ProfilingResult:
        """Profile the impact scorer throughput."""
        print(f"🎯 Profiling Impact Scorer with {num_requests} requests...")

        from acgs2_core.enhanced_agent_bus.deliberation_layer.impact_scorer import ImpactScorer
        from acgs2_core.enhanced_agent_bus.models import AgentMessage, MessageType, Priority

        scorer = ImpactScorer()
        latencies = []

        start_time = time.time()

        # Create test messages with varying complexity
        messages = []
        for i in range(num_requests):
            complexity = "low" if i % 3 == 0 else "medium" if i % 3 == 1 else "high"
            content_size = 50 if complexity == "low" else 200 if complexity == "medium" else 500

            msg = AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                sender_id=f"agent_{i}",
                content={
                    "action": f"test_action_{i}",
                    "data": "x" * content_size,
                    "keywords": ["test"]
                    * (1 if complexity == "low" else 5 if complexity == "medium" else 15),
                },
                priority=Priority.NORMAL if i % 10 != 0 else Priority.HIGH,
                message_id=f"msg_{i}",
            )
            messages.append(msg)

        # Profile scoring operations
        scoring_start = time.time()
        for msg in messages:
            req_start = time.time()
            result = await scorer.score_impact(msg)
            latencies.append((time.time() - req_start) * 1000)

        time.time() - scoring_start
        total_time = time.time() - start_time

        # Calculate metrics
        rps = num_requests / total_time
        avg_latency = np.mean(latencies)

        bottlenecks = []
        recommendations = []

        # Analyze bottlenecks
        if rps < 50:  # Impact scoring should be faster
            bottlenecks.append("Low scoring throughput (<50 RPS)")
            recommendations.append("Optimize BERT inference with ONNX or TensorRT")

        if avg_latency > 50:  # >50ms average latency for scoring
            bottlenecks.append("High average scoring latency (>50ms)")
            recommendations.append("Implement scoring result caching")

        # Check model loading
        if hasattr(scorer, "_bert_enabled") and not scorer._bert_enabled:
            bottlenecks.append("BERT model not loaded efficiently")
            recommendations.append("Pre-load models at startup and use ONNX optimization")

        result = ProfilingResult(
            total_requests=num_requests,
            total_time=total_time,
            requests_per_second=rps,
            avg_latency_ms=avg_latency,
            p50_latency_ms=np.percentile(latencies, 50),
            p95_latency_ms=np.percentile(latencies, 95),
            p99_latency_ms=np.percentile(latencies, 99),
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )

        return result

    async def profile_full_pipeline(self, num_requests: int = 500) -> ProfilingResult:
        """Profile the full deliberation pipeline."""
        print(f"🔬 Profiling Full Deliberation Pipeline with {num_requests} requests...")

        from acgs2_core.enhanced_agent_bus.deliberation_layer.deliberation_queue import (
            DeliberationQueue,
        )
        from acgs2_core.enhanced_agent_bus.deliberation_layer.impact_scorer import ImpactScorer
        from acgs2_core.enhanced_agent_bus.models import AgentMessage, MessageType, Priority

        queue = DeliberationQueue()
        scorer = ImpactScorer()
        latencies = []

        start_time = time.time()

        # Create test messages
        messages = []
        for i in range(num_requests):
            msg = AgentMessage(
                message_type=MessageType.TASK_REQUEST,
                sender_id=f"agent_{i}",
                content={"action": f"test_action_{i}", "data": "x" * 200},
                priority=Priority.NORMAL if i % 10 != 0 else Priority.HIGH,
                message_id=f"msg_{i}",
            )
            messages.append(msg)

        # Profile full pipeline: scoring -> queuing -> processing
        for msg in messages:
            req_start = time.time()

            # Step 1: Impact scoring
            impact_result = await scorer.score_impact(msg)

            # Step 2: Queue for deliberation if high impact
            if impact_result.requires_deliberation:
                await queue.enqueue_for_deliberation(msg, requires_human_review=True)
                # Simulate brief processing
                await asyncio.sleep(0.001)

            latencies.append((time.time() - req_start) * 1000)

        total_time = time.time() - start_time

        # Calculate metrics
        rps = num_requests / total_time
        avg_latency = np.mean(latencies)

        bottlenecks = []
        recommendations = []

        # Analyze bottlenecks
        if rps < 30:  # Full pipeline should handle reasonable load
            bottlenecks.append("Low full pipeline throughput (<30 RPS)")
            recommendations.append("Implement parallel processing for scoring and queuing")

        if avg_latency > 100:  # >100ms for full pipeline
            bottlenecks.append("High full pipeline latency (>100ms)")
            recommendations.append("Add result caching and async batching")

        # Current target is 2,605 RPS, so we're at ~41% of target
        target_rps = 2605
        (rps / target_rps) * 100
        bottlenecks.append(".1f")
        recommendations.append("Focus optimization on impact scoring and queue processing")

        result = ProfilingResult(
            total_requests=num_requests,
            total_time=total_time,
            requests_per_second=rps,
            avg_latency_ms=avg_latency,
            p50_latency_ms=np.percentile(latencies, 50),
            p95_latency_ms=np.percentile(latencies, 95),
            p99_latency_ms=np.percentile(latencies, 99),
            bottlenecks=bottlenecks,
            recommendations=recommendations,
        )

        await queue.cleanup()
        return result

    async def run_comprehensive_profile(self) -> Dict[str, ProfilingResult]:
        """Run comprehensive profiling across all deliberation components."""
        print("🚀 Starting Comprehensive Deliberation Layer Profiling...")

        results = {}

        # Profile individual components
        results["deliberation_queue"] = await self.profile_deliberation_queue(1000)
        results["impact_scorer"] = await self.profile_impact_scorer(1000)
        results["full_pipeline"] = await self.profile_full_pipeline(500)

        # Print summary
        print("\n📊 PROFILING RESULTS SUMMARY")
        print("=" * 60)

        for component, result in results.items():
            print(f"\n🔹 {component.upper()}")
            print(f"   Throughput: {result.requests_per_second:.1f} RPS")
            print(f"   Avg Latency: {result.avg_latency_ms:.1f} ms")
            print(f"   P95 Latency: {result.p95_latency_ms:.1f} ms")
            print(f"   P99 Latency: {result.p99_latency_ms:.1f} ms")

            if result.bottlenecks:
                print("   🚨 Bottlenecks:")
                for bottleneck in result.bottlenecks:
                    print(f"      • {bottleneck}")

            if result.recommendations:
                print("   💡 Recommendations:")
                for rec in result.recommendations:
                    print(f"      • {rec}")

        # Overall assessment
        avg_rps = np.mean([r.requests_per_second for r in results.values()])
        target_rps = 2605
        current_percentage = (avg_rps / target_rps) * 100

        print("\n🎯 OVERALL ASSESSMENT")
        print(f"   Current Average RPS: {avg_rps:.1f}")
        print(f"   Target RPS: {target_rps}")
        print(f"   Current Percentage: {current_percentage:.1f}%")
        if current_percentage < 50:
            print("   🔴 STATUS: Critical - Major optimization required")
        elif current_percentage < 75:
            print("   🟡 STATUS: Warning - Optimization needed")
        else:
            print("   🟢 STATUS: Good - Minor tuning may help")

        print("\n📋 TOP OPTIMIZATION PRIORITIES:")
        print("   1. Optimize BERT inference in ImpactScorer (use ONNX/TensorRT)")
        print("   2. Implement async batching for queue operations")
        print("   3. Add result caching for scoring operations")
        print("   4. Consider parallel processing pipelines")
        print("   5. Profile and optimize JSON serialization overhead")

        return results


async def main():
    """Main profiling entry point."""
    profiler = DeliberationLayerProfiler()
    try:
        await profiler.run_comprehensive_profile()
    finally:
        profiler.executor.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
