#!/bin/bash
"""
Unified Test Runner Script for ACGS-2

This script runs all tests across components using their respective configurations.
It resolves pytest configuration conflicts by running tests in component-specific directories.
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Running ACGS-2 Unified Test Suite"
echo "====================================="

# Change to project root
cd "$(dirname "$0")/.."

TOTAL_COMPONENTS=0
PASSED_COMPONENTS=0
FAILED_COMPONENTS=0
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

run_component_tests() {
    local component_name="$1"
    local test_command="$2"
    local expected_tests="$3"

    echo -e "\n${YELLOW}Running ${component_name}...${NC}"
    TOTAL_COMPONENTS=$((TOTAL_COMPONENTS + 1))

    if eval "$test_command"; then
        echo -e "${GREEN}✅ ${component_name}: PASSED${NC}"
        PASSED_COMPONENTS=$((PASSED_COMPONENTS + 1))
        if [ -n "$expected_tests" ]; then
            PASSED_TESTS=$((PASSED_TESTS + expected_tests))
        fi
    else
        echo -e "${RED}❌ ${component_name}: FAILED${NC}"
        FAILED_COMPONENTS=$((FAILED_COMPONENTS + 1))
    fi

    if [ -n "$expected_tests" ]; then
        TOTAL_TESTS=$((TOTAL_TESTS + expected_tests))
    fi
}

# Run test components with proper working directories
run_component_tests "Enhanced Agent Bus Tests" "cd acgs2-core/enhanced_agent_bus && python -m pytest tests/ -q --tb=line" 4570
run_component_tests "Policy Registry Tests" "cd acgs2-core && python -m pytest services/policy_registry/tests/ -q --tb=line" 120
run_component_tests "Metering Tests" "cd acgs2-core && python -m pytest services/metering/tests/ -q --tb=line" 9
run_component_tests "Shared Tests" "cd acgs2-core && python -m pytest shared/tests/ -q --tb=line" 10
run_component_tests "Core Tests" "cd acgs2-core && python -m pytest tests/ -q --tb=line" 6
run_component_tests "Observability Tests" "cd acgs2-observability && python -m pytest tests/ -q --tb=line" 28
run_component_tests "Governance Experiments" "cd acgs2-research && python -m pytest governance-experiments/tests/ -q --tb=line" 4
run_component_tests "Research Tests" "cd acgs2-research && python -m pytest tests/ -q --tb=line" 5

# Performance validation
echo -e "\n${YELLOW}Running Performance Validation...${NC}"
if cd acgs2-core && python testing/comprehensive_profiler.py --iterations 50 --baseline 2>/dev/null; then
    echo -e "${GREEN}✅ Performance Validation: PASSED${NC}"
    PASSED_COMPONENTS=$((PASSED_COMPONENTS + 1))
else
    echo -e "${RED}❌ Performance Validation: FAILED${NC}"
    FAILED_COMPONENTS=$((FAILED_COMPONENTS + 1))
fi
TOTAL_COMPONENTS=$((TOTAL_COMPONENTS + 1))

# Print summary
echo -e "\n====================================="
echo "🧪 ACGS-2 Test Suite Results"
echo "====================================="
echo "Components: $TOTAL_COMPONENTS total, $PASSED_COMPONENTS passed, $FAILED_COMPONENTS failed"
echo "Tests: $TOTAL_TESTS expected tests"

if [ $FAILED_COMPONENTS -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Check output above for details.${NC}"
    exit 1
fi
