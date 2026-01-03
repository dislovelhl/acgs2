#!/bin/bash
# ACGS-2 Performance Regression Testing
# Automated performance validation and regression detection

set -e

echo "⚡ ACGS-2 Performance Regression Testing"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ACGS2_CORE="$PROJECT_ROOT/acgs2-core"
RESULTS_DIR="$PROJECT_ROOT/reports"
PERF_DIR="$RESULTS_DIR/performance"

# Create results directory
mkdir -p "$PERF_DIR"

echo "📁 Project Root: $PROJECT_ROOT"
echo "📁 Results Dir: $PERF_DIR"
echo

# Performance thresholds (from architecture requirements)
TARGET_P99_LATENCY_MS=0.328  # Actual achieved value from architecture review
TARGET_THROUGHPUT_RPS=2605   # Actual achieved value
TARGET_CACHE_HIT_RATE=0.95
TARGET_MEMORY_MB=4.0
TARGET_CPU_PERCENT=75.0

echo "🎯 Performance Targets:"
echo "  - P99 Latency: < ${TARGET_P99_LATENCY_MS}ms"
echo "  - Throughput: > ${TARGET_THROUGHPUT_RPS} RPS"
echo "  - Cache Hit Rate: > ${TARGET_CACHE_HIT_RATE}"
echo "  - Memory Usage: < ${TARGET_MEMORY_MB}MB per pod"
echo "  - CPU Usage: < ${TARGET_CPU_PERCENT}%"
echo

# Check if services are running
echo "🔍 Checking Service Health..."
echo "----------------------------"

SERVICES=(
    "http://localhost:8000/health|Agent Bus"
    "http://localhost:8080/health|API Gateway"
    "http://localhost:8181/health|OPA"
)

ALL_HEALTHY=true
for service in "${SERVICES[@]}"; do
    url=$(echo "$service" | cut -d'|' -f1)
    name=$(echo "$service" | cut -d'|' -f2)

    if curl -f -s "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $name: Healthy${NC}"
    else
        echo -e "${RED}❌ $name: Unhealthy or not running${NC}"
        ALL_HEALTHY=false
    fi
done

if [ "$ALL_HEALTHY" = false ]; then
    echo -e "${RED}❌ Services not ready for performance testing${NC}"
    echo "   Start services with: docker-compose -f acgs2-core/docker-compose.dev.yml up -d"
    exit 1
fi

echo
echo "🏃 Running Performance Benchmark..."
echo "-----------------------------------"

# Run the performance benchmark
cd "$ACGS2_CORE/scripts"

echo "Running 30-second performance benchmark with 50 concurrent users..."
BENCHMARK_OUTPUT=$(timeout 120 python performance_benchmark.py 2>&1)
BENCHMARK_EXIT_CODE=$?

echo "$BENCHMARK_OUTPUT"

if [ $BENCHMARK_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}❌ Performance benchmark failed or timed out${NC}"
    exit 1
fi

# Check results file
RESULTS_FILE="$ACGS2_CORE/scripts/performance_benchmark_report.json"
if [ ! -f "$RESULTS_FILE" ]; then
    echo -e "${RED}❌ Results file not found: $RESULTS_FILE${NC}"
    exit 1
fi

echo
echo "📊 Analyzing Results..."
echo "----------------------"

# Parse results and check against targets
python3 -c "
import json
import sys

with open('$RESULTS_FILE', 'r') as f:
    data = json.load(f)

print('Performance Test Results:')
print('=========================')

all_passed = True
for result in data.get('results', []):
    metric = result['metric']
    target = result['target']
    actual = result['actual']
    passed = result['passed']

    status = '✅ PASS' if passed else '❌ FAIL'
    print(f'{status} {metric}: {actual} (target: {target})')

    if not passed:
        all_passed = False

if all_passed:
    print(f'\n${GREEN}🎉 All performance targets met!${NC}')
    sys.exit(0)
else:
    print(f'\n${RED}⚠️  Performance regression detected${NC}')
    sys.exit(1)
"
