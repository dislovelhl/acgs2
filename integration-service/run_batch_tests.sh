#!/bin/bash
# Test Verification Script for Batch Event Processing
# Run this script to verify all batch processing tests pass

set -e

echo "========================================="
echo "Batch Event Processing Test Suite"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to integration-service directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Working directory: $(pwd)"
echo ""

# Check if pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}❌ pytest is not installed${NC}"
    echo "Install it with: pip install pytest pytest-asyncio"
    exit 1
fi

echo -e "${YELLOW}Running batch processing tests...${NC}"
echo ""

# Track results
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run tests and track results
run_test() {
    local test_name="$1"
    local test_path="$2"
    local test_filter="$3"

    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}Running: $test_name${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    if [ -n "$test_filter" ]; then
        if pytest "$test_path" -v -k "$test_filter" --tb=short; then
            echo -e "${GREEN}✅ $test_name: PASSED${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}❌ $test_name: FAILED${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    else
        if pytest "$test_path" -v --tb=short; then
            echo -e "${GREEN}✅ $test_name: PASSED${NC}"
            TESTS_PASSED=$((TESTS_PASSED + 1))
        else
            echo -e "${RED}❌ $test_name: FAILED${NC}"
            TESTS_FAILED=$((TESTS_FAILED + 1))
        fi
    fi

    echo ""
}

# Run test suites
run_test "Base Integration Batch Tests" "tests/integrations/test_base.py" ""
run_test "Splunk Adapter Batch Tests" "tests/integrations/test_splunk.py" "batch"
run_test "Sentinel Adapter Batch Tests" "tests/integrations/test_sentinel.py" "batch"

# Print summary
echo -e "${YELLOW}=========================================${NC}"
echo -e "${YELLOW}Test Suite Summary${NC}"
echo -e "${YELLOW}=========================================${NC}"
echo ""
echo "Total test groups run: $((TESTS_PASSED + TESTS_FAILED))"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All batch processing tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Update implementation_plan.json to mark subtask-5-4 as completed"
    echo "2. Commit the changes with: git commit -m 'auto-claude: subtask-5-4 - Execute full test suite'"
    echo "3. Update QA sign-off status"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review the output above.${NC}"
    exit 1
fi
