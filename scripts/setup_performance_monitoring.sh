#!/bin/bash
# ACGS-2 Performance Monitoring Setup
# Automated performance regression testing and monitoring

set -e

echo "📊 Setting up ACGS-2 Performance Monitoring"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORTS_DIR="$PROJECT_ROOT/reports"
PERF_DIR="$REPORTS_DIR/performance"
MONITORING_DIR="$REPORTS_DIR/monitoring"

# Create directories
mkdir -p "$PERF_DIR"
mkdir -p "$MONITORING_DIR"
mkdir -p "$REPORTS_DIR/trends"

echo "📁 Created monitoring directories"

# Create cron job for regular performance testing
CRON_JOB="@daily $PROJECT_ROOT/scripts/performance_regression_test.sh >> $MONITORING_DIR/performance_cron.log 2>&1"
CRON_JOB_WEEKLY="@weekly $PROJECT_ROOT/scripts/quality_gate.sh >> $MONITORING_DIR/quality_cron.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "performance_regression_test.sh"; then
    echo -e "${YELLOW}⚠️  Performance monitoring cron job already exists${NC}"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo -e "${GREEN}✅ Added daily performance regression testing to cron${NC}"
fi

if crontab -l 2>/dev/null | grep -q "quality_gate.sh"; then
    echo -e "${YELLOW}⚠️  Quality gate cron job already exists${NC}"
else
    (crontab -l 2>/dev/null; echo "$CRON_JOB_WEEKLY") | crontab -
    echo -e "${GREEN}✅ Added weekly quality gate monitoring to cron${NC}"
fi

# Create performance monitoring dashboard script
cat > "$PROJECT_ROOT/scripts/performance_dashboard.py" << 'EOF'
#!/usr/bin/env python3
"""
ACGS-2 Performance Monitoring Dashboard
Analyzes performance trends and alerts on regressions
"""

import json
import glob
from pathlib import Path
from datetime import datetime, timedelta
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
            with open(file_path, 'r') as f:
                data = json.load(f)
                timestamp = datetime.fromisoformat(data['timestamp'].replace('Z', '+00:00'))
                results.append({
                    'timestamp': timestamp,
                    'results': data['results'],
                    'summary': data['summary']
                })
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
    df = pd.DataFrame([
        {
            'timestamp': r['timestamp'],
            'latency_p99': next((res['actual'] for res in r['results'] if res['metric'] == 'latency_p99'), None),
            'throughput_rps': next((res['actual'] for res in r['results'] if res['metric'] == 'throughput_rps'), None),
            'cache_hit_rate': next((res['actual'] for res in r['results'] if res['metric'] == 'cache_hit_rate'), None),
        }
        for r in results
    ])

    # Create trend plots
    fig, axes = plt.subplots(3, 1, figsize=(12, 8))
    fig.suptitle('ACGS-2 Performance Trends')

    df.plot(x='timestamp', y='latency_p99', ax=axes[0], title='P99 Latency (ms)')
    df.plot(x='timestamp', y='throughput_rps', ax=axes[1], title='Throughput (RPS)')
    df.plot(x='timestamp', y='cache_hit_rate', ax=axes[2], title='Cache Hit Rate')

    plt.tight_layout()
    plt.savefig('reports/trends/performance_trends.png')
    print("📊 Performance trend charts saved to reports/trends/performance_trends.png")

