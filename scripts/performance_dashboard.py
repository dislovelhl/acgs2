#!/usr/bin/env python3
"""
ACGS-2 Performance Monitoring Dashboard
Analyzes performance trends and alerts on regressions
"""

import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def analyze_performance_trends():
    """Analyze performance trends from historical data."""
    reports_dir = Path("reports/performance")
    results_files = list(reports_dir.glob("performance_benchmark_report_*.json"))

    if not results_files:
        print("No performance reports found")
        return

    # Load all results
    results = []
    for file_path in sorted(results_files):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
                timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
                results.append(
                    {"timestamp": timestamp, "results": data["results"], "summary": data["summary"]}
                )
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    if not results:
        print("No valid performance data found")
        return

    # Create trend analysis
    create_performance_trends(results)
    check_for_regressions(results)
    generate_alerts(results)


def create_performance_trends(results):
    """Create performance trend visualizations."""
    df = pd.DataFrame(
        [
            {
                "timestamp": r["timestamp"],
                "latency_p99": next(
                    (res["actual"] for res in r["results"] if res["metric"] == "latency_p99"), None
                ),
                "throughput_rps": next(
                    (res["actual"] for res in r["results"] if res["metric"] == "throughput_rps"),
                    None,
                ),
                "cache_hit_rate": next(
                    (res["actual"] for res in r["results"] if res["metric"] == "cache_hit_rate"),
                    None,
                ),
            }
            for r in results
        ]
    )

    # Create trend plots
    fig, axes = plt.subplots(3, 1, figsize=(12, 8))
    fig.suptitle("ACGS-2 Performance Trends")

    df.plot(x="timestamp", y="latency_p99", ax=axes[0], title="P99 Latency (ms)")
    df.plot(x="timestamp", y="throughput_rps", ax=axes[1], title="Throughput (RPS)")
    df.plot(x="timestamp", y="cache_hit_rate", ax=axes[2], title="Cache Hit Rate")

    plt.tight_layout()
    plt.savefig("reports/trends/performance_trends.png")
    print("📊 Performance trend charts saved to reports/trends/performance_trends.png")


def check_for_regressions(results):
    """Check for performance regressions."""
    if len(results) < 2:
        return

    latest = results[-1]
    previous = results[-2]

    regressions = []

    for latest_result in latest["results"]:
        metric = latest_result["metric"]
        latest_value = latest_result["actual"]

        # Find corresponding previous result
        prev_result = next((r for r in previous["results"] if r["metric"] == metric), None)
        if prev_result:
            prev_value = prev_result["actual"]

            # Check for regressions (latency increase, throughput decrease)
            if metric == "latency_p99" and latest_value > prev_value * 1.1:  # 10% increase
                regressions.append(
                    f"🚨 {metric}: {prev_value:.2f} → {latest_value:.2f} (+{((latest_value / prev_value) - 1) * 100:.1f}%)"
                )
            elif (
                metric in ["throughput_rps", "cache_hit_rate"] and latest_value < prev_value * 0.9
            ):  # 10% decrease
                regressions.append(
                    f"🚨 {metric}: {prev_value:.2f} → {latest_value:.2f} (-{((prev_value / latest_value) - 1) * 100:.1f}%)"
                )

    if regressions:
        print("\n🚨 PERFORMANCE REGRESSIONS DETECTED:")
        for regression in regressions:
            print(f"  {regression}")

        # Save alert
        alert_file = Path("reports/monitoring/performance_alerts.txt")
        with open(alert_file, "a") as f:
            f.write(f"\n{datetime.now()}: Performance regressions detected\n")
            for regression in regressions:
                f.write(f"  {regression}\n")


def generate_alerts(results):
    """Generate alerts based on performance thresholds."""
    if not results:
        return

    latest = results[-1]

    # Define alert thresholds
    alerts = []

    for result in latest["results"]:
        metric = result["metric"]
        actual = result["actual"]
        target = result["target"]

        if metric == "latency_p99" and actual > target:
            alerts.append(f"⚠️  P99 Latency exceeds target: {actual:.2f}ms > {target:.2f}ms")
        elif metric == "throughput_rps" and actual < target:
            alerts.append(f"⚠️  Throughput below target: {actual:.0f} RPS < {target:.0f} RPS")
        elif metric == "cache_hit_rate" and actual < target:
            alerts.append(f"⚠️  Cache hit rate below target: {actual:.2%} < {target:.2%}")

    if alerts:
        print("\n⚠️  PERFORMANCE ALERTS:")
        for alert in alerts:
            print(f"  {alert}")


if __name__ == "__main__":
    analyze_performance_trends()
