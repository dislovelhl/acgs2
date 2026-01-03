#!/usr/bin/env python3
"""
Message Processor Profiling Tool
Constitutional Hash: cdd01ef066bc6cf2

Profiles the MessageProcessor pipeline to identify performance bottlenecks,
especially OpenTelemetry tracing impact and other potential issues.
"""

import asyncio
import cProfile
import io
import pstats
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Optional

# Add the enhanced_agent_bus to path
sys.path.insert(0, '/home/dislove/document/acgs2/acgs2-core')

# Mock missing dependencies
sys.modules['litellm'] = type(sys)('litellm')
sys.modules['litellm.caching'] = type(sys)('caching')
sys.modules['config'] = type(sys)('config')
sys.modules['config'].BusConfiguration = type('BusConfiguration', (), {
    'intelligence': type('obj', (object,), {'intent_classifier_enabled': False}),
    'deliberation': type('obj', (object,), {'enabled': False})
})()

try:
    from enhanced_agent_bus.message_processor import MessageProcessor
    from enhanced_agent_bus.models import AgentMessage, MessageType, Priority
except ImportError as e:
    print(f"Failed to import MessageProcessor: {e}")
    sys.exit(1)


@dataclass
class ProfilingResult:
    """Result of profiling a single operation."""
    operation: str
    total_time: float
    call_count: int
    avg_time: float
    cumulative_time: float
    filename_lineno: str


@dataclass
class PipelineProfile:
    """Complete profiling results for message processing pipeline."""
    total_messages: int
    total_time: float
    avg_latency: float
    p95_latency: float
    p99_latency: float
    throughput_rps: float
    component_breakdown: Dict[str, ProfilingResult]
    memory_usage_mb: Optional[float] = None


@contextmanager
def profile_context():
    """Context manager for profiling code execution."""
    profiler = cProfile.Profile()
    profiler.enable()
    try:
        yield profiler
    finally:
        profiler.disable()


async def profile_message_processing(num_messages: int = 1000) -> PipelineProfile:
    """
    Profile message processing performance.

    Args:
        num_messages: Number of messages to process

    Returns:
        PipelineProfile with detailed performance metrics
    """
    print(f"Profiling message processing with {num_messages} messages...")

    # Create processor with isolated mode to avoid external dependencies
    processor = MessageProcessor(isolated_mode=True)

    # Create test messages
    messages = []
    for i in range(num_messages):
        msg = AgentMessage(
            message_id=f'profile-{i}',
            from_agent='test-agent',
            to_agent='bus',
            message_type=MessageType.TASK_REQUEST,
            priority=Priority.NORMAL,
            content=f'test message {i}',
            tenant_id='test-tenant',
            constitutional_hash='cdd01ef066bc6cf2'
        )
        messages.append(msg)

    # Profile the entire processing pipeline
    latencies = []
    component_times = {}

    with profile_context() as profiler:
        start_time = time.perf_counter()

        for i, msg in enumerate(messages):
            msg_start = time.perf_counter()

            # Process message
            result = await processor.process(msg)

            msg_end = time.perf_counter()
            latency = (msg_end - msg_start) * 1000  # Convert to ms
            latencies.append(latency)

            if not result.is_valid:
                print(f"Warning: Message {i} failed validation: {result.errors}")

        end_time = time.perf_counter()

    total_time = end_time - start_time

    # Analyze profiling results
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats()

    # Parse profiling output to extract component times
    profile_output = s.getvalue()
    component_breakdown = parse_profiling_output(profile_output)

    # Calculate latency statistics
    latencies.sort()
    p95_index = int(0.95 * len(latencies))
    p99_index = int(0.99 * len(latencies))

    return PipelineProfile(
        total_messages=num_messages,
        total_time=total_time,
        avg_latency=sum(latencies) / len(latencies),
        p95_latency=latencies[p95_index],
        p99_latency=latencies[p99_index],
        throughput_rps=num_messages / total_time,
        component_breakdown=component_breakdown
    )