def check_for_regressions(results):
    """Check for performance regressions."""
    if len(results) < 2:
        return

    latest = results[-1]
    previous = results[-2]

    regressions = []

    for latest_result in latest['results']:
        metric = latest_result['metric']
        latest_value = latest_result['actual']

        # Find corresponding previous result
        prev_result = next((r for r in previous['results'] if r['metric'] == metric), None)
        if prev_result:
            prev_value = prev_result['actual']

            # Check for regressions (latency increase, throughput decrease)
            if metric == 'latency_p99' and latest_value > prev_value * 1.1:  # 10% increase
                regressions.append(f"🚨 {metric}: {prev_value:.2f} → {latest_value:.2f} (+{((latest_value/prev_value)-1)*100:.1f}%)")
            elif metric in ['throughput_rps', 'cache_hit_rate'] and latest_value < prev_value * 0.9:  # 10% decrease
                regressions.append(f"🚨 {metric}: {prev_value:.2f} → {latest_value:.2f} (-{((prev_value/latest_value)-1)*100:.1f}%)")

    if regressions:
        print("\n🚨 PERFORMANCE REGRESSIONS DETECTED:")
        for regression in regressions:
            print(f"  {regression}")

        # Save alert
        alert_file = Path("reports/monitoring/performance_alerts.txt")
        with open(alert_file, 'a') as f:
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

    for result in latest['results']:
        metric = result['metric']
        actual = result['actual']
        target = result['target']

        if metric == 'latency_p99' and actual > target:
            alerts.append(f"⚠️  P99 Latency exceeds target: {actual:.2f}ms > {target:.2f}ms")
        elif metric == 'throughput_rps' and actual < target:
            alerts.append(f"⚠️  Throughput below target: {actual:.0f} RPS < {target:.0f} RPS")
        elif metric == 'cache_hit_rate' and actual < target:
            alerts.append(f"⚠️  Cache hit rate below target: {actual:.2%} < {target:.2%}")

    if alerts:
        print("\n⚠️  PERFORMANCE ALERTS:")
        for alert in alerts:
            print(f"  {alert}")

if __name__ == '__main__':
    analyze_performance_trends()
EOF

chmod +x "$PROJECT_ROOT/scripts/performance_dashboard.py"
echo -e "${GREEN}✅ Created performance monitoring dashboard${NC}"

# Create systemd service for continuous monitoring (optional)
SERVICE_FILE="/etc/systemd/system/acgs2-performance-monitor.service"
if [ -w /etc/systemd/system ]; then
    cat > "$SERVICE_FILE" << EOF
[Unit]
Description=ACGS-2 Performance Monitor
After=network.target

[Service]
Type=oneshot
User=$USER
WorkingDirectory=$PROJECT_ROOT
ExecStart=$PROJECT_ROOT/scripts/performance_regression_test.sh
EOF

    echo -e "${GREEN}✅ Created systemd service for automated monitoring${NC}"
    echo "   Enable with: sudo systemctl enable acgs2-performance-monitor"
    echo "   Run manually: sudo systemctl start acgs2-performance-monitor"
else
    echo -e "${YELLOW}⚠️  Cannot create systemd service (no write access to /etc/systemd/system)${NC}"
fi

# Create monitoring configuration
cat > "$REPORTS_DIR/monitoring/config.json" << EOF
{
  "performance_targets": {
    "latency_p99_ms": 0.328,
    "throughput_rps": 2605,
    "cache_hit_rate": 0.95,
    "memory_mb": 4.0,
    "cpu_percent": 75.0
  },
  "alert_thresholds": {
    "latency_regression_percent": 10,
    "throughput_regression_percent": 10,
    "cache_regression_percent": 5
  },
  "monitoring_schedule": {
    "performance_tests": "daily",
    "quality_gates": "weekly",
    "chaos_tests": "monthly"
  }
}
EOF

echo -e "${GREEN}✅ Created monitoring configuration${NC}"

# Initial performance baseline
echo "🏃 Running initial performance baseline..."
if "$PROJECT_ROOT/scripts/performance_regression_test.sh" > "$MONITORING_DIR/baseline.log" 2>&1; then
    echo -e "${GREEN}✅ Initial performance baseline established${NC}"
else
    echo -e "${YELLOW}⚠️  Could not establish baseline (services may not be running)${NC}"
fi

echo
echo "🎯 Performance Monitoring Setup Complete!"
echo "========================================="
echo "Daily performance regression testing is now scheduled"
echo "Weekly quality gate monitoring is active"
echo "Results stored in: $REPORTS_DIR/"
echo
echo "Manual commands:"
echo "  Run performance test: ./scripts/performance_regression_test.sh"
echo "  Run quality gate: ./scripts/quality_gate.sh"
echo "  View dashboard: python scripts/performance_dashboard.py"
echo "  View trends: open reports/trends/performance_trends.png"
