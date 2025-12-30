import time

import numpy as np
from enhanced_agent_bus.deliberation_layer.impact_scorer import ImpactScorer


def benchmark_scorer(iterations=100):
    print(f"Starting benchmark with {iterations} iterations...")

    # Test data
    test_message = {
        "content": "CRITICAL: Security breach detected in the blockchain payment gateway. Emergency shutdown required.",
        "priority": "critical",
        "message_type": "security_alert",
        "tools": [{"name": "admin_execute"}],
    }

    # 1. Baseline Scorer (Standard BERT if possible)
    print("\n--- Baseline (bert-base-uncased) ---")
    start_time = time.time()
    try:
        baseline = ImpactScorer(model_name="bert-base-uncased")
        load_time = time.time() - start_time
        print(f"Model Load Time: {load_time:.4f}s")

        latencies = []
        for _ in range(iterations):
            s = time.time()
            baseline.calculate_impact_score(test_message)
            latencies.append(time.time() - s)

        print(f"Avg Inference Latency: {np.mean(latencies)*1000:.2f}ms")
        print(f"Throughput: {1/np.mean(latencies):.2f} qps")
    except Exception as e:
        print(f"Baseline failed: {e}")

    # 2. Optimized Scorer (DistilBERT)
    print("\n--- Optimized (distilbert-base-uncased) ---")
    start_time = time.time()
    try:
        optimized = ImpactScorer(model_name="distilbert-base-uncased")
        load_time = time.time() - start_time
        print(f"Model Load Time: {load_time:.4f}s")

        latencies = []
        for _ in range(iterations):
            s = time.time()
            optimized.calculate_impact_score(test_message)
            latencies.append(time.time() - s)

        print(f"Avg Inference Latency: {np.mean(latencies)*1000:.2f}ms")
        print(f"Throughput: {1/np.mean(latencies):.2f} qps")
    except Exception as e:
        print(f"Optimized failed: {e}")


if __name__ == "__main__":
    benchmark_scorer()