def parse_profiling_output(profile_output: str) -> Dict[str, ProfilingResult]:
    """
    Parse cProfile output to extract component timing information.

    Args:
        profile_output: Raw profiling output string

    Returns:
        Dictionary of component profiling results
    """
    results = {}
    lines = profile_output.split('\n')

    # Skip header lines
    in_stats = False
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('ncalls'):
            in_stats = True
            continue

        if not in_stats:
            continue

        # Parse stats line: ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        if line and not line.startswith('ncalls'):
            try:
                parts = line.split()
                if len(parts) >= 6:
                    ncalls = parts[0]
                    tottime = float(parts[1])
                    cumtime = float(parts[3])
                    filename_lineno = ' '.join(parts[5:])

                    # Extract function name
                    if '(' in filename_lineno and ')' in filename_lineno:
                        func_part = filename_lineno.split('(')[-1].split(')')[0]
                        if '.' in func_part:
                            operation = func_part.split('.')[-1]
                        else:
                            operation = func_part
                    else:
                        operation = filename_lineno

                    results[operation] = ProfilingResult(
                        operation=operation,
                        total_time=tottime,
                        call_count=int(ncalls.split('/')[0]) if '/' in ncalls else int(ncalls),
                        avg_time=tottime / (int(ncalls.split('/')[0]) if '/' in ncalls else int(ncalls)),
                        cumulative_time=cumtime,
                        filename_lineno=filename_lineno
                    )
            except (ValueError, IndexError):
                continue

    return results


def print_profiling_report(profile: PipelineProfile):
    """Print a detailed profiling report."""
    print("\n" + "="*80)
    print("MESSAGE PROCESSOR PROFILING REPORT")
    print("="*80)

    print("\nOVERALL PERFORMANCE:")
    print(f"  Total Messages: {profile.total_messages}")
    print(f"  Total Time: {profile.total_time:.2f}s")
    print(f"  Avg Latency: {profile.avg_latency:.2f}ms")
    print(f"  P95 Latency: {profile.p95_latency:.2f}ms")
    print(f"  P99 Latency: {profile.p99_latency:.2f}ms")
    print(f"  Throughput: {profile.throughput_rps:.0f} RPS")
    print(f"  Memory Usage: {profile.memory_usage_mb:.2f} MB" if profile.memory_usage_mb else "  Memory Usage: Not measured")

    print("\nTOP PERFORMANCE BOTTLENECKS:")

    # Sort components by cumulative time
    sorted_components = sorted(
        profile.component_breakdown.values(),
        key=lambda x: x.cumulative_time,
        reverse=True
    )

    for i, component in enumerate(sorted_components[:10]):  # Top 10
        print(f"  {i+1:2d}. {component.operation:<30} "
              f"{component.cumulative_time:>8.3f}s "
              f"({component.cumulative_time/profile.total_time*100:>5.1f}%) "
              f"calls: {component.call_count:>6}")

    print("\nDETAILED COMPONENT ANALYSIS:")

    # Group by potential bottleneck categories
    categories = {
        'Intent Classification': [],
        'Validation': [],
        'SDPC Processing': [],
        'Memory Profiling': [],
        'Other': []
    }

    for component in sorted_components:
        name = component.operation.lower()
        if 'intent' in name or 'classifier' in name:
            categories['Intent Classification'].append(component)
        elif 'valid' in name or 'check' in name:
            categories['Validation'].append(component)
        elif 'sdpc' in name or 'pacar' in name or 'asc' in name:
            categories['SDPC Processing'].append(component)
        elif 'profil' in name or 'memory' in name:
            categories['Memory Profiling'].append(component)
        else:
            categories['Other'].append(component)

    for category, components in categories.items():
        if components:
            print(f"\n  {category}:")
            for component in components[:5]:  # Top 5 per category
                    print(f"    {component.operation:<25} {component.cumulative_time:>8.3f}s ({component.cumulative_time/profile.total_time*100:>5.1f}%)")
    print("\n" + "="*80)


async def main():
    """Main profiling execution."""
    try:
        # Profile with different message volumes
        volumes = [100, 500, 1000]

        for num_messages in volumes:
            print(f"\n{'='*60}")
            print(f"PROFILING WITH {num_messages} MESSAGES")
            print(f"{'='*60}")

            profile = await profile_message_processing(num_messages)
            print_profiling_report(profile)

            # Brief pause between runs
            await asyncio.sleep(1)

    except Exception as e:
        print(f"Profiling failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
